"""Tests for LoonHandler."""

from __future__ import annotations

import pytest

from adfilter.constants import RuleSet
from adfilter.handler import get_handler
from adfilter.model import Control, Mode, Rule, RuleType, Scope


@pytest.fixture
def handler():
    return get_handler(RuleSet.LOON)


class TestParse:
    def test_domain_reject(self, handler):
        rule = handler.parse("DOMAIN,ads.example.com,REJECT")
        assert rule.target == "ads.example.com"
        assert rule.mode == Mode.DENY
        assert rule.type == RuleType.BASIC
        assert Control.OVERLAY not in rule.controls

    def test_domain_suffix_reject(self, handler):
        rule = handler.parse("DOMAIN-SUFFIX,example.com,REJECT")
        assert rule.target == "example.com"
        assert rule.mode == Mode.DENY
        assert Control.OVERLAY in rule.controls

    def test_domain_keyword(self, handler):
        rule = handler.parse("DOMAIN-KEYWORD,tracker,REJECT")
        assert rule.target == "tracker"
        assert rule.type == RuleType.WILDCARD

    def test_direct_is_allow(self, handler):
        rule = handler.parse("DOMAIN,example.com,DIRECT")
        assert rule.mode == Mode.ALLOW

    def test_empty_line(self, handler):
        rule = handler.parse("")
        assert rule.is_empty()


class TestFormat:
    def test_basic_domain(self, handler):
        rule = Rule(
            target="ads.example.com",
            mode=Mode.DENY,
            scope=Scope.DOMAIN,
            type=RuleType.BASIC,
        )
        assert handler.format(rule) == "DOMAIN,ads.example.com,REJECT"

    def test_overlay_domain_suffix(self, handler):
        rule = Rule(
            target="example.com",
            mode=Mode.DENY,
            scope=Scope.DOMAIN,
            type=RuleType.BASIC,
            controls={Control.OVERLAY},
        )
        assert handler.format(rule) == "DOMAIN-SUFFIX,example.com,REJECT"

    def test_wildcard_keyword(self, handler):
        rule = Rule(
            target="tracker",
            mode=Mode.DENY,
            scope=Scope.DOMAIN,
            type=RuleType.WILDCARD,
        )
        assert handler.format(rule) == "DOMAIN-KEYWORD,tracker,REJECT"

    def test_allow_skipped(self, handler):
        rule = Rule(
            target="example.com",
            mode=Mode.ALLOW,
            scope=Scope.DOMAIN,
            type=RuleType.BASIC,
        )
        assert handler.format(rule) is None
