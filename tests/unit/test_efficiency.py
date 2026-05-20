"""Tests for the efficiency metrics module."""

from __future__ import annotations

from adfilter.quality.efficiency import EfficiencyMetrics


class TestEfficiencyMetrics:
    def test_empty(self):
        m = EfficiencyMetrics()
        assert m.liveness_rate == 0.0
        assert m.efficiency_score == 0.0
        assert m.bloat_ratio == 0.0

    def test_perfect(self):
        m = EfficiencyMetrics(
            total_rules=1000,
            live_domains=1000,
            dead_domains=0,
            redundant_rules=0,
            unique_rules=1000,
        )
        assert m.liveness_rate == 1.0
        assert m.efficiency_score == 1.0
        assert m.bloat_ratio == 0.0
        assert m.grade == "Excellent"

    def test_typical(self):
        m = EfficiencyMetrics(
            total_rules=10000,
            live_domains=9000,
            dead_domains=600,
            redundant_rules=400,
            unique_rules=9600,
        )
        assert abs(m.liveness_rate - 0.9) < 0.001
        assert abs(m.bloat_ratio - 0.1) < 0.001
        assert m.efficiency_score > 0.8
        assert m.grade in ("Excellent", "Good")

    def test_poor(self):
        m = EfficiencyMetrics(
            total_rules=1000,
            live_domains=300,
            dead_domains=500,
            redundant_rules=200,
            unique_rules=800,
        )
        assert m.liveness_rate == 0.3
        assert m.bloat_ratio == 0.7
        assert m.efficiency_score == 0.1
        assert m.grade == "Critical"

    def test_to_dict(self):
        m = EfficiencyMetrics(total_rules=100, live_domains=90, dead_domains=5, redundant_rules=5)
        d = m.to_dict()
        assert d["total_rules"] == 100
        assert "grade" in d
        assert "efficiency_score" in d
