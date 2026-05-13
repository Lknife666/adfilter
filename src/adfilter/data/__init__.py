"""Data files: source catalog and regional presets."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_source_catalog() -> dict[str, dict[str, Any]]:
    """Load the built-in source catalog, returning {id: source_dict}."""
    catalog_path = Path(__file__).parent / "source_catalog.yaml"
    if not catalog_path.exists():
        return {}
    data = yaml.safe_load(catalog_path.read_text(encoding="utf-8")) or {}
    sources = data.get("sources", [])
    return {s["id"]: s for s in sources if "id" in s}

