"""Unit tests for utility functions."""

from __future__ import annotations

import pytest

from adfilter.model import RuleType
from adfilter.util import (
    between,
    commented_lines,
    detect_base_rule,
    normalize_path,
    parse_hosts,
    split_ignore_blank,
    starts_with_any,
    sub_after,
    sub_before,
    sub_between,
)


class TestStartsWithAny:
    def test_matches(self):
        assert starts_with_any("hello world", "he", "wo") is True

    def test_no_match(self):
        assert starts_with_any("hello", "x", "y") is False

    def test_none_input(self):
        assert starts_with_any(None, "a") is False

    def test_empty_prefixes(self):
        assert starts_with_any("hello") is False


class TestBetween:
    def test_matches(self):
        assert between("[Adblock Plus]", "[", "]") is True

    def test_no_match(self):
        assert between("hello", "[", "]") is False

    def test_empty_input(self):
        assert between("", "[", "]") is False


class TestSubBefore:
    def test_basic(self):
        assert sub_before("hello.world", ".") == "hello"

    def test_not_found(self):
        assert sub_before("hello", ".") == ""

    def test_is_last(self):
        assert sub_before("a.b.c", ".", is_last=True) == "a.b"

    def test_empty(self):
        assert sub_before("", ".") == ""


class TestSubAfter:
    def test_basic(self):
        assert sub_after("hello.world", ".") == "world"

    def test_not_found(self):
        assert sub_after("hello", ".") == ""

    def test_is_last(self):
        assert sub_after("a.b.c", ".", is_last=True) == "c"


class TestSubBetween:
    def test_basic(self):
        assert sub_between("[content]", "[", "]") == "content"

    def test_no_start(self):
        assert sub_between("content]", "[", "]") == ""

    def test_empty(self):
        assert sub_between("", "[", "]") == ""


class TestSplitIgnoreBlank:
    def test_basic(self):
        result = split_ignore_blank("a\nb\n\nc", "\n")
        assert result == ["a", "b", "c"]

    def test_empty(self):
        assert split_ignore_blank("", "\n") == []


class TestParseHosts:
    def test_valid_hosts_line(self):
        result = parse_hosts("0.0.0.0 ads.example.com")
        assert result == ("0.0.0.0", "ads.example.com")

    def test_with_tab(self):
        result = parse_hosts("127.0.0.1\ttracker.org")
        assert result == ("127.0.0.1", "tracker.org")

    def test_invalid_too_many_parts(self):
        assert parse_hosts("0.0.0.0 a b c") is None

    def test_invalid_ip(self):
        assert parse_hosts("999.999.999.999 domain.com") is None


class TestDetectBaseRule:
    def test_basic_domain(self):
        assert detect_base_rule("example.com") == RuleType.BASIC

    def test_wildcard(self):
        assert detect_base_rule("*.example.com") == RuleType.WILDCARD

    def test_invalid(self):
        assert detect_base_rule("not a domain!@#$") is None


class TestNormalizePath:
    def test_absolute(self):
        from pathlib import Path

        result = normalize_path("/tmp/file.txt")
        assert result == Path("/tmp/file.txt")

    def test_relative_with_root(self):
        from pathlib import Path

        result = normalize_path("file.txt", root=Path("/opt"))
        assert result == Path("/opt/file.txt")


class TestCommentedLines:
    def test_basic(self):
        result = commented_lines("line1\nline2", "# ")
        assert "# line1" in result
        assert "# line2" in result
