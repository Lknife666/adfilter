"""Tests for EasylistHandler."""

from __future__ import annotations

import pytest

from adfilter.constants import RuleSet
from adfilter.handler import get_handler
from adfilter.model import Control, Mode, Rule, RuleType, Scope


@pytest.fixture
def handler():
    return get_handler(RuleSet.EASYLIST)


class TestParse:
    def test_basic_domain(self, handler):
        rule = handler.parse("||example.com^")
        assert rule.target == "example.com"
        assert rule.mode == Mode.DENY
        assert rule.type == RuleType.BASIC
        assert Control.OVERLAY in rule.controls
        assert Control.QUALIFIER in rule.controls

    def test_allow_rule(self, handler):
        rule = handler.parse("@@||allow.example.com^")
        assert rule.target == "allow.example.com"
        assert rule.mode == Mode.ALLOW
        assert Control.OVERLAY in rule.controls

    def test_important_modifier(self, handler):
        rule = handler.parse("||ads.example.com^$important")
        assert rule.target == "ads.example.com"
        assert Control.IMPORTANT in rule.controls

    def test_all_modifier(self, handler):
        rule = handler.parse("||ads.example.com^$all")
        assert Control.ALL in rule.controls

    def test_unknown_modifier(self, handler):
        rule = handler.parse("||ads.example.com^$third-party")
        assert rule.type == RuleType.UNKNOWN

    def test_regex_rule(self, handler):
        rule = handler.parse("/ads[0-9]+\\.example\\.com/")
        assert rule.type == RuleType.REGEX
        assert rule.target == "ads[0-9]+\\.example\\.com"

    def test_comment_detection(self, handler):
        assert handler.is_comment("! Title: Test")
        assert handler.is_comment("# Comment")
        assert handler.is_comment("[Adblock Plus]")
        assert not handler.is_comment("||example.com^")


class TestFormat:
    def test_basic_deny(self, handler):
        rule = Rule(
            target="example.com",
            mode=Mode.DENY,
            scope=Scope.DOMAIN,
            type=RuleType.BASIC,
            controls={Control.OVERLAY, Control.QUALIFIER},
        )
        assert handler.format(rule) == "||example.com^"

    def test_allow_format(self, handler):
        rule = Rule(
            target="example.com",
            mode=Mode.ALLOW,
            scope=Scope.DOMAIN,
            type=RuleType.BASIC,
            controls={Control.OVERLAY, Control.QUALIFIER},
        )
        assert handler.format(rule) == "@@||example.com^"

    def test_unknown_same_source_verbatim(self, handler):
        rule = Rule(
            origin="some-unknown-line",
            type=RuleType.UNKNOWN,
            source_type=RuleSet.EASYLIST,
        )
        assert handler.format(rule) == "some-unknown-line"

    def test_unknown_other_source_none(self, handler):
        rule = Rule(
            origin="some-unknown-line",
            type=RuleType.UNKNOWN,
            source_type=RuleSet.HOSTS,
        )
        assert handler.format(rule) is None

    def test_rewrite_none(self, handler):
        rule = Rule(
            target="example.com",
            mode=Mode.REWRITE,
            scope=Scope.DOMAIN,
            type=RuleType.BASIC,
        )
        assert handler.format(rule) is None
