"""Integration tests for sources and init commands (v0.4)."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from adfilter.__main__ import app

runner = CliRunner()


class TestSourcesCommand:
    def test_sources_list(self):
        result = runner.invoke(app, ["sources", "list"])
        assert result.exit_code == 0
        assert "anti-ad" in result.output.lower() or "anti-AD" in result.output

    def test_sources_list_region_cn(self):
        result = runner.invoke(app, ["sources", "list", "--region", "cn"])
        assert result.exit_code == 0
        assert "anti" in result.output.lower()

    def test_sources_add(self, tmp_path):
        # Create a minimal config
        config = tmp_path / "config.yaml"
        config.write_text(
            "application:\n  config:\n    input:\n      rule:\n        default: []\n"
            "    output:\n      path: ./rule\n      files:\n"
            "        - {name: dns.txt, type: dns}\n"
        )
        result = runner.invoke(app, ["sources", "add", "anti-ad", "--config", str(config)])
        assert result.exit_code == 0
        assert "added" in result.output.lower()
        # Verify it's in config
        content = config.read_text()
        assert "anti-ad.net" in content

    def test_sources_remove(self, tmp_path):
        config = tmp_path / "config.yaml"
        config.write_text(
            "application:\n  config:\n    input:\n      rule:\n        default:\n"
            "          - {name: anti-ad, type: easylist, path: 'https://anti-ad.net/easylist.txt'}\n"
            "    output:\n      path: ./rule\n      files:\n"
            "        - {name: dns.txt, type: dns}\n"
        )
        result = runner.invoke(app, ["sources", "remove", "anti-ad", "--config", str(config)])
        assert result.exit_code == 0
        assert "removed" in result.output.lower()


class TestInitCommand:
    def test_init_cn_preset(self, tmp_path):
        output = tmp_path / "config.yaml"
        result = runner.invoke(app, ["init", "--preset", "cn", "--output", str(output)])
        assert result.exit_code == 0
        assert output.exists()
        content = output.read_text()
        assert "anti-ad" in content

    def test_init_jp_preset(self, tmp_path):
        output = tmp_path / "config.yaml"
        result = runner.invoke(app, ["init", "--preset", "jp", "--output", str(output)])
        assert result.exit_code == 0
        content = output.read_text()
        assert "280blocker" in content

    def test_init_global_preset(self, tmp_path):
        output = tmp_path / "config.yaml"
        result = runner.invoke(app, ["init", "--preset", "global", "--output", str(output)])
        assert result.exit_code == 0
        content = output.read_text()
        assert "easylist" in content

    def test_init_unknown_preset(self, tmp_path):
        output = tmp_path / "config.yaml"
        result = runner.invoke(app, ["init", "--preset", "unknown_xyz", "--output", str(output)])
        assert result.exit_code != 0
