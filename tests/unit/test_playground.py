"""Tests for the playground CLI module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from adfilter.cli.playground import _handle_query, _handle_whatif_add, _handle_whatif_remove
from adfilter.trie import DomainTrie


class TestPlaygroundHelpers:
    def _setup_trie(self):
        trie = DomainTrie()
        trie.insert("ads.example.com")
        trie.insert("tracker.net")
        origins = {"ads.example.com": "dns.txt", "tracker.net": "hosts.txt"}
        return trie, origins

    def test_query_exact_match(self, capsys):
        from rich.console import Console

        trie, origins = self._setup_trie()
        c = Console(file=open("/dev/null", "w"))
        # Just verify no crash
        _handle_query(c, trie, origins, "ads.example.com")

    def test_query_suffix_match(self, capsys):
        from rich.console import Console

        trie, origins = self._setup_trie()
        c = Console(file=open("/dev/null", "w"))
        _handle_query(c, trie, origins, "sub.tracker.net")

    def test_query_not_blocked(self, capsys):
        from rich.console import Console

        trie, origins = self._setup_trie()
        c = Console(file=open("/dev/null", "w"))
        _handle_query(c, trie, origins, "google.com")

    def test_whatif_add_redundant(self, capsys):
        from rich.console import Console

        trie, _ = self._setup_trie()
        c = Console(file=open("/dev/null", "w"))
        _handle_whatif_add(c, trie, "sub.tracker.net")

    def test_whatif_add_new(self, capsys):
        from rich.console import Console

        trie, _ = self._setup_trie()
        c = Console(file=open("/dev/null", "w"))
        _handle_whatif_add(c, trie, "newdomain.com")

    def test_whatif_remove_direct(self, capsys):
        from rich.console import Console

        trie, origins = self._setup_trie()
        c = Console(file=open("/dev/null", "w"))
        _handle_whatif_remove(c, trie, origins, "ads.example.com")

    def test_whatif_remove_parent(self, capsys):
        from rich.console import Console

        trie, origins = self._setup_trie()
        c = Console(file=open("/dev/null", "w"))
        _handle_whatif_remove(c, trie, origins, "sub.tracker.net")

    def test_whatif_remove_not_found(self, capsys):
        from rich.console import Console

        trie, origins = self._setup_trie()
        c = Console(file=open("/dev/null", "w"))
        _handle_whatif_remove(c, trie, origins, "nothere.com")


class TestPlaygroundCommand:
    def test_playground_missing_dir(self):
        from typer.testing import CliRunner

        from adfilter.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["playground", "--rule-dir", "/nonexistent/path"])
        assert result.exit_code == 2

    def test_playground_loads_and_quits(self, tmp_path):
        from typer.testing import CliRunner

        from adfilter.cli import app

        # Create a minimal dns.txt
        (tmp_path / "dns.txt").write_text("||ads.example.com^\n||tracker.net^\n")
        runner = CliRunner()
        result = runner.invoke(app, ["playground", "--rule-dir", str(tmp_path)], input="quit\n")
        assert result.exit_code == 0
        assert "Loaded" in result.output

    def test_playground_query_command(self, tmp_path):
        from typer.testing import CliRunner

        from adfilter.cli import app

        (tmp_path / "dns.txt").write_text("||ads.example.com^\n")
        runner = CliRunner()
        result = runner.invoke(
            app, ["playground", "--rule-dir", str(tmp_path)], input="query ads.example.com\nquit\n"
        )
        assert result.exit_code == 0
        assert "BLOCKED" in result.output

    def test_playground_help_command(self, tmp_path):
        from typer.testing import CliRunner

        from adfilter.cli import app

        (tmp_path / "dns.txt").write_text("||test.com^\n")
        runner = CliRunner()
        result = runner.invoke(app, ["playground", "--rule-dir", str(tmp_path)], input="help\nquit\n")
        assert result.exit_code == 0
        assert "query" in result.output


class TestSchemaGeneration:
    def test_schema_file_exists(self):
        schema_path = Path("config/schema.json")
        assert schema_path.exists()

    def test_schema_is_valid_json(self):
        import json

        schema_path = Path("config/schema.json")
        data = json.loads(schema_path.read_text(encoding="utf-8"))
        assert "$schema" in data
        assert data["title"] == "adfilter configuration"
        assert "properties" in data


class TestStatsEfficiency:
    def test_stats_efficiency_flag(self, tmp_path):
        import json

        from typer.testing import CliRunner

        from adfilter.cli import app

        report = {
            "total_rules": 1000,
            "sources": [
                {"name": "a", "total": 600, "effective": 500, "invalid": 50, "repeat": 50, "elapsed_ms": 100},
                {
                    "name": "b",
                    "total": 700,
                    "effective": 500,
                    "invalid": 100,
                    "repeat": 100,
                    "elapsed_ms": 200,
                },
            ],
        }
        report_path = tmp_path / "build-report.json"
        report_path.write_text(json.dumps(report))

        runner = CliRunner()
        result = runner.invoke(app, ["stats", str(report_path), "--efficiency"])
        assert result.exit_code == 0
        assert "Efficiency" in result.output
