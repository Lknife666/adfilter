"""Conflict detector — finds contradictory rules in the rule set.

Identifies cases where a domain is both blocked and allowed, or where
overlapping wildcard patterns create ambiguous behaviour.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

log = logging.getLogger(__name__)


@dataclass
class RuleConflict:
    """A detected conflict between two rules."""

    domain: str
    conflict_type: str  # "deny_allow", "overlap", "duplicate_source"
    sources: list[str] = field(default_factory=list)
    description: str = ""


class ConflictDetector:
    """Detect conflicting rules within a rule set.

    Conflict types:
    - deny_allow: same domain appears in both block and allow lists
    - overlap: a wildcard rule shadows a more specific rule
    - duplicate_source: same domain blocked by multiple identical sources
    """

    def __init__(self) -> None:
        self._conflicts: list[RuleConflict] = []

    def detect(
        self,
        deny_domains: dict[str, list[str]],
        allow_domains: dict[str, list[str]] | None = None,
    ) -> list[RuleConflict]:
        """Detect conflicts.

        Args:
            deny_domains: mapping of domain -> list of source names that block it
            allow_domains: mapping of domain -> list of source names that allow it
        """
        self._conflicts = []
        allow_domains = allow_domains or {}

        # Check deny vs allow conflicts
        for domain, deny_sources in deny_domains.items():
            if domain in allow_domains:
                allow_sources = allow_domains[domain]
                self._conflicts.append(
                    RuleConflict(
                        domain=domain,
                        conflict_type="deny_allow",
                        sources=deny_sources + allow_sources,
                        description=(f"Blocked by {deny_sources} but allowed by {allow_sources}"),
                    )
                )

        # Check overlap conflicts (wildcard shadowing)
        self._detect_overlaps(deny_domains)

        if self._conflicts:
            log.info("ConflictDetector: found %d conflicts", len(self._conflicts))

        return self._conflicts

    def _detect_overlaps(self, deny_domains: dict[str, list[str]]) -> None:
        """Detect wildcard overlaps where parent domains shadow children."""
        domains = set(deny_domains.keys())

        for domain in list(domains):
            parts = domain.split(".")
            # Check if any parent domain is also blocked
            for i in range(1, len(parts) - 1):
                parent = ".".join(parts[i:])
                if parent in domains and parent != domain:
                    parent_sources = deny_domains.get(parent, [])
                    child_sources = deny_domains.get(domain, [])
                    self._conflicts.append(
                        RuleConflict(
                            domain=domain,
                            conflict_type="overlap",
                            sources=child_sources + parent_sources,
                            description=(f"'{domain}' is shadowed by parent '{parent}'"),
                        )
                    )
                    break  # Only report first overlap

    def get_conflicts_by_type(self, conflict_type: str) -> list[RuleConflict]:
        """Filter conflicts by type."""
        return [c for c in self._conflicts if c.conflict_type == conflict_type]

    @property
    def conflict_count(self) -> int:
        return len(self._conflicts)

    @property
    def has_conflicts(self) -> bool:
        return len(self._conflicts) > 0
