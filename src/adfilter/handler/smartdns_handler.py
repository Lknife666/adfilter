"""smartdns handler (address /domain/#)."""

from __future__ import annotations

from ..constants import (
    ASTERISK,
    CRLF,
    DASH,
    DOT,
    EMPTY,
    HASH,
    LF,
    SLASH,
    SMARTDNS_HEADER,
    UNKNOWN_IP,
    WHITESPACE,
    RuleSet,
)
from ..model import Control, Mode, Rule, RuleType, Scope
from ..util import split_ignore_blank, sub_after
from .base import Handler, register_handler


class SmartdnsHandler(Handler):
    rule_set = RuleSet.SMARTDNS

    def __init__(self) -> None:
        register_handler(self.rule_set, self)

    def parse(self, line: str) -> Rule:
        content = sub_after(line, SMARTDNS_HEADER, is_last=True)
        data = split_ignore_blank(content, SLASH)
        if len(data) != 2:
            return Rule.empty()

        domain, control = data
        rule = Rule(origin=line, source_type=RuleSet.SMARTDNS)
        match control:
            case "#":
                rule.mode = Mode.DENY
            case "-":
                rule.mode = Mode.ALLOW
            case _:
                rule.type = RuleType.UNKNOWN
                return rule

        # strip leading dash/dot; leading "-" marks "only exact domain"
        if domain.startswith(DASH):
            domain = domain[len(DASH):]
        else:
            rule.controls.add(Control.OVERLAY)
        if domain.startswith(DOT):
            domain = domain[len(DOT):]

        rule.type = RuleType.WILDCARD if domain.startswith(ASTERISK) else RuleType.BASIC
        rule.target = domain
        rule.dest = UNKNOWN_IP
        rule.scope = Scope.DOMAIN
        return rule

    def format(self, rule: Rule) -> str | None:
        if rule.type is RuleType.UNKNOWN:
            if rule.source_type is RuleSet.SMARTDNS:
                return rule.origin
            return None

        if rule.mode is Mode.REWRITE or rule.scope is not Scope.DOMAIN:
            return None

        control = HASH if rule.mode is Mode.DENY else DASH

        match rule.type:
            case RuleType.BASIC:
                prefix = EMPTY if Control.OVERLAY in rule.controls else f"{ASTERISK}{DOT}"
                return f"{SMARTDNS_HEADER}{prefix}{rule.target}/{control}"
            case RuleType.WILDCARD:
                # smartdns only accepts leading *
                if rule.target.rfind(ASTERISK) == 0:
                    return f"{SMARTDNS_HEADER}{rule.target}/{DASH}"
                return None
            case _:
                return None

    def is_comment(self, line: str) -> bool:
        return line.startswith(HASH)

    def commented(self, value: str) -> str:
        return CRLF.join(
            f"{HASH}{WHITESPACE}{ln.strip()}"
            for ln in split_ignore_blank(value, LF)
        )
