"""HTTP fetcher — streaming, line-buffered, with conditional-GET cache and fallback."""

from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import json
import logging
import socket
import time
from collections.abc import AsyncIterator
from pathlib import Path
from urllib.parse import urlparse

import aiohttp

from ..config import HttpFetcherConfig
from .base import Fetcher

log = logging.getLogger(__name__)

_CHUNK = 16 * 1024

# ── SSRF protection: block requests to private/reserved IP ranges ──
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),   # link-local
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("::1/128"),           # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),          # IPv6 unique local
    ipaddress.ip_network("fe80::/10"),         # IPv6 link-local
]


class SSRFError(Exception):
    """Raised when a URL resolves to a private/reserved IP address."""

    def __init__(self, url: str, ip: str) -> None:
        self.url = url
        self.ip = ip
        super().__init__(f"SSRF blocked: {url} resolves to private address {ip}")


def _check_ssrf(url: str) -> None:
    """Resolve the hostname and reject private/reserved IPs to prevent SSRF attacks."""
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        raise SSRFError(url, "<no host>")

    try:
        addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror:
        # Cannot resolve — let aiohttp handle the DNS error naturally
        return

    for _family, _type, _proto, _canonname, sockaddr in addr_info:
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        for network in _BLOCKED_NETWORKS:
            if ip in network:
                raise SSRFError(url, ip_str)



def _cache_key(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


class FetchError(Exception):
    """Raised when fetch fails and fallback is exhausted."""

    def __init__(self, url: str, cause: Exception, used_cache: bool = False) -> None:
        self.url = url
        self.cause = cause
        self.used_cache = used_cache
        super().__init__(f"fetch failed for {url}: {cause}")


class HttpFetcher(Fetcher):
    """Async HTTP fetcher.

    Feature #11 — optional on-disk cache with conditional GET.
    v0.2 — error fallback: on_failure = fail_fast | cache_then_skip | skip_always
    """

    def __init__(self, config: HttpFetcherConfig) -> None:
        self._config = config
        self._cache_dir: Path | None = None
        if config.cache_dir:
            self._cache_dir = Path(config.cache_dir).expanduser()
            self._cache_dir.mkdir(parents=True, exist_ok=True)

    # ── public ──────────────────────────────────────────────────────
    async def fetch(self, path: str) -> AsyncIterator[str]:
        # SSRF guard: reject URLs that resolve to private/reserved IPs
        try:
            _check_ssrf(path)
        except SSRFError as e:
            log.error("SSRF protection blocked request: %s", e)
            return

        timeout = aiohttp.ClientTimeout(total=self._config.timeout_seconds)
        base_headers = {"User-Agent": self._config.user_agent, **self._config.headers}

        cached_body: str | None = None
        conditional_headers: dict[str, str] = {}
        meta_path, body_path = self._cache_paths(path)
        if meta_path and body_path and meta_path.exists() and body_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                if etag := meta.get("etag"):
                    conditional_headers["If-None-Match"] = etag
                if last_modified := meta.get("last_modified"):
                    conditional_headers["If-Modified-Since"] = last_modified
                cached_body = body_path.read_text(encoding=self._config.encoding, errors="replace")
            except (OSError, json.JSONDecodeError) as e:
                log.debug("cache read failed for %s: %s", path, e)

        attempt = 0
        last_error: Exception | None = None
        while True:
            try:
                headers = {**base_headers, **conditional_headers}
                async for line in self._stream(path, timeout, headers, cached_body):
                    yield line
                return
            except (TimeoutError, aiohttp.ClientError) as e:
                last_error = e
                attempt += 1
                if attempt > self._config.max_retries:
                    break
                backoff = min(2**attempt, 30)
                log.warning("fetch %s failed (attempt %d): %s, retrying in %ds",
                            path, attempt, e, backoff)
                await asyncio.sleep(backoff)

        # ── fallback logic ──────────────────────────────────────────
        assert last_error is not None
        strategy = self._config.on_failure

        if strategy == "fail_fast":
            log.error("fetch %s failed after %d retries (fail_fast): %s",
                      path, attempt, last_error)
            raise FetchError(path, last_error)

        if strategy in ("cache_then_skip", "skip_always"):
            # Try stale cache first (unless skip_always)
            if strategy == "cache_then_skip" and cached_body is not None:
                cache_age = self._cache_age_hours(meta_path)
                if cache_age <= self._config.max_cache_age_hours:
                    log.warning(
                        "fetch %s failed, using cached version (%.1fh old): %s",
                        path, cache_age, last_error,
                    )
                    for ln in cached_body.splitlines():
                        yield ln
                    return
                log.warning(
                    "fetch %s failed, cache too old (%.1fh > %dh limit), skipping: %s",
                    path, cache_age, self._config.max_cache_age_hours, last_error,
                )
            else:
                log.warning("fetch %s failed, no cache available, skipping: %s",
                            path, last_error)
            # Skip: yield nothing (empty source)
            return

        # Unknown strategy → fail
        log.error("fetch %s failed (unknown strategy %r): %s", path, strategy, last_error)
        raise FetchError(path, last_error)

    def _cache_age_hours(self, meta_path: Path | None) -> float:
        """Return cache age in hours, or infinity if unknown."""
        if meta_path is None or not meta_path.exists():
            return float("inf")
        try:
            mtime = meta_path.stat().st_mtime
            return (time.time() - mtime) / 3600
        except OSError:
            return float("inf")

    # ── internals ───────────────────────────────────────────────────
    def _cache_paths(self, url: str) -> tuple[Path | None, Path | None]:
        if self._cache_dir is None:
            return None, None
        key = _cache_key(url)
        return (self._cache_dir / f"{key}.meta.json",
                self._cache_dir / f"{key}.body")

    async def _stream(
        self,
        url: str,
        timeout: aiohttp.ClientTimeout,
        headers: dict[str, str],
        cached_body: str | None,
    ) -> AsyncIterator[str]:
        enc = self._config.encoding
        async with (
            aiohttp.ClientSession(timeout=timeout, headers=headers) as session,
            session.get(url) as resp,
        ):
            if resp.status == 304 and cached_body is not None:
                log.info("fetch %s => 304 Not Modified (using cache)", url)
                for ln in cached_body.splitlines():
                    yield ln
                return

            resp.raise_for_status()

            # capture to disk as we stream, so we can cache on success
            body_path = None
            meta_path, body_path = self._cache_paths(url)
            writer = None
            if body_path is not None:
                tmp = body_path.with_suffix(".tmp")
                writer = tmp.open("w", encoding=enc)

            try:
                buf = ""
                async for chunk in resp.content.iter_chunked(_CHUNK):
                    text = chunk.decode(enc, errors="replace")
                    if writer is not None:
                        writer.write(text)
                    buf += text
                    parts = buf.splitlines(keepends=True)
                    buf = parts.pop() if parts and not parts[-1].endswith(("\n", "\r")) else ""
                    for p in parts:
                        yield p.rstrip("\r\n")
                if buf:
                    yield buf
            finally:
                if writer is not None:
                    writer.close()

            # success → commit to cache
            if body_path is not None and meta_path is not None and writer is not None:
                tmp = body_path.with_suffix(".tmp")
                tmp.replace(body_path)
                meta: dict[str, str] = {}
                if etag := resp.headers.get("ETag"):
                    meta["etag"] = etag
                if lm := resp.headers.get("Last-Modified"):
                    meta["last_modified"] = lm
                meta_path.write_text(json.dumps(meta), encoding="utf-8")
