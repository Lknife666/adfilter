"""Unbound ``local-zone`` handler.

Typical server block::

    server:
        local-zone: "ads.example.com." always_nxdomain
        local-zone: "tracker.example.org." always_nxdomain
"""

from __future__ import annotations

from ..constants import (
    CRLF,
    HASH,
    LF,
    WHITESPACE,
    RuleSet,
)
from ..model import Mode, Rule, RuleType, Scope
from ..util import detect_base_rule, split_ignore_blank
from .base import Handler, register_handler


class UnboundHandler(Handler):
    rule_set = RuleSet.UNBOUND

    def __init__(self) -> None:
        register_handler(self.rule_set, self)

    def parse(self, line: str) -> Rule:
        stripped = line.strip()
        if not stripped.startswith("local-zone:"):
            return Rule.empty()
        try:
            _, rest = stripped.split(":", 1)
            parts = rest.strip().split()
            if not parts:
                return Rule.empty()
            domain = parts[0].strip('"').rstrip(".")
        except (IndexError, ValueError):
            return Rule.empty()
        detected = detect_base_rule(domain)
        if detected is None:
            return Rule.empty()
        return Rule(
            origin=line,
            source_type=RuleSet.UNBOUND,
            target=domain,
            mode=Mode.DENY,
            scope=Scope.DOMAIN,
            type=detected,
        )

    def format(self, rule: Rule) -> str | None:
        if rule.type not in (RuleType.BASIC, RuleType.WILDCARD):
            return None
        if rule.scope is not Scope.DOMAIN or rule.mode is not Mode.DENY:
            return None
        # unbound expects a trailing dot on zone names
        return f'    local-zone: "{rule.target}." always_nxdomain'

    def head_format(self) -> str:
        return "server:"

    def is_comment(self, line: str) -> bool:
        return line.lstrip().startswith(HASH)

    def commented(self, value: str) -> str:
        return CRLF.join(f"{HASH}{WHITESPACE}{ln.strip()}" for ln in split_ignore_blank(value, LF))
