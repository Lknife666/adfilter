"""Unit tests for HTTP fetcher — SSRF protection and cache logic."""

from __future__ import annotations

import pytest

from adfilter.fetcher.http import SSRFError, _check_url_scheme, _is_private_ip


class TestSSRFProtection:
    """Tests for the SSRF protection guards."""

    def test_blocks_localhost_hostname(self):
        with pytest.raises(SSRFError):
            _check_url_scheme("http://localhost/list.txt")

    def test_blocks_localhost_localdomain(self):
        with pytest.raises(SSRFError):
            _check_url_scheme("http://localhost.localdomain/list.txt")

    def test_blocks_private_ip_literal_10(self):
        with pytest.raises(SSRFError):
            _check_url_scheme("http://10.0.1.5/rules.txt")

    def test_blocks_private_ip_literal_172_16(self):
        with pytest.raises(SSRFError):
            _check_url_scheme("http://172.16.0.1/rules.txt")

    def test_blocks_private_ip_literal_192_168(self):
        with pytest.raises(SSRFError):
            _check_url_scheme("http://192.168.1.100/rules.txt")

    def test_blocks_link_local_ip_literal(self):
        with pytest.raises(SSRFError):
            _check_url_scheme("http://169.254.169.254/latest")

    def test_blocks_ipv6_loopback_literal(self):
        with pytest.raises(SSRFError):
            _check_url_scheme("http://[::1]/rules.txt")

    def test_blocks_ipv6_ula_literal(self):
        with pytest.raises(SSRFError):
            _check_url_scheme("http://[fd12:3456:789a::1]/rules.txt")

    def test_blocks_file_scheme(self):
        with pytest.raises(SSRFError):
            _check_url_scheme("file:///etc/passwd")

    def test_blocks_ftp_scheme(self):
        with pytest.raises(SSRFError):
            _check_url_scheme("ftp://evil.com/payload")

    def test_allows_public_domain(self):
        # Should NOT raise — domain names pass scheme check
        _check_url_scheme("http://example.com/list.txt")

    def test_allows_https(self):
        _check_url_scheme("https://raw.githubusercontent.com/user/repo/main/list.txt")

    def test_allows_public_ip_literal(self):
        _check_url_scheme("http://93.184.216.34/list.txt")

    def test_no_hostname_raises(self):
        with pytest.raises(SSRFError):
            _check_url_scheme("http:///path/only")

    def test_is_private_ip_detects_private(self):
        assert _is_private_ip("127.0.0.1") is True
        assert _is_private_ip("10.0.0.1") is True
        assert _is_private_ip("172.16.0.1") is True
        assert _is_private_ip("192.168.1.1") is True
        assert _is_private_ip("169.254.169.254") is True
        assert _is_private_ip("100.64.0.1") is True  # CGNAT
        assert _is_private_ip("::1") is True

    def test_is_private_ip_allows_public(self):
        assert _is_private_ip("8.8.8.8") is False
        assert _is_private_ip("93.184.216.34") is False
        assert _is_private_ip("2606:2800:220:1:248:1893:25c8:1946") is False

    def test_is_private_ip_invalid_returns_false(self):
        assert _is_private_ip("not-an-ip") is False


class TestFetcherFactory:
    """Test fetcher/factory.py — detect_handle_type and get_fetcher."""

    def test_detect_http_url(self):
        from adfilter.constants import HandleType
        from adfilter.fetcher.factory import detect_handle_type

        assert detect_handle_type("https://example.com/list.txt") == HandleType.REMOTE
        assert detect_handle_type("http://example.com/list.txt") == HandleType.REMOTE
        assert detect_handle_type("HTTP://EXAMPLE.COM") == HandleType.REMOTE

    def test_detect_local_path(self):
        from adfilter.constants import HandleType
        from adfilter.fetcher.factory import detect_handle_type

        assert detect_handle_type("/tmp/rules.txt") == HandleType.LOCAL
        assert detect_handle_type("./relative/path.txt") == HandleType.LOCAL
        assert detect_handle_type("file.txt") == HandleType.LOCAL

    def test_get_fetcher_remote(self):
        from adfilter.config import FetcherConfig
        from adfilter.constants import HandleType
        from adfilter.fetcher.factory import get_fetcher
        from adfilter.fetcher.http import HttpFetcher

        config = FetcherConfig()
        fetcher = get_fetcher(HandleType.REMOTE, config)
        assert isinstance(fetcher, HttpFetcher)

    def test_get_fetcher_local(self):
        from adfilter.config import FetcherConfig
        from adfilter.constants import HandleType
        from adfilter.fetcher.factory import get_fetcher
        from adfilter.fetcher.local import LocalFetcher

        config = FetcherConfig()
        fetcher = get_fetcher(HandleType.LOCAL, config)
        assert isinstance(fetcher, LocalFetcher)


class TestLocalFetcher:
    """Test fetcher/local.py."""

    @pytest.mark.asyncio
    async def test_reads_file_lines(self, tmp_path):
        from adfilter.config import LocalFetcherConfig
        from adfilter.fetcher.local import LocalFetcher

        f = tmp_path / "rules.txt"
        f.write_text("line1\nline2\nline3\n", encoding="utf-8")

        fetcher = LocalFetcher(LocalFetcherConfig())
        lines = []
        async for line in fetcher.fetch(str(f)):
            lines.append(line)

        assert lines == ["line1", "line2", "line3"]

    @pytest.mark.asyncio
    async def test_strips_crlf(self, tmp_path):
        from adfilter.config import LocalFetcherConfig
        from adfilter.fetcher.local import LocalFetcher

        f = tmp_path / "rules.txt"
        f.write_bytes(b"line1\r\nline2\r\n")

        fetcher = LocalFetcher(LocalFetcherConfig())
        lines = []
        async for line in fetcher.fetch(str(f)):
            lines.append(line)

        assert lines == ["line1", "line2"]
