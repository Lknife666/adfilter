"""Rule-level optimizers.

These run *after* per-source parsing and *before* writing, operating on
the stream of accepted rules.  None of them are in the upstream Java
project — they are adfilter-specific differentiators.

#13  Subdomain collapse: drop ``||a.b.c^`` when ``||b.c^`` (overlay) is
     already present (since the latter already matches the former).

#14  Allow-shadow elimination: drop a DENY rule when an equivalent
     ALLOW rule (``@@||...``) is present for the same target.

#15  Multi-source voting: only keep rules that appear in at least *N*
     distinct sources (useful for de-noising community lists).

#16  IDN/punycode normalisation: canonicalise unicode domains to ASCII
     punycode before dedupe, so ``测试.com`` and ``xn--0zwm56d.com`` are
     treated identically.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Iterable

from .config import OptimizerConfig
from .model import Control, Mode, Rule, RuleType, Scope

log = logging.getLogger(__name__)


def normalize_idn(target: str) -> str:
    """Canonicalise a domain to lowercase ASCII punycode.

    Passes through ASCII-only domains unchanged.  Invalid IDN labels
    fall back to the original string.
    """
    if not target:
        return target
    if target.isascii():
        return target.lower()
    try:
        return target.encode("idna").decode("ascii").lower()
    except (UnicodeError, ValueError):
        return target.lower()


class RuleOptimizer:
    """Accumulates every accepted rule then yields the optimised set."""

    def __init__(self, config: OptimizerConfig, allowlist: set[str] | None = None) -> None:
        self.config = config
        self._rules: list[Rule] = []
        # target → count of distinct source names (for voting)
        self._sources_per_target: dict[str, set[str]] = defaultdict(set)
        # v0.3: allowlist domains to remove
        self._allowlist: set[str] = allowlist or set()

    # ── ingest ───────────────────────────────────────────────────────
    def feed(self, rule: Rule) -> None:
        if self.config.normalize_idn:
            rule.target = normalize_idn(rule.target)
        self._rules.append(rule)
        if rule.source_name and rule.target:
            self._sources_per_target[rule.target].add(rule.source_name)

    # ── drain ────────────────────────────────────────────────────────
    def drain(self) -> Iterable[Rule]:
        rules = self._rules
        before = len(rules)

        if self.config.min_source_votes > 1:
            threshold = self.config.min_source_votes
            kept = [
                r
                for r in rules
                if not r.target or len(self._sources_per_target.get(r.target, set())) >= threshold
            ]
            log.info("optimizer: voting (n>=%d) kept %d/%d", threshold, len(kept), len(rules))
            rules = kept

        if self.config.drop_allow_shadowed_deny:
            rules = _drop_allow_shadowed(rules)

        if self.config.collapse_subdomains:
            rules = _collapse_subdomains(rules)

        # v0.3: apply allowlist (remove deny rules for allowlisted domains)
        if self._allowlist:
            rules = _apply_allowlist(rules, self._allowlist)

        log.info("optimizer done: %d -> %d rules (%+d)", before, len(rules), len(rules) - before)
        yield from rules


def _drop_allow_shadowed(rules: list[Rule]) -> list[Rule]:
    allow_targets = {
        r.target
        for r in rules
        if r.mode is Mode.ALLOW
        and r.target
        and r.scope is Scope.DOMAIN
        and r.type in (RuleType.BASIC, RuleType.WILDCARD)
    }
    if not allow_targets:
        return rules
    kept = [r for r in rules if not (r.mode is Mode.DENY and r.target in allow_targets)]
    dropped = len(rules) - len(kept)
    if dropped:
        log.info("optimizer: dropped %d deny rules shadowed by an allow", dropped)
    return kept


def _collapse_subdomains(rules: list[Rule]) -> list[Rule]:
    """If ``||parent^`` (overlay) is present, drop ``||child.parent^``."""
    overlay_parents: set[str] = {
        r.target
        for r in rules
        if r.type is RuleType.BASIC
        and r.mode is Mode.DENY
        and r.scope is Scope.DOMAIN
        and Control.OVERLAY in r.controls
        and r.target
    }
    if not overlay_parents:
        return rules

    def is_shadowed(r: Rule) -> bool:
        if r.type is not RuleType.BASIC:
            return False
        if r.mode is not Mode.DENY:
            return False
        if r.scope is not Scope.DOMAIN:
            return False
        if not r.target:
            return False
        # walk the dot-separated ancestry upward
        parts = r.target.split(".")
        for i in range(1, len(parts) - 1):
            parent = ".".join(parts[i:])
            if parent in overlay_parents and parent != r.target:
                return True
        return False

    kept = [r for r in rules if not is_shadowed(r)]
    dropped = len(rules) - len(kept)
    if dropped:
        log.info("optimizer: collapsed %d child rules into overlay parents", dropped)
    return kept


def _apply_allowlist(rules: list[Rule], allowlist: set[str]) -> list[Rule]:
    """Remove DENY rules whose target is in the allowlist (exact or suffix match)."""

    def is_allowed(target: str) -> bool:
        if target in allowlist:
            return True
        # suffix match: if "example.com" in allowlist, also matches "sub.example.com"
        parts = target.split(".")
        for i in range(1, len(parts) - 1):
            parent = ".".join(parts[i:])
            if parent in allowlist:
                return True
        return False

    kept = [r for r in rules if not (r.mode is Mode.DENY and r.target and is_allowed(r.target))]
    dropped = len(rules) - len(kept)
    if dropped:
        log.info("optimizer: allowlist removed %d rules", dropped)
    return kept
