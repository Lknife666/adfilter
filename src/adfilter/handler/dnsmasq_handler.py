"""dnsmasq handler (address=/domain/ip)."""

from __future__ import annotations

from ..constants import (
    CRLF,
    DNSMASQ_HEADER,
    HASH,
    LF,
    SLASH,
    UNKNOWN_IP,
    WHITESPACE,
    RuleSet,
)
from ..model import Mode, Rule, RuleType, Scope
from ..util import detect_base_rule, split_ignore_blank, sub_after
from .base import Handler, register_handler


class DnsmasqHandler(Handler):
    rule_set = RuleSet.DNSMASQ

    def __init__(self) -> None:
        register_handler(self.rule_set, self)

    def parse(self, line: str) -> Rule:
        # "address=/domain/[ip]"
        if not line.startswith(DNSMASQ_HEADER):
            return Rule.empty()

        content = sub_after(line, DNSMASQ_HEADER, is_last=True)
        parts = split_ignore_blank(content, SLASH)
        if not parts:
            return Rule.empty()

        rule = Rule(origin=line, source_type=RuleSet.DNSMASQ, scope=Scope.DOMAIN)
        if len(parts) == 1:
            # "address=/domain/" → default deny to 0.0.0.0
            domain = parts[0]
            rule.target = domain
            rule.dest = UNKNOWN_IP
            rule.mode = Mode.DENY
        elif len(parts) == 2:
            domain, dest = parts
            rule.target = domain
            rule.dest = dest
            rule.mode = Mode.DENY if dest == UNKNOWN_IP else Mode.REWRITE
        else:
            rule.type = RuleType.UNKNOWN
            return rule

        detected = detect_base_rule(rule.target)
        rule.type = detected if detected is not None else RuleType.UNKNOWN
        return rule

    def format(self, rule: Rule) -> str | None:
        if rule.type is RuleType.UNKNOWN:
            if rule.source_type is RuleSet.DNSMASQ:
                return rule.origin
            return None

        if rule.scope is not Scope.DOMAIN:
            return None
        if rule.type not in (RuleType.BASIC, RuleType.WILDCARD):
            return None
        if rule.mode is Mode.ALLOW:
            # dnsmasq cannot express allow — skip
            return None

        dest = rule.dest or UNKNOWN_IP
        return f"{DNSMASQ_HEADER}{rule.target}/{dest}"

    def is_comment(self, line: str) -> bool:
        return line.startswith(HASH)

    def commented(self, value: str) -> str:
        return CRLF.join(
            f"{HASH}{WHITESPACE}{ln.strip()}"
            for ln in split_ignore_blank(value, LF)
        )
