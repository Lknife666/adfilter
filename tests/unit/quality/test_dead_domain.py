"""Tests for DeadDomainDetector (unit tests without actual DNS queries)."""

from __future__ import annotations

import json
import time

import pytest

from adfilter.quality.dead_domain_detector import DeadDomainConfig, DiskCache


class TestDiskCache:
    def test_set_and_get(self, tmp_path):
        cache = DiskCache(str(tmp_path / "cache"), ttl_hours=24)
        cache.set("example.com", True)
        assert cache.get("example.com") is True

    def test_expired_entry_returns_none(self, tmp_path):
        cache = DiskCache(str(tmp_path / "cache"), ttl_hours=0)  # Immediate expiry
        cache._data["old.com"] = (True, time.time() - 10)
        assert cache.get("old.com") is None

    def test_missing_entry_returns_none(self, tmp_path):
        cache = DiskCache(str(tmp_path / "cache"), ttl_hours=24)
        assert cache.get("nothere.com") is None

    def test_save_and_reload(self, tmp_path):
        cache_dir = str(tmp_path / "cache")
        cache1 = DiskCache(cache_dir, ttl_hours=24)
        cache1.set("saved.com", False)
        cache1.save()

        cache2 = DiskCache(cache_dir, ttl_hours=24)
        assert cache2.get("saved.com") is False

    def test_corrupted_cache_handled(self, tmp_path):
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        (cache_dir / "dns_cache.json").write_text("invalid json{{{", encoding="utf-8")
        cache = DiskCache(str(cache_dir), ttl_hours=24)
        # Should not raise, starts empty
        assert cache.get("any.com") is None


class TestDeadDomainConfig:
    def test_defaults(self):
        config = DeadDomainConfig()
        assert config.enable is False
        assert config.concurrency == 100
        assert config.timeout_seconds == 3.0
        assert config.min_consecutive_failures == 3
        assert config.auto_remove is False
        assert len(config.nameservers) == 3

    def test_custom_config(self):
        config = DeadDomainConfig(
            enable=True,
            concurrency=50,
            timeout_seconds=5.0,
            min_consecutive_failures=5,
            nameservers=["8.8.8.8"],
        )
        assert config.concurrency == 50
        assert config.min_consecutive_failures == 5
