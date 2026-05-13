"""Quantumult X filter handler.

Output format::

    host, ads.example.com, reject
    host-suffix, example.com, reject
    host-keyword, tracker, reject

Reference: https://github.com/crossutility/Quantumult-X
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


class QuantumultHandler(Handler):
    rule_set = RuleSet.QUANTUMULT

    def __init__(self) -> None:
        register_handler(self.rule_set, self)

    def parse(self, line: str) -> Rule:
        stripped = line.strip()
        if not stripped:
            return Rule.empty()

        rule = Rule(origin=line, source_type=RuleSet.QUANTUMULT, scope=Scope.DOMAIN)

        # Parse "host, domain, reject" / "host-suffix, domain, reject"
        parts = [p.strip() for p in stripped.split(",")]
        if len(parts) < 3:
            rule.type = RuleType.UNKNOWN
            return rule

        rule_type_str, domain, action = parts[0].lower(), parts[1], parts[2].lower()

        match action:
            case "reject" | "reject-200" | "reject-img" | "reject-dict" | "reject-array":
                rule.mode = Mode.DENY
            case "direct" | "proxy":
                rule.mode = Mode.ALLOW
            case _:
                rule.mode = Mode.DENY

        match rule_type_str:
            case "host":
                rule.type = RuleType.BASIC
                rule.target = domain
            case "host-suffix":
                rule.type = RuleType.BASIC
                rule.target = domain
                rule.controls.add(Control.OVERLAY)
            case "host-keyword":
                rule.type = RuleType.WILDCARD
                rule.target = domain
            case _:
                rule.type = RuleType.UNKNOWN
                return rule

        return rule

    def format(self, rule: Rule) -> str | None:
        if rule.type is RuleType.UNKNOWN:
            return rule.origin if rule.source_type is RuleSet.QUANTUMULT else None
        if rule.scope is not Scope.DOMAIN:
            return None
        if rule.mode is Mode.ALLOW:
            return None

        if rule.type is RuleType.BASIC:
            if Control.OVERLAY in rule.controls:
                return f"host-suffix, {rule.target}, reject"
            return f"host, {rule.target}, reject"
        if rule.type is RuleType.WILDCARD:
            return f"host-keyword, {rule.target}, reject"
        return None

    def is_comment(self, line: str) -> bool:
        stripped = line.lstrip()
        return stripped.startswith(HASH) or stripped.startswith(";") or stripped.startswith("//")

    def commented(self, value: str) -> str:
        return CRLF.join(
            f"# {ln.strip()}"
            for ln in split_ignore_blank(value, LF)
        )
