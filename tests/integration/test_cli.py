"""Integration tests for CLI commands."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from adfilter.cli import app


runner = CliRunner()


class TestValidateCommand:
    def test_validate_valid_config(self):
        result = runner.invoke(app, ["validate", "--config", "config/application.yaml"])
        assert result.exit_code == 0
        assert "OK" in result.output

    def test_validate_missing_config(self, tmp_path):
        result = runner.invoke(app, ["validate", "--config", str(tmp_path / "missing.yaml")])
        assert result.exit_code != 0


class TestFormatsCommand:
    def test_formats_lists_all(self):
        result = runner.invoke(app, ["formats"])
        assert result.exit_code == 0
        assert "easylist" in result.output.lower()
        assert "dns" in result.output.lower()
        assert "clash" in result.output.lower()
        assert "surge" in result.output.lower()
        assert "singbox" in result.output.lower()


class TestDoctorCommand:
    def test_doctor_checks_deps(self):
        result = runner.invoke(app, ["doctor", "--config", "config/application.yaml"])
        # May fail if config has issues, but should not crash
        assert result.exit_code in (0, 1)
        assert "Python" in result.output


class TestConvertCommand:
    def test_convert_hosts_to_clash(self, tmp_path):
        # Create a small hosts file
        src = tmp_path / "input.txt"
        src.write_text("0.0.0.0 ads.example.com\n0.0.0.0 tracker.example.org\n")
        dst = tmp_path / "output.yaml"

        result = runner.invoke(app, [
            "convert", str(src), str(dst),
            "--from", "hosts", "--to", "clash",
        ])
        assert result.exit_code == 0
        assert "converted" in result.output
        assert dst.exists()
        content = dst.read_text()
        assert "ads.example.com" in content

    def test_convert_easylist_to_dnsmasq(self, tmp_path):
        src = tmp_path / "input.txt"
        src.write_text("||ads.example.com^\n||tracker.example.org^\n")
        dst = tmp_path / "output.conf"

        result = runner.invoke(app, [
            "convert", str(src), str(dst),
            "--from", "easylist", "--to", "dnsmasq",
        ])
        assert result.exit_code == 0
        content = dst.read_text()
        assert "address=/" in content


class TestDiffCommand:
    def test_diff_identical_files(self, tmp_path):
        f = tmp_path / "rules.txt"
        f.write_text("||ads.example.com^\n||tracker.example.org^\n")

        result = runner.invoke(app, ["diff", str(f), str(f), "--format", "easylist"])
        assert result.exit_code == 0
        assert "unchanged" in result.output.lower()

    def test_diff_different_files(self, tmp_path):
        old = tmp_path / "old.txt"
        old.write_text("||ads.example.com^\n||removed.example.org^\n")
        new = tmp_path / "new.txt"
        new.write_text("||ads.example.com^\n||added.example.net^\n")

        result = runner.invoke(app, ["diff", str(old), str(new), "--format", "easylist"])
        assert result.exit_code == 0
        assert "added" in result.output.lower()
        assert "removed" in result.output.lower()


class TestCompletionCommand:
    def test_bash_completion(self):
        result = runner.invoke(app, ["completion", "bash"])
        assert result.exit_code == 0
        assert "COMPLETE" in result.output

    def test_unknown_shell(self):
        result = runner.invoke(app, ["completion", "unknown_shell"])
        assert result.exit_code != 0
