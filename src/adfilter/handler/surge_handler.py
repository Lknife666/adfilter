"""Surge ``domain-set`` handler.

Surge / Shadowrocket / Stash consume a plain list of domain entries,
one per line, where a leading dot means "this domain and any subdomain"::

    .example.com      # matches foo.example.com, bar.example.com, example.com
    exact.example.net # exact match only

Reference: https://manual.nssurge.com/tutorial/domain-set.html
"""

from __future__ import annotations

from ..constants import (
    CRLF,
    DOT,
    HASH,
    LF,
    WHITESPACE,
    RuleSet,
)
from ..model import Control, Mode, Rule, RuleType, Scope
from ..util import detect_base_rule, split_ignore_blank
from .base import Handler, register_handler


class SurgeHandler(Handler):
    rule_set = RuleSet.SURGE

    def __init__(self) -> None:
        register_handler(self.rule_set, self)

    def parse(self, line: str) -> Rule:
        stripped = line.strip()
        if not stripped:
            return Rule.empty()

        rule = Rule(origin=line, source_type=RuleSet.SURGE, mode=Mode.DENY, scope=Scope.DOMAIN)
        work = stripped
        if work.startswith(DOT):
            work = work[1:]
            rule.controls.add(Control.OVERLAY)

        detected = detect_base_rule(work)
        if detected is None:
            rule.type = RuleType.UNKNOWN
            return rule

        rule.type = detected
        rule.target = work
        return rule

    def format(self, rule: Rule) -> str | None:
        if rule.type is RuleType.UNKNOWN:
            return rule.origin if rule.source_type is RuleSet.SURGE else None
        if rule.scope is not Scope.DOMAIN:
            return None
        if rule.type not in (RuleType.BASIC, RuleType.WILDCARD):
            return None
        if rule.mode is Mode.ALLOW:
            # Surge expresses allow via a separate ruleset, skip
            return None
        prefix = DOT if Control.OVERLAY in rule.controls else ""
        return f"{prefix}{rule.target}"

    def is_comment(self, line: str) -> bool:
        return line.lstrip().startswith(HASH)

    def commented(self, value: str) -> str:
        return CRLF.join(f"{HASH}{WHITESPACE}{ln.strip()}" for ln in split_ignore_blank(value, LF))
