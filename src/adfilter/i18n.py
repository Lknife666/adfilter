"""Internationalization (i18n) support for adfilter.

Provides simple message translation for CLI output and notifications.
Supports English and Chinese out of the box.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

log = logging.getLogger(__name__)

# Supported locales
SUPPORTED_LOCALES = ("en", "zh")
DEFAULT_LOCALE = "en"

# Translation catalog
_CATALOG: dict[str, dict[str, str]] = {
    "build.started": {
        "en": "Build started",
        "zh": "构建已启动",
    },
    "build.completed": {
        "en": "Build completed successfully",
        "zh": "构建成功完成",
    },
    "build.failed": {
        "en": "Build failed",
        "zh": "构建失败",
    },
    "build.rules_generated": {
        "en": "Generated {count} rules in {formats} formats",
        "zh": "生成了 {count} 条规则，{formats} 种格式",
    },
    "fetch.started": {
        "en": "Fetching rule sources...",
        "zh": "正在获取规则源...",
    },
    "fetch.success": {
        "en": "Successfully fetched {name}",
        "zh": "成功获取 {name}",
    },
    "fetch.failed": {
        "en": "Failed to fetch {name}: {error}",
        "zh": "获取 {name} 失败: {error}",
    },
    "fetch.cache_fallback": {
        "en": "Using cached version for {name}",
        "zh": "使用 {name} 的缓存版本",
    },
    "optimizer.started": {
        "en": "Optimizing rules...",
        "zh": "正在优化规则...",
    },
    "optimizer.collapsed": {
        "en": "Collapsed {count} subdomain rules",
        "zh": "合并了 {count} 条子域名规则",
    },
    "optimizer.allowlist_removed": {
        "en": "Allowlist removed {count} rules",
        "zh": "白名单移除了 {count} 条规则",
    },
    "guard.passed": {
        "en": "Build guard checks passed",
        "zh": "构建守卫检查通过",
    },
    "guard.failed": {
        "en": "Build guard checks failed: {reason}",
        "zh": "构建守卫检查失败: {reason}",
    },
    "notify.sending": {
        "en": "Sending notification via {channel}...",
        "zh": "正在通过 {channel} 发送通知...",
    },
    "notify.success": {
        "en": "Notification sent successfully",
        "zh": "通知发送成功",
    },
    "notify.failed": {
        "en": "Failed to send notification: {error}",
        "zh": "通知发送失败: {error}",
    },
}


@dataclass
class I18n:
    """Internationalization helper for adfilter messages."""

    locale: str = DEFAULT_LOCALE
    _fallback: str = DEFAULT_LOCALE
    _custom_messages: dict[str, dict[str, str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.locale not in SUPPORTED_LOCALES:
            log.warning(
                "Unsupported locale '%s', falling back to '%s'",
                self.locale,
                self._fallback,
            )
            self.locale = self._fallback

    @classmethod
    def from_env(cls) -> I18n:
        """Create an I18n instance from environment variables.

        Checks ADFILTER_LOCALE, LANG, and LC_ALL.
        """
        locale = os.environ.get("ADFILTER_LOCALE", "")
        if not locale:
            lang = os.environ.get("LANG", os.environ.get("LC_ALL", ""))
            locale = "zh" if lang.startswith("zh") else DEFAULT_LOCALE
        return cls(locale=locale[:2].lower())

    def t(self, key: str, **kwargs: object) -> str:
        """Translate a message key with optional formatting.

        Falls back to English if the key or locale is not found.
        """
        # Check custom messages first
        if key in self._custom_messages:
            messages = self._custom_messages[key]
            template = messages.get(self.locale, messages.get(self._fallback, key))
        elif key in _CATALOG:
            messages = _CATALOG[key]
            template = messages.get(self.locale, messages.get(self._fallback, key))
        else:
            return key

        if kwargs:
            try:
                return template.format(**{k: str(v) for k, v in kwargs.items()})
            except KeyError, ValueError:
                return template
        return template

    def add_messages(self, messages: dict[str, dict[str, str]]) -> None:
        """Add custom messages to the catalog.

        Args:
            messages: dict of key -> {locale: translation}
        """
        self._custom_messages.update(messages)

    @property
    def is_chinese(self) -> bool:
        return self.locale == "zh"

    @property
    def is_english(self) -> bool:
        return self.locale == "en"


# Module-level convenience instance
_default: I18n | None = None


def get_i18n() -> I18n:
    """Get the global I18n instance (lazy-initialized from env)."""
    global _default  # noqa: PLW0603
    if _default is None:
        _default = I18n.from_env()
    return _default


def t(key: str, **kwargs: object) -> str:
    """Translate a message using the global I18n instance."""
    return get_i18n().t(key, **kwargs)
