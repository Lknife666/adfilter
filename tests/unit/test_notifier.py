"""Unit tests for the notifier system (v0.3)."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from adfilter.config import NotifierChannel, NotifierConfig
from adfilter.notifier.base import NotifyPayload, _resolve_env, _create_notifier
from adfilter.stats import BuildReport, OutputReport


class TestNotifyPayload:
    def test_success_summary(self):
        report = BuildReport(elapsed_ms=2500, fingerprint="abc123def456")
        report.outputs = [
            OutputReport(name="dns.txt", type="dns", count=1000, bytes=50000, path="/rule/dns.txt"),
            OutputReport(name="clash.yaml", type="clash", count=800, bytes=40000, path="/rule/clash.yaml"),
        ]
        payload = NotifyPayload(success=True, report=report)
        summary = payload.summary()
        assert "completed" in summary.lower() or "✅" in summary
        assert "1,800" in summary  # total rules
        assert "2" in summary  # total files

    def test_failure_summary(self):
        payload = NotifyPayload(success=False, report=None, error_message="timeout")
        summary = payload.summary()
        assert "failed" in summary.lower() or "❌" in summary
        assert "timeout" in summary

    def test_no_report_summary(self):
        payload = NotifyPayload(success=True, report=None)
        summary = payload.summary()
        assert "completed" in summary.lower()


class TestResolveEnv:
    def test_env_var_resolved(self):
        with patch.dict(os.environ, {"MY_TOKEN": "secret123"}):
            assert _resolve_env("${MY_TOKEN}") == "secret123"

    def test_missing_env_var(self):
        assert _resolve_env("${NONEXISTENT_VAR_XYZ}") == ""

    def test_plain_value_passthrough(self):
        assert _resolve_env("plain-value") == "plain-value"


class TestCreateNotifier:
    def test_telegram_with_credentials(self):
        channel = NotifierChannel(type="telegram", bot_token="token123", chat_id="12345")
        notifier = _create_notifier(channel)
        assert notifier is not None

    def test_telegram_missing_token(self):
        channel = NotifierChannel(type="telegram", bot_token="", chat_id="12345")
        notifier = _create_notifier(channel)
        assert notifier is None

    def test_discord_with_url(self):
        channel = NotifierChannel(type="discord", webhook_url="https://discord.com/api/webhooks/test")
        notifier = _create_notifier(channel)
        assert notifier is not None

    def test_discord_missing_url(self):
        channel = NotifierChannel(type="discord", webhook_url="")
        notifier = _create_notifier(channel)
        assert notifier is None

    def test_wecom_with_key(self):
        channel = NotifierChannel(type="wecom", webhook_key="key123")
        notifier = _create_notifier(channel)
        assert notifier is not None

    def test_unknown_type(self):
        channel = NotifierChannel(type="unknown_service")
        notifier = _create_notifier(channel)
        assert notifier is None
