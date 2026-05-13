"""Tests for HostsHandler."""

from __future__ import annotations

import pytest

from adfilter.constants import RuleSet
from adfilter.handler import get_handler
from adfilter.model import Mode, Rule, RuleType, Scope


@pytest.fixture
def handler():
    return get_handler(RuleSet.HOSTS)


class TestParse:
    def test_deny_rule(self, handler):
        rule = handler.parse("0.0.0.0 ads.example.com")
        assert rule.target == "ads.example.com"
        assert rule.mode == Mode.DENY
        assert rule.type == RuleType.BASIC

    def test_deny_127(self, handler):
        rule = handler.parse("127.0.0.1 tracker.example.com")
        assert rule.target == "tracker.example.com"
        assert rule.mode == Mode.DENY

    def test_rewrite_rule(self, handler):
        rule = handler.parse("192.168.1.1 custom.local")
        assert rule.mode == Mode.REWRITE
        assert rule.dest == "192.168.1.1"

    def test_localhost_skipped(self, handler):
        rule = handler.parse("127.0.0.1 localhost")
        # "localhost" doesn't match PATTERN_DOMAIN (no dot), so parse_hosts returns None
        assert rule.is_empty()

    def test_invalid_line(self, handler):
        rule = handler.parse("not a valid hosts line at all")
        assert rule.is_empty()

    def test_tab_separated(self, handler):
        rule = handler.parse("0.0.0.0\tads.example.com")
        assert rule.target == "ads.example.com"


class TestFormat:
    def test_basic_deny(self, handler):
        rule = Rule(
            target="ads.example.com",
            mode=Mode.DENY,
            scope=Scope.DOMAIN,
            type=RuleType.BASIC,
            dest="0.0.0.0",
        )
        result = handler.format(rule)
        assert result == "0.0.0.0\tads.example.com"

    def test_wildcard_skipped(self, handler):
        rule = Rule(
            target="*.example.com",
            mode=Mode.DENY,
            scope=Scope.DOMAIN,
            type=RuleType.WILDCARD,
        )
        assert handler.format(rule) is None
