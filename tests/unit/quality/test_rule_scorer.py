"""Tests for RuleScorer."""

from __future__ import annotations

import pytest

from adfilter.model import Control, Mode, Rule, RuleType, Scope
from adfilter.quality.rule_scorer import RuleScore, RuleScorer, ScoreSummary


def _rule(target: str, source: str = "src1", rtype: RuleType = RuleType.BASIC, overlay: bool = False) -> Rule:
    controls = {Control.OVERLAY} if overlay else set()
    return Rule(
        target=target, mode=Mode.DENY, scope=Scope.DOMAIN,
        type=rtype, source_name=source, controls=controls,
    )


class TestRuleScoring:
    def test_multi_source_high_score(self):
        source_counts = {"well-known.com": {"src1", "src2", "src3", "src4"}}
        scorer = RuleScorer(source_counts=source_counts)
        score = scorer.score(_rule("well-known.com"))
        assert score.components["multi_source"] == 100.0

    def test_single_source_low_score(self):
        source_counts = {"single.com": {"src1"}}
        scorer = RuleScorer(source_counts=source_counts)
        score = scorer.score(_rule("single.com"))
        assert score.components["multi_source"] == 20.0

    def test_alive_domain_high_freshness(self):
        alive = {"alive.com"}
        scorer = RuleScorer(alive_domains=alive)
        score = scorer.score(_rule("alive.com"))
        assert score.components["freshness"] == 100.0

    def test_dead_domain_zero_freshness(self):
        alive = {"other.com"}
        scorer = RuleScorer(alive_domains=alive)
        score = scorer.score(_rule("dead.com"))
        assert score.components["freshness"] == 0.0

    def test_no_freshness_data_neutral(self):
        scorer = RuleScorer()  # No alive_domains provided
        score = scorer.score(_rule("any.com"))
        assert score.components["freshness"] == 50.0

    def test_basic_type_high_specificity(self):
        scorer = RuleScorer()
        score = scorer.score(_rule("exact.com", rtype=RuleType.BASIC))
        assert score.components["specificity"] == 100.0

    def test_wildcard_type_medium_specificity(self):
        scorer = RuleScorer()
        score = scorer.score(_rule("*.wild.com", rtype=RuleType.WILDCARD))
        assert score.components["specificity"] == 50.0

    def test_conflict_domain_zero_score(self):
        conflicts = {"conflicted.com"}
        scorer = RuleScorer(conflict_domains=conflicts)
        score = scorer.score(_rule("conflicted.com"))
        assert score.components["no_conflict"] == 0.0

    def test_no_conflict_full_score(self):
        scorer = RuleScorer(conflict_domains=set())
        score = scorer.score(_rule("clean.com"))
        assert score.components["no_conflict"] == 100.0

    def test_broad_overlay_low_breadth(self):
        scorer = RuleScorer()
        score = scorer.score(_rule("example.com", overlay=True))  # TLD+1 overlay
        assert score.components["not_overbroad"] <= 50.0

    def test_deep_subdomain_high_breadth(self):
        scorer = RuleScorer()
        score = scorer.score(_rule("ads.sub.example.com"))
        assert score.components["not_overbroad"] == 100.0


class TestRuleGrade:
    def test_grade_a(self):
        s = RuleScore(domain="test", total_score=85.0)
        assert s.grade == "A"

    def test_grade_b(self):
        s = RuleScore(domain="test", total_score=65.0)
        assert s.grade == "B"

    def test_grade_c(self):
        s = RuleScore(domain="test", total_score=45.0)
        assert s.grade == "C"

    def test_grade_d(self):
        s = RuleScore(domain="test", total_score=25.0)
        assert s.grade == "D"

    def test_grade_f(self):
        s = RuleScore(domain="test", total_score=10.0)
        assert s.grade == "F"


class TestBatchScoring:
    def test_batch_summary(self):
        source_counts = {
            "popular.com": {"s1", "s2", "s3"},
            "single.com": {"s1"},
        }
        scorer = RuleScorer(source_counts=source_counts)
        rules = [
            _rule("popular.com", source="s1"),
            _rule("single.com", source="s1"),
        ]
        summary = scorer.score_batch(rules)
        assert summary.total_rules == 2
        assert summary.average_score > 0
        assert "s1" in summary.source_averages

    def test_empty_batch(self):
        scorer = RuleScorer()
        summary = scorer.score_batch([])
        assert summary.total_rules == 0
        assert summary.average_score == 0.0
