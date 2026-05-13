"""Tests for MikrotikHandler."""

from __future__ import annotations

import pytest

from adfilter.constants import RuleSet
from adfilter.handler import get_handler
from adfilter.model import Mode, Rule, RuleType, Scope


@pytest.fixture
def handler():
    return get_handler(RuleSet.MIKROTIK)


class TestParse:
    def test_add_name(self, handler):
        line = 'add name=ads.example.com type=A address=0.0.0.0 comment="adfilter"'
        rule = handler.parse(line)
        assert rule.target == "ads.example.com"
        assert rule.mode == Mode.DENY
        assert rule.type == RuleType.BASIC

    def test_invalid_line(self, handler):
        rule = handler.parse("/ip dns static")
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
        result = handler.format(rule)
        assert result == 'add name=ads.example.com type=A address=0.0.0.0 comment="adfilter"'

    def test_wildcard_skipped(self, handler):
        rule = Rule(
            target="*.example.com",
            mode=Mode.DENY,
            scope=Scope.DOMAIN,
            type=RuleType.WILDCARD,
        )
        assert handler.format(rule) is None

    def test_head_format(self, handler):
        assert handler.head_format() == "/ip dns static"
