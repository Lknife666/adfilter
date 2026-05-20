"""Tests for the source quality scoring module."""

from __future__ import annotations

import time

from adfilter.quality.source_scorer import (
    FetchRecord,
    SourceHistory,
    SourceQualityScore,
    SourceScorer,
)


class TestSourceQualityScore:
    def test_grade_A(self):
        s = SourceQualityScore(source_id="test", overall_score=95)
        assert s.grade == "A"

    def test_grade_B(self):
        s = SourceQualityScore(source_id="test", overall_score=80)
        assert s.grade == "B"

    def test_grade_C(self):
        s = SourceQualityScore(source_id="test", overall_score=65)
        assert s.grade == "C"

    def test_grade_D(self):
        s = SourceQualityScore(source_id="test", overall_score=45)
        assert s.grade == "D"

    def test_grade_F(self):
        s = SourceQualityScore(source_id="test", overall_score=30)
        assert s.grade == "F"

    def test_compute_overall_perfect(self):
        s = SourceQualityScore(
            source_id="test",
            freshness=1.0,
            availability=1.0,
            dead_domain_ratio=0.0,
            false_positive_rate=0.0,
            unique_contribution=1.0,
            stability=1.0,
            community_trust=1.0,
        )
        result = s.compute_overall()
        assert result == 100.0

    def test_compute_overall_worst(self):
        s = SourceQualityScore(
            source_id="test",
            freshness=0.0,
            availability=0.0,
            dead_domain_ratio=1.0,
            false_positive_rate=1.0,
            unique_contribution=0.0,
            stability=0.0,
            community_trust=0.0,
        )
        result = s.compute_overall()
        # (0*0.15 + 0*0.20 + 0*0.15 + 0*0.20 + 0*0.15 + 0*0.10 + 0*0.05) * 100 = 0
        assert result == 0.0

    def test_to_dict(self):
        s = SourceQualityScore(source_id="test")
        s.compute_overall()
        d = s.to_dict()
        assert d["source_id"] == "test"
        assert "grade" in d
        assert "overall_score" in d


class TestSourceHistory:
    def test_availability_rate_empty(self):
        h = SourceHistory(source_id="test")
        assert h.availability_rate == 1.0

    def test_availability_rate(self):
        h = SourceHistory(source_id="test")
        h.fetch_records = [
            FetchRecord(timestamp=time.time(), success=True),
            FetchRecord(timestamp=time.time(), success=True),
            FetchRecord(timestamp=time.time(), success=False),
        ]
        assert abs(h.availability_rate - 2 / 3) < 0.01

    def test_freshness_score_recent(self):
        h = SourceHistory(source_id="test")
        h.fetch_records = [FetchRecord(timestamp=time.time(), success=True)]
        assert h.freshness_score == 1.0

    def test_freshness_score_old(self):
        h = SourceHistory(source_id="test")
        h.fetch_records = [FetchRecord(timestamp=time.time() - 200 * 3600, success=True)]
        assert h.freshness_score == 0.3

    def test_stability_no_history(self):
        h = SourceHistory(source_id="test")
        assert h.stability_score == 1.0

    def test_stability_stable(self):
        h = SourceHistory(source_id="test")
        h.rule_count_history = [1000, 1001, 1002, 1003]
        assert h.stability_score >= 0.9

    def test_stability_volatile(self):
        h = SourceHistory(source_id="test")
        h.rule_count_history = [1000, 2000, 500, 3000]
        assert h.stability_score <= 0.5


class TestSourceScorer:
    def test_record_fetch_and_compute(self, tmp_path):
        scorer = SourceScorer(cache_file=tmp_path / "scores.json")
        scorer.record_fetch("anti-ad", success=True, rule_count=5000, duration_ms=1200)
        scorer.record_fetch("easylist", success=True, rule_count=8000, duration_ms=900)
        scorer.record_fetch("bad-source", success=False, rule_count=0)

        scores = scorer.compute_scores()
        assert "anti-ad" in scores
        assert "easylist" in scores
        assert "bad-source" in scores
        assert scores["anti-ad"].availability == 1.0
        assert scores["bad-source"].availability == 0.0

    def test_cache_persistence(self, tmp_path):
        cache = tmp_path / "scores.json"
        scorer1 = SourceScorer(cache_file=cache)
        scorer1.record_fetch("test", success=True, rule_count=1000)
        scorer1.compute_scores()

        # Load from cache
        scorer2 = SourceScorer(cache_file=cache)
        assert "test" in scorer2._histories
        assert scorer2._histories["test"].last_rule_count == 1000

    def test_update_dead_ratio(self, tmp_path):
        scorer = SourceScorer(cache_file=tmp_path / "scores.json")
        scorer.record_fetch("test", success=True, rule_count=100)
        scorer.update_dead_ratio("test", 0.05, ["dead1.com", "dead2.com"])
        scores = scorer.compute_scores()
        assert scores["test"].dead_domain_ratio == 0.05
