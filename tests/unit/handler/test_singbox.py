"""Tests for SingboxHandler."""

from __future__ import annotations

import json

import pytest

from adfilter.constants import RuleSet
from adfilter.handler import get_handler
from adfilter.model import Control, Mode, Rule, RuleType, Scope


@pytest.fixture
def handler():
    return get_handler(RuleSet.SINGBOX)


class TestParse:
    def test_json_domain_suffix(self, handler):
        line = '{"domain_suffix": ["example.com"]}'
        rule = handler.parse(line)
        assert rule.target == "example.com"
        assert Control.OVERLAY in rule.controls

    def test_json_domain_exact(self, handler):
        line = '{"domain": ["exact.example.com"]}'
        rule = handler.parse(line)
        assert rule.target == "exact.example.com"
        assert Control.OVERLAY not in rule.controls

    def test_bare_domain(self, handler):
        rule = handler.parse("example.com")
        assert rule.target == "example.com"
        assert rule.type == RuleType.BASIC

    def test_bare_domain_with_dot(self, handler):
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
        result = handler.format(rule)
        assert result is not None
        obj = json.loads(result)
        assert "domain" in obj
        assert obj["domain"] == ["example.com"]

    def test_overlay_domain_suffix(self, handler):
        rule = Rule(
            target="example.com",
            mode=Mode.DENY,
            scope=Scope.DOMAIN,
            type=RuleType.BASIC,
            controls={Control.OVERLAY},
        )
        result = handler.format(rule)
        assert result is not None
        obj = json.loads(result)
        assert "domain_suffix" in obj
        assert obj["domain_suffix"] == ["example.com"]

    def test_allow_skipped(self, handler):
        rule = Rule(
            target="example.com",
            mode=Mode.ALLOW,
            scope=Scope.DOMAIN,
            type=RuleType.BASIC,
        )
        assert handler.format(rule) is None
