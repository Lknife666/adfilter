"""Security hardening — input validation, rate limiting, secret masking.

Provides defense-in-depth against:
- Malicious rule content (injection attacks)
- Path traversal in output configuration
- Secret leakage in logs/reports
- Abuse of API endpoints (rate limiting)
"""

from __future__ import annotations

import logging
import re
import time
from collections import deque
from dataclasses import dataclass, field
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network
from pathlib import Path

log = logging.getLogger(__name__)

# ─── Input Validation ─────────────────────────────────────────────────

# Characters that should never appear in domain rules
FORBIDDEN_DOMAIN_PATTERNS = [
    re.compile(r"[;&|`${}]"),       # Shell metacharacters
    re.compile(r"\.\./"),           # Path traversal
    re.compile(r"<\s*script", re.I),  # XSS attempt
    re.compile(r"\x00"),            # Null byte
    re.compile(r"[\r\n]"),          # Line injection
]

# Maximum safe domain length (RFC 1035)
MAX_DOMAIN_LENGTH = 253
MAX_LABEL_LENGTH = 63


def validate_domain(domain: str) -> tuple[bool, str]:
    """Validate a domain string for security issues.

    Returns:
        (is_valid, error_message) — error_message is empty if valid
    """
    if not domain:
        return False, "empty domain"

    if len(domain) > MAX_DOMAIN_LENGTH:
        return False, f"domain exceeds {MAX_DOMAIN_LENGTH} chars"

    for pattern in FORBIDDEN_DOMAIN_PATTERNS:
        if pattern.search(domain):
            return False, f"forbidden pattern detected: {pattern.pattern}"

    # Check individual labels
    labels = domain.split(".")
    for label in labels:
        if len(label) > MAX_LABEL_LENGTH:
            return False, f"label '{label[:20]}...' exceeds {MAX_LABEL_LENGTH} chars"

    return True, ""


def validate_output_path(path: str, allowed_root: Path) -> tuple[bool, str]:
    """Validate an output path is within the allowed directory.

    Prevents path traversal attacks in output configuration.
    """
    try:
        resolved = Path(path).resolve()
        root_resolved = allowed_root.resolve()
        if not str(resolved).startswith(str(root_resolved)):
            return False, f"path '{path}' escapes allowed root '{allowed_root}'"
        return True, ""
    except (OSError, ValueError) as e:
        return False, f"invalid path: {e}"


# ─── SSRF Protection ──────────────────────────────────────────────────

# Private/reserved IP ranges that should not be fetched
PRIVATE_NETWORKS = [
    IPv4Network("10.0.0.0/8"),
    IPv4Network("172.16.0.0/12"),
    IPv4Network("192.168.0.0/16"),
    IPv4Network("127.0.0.0/8"),
    IPv4Network("169.254.0.0/16"),  # Link-local
    IPv4Network("0.0.0.0/8"),
    IPv6Network("::1/128"),
    IPv6Network("fc00::/7"),        # Unique local
    IPv6Network("fe80::/10"),       # Link-local
]


def is_private_ip(ip_str: str) -> bool:
    """Check if an IP address is in a private/reserved range."""
    try:
        ip = IPv4Address(ip_str)
        return any(ip in net for net in PRIVATE_NETWORKS if isinstance(net, IPv4Network))
    except ValueError:
        pass
    try:
        ip6 = IPv6Address(ip_str)
        return any(ip6 in net for net in PRIVATE_NETWORKS if isinstance(net, IPv6Network))
    except ValueError:
        return False


def validate_fetch_url(url: str) -> tuple[bool, str]:
    """Validate a URL for SSRF protection."""
    if not url:
        return False, "empty URL"

    # Only allow http/https
    if not url.startswith(("http://", "https://")):
        return False, f"unsupported scheme (only http/https allowed)"

    # Block file://, ftp://, etc.
    if "://" in url:
        scheme = url.split("://")[0].lower()
        if scheme not in ("http", "https"):
            return False, f"blocked scheme: {scheme}"

    return True, ""


# ─── Secret Masking ───────────────────────────────────────────────────

# Patterns that look like secrets in log output
SECRET_PATTERNS = [
    re.compile(r"(bot_token[\"']?\s*[:=]\s*[\"']?)([a-zA-Z0-9:_-]{20,})", re.I),
    re.compile(r"(webhook_url[\"']?\s*[:=]\s*[\"']?)(https?://[^\s\"']+)", re.I),
    re.compile(r"(webhook_key[\"']?\s*[:=]\s*[\"']?)([a-zA-Z0-9-]{20,})", re.I),
    re.compile(r"(token[\"']?\s*[:=]\s*[\"']?)([a-zA-Z0-9._-]{20,})", re.I),
    re.compile(r"(password[\"']?\s*[:=]\s*[\"']?)(\S{8,})", re.I),
    re.compile(r"(secret[\"']?\s*[:=]\s*[\"']?)(\S{8,})", re.I),
]


def mask_secrets(text: str) -> str:
    """Mask potential secrets in text for safe logging."""
    result = text
    for pattern in SECRET_PATTERNS:
        result = pattern.sub(lambda m: m.group(1) + "***REDACTED***", result)
    return result


class SecretFilter(logging.Filter):
    """Logging filter that masks secrets in log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = mask_secrets(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: mask_secrets(str(v)) if isinstance(v, str) else v
                               for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    mask_secrets(str(a)) if isinstance(a, str) else a
                    for a in record.args
                )
        return True


# ─── Rate Limiting ────────────────────────────────────────────────────

@dataclass
class RateLimiter:
    """Simple sliding window rate limiter.

    Usage:
        limiter = RateLimiter(max_requests=30, window_seconds=60)
        if limiter.allow("client-ip"):
            # process request
        else:
            # return 429
    """
    max_requests: int = 60
    window_seconds: float = 60.0
    _windows: dict[str, deque[float]] = field(default_factory=dict)

    def allow(self, key: str) -> bool:
        """Check if a request from `key` is allowed."""
        now = time.time()
        cutoff = now - self.window_seconds

        if key not in self._windows:
            self._windows[key] = deque()

        window = self._windows[key]

        # Remove expired entries
        while window and window[0] < cutoff:
            window.popleft()

        if len(window) >= self.max_requests:
            return False

        window.append(now)
        return True

    def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        self._windows.pop(key, None)
