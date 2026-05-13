"""Rule conflict detector — finds logical contradictions in merged rule sets.

Detects:
1. Same domain with both DENY and ALLOW rules
2. Parent domain DENY vs child domain ALLOW (or vice versa)
3. Different sources disagreeing on a domain's treatment
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from enum import StrEnum, auto

from ..model import Control, Mode, Rule, RuleType, Scope

log = logging.getLogger(__name__)


class ConflictType(StrEnum):
    DENY_ALLOW_SAME_TARGET = auto()
    PARENT_CHILD_CONFLICT = auto()
    SOURCE_DISAGREEMENT = auto()


@dataclass(slots=True)
class Conflict:
    """A detected rule conflict."""
    type: ConflictType
    domain: str
    rules: list[Rule] = field(default_factory=list)
    deny_sources: list[str] = field(default_factory=list)
    allow_sources: list[str] = field(default_factory=list)
    resolution: str = ""
    confidence: float = 0.0


@dataclass(slots=True)
class ConflictReport:
    """Summary of all detected conflicts."""
    total_conflicts: int = 0
    auto_resolved: int = 0
    needs_review: int = 0
    conflicts: list[Conflict] = field(default_factory=list)

    def by_type(self, ctype: ConflictType) -> list[Conflict]:
        return [c for c in self.conflicts if c.type == ctype]


class ConflictDetector:
    """Detects logical conflicts in a rule set."""

    def detect(self, rules: list[Rule]) -> ConflictReport:
        """Analyze a rule set for conflicts."""
        conflicts: list[Conflict] = []
        conflicts.extend(self._find_deny_allow_conflicts(rules))
        conflicts.extend(self._find_hierarchy_conflicts(rules))
        conflicts.extend(self._find_source_disagreements(rules))

        auto_resolved = sum(1 for c in conflicts if c.confidence >= 0.8)
        needs_review = len(conflicts) - auto_resolved

        report = ConflictReport(
            total_conflicts=len(conflicts),
            auto_resolved=auto_resolved,
            needs_review=needs_review,
            conflicts=conflicts,
        )

        log.info("conflict detector: %d conflicts (%d auto-resolved, %d need review)",
                 len(conflicts), auto_resolved, needs_review)
        return report

    def _find_deny_allow_conflicts(self, rules: list[Rule]) -> list[Conflict]:
        """Find domains that have both DENY and ALLOW rules."""
        deny_targets: dict[str, list[Rule]] = defaultdict(list)
        allow_targets: dict[str, list[Rule]] = defaultdict(list)

        for r in rules:
            if not r.target or r.scope != Scope.DOMAIN:
                continue
            if r.type not in (RuleType.BASIC, RuleType.WILDCARD):
                continue
            if r.mode == Mode.DENY:
                deny_targets[r.target].append(r)
            elif r.mode == Mode.ALLOW:
                allow_targets[r.target].append(r)

        conflicts: list[Conflict] = []
        for target in set(deny_targets) & set(allow_targets):
            deny_rules = deny_targets[target]
            allow_rules = allow_targets[target]
            deny_sources = list({r.source_name for r in deny_rules if r.source_name})
            allow_sources = list({r.source_name for r in allow_rules if r.source_name})

            conflicts.append(Conflict(
                type=ConflictType.DENY_ALLOW_SAME_TARGET,
                domain=target,
                rules=deny_rules + allow_rules,
                deny_sources=deny_sources,
                allow_sources=allow_sources,
                resolution="ALLOW takes precedence (explicit allowlist overrides block)",
                confidence=0.9,
            ))

        return conflicts

    def _find_hierarchy_conflicts(self, rules: list[Rule]) -> list[Conflict]:
        """Find parent-child domain conflicts (parent DENY, child ALLOW or vice versa)."""
        # Build sets of overlay-deny parents and allow domains
        overlay_deny: set[str] = set()
        allow_domains: set[str] = set()

        for r in rules:
            if not r.target or r.scope != Scope.DOMAIN:
                continue
            if r.type not in (RuleType.BASIC, RuleType.WILDCARD):
                continue
            if r.mode == Mode.DENY and Control.OVERLAY in r.controls:
                overlay_deny.add(r.target)
            elif r.mode == Mode.ALLOW:
                allow_domains.add(r.target)

        conflicts: list[Conflict] = []

        # Check: parent blocks (overlay), but child is explicitly allowed
        for allowed in allow_domains:
            parts = allowed.split(".")
            for i in range(1, len(parts) - 1):
                parent = ".".join(parts[i:])
                if parent in overlay_deny:
                    conflicts.append(Conflict(
                        type=ConflictType.PARENT_CHILD_CONFLICT,
                        domain=allowed,
                        resolution=f"Child ALLOW '{allowed}' overrides parent DENY '{parent}' (exception rule)",
                        confidence=0.85,
                    ))
                    break  # Only report the closest parent

        return conflicts

    def _find_source_disagreements(self, rules: list[Rule]) -> list[Conflict]:
        """Find domains where different sources have contradicting opinions.

        Only reports if one source blocks and another allows the same domain.
        """
        # Group by target: source → mode
        target_source_modes: dict[str, dict[str, Mode]] = defaultdict(dict)

        for r in rules:
            if not r.target or not r.source_name or r.scope != Scope.DOMAIN:
                continue
            if r.type not in (RuleType.BASIC, RuleType.WILDCARD):
                continue
            if r.mode in (Mode.DENY, Mode.ALLOW):
                target_source_modes[r.target][r.source_name] = r.mode

        conflicts: list[Conflict] = []
        for target, source_modes in target_source_modes.items():
            modes = set(source_modes.values())
            if Mode.DENY in modes and Mode.ALLOW in modes:
                deny_sources = [s for s, m in source_modes.items() if m == Mode.DENY]
                allow_sources = [s for s, m in source_modes.items() if m == Mode.ALLOW]

                # Skip if already caught by deny_allow_conflicts
                # (this catches inter-source disagreements specifically)
                if len(deny_sources) > 0 and len(allow_sources) > 0:
                    conflicts.append(Conflict(
                        type=ConflictType.SOURCE_DISAGREEMENT,
                        domain=target,
                        deny_sources=deny_sources,
                        allow_sources=allow_sources,
                        resolution="Majority vote: follow the majority of sources",
                        confidence=0.6,
                    ))

        return conflicts
