"""Unit tests for model module."""

from __future__ import annotations

import pytest

from adfilter.model import Control, Mode, Rule, RuleType, Scope


class TestRule:
    def test_empty_sentinel(self):
        empty = Rule.empty()
        assert empty.is_empty()

    def test_is_empty_no_data(self):
        rule = Rule()
        assert rule.is_empty()

    def test_is_empty_with_data(self):
        rule = Rule(origin="test", target="example.com", type=RuleType.BASIC)
        assert not rule.is_empty()

    def test_murmur3_hash_basic(self):
        r1 = Rule(target="example.com", mode=Mode.DENY, scope=Scope.DOMAIN, type=RuleType.BASIC)
        r2 = Rule(target="example.com", mode=Mode.DENY, scope=Scope.DOMAIN, type=RuleType.BASIC)
        assert r1.murmur3_hash() == r2.murmur3_hash()

    def test_murmur3_hash_different_targets(self):
        r1 = Rule(target="a.com", mode=Mode.DENY, scope=Scope.DOMAIN, type=RuleType.BASIC)
        r2 = Rule(target="b.com", mode=Mode.DENY, scope=Scope.DOMAIN, type=RuleType.BASIC)
        assert r1.murmur3_hash() != r2.murmur3_hash()

    def test_murmur3_hash_different_modes(self):
        r1 = Rule(target="a.com", mode=Mode.DENY, scope=Scope.DOMAIN, type=RuleType.BASIC)
        r2 = Rule(target="a.com", mode=Mode.ALLOW, scope=Scope.DOMAIN, type=RuleType.BASIC)
        assert r1.murmur3_hash() != r2.murmur3_hash()

    def test_murmur3_hash_unknown_uses_origin(self):
        r1 = Rule(origin="line-a", type=RuleType.UNKNOWN)
        r2 = Rule(origin="line-b", type=RuleType.UNKNOWN)
        assert r1.murmur3_hash() != r2.murmur3_hash()

    def test_default_controls_empty(self):
        rule = Rule()
        assert rule.controls == set()

    def test_controls_set(self):
        rule = Rule(controls={Control.OVERLAY, Control.QUALIFIER})
        assert Control.OVERLAY in rule.controls
        assert Control.QUALIFIER in rule.controls


class TestEnums:
    def test_mode_values(self):
        assert Mode.DENY == "deny"
        assert Mode.ALLOW == "allow"
        assert Mode.REWRITE == "rewrite"

    def test_scope_values(self):
        assert Scope.DOMAIN == "domain"
        assert Scope.IP == "ip"
        assert Scope.URL == "url"

    def test_rule_type_values(self):
        assert RuleType.BASIC == "basic"
        assert RuleType.WILDCARD == "wildcard"
        assert RuleType.REGEX == "regex"
        assert RuleType.UNKNOWN == "unknown"
