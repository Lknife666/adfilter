"""Content auditor — detects dangerous or anomalous rules before publishing.

Checks for:
- Rules targeting protected infrastructure domains
- Volume anomalies (sudden spikes in rule count)
- Suspicious patterns (blocking entire TLDs, very short domains)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class SecurityAlert:
    """A single security alert raised during audit."""

    severity: str  # "critical" | "warning"
    source: str
    message: str
    rule: str = ""


@dataclass
class AuditResult:
    """Result of auditing a single source."""

    source: str
    passed: bool
    alerts: list[SecurityAlert] = field(default_factory=list)

    @property
    def critical_count(self) -> int:
        return sum(1 for a in self.alerts if a.severity == "critical")

    @property
    def warning_count(self) -> int:
        return sum(1 for a in self.alerts if a.severity == "warning")


@dataclass
class AuditPolicy:
    """Configuration for the content auditor."""

    protected_domains: frozenset[str] = field(default_factory=frozenset)
    max_new_rules_per_source: int = 5000
    max_new_rules_ratio: float = 0.5
    allowed_hosts_targets: frozenset[str] = field(
        default_factory=lambda: frozenset({"0.0.0.0", "127.0.0.1", "::1", "::"}),
    )
    suspicious_patterns: list[re.Pattern[str]] = field(default_factory=list)

    @classmethod
    def from_file(cls, protected_domains_file: str | Path, **kwargs: object) -> AuditPolicy:
        """Create policy loading protected domains from a file."""
        path = Path(protected_domains_file)
        domains: set[str] = set()
        if path.exists():
            for raw_line in path.read_text(encoding="utf-8").splitlines():
                entry = raw_line.strip()
                if entry and not entry.startswith("#"):
                    domains.add(entry.lower())
        return cls(protected_domains=frozenset(domains), **kwargs)  # type: ignore[arg-type]


class ContentAuditor:
    """Audit rule sources for security issues.

    Designed to run after parsing but before optimization/writing.
    """

    def __init__(
        self,
        policy: AuditPolicy,
        previous_counts: dict[str, int] | None = None,
    ) -> None:
        self.policy = policy
        self.previous_counts = previous_counts or {}

    def audit_domains(
        self, source_name: str, domains: list[str]
    ) -> AuditResult:
        """Audit a list of blocked domains from a single source."""
        alerts: list[SecurityAlert] = []

        # Check 1: Protected domains
        for domain in domains:
            if domain in self.policy.protected_domains:
                alerts.append(
                    SecurityAlert(
                        severity="critical",
                        source=source_name,
                        message=f"Attempts to block protected domain: {domain}",
                        rule=domain,
                    )
                )

        # Check 2: Volume anomaly
        prev_count = self.previous_counts.get(source_name, 0)
        current_count = len(domains)
        if prev_count > 0:
            new_rules = current_count - prev_count
            if new_rules > self.policy.max_new_rules_per_source:
                alerts.append(
                    SecurityAlert(
                        severity="warning",
                        source=source_name,
                        message=(
                            f"Rule count spike: +{new_rules} new rules "
                            f"(threshold: {self.policy.max_new_rules_per_source})"
                        ),
                    )
                )
            elif prev_count > 0 and new_rules / prev_count > self.policy.max_new_rules_ratio:
                alerts.append(
                    SecurityAlert(
                        severity="warning",
                        source=source_name,
                        message=(
                            f"Rule count grew by {new_rules / prev_count:.0%} "
                            f"(threshold: {self.policy.max_new_rules_ratio:.0%})"
                        ),
                    )
                )

        # Check 3: Suspicious patterns
        for domain in domains:
            for pattern in self.policy.suspicious_patterns:
                if pattern.match(domain):
                    alerts.append(
                        SecurityAlert(
                            severity="warning",
                            source=source_name,
                            message=f"Suspicious domain pattern: {domain}",
                            rule=domain,
                        )
                    )
                    break  # one alert per domain

        has_critical = any(a.severity == "critical" for a in alerts)
        return AuditResult(
            source=source_name,
            passed=not has_critical,
            alerts=alerts,
        )

    def audit_batch(
        self, sources: dict[str, list[str]]
    ) -> list[AuditResult]:
        """Audit multiple sources at once."""
        return [self.audit_domains(name, domains) for name, domains in sources.items()]
