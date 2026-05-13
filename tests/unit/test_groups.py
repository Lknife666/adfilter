"""Unit tests for grouped/categorized output (v0.3)."""

from __future__ import annotations

import pytest

from adfilter.config import InputConfig, InputItem, OutputItem
from adfilter.constants import RuleSet
from adfilter.model import Mode, Rule, RuleType, Scope


class TestInputGrouping:
    def test_groups_preserved_from_rule_dict(self):
        items = [
            InputItem(name="src-a", type=RuleSet.EASYLIST, path="http://a.com/list.txt"),
            InputItem(name="src-b", type=RuleSet.EASYLIST, path="http://b.com/list.txt"),
        ]
        cfg = InputConfig(rule={"ads": items})
        # All items should have group="ads"
        for item in cfg.input:
            assert item.group == "ads"

    def test_explicit_group_not_overridden(self):
        item = InputItem(name="src-a", type=RuleSet.EASYLIST, path="http://a.com/list.txt", group="custom")
        cfg = InputConfig(rule={"ads": [item]})
        for item in cfg.input:
            assert item.group == "custom"


class TestOutputGroupFiltering:
    def test_output_with_groups_config(self):
        out = OutputItem(name="ads.dns.txt", type=RuleSet.DNS, groups=["ads"])
        assert out.groups == ["ads"]

    def test_output_without_groups_accepts_all(self):
        out = OutputItem(name="dns.txt", type=RuleSet.DNS)
        assert out.groups == []
