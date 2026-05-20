"""Small utilities."""

from __future__ import annotations

from pathlib import Path

from .constants import (
    ASTERISK,
    DOT,
    LF,
    TAB,
    WHITESPACE,
)
from .model import RuleType
from .regex_patterns import DOMAIN_PART, PATTERN_DOMAIN, PATTERN_IP


def starts_with_any(s: str | None, *prefixes: str) -> bool:
    if not s or not prefixes:
        return False
    return any(s.startswith(p) for p in prefixes)


def between(s: str, start: str, end: str) -> bool:
    if not s or not start or not end:
        return False
    return s.startswith(start) and s.endswith(end)


def sub_before(s: str, flag: str, *, is_last: bool = False) -> str:
    if not s or not flag:
        return ""
    idx = s.rfind(flag) if is_last else s.find(flag)
    return s[:idx] if idx >= 0 else ""


def sub_after(s: str, flag: str, *, is_last: bool = False) -> str:
    if not s or not flag:
        return ""
    idx = s.rfind(flag) if is_last else s.find(flag)
    return s[idx + len(flag) :] if idx >= 0 else ""


def sub_between(s: str, start: str, end: str) -> str:
    if not s or not start or not end:
        return ""
    start_idx = s.find(start)
    end_idx = s.rfind(end)
    if start_idx >= 0 and end_idx > 0 and start_idx < end_idx:
        return s[start_idx + len(start) : end_idx]
    return ""


def split_ignore_blank(s: str, flag: str) -> list[str]:
    if not s or not flag:
        return []
    return [p for p in s.split(flag) if p and not p.isspace()]


def parse_hosts(content: str) -> tuple[str, str] | None:
    """(ip, domain) or None."""
    if TAB in content:
        content = content.replace(TAB, WHITESPACE)
    parts = split_ignore_blank(content, WHITESPACE)
    if len(parts) != 2:
        return None
    ip, domain = parts[0].strip(), parts[1].strip()
    if PATTERN_IP.match(ip) and PATTERN_DOMAIN.match(domain):
        return ip, domain
    return None


def detect_base_rule(content: str) -> RuleType | None:
    """Return BASIC / WILDCARD / None for a bare domain-like string."""
    temp = content.replace(ASTERISK, "a") if ASTERISK in content else content
    temp = temp.lstrip(DOT).rstrip(DOT)

    if PATTERN_DOMAIN.match(temp):
        return RuleType.BASIC if content == temp else RuleType.WILDCARD
    if DOMAIN_PART.match(temp):
        return RuleType.WILDCARD
    return None


def normalize_path(p: str, *, root: Path | None = None) -> Path:
    path = Path(p)
    if not path.is_absolute():
        path = (root or Path.cwd()) / p
    return path


def commented_lines(value: str, prefix: str) -> str:
    """Prepend *prefix* to every non-blank line of *value*."""
    return "\r\n".join(prefix + line.strip() for line in value.split(LF) if line.strip())
