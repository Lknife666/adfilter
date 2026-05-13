"""False positive analyzer — detects rules that may block legitimate domains.

Uses heuristics and known-good domain lists to identify potential
false positives in the rule set.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

log = logging.getLogger(__name__)

# Top domains that should almost never be blocked
DEFAULT_POPULAR_DOMAINS = frozenset({
    "google.com",
    "youtube.com",
    "facebook.com",
    "twitter.com",
    "github.com",
    "microsoft.com",
    "apple.com",
    "amazon.com",
    "wikipedia.org",
    "reddit.com",
    "linkedin.com",
    "stackoverflow.com",
    "cloudflare.com",
    "netflix.com",
    "spotify.com",
})


@dataclass
class FalsePositiveHit:
    """A rule flagged as a potential false positive."""

    domain: str
    reason: str
    confidence: float  # 0.0 to 1.0
    source: str = ""


class FalsePositiveAnalyzer:
    """Analyze rules for potential false positives.

    Checks against popular domains, short domains, and patterns
    that commonly cause over-blocking.
    """

    def __init__(
        self,
        *,
        popular_domains: frozenset[str] | None = None,
        min_domain_length: int = 4,
        max_label_count: int = 2,
    ) -> None:
        self.popular_domains = popular_domains or DEFAULT_POPULAR_DOMAINS
        self.min_domain_length = min_domain_length
        self.max_label_count = max_label_count
        self._hits: list[FalsePositiveHit] = []

    def analyze(
        self, domains: list[str], source_name: str = ""
    ) -> list[FalsePositiveHit]:
        """Analyze a list of blocked domains for potential false positives."""
        self._hits = []

        for domain in domains:
            # Check popular domain match
            if self._is_popular(domain):
                self._hits.append(
                    FalsePositiveHit(
                        domain=domain,
                        reason="matches popular domain",
                        confidence=0.9,
                        source=source_name,
                    )
                )
                continue

            # Check suspiciously short domains
            if len(domain) < self.min_domain_length:
                self._hits.append(
                    FalsePositiveHit(
                        domain=domain,
                        reason="suspiciously short domain",
                        confidence=0.6,
                        source=source_name,
                    )
                )
                continue

            # Check if domain has too few labels (e.g., blocking a TLD)
            labels = domain.split(".")
            if len(labels) <= self.max_label_count and len(labels[0]) <= 3:
                self._hits.append(
                    FalsePositiveHit(
                        domain=domain,
                        reason="very short base domain, may over-block",
                        confidence=0.5,
                        source=source_name,
                    )
                )

        return self._hits

    def _is_popular(self, domain: str) -> bool:
        """Check if domain matches or is a parent of a popular domain."""
        if domain in self.popular_domains:
            return True
        # Check if this is blocking a parent of a popular domain
        for popular in self.popular_domains:
            if popular.endswith(f".{domain}"):
                return True
        return False

    @property
    def high_confidence_hits(self) -> list[FalsePositiveHit]:
        """Return only hits with confidence >= 0.8."""
        return [h for h in self._hits if h.confidence >= 0.8]

    @property
    def hit_count(self) -> int:
        return len(self._hits)
