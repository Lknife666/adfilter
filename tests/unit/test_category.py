"""Tests for the category classification module."""

from __future__ import annotations

from adfilter.category import (
    RuleCategory,
    category_from_source,
    classify_domain,
    infer_category,
)


class TestRuleCategory:
    def test_enum_values(self):
        assert RuleCategory.ADS == "ads"
        assert RuleCategory.TRACKING == "tracking"
        assert RuleCategory.MALWARE == "malware"

    def test_category_from_source(self):
        assert category_from_source("ads") == RuleCategory.ADS
        assert category_from_source("privacy") == RuleCategory.TRACKING
        assert category_from_source("malware") == RuleCategory.MALWARE
        assert category_from_source("annoyance") == RuleCategory.ANNOYANCE
        assert category_from_source("unknown_thing") == RuleCategory.UNKNOWN

    def test_category_from_source_case_insensitive(self):
        assert category_from_source("ADS") == RuleCategory.ADS
        assert category_from_source("Privacy") == RuleCategory.TRACKING

    def test_infer_tracking(self):
        assert infer_category("track.example.com") == RuleCategory.TRACKING
        assert infer_category("pixel.analytics.com") == RuleCategory.TRACKING
        assert infer_category("beacon.site.com") == RuleCategory.TRACKING

    def test_infer_ads(self):
        assert infer_category("ads.example.com") == RuleCategory.ADS
        assert infer_category("adserver.network.com") == RuleCategory.ADS
        assert infer_category("doubleclick.net") == RuleCategory.ADS

    def test_infer_malware(self):
        assert infer_category("malware-distribution.com") == RuleCategory.MALWARE
        assert infer_category("phishing-site.net") == RuleCategory.MALWARE

    def test_infer_cryptominer(self):
        assert infer_category("coinhive.com") == RuleCategory.CRYPTOMINER

    def test_infer_unknown(self):
        assert infer_category("normal-website.com") == RuleCategory.UNKNOWN

    def test_classify_domain_source_priority(self):
        # Source category overrides keyword inference
        result = classify_domain("ads.example.com", source_category="malware")
        assert result == RuleCategory.MALWARE

    def test_classify_domain_fallback_to_inference(self):
        result = classify_domain("tracker.example.com", source_category="")
        assert result == RuleCategory.TRACKING

    def test_classify_domain_unknown_source_uses_inference(self):
        result = classify_domain("ads.network.com", source_category="something_new")
        assert result == RuleCategory.ADS
