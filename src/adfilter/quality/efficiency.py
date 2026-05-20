"""Rule efficiency metrics — measures how lean and effective a rule set is.

Tracks live/dead domain ratios and redundancy to quantify bloat.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EfficiencyMetrics:
    """Efficiency metrics for a rule set."""

    total_rules: int = 0
    live_domains: int = 0
    dead_domains: int = 0
    redundant_rules: int = 0
    unique_rules: int = 0

    @property
    def liveness_rate(self) -> float:
        """Fraction of rules targeting still-alive domains."""
        if self.total_rules == 0:
            return 0.0
        return self.live_domains / self.total_rules

    @property
    def efficiency_score(self) -> float:
        """Fraction of rules that are effective (live and non-redundant)."""
        if self.total_rules == 0:
            return 0.0
        effective = self.live_domains - self.redundant_rules
        return max(0.0, effective / self.total_rules)

    @property
    def bloat_ratio(self) -> float:
        """Fraction of rules that are dead or redundant."""
        if self.total_rules == 0:
            return 0.0
        return (self.dead_domains + self.redundant_rules) / self.total_rules

    @property
    def grade(self) -> str:
        """Letter grade based on efficiency score."""
        score = self.efficiency_score
        if score >= 0.90:
            return "Excellent"
        if score >= 0.75:
            return "Good"
        if score >= 0.60:
            return "Fair"
        if score >= 0.40:
            return "Poor"
        return "Critical"

    def to_dict(self) -> dict:
        return {
            "total_rules": self.total_rules,
            "live_domains": self.live_domains,
            "dead_domains": self.dead_domains,
            "redundant_rules": self.redundant_rules,
            "unique_rules": self.unique_rules,
            "liveness_rate": round(self.liveness_rate, 4),
            "efficiency_score": round(self.efficiency_score, 4),
            "bloat_ratio": round(self.bloat_ratio, 4),
            "grade": self.grade,
        }
