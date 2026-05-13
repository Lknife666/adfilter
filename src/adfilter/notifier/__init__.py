"""Webhook notification system (v0.3) with plugin support (v0.4)."""

from . import discord, telegram, wecom  # noqa: F401
from .base import Notifier, discover_notifier_plugins, register_notifier, send_notifications

# Discover third-party notifier plugins via entry_points.
discover_notifier_plugins()

__all__ = ["Notifier", "register_notifier", "send_notifications"]
