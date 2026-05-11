"""Optional asynchronous DNS existence prober.

Round-robin over multiple aiodns resolvers with a bounded in-memory cache.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from itertools import cycle

import aiodns

from .config import DnsProbeConfig

log = logging.getLogger(__name__)


@dataclass(slots=True)
class _CacheEntry:
    ok: bool
    expires_at: float


@dataclass(slots=True)
class DnsProber:
    """Verify that a domain actually resolves.

    Used to strip filter rules for domains that no longer exist.
    """

    config: DnsProbeConfig
    _resolvers: list[aiodns.DNSResolver] = field(default_factory=list, init=False)
    _resolver_cycle: object = field(default=None, init=False)
    _cache: OrderedDict[str, _CacheEntry] = field(default_factory=OrderedDict, init=False)
    _max_cache_size: int = 50_000
    _cache_lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)
    _total_queries: int = 0
    _cache_hits: int = 0

    def __post_init__(self) -> None:
        num = min(4, os.cpu_count() or 1)
        servers = [p.host for p in self.config.provider] or None
        timeout = self.config.timeout_seconds
        self._resolvers = [
            aiodns.DNSResolver(nameservers=servers, timeout=timeout, tries=2)
            for _ in range(num)
        ]
        self._resolver_cycle = cycle(self._resolvers)
        log.info("dns prober ready: %d resolvers, %d servers", num, len(servers or []))

    async def lookup(self, domain: str) -> bool:
        """Return True if the domain resolves (A or AAAA), False otherwise."""
        if not domain:
            return True
        key = domain.lower().strip()
        now = time.monotonic()

        # cache
        async with self._cache_lock:
            entry = self._cache.get(key)
            if entry and entry.expires_at > now:
                self._cache.move_to_end(key)
                self._cache_hits += 1
                return entry.ok

        self._total_queries += 1
        resolver = next(self._resolver_cycle)  # type: ignore[arg-type]
        ok = await self._resolve_one(resolver, key)

        ttl = self.config.cache_ttl_max_seconds if ok else self.config.cache_negative_ttl_seconds
        expires = now + max(self.config.cache_ttl_min_seconds, ttl)
        async with self._cache_lock:
            self._cache[key] = _CacheEntry(ok=ok, expires_at=expires)
            self._cache.move_to_end(key)
            while len(self._cache) > self._max_cache_size:
                self._cache.popitem(last=False)
        return ok

    async def _resolve_one(self, resolver: aiodns.DNSResolver, domain: str) -> bool:
        for rr in ("A", "AAAA"):
            try:
                result = await resolver.query(domain, rr)
                if result:
                    return True
            except aiodns.error.DNSError as e:
                code = e.args[0] if e.args else None
                if code in (aiodns.error.ARES_ENOTFOUND, aiodns.error.ARES_ENODATA):
                    continue
                log.debug("dns probe %s %s failed: %s", domain, rr, e)
                # transient failure → assume exists to avoid over-pruning
                return True
        return False

    def stats(self) -> dict[str, int]:
        return {
            "total_queries": self._total_queries,
            "cache_hits": self._cache_hits,
            "cache_size": len(self._cache),
        }

    async def close(self) -> None:
        for r in self._resolvers:
            r.cancel()
