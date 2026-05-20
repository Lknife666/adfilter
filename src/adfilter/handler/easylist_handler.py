"""EasyList / ABP / AdGuard-style handler."""

from __future__ import annotations

from ..constants import (
    ALL,
    CARET,
    COMMA,
    CRLF,
    DOLLAR,
    DOUBLE_AT,
    DOUBLE_PIPE,
    EXCLAMATION,
    HASH,
    IMPORTANT,
    LBRACKET,
    LF,
    RBRACKET,
    SLASH,
    UNKNOWN_IP,
    WHITESPACE,
    RuleSet,
)
from ..model import Control, Mode, Rule, RuleType, Scope
from ..util import between, detect_base_rule, split_ignore_blank, starts_with_any
from .base import Handler, register_handler


class EasylistHandler(Handler):
    rule_set = RuleSet.EASYLIST

    def __init__(self) -> None:
        register_handler(self.rule_set, self)

    # ────────── parse ──────────
    def parse(self, line: str) -> Rule:
        rule = Rule(origin=line, source_type=RuleSet.EASYLIST, mode=Mode.DENY)
        work = line

        # @@ exception
        if work.startswith(DOUBLE_AT):
            rule.mode = Mode.ALLOW
            work = work[2:]

        # || overlay
        if work.startswith(DOUBLE_PIPE):
            rule.controls.add(Control.OVERLAY)
            work = work[2:]

        # $modifiers
        if DOLLAR in work:
            i = work.index(DOLLAR)
            mod = work[i + 1 :].strip()
            work = work[:i]
            match mod:
                case "important":
                    rule.controls.add(Control.IMPORTANT)
                case "all":
                    rule.controls.add(Control.ALL)
                case _:
                    rule.type = RuleType.UNKNOWN
                    return rule

        # ^ qualifier
        if work.endswith(CARET):
            rule.controls.add(Control.QUALIFIER)
            work = work[:-1]

        # /regex/
        if work.startswith(SLASH) and work.endswith(SLASH) and len(work) > 2:
            rule.type = RuleType.REGEX
            work = work[1:-1]
            rule.target = work

        # domain / wildcard detection
        detected = detect_base_rule(work)
        if detected is not None:
            rule.type = detected
            rule.target = work
            rule.scope = Scope.DOMAIN
            if rule.mode is Mode.DENY:
                rule.dest = UNKNOWN_IP
        elif rule.type is None:
            rule.type = RuleType.UNKNOWN

        # scope cannot be distinguished further for UNKNOWN/REGEX – default to DOMAIN
        rule.scope = Scope.DOMAIN
        return rule

    # ────────── format ──────────
    def format(self, rule: Rule) -> str | None:
        # same-source unknown → return verbatim
        if rule.type is RuleType.UNKNOWN and rule.source_type is RuleSet.EASYLIST:
            return rule.origin
        # otherwise: unknown / rewrite cannot be represented
        if rule.type is RuleType.UNKNOWN or rule.mode is Mode.REWRITE:
            return None

        parts: list[str] = []
        if rule.mode is Mode.ALLOW:
            parts.append(DOUBLE_AT)
        if Control.OVERLAY in rule.controls:
            parts.append(DOUBLE_PIPE)

        if rule.type in (RuleType.REGEX, RuleType.WILDCARD):
            parts.append(f"{SLASH}{rule.target}{SLASH}")
        else:
            parts.append(rule.target)

        if Control.QUALIFIER in rule.controls:
            parts.append(CARET)
        if Control.IMPORTANT in rule.controls:
            parts.append(DOLLAR + IMPORTANT)
        if Control.ALL in rule.controls:
            out = "".join(parts)
            if DOLLAR in out:
                return out + COMMA + ALL
            return out + DOLLAR + ALL

        return "".join(parts)

    # ────────── comment handling ──────────
    def is_comment(self, line: str) -> bool:
        return starts_with_any(line, HASH, EXCLAMATION) or between(line, LBRACKET, RBRACKET)

    def commented(self, value: str) -> str:
        return CRLF.join(f"{EXCLAMATION}{WHITESPACE}{ln.strip()}" for ln in split_ignore_blank(value, LF))
