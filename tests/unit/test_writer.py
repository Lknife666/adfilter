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



class TestWriteSingbox:
    """Test the _write_singbox JSON assembly function."""

    def test_assembles_valid_json(self, tmp_path):
        from adfilter.writer import _write_singbox

        # Create a temp file with JSON-line fragments
        temp = tmp_path / "input.tmp"
        temp.write_text(
            '{"domain_suffix": ["example.com"]}\n'
            '{"domain": ["exact.example.com"]}\n'
            '{"domain_suffix": ["test.org"]}\n',
            encoding="utf-8",
        )
        output = tmp_path / "output.json"
        _write_singbox(output, temp, "")

        data = json.loads(output.read_text(encoding="utf-8"))
        assert data["version"] == 2
        assert "rules" in data
        # Should have domain_suffix and domain arrays
        all_suffixes = []
        all_domains = []
        for rule in data["rules"]:
            all_suffixes.extend(rule.get("domain_suffix", []))
            all_domains.extend(rule.get("domain", []))
        assert "example.com" in all_suffixes
        assert "test.org" in all_suffixes
        assert "exact.example.com" in all_domains

    def test_skips_comments(self, tmp_path):
        from adfilter.writer import _write_singbox

        temp = tmp_path / "input.tmp"
        temp.write_text(
            '// this is a comment\n'
            '# another comment\n'
            '{"domain_suffix": ["only.com"]}\n',
            encoding="utf-8",
        )
        output = tmp_path / "output.json"
        _write_singbox(output, temp, "")

        data = json.loads(output.read_text(encoding="utf-8"))
        rules = data["rules"]
        assert len(rules) == 1
        assert "only.com" in rules[0]["domain_suffix"]

    def test_deduplicates_domains(self, tmp_path):
        from adfilter.writer import _write_singbox

        temp = tmp_path / "input.tmp"
        temp.write_text(
            '{"domain_suffix": ["dup.com"]}\n'
            '{"domain_suffix": ["dup.com"]}\n'
            '{"domain_suffix": ["unique.com"]}\n',
            encoding="utf-8",
        )
        output = tmp_path / "output.json"
        _write_singbox(output, temp, "")

        data = json.loads(output.read_text(encoding="utf-8"))
        suffixes = data["rules"][0]["domain_suffix"]
        assert suffixes.count("dup.com") == 1  # deduplicated

    def test_header_creates_sidecar(self, tmp_path):
        from adfilter.writer import _write_singbox

        temp = tmp_path / "input.tmp"
        temp.write_text('{"domain": ["x.com"]}\n', encoding="utf-8")
        output = tmp_path / "output.json"
        _write_singbox(output, temp, "# My Header\n# Description\n")

        sidecar = output.with_suffix(output.suffix + ".about.txt")
        assert sidecar.exists()
        assert "My Header" in sidecar.read_text(encoding="utf-8")


class TestWritePlain:
    def test_prepends_header(self, tmp_path):
        from adfilter.writer import _write_plain

        temp = tmp_path / "body.tmp"
        temp.write_text("line1\nline2\nline3\n", encoding="utf-8")
        output = tmp_path / "output.txt"
        _write_plain(output, temp, "# Header\n")

        content = output.read_text(encoding="utf-8")
        assert content.startswith("# Header\n")
        assert "line1\nline2\nline3\n" in content

    def test_no_header(self, tmp_path):
        from adfilter.writer import _write_plain

        temp = tmp_path / "body.tmp"
        temp.write_text("data\n", encoding="utf-8")
        output = tmp_path / "output.txt"
        _write_plain(output, temp, "")

        content = output.read_text(encoding="utf-8")
        assert content == "data\n"
