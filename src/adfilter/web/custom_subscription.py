"""Custom subscription builder — generates personalized rule URLs.

Allows users to build a subscription URL that includes only
selected sources, formats, and categories.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field

log = logging.getLogger(__name__)


@dataclass
class SubscriptionConfig:
    """Configuration for a custom subscription."""

    sources: list[str] = field(default_factory=list)
    formats: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    allowlist: list[str] = field(default_factory=list)
    name: str = ""

    @property
    def config_hash(self) -> str:
        """Generate a short hash identifying this configuration."""
        content = "|".join(sorted(self.sources + self.formats + self.categories))
        return hashlib.sha256(content.encode()).hexdigest()[:8]


class CustomSubscriptionBuilder:
    """Build custom subscription URLs based on user preferences.

    Generates URLs that encode selected sources, formats, and
    filtering options into a deterministic endpoint.
    """

    def __init__(
        self,
        *,
        base_url: str = "https://raw.githubusercontent.com/Lknife666/adfilter/release",
        available_sources: list[str] | None = None,
        available_formats: list[str] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.available_sources = available_sources or [
            "anti-ad",
            "easylist",
            "easyprivacy",
            "peter-lowe",
            "adguard-dns",
            "urlhaus",
            "phishing-army",
        ]
        self.available_formats = available_formats or [
            "dns",
            "easylist",
            "clash",
            "singbox",
            "surge",
            "quantumult",
            "loon",
            "dnsmasq",
            "smartdns",
            "hosts",
            "mikrotik",
            "unbound",
        ]

    def build_url(self, config: SubscriptionConfig) -> dict[str, str]:
        """Generate subscription URLs for the given configuration.

        Returns a dict mapping format name to its subscribe URL.
        """
        urls: dict[str, str] = {}
        formats = config.formats or self.available_formats

        format_extensions = {
            "dns": "dns.txt",
            "easylist": "easylist.txt",
            "clash": "clash.yaml",
            "singbox": "singbox.json",
            "surge": "surge.conf",
            "quantumult": "quantumult.conf",
            "loon": "loon.conf",
            "dnsmasq": "dnsmasq.conf",
            "smartdns": "smartdns.conf",
            "hosts": "hosts.txt",
            "mikrotik": "mikrotik.rsc",
            "unbound": "unbound.conf",
        }

        for fmt in formats:
            filename = format_extensions.get(fmt)
            if filename:
                urls[fmt] = f"{self.base_url}/{filename}"

        return urls

    def validate_config(self, config: SubscriptionConfig) -> list[str]:
        """Validate a subscription configuration.

        Returns a list of validation errors (empty = valid).
        """
        errors: list[str] = []

        for source in config.sources:
            if source not in self.available_sources:
                errors.append(f"Unknown source: {source}")

        for fmt in config.formats:
            if fmt not in self.available_formats:
                errors.append(f"Unknown format: {fmt}")

        return errors

    def generate_config_yaml(self, config: SubscriptionConfig) -> str:
        """Generate a YAML config snippet for the subscription."""
        lines = [
            "# Custom adfilter subscription configuration",
            f"# Config hash: {config.config_hash}",
            "",
            "application:",
            "  config:",
            "    input:",
            "      rule:",
            "        default:",
        ]

        for source in config.sources:
            lines.append(f"          - name: {source}")
            lines.append("            type: easylist")
            lines.append(f"            path: # Add URL for {source}")

        lines.extend(
            [
                "",
                "    output:",
                "      path: ./rule",
                "      files:",
            ]
        )

        format_extensions = {
            "dns": "dns.txt",
            "easylist": "easylist.txt",
            "clash": "clash.yaml",
            "singbox": "singbox.json",
            "surge": "surge.conf",
            "quantumult": "quantumult.conf",
            "loon": "loon.conf",
            "dnsmasq": "dnsmasq.conf",
            "smartdns": "smartdns.conf",
            "hosts": "hosts.txt",
            "mikrotik": "mikrotik.rsc",
            "unbound": "unbound.conf",
        }

        for fmt in config.formats:
            ext = format_extensions.get(fmt, f"{fmt}.txt")
            lines.append(f"        - {{ name: {ext}, type: {fmt} }}")

        return "\n".join(lines) + "\n"
