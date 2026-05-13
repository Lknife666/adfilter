"""Tests for SmartdnsHandler."""

from __future__ import annotations

import pytest

from adfilter.constants import RuleSet
from adfilter.handler import get_handler
from adfilter.model import Control, Mode, Rule, RuleType, Scope


@pytest.fixture
def handler():
    return get_handler(RuleSet.SMARTDNS)


class TestParse:
    def test_deny_overlay(self, handler):
        rule = handler.parse("address /example.com/#")
        assert rule.target == "example.com"
        assert rule.mode == Mode.DENY
        assert Control.OVERLAY in rule.controls

    def test_allow_rule(self, handler):
        rule = handler.parse("address /example.com/-")
        assert rule.mode == Mode.ALLOW

    def test_exact_domain(self, handler):
        rule = handler.parse("address /-example.com/#")
        assert rule.target == "example.com"
        assert Control.OVERLAY not in rule.controls


class TestFormat:
    def test_basic_deny_overlay(self, handler):
        rule = Rule(
            target="example.com",
            mode=Mode.DENY,
            scope=Scope.DOMAIN,
            type=RuleType.BASIC,
            controls={Control.OVERLAY},
        )
        result = handler.format(rule)
        assert result == "address /example.com/#"

    def test_allow_skipped_for_rewrite(self, handler):
        rule = Rule(
            target="example.com",
            mode=Mode.REWRITE,
            scope=Scope.DOMAIN,
            type=RuleType.BASIC,
        )
        assert handler.format(rule) is None
