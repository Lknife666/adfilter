"""Rule efficiency metrics — measures how lean and effective a rule set is.

Field semantics (aligned with ``parser.py`` pipeline):

* ``total_rules``     — raw input count: effective + invalid + repeat + dead.
* ``live_domains``    — rules that made it into output (= effective).
* ``dead_domains``    — NXDOMAIN from DNS probe (0 when probe disabled).
* ``redundant_rules`` — cross-source duplicates (hash already emitted).
* ``unique_rules``    — alias for live_domains (kept for backward compat).
* ``invalid_rules``   — parse failures / empty / filtered by length.

Key formulas:
    efficiency_score = live_domains / total_rules
    liveness_rate    = live_domains / (live_domains + dead_domains)
    bloat_ratio      = (invalid_rules + redundant_rules + dead_domains) / total_rules
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EfficiencyMetrics:
    """Efficiency metrics for a rule set.

    All counts refer to the *pre-optimization* parse stage.  The
    optimizer (subdomain collapse, allow-shadow, voting) may further
    reduce the final output — that reduction is NOT reflected here.
    """

    total_rules: int = 0
    live_domains: int = 0
    dead_domains: int = 0
    redundant_rules: int = 0
    unique_rules: int = 0
    invalid_rules: int = 0

    @property
    def liveness_rate(self) -> float:
        """Fraction of *resolvable* rules among those that were probed.

        When DNS probe is disabled (dead_domains == 0), returns 1.0
        because we have no evidence of dead domains.
        """
        denominator = self.live_domains + self.dead_domains
        if denominator == 0:
            return 1.0
        return self.live_domains / denominator

    @property
    def efficiency_score(self) -> float:
        """Fraction of raw input that ended up in the final output.

        efficiency_score = effective / raw_total

        A score of 1.0 means every parsed line became an output rule
        (no duplicates, no parse failures, no dead domains).
        """
        if self.total_rules == 0:
            return 0.0
        return self.live_domains / self.total_rules

    @property
    def bloat_ratio(self) -> float:
        """Fraction of raw input that was discarded.

        bloat = (invalid + repeat + dead) / raw_total
        Equivalently: 1.0 - efficiency_score
        """
        if self.total_rules == 0:
            return 0.0
        waste = self.invalid_rules + self.redundant_rules + self.dead_domains
        return min(1.0, waste / self.total_rules)

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
            "invalid_rules": self.invalid_rules,
            "unique_rules": self.unique_rules,
            "liveness_rate": round(self.liveness_rate, 4),
            "efficiency_score": round(self.efficiency_score, 4),
            "bloat_ratio": round(self.bloat_ratio, 4),
            "grade": self.grade,
        }
