"""Tests for dead domain detector."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from adfilter.quality.dead_domain_detector import DeadDomainDetector, DomainCheckResult


class TestDeadDomainDetector:
    def test_init_defaults(self):
        detector = DeadDomainDetector()
        assert detector.timeout == 5.0
        assert detector.max_concurrency == 50
        assert detector.dead_count == 0
        assert detector.total_checked == 0

    def test_get_dead_domains_empty(self):
        detector = DeadDomainDetector()
        assert detector.get_dead_domains() == []

    def test_get_live_domains_empty(self):
        detector = DeadDomainDetector()
        assert detector.get_live_domains() == []


class TestDomainCheckResult:
    def test_dead_result(self):
        r = DomainCheckResult(domain="dead.example.com", is_dead=True, reason="NXDOMAIN")
        assert r.is_dead is True
        assert r.reason == "NXDOMAIN"

    def test_live_result(self):
        r = DomainCheckResult(domain="live.example.com", is_dead=False)
        assert r.is_dead is False
        assert r.reason == ""


class TestDeadDomainDetectorAsync:
    @pytest.mark.asyncio
    async def test_check_domains_with_mock(self):
        detector = DeadDomainDetector(timeout=1.0, max_concurrency=5)

        import socket

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.getaddrinfo = AsyncMock(side_effect=socket.gaierror("NXDOMAIN"))
            results = await detector.check_domains(["dead.example.invalid"])
            assert len(results) == 1
            assert results[0].is_dead is True

    @pytest.mark.asyncio
    async def test_check_domains_live(self):
        detector = DeadDomainDetector(timeout=1.0)

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.getaddrinfo = AsyncMock(
                return_value=[("AF_INET", None, None, None, ("1.2.3.4", 0))]
            )
            results = await detector.check_domains(["example.com"])
            assert len(results) == 1
            assert results[0].is_dead is False
