"""Notifier base, registry, and dispatcher."""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from importlib.metadata import entry_points

from ..config import NotifierChannel, NotifierConfig
from ..stats import BuildReport

log = logging.getLogger(__name__)

# ── Registry ────────────────────────────────────────────────────────
_NOTIFIER_REGISTRY: dict[str, type[Notifier]] = {}


def register_notifier(name: str, cls: type[Notifier]) -> None:
    """Register a notifier class under a channel type name."""
    _NOTIFIER_REGISTRY[name] = cls


def get_notifier_class(name: str) -> type[Notifier] | None:
    """Look up a registered notifier class by type name."""
    return _NOTIFIER_REGISTRY.get(name)


def discover_notifier_plugins() -> None:
    """Load third-party notifiers registered via entry_points.

    Third-party packages declare entry points under ``adfilter.notifiers``::

        [project.entry-points."adfilter.notifiers"]
        slack = "my_package.notifier:SlackNotifier"

    Each entry point must resolve to a Notifier subclass.
    """
    try:
        eps = entry_points(group="adfilter.notifiers")
    except TypeError:
        eps = entry_points().get("adfilter.notifiers", [])

    for ep in eps:
        try:
            notifier_cls = ep.load()
            if isinstance(notifier_cls, type) and issubclass(notifier_cls, Notifier):
                register_notifier(ep.name, notifier_cls)
                log.info("loaded notifier plugin: %s", ep.name)
            else:
                log.warning("notifier plugin %s is not a Notifier subclass, skipping", ep.name)
        except Exception as e:  # noqa: BLE001
            log.warning("failed to load notifier plugin %s: %s", ep.name, e)


# ── Data ────────────────────────────────────────────────────────────


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


# ── Abstract base ───────────────────────────────────────────────────


class Notifier(ABC):
    """Abstract notifier."""

    @abstractmethod
    async def send(self, payload: NotifyPayload) -> bool:
        """Send notification. Return True on success."""


# ── Helpers ─────────────────────────────────────────────────────────


def _resolve_env(value: str) -> str:
    """Resolve ${VAR} style environment variable references."""
    if value.startswith("${") and value.endswith("}"):
        env_name = value[2:-1]
        return os.environ.get(env_name, "")
    return value


def _create_notifier(channel: NotifierChannel) -> Notifier | None:
    """Factory: create notifier from channel config using the registry."""
    cls = get_notifier_class(channel.type)
    if cls is None:
        log.warning("unknown notifier type: %s", channel.type)
        return None

    # Each built-in notifier has a from_channel classmethod or we use
    # type-specific construction logic based on channel fields.
    match channel.type:
        case "telegram":
            token = _resolve_env(channel.bot_token)
            chat_id = _resolve_env(channel.chat_id)
            if not token or not chat_id:
                log.warning("telegram notifier: missing bot_token or chat_id")
                return None
            return cls(bot_token=token, chat_id=chat_id)  # type: ignore[call-arg]
        case "discord":
            url = _resolve_env(channel.webhook_url)
            if not url:
                log.warning("discord notifier: missing webhook_url")
                return None
            return cls(webhook_url=url)  # type: ignore[call-arg]
        case "wecom":
            key = _resolve_env(channel.webhook_key)
            if not key:
                log.warning("wecom notifier: missing webhook_key")
                return None
            return cls(webhook_key=key)  # type: ignore[call-arg]
        case _:
            # Third-party plugins: try generic construction with channel data
            try:
                return cls(channel=channel)  # type: ignore[call-arg]
            except TypeError:
                log.warning("notifier %s: could not construct from channel config", channel.type)
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
