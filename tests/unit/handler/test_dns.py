"""Tests for DnsHandler."""

from __future__ import annotations

import pytest

from adfilter.constants import RuleSet
from adfilter.handler import get_handler
from adfilter.model import Control, Mode, Rule, RuleType, Scope


@pytest.fixture
def handler():
    return get_handler(RuleSet.DNS)


class TestParse:
    def test_easylist_format(self, handler):
        rule = handler.parse("||ads.example.com^")
        assert rule.target == "ads.example.com"
        assert rule.mode == Mode.DENY
        assert rule.type == RuleType.BASIC

    def test_hosts_format(self, handler):
        rule = handler.parse("0.0.0.0 ads.example.com")
        assert rule.target == "ads.example.com"
        assert rule.mode == Mode.DENY
        assert rule.type == RuleType.BASIC

    def test_hosts_rewrite(self, handler):
        rule = handler.parse("192.168.1.1 custom.local")
        assert rule.mode == Mode.REWRITE
        assert rule.dest == "192.168.1.1"


class TestFormat:
    def test_basic_deny(self, handler):
        rule = Rule(
            target="example.com",
            mode=Mode.DENY,
            scope=Scope.DOMAIN,
            type=RuleType.BASIC,
            controls={Control.OVERLAY, Control.QUALIFIER},
        )
        result = handler.format(rule)
        assert result == "||example.com^"

    def test_rewrite_hosts_line(self, handler):
        rule = Rule(
            target="custom.local",
            mode=Mode.REWRITE,
            scope=Scope.DOMAIN,
            type=RuleType.BASIC,
            dest="192.168.1.1",
        )
        result = handler.format(rule)
        assert result == "192.168.1.1\tcustom.local"
