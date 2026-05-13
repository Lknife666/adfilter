"""Notifier base and dispatcher."""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..config import NotifierChannel, NotifierConfig
from ..stats import BuildReport

log = logging.getLogger(__name__)


@dataclass
class NotifyPayload:
    """Data passed to notifiers."""
    success: bool
    report: BuildReport | None
    error_message: str = ""
    repository: str = ""

    def summary(self) -> str:
        if not self.success:
            return f"❌ adfilter build failed\n{self.error_message}"
        if self.report is None:
            return "✅ adfilter build completed"
        total_rules = sum(o.count for o in self.report.outputs)
        total_files = len(self.report.outputs)
        elapsed = self.report.elapsed_ms
        lines = [
            "✅ adfilter build completed",
            f"Rules: {total_rules:,}",
            f"Files: {total_files}",
            f"Time: {elapsed}ms",
        ]
        if self.report.fingerprint:
            lines.append(f"Fingerprint: {self.report.fingerprint[:12]}")
        return "\n".join(lines)


class Notifier(ABC):
    """Abstract notifier."""

    @abstractmethod
    async def send(self, payload: NotifyPayload) -> bool:
        """Send notification. Return True on success."""


def _resolve_env(value: str) -> str:
    """Resolve ${VAR} style environment variable references."""
    if value.startswith("${") and value.endswith("}"):
        env_name = value[2:-1]
        return os.environ.get(env_name, "")
    return value


def _create_notifier(channel: NotifierChannel) -> Notifier | None:
    """Factory: create notifier from channel config."""
    match channel.type:
        case "telegram":
            from .telegram import TelegramNotifier
            token = _resolve_env(channel.bot_token)
            chat_id = _resolve_env(channel.chat_id)
            if not token or not chat_id:
                log.warning("telegram notifier: missing bot_token or chat_id")
                return None
            return TelegramNotifier(bot_token=token, chat_id=chat_id)
        case "discord":
            from .discord import DiscordNotifier
            url = _resolve_env(channel.webhook_url)
            if not url:
                log.warning("discord notifier: missing webhook_url")
                return None
            return DiscordNotifier(webhook_url=url)
        case "wecom":
            from .wecom import WecomNotifier
            key = _resolve_env(channel.webhook_key)
            if not key:
                log.warning("wecom notifier: missing webhook_key")
                return None
            return WecomNotifier(webhook_key=key)
        case _:
            log.warning("unknown notifier type: %s", channel.type)
            return None


async def send_notifications(config: NotifierConfig, payload: NotifyPayload) -> None:
    """Send notifications to all configured channels."""
    if not config.enable:
        return
    if payload.success and not config.on_success:
        return
    if not payload.success and not config.on_failure:
        return

    for channel in config.channels:
        notifier = _create_notifier(channel)
        if notifier is None:
            continue
        try:
            ok = await notifier.send(payload)
            if ok:
                log.info("notification sent via %s", channel.type)
            else:
                log.warning("notification failed via %s", channel.type)
        except Exception as e:  # noqa: BLE001
            log.warning("notification error via %s: %s", channel.type, e)
