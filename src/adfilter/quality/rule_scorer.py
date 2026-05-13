"""Rule scorer — assigns quality scores to individual rules.

Scoring criteria:
- Source reputation (how many lists include the rule)
- Age/stability (how long the rule has been present)
- Specificity (more specific rules score higher)
- False positive risk (popular domain proximity lowers score)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

log = logging.getLogger(__name__)


@dataclass
class ScoredRule:
    """A rule with an attached quality score."""

    domain: str
    score: float  # 0.0 to 1.0
    factors: dict[str, float] = field(default_factory=dict)
    sources: list[str] = field(default_factory=list)


class RuleScorer:
    """Score rules based on multiple quality factors.

    Higher scores indicate higher confidence that the rule is
    legitimate and should be kept.
    """

    def __init__(
        self,
        *,
        source_weight: float = 0.4,
        specificity_weight: float = 0.3,
        length_weight: float = 0.15,
        label_weight: float = 0.15,
    ) -> None:
        self.source_weight = source_weight
        self.specificity_weight = specificity_weight
        self.length_weight = length_weight
        self.label_weight = label_weight
        self._scores: list[ScoredRule] = []

    def score_rules(
        self,
        domain_sources: dict[str, list[str]],
        total_sources: int = 1,
    ) -> list[ScoredRule]:
        """Score all rules based on their domain-to-source mapping.

        Args:
            domain_sources: mapping of domain -> list of sources that include it
            total_sources: total number of distinct sources
        """
        self._scores = []

        for domain, sources in domain_sources.items():
            factors: dict[str, float] = {}

            # Source reputation: how many lists include this rule
            source_score = min(len(sources) / max(total_sources, 1), 1.0)
            factors["source_reputation"] = source_score

            # Specificity: more labels = more specific = better
            labels = domain.split(".")
            specificity = min(len(labels) / 5.0, 1.0)
            factors["specificity"] = specificity

            # Length factor: very short domains are suspicious
            length_score = min(len(domain) / 20.0, 1.0)
            factors["length"] = length_score

            # Label count factor
            label_score = min(len(labels) / 4.0, 1.0)
            factors["label_count"] = label_score

            # Weighted total
            total = (
                source_score * self.source_weight
                + specificity * self.specificity_weight
                + length_score * self.length_weight
                + label_score * self.label_weight
            )

            self._scores.append(
                ScoredRule(
                    domain=domain,
                    score=round(total, 4),
                    factors=factors,
                    sources=sources,
                )
            )

        # Sort by score descending
        self._scores.sort(key=lambda s: s.score, reverse=True)
        return self._scores

    def get_low_quality(self, threshold: float = 0.3) -> list[ScoredRule]:
        """Return rules scoring below the given threshold."""
        return [s for s in self._scores if s.score < threshold]

    def get_high_quality(self, threshold: float = 0.7) -> list[ScoredRule]:
        """Return rules scoring above the given threshold."""
        return [s for s in self._scores if s.score >= threshold]

    @property
    def average_score(self) -> float:
        """Return the average score across all rules."""
        if not self._scores:
            return 0.0
        return sum(s.score for s in self._scores) / len(self._scores)

    @property
    def total_scored(self) -> int:
        return len(self._scores)
