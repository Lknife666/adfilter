"""Multi-tenant support for adfilter.

Enables running multiple independent filter configurations from a
single installation, each with isolated sources, outputs, and state.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class TenantConfig:
    """Configuration for a single tenant."""

    id: str
    name: str
    config_path: str
    output_dir: str = ""
    enabled: bool = True
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.output_dir:
            self.output_dir = f"./rule/{self.id}"


class TenantManager:
    """Manage multiple tenant configurations.

    Each tenant has its own:
    - Configuration file
    - Output directory
    - Build state
    - Allowlist
    """

    def __init__(self, base_dir: str | Path = ".") -> None:
        self.base_dir = Path(base_dir)
        self._tenants: dict[str, TenantConfig] = {}

    def register(self, tenant: TenantConfig) -> None:
        """Register a new tenant."""
        if tenant.id in self._tenants:
            log.warning("Tenant '%s' already registered, overwriting", tenant.id)
        self._tenants[tenant.id] = tenant
        log.info("Registered tenant: %s (%s)", tenant.id, tenant.name)

    def unregister(self, tenant_id: str) -> bool:
        """Remove a tenant registration."""
        if tenant_id in self._tenants:
            del self._tenants[tenant_id]
            log.info("Unregistered tenant: %s", tenant_id)
            return True
        return False

    def get(self, tenant_id: str) -> TenantConfig | None:
        """Get a tenant by ID."""
        return self._tenants.get(tenant_id)

    def list_tenants(self) -> list[TenantConfig]:
        """List all registered tenants."""
        return list(self._tenants.values())

    def list_enabled(self) -> list[TenantConfig]:
        """List only enabled tenants."""
        return [t for t in self._tenants.values() if t.enabled]

    def get_output_dir(self, tenant_id: str) -> Path:
        """Get the output directory for a tenant."""
        tenant = self._tenants.get(tenant_id)
        if tenant:
            return self.base_dir / tenant.output_dir
        return self.base_dir / "rule"

    def get_config_path(self, tenant_id: str) -> Path | None:
        """Get the configuration file path for a tenant."""
        tenant = self._tenants.get(tenant_id)
        if tenant:
            path = Path(tenant.config_path)
            if not path.is_absolute():
                path = self.base_dir / path
            return path
        return None

    @property
    def tenant_count(self) -> int:
        return len(self._tenants)

    def ensure_directories(self) -> None:
        """Create output directories for all tenants."""
        for tenant in self._tenants.values():
            output = self.base_dir / tenant.output_dir
            output.mkdir(parents=True, exist_ok=True)
