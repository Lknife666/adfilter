"""Unit tests for the writer module — header building and singbox assembly."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from adfilter.config import OutputItem
from adfilter.constants import RuleSet
from adfilter.writer import (
    build_header,
    input_fingerprint,
    load_build_cache,
    save_build_cache,
)


class TestInputFingerprint:
    def test_deterministic(self):
        payload = [("source-a", "http://a.com"), ("source-b", "http://b.com")]
        h1 = input_fingerprint(payload)
        h2 = input_fingerprint(payload)
        assert h1 == h2

    def test_order_independent(self):
        """Fingerprint should be same regardless of input order (sorted internally)."""
        p1 = [("a", "http://a"), ("b", "http://b")]
        p2 = [("b", "http://b"), ("a", "http://a")]
        assert input_fingerprint(p1) == input_fingerprint(p2)

    def test_different_inputs_different_hash(self):
        p1 = [("a", "http://a")]
        p2 = [("b", "http://b")]
        assert input_fingerprint(p1) != input_fingerprint(p2)

    def test_empty_payload(self):
        h = input_fingerprint([])
        assert len(h) == 64  # SHA-256 hex digest


class TestBuildCache:
    def test_save_and_load(self, tmp_path):
        cache_file = tmp_path / "cache.json"
        data = {"fingerprint": "abc123", "extra": True}
        save_build_cache(cache_file, data)
        loaded = load_build_cache(cache_file)
        assert loaded == data

    def test_load_missing_file(self, tmp_path):
        cache_file = tmp_path / "nonexistent.json"
        assert load_build_cache(cache_file) == {}

    def test_load_invalid_json(self, tmp_path):
        cache_file = tmp_path / "broken.json"
        cache_file.write_text("not valid json {{{{", encoding="utf-8")
        assert load_build_cache(cache_file) == {}


class TestBuildHeader:
    def test_header_with_placeholders(self):
        item = OutputItem(name="dns.txt", type=RuleSet.DNS, desc="Test DNS")
        header = build_header(item, "Generated: ${date}\nName: ${name}\nDesc: ${desc}\nTotal: ${total}", 100)
        assert "Name: dns.txt" in header
        assert "Desc: Test DNS" in header
        assert "Total: 100" in header

    def test_empty_header(self):
        item = OutputItem(name="dns.txt", type=RuleSet.DNS)
        header = build_header(item, "", 0)
        # DNS handler has no head_format, so header should be empty or minimal
        assert header == ""

    def test_clash_includes_payload_head(self):
        item = OutputItem(name="clash.yaml", type=RuleSet.CLASH, desc="Clash")
        header = build_header(item, "Header: ${name}", 50)
        # Clash handler's head_format returns "payload:"
        assert "payload:" in header
