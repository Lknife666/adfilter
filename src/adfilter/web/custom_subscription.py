"""Custom subscription system — personalized rule generation per user config.

Users create subscriptions by selecting categories, regions, formats, and
allowlists. Each unique configuration gets a stable hash-based ID. Rule
content is generated on-demand from pre-built category/region indexes.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

log = logging.getLogger(__name__)


class SubscriptionConfig(BaseModel):
    """User-defined subscription configuration."""
    categories: list[str] = Field(default_factory=lambda: ["ads"])
    regions: list[str] = Field(default_factory=lambda: ["global"])
    format: str = "dns"
    allowlist: list[str] = Field(default_factory=list)
    quality_threshold: float | None = None  # Min score to include (0-100)

    def config_hash(self) -> str:
        """Stable 8-char hash from configuration content."""
        payload = self.model_dump_json(exclude_none=True)
        return hashlib.sha256(payload.encode()).hexdigest()[:8]


@dataclass(slots=True)
class SubscriptionInfo:
    """Metadata about a created subscription."""
    subscription_id: str
    url: str
    config: SubscriptionConfig
    estimated_rules: int = 0
    created_at: str = ""


class CustomSubscriptionManager:
    """Manages personalized subscriptions with JSON file storage."""

    def __init__(self, storage_dir: Path, base_url: str = "") -> None:
        self._storage_dir = storage_dir
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._base_url = base_url.rstrip("/")
        self._subscriptions: dict[str, SubscriptionConfig] = {}
        self._load_all()

    def create(self, config: SubscriptionConfig) -> SubscriptionInfo:
        """Create or retrieve a subscription. Same config = same ID."""
        sub_id = config.config_hash()

        # Store config
        self._subscriptions[sub_id] = config
        self._persist(sub_id, config)

        url = f"{self._base_url}/api/v1/subscribe/custom/{sub_id}" if self._base_url else f"/api/v1/subscribe/custom/{sub_id}"

        return SubscriptionInfo(
            subscription_id=sub_id,
            url=url,
            config=config,
        )

    def get(self, sub_id: str) -> SubscriptionConfig | None:
        """Retrieve subscription config by ID."""
        return self._subscriptions.get(sub_id)

    def list_all(self) -> list[SubscriptionInfo]:
        """List all stored subscriptions."""
        result = []
        for sub_id, config in self._subscriptions.items():
            url = f"{self._base_url}/api/v1/subscribe/custom/{sub_id}" if self._base_url else f"/api/v1/subscribe/custom/{sub_id}"
            result.append(SubscriptionInfo(subscription_id=sub_id, url=url, config=config))
        return result

    def delete(self, sub_id: str) -> bool:
        """Delete a subscription."""
        if sub_id not in self._subscriptions:
            return False
        del self._subscriptions[sub_id]
        path = self._storage_dir / f"{sub_id}.json"
        path.unlink(missing_ok=True)
        return True

    def generate_rules(
        self,
        sub_id: str,
        rule_index: "RuleIndex | None" = None,
    ) -> str | None:
        """Generate rule file content for a subscription.

        Args:
            sub_id: Subscription ID
            rule_index: Pre-built rule index (category/region → domains)

        Returns:
            Formatted rule content string, or None if subscription not found
        """
        config = self.get(sub_id)
        if config is None:
            return None

        if rule_index is None:
            return None

        # Gather domains from selected categories and regions
        domains = rule_index.query(
            categories=config.categories,
            regions=config.regions,
            quality_threshold=config.quality_threshold,
        )

        # Apply user allowlist
        if config.allowlist:
            allowset = set(config.allowlist)
            domains = [d for d in domains if not _is_allowed(d, allowset)]

        # Format output
        from ..handler import get_handler
        from ..constants import RuleSet
        from ..model import Control, Mode, Rule, RuleType, Scope

        try:
            rs = RuleSet(config.format)
        except ValueError:
            rs = RuleSet.DNS

        handler = get_handler(rs)
        lines: list[str] = []

        # Add header
        head = handler.head_format()
        if head:
            lines.append(head)

        for domain in sorted(domains):
            rule = Rule(
                target=domain,
                mode=Mode.DENY,
                scope=Scope.DOMAIN,
                type=RuleType.BASIC,
                controls={Control.OVERLAY},
            )
            formatted = handler.format(rule)
            if formatted:
                lines.append(formatted)

        return "\n".join(lines) + "\n"

    def _persist(self, sub_id: str, config: SubscriptionConfig) -> None:
        path = self._storage_dir / f"{sub_id}.json"
        try:
            path.write_text(config.model_dump_json(indent=2), encoding="utf-8")
        except OSError as e:
            log.warning("Failed to persist subscription %s: %s", sub_id, e)

    def _load_all(self) -> None:
        for path in self._storage_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                config = SubscriptionConfig.model_validate(data)
                sub_id = path.stem
                self._subscriptions[sub_id] = config
            except (json.JSONDecodeError, OSError, ValueError) as e:
                log.warning("Failed to load subscription %s: %s", path.name, e)


def _is_allowed(domain: str, allowset: set[str]) -> bool:
    """Check if domain is in allowlist (exact or suffix match)."""
    if domain in allowset:
        return True
    parts = domain.split(".")
    for i in range(1, len(parts) - 1):
        parent = ".".join(parts[i:])
        if parent in allowset:
            return True
    return False


@dataclass
class RuleIndex:
    """Pre-built index of rules organized by category and region.

    Built from build-report and source catalog data.
    """
    # category → set of domains
    by_category: dict[str, set[str]] = field(default_factory=dict)
    # region → set of domains
    by_region: dict[str, set[str]] = field(default_factory=dict)
    # domain → quality score (optional)
    scores: dict[str, float] = field(default_factory=dict)

    def add(self, domain: str, category: str = "", region: str = "", score: float = 50.0) -> None:
        """Add a domain to the index."""
        if category:
            self.by_category.setdefault(category, set()).add(domain)
        if region:
            self.by_region.setdefault(region, set()).add(domain)
        self.scores[domain] = score

    def query(
        self,
        categories: list[str] | None = None,
        regions: list[str] | None = None,
        quality_threshold: float | None = None,
    ) -> list[str]:
        """Query domains matching categories/regions and quality threshold."""
        result: set[str] = set()

        if categories:
            for cat in categories:
                result.update(self.by_category.get(cat, set()))

        if regions:
            for reg in regions:
                result.update(self.by_region.get(reg, set()))

        # If neither specified, return all
        if not categories and not regions:
            result = set(self.scores.keys())

        # Apply quality threshold
        if quality_threshold is not None:
            result = {d for d in result if self.scores.get(d, 0) >= quality_threshold}

        return sorted(result)
