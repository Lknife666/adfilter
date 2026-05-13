"""False positive analyzer — detects rules that may accidentally block legitimate domains.

Uses domain popularity rankings (Tranco Top-1M), known-good domain lists,
and heuristics to flag potentially dangerous rules.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel

from ..model import Control, Mode, Rule, RuleType, Scope

log = logging.getLogger(__name__)

# Well-known CDN/service suffixes that should rarely be blocked entirely
COMMON_SERVICE_SUFFIXES = frozenset({
    "cloudflare.com", "cloudfront.net", "akamaiedge.net", "akamai.net",
    "fastly.net", "googleapis.com", "gstatic.com", "googleusercontent.com",
    "amazonaws.com", "azureedge.net", "azure.com", "microsoft.com",
    "apple.com", "icloud.com", "cdn.cloudflare.net",
    "github.com", "github.io", "githubusercontent.com",
    "cloudflare-dns.com", "one.one.one.one",
})


class FalsePositiveConfig(BaseModel):
    """Configuration for false positive analysis."""
    enable: bool = False
    alert_threshold: float = 30.0
    tranco_path: str = ".cache/tranco.csv"
    tranco_max_rank: int = 100000  # Only load top 100K
    known_good_lists: list[str] = field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}


@dataclass(slots=True)
class FalsePositiveSuspect:
    """A rule suspected of causing false positives."""
    domain: str
    risk_score: float
    reasons: list[str]
    source: str = ""
    rank: int | None = None


@dataclass(slots=True)
class FalsePositiveReport:
    """Report of potential false positive rules."""
    total_analyzed: int = 0
    suspects_found: int = 0
    suspects: list[FalsePositiveSuspect] = field(default_factory=list)

    def top(self, n: int = 50) -> list[FalsePositiveSuspect]:
        return sorted(self.suspects, key=lambda s: -s.risk_score)[:n]


class FalsePositiveAnalyzer:
    """Analyzes rules for potential false positives using popularity and known-good data."""

    def __init__(self, config: FalsePositiveConfig) -> None:
        self.config = config
        self._popularity_rank: dict[str, int] = {}
        self._known_good: set[str] = set()
        self._loaded = False

    def load_data(self) -> None:
        """Load Tranco rankings and known-good lists. Call before analyze()."""
        self._load_tranco()
        self._load_known_good()
        self._loaded = True

    def analyze(self, rules: list[Rule]) -> FalsePositiveReport:
        """Analyze rules for potential false positives."""
        if not self._loaded:
            self.load_data()

        suspects: list[FalsePositiveSuspect] = []

        for rule in rules:
            if rule.mode != Mode.DENY:
                continue
            if rule.scope != Scope.DOMAIN:
                continue
            if not rule.target:
                continue

            risk_score = 0.0
            reasons: list[str] = []
            rank: int | None = None

            # 1. Domain in Tranco Top-N
            r = self._popularity_rank.get(rule.target)
            if r is not None:
                rank = r
                # Higher score for more popular domains
                risk_score += max(0, (self.config.tranco_max_rank - r) / 1000)
                reasons.append(f"Tranco rank #{r:,}")

            # 2. Domain in known-good list
            if rule.target in self._known_good:
                risk_score += 50
                reasons.append("In known-good domain list")

            # 3. Domain is subdomain of a common service
            if self._is_common_service_subdomain(rule.target):
                risk_score += 30
                reasons.append("Subdomain of common CDN/service")

            # 4. Overly broad overlay on a short domain (TLD+1)
            if Control.OVERLAY in rule.controls and rule.target.count(".") == 1:
                risk_score += 20
                reasons.append("Broad overlay on 2nd-level domain (affects all subdomains)")

            # 5. Rule type is wildcard on short pattern
            if rule.type == RuleType.WILDCARD and len(rule.target) < 8:
                risk_score += 15
                reasons.append("Short wildcard pattern (high collision risk)")

            if risk_score >= self.config.alert_threshold:
                suspects.append(FalsePositiveSuspect(
                    domain=rule.target,
                    risk_score=risk_score,
                    reasons=reasons,
                    source=rule.source_name,
                    rank=rank,
                ))

        report = FalsePositiveReport(
            total_analyzed=len(rules),
            suspects_found=len(suspects),
            suspects=suspects,
        )

        log.info("false positive analyzer: %d suspects from %d rules (threshold=%.0f)",
                 len(suspects), len(rules), self.config.alert_threshold)
        return report

    def _is_common_service_subdomain(self, domain: str) -> bool:
        """Check if domain is a subdomain of a known CDN/service."""
        parts = domain.split(".")
        for i in range(1, len(parts)):
            parent = ".".join(parts[i:])
            if parent in COMMON_SERVICE_SUFFIXES:
                return True
        return False

    def _load_tranco(self) -> None:
        """Load Tranco Top-1M CSV (rank,domain format)."""
        path = Path(self.config.tranco_path)
        if not path.exists():
            log.info("Tranco file not found at %s, skipping popularity check", path)
            return

        try:
            count = 0
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split(",", 1)
                    if len(parts) == 2:
                        try:
                            rank = int(parts[0])
                            domain = parts[1].strip().lower()
                            if rank <= self.config.tranco_max_rank:
                                self._popularity_rank[domain] = rank
                                count += 1
                        except ValueError:
                            continue
            log.info("Loaded %d domains from Tranco list", count)
        except OSError as e:
            log.warning("Failed to load Tranco list: %s", e)

    def _load_known_good(self) -> None:
        """Load known-good domain lists (local files or URLs)."""
        for list_path in self.config.known_good_lists:
            path = Path(list_path)
            if not path.exists():
                log.debug("Known-good list not found: %s", list_path)
                continue
            try:
                for line in path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        self._known_good.add(line.lower())
                log.info("Loaded %d known-good domains from %s", len(self._known_good), list_path)
            except OSError as e:
                log.warning("Failed to load known-good list %s: %s", list_path, e)
