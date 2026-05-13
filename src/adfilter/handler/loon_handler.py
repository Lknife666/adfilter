"""Loon plugin rules handler.

Output format::

    DOMAIN,ads.example.com,REJECT
    DOMAIN-SUFFIX,example.com,REJECT
    DOMAIN-KEYWORD,tracker,REJECT

Reference: https://nsloon.app/docs/
"""

from __future__ import annotations

from ..constants import (
    CRLF,
    HASH,
    LF,
    RuleSet,
)
from ..model import Control, Mode, Rule, RuleType, Scope
from ..util import split_ignore_blank
from .base import Handler, register_handler


class LoonHandler(Handler):
    rule_set = RuleSet.LOON

    def __init__(self) -> None:
        register_handler(self.rule_set, self)

    def parse(self, line: str) -> Rule:
        stripped = line.strip()
        if not stripped:
            return Rule.empty()

        rule = Rule(origin=line, source_type=RuleSet.LOON, scope=Scope.DOMAIN)

        parts = [p.strip() for p in stripped.split(",")]
        if len(parts) < 3:
            rule.type = RuleType.UNKNOWN
            return rule

        rule_type_str, domain, action = parts[0].upper(), parts[1], parts[2].upper()

        match action:
            case "REJECT" | "REJECT-DROP" | "REJECT-NO-DROP" | "REJECT-IMG":
                rule.mode = Mode.DENY
            case "DIRECT" | "PROXY":
                rule.mode = Mode.ALLOW
            case _:
                rule.mode = Mode.DENY

        match rule_type_str:
            case "DOMAIN":
                rule.type = RuleType.BASIC
                rule.target = domain
            case "DOMAIN-SUFFIX":
                rule.type = RuleType.BASIC
                rule.target = domain
                rule.controls.add(Control.OVERLAY)
            case "DOMAIN-KEYWORD":
                rule.type = RuleType.WILDCARD
                rule.target = domain
            case _:
                rule.type = RuleType.UNKNOWN
                return rule

        return rule

    def format(self, rule: Rule) -> str | None:
        if rule.type is RuleType.UNKNOWN:
            return rule.origin if rule.source_type is RuleSet.LOON else None
        if rule.scope is not Scope.DOMAIN:
            return None
        if rule.mode is Mode.ALLOW:
            return None

        if rule.type is RuleType.BASIC:
            if Control.OVERLAY in rule.controls:
                return f"DOMAIN-SUFFIX,{rule.target},REJECT"
            return f"DOMAIN,{rule.target},REJECT"
        if rule.type is RuleType.WILDCARD:
            return f"DOMAIN-KEYWORD,{rule.target},REJECT"
        return None

    def is_comment(self, line: str) -> bool:
        stripped = line.lstrip()
        return stripped.startswith(HASH) or stripped.startswith("//")

    def commented(self, value: str) -> str:
        return CRLF.join(
            f"# {ln.strip()}"
            for ln in split_ignore_blank(value, LF)
        )
