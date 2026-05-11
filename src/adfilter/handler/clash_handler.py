"""Clash domain-rule handler (``- '+.example.com'``)."""

from __future__ import annotations

from ..constants import (
    ASTERISK,
    COLON,
    CRLF,
    DASH,
    DOT,
    HASH,
    LF,
    PAYLOAD,
    PLUS,
    QUOTE,
    SINGLE_QUOTE,
    UNKNOWN_IP,
    RuleSet,
)
from ..model import Control, Mode, Rule, RuleType, Scope
from ..regex_patterns import PATTERN_DOMAIN
from ..util import split_ignore_blank, sub_between
from .base import Handler, register_handler


class ClashHandler(Handler):
    rule_set = RuleSet.CLASH

    def __init__(self) -> None:
        register_handler(self.rule_set, self)

    def parse(self, line: str) -> Rule:
        if line.startswith(PAYLOAD):
            return Rule.empty()

        rule = Rule(origin=line, source_type=RuleSet.CLASH)
        # strip leading whitespace + optional leading "-"
        stripped = line.lstrip()
        content = (stripped[len(DASH):] if stripped.startswith(DASH) else stripped).strip()
        if content.startswith(SINGLE_QUOTE):
            content = sub_between(content, SINGLE_QUOTE, SINGLE_QUOTE).strip()
        elif content.startswith(QUOTE):
            content = sub_between(content, QUOTE, QUOTE).strip()

        # leading "*" cannot be expressed in easylist form
        if content.startswith(ASTERISK):
            rule.type = RuleType.UNKNOWN
            return rule

        # "+" wildcard (clash) → overlay
        if content.startswith(PLUS):
            skip = 2 if content.startswith("+.") else 1
            content = content[skip:]
            rule.controls.add(Control.OVERLAY)

        have_asterisk = ASTERISK in content
        temp = content.replace(ASTERISK, "a") if have_asterisk else content
        if PATTERN_DOMAIN.match(temp):
            rule.type = RuleType.WILDCARD if have_asterisk else RuleType.BASIC

        rule.target = content
        rule.dest = UNKNOWN_IP
        rule.mode = Mode.DENY
        rule.scope = Scope.DOMAIN
        if rule.type is None:
            rule.type = RuleType.UNKNOWN
        return rule

    def format(self, rule: Rule) -> str | None:
        if rule.type is RuleType.UNKNOWN:
            if rule.source_type is RuleSet.CLASH:
                return rule.origin
            return None

        if rule.type not in (RuleType.BASIC, RuleType.WILDCARD):
            return None
        if rule.mode is not Mode.DENY or rule.scope is not Scope.DOMAIN:
            return None

        prefix = f"{PLUS}{DOT}" if Control.OVERLAY in rule.controls else ""
        return f"  {DASH} {QUOTE}{prefix}{rule.target}{QUOTE}"

    def head_format(self) -> str:
        return f"{PAYLOAD}{COLON}"

    def is_comment(self, line: str) -> bool:
        return line.startswith(HASH)

    def commented(self, value: str) -> str:
        return CRLF.join(
            f"{HASH}{ln.strip()}" for ln in split_ignore_blank(value, LF)
        )
