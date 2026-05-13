"""Tests for DnsmasqHandler."""

from __future__ import annotations

import pytest

from adfilter.constants import RuleSet
from adfilter.handler import get_handler
from adfilter.model import Mode, Rule, RuleType, Scope


@pytest.fixture
def handler():
    return get_handler(RuleSet.DNSMASQ)


class TestParse:
    def test_deny_rule(self, handler):
        rule = handler.parse("address=/ads.example.com/0.0.0.0")
        assert rule.target == "ads.example.com"
        assert rule.mode == Mode.DENY
        assert rule.type == RuleType.BASIC

    def test_deny_no_ip(self, handler):
        rule = handler.parse("address=/ads.example.com/")
        assert rule.target == "ads.example.com"
        assert rule.mode == Mode.DENY

    def test_rewrite_rule(self, handler):
        rule = handler.parse("address=/custom.local/192.168.1.1")
        assert rule.mode == Mode.REWRITE
        assert rule.dest == "192.168.1.1"

    def test_invalid_line(self, handler):
        rule = handler.parse("server=8.8.8.8")
        assert rule.is_empty()


class TestFormat:
    def test_basic_deny(self, handler):
        rule = Rule(
            target="ads.example.com",
            mode=Mode.DENY,
            scope=Scope.DOMAIN,
            type=RuleType.BASIC,
            dest="0.0.0.0",
        )
        assert handler.format(rule) == "address=/ads.example.com/0.0.0.0"

    def test_allow_skipped(self, handler):
        rule = Rule(
            target="example.com",
            mode=Mode.ALLOW,
            scope=Scope.DOMAIN,
            type=RuleType.BASIC,
        )
        assert handler.format(rule) is None
