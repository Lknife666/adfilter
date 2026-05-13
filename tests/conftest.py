"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def sample_easylist() -> str:
    return (FIXTURES_DIR / "sample_easylist.txt").read_text(encoding="utf-8")


@pytest.fixture
def sample_hosts() -> str:
    return (FIXTURES_DIR / "sample_hosts.txt").read_text(encoding="utf-8")


@pytest.fixture
def sample_clash() -> str:
    return (FIXTURES_DIR / "sample_clash.yaml").read_text(encoding="utf-8")


@pytest.fixture
def sample_dnsmasq() -> str:
    return (FIXTURES_DIR / "sample_dnsmasq.conf").read_text(encoding="utf-8")
