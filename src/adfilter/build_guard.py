"""Build Guard — detects anomalous build results and raises alerts.

Monitors rule count drops and source failures to prevent publishing
degraded rulesets silently.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass(slots=True)
class Alert:
    level: str  # "info" | "warning" | "critical"
    message: str
    suggestion: str = ""


@dataclass(slots=True)
class BuildGuardConfig:
    enable: bool = True
    max_drop_ratio: float = 0.3  # alert if rule count drops > 30%
    min_total_rules: int = 1000  # alert if total rules below this
    state_file: str = ".adfilter-guard-state.json"


@dataclass(slots=True)
class BuildGuardState:
    last_rule_count: int = 0
    last_source_count: int = 0
    consecutive_low_counts: int = 0


class BuildGuard:
    """Monitors build output quality and raises alerts on anomalies."""

    def __init__(self, config: BuildGuardConfig, state_dir: Path | None = None) -> None:
        self.config = config
        self._state_path = (state_dir or Path.cwd()) / config.state_file
        self._state = self._load_state()
        self._alerts: list[Alert] = []

    def check(self, current_rule_count: int, source_success: int = 0, source_total: int = 0) -> list[Alert]:
        """Run all guard checks and return any alerts."""
        if not self.config.enable:
            return []

        self._alerts = []
        self._check_rule_count_drop(current_rule_count)
        self._check_minimum_rules(current_rule_count)
        self._check_source_failures(source_success, source_total)

        # Update state
        self._state.last_rule_count = current_rule_count
        if source_total > 0:
            self._state.last_source_count = source_total
        self._save_state()

        return self._alerts

    def _check_rule_count_drop(self, current: int) -> None:
        """Alert if rule count dropped significantly from last build."""
        last = self._state.last_rule_count
        if last == 0:
            # First run, no baseline
            return

        if current >= last:
            self._state.consecutive_low_counts = 0
            return

        drop_ratio = 1 - (current / last)
        if drop_ratio > self.config.max_drop_ratio:
            self._state.consecutive_low_counts += 1
            level = "critical" if self._state.consecutive_low_counts >= 3 else "warning"
            self._alerts.append(Alert(
                level=level,
                message=(
                    f"Rule count dropped {drop_ratio:.0%}: "
                    f"{last:,} → {current:,} "
                    f"(consecutive drops: {self._state.consecutive_low_counts})"
                ),
                suggestion=(
                    "Multiple rule sources may be unreachable. "
                    "Check network connectivity and source URLs. "
                    "Cached versions were used if available."
                ),
            ))
        else:
            self._state.consecutive_low_counts = 0

    def _check_minimum_rules(self, current: int) -> None:
        """Alert if total rule count is suspiciously low."""
        if current < self.config.min_total_rules:
            self._alerts.append(Alert(
                level="warning",
                message=f"Total rules ({current:,}) below minimum threshold ({self.config.min_total_rules:,})",
                suggestion="Check if rule sources are configured correctly and reachable.",
            ))

    def _check_source_failures(self, success: int, total: int) -> None:
        """Alert if too many sources failed to fetch."""
        if total == 0:
            return
        failure_count = total - success
        if failure_count == 0:
            return
        failure_ratio = failure_count / total
        if failure_ratio > 0.5:
            self._alerts.append(Alert(
                level="critical",
                message=f"{failure_count}/{total} sources failed to fetch ({failure_ratio:.0%})",
                suggestion="Check network connectivity. Most rules may be stale cached versions.",
            ))
        elif failure_count > 0:
            self._alerts.append(Alert(
                level="info",
                message=f"{failure_count}/{total} sources failed (using cache fallback)",
                suggestion="",
            ))

    def _load_state(self) -> BuildGuardState:
        if self._state_path.exists():
            try:
                data = json.loads(self._state_path.read_text(encoding="utf-8"))
                return BuildGuardState(
                    last_rule_count=data.get("last_rule_count", 0),
                    last_source_count=data.get("last_source_count", 0),
                    consecutive_low_counts=data.get("consecutive_low_counts", 0),
                )
            except (json.JSONDecodeError, KeyError, TypeError):
                log.warning("build guard: could not load state file, starting fresh")
        return BuildGuardState()

    def _save_state(self) -> None:
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            self._state_path.write_text(
                json.dumps(asdict(self._state), indent=2),
                encoding="utf-8",
            )
        except OSError as e:
            log.warning("build guard: could not save state: %s", e)
