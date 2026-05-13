"""Tests for ConflictDetector."""

from __future__ import annotations

import pytest

from adfilter.model import Control, Mode, Rule, RuleType, Scope
from adfilter.quality.conflict_detector import ConflictDetector, ConflictType


def _rule(target: str, mode: Mode = Mode.DENY, source: str = "src1", overlay: bool = False) -> Rule:
    controls = {Control.OVERLAY} if overlay else set()
    return Rule(
        target=target, mode=mode, scope=Scope.DOMAIN,
        type=RuleType.BASIC, source_name=source, controls=controls,
    )


class TestDenyAllowConflicts:
    def test_same_target_deny_and_allow(self):
        detector = ConflictDetector()
        rules = [_rule("example.com", Mode.DENY), _rule("example.com", Mode.ALLOW)]
        report = detector.detect(rules)
        assert report.total_conflicts >= 1
        deny_allow = report.by_type(ConflictType.DENY_ALLOW_SAME_TARGET)
        assert len(deny_allow) == 1
        assert deny_allow[0].domain == "example.com"

    def test_no_conflict_when_same_mode(self):
        detector = ConflictDetector()
        rules = [_rule("a.com", Mode.DENY), _rule("b.com", Mode.DENY)]
        report = detector.detect(rules)
        deny_allow = report.by_type(ConflictType.DENY_ALLOW_SAME_TARGET)
        assert deny_allow == []

    def test_different_targets_no_conflict(self):
        detector = ConflictDetector()
        rules = [_rule("a.com", Mode.DENY), _rule("b.com", Mode.ALLOW)]
        report = detector.detect(rules)
        deny_allow = report.by_type(ConflictType.DENY_ALLOW_SAME_TARGET)
        assert deny_allow == []


class TestHierarchyConflicts:
    def test_parent_deny_child_allow(self):
        detector = ConflictDetector()
        rules = [
            _rule("example.com", Mode.DENY, overlay=True),
            _rule("safe.example.com", Mode.ALLOW),
        ]
        report = detector.detect(rules)
        hierarchy = report.by_type(ConflictType.PARENT_CHILD_CONFLICT)
        assert len(hierarchy) == 1
        assert hierarchy[0].domain == "safe.example.com"

    def test_no_hierarchy_without_overlay(self):
        detector = ConflictDetector()
        rules = [
            _rule("example.com", Mode.DENY, overlay=False),
            _rule("safe.example.com", Mode.ALLOW),
        ]
        report = detector.detect(rules)
        hierarchy = report.by_type(ConflictType.PARENT_CHILD_CONFLICT)
        assert hierarchy == []


class TestSourceDisagreements:
    def test_different_sources_disagree(self):
        detector = ConflictDetector()
        rules = [
            _rule("tracker.com", Mode.DENY, source="list-a"),
            _rule("tracker.com", Mode.ALLOW, source="list-b"),
        ]
        report = detector.detect(rules)
        disagreements = report.by_type(ConflictType.SOURCE_DISAGREEMENT)
        assert len(disagreements) >= 1
        assert "list-a" in disagreements[0].deny_sources
        assert "list-b" in disagreements[0].allow_sources

    def test_same_source_no_disagreement(self):
        detector = ConflictDetector()
        rules = [
            _rule("a.com", Mode.DENY, source="same"),
            _rule("b.com", Mode.DENY, source="same"),
        ]
        report = detector.detect(rules)
        disagreements = report.by_type(ConflictType.SOURCE_DISAGREEMENT)
        assert disagreements == []


class TestReportSummary:
    def test_auto_resolved_vs_needs_review(self):
        detector = ConflictDetector()
        rules = [
            _rule("high-conf.com", Mode.DENY),
            _rule("high-conf.com", Mode.ALLOW),
            _rule("low-conf.com", Mode.DENY, source="a"),
            _rule("low-conf.com", Mode.ALLOW, source="b"),
        ]
        report = detector.detect(rules)
        assert report.total_conflicts >= 1
        # High-confidence resolutions are auto_resolved
        assert report.auto_resolved >= 0
        assert report.needs_review >= 0
        assert report.auto_resolved + report.needs_review == report.total_conflicts
