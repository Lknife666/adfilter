"""Tests for BuildGuard."""

from __future__ import annotations

import json

import pytest

from adfilter.build_guard import Alert, BuildGuard, BuildGuardConfig, BuildGuardState


@pytest.fixture
def guard_config():
    return BuildGuardConfig(enable=True, max_drop_ratio=0.3, min_total_rules=1000)


@pytest.fixture
def guard(guard_config, tmp_path):
    return BuildGuard(guard_config, state_dir=tmp_path)


class TestRuleCountDrop:
    def test_first_run_no_alert(self, guard):
        """First run has no baseline, so no drop alert."""
        alerts = guard.check(50000)
        # Only min_total check may fire, but 50000 > 1000
        drop_alerts = [a for a in alerts if "dropped" in a.message.lower()]
        assert drop_alerts == []

    def test_normal_increase_no_alert(self, guard):
        """Rule count going up should not alert."""
        guard.check(50000)  # establish baseline
        alerts = guard.check(60000)
        drop_alerts = [a for a in alerts if "dropped" in a.message.lower()]
        assert drop_alerts == []

    def test_small_drop_no_alert(self, guard):
        """Drop under threshold should not alert."""
        guard.check(100000)
        alerts = guard.check(80000)  # 20% drop, under 30% threshold
        drop_alerts = [a for a in alerts if "dropped" in a.message.lower()]
        assert drop_alerts == []

    def test_large_drop_warns(self, guard):
        """Drop over threshold should warn."""
        guard.check(100000)
        alerts = guard.check(50000)  # 50% drop
        drop_alerts = [a for a in alerts if "dropped" in a.message.lower()]
        assert len(drop_alerts) == 1
        assert drop_alerts[0].level == "warning"

    def test_consecutive_drops_escalate_to_critical(self, guard):
        """Multiple consecutive drops escalate to critical."""
        guard.check(100000)
        guard.check(50000)  # 1st drop
        guard.check(30000)  # 2nd drop
        alerts = guard.check(15000)  # 3rd drop
        drop_alerts = [a for a in alerts if "dropped" in a.message.lower()]
        assert len(drop_alerts) == 1
        assert drop_alerts[0].level == "critical"


class TestMinimumRules:
    def test_below_minimum_alerts(self, guard):
        alerts = guard.check(500)
        min_alerts = [a for a in alerts if "below minimum" in a.message.lower()]
        assert len(min_alerts) == 1
        assert min_alerts[0].level == "warning"

    def test_above_minimum_no_alert(self, guard):
        alerts = guard.check(5000)
        min_alerts = [a for a in alerts if "below minimum" in a.message.lower()]
        assert min_alerts == []


class TestSourceFailures:
    def test_no_failures_no_alert(self, guard):
        alerts = guard.check(50000, source_success=5, source_total=5)
        src_alerts = [a for a in alerts if "sources failed" in a.message.lower()]
        assert src_alerts == []

    def test_some_failures_info(self, guard):
        alerts = guard.check(50000, source_success=4, source_total=5)
        src_alerts = [a for a in alerts if "sources failed" in a.message.lower()]
        assert len(src_alerts) == 1
        assert src_alerts[0].level == "info"

    def test_majority_failures_critical(self, guard):
        alerts = guard.check(50000, source_success=1, source_total=5)
        src_alerts = [a for a in alerts if "sources failed" in a.message.lower()]
        assert len(src_alerts) == 1
        assert src_alerts[0].level == "critical"


class TestStateFile:
    def test_state_persists(self, guard_config, tmp_path):
        guard1 = BuildGuard(guard_config, state_dir=tmp_path)
        guard1.check(100000)

        # New guard instance reads the state
        guard2 = BuildGuard(guard_config, state_dir=tmp_path)
        alerts = guard2.check(50000)  # 50% drop from persisted state
        drop_alerts = [a for a in alerts if "dropped" in a.message.lower()]
        assert len(drop_alerts) == 1

    def test_corrupted_state_handled(self, guard_config, tmp_path):
        state_file = tmp_path / guard_config.state_file
        state_file.write_text("not valid json", encoding="utf-8")
        guard = BuildGuard(guard_config, state_dir=tmp_path)
        # Should not raise, starts fresh
        alerts = guard.check(50000)
        assert isinstance(alerts, list)


class TestDisabled:
    def test_disabled_returns_empty(self, tmp_path):
        config = BuildGuardConfig(enable=False)
        guard = BuildGuard(config, state_dir=tmp_path)
        alerts = guard.check(0, source_success=0, source_total=10)
        assert alerts == []
