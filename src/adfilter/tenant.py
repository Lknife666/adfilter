"""Multi-tenant support — per-tenant configuration, build, and output.

Allows running adfilter for multiple tenants (organizations, teams, or users)
each with their own source selection, allowlist, and output configuration.

Usage:
    adfilter run --tenants config/tenants/
    adfilter run --tenant company-a

Each tenant config is a YAML file in the tenants directory.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)


class TenantConfig(BaseModel):
    """Configuration for a single tenant."""
    id: str
    name: str = ""
    sources: list[str] = Field(default_factory=list)  # Source IDs from catalog
    allowlist: list[str] = Field(default_factory=list)  # Domains to allow
    formats: list[str] = Field(default_factory=lambda: ["dns", "clash", "hosts"])
    output_path: str = ""  # Override output directory
    base_url: str = ""  # Base URL for subscription links

    @classmethod
    def from_yaml(cls, path: Path) -> TenantConfig:
        """Load tenant config from YAML file."""
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if "tenant" in data:
            data = data["tenant"]
        return cls.model_validate(data)


@dataclass(slots=True)
class TenantBuildResult:
    """Result of building rules for one tenant."""
    tenant_id: str
    tenant_name: str
    success: bool = True
    rule_count: int = 0
    output_path: str = ""
    error: str = ""
    elapsed_ms: int = 0


class TenantManager:
    """Manages multiple tenant configurations and builds."""

    def __init__(self, tenants_dir: Path | None = None) -> None:
        self._tenants: dict[str, TenantConfig] = {}
        if tenants_dir and tenants_dir.exists():
            self._load_tenants(tenants_dir)

    @property
    def tenants(self) -> dict[str, TenantConfig]:
        return self._tenants

    def add_tenant(self, config: TenantConfig) -> None:
        """Register a tenant configuration."""
        self._tenants[config.id] = config

    def get_tenant(self, tenant_id: str) -> TenantConfig | None:
        """Get tenant config by ID."""
        return self._tenants.get(tenant_id)

    def list_tenants(self) -> list[TenantConfig]:
        """List all registered tenants."""
        return list(self._tenants.values())

    def generate_tenant_config(self, tenant: TenantConfig, base_config_path: Path) -> dict[str, Any]:
        """Generate a full AppConfig dict for a tenant based on base config + overrides.

        Args:
            tenant: Tenant configuration
            base_config_path: Path to the base application.yaml

        Returns:
            Modified config dict ready for AppConfig.model_validate()
        """
        # Load base config
        base_data = yaml.safe_load(base_config_path.read_text(encoding="utf-8")) or {}
        if "application" in base_data and "config" in base_data.get("application", {}):
            config = base_data["application"]["config"]
        else:
            config = base_data

        # Override sources if tenant specifies them
        if tenant.sources:
            # Load source catalog to resolve IDs → full input items
            from .data import load_source_catalog
            catalog = load_source_catalog()
            tenant_sources = []
            for src_id in tenant.sources:
                src = catalog.get(src_id)
                if src:
                    tenant_sources.append(src)
                else:
                    log.warning("Tenant %s: source '%s' not found in catalog", tenant.id, src_id)

            if tenant_sources:
                config.setdefault("input", {})
                config["input"]["rule"] = {"default": tenant_sources}

        # Override allowlist
        if tenant.allowlist:
            config.setdefault("input", {})
            # Write tenant allowlist to a temp file concept; for now, inject inline
            config["input"]["allowlist"] = [{"path": f"config/tenants/{tenant.id}-allowlist.txt"}]

        # Override output path
        if tenant.output_path:
            config.setdefault("output", {})
            config["output"]["path"] = tenant.output_path
        else:
            config.setdefault("output", {})
            config["output"]["path"] = f"./rule/tenants/{tenant.id}"

        # Override output formats
        if tenant.formats:
            from .constants import RuleSet
            config["output"]["files"] = [
                {"name": _format_filename(fmt), "type": fmt, "desc": f"{tenant.name} - {fmt}"}
                for fmt in tenant.formats
            ]

        return config

    def _load_tenants(self, tenants_dir: Path) -> None:
        """Load all tenant YAML files from directory."""
        for path in sorted(tenants_dir.glob("*.yaml")):
            if path.name.endswith("-allowlist.txt"):
                continue
            try:
                config = TenantConfig.from_yaml(path)
                self._tenants[config.id] = config
                log.info("Loaded tenant: %s (%s)", config.id, config.name)
            except Exception as e:  # noqa: BLE001
                log.warning("Failed to load tenant %s: %s", path.name, e)


def _format_filename(fmt: str) -> str:
    """Map format type to output filename."""
    mapping = {
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
    return mapping.get(fmt, f"{fmt}.txt")
