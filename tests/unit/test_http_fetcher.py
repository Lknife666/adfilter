"""Unit tests for HTTP fetcher — SSRF protection and cache logic."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from adfilter.fetcher.http import SSRFError, _check_ssrf


class TestSSRFProtection:
    """Tests for the _check_ssrf guard."""

    def test_blocks_localhost_127(self):
        with patch("socket.getaddrinfo", return_value=[
            (2, 1, 6, "", ("127.0.0.1", 0)),
        ]):
            with pytest.raises(SSRFError) as exc_info:
                _check_ssrf("http://localhost/list.txt")
            assert "127.0.0.1" in str(exc_info.value)

    def test_blocks_private_10_network(self):
        with patch("socket.getaddrinfo", return_value=[
            (2, 1, 6, "", ("10.0.1.5", 0)),
        ]):
            with pytest.raises(SSRFError):
                _check_ssrf("http://internal.corp/rules.txt")

    def test_blocks_private_172_16_network(self):
        with patch("socket.getaddrinfo", return_value=[
            (2, 1, 6, "", ("172.16.0.1", 0)),
        ]):
            with pytest.raises(SSRFError):
                _check_ssrf("http://private.lan/rules.txt")

    def test_blocks_private_192_168_network(self):
        with patch("socket.getaddrinfo", return_value=[
            (2, 1, 6, "", ("192.168.1.100", 0)),
        ]):
            with pytest.raises(SSRFError):
                _check_ssrf("http://router.local/rules.txt")

    def test_blocks_link_local(self):
        with patch("socket.getaddrinfo", return_value=[
            (2, 1, 6, "", ("169.254.169.254", 0)),
        ]):
            with pytest.raises(SSRFError):
                _check_ssrf("http://metadata.internal/latest")

    def test_blocks_ipv6_loopback(self):
        with patch("socket.getaddrinfo", return_value=[
            (10, 1, 6, "", ("::1", 0, 0, 0)),
        ]):
            with pytest.raises(SSRFError):
                _check_ssrf("http://[::1]/rules.txt")

    def test_blocks_ipv6_ula(self):
        with patch("socket.getaddrinfo", return_value=[
            (10, 1, 6, "", ("fd12:3456:789a::1", 0, 0, 0)),
        ]):
            with pytest.raises(SSRFError):
                _check_ssrf("http://[fd12:3456:789a::1]/rules.txt")

    def test_allows_public_ip(self):
        with patch("socket.getaddrinfo", return_value=[
            (2, 1, 6, "", ("93.184.216.34", 0)),
        ]):
            # Should NOT raise
            _check_ssrf("http://example.com/list.txt")

    def test_allows_public_ipv6(self):
        with patch("socket.getaddrinfo", return_value=[
            (10, 1, 6, "", ("2606:2800:220:1:248:1893:25c8:1946", 0, 0, 0)),
        ]):
            _check_ssrf("http://example.com/list.txt")

    def test_dns_failure_passes_through(self):
        """If DNS resolution fails, let aiohttp handle it later."""
        import socket
        with patch("socket.getaddrinfo", side_effect=socket.gaierror("DNS failed")):
            # Should NOT raise — let the actual fetch handle DNS errors
            _check_ssrf("http://nonexistent.example.com/rules.txt")

    def test_no_hostname_raises(self):
        with pytest.raises(SSRFError):
            _check_ssrf("http:///path/only")



class TestFetcherFactory:
    """Test fetcher/factory.py — detect_handle_type and get_fetcher."""

    def test_detect_http_url(self):
        from adfilter.fetcher.factory import detect_handle_type
        from adfilter.constants import HandleType

        assert detect_handle_type("https://example.com/list.txt") == HandleType.REMOTE
        assert detect_handle_type("http://example.com/list.txt") == HandleType.REMOTE
        assert detect_handle_type("HTTP://EXAMPLE.COM") == HandleType.REMOTE

    def test_detect_local_path(self):
        from adfilter.fetcher.factory import detect_handle_type
        from adfilter.constants import HandleType

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
