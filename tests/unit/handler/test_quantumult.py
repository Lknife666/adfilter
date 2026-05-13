"""Tests for QuantumultHandler."""

from __future__ import annotations

import pytest

from adfilter.constants import RuleSet
from adfilter.handler import get_handler
from adfilter.model import Control, Mode, Rule, RuleType, Scope


@pytest.fixture
def handler():
    return get_handler(RuleSet.QUANTUMULT)


class TestParse:
    def test_host_reject(self, handler):
        rule = handler.parse("host, ads.example.com, reject")
        assert rule.target == "ads.example.com"
        assert rule.mode == Mode.DENY
        assert rule.type == RuleType.BASIC
        assert Control.OVERLAY not in rule.controls

    def test_host_suffix_reject(self, handler):
        rule = handler.parse("host-suffix, example.com, reject")
        assert rule.target == "example.com"
        assert rule.mode == Mode.DENY
        assert Control.OVERLAY in rule.controls

    def test_host_keyword(self, handler):
        rule = handler.parse("host-keyword, tracker, reject")
        assert rule.target == "tracker"
        assert rule.type == RuleType.WILDCARD

    def test_direct_is_allow(self, handler):
        rule = handler.parse("host, example.com, direct")
        assert rule.mode == Mode.ALLOW

    def test_empty_line(self, handler):
        rule = handler.parse("")
        assert rule.is_empty()


class TestFormat:
    def test_basic_host(self, handler):
        rule = Rule(
            target="ads.example.com",
            mode=Mode.DENY,
            scope=Scope.DOMAIN,
            type=RuleType.BASIC,
        )
        assert handler.format(rule) == "host, ads.example.com, reject"

    def test_overlay_host_suffix(self, handler):
        rule = Rule(
            target="example.com",
            mode=Mode.DENY,
            scope=Scope.DOMAIN,
            type=RuleType.BASIC,
            controls={Control.OVERLAY},
        )
        assert handler.format(rule) == "host-suffix, example.com, reject"

    def test_wildcard_keyword(self, handler):
        rule = Rule(
            target="tracker",
            mode=Mode.DENY,
            scope=Scope.DOMAIN,
            type=RuleType.WILDCARD,
        )
        assert handler.format(rule) == "host-keyword, tracker, reject"

    def test_allow_skipped(self, handler):
        rule = Rule(
            target="example.com",
            mode=Mode.ALLOW,
            scope=Scope.DOMAIN,
            type=RuleType.BASIC,
        )
        assert handler.format(rule) is None
