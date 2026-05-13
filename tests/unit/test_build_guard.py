"""Tests for BuildGuard."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from adfilter.build_guard import BuildGuard, SourceStatus


@pytest.fixture
def state_file(tmp_path: Path) -> Path:
    return tmp_path / "guard-state.json"


@pytest.fixture
def guard(state_file: Path) -> BuildGuard:
    return BuildGuard(
        drop_threshold=0.3,
        min_rules=100,
        max_source_failures=0.5,
        state_file=state_file,
    )


class TestBuildGuardMinimumThreshold:
    def test_passes_above_minimum(self, guard: BuildGuard):
        result = guard.check(500)
        assert result.passed is True
        assert not result.errors

    def test_fails_below_minimum(self, guard: BuildGuard):
        result = guard.check(50)
        assert result.passed is False
        assert any("below minimum" in e for e in result.errors)

    def test_fails_at_zero(self, guard: BuildGuard):
        result = guard.check(0)
        assert result.passed is False


class TestBuildGuardDropDetection:
    def test_detects_large_drop(self, state_file: Path):
        # Seed previous state
        state_file.write_text(json.dumps({"total_rules": 1000}))
        guard = BuildGuard(
            drop_threshold=0.3, min_rules=100, state_file=state_file
        )
        result = guard.check(500)  # 50% drop
        assert result.passed is False
        assert any("dropped" in e.lower() for e in result.errors)

    def test_no_drop_passes(self, state_file: Path):
        state_file.write_text(json.dumps({"total_rules": 1000}))
        guard = BuildGuard(
            drop_threshold=0.3, min_rules=100, state_file=state_file
        )
        result = guard.check(950)
        assert result.passed is True

    def test_small_drop_warns(self, state_file: Path):
        state_file.write_text(json.dumps({"total_rules": 1000}))
        guard = BuildGuard(
            drop_threshold=0.3, min_rules=100, state_file=state_file
        )
        result = guard.check(820)  # 18% drop (above 15% warning threshold)
        assert result.passed is True
        assert len(result.warnings) > 0

    def test_no_previous_state_passes(self, guard: BuildGuard):
        result = guard.check(500)
        assert result.passed is True


class TestBuildGuardSourceFailures:
    def test_passes_with_no_failures(self, guard: BuildGuard):
        sources = [
            SourceStatus(name="s1", success=True, rule_count=100),
            SourceStatus(name="s2", success=True, rule_count=200),
        ]
        result = guard.check(300, sources)
        assert result.passed is True

    def test_fails_with_too_many_failures(self, guard: BuildGuard):
        sources = [
            SourceStatus(name="s1", success=False, error="timeout"),
            SourceStatus(name="s2", success=False, error="404"),
            SourceStatus(name="s3", success=True, rule_count=100),
        ]
        result = guard.check(500, sources)  # 66% failure rate
        assert result.passed is False
        assert any("sources failed" in e for e in result.errors)

    def test_warns_on_partial_failures(self, guard: BuildGuard):
        sources = [
            SourceStatus(name="s1", success=False, error="timeout"),
            SourceStatus(name="s2", success=True, rule_count=200),
            SourceStatus(name="s3", success=True, rule_count=300),
        ]
        result = guard.check(500, sources)
        assert result.passed is True
        assert any("Failed sources" in w for w in result.warnings)


class TestBuildGuardStatePersistence:
    def test_saves_state_on_success(self, guard: BuildGuard, state_file: Path):
        guard.check(500)
        assert state_file.exists()
        state = json.loads(state_file.read_text())
        assert state["total_rules"] == 500

    def test_does_not_save_on_failure(self, guard: BuildGuard, state_file: Path):
        guard.check(50)  # below minimum
        assert not state_file.exists()

    def test_get_previous_count(self, state_file: Path):
        state_file.write_text(json.dumps({"total_rules": 777}))
        guard = BuildGuard(state_file=state_file, min_rules=0)
        assert guard.get_previous_count() == 777
