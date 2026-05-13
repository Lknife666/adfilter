"""Tests for conflict detector."""

from __future__ import annotations

import pytest

from adfilter.quality.conflict_detector import ConflictDetector, RuleConflict


class TestConflictDetector:
    def test_no_conflicts(self):
        detector = ConflictDetector()
        deny = {"ads.example.com": ["source1"], "tracker.net": ["source2"]}
        conflicts = detector.detect(deny)
        assert conflicts == []
        assert detector.conflict_count == 0
        assert detector.has_conflicts is False

    def test_deny_allow_conflict(self):
        detector = ConflictDetector()
        deny = {"example.com": ["blocker1"]}
        allow = {"example.com": ["allowlist1"]}
        conflicts = detector.detect(deny, allow)
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == "deny_allow"
        assert conflicts[0].domain == "example.com"

    def test_overlap_conflict(self):
        detector = ConflictDetector()
        deny = {
            "example.com": ["source1"],
            "sub.example.com": ["source2"],
        }
        conflicts = detector.detect(deny)
        overlap_conflicts = detector.get_conflicts_by_type("overlap")
        assert len(overlap_conflicts) >= 1
        assert overlap_conflicts[0].domain == "sub.example.com"
        assert "shadowed" in overlap_conflicts[0].description

    def test_no_overlap_for_different_domains(self):
        detector = ConflictDetector()
        deny = {
            "example.com": ["source1"],
            "other.net": ["source2"],
        }
        conflicts = detector.detect(deny)
        overlap = detector.get_conflicts_by_type("overlap")
        assert len(overlap) == 0

    def test_get_conflicts_by_type(self):
        detector = ConflictDetector()
        deny = {
            "example.com": ["s1"],
            "sub.example.com": ["s2"],
        }
        allow = {"example.com": ["s3"]}
        detector.detect(deny, allow)

        deny_allow = detector.get_conflicts_by_type("deny_allow")
        overlap = detector.get_conflicts_by_type("overlap")
        assert len(deny_allow) == 1
        assert len(overlap) >= 1

    def test_has_conflicts_property(self):
        detector = ConflictDetector()
        deny = {"example.com": ["s1"]}
        allow = {"example.com": ["s2"]}
        detector.detect(deny, allow)
        assert detector.has_conflicts is True

    def test_empty_input(self):
        detector = ConflictDetector()
        conflicts = detector.detect({})
        assert conflicts == []


class TestRuleConflict:
    def test_dataclass(self):
        conflict = RuleConflict(
            domain="test.com",
            conflict_type="deny_allow",
            sources=["s1", "s2"],
            description="test conflict",
        )
        assert conflict.domain == "test.com"
        assert conflict.conflict_type == "deny_allow"
        assert len(conflict.sources) == 2
