"""Tests for the data package initialization."""

from __future__ import annotations

import pytest

from adfilter.data import load_preset, load_source_catalog


class TestLoadSourceCatalog:
    def test_returns_dict(self):
        result = load_source_catalog()
        assert isinstance(result, dict)

    def test_has_sources_key(self):
        result = load_source_catalog()
        assert "sources" in result


class TestLoadPreset:
    def test_load_global_preset(self):
        result = load_preset("global")
        assert isinstance(result, dict)

    def test_load_cn_preset(self):
        result = load_preset("cn")
        assert isinstance(result, dict)

    def test_load_jp_preset(self):
        result = load_preset("jp")
        assert isinstance(result, dict)

    def test_nonexistent_preset_raises(self):
        with pytest.raises(FileNotFoundError):
            load_preset("nonexistent_region")
