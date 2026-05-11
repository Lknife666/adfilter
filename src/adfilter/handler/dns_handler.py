"""DNS (AdGuardHome) handler — superset of Easylist with hosts support."""

from __future__ import annotations

from ..constants import (
    CARET,
    CRLF,
    DOLLAR,
    DOUBLE_AT,
    DOUBLE_PIPE,
    IMPORTANT,
    LF,
    LOCAL_DOMAINS,
    LOCAL_IPS,
    SLASH,
    TAB,
    UNKNOWN_IP,
    RuleSet,
)
from ..model import Control, Mode, Rule, RuleType, Scope
from ..util import parse_hosts, split_ignore_blank
from .base import register_handler
from .easylist_handler import EasylistHandler


class DnsHandler(EasylistHandler):
    rule_set = RuleSet.DNS

    def __init__(self) -> None:
        # override parent registration
        register_handler(self.rule_set, self)

    def parse(self, line: str) -> Rule:
        hosts = parse_hosts(line)
        if hosts is not None:
            ip, domain = hosts
            is_local_ip = ip in LOCAL_IPS and domain not in LOCAL_DOMAINS
            return Rule(
                origin=line,
                source_type=RuleSet.HOSTS,
                target=domain,
                mode=Mode.DENY if is_local_ip else Mode.REWRITE,
                dest=UNKNOWN_IP if is_local_ip else ip,
                scope=Scope.DOMAIN,
                type=RuleType.BASIC,
            )

        rule = super().parse(line)
        rule.source_type = RuleSet.DNS
        return rule

    def format(self, rule: Rule) -> str | None:
        # same-source unknown → verbatim
        if rule.type is RuleType.UNKNOWN:
            if rule.source_type is RuleSet.DNS:
                return rule.origin
            return None

        if rule.type not in (RuleType.BASIC, RuleType.WILDCARD):
            return None

        # REWRITE → hosts line
        if rule.mode is Mode.REWRITE:
            if rule.scope is Scope.DOMAIN and rule.type is RuleType.BASIC:
                return f"{rule.dest or UNKNOWN_IP}{TAB}{rule.target}"
            return None

        parts: list[str] = []
        if rule.mode is Mode.ALLOW:
            parts.append(DOUBLE_AT)
        if Control.OVERLAY in rule.controls:
            parts.append(DOUBLE_PIPE)

        if rule.type is RuleType.WILDCARD:
            parts.append(f"{SLASH}{rule.target}{SLASH}")
        else:
            parts.append(rule.target)

        if Control.QUALIFIER in rule.controls:
            parts.append(CARET)
        if Control.IMPORTANT in rule.controls:
            parts.append(DOLLAR + IMPORTANT)

        return "".join(parts)

    def commented(self, value: str) -> str:
        return CRLF.join(
            f"# {ln.strip()}" for ln in split_ignore_blank(value, LF)
        )
