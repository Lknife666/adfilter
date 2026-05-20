"""Tests for the plugin discovery system (v0.4)."""

from __future__ import annotations

import pytest

from adfilter.handler.base import Handler, discover_plugins, get_handler, _REGISTRY
from adfilter.constants import RuleSet


class TestPluginDiscovery:
    def test_all_builtin_handlers_registered(self):
        """All 12 built-in handlers should be registered."""
        expected = {
            RuleSet.EASYLIST,
            RuleSet.DNS,
            RuleSet.DNSMASQ,
            RuleSet.SMARTDNS,
            RuleSet.CLASH,
            RuleSet.HOSTS,
            RuleSet.SURGE,
            RuleSet.SINGBOX,
            RuleSet.MIKROTIK,
            RuleSet.UNBOUND,
            RuleSet.QUANTUMULT,
            RuleSet.LOON,
        }
        assert expected.issubset(set(_REGISTRY.keys()))

    def test_discover_plugins_doesnt_crash(self):
        """discover_plugins should not crash even with no external plugins."""
        # Just verify it runs without error
        discover_plugins()

    def test_get_handler_quantumult(self):
        handler = get_handler(RuleSet.QUANTUMULT)
        assert handler is not None
        assert handler.rule_set == RuleSet.QUANTUMULT

    def test_get_handler_loon(self):
        handler = get_handler(RuleSet.LOON)
        assert handler is not None
        assert handler.rule_set == RuleSet.LOON

    def test_get_handler_unknown_raises(self):
        with pytest.raises(ValueError, match="no handler registered"):
            get_handler("nonexistent_format")  # type: ignore[arg-type]
