"""Unit tests for the rule optimizer."""

from __future__ import annotations

import pytest

from adfilter.config import OptimizerConfig
from adfilter.model import Control, Mode, Rule, RuleType, Scope
from adfilter.optimizer import RuleOptimizer, normalize_idn


def _make_rule(
    target: str,
    mode: Mode = Mode.DENY,
    scope: Scope = Scope.DOMAIN,
    rtype: RuleType = RuleType.BASIC,
    controls: set[Control] | None = None,
    source_name: str = "test-source",
) -> Rule:
    return Rule(
        origin=f"||{target}^",
        target=target,
        mode=mode,
        scope=scope,
        type=rtype,
        controls=controls or set(),
        source_name=source_name,
    )


class TestSubdomainCollapse:
    def test_child_collapsed_by_overlay_parent(self):
        config = OptimizerConfig(enable=True, collapse_subdomains=True)
        opt = RuleOptimizer(config)

        parent = _make_rule("example.com", controls={Control.OVERLAY})
        child = _make_rule("sub.example.com")

        opt.feed(parent)
        opt.feed(child)
        results = list(opt.drain())

        targets = {r.target for r in results}
        assert "example.com" in targets
        assert "sub.example.com" not in targets

    def test_no_collapse_without_overlay(self):
        config = OptimizerConfig(enable=True, collapse_subdomains=True)
        opt = RuleOptimizer(config)

        parent = _make_rule("example.com")  # No OVERLAY control
        child = _make_rule("sub.example.com")

        opt.feed(parent)
        opt.feed(child)
        results = list(opt.drain())

        targets = {r.target for r in results}
        assert "example.com" in targets
        assert "sub.example.com" in targets

    def test_deep_nesting_collapsed(self):
        config = OptimizerConfig(enable=True, collapse_subdomains=True)
        opt = RuleOptimizer(config)

        parent = _make_rule("example.com", controls={Control.OVERLAY})
        deep_child = _make_rule("a.b.c.example.com")

        opt.feed(parent)
        opt.feed(deep_child)
        results = list(opt.drain())

        targets = {r.target for r in results}
        assert "example.com" in targets
        assert "a.b.c.example.com" not in targets


class TestAllowShadowElimination:
    def test_deny_dropped_when_allow_exists(self):
        config = OptimizerConfig(enable=True, drop_allow_shadowed_deny=True)
        opt = RuleOptimizer(config)

        deny = _make_rule("example.com", mode=Mode.DENY)
        allow = _make_rule("example.com", mode=Mode.ALLOW)

        opt.feed(deny)
        opt.feed(allow)
        results = list(opt.drain())

        modes = {(r.target, r.mode) for r in results}
        assert ("example.com", Mode.ALLOW) in modes
        assert ("example.com", Mode.DENY) not in modes

    def test_deny_kept_without_matching_allow(self):
        config = OptimizerConfig(enable=True, drop_allow_shadowed_deny=True)
        opt = RuleOptimizer(config)

        deny = _make_rule("ads.example.com", mode=Mode.DENY)
        allow = _make_rule("other.example.com", mode=Mode.ALLOW)

        opt.feed(deny)
        opt.feed(allow)
        results = list(opt.drain())

        targets = {r.target for r in results}
        assert "ads.example.com" in targets


class TestMultiSourceVoting:
    def test_rule_below_threshold_dropped(self):
        config = OptimizerConfig(enable=True, min_source_votes=2)
        opt = RuleOptimizer(config)

        rule1 = _make_rule("only-one.com", source_name="source-a")
        rule2 = _make_rule("popular.com", source_name="source-a")
        rule3 = _make_rule("popular.com", source_name="source-b")

        opt.feed(rule1)
        opt.feed(rule2)
        opt.feed(rule3)
        results = list(opt.drain())

        targets = {r.target for r in results}
        assert "popular.com" in targets
        assert "only-one.com" not in targets

    def test_threshold_of_1_keeps_everything(self):
        config = OptimizerConfig(enable=True, min_source_votes=1)
        opt = RuleOptimizer(config)

        rule = _make_rule("single.com", source_name="only-source")
        opt.feed(rule)
        results = list(opt.drain())
        assert len(results) == 1


class TestIDNNormalization:
    def test_idn_normalized_on_feed(self):
        config = OptimizerConfig(enable=True, normalize_idn=True)
        opt = RuleOptimizer(config)

        rule = Rule(
            origin="||München.de^",
            target="München.de",
            mode=Mode.DENY,
            scope=Scope.DOMAIN,
            type=RuleType.BASIC,
            source_name="test",
        )
        opt.feed(rule)
        results = list(opt.drain())
        assert results[0].target.isascii()
        assert "xn--" in results[0].target

    def test_idn_disabled(self):
        config = OptimizerConfig(enable=True, normalize_idn=False)
        opt = RuleOptimizer(config)

        rule = Rule(
            origin="||München.de^",
            target="München.de",
            mode=Mode.DENY,
            scope=Scope.DOMAIN,
            type=RuleType.BASIC,
            source_name="test",
        )
        opt.feed(rule)
        results = list(opt.drain())
        assert results[0].target == "München.de"


class TestCombinedOptimizations:
    def test_all_optimizations_together(self):
        config = OptimizerConfig(
            enable=True,
            collapse_subdomains=True,
            drop_allow_shadowed_deny=True,
            min_source_votes=1,
            normalize_idn=True,
        )
        opt = RuleOptimizer(config)

        # parent overlay
        opt.feed(_make_rule("example.com", controls={Control.OVERLAY}, source_name="a"))
        # child (should be collapsed)
        opt.feed(_make_rule("sub.example.com", source_name="a"))
        # allow + deny (deny should be dropped)
        opt.feed(_make_rule("shadowed.com", mode=Mode.DENY, source_name="a"))
        opt.feed(_make_rule("shadowed.com", mode=Mode.ALLOW, source_name="a"))
        # normal rule (kept)
        opt.feed(_make_rule("normal.com", source_name="a"))

        results = list(opt.drain())
        targets = {r.target for r in results}

        assert "example.com" in targets
        assert "sub.example.com" not in targets
        assert ("shadowed.com", Mode.DENY) not in {(r.target, r.mode) for r in results}
        assert "normal.com" in targets
