"""BuildGuard — safety checks for rule builds.

Detects anomalous rule count drops, minimum thresholds, and source
failures to prevent publishing a degraded rule list.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)

# Defaults
DEFAULT_DROP_THRESHOLD = 0.3  # 30% drop triggers alert
DEFAULT_MIN_RULES = 1000
DEFAULT_STATE_FILE = ".adfilter-guard-state.json"


@dataclass
class SourceStatus:
    """Status of a single rule source fetch."""

    name: str
    success: bool
    rule_count: int = 0
    error: str = ""


@dataclass
class GuardResult:
    """Result of a build guard check."""

    passed: bool = True
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)
        log.warning("BuildGuard: %s", msg)

    def add_error(self, msg: str) -> None:
        self.passed = False
        self.errors.append(msg)
        log.error("BuildGuard: %s", msg)


class BuildGuard:
    """Validates build output before publishing.

    Checks:
    - Rule count drop detection (compared to last successful build)
    - Minimum rule count threshold
    - Source failure ratio
    """

    def __init__(
        self,
        *,
        drop_threshold: float = DEFAULT_DROP_THRESHOLD,
        min_rules: int = DEFAULT_MIN_RULES,
        max_source_failures: float = 0.5,
        state_file: str | Path = DEFAULT_STATE_FILE,
    ) -> None:
        self.drop_threshold = drop_threshold
        self.min_rules = min_rules
        self.max_source_failures = max_source_failures
        self.state_file = Path(state_file)
        self._previous_state = self._load_state()

    def check(
        self,
        total_rules: int,
        sources: list[SourceStatus] | None = None,
    ) -> GuardResult:
        """Run all guard checks and return the result."""
        result = GuardResult()

        # Check minimum threshold
        if total_rules < self.min_rules:
            result.add_error(
                f"Rule count {total_rules} is below minimum threshold {self.min_rules}"
            )

        # Check drop from previous build
        prev_count = self._previous_state.get("total_rules", 0)
        if prev_count > 0:
            drop_ratio = (prev_count - total_rules) / prev_count
            if drop_ratio > self.drop_threshold:
                result.add_error(
                    f"Rule count dropped by {drop_ratio:.1%} "
                    f"({prev_count} → {total_rules}), "
                    f"threshold is {self.drop_threshold:.0%}"
                )
            elif drop_ratio > self.drop_threshold * 0.5:
                result.add_warning(
                    f"Rule count decreased by {drop_ratio:.1%} "
                    f"({prev_count} → {total_rules})"
                )

        # Check source failures
        if sources:
            failed = [s for s in sources if not s.success]
            total_sources = len(sources)
            if total_sources > 0:
                failure_ratio = len(failed) / total_sources
                if failure_ratio > self.max_source_failures:
                    result.add_error(
                        f"{len(failed)}/{total_sources} sources failed "
                        f"({failure_ratio:.0%}), max allowed is "
                        f"{self.max_source_failures:.0%}"
                    )
                elif failed:
                    names = ", ".join(s.name for s in failed)
                    result.add_warning(f"Failed sources: {names}")

        # Save state if passed
        if result.passed:
            self._save_state(total_rules, sources)

        return result

    def _load_state(self) -> dict:
        """Load persistent state from disk."""
        if not self.state_file.exists():
            return {}
        try:
            with self.state_file.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            log.warning("BuildGuard: failed to load state: %s", e)
            return {}

    def _save_state(
        self,
        total_rules: int,
        sources: list[SourceStatus] | None = None,
    ) -> None:
        """Persist state to disk after a successful build."""
        state = {
            "total_rules": total_rules,
            "timestamp": time.time(),
            "sources": {},
        }
        if sources:
            state["sources"] = {
                s.name: {"success": s.success, "rule_count": s.rule_count}
                for s in sources
            }
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with self.state_file.open("w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except OSError as e:
            log.warning("BuildGuard: failed to save state: %s", e)

    def get_previous_count(self) -> int:
        """Get the rule count from the last successful build."""
        return self._previous_state.get("total_rules", 0)
