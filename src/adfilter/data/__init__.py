"""Data files: source catalog and regional presets."""

from __future__ import annotations

from pathlib import Path

import yaml

_DATA_DIR = Path(__file__).parent


def load_source_catalog() -> dict:
    """Load the source catalog from the bundled YAML file.

    Returns a dict with a 'sources' key containing the list of
    known rule sources with metadata (name, url, type, etc.).
    """
    catalog_path = _DATA_DIR / "source_catalog.yaml"
    if not catalog_path.exists():
        return {"sources": []}
    with catalog_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


def load_preset(preset_name: str) -> dict:
    """Load a regional preset configuration.

    Args:
        preset_name: one of 'cn', 'jp', 'global'

    Returns the preset configuration dict.
    """
    preset_path = _DATA_DIR / "presets" / f"{preset_name}.yaml"
    if not preset_path.exists():
        raise FileNotFoundError(f"Preset not found: {preset_name}")
    with preset_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
