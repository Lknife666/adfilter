"""Unit tests for the Parser (pipeline logic, not full I/O)."""

from __future__ import annotations

import pytest

from adfilter.config import FetcherConfig, ParserConfig
from adfilter.model import Control, Mode, Rule, RuleType, Scope
from adfilter.optimizer import normalize_idn


class TestNormalizeIDN:
    def test_ascii_passthrough(self):
        assert normalize_idn("example.com") == "example.com"

    def test_ascii_lowercase(self):
        assert normalize_idn("Example.COM") == "example.com"

    def test_unicode_to_punycode(self):
        result = normalize_idn("münchen.de")
        assert result.isascii()
        assert "xn--" in result

    def test_empty_string(self):
        assert normalize_idn("") == ""

    def test_already_punycode(self):
        result = normalize_idn("xn--mnchen-3ya.de")
        assert result == "xn--mnchen-3ya.de"

    def test_invalid_idn_fallback(self):
        # Invalid IDN should fall back to lowercase
        result = normalize_idn("bad\x00domain.com")
        assert result == result.lower()


class TestParserConfig:
    def test_defaults(self):
        cfg = ParserConfig()
        assert cfg.min_length == 0
        assert cfg.max_length == 0
        assert cfg.alert_length == 0
        assert cfg.excludes == set()
        assert cfg.incremental_build is False
        assert cfg.progress is False
        assert cfg.json_logs is False

    def test_excludes_set(self):
        cfg = ParserConfig(excludes={"ads.example.com", "tracker.org"})
        assert "ads.example.com" in cfg.excludes
        assert "tracker.org" in cfg.excludes
