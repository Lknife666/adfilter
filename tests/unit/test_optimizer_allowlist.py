"""Tests for optimizer allowlist feature."""

from __future__ import annotations

import pytest

from adfilter.config import OptimizerConfig
from adfilter.model import Control, Mode, Rule, RuleType, Scope
from adfilter.optimizer import RuleOptimizer


def _make_rule(target: str, mode: Mode = Mode.DENY, source_name: str = "test") -> Rule:
    return Rule(
        origin=f"||{target}^",
        target=target,
        mode=mode,
        scope=Scope.DOMAIN,
        type=RuleType.BASIC,
        controls={Control.OVERLAY},
        source_name=source_name,
    )


class TestAllowlist:
    def test_exact_match_removes_deny(self):
        config = OptimizerConfig(enable=True)
        allowlist = {"blocked.com"}
        opt = RuleOptimizer(config, allowlist=allowlist)

        opt.feed(_make_rule("blocked.com"))
        opt.feed(_make_rule("notblocked.com"))
        results = list(opt.drain())

        targets = {r.target for r in results}
        assert "blocked.com" not in targets
        assert "notblocked.com" in targets

    def test_suffix_match_removes_subdomain(self):
        config = OptimizerConfig(enable=True)
        allowlist = {"example.com"}
        opt = RuleOptimizer(config, allowlist=allowlist)

        opt.feed(_make_rule("sub.example.com"))
        opt.feed(_make_rule("deep.sub.example.com"))
        opt.feed(_make_rule("other.net"))
        results = list(opt.drain())

        targets = {r.target for r in results}
        assert "sub.example.com" not in targets
        assert "deep.sub.example.com" not in targets
        assert "other.net" in targets

    def test_allow_rules_not_affected(self):
        config = OptimizerConfig(enable=True)
        allowlist = {"example.com"}
        opt = RuleOptimizer(config, allowlist=allowlist)

        opt.feed(_make_rule("example.com", mode=Mode.ALLOW))
        results = list(opt.drain())

        # ALLOW rules should not be removed by allowlist
        assert len(results) == 1
        assert results[0].mode == Mode.ALLOW

    def test_empty_allowlist_no_effect(self):
        config = OptimizerConfig(enable=True)
        opt = RuleOptimizer(config, allowlist=set())

        opt.feed(_make_rule("example.com"))
        results = list(opt.drain())
        assert len(results) == 1

    def test_allowlist_with_optimizer_combined(self):
        config = OptimizerConfig(
            enable=True,
            collapse_subdomains=True,
            drop_allow_shadowed_deny=True,
        )
        allowlist = {"remove-me.com"}
        opt = RuleOptimizer(config, allowlist=allowlist)

        opt.feed(_make_rule("remove-me.com"))
        opt.feed(_make_rule("keep-me.com"))
        results = list(opt.drain())

        targets = {r.target for r in results}
        assert "remove-me.com" not in targets
        assert "keep-me.com" in targets
