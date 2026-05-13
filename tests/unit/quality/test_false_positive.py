"""Tests for false positive analyzer."""

from __future__ import annotations

import pytest

from adfilter.quality.false_positive_analyzer import (
    DEFAULT_POPULAR_DOMAINS,
    FalsePositiveAnalyzer,
    FalsePositiveHit,
)


class TestFalsePositiveAnalyzer:
    def test_detects_popular_domain(self):
        analyzer = FalsePositiveAnalyzer()
        hits = analyzer.analyze(["google.com"])
        assert len(hits) == 1
        assert hits[0].domain == "google.com"
        assert hits[0].confidence == 0.9
        assert "popular" in hits[0].reason

    def test_detects_parent_of_popular(self):
        analyzer = FalsePositiveAnalyzer()
        hits = analyzer.analyze(["com"])
        # "com" is a parent of popular domains like google.com
        assert len(hits) >= 1

    def test_detects_short_domain(self):
        analyzer = FalsePositiveAnalyzer(min_domain_length=5)
        hits = analyzer.analyze(["a.co"])
        assert len(hits) == 1
        assert "short" in hits[0].reason

    def test_no_false_positive_for_ad_domain(self):
        analyzer = FalsePositiveAnalyzer()
        hits = analyzer.analyze(["tracking.adserver.example.com"])
        assert len(hits) == 0

    def test_high_confidence_hits(self):
        analyzer = FalsePositiveAnalyzer()
        analyzer.analyze(["github.com", "a.co", "normal.example.com"])
        high = analyzer.high_confidence_hits
        assert any(h.domain == "github.com" for h in high)
        assert not any(h.domain == "normal.example.com" for h in high)

    def test_hit_count(self):
        analyzer = FalsePositiveAnalyzer()
        analyzer.analyze(["google.com", "facebook.com", "random.adserv.net"])
        assert analyzer.hit_count == 2

    def test_empty_input(self):
        analyzer = FalsePositiveAnalyzer()
        hits = analyzer.analyze([])
        assert hits == []
        assert analyzer.hit_count == 0

    def test_custom_popular_domains(self):
        custom = frozenset({"mysite.com"})
        analyzer = FalsePositiveAnalyzer(popular_domains=custom)
        hits = analyzer.analyze(["mysite.com"])
        assert len(hits) == 1
        assert hits[0].confidence == 0.9

    def test_source_name_preserved(self):
        analyzer = FalsePositiveAnalyzer()
        hits = analyzer.analyze(["google.com"], source_name="test-list")
        assert hits[0].source == "test-list"
