"""Tests for ClashHandler."""

from __future__ import annotations

import pytest

from adfilter.constants import RuleSet
from adfilter.handler import get_handler
from adfilter.model import Control, Mode, Rule, RuleType, Scope


@pytest.fixture
def handler():
    return get_handler(RuleSet.CLASH)


class TestParse:
    def test_basic_domain(self, handler):
        rule = handler.parse("  - 'example.com'")
        assert rule.target == "example.com"
        assert rule.mode == Mode.DENY
        assert rule.type == RuleType.BASIC

    def test_overlay_domain(self, handler):
        rule = handler.parse("  - '+.example.com'")
        assert rule.target == "example.com"
        assert Control.OVERLAY in rule.controls

    def test_wildcard_domain(self, handler):
        rule = handler.parse("  - '*.wild.example.com'")
        assert rule.type == RuleType.UNKNOWN  # leading * is UNKNOWN

    def test_payload_line(self, handler):
        rule = handler.parse("payload:")
        assert rule.is_empty()

    def test_double_quoted(self, handler):
        rule = handler.parse('  - "example.com"')
        assert rule.target == "example.com"


class TestFormat:
    def test_basic_domain(self, handler):
        rule = Rule(
            target="example.com",
            mode=Mode.DENY,
            scope=Scope.DOMAIN,
            type=RuleType.BASIC,
        )
        result = handler.format(rule)
        assert result == "  - \"example.com\""

    def test_overlay_domain(self, handler):
        rule = Rule(
            target="example.com",
            mode=Mode.DENY,
            scope=Scope.DOMAIN,
            type=RuleType.BASIC,
            controls={Control.OVERLAY},
        )
        result = handler.format(rule)
        assert result == "  - \"+.example.com\""

    def test_allow_skipped(self, handler):
        rule = Rule(
            target="example.com",
            mode=Mode.ALLOW,
            scope=Scope.DOMAIN,
            type=RuleType.BASIC,
        )
        assert handler.format(rule) is None
