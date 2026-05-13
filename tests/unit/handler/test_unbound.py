"""Tests for UnboundHandler."""

from __future__ import annotations

import pytest

from adfilter.constants import RuleSet
from adfilter.handler import get_handler
from adfilter.model import Mode, Rule, RuleType, Scope


@pytest.fixture
def handler():
    return get_handler(RuleSet.UNBOUND)


class TestParse:
    def test_local_zone(self, handler):
        line = '    local-zone: "ads.example.com." always_nxdomain'
        rule = handler.parse(line)
        assert rule.target == "ads.example.com"
        assert rule.mode == Mode.DENY
        assert rule.type == RuleType.BASIC

    def test_invalid_line(self, handler):
        rule = handler.parse("server:")
        assert rule.is_empty()


class TestFormat:
    def test_basic_deny(self, handler):
        rule = Rule(
            target="ads.example.com",
            mode=Mode.DENY,
            scope=Scope.DOMAIN,
            type=RuleType.BASIC,
        )
        result = handler.format(rule)
        assert result == '    local-zone: "ads.example.com." always_nxdomain'

    def test_head_format(self, handler):
        assert handler.head_format() == "server:"
