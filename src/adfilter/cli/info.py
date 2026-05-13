"""Informational commands — stats, doctor, formats, completion."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from ..config import AppConfig
from ..constants import RuleSet
from ..logging_setup import setup_logging
from . import app


@app.command(name="stats")
def cmd_stats(
    report: Annotated[Path, typer.Argument(help="Path to build-report JSON")],
) -> None:
    """Render a build report as a pretty table."""
    if not report.exists():
        typer.echo(f"not found: {report}", err=True)
        raise typer.Exit(code=2)
    data = json.loads(report.read_text(encoding="utf-8"))
    c = Console()

    c.print(f"[bold]build report[/]  fingerprint={data.get('fingerprint','')[:12]}  "
            f"elapsed_ms={data.get('elapsed_ms')}")
    if data.get("incremental_skip"):
        c.print("[yellow]incremental: SKIPPED[/]")

    if srcs := data.get("sources"):
        t = Table(title="sources")
        for col in ("name", "total", "effective", "invalid", "repeat", "elapsed_ms"):
            t.add_column(col)
        for s in srcs:
            t.add_row(s["name"], str(s["total"]), str(s["effective"]),
                      str(s["invalid"]), str(s["repeat"]), str(s["elapsed_ms"]))
        c.print(t)

    if outs := data.get("outputs"):
        t = Table(title="outputs")
        for col in ("name", "type", "count", "bytes", "path"):
            t.add_column(col)
        for o in outs:
            t.add_row(o["name"], o["type"], str(o["count"]), str(o["bytes"]), o["path"])
        c.print(t)


@app.command(name="doctor")
def cmd_doctor(
    config: Annotated[Path, typer.Option("--config", "-c")] = Path("config/application.yaml"),
) -> None:
    """Environment + config sanity check."""
    import platform
    setup_logging("INFO")
    c = Console()
    c.print(f"Python {platform.python_version()} ({platform.platform()})")
    # try imports
    problems: list[str] = []
    for mod in ("aiohttp", "aiodns", "mmh3", "pydantic", "yaml", "typer", "rich"):
        try:
            __import__(mod)
            c.print(f"  [green]ok[/]   {mod}")
        except ImportError as e:
            problems.append(f"missing: {mod} ({e})")
            c.print(f"  [red]FAIL[/] {mod}: {e}")

    try:
        cfg = AppConfig.from_yaml(config)
        c.print(f"[green]config ok[/] — {len(cfg.input.input)} inputs, "
                f"{len(cfg.output.files)} outputs")
    except Exception as e:  # noqa: BLE001
        problems.append(f"config: {e}")
        c.print(f"[red]config FAIL[/] {e}")

    if problems:
        raise typer.Exit(code=1)


@app.command(name="formats")
def cmd_formats() -> None:
    """List every rule format adfilter can read/write."""
    c = Console()
    t = Table(title="supported formats", show_header=True)
    t.add_column("format"); t.add_column("input"); t.add_column("output"); t.add_column("description")
    known = {
        RuleSet.EASYLIST: "EasyList / ABP / AdGuard",
        RuleSet.DNS:      "AdGuard Home",
        RuleSet.DNSMASQ:  "dnsmasq address=/…/ip",
        RuleSet.SMARTDNS: "smartdns address /…/#",
        RuleSet.CLASH:    "Clash domain rule-provider",
        RuleSet.HOSTS:    "/etc/hosts",
        RuleSet.SURGE:    "Surge domain-set",
        RuleSet.SINGBOX:  "sing-box rule-set (JSON)",
        RuleSet.MIKROTIK: "MikroTik RouterOS /ip dns static",
        RuleSet.UNBOUND:  "Unbound local-zone",
        RuleSet.QUANTUMULT: "Quantumult X filter",
        RuleSet.LOON:     "Loon plugin rules",
    }
    for rs, desc in known.items():
        t.add_row(rs.value, "✓", "✓", desc)
    c.print(t)


@app.command(name="completion")
def cmd_completion(
    shell: Annotated[str, typer.Argument(help="bash|zsh|fish|powershell")] = "bash",
) -> None:
    """Print a shell-completion script (source it to get tab completion)."""
    script = {
        "bash": 'eval "$(_ADFILTER_COMPLETE=bash_source adfilter)"',
        "zsh":  'eval "$(_ADFILTER_COMPLETE=zsh_source adfilter)"',
        "fish": '_ADFILTER_COMPLETE=fish_source adfilter | source',
        "powershell": 'Invoke-Expression (& { (_ADFILTER_COMPLETE=powershell_source adfilter) })',
    }.get(shell)
    if not script:
        typer.echo(f"unknown shell: {shell}", err=True); raise typer.Exit(code=2)
    typer.echo(script)
