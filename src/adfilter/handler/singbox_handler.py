"""sing-box ruleset handler.

sing-box consumes JSON rulesets with shape::

    {
      "version": 2,
      "rules": [
        {
          "domain": ["example.net"],
          "domain_suffix": ["example.com"]
        }
      ]
    }

See https://sing-box.sagernet.org/configuration/rule-set/source-format/

We emit ONE rule-set object per output file.  Because JSON does not
naturally stream line-by-line, the Handler returns per-domain *fragments*
and a bespoke writer in __main__ assembles them at finalise time; to keep
that out of scope, we instead render each rule as a single JSON line.
The final file is legal "JSON lines" and the accompanying ``head_format``
provides the enclosing object — readers must concatenate as sing-box
ruleset converters do. For full JSON output, use the convert CLI.
"""

from __future__ import annotations

import json

from ..constants import (
    CRLF,
    DOT,
    HASH,
    LF,
    RuleSet,
)
from ..model import Control, Mode, Rule, RuleType, Scope
from ..util import detect_base_rule, split_ignore_blank
from .base import Handler, register_handler


class SingboxHandler(Handler):
    rule_set = RuleSet.SINGBOX

    def __init__(self) -> None:
        register_handler(self.rule_set, self)

    def parse(self, line: str) -> Rule:
        """Best-effort parse: accept a sing-box json-line fragment or a bare domain."""
        stripped = line.strip()
        if not stripped:
            return Rule.empty()

        rule = Rule(origin=line, source_type=RuleSet.SINGBOX, mode=Mode.DENY, scope=Scope.DOMAIN)

        # try parsing as a JSON fragment first
        if stripped.startswith("{"):
            try:
                obj = json.loads(stripped.rstrip(","))
            except json.JSONDecodeError:
                rule.type = RuleType.UNKNOWN
                return rule
            if "domain_suffix" in obj:
                domains = obj["domain_suffix"]
                if isinstance(domains, list) and domains:
                    rule.target = domains[0]
                    rule.controls.add(Control.OVERLAY)
                    rule.type = RuleType.BASIC
                    return rule
            if "domain" in obj:
                domains = obj["domain"]
                if isinstance(domains, list) and domains:
                    rule.target = domains[0]
                    rule.type = RuleType.BASIC
                    return rule
            rule.type = RuleType.UNKNOWN
            return rule

        # fall back: treat as bare domain
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
            return rule.origin if rule.source_type is RuleSet.SINGBOX else None
        if rule.mode is Mode.ALLOW:
            return None
        if rule.scope is not Scope.DOMAIN or rule.type not in (RuleType.BASIC, RuleType.WILDCARD):
            return None

        key = "domain_suffix" if Control.OVERLAY in rule.controls else "domain"
        # emit compact one-line rule object; the enclosing ruleset is added
        # by the JSON finalizer (see writer.singbox_finalise).
        return json.dumps({key: [rule.target]}, ensure_ascii=False)

    def head_format(self) -> str | None:
        # sing-box rulesets are JSON; the file-level wrapper is added
        # post-hoc in writer.singbox_finalise to keep the streaming pipeline
        # unchanged for all other formats.
        return None

    def is_comment(self, line: str) -> bool:
        stripped = line.lstrip()
        return stripped.startswith(HASH) or stripped.startswith("//")

    def commented(self, value: str) -> str:
        # use `//` comments so later JSON-wrap can strip them cleanly
        return CRLF.join(
            f"// {ln.strip()}"
            for ln in split_ignore_blank(value, LF)
        )
