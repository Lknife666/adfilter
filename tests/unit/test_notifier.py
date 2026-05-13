"""Unit tests for the notifier system — registry and payload formatting."""

from __future__ import annotations

import pytest

from adfilter.notifier.base import (
    Notifier,
    NotifyPayload,
    _resolve_env,
    get_notifier_class,
    register_notifier,
)
from adfilter.stats import BuildReport, OutputReport


class TestNotifyPayload:
    def test_failure_summary(self):
        payload = NotifyPayload(success=False, report=None, error_message="timeout")
        summary = payload.summary()
        assert "failed" in summary.lower() or "❌" in summary
        assert "timeout" in summary

    def test_success_summary_no_report(self):
        payload = NotifyPayload(success=True, report=None)
        summary = payload.summary()
        assert "completed" in summary.lower() or "✅" in summary

    def test_success_summary_with_report(self):
        report = BuildReport(
            elapsed_ms=2500,
            fingerprint="abcdef123456789",
            outputs=[
                OutputReport(name="dns.txt", type="dns", count=1000, bytes=50000, path="/out/dns.txt"),
                OutputReport(name="clash.yaml", type="clash", count=800, bytes=30000, path="/out/clash.yaml"),
            ],
        )
        payload = NotifyPayload(success=True, report=report)
        summary = payload.summary()
        assert "1,800" in summary  # total rules
        assert "2" in summary      # total files
        assert "2500" in summary   # elapsed
        assert "abcdef123456" in summary  # fingerprint truncated

    def test_success_summary_empty_outputs(self):
        report = BuildReport(elapsed_ms=100, outputs=[])
        payload = NotifyPayload(success=True, report=report)
        summary = payload.summary()
        assert "0" in summary


class TestResolveEnv:
    def test_resolves_env_var(self, monkeypatch):
        monkeypatch.setenv("MY_TOKEN", "secret123")
        assert _resolve_env("${MY_TOKEN}") == "secret123"

    def test_missing_env_var_returns_empty(self, monkeypatch):
        monkeypatch.delenv("NONEXISTENT_VAR", raising=False)
        assert _resolve_env("${NONEXISTENT_VAR}") == ""

    def test_plain_value_passthrough(self):
        assert _resolve_env("just-a-string") == "just-a-string"

    def test_partial_syntax_passthrough(self):
        assert _resolve_env("${INCOMPLETE") == "${INCOMPLETE"
        assert _resolve_env("INCOMPLETE}") == "INCOMPLETE}"


class TestNotifierRegistry:
    def test_builtin_telegram_registered(self):
        # Importing the notifier package triggers registration
        import adfilter.notifier  # noqa: F401
        cls = get_notifier_class("telegram")
        assert cls is not None
        assert issubclass(cls, Notifier)

    def test_builtin_discord_registered(self):
        import adfilter.notifier  # noqa: F401
        cls = get_notifier_class("discord")
        assert cls is not None

    def test_builtin_wecom_registered(self):
        import adfilter.notifier  # noqa: F401
        cls = get_notifier_class("wecom")
        assert cls is not None

    def test_unknown_type_returns_none(self):
        cls = get_notifier_class("unknown_channel_xyz")
        assert cls is None

    def test_custom_registration(self):
        class CustomNotifier(Notifier):
            async def send(self, payload: NotifyPayload) -> bool:
                return True

        register_notifier("custom_test", CustomNotifier)
        assert get_notifier_class("custom_test") is CustomNotifier
