#!/usr/bin/env python3
"""Generate JSON Schema for application.yaml config file.

Usage:
    uv run python scripts/generate_schema.py
    # Outputs config/schema.json
"""

from __future__ import annotations

import json
from pathlib import Path

from adfilter.config import AppConfig


def main() -> None:
    schema = AppConfig.model_json_schema()
    schema["$schema"] = "http://json-schema.org/draft-07/schema#"
    schema["title"] = "adfilter configuration"
    schema["description"] = (
        "Configuration schema for adfilter. Use with VS Code YAML extension for autocompletion."
    )

    output_path = Path("config/schema.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
    print(f"✓ Generated {output_path} ({len(schema.get('properties', {}))} top-level properties)")


if __name__ == "__main__":
    main()
