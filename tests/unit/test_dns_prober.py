"""Unit tests for the DNS prober — cache behavior and resolution logic."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from adfilter.config import DnsProbeConfig, DnsProvider
from adfilter.dns_prober import DnsProber


@pytest.fixture
def prober_config():
    return DnsProbeConfig(
        enable=True,
        timeout_seconds=2.0,
        cache_ttl_min_seconds=10,
        cache_ttl_max_seconds=60,
        cache_negative_ttl_seconds=5,
        provider=[DnsProvider(host="8.8.8.8")],
    )


class TestDnsProber:
    @pytest.mark.asyncio
    async def test_empty_domain_returns_true(self, prober_config):
        prober = DnsProber(prober_config)
        result = await prober.lookup("")
        assert result is True
        await prober.close()

    @pytest.mark.asyncio
    async def test_successful_lookup(self, prober_config):
        prober = DnsProber(prober_config)
        # Mock the resolver to return a result
        mock_result = [MagicMock()]
        for resolver in prober._resolvers:
            resolver.query = AsyncMock(return_value=mock_result)

        result = await prober.lookup("example.com")
        assert result is True
        await prober.close()

    @pytest.mark.asyncio
    async def test_nxdomain_returns_false(self, prober_config):
        import aiodns

        prober = DnsProber(prober_config)
        # Mock: NXDOMAIN for both A and AAAA
        for resolver in prober._resolvers:
            resolver.query = AsyncMock(
                side_effect=aiodns.error.DNSError(aiodns.error.ARES_ENOTFOUND, "not found")
            )

        result = await prober.lookup("nonexistent.invalid")
        assert result is False
        await prober.close()

    @pytest.mark.asyncio
    async def test_cache_hit(self, prober_config):
        prober = DnsProber(prober_config)
        mock_result = [MagicMock()]
        for resolver in prober._resolvers:
            resolver.query = AsyncMock(return_value=mock_result)

        # First call populates cache
        await prober.lookup("cached.com")
        # Second call should hit cache
        await prober.lookup("cached.com")

        stats = prober.stats()
        assert stats["cache_hits"] == 1
        assert stats["total_queries"] == 1  # Only one actual DNS query
        await prober.close()

    @pytest.mark.asyncio
    async def test_transient_failure_assumes_exists(self, prober_config):
        """Transient DNS errors should assume the domain exists to avoid over-pruning."""
        import aiodns

        prober = DnsProber(prober_config)
        # Simulate a transient error (not NXDOMAIN)
        for resolver in prober._resolvers:
            resolver.query = AsyncMock(side_effect=aiodns.error.DNSError(99, "network unreachable"))

        result = await prober.lookup("flaky.example.com")
        assert result is True  # Conservative: assume exists
        await prober.close()

    @pytest.mark.asyncio
    async def test_stats(self, prober_config):
        prober = DnsProber(prober_config)
        stats = prober.stats()
        assert stats["total_queries"] == 0
        assert stats["cache_hits"] == 0
        assert stats["cache_size"] == 0
        await prober.close()
