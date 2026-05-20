"""Tests for the security module."""

from __future__ import annotations

import pytest

from adfilter.security import (
    SSRFError,
    ValidationError,
    is_private_ip,
    mask_secret,
    sanitize_path,
    validate_domain,
    validate_url,
)


class TestIsPrivateIp:
    def test_private_ipv4(self):
        assert is_private_ip("10.0.0.1")
        assert is_private_ip("172.16.0.1")
        assert is_private_ip("192.168.1.1")
        assert is_private_ip("127.0.0.1")

    def test_public_ipv4(self):
        assert not is_private_ip("8.8.8.8")
        assert not is_private_ip("1.1.1.1")

    def test_ipv6_loopback(self):
        assert is_private_ip("::1")

    def test_ipv6_ula(self):
        assert is_private_ip("fc00::1")

    def test_invalid_ip(self):
        assert not is_private_ip("not-an-ip")

    def test_link_local(self):
        assert is_private_ip("169.254.1.1")


class TestValidateUrl:
    def test_valid_https(self):
        url = "https://example.com/rules.txt"
        assert validate_url(url) == url

    def test_valid_http(self):
        url = "http://example.com/rules.txt"
        assert validate_url(url) == url

    def test_empty_url(self):
        with pytest.raises(ValidationError):
            validate_url("")

    def test_too_long_url(self):
        url = "https://example.com/" + "a" * 5000
        with pytest.raises(ValidationError):
            validate_url(url)

    def test_file_scheme_blocked(self):
        with pytest.raises(SSRFError):
            validate_url("file:///etc/passwd")

    def test_ftp_scheme_blocked(self):
        with pytest.raises(SSRFError):
            validate_url("ftp://example.com/file")

    def test_unknown_scheme(self):
        with pytest.raises(SSRFError):
            validate_url("custom://example.com")

    def test_no_hostname(self):
        with pytest.raises(SSRFError):
            validate_url("http://")

    def test_private_ip_target(self):
        with pytest.raises(SSRFError):
            validate_url("http://192.168.1.1/admin")

    def test_localhost_blocked(self):
        with pytest.raises(SSRFError):
            validate_url("http://localhost/api")

    def test_localhost_localdomain_blocked(self):
        with pytest.raises(SSRFError):
            validate_url("http://localhost.localdomain/api")


class TestValidateDomain:
    def test_valid_domain(self):
        assert validate_domain("example.com")
        assert validate_domain("sub.example.com")

    def test_empty_domain(self):
        assert not validate_domain("")

    def test_too_long_domain(self):
        assert not validate_domain("a" * 254)

    def test_single_label(self):
        assert not validate_domain("localhost")

    def test_trailing_dot(self):
        assert validate_domain("example.com.")

    def test_label_starts_with_hyphen(self):
        assert not validate_domain("-example.com")

    def test_label_ends_with_hyphen(self):
        assert not validate_domain("example-.com")

    def test_empty_label(self):
        assert not validate_domain("example..com")

    def test_label_too_long(self):
        assert not validate_domain("a" * 64 + ".com")


class TestSanitizePath:
    def test_removes_traversal(self):
        assert sanitize_path("../etc/passwd") == "etc/passwd"

    def test_removes_null_bytes(self):
        assert sanitize_path("file\x00name.txt") == "filename.txt"

    def test_normalizes_backslash(self):
        assert sanitize_path("path\\to\\file") == "path/to/file"

    def test_removes_dot_segments(self):
        assert sanitize_path("./path/./file") == "path/file"

    def test_normal_path_unchanged(self):
        assert sanitize_path("path/to/file.txt") == "path/to/file.txt"


class TestMaskSecret:
    def test_mask_normal(self):
        assert mask_secret("mysecretkey") == "myse*******"

    def test_mask_short(self):
        assert mask_secret("abc") == "***"

    def test_mask_empty(self):
        assert mask_secret("") == "***"

    def test_mask_custom_visible(self):
        assert mask_secret("mysecretkey", visible_chars=6) == "mysecr*****"
