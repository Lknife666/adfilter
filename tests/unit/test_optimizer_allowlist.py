"""Tests for optimizer allowlist functionality."""

from __future__ import annotations

import pytest

from adfilter.config import OptimizerConfig
from adfilter.model import Control, Mode, Rule, RuleType, Scope
from adfilter.optimizer import RuleOptimizer


def _deny_rule(target: str, source: str = "test") -> Rule:
    return Rule(
        origin=f"||{target}^",
        target=target,
        mode=Mode.DENY,
        scope=Scope.DOMAIN,
        type=RuleType.BASIC,
        source_name=source,
    )


def _allow_rule(target: str) -> Rule:
    return Rule(
        origin=f"@@||{target}^",
        target=target,
        mode=Mode.ALLOW,
        scope=Scope.DOMAIN,
        type=RuleType.BASIC,
        source_name="test",
    )


class TestAllowlistExactMatch:
    def test_removes_exact_match(self):
        config = OptimizerConfig(enable=True)
        allowlist = {"ads.example.com"}
        opt = RuleOptimizer(config, allowlist=allowlist)

        opt.feed(_deny_rule("ads.example.com"))
        opt.feed(_deny_rule("other.example.com"))

        results = list(opt.drain())
        targets = {r.target for r in results}
        assert "ads.example.com" not in targets
        assert "other.example.com" in targets

    def test_keeps_non_matching(self):
        config = OptimizerConfig(enable=True)
        allowlist = {"safe.example.com"}
        opt = RuleOptimizer(config, allowlist=allowlist)

        opt.feed(_deny_rule("ads.example.com"))
        results = list(opt.drain())
        assert len(results) == 1
        assert results[0].target == "ads.example.com"


class TestAllowlistSuffixMatch:
    def test_removes_subdomain_of_allowed(self):
        config = OptimizerConfig(enable=True)
        allowlist = {"example.com"}
        opt = RuleOptimizer(config, allowlist=allowlist)

        opt.feed(_deny_rule("ads.example.com"))
        opt.feed(_deny_rule("tracker.example.com"))
        opt.feed(_deny_rule("other.net"))

        results = list(opt.drain())
        targets = {r.target for r in results}
        assert "ads.example.com" not in targets
        assert "tracker.example.com" not in targets
        assert "other.net" in targets

    def test_does_not_remove_partial_match(self):
        config = OptimizerConfig(enable=True)
        allowlist = {"ample.com"}
        opt = RuleOptimizer(config, allowlist=allowlist)

        opt.feed(_deny_rule("example.com"))
        results = list(opt.drain())
        assert len(results) == 1


class TestAllowlistPreservesAllowRules:
    def test_allow_rules_not_removed(self):
        config = OptimizerConfig(enable=True)
        allowlist = {"example.com"}
        opt = RuleOptimizer(config, allowlist=allowlist)

        opt.feed(_allow_rule("example.com"))
        results = list(opt.drain())
        assert len(results) == 1
        assert results[0].mode == Mode.ALLOW


class TestAllowlistEmpty:
    def test_empty_allowlist_keeps_all(self):
        config = OptimizerConfig(enable=True)
        opt = RuleOptimizer(config, allowlist=set())

        opt.feed(_deny_rule("ads.example.com"))
        opt.feed(_deny_rule("tracker.example.com"))

        results = list(opt.drain())
        assert len(results) == 2
