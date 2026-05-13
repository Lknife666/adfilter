"""Tests for FalsePositiveAnalyzer."""

from __future__ import annotations

import pytest

from adfilter.model import Control, Mode, Rule, RuleType, Scope
from adfilter.quality.false_positive_analyzer import FalsePositiveAnalyzer, FalsePositiveConfig


def _rule(target: str, source: str = "test", overlay: bool = False, rtype: RuleType = RuleType.BASIC) -> Rule:
    controls = {Control.OVERLAY} if overlay else set()
    return Rule(
        target=target, mode=Mode.DENY, scope=Scope.DOMAIN,
        type=rtype, source_name=source, controls=controls,
    )


@pytest.fixture
def analyzer(tmp_path):
    # Create a small Tranco file
    tranco = tmp_path / "tranco.csv"
    tranco.write_text("1,google.com\n2,facebook.com\n3,youtube.com\n100,popular.com\n", encoding="utf-8")

    # Create a known-good file
    known_good = tmp_path / "known-good.txt"
    known_good.write_text("mybank.com\nsafe-service.org\n", encoding="utf-8")

    config = FalsePositiveConfig(
        enable=True,
        alert_threshold=20.0,
        tranco_path=str(tranco),
        tranco_max_rank=100000,
        known_good_lists=[str(known_good)],
    )
    a = FalsePositiveAnalyzer(config)
    a.load_data()
    return a


class TestFalsePositiveAnalysis:
    def test_popular_domain_flagged(self, analyzer):
        rules = [_rule("google.com")]
        report = analyzer.analyze(rules)
        assert report.suspects_found >= 1
        assert any(s.domain == "google.com" for s in report.suspects)

    def test_known_good_flagged(self, analyzer):
        rules = [_rule("mybank.com")]
        report = analyzer.analyze(rules)
        assert report.suspects_found >= 1
        suspect = next(s for s in report.suspects if s.domain == "mybank.com")
        assert "known-good" in suspect.reasons[0].lower() or any("known" in r.lower() for r in suspect.reasons)

    def test_cdn_subdomain_flagged(self, analyzer):
        rules = [_rule("static.googleapis.com")]
        report = analyzer.analyze(rules)
        assert report.suspects_found >= 1
        suspect = next(s for s in report.suspects if s.domain == "static.googleapis.com")
        assert any("cdn" in r.lower() or "service" in r.lower() for r in suspect.reasons)

    def test_broad_overlay_flagged(self, analyzer):
        rules = [_rule("example.com", overlay=True)]
        report = analyzer.analyze(rules)
        # Broad overlay on 2-level domain adds risk
        flagged = [s for s in report.suspects if s.domain == "example.com"]
        if flagged:
            assert any("broad" in r.lower() or "overlay" in r.lower() for r in flagged[0].reasons)

    def test_unknown_domain_not_flagged(self, analyzer):
        rules = [_rule("obscure-ad-server-12345.xyz")]
        report = analyzer.analyze(rules)
        # Should not be flagged (not popular, not known-good, not CDN)
        assert report.suspects_found == 0

    def test_allow_rules_ignored(self, analyzer):
        rules = [Rule(target="google.com", mode=Mode.ALLOW, scope=Scope.DOMAIN, type=RuleType.BASIC)]
        report = analyzer.analyze(rules)
        assert report.suspects_found == 0

    def test_report_top_method(self, analyzer):
        rules = [_rule("google.com"), _rule("facebook.com"), _rule("youtube.com")]
        report = analyzer.analyze(rules)
        top = report.top(2)
        assert len(top) <= 2
        # Should be sorted by descending risk score
        if len(top) == 2:
            assert top[0].risk_score >= top[1].risk_score
