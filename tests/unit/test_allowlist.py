"""Unit tests for allowlist feature (v0.3)."""

from __future__ import annotations

import pytest

from adfilter.config import OptimizerConfig
from adfilter.model import Control, Mode, Rule, RuleType, Scope
from adfilter.optimizer import RuleOptimizer, _apply_allowlist


def _make_rule(target: str, mode: Mode = Mode.DENY) -> Rule:
    return Rule(
        origin=f"||{target}^",
        target=target,
        mode=mode,
        scope=Scope.DOMAIN,
        type=RuleType.BASIC,
        source_name="test",
    )


class TestApplyAllowlist:
    def test_exact_match_removed(self):
        rules = [_make_rule("ads.example.com"), _make_rule("keep.example.com")]
        allowlist = {"ads.example.com"}
        result = _apply_allowlist(rules, allowlist)
        targets = {r.target for r in result}
        assert "ads.example.com" not in targets
        assert "keep.example.com" in targets

    def test_suffix_match_removed(self):
        rules = [_make_rule("sub.ads.example.com"), _make_rule("keep.com")]
        allowlist = {"ads.example.com"}
        result = _apply_allowlist(rules, allowlist)
        targets = {r.target for r in result}
        assert "sub.ads.example.com" not in targets
        assert "keep.com" in targets

    def test_allow_rules_not_affected(self):
        rules = [
            _make_rule("ads.example.com", mode=Mode.ALLOW),
            _make_rule("ads.example.com", mode=Mode.DENY),
        ]
        allowlist = {"ads.example.com"}
        result = _apply_allowlist(rules, allowlist)
        # ALLOW is kept, DENY is removed
        modes = {r.mode for r in result}
        assert Mode.ALLOW in modes
        assert Mode.DENY not in modes

    def test_empty_allowlist_no_change(self):
        rules = [_make_rule("ads.example.com")]
        result = _apply_allowlist(rules, set())
        assert len(result) == 1


class TestOptimizerWithAllowlist:
    def test_allowlist_applied_during_drain(self):
        config = OptimizerConfig(enable=True)
        allowlist = {"blocked.com"}
        opt = RuleOptimizer(config, allowlist=allowlist)

        opt.feed(_make_rule("blocked.com"))
        opt.feed(_make_rule("kept.com"))
        results = list(opt.drain())

        targets = {r.target for r in results}
        assert "blocked.com" not in targets
        assert "kept.com" in targets
