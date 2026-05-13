"""Dead domain detector — async batch DNS probing with caching and consecutive failure tracking.

Detects domains that no longer resolve (expired, cancelled, sinkholed) and
reports them for removal or flagging. Uses conservative thresholds to avoid
false positives from transient DNS failures.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from pydantic import BaseModel

log = logging.getLogger(__name__)

# Well-known sinkhole IPs that indicate a domain is "dead" even if it resolves
SINKHOLE_IPS = frozenset({
    "0.0.0.0", "127.0.0.1", "::1",
    "0.0.0.0",
    # Common sinkhole services
    "192.0.2.1", "198.51.100.1", "203.0.113.1",  # RFC 5737 documentation
})


class DeadDomainConfig(BaseModel):
    """Configuration for dead domain detection."""
    enable: bool = False
    concurrency: int = 100
    timeout_seconds: float = 3.0
    cache_dir: str = ".cache/dns_probe"
    cache_ttl_hours: int = 168  # 7 days
    min_consecutive_failures: int = 3
    auto_remove: bool = False
    report_path: str = "rule/dead-domains.json"
    nameservers: list[str] = field(default_factory=lambda: ["8.8.8.8", "1.1.1.1", "223.5.5.5"])

    model_config = {"arbitrary_types_allowed": True}


@dataclass(slots=True)
class DeadDomainReport:
    """Report of dead domain detection results."""
    scan_date: str = ""
    total_rules: int = 0
    total_checked: int = 0
    dead_count: int = 0
    dead_ratio: str = "0%"
    dead_domains: list[str] = field(default_factory=list)
    top_dead_sources: list[dict[str, object]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")


class DiskCache:
    """Simple JSON-file-based DNS probe result cache."""

    def __init__(self, cache_dir: str, ttl_hours: int = 168) -> None:
        self._dir = Path(cache_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._ttl_seconds = ttl_hours * 3600
        self._data: dict[str, tuple[bool, float]] = {}
        self._load()

    def get(self, domain: str) -> bool | None:
        """Return cached alive status, or None if not cached/expired."""
        entry = self._data.get(domain)
        if entry is None:
            return None
        alive, timestamp = entry
        if time.time() - timestamp > self._ttl_seconds:
            del self._data[domain]
            return None
        return alive

    def set(self, domain: str, alive: bool) -> None:
        self._data[domain] = (alive, time.time())

    def save(self) -> None:
        """Persist cache to disk."""
        cache_file = self._dir / "dns_cache.json"
        try:
            # Only save recent entries
            cutoff = time.time() - self._ttl_seconds
            valid = {k: v for k, v in self._data.items() if v[1] > cutoff}
            cache_file.write_text(
                json.dumps(valid, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as e:
            log.warning("dns cache save failed: %s", e)

    def _load(self) -> None:
        cache_file = self._dir / "dns_cache.json"
        if not cache_file.exists():
            return
        try:
            raw = json.loads(cache_file.read_text(encoding="utf-8"))
            cutoff = time.time() - self._ttl_seconds
            self._data = {k: tuple(v) for k, v in raw.items() if v[1] > cutoff}
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            log.warning("dns cache corrupted, starting fresh")
            self._data = {}


class DeadDomainDetector:
    """Async batch DNS probe for detecting dead domains."""

    def __init__(self, config: DeadDomainConfig) -> None:
        self.config = config
        self._cache = DiskCache(config.cache_dir, config.cache_ttl_hours)
        self._semaphore = asyncio.Semaphore(config.concurrency)
        # Track consecutive failures across runs
        self._failure_tracker = self._load_failure_tracker()

    async def detect_batch(self, domains: list[str], source_map: dict[str, str] | None = None) -> DeadDomainReport:
        """Probe a batch of domains and return a report.

        Args:
            domains: List of domains to check
            source_map: Optional mapping of domain → source name for reporting
        """
        from datetime import UTC, datetime

        total = len(domains)
        log.info("dead domain detector: checking %d domains (concurrency=%d)", total, self.config.concurrency)

        tasks = [self._check_one(d) for d in domains]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        dead: list[str] = []
        for domain, result in zip(domains, results):
            if isinstance(result, Exception):
                # Treat exceptions as probe failure
                self._record_failure(domain)
                if self._is_confirmed_dead(domain):
                    dead.append(domain)
            elif result is False:
                self._record_failure(domain)
                if self._is_confirmed_dead(domain):
                    dead.append(domain)
            else:
                # Domain is alive, reset failure counter
                self._failure_tracker.pop(domain, None)

        # Build source breakdown
        top_dead_sources: list[dict[str, object]] = []
        if source_map:
            source_dead_count: dict[str, int] = {}
            source_total_count: dict[str, int] = {}
            for d in domains:
                src = source_map.get(d, "unknown")
                source_total_count[src] = source_total_count.get(src, 0) + 1
            for d in dead:
                src = source_map.get(d, "unknown")
                source_dead_count[src] = source_dead_count.get(src, 0) + 1

            for src, count in sorted(source_dead_count.items(), key=lambda x: -x[1])[:10]:
                total_in_src = source_total_count.get(src, 1)
                top_dead_sources.append({
                    "source": src,
                    "dead_count": count,
                    "dead_ratio": f"{count / total_in_src:.1%}",
                })

        # Save state
        self._cache.save()
        self._save_failure_tracker()

        dead_ratio = f"{len(dead) / max(total, 1):.2%}"
        report = DeadDomainReport(
            scan_date=datetime.now(tz=UTC).isoformat(),
            total_rules=total,
            total_checked=total,
            dead_count=len(dead),
            dead_ratio=dead_ratio,
            dead_domains=dead,
            top_dead_sources=top_dead_sources,
        )

        log.info("dead domain detector: %d/%d dead (%.1f%%)", len(dead), total, len(dead) / max(total, 1) * 100)
        return report

    async def _check_one(self, domain: str) -> bool:
        """Check if a single domain is alive. Returns True if alive."""
        # Check cache first
        cached = self._cache.get(domain)
        if cached is not None:
            return cached

        async with self._semaphore:
            alive = await self._resolve(domain)
            self._cache.set(domain, alive)
            return alive

    async def _resolve(self, domain: str) -> bool:
        """Attempt DNS resolution. Returns True if domain has valid records."""
        import aiodns

        resolver = aiodns.DNSResolver(
            nameservers=self.config.nameservers,
            timeout=self.config.timeout_seconds,
        )

        for qtype in ("A", "AAAA", "CNAME"):
            try:
                result = await asyncio.wait_for(
                    resolver.query(domain, qtype),
                    timeout=self.config.timeout_seconds + 1,
                )
                # Check for sinkhole IPs
                if qtype == "A" and result:
                    ip = result[0].host if hasattr(result[0], "host") else str(result[0])
                    if ip in SINKHOLE_IPS:
                        return False
                return True
            except (aiodns.error.DNSError, asyncio.TimeoutError, OSError):
                continue
            except Exception:  # noqa: BLE001
                continue

        return False

    def _record_failure(self, domain: str) -> None:
        self._failure_tracker[domain] = self._failure_tracker.get(domain, 0) + 1

    def _is_confirmed_dead(self, domain: str) -> bool:
        """A domain is confirmed dead only after N consecutive failures."""
        return self._failure_tracker.get(domain, 0) >= self.config.min_consecutive_failures

    def _load_failure_tracker(self) -> dict[str, int]:
        tracker_path = Path(self.config.cache_dir) / "failure_tracker.json"
        if tracker_path.exists():
            try:
                return json.loads(tracker_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def _save_failure_tracker(self) -> None:
        tracker_path = Path(self.config.cache_dir) / "failure_tracker.json"
        try:
            tracker_path.parent.mkdir(parents=True, exist_ok=True)
            tracker_path.write_text(
                json.dumps(self._failure_tracker, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as e:
            log.warning("failure tracker save failed: %s", e)
