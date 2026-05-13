"""Tests for utility functions."""

from __future__ import annotations

import pytest

from adfilter.model import RuleType
from adfilter.util import (
    between,
    detect_base_rule,
    parse_hosts,
    split_ignore_blank,
    starts_with_any,
    sub_after,
    sub_before,
    sub_between,
)


class TestStartsWithAny:
    def test_match_first(self):
        assert starts_with_any("hello", "he", "wo") is True

    def test_match_second(self):
        assert starts_with_any("world", "he", "wo") is True

    def test_no_match(self):
        assert starts_with_any("test", "he", "wo") is False

    def test_empty_string(self):
        assert starts_with_any("", "he") is False

    def test_none_input(self):
        assert starts_with_any(None, "he") is False

    def test_no_prefixes(self):
        assert starts_with_any("test") is False


class TestBetween:
    def test_valid(self):
        assert between("[Adblock Plus]", "[", "]") is True

    def test_no_start(self):
        assert between("Adblock Plus]", "[", "]") is False

    def test_no_end(self):
        assert between("[Adblock Plus", "[", "]") is False

    def test_empty(self):
        assert between("", "[", "]") is False


class TestSubBefore:
    def test_basic(self):
        assert sub_before("hello/world", "/") == "hello"

    def test_not_found(self):
        assert sub_before("hello", "/") == ""

    def test_empty(self):
        assert sub_before("", "/") == ""

    def test_last(self):
        assert sub_before("a/b/c", "/", is_last=True) == "a/b"


class TestSubAfter:
    def test_basic(self):
        assert sub_after("hello/world", "/") == "world"

    def test_not_found(self):
        assert sub_after("hello", "/") == ""

    def test_empty(self):
        assert sub_after("", "/") == ""

    def test_last(self):
        assert sub_after("address=/domain/0.0.0.0", "address=/", is_last=True) == "domain/0.0.0.0"


class TestSubBetween:
    def test_basic(self):
        assert sub_between("'hello'", "'", "'") == "hello"

    def test_no_match(self):
        assert sub_between("hello", "'", "'") == ""

    def test_empty(self):
        assert sub_between("", "'", "'") == ""


class TestSplitIgnoreBlank:
    def test_basic(self):
        assert split_ignore_blank("a/b/c", "/") == ["a", "b", "c"]

    def test_empty_parts(self):
        assert split_ignore_blank("a//b", "/") == ["a", "b"]

    def test_empty_input(self):
        assert split_ignore_blank("", "/") == []

    def test_whitespace_parts_skipped(self):
        assert split_ignore_blank("a/ /b", "/") == ["a", "b"]


class TestParseHosts:
    def test_valid_ipv4(self):
        result = parse_hosts("0.0.0.0 ads.example.com")
        assert result == ("0.0.0.0", "ads.example.com")

    def test_tab_separated(self):
        result = parse_hosts("127.0.0.1\ttracker.org")
        assert result == ("127.0.0.1", "tracker.org")

    def test_invalid_ip(self):
        assert parse_hosts("notanip example.com") is None

    def test_too_many_parts(self):
        assert parse_hosts("0.0.0.0 a.com b.com") is None

    def test_invalid_domain(self):
        # single-label domains without TLD don't match PATTERN_DOMAIN
        assert parse_hosts("0.0.0.0 localhost") is None

    def test_empty(self):
        assert parse_hosts("") is None


class TestDetectBaseRule:
    def test_basic_domain(self):
        assert detect_base_rule("example.com") == RuleType.BASIC

    def test_subdomain(self):
        assert detect_base_rule("sub.example.com") == RuleType.BASIC

    def test_wildcard(self):
        assert detect_base_rule("*.example.com") == RuleType.WILDCARD

    def test_not_a_domain(self):
        assert detect_base_rule("not a domain at all") is None

    def test_leading_dot(self):
        # Leading dot causes content != temp after strip, returns WILDCARD
        assert detect_base_rule(".example.com") == RuleType.WILDCARD

    def test_trailing_dot(self):
        # Trailing dot causes content != temp after strip, returns WILDCARD
        assert detect_base_rule("example.com.") == RuleType.WILDCARD
