"""Core pipeline: fetch → parse → filter → dedupe → emit."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from .config import FetcherConfig, InputItem, ParserConfig
from .dns_prober import DnsProber
from .fetcher import get_fetcher
from .fetcher.factory import detect_handle_type
from .handler import get_handler
from .model import Rule, RuleType, Scope
from .optimizer import normalize_idn

log = logging.getLogger(__name__)


@dataclass(slots=True)
class SourceStats:
    name: str = ""
    total: int = 0
    invalid: int = 0
    repeat: int = 0
    dead: int = 0
    effective: int = 0
    elapsed_ms: int = 0


@dataclass(slots=True)
class Parser:
    fetcher_config: FetcherConfig
    parser_config: ParserConfig
    prober: DnsProber | None = None
    normalize_idn: bool = True
    on_source_done: object | None = None  # callback(SourceStats) for progress UI
    _seen_hashes: set[int] = field(default_factory=set)
    _seen_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def handle(self, item: InputItem) -> AsyncIterator[Rule]:
        """Stream valid, de-duplicated rules from one input source."""
        stats = SourceStats(name=item.name)
        started = time.monotonic()

        handler = get_handler(item.type)
        handle_type = detect_handle_type(item.path)
        fetcher = get_fetcher(handle_type, self.fetcher_config)

        async for line in fetcher.fetch(item.path):
            if not line or line.isspace():
                continue
            if handler.is_comment(line):
                log.debug("[%s] comment: %s", item.name, line)
                continue

            n = len(line)
            if self.parser_config.min_length > 0 and n < self.parser_config.min_length:
                continue
            if self.parser_config.max_length > 0 and n > self.parser_config.max_length:
                continue

            try:
                rule = handler.parse(line)
            except Exception as e:  # noqa: BLE001
                log.warning("[%s] parse error on %r: %s", item.name, line, e)
                continue

            stats.total += 1
            if rule.is_empty():
                stats.invalid += 1
                continue

            rule.source_name = item.name
            if self.normalize_idn and rule.target:
                rule.target = normalize_idn(rule.target)

            if rule.target and rule.target in self.parser_config.excludes:
                log.debug("[%s] excluded: %s", item.name, rule.origin)
                continue
            if self.parser_config.alert_length > 0 and len(rule.origin) <= self.parser_config.alert_length:
                log.warning("[%s] suspicious short rule: %s", item.name, rule.origin)

            # dedupe by murmur3
            h = rule.murmur3_hash()
            async with self._seen_lock:
                if h in self._seen_hashes:
                    stats.repeat += 1
                    continue
                self._seen_hashes.add(h)

            # optional DNS probe — failures are tracked separately as
            # "dead" (domain does not resolve) rather than "invalid"
            # (could not parse), so the build report can distinguish.
            if self.prober is not None and rule.type is RuleType.BASIC and rule.scope is Scope.DOMAIN:
                exists = await self.prober.lookup(rule.target)
                if not exists:
                    stats.dead += 1
                    continue

            stats.effective += 1
            yield rule

        stats.elapsed_ms = int((time.monotonic() - started) * 1000)
        log.info(
            "[%s] done: total=%d effective=%d invalid=%d repeat=%d dead=%d in %dms",
            item.name,
            stats.total,
            stats.effective,
            stats.invalid,
            stats.repeat,
            stats.dead,
            stats.elapsed_ms,
        )
        if self.on_source_done:
            try:
                self.on_source_done(stats)  # type: ignore[misc]
            except Exception:  # noqa: BLE001
                pass
