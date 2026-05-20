"""Tests for rule scorer."""

from __future__ import annotations

import pytest

from adfilter.quality.rule_scorer import RuleScorer, ScoredRule


class TestRuleScorer:
    def test_empty_input(self):
        scorer = RuleScorer()
        results = scorer.score_rules({})
        assert results == []
        assert scorer.average_score == 0.0
        assert scorer.total_scored == 0

    def test_single_domain_single_source(self):
        scorer = RuleScorer()
        results = scorer.score_rules({"ads.example.com": ["source1"]}, total_sources=5)
        assert len(results) == 1
        assert 0.0 <= results[0].score <= 1.0
        assert results[0].domain == "ads.example.com"
        assert results[0].sources == ["source1"]

    def test_multi_source_scores_higher(self):
        scorer = RuleScorer()
        results = scorer.score_rules(
            {
                "popular.ad.com": ["s1", "s2", "s3", "s4"],
                "rare.ad.com": ["s1"],
            },
            total_sources=5,
        )
        # The one with more sources should score higher
        popular = next(r for r in results if r.domain == "popular.ad.com")
        rare = next(r for r in results if r.domain == "rare.ad.com")
        assert popular.score > rare.score

    def test_sorted_by_score_descending(self):
        scorer = RuleScorer()
        results = scorer.score_rules(
            {
                "a.com": ["s1"],
                "b.c.d.e.com": ["s1", "s2", "s3"],
            },
            total_sources=3,
        )
        assert results[0].score >= results[-1].score

    def test_get_low_quality(self):
        scorer = RuleScorer()
        scorer.score_rules(
            {
                "a.b": ["s1"],  # short, few labels -> low score
                "tracking.ads.example.com": ["s1", "s2", "s3"],
            },
            total_sources=3,
        )
        low = scorer.get_low_quality(threshold=0.5)
        # The short domain should be low quality
        assert any(r.domain == "a.b" for r in low)

    def test_get_high_quality(self):
        scorer = RuleScorer()
        scorer.score_rules(
            {
                "tracking.ads.very.specific.example.com": ["s1", "s2", "s3"],
            },
            total_sources=3,
        )
        high = scorer.get_high_quality(threshold=0.5)
        assert len(high) == 1

    def test_average_score(self):
        scorer = RuleScorer()
        scorer.score_rules({"a.com": ["s1"], "b.com": ["s1"]}, total_sources=1)
        avg = scorer.average_score
        assert 0.0 < avg < 1.0

    def test_factors_populated(self):
        scorer = RuleScorer()
        results = scorer.score_rules({"test.example.com": ["s1"]}, total_sources=2)
        assert "source_reputation" in results[0].factors
        assert "specificity" in results[0].factors
        assert "length" in results[0].factors
        assert "label_count" in results[0].factors
