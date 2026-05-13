"""Rule scoring system — assigns quality scores to individual rules.

Dimensions:
- Multi-source confirmation (30%): rules appearing in multiple independent sources
- Domain freshness (25%): domain is alive (DNS resolves)
- Specificity (20%): exact domain match preferred over wildcards
- No conflict (15%): rule doesn't conflict with other rules
- Not overbroad (10%): rule doesn't affect too many subdomains

The score helps users understand rule quality and enables "quality threshold"
filtering for generating lean, high-confidence rule sets.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field

from ..model import Control, Mode, Rule, RuleType, Scope

log = logging.getLogger(__name__)


@dataclass(slots=True)
class RuleScore:
    """Quality score for a single rule."""
    domain: str
    total_score: float = 0.0
    components: dict[str, float] = field(default_factory=dict)
    grade: str = ""  # A/B/C/D/F

    def __post_init__(self) -> None:
        if self.total_score >= 80:
            self.grade = "A"
        elif self.total_score >= 60:
            self.grade = "B"
        elif self.total_score >= 40:
            self.grade = "C"
        elif self.total_score >= 20:
            self.grade = "D"
        else:
            self.grade = "F"


@dataclass(slots=True)
class ScoreSummary:
    """Aggregate scoring summary for a rule set."""
    total_rules: int = 0
    average_score: float = 0.0
    grade_distribution: dict[str, int] = field(default_factory=dict)
    source_averages: dict[str, float] = field(default_factory=dict)


class RuleScorer:
    """Computes quality scores for rules based on multiple dimensions."""

    # Dimension weights (must sum to 1.0)
    WEIGHT_MULTI_SOURCE = 0.30
    WEIGHT_FRESHNESS = 0.25
    WEIGHT_SPECIFICITY = 0.20
    WEIGHT_NO_CONFLICT = 0.15
    WEIGHT_NOT_OVERBROAD = 0.10

    def __init__(
        self,
        source_counts: dict[str, set[str]] | None = None,
        alive_domains: set[str] | None = None,
        conflict_domains: set[str] | None = None,
    ) -> None:
        """
        Args:
            source_counts: domain → set of source names that contain it
            alive_domains: set of domains confirmed alive by DNS probe
            conflict_domains: set of domains involved in conflicts
        """
        self._source_counts = source_counts or {}
        self._alive_domains = alive_domains or set()
        self._conflict_domains = conflict_domains or set()

    def score(self, rule: Rule) -> RuleScore:
        """Compute the quality score for a single rule."""
        if not rule.target or rule.mode != Mode.DENY or rule.scope != Scope.DOMAIN:
            return RuleScore(domain=rule.target or "", total_score=0.0)

        components: dict[str, float] = {
            "multi_source": self._score_multi_source(rule),
            "freshness": self._score_freshness(rule),
            "specificity": self._score_specificity(rule),
            "no_conflict": self._score_no_conflict(rule),
            "not_overbroad": self._score_not_overbroad(rule),
        }

        total = (
            components["multi_source"] * self.WEIGHT_MULTI_SOURCE
            + components["freshness"] * self.WEIGHT_FRESHNESS
            + components["specificity"] * self.WEIGHT_SPECIFICITY
            + components["no_conflict"] * self.WEIGHT_NO_CONFLICT
            + components["not_overbroad"] * self.WEIGHT_NOT_OVERBROAD
        )

        return RuleScore(domain=rule.target, total_score=total, components=components)

    def score_batch(self, rules: list[Rule]) -> ScoreSummary:
        """Score all rules and return aggregate summary."""
        scores: list[RuleScore] = []
        source_totals: dict[str, list[float]] = defaultdict(list)
        grade_dist: dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}

        for rule in rules:
            if rule.mode != Mode.DENY or rule.scope != Scope.DOMAIN:
                continue
            s = self.score(rule)
            scores.append(s)
            grade_dist[s.grade] = grade_dist.get(s.grade, 0) + 1
            if rule.source_name:
                source_totals[rule.source_name].append(s.total_score)

        avg = sum(s.total_score for s in scores) / max(len(scores), 1)
        source_avgs = {src: sum(vals) / len(vals) for src, vals in source_totals.items()}

        return ScoreSummary(
            total_rules=len(scores),
            average_score=round(avg, 1),
            grade_distribution=grade_dist,
            source_averages={k: round(v, 1) for k, v in source_avgs.items()},
        )

    def _score_multi_source(self, rule: Rule) -> float:
        """Score based on how many independent sources contain this rule. Max 100."""
        sources = self._source_counts.get(rule.target, set())
        count = len(sources)
        if count >= 4:
            return 100.0
        if count == 3:
            return 80.0
        if count == 2:
            return 50.0
        return 20.0  # Only one source

    def _score_freshness(self, rule: Rule) -> float:
        """Score based on whether the domain is confirmed alive. Max 100."""
        if not self._alive_domains:
            return 50.0  # No data, neutral score
        if rule.target in self._alive_domains:
            return 100.0
        return 0.0  # Not confirmed alive (possibly dead)

    def _score_specificity(self, rule: Rule) -> float:
        """Score based on rule precision. Max 100."""
        if rule.type == RuleType.BASIC:
            return 100.0
        if rule.type == RuleType.WILDCARD:
            return 50.0
        if rule.type == RuleType.REGEX:
            return 30.0
        return 10.0  # UNKNOWN

    def _score_no_conflict(self, rule: Rule) -> float:
        """Score based on absence of conflicts. Max 100."""
        if rule.target in self._conflict_domains:
            return 0.0
        return 100.0

    def _score_not_overbroad(self, rule: Rule) -> float:
        """Score based on how specific the rule is (not too broad). Max 100."""
        if not rule.target:
            return 0.0

        dot_count = rule.target.count(".")
        has_overlay = Control.OVERLAY in rule.controls

        # Overlay on TLD+1 (e.g., "example.com" blocking all subdomains) — risky
        if has_overlay and dot_count == 1:
            return 30.0
        # Overlay on TLD+2 — less risky
        if has_overlay and dot_count == 2:
            return 70.0
        # Deep subdomain or no overlay — very specific
        if dot_count >= 2 or not has_overlay:
            return 100.0

        return 50.0
