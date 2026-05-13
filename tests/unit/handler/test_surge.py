"""Tests for SurgeHandler."""

from __future__ import annotations

import pytest

from adfilter.constants import RuleSet
from adfilter.handler import get_handler
from adfilter.model import Control, Mode, Rule, RuleType, Scope


@pytest.fixture
def handler():
    return get_handler(RuleSet.SURGE)


class TestParse:
    def test_basic_domain(self, handler):
        rule = handler.parse("example.com")
        assert rule.target == "example.com"
        assert rule.type == RuleType.BASIC
        assert rule.mode == Mode.DENY

    def test_overlay_domain(self, handler):
        rule = handler.parse(".example.com")
        assert rule.target == "example.com"
        assert Control.OVERLAY in rule.controls

    def test_empty_line(self, handler):
        rule = handler.parse("")
        assert rule.is_empty()


class TestFormat:
    def test_basic_domain(self, handler):
        rule = Rule(
            target="example.com",
            mode=Mode.DENY,
            scope=Scope.DOMAIN,
            type=RuleType.BASIC,
        )
        assert handler.format(rule) == "example.com"

    def test_overlay_domain(self, handler):
        rule = Rule(
            target="example.com",
            mode=Mode.DENY,
            scope=Scope.DOMAIN,
            type=RuleType.BASIC,
            controls={Control.OVERLAY},
        )
        assert handler.format(rule) == ".example.com"

    def test_allow_skipped(self, handler):
        rule = Rule(
            target="example.com",
            mode=Mode.ALLOW,
            scope=Scope.DOMAIN,
            type=RuleType.BASIC,
        )
        assert handler.format(rule) is None
