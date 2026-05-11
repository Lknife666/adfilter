"""MikroTik RouterOS /ip dns static script handler.

Example output::

    /ip dns static
    add name=ads.example.com type=A address=0.0.0.0 comment="adfilter"
    add name=tracker.example.org type=A address=0.0.0.0 comment="adfilter"

RouterOS v7 also supports wildcard via regex but compatibility differs,
so we only emit exact entries.
"""

from __future__ import annotations

from ..constants import (
    CRLF,
    HASH,
    LF,
    UNKNOWN_IP,
    WHITESPACE,
    RuleSet,
)
from ..model import Mode, Rule, RuleType, Scope
from ..util import detect_base_rule, split_ignore_blank
from .base import Handler, register_handler


class MikrotikHandler(Handler):
    rule_set = RuleSet.MIKROTIK

    def __init__(self) -> None:
        register_handler(self.rule_set, self)

    def parse(self, line: str) -> Rule:
        stripped = line.strip()
        # tolerate re-parsing of our own output
        if stripped.startswith("add name="):
            try:
                name = stripped.split("name=", 1)[1].split(" ", 1)[0].strip('"')
            except (IndexError, ValueError):
                return Rule.empty()
            detected = detect_base_rule(name)
            if detected is None:
                return Rule.empty()
            return Rule(
                origin=line,
                source_type=RuleSet.MIKROTIK,
                target=name,
                dest=UNKNOWN_IP,
                mode=Mode.DENY,
                scope=Scope.DOMAIN,
                type=detected,
            )
        return Rule.empty()

    def format(self, rule: Rule) -> str | None:
        if rule.type is not RuleType.BASIC:
            return None
        if rule.scope is not Scope.DOMAIN or rule.mode is not Mode.DENY:
            return None
        dest = rule.dest or UNKNOWN_IP
        return f'add name={rule.target} type=A address={dest} comment="adfilter"'

    def head_format(self) -> str:
        return "/ip dns static"

    def is_comment(self, line: str) -> bool:
        return line.lstrip().startswith(HASH)

    def commented(self, value: str) -> str:
        return CRLF.join(
            f"{HASH}{WHITESPACE}{ln.strip()}"
            for ln in split_ignore_blank(value, LF)
        )
