"""/etc/hosts handler."""

from __future__ import annotations

from ..constants import (
    CRLF,
    HASH,
    LF,
    LOCAL_DOMAINS,
    LOCAL_IPS,
    TAB,
    UNKNOWN_IP,
    WHITESPACE,
    RuleSet,
)
from ..model import Mode, Rule, RuleType, Scope
from ..util import parse_hosts, split_ignore_blank
from .base import Handler, register_handler


class HostsHandler(Handler):
    rule_set = RuleSet.HOSTS

    def __init__(self) -> None:
        register_handler(self.rule_set, self)

    def parse(self, line: str) -> Rule:
        hosts = parse_hosts(line)
        if hosts is None:
            return Rule.empty()
        ip, domain = hosts
        is_local = ip in LOCAL_IPS and domain not in LOCAL_DOMAINS
        return Rule(
            origin=line,
            source_type=RuleSet.HOSTS,
            target=domain,
            dest=UNKNOWN_IP if is_local else ip,
            mode=Mode.DENY if is_local else Mode.REWRITE,
            scope=Scope.DOMAIN,
            type=RuleType.BASIC,
        )

    def format(self, rule: Rule) -> str | None:
        if rule.type is not RuleType.BASIC or rule.scope is not Scope.DOMAIN:
            return None
        dest = rule.dest or UNKNOWN_IP
        return f"{dest}{TAB}{rule.target}"

    def is_comment(self, line: str) -> bool:
        return line.startswith(HASH)

    def commented(self, value: str) -> str:
        return CRLF.join(
            f"{HASH}{WHITESPACE}{ln.strip()}"
            for ln in split_ignore_blank(value, LF)
        )
