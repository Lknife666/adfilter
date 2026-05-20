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
    efficiency: Annotated[bool, typer.Option("--efficiency", "-e", help="Show efficiency metrics")] = False,
) -> None:
    """Render a build report as a pretty table."""
    if not report.exists():
        typer.echo(f"not found: {report}", err=True)
        raise typer.Exit(code=2)
    data = json.loads(report.read_text(encoding="utf-8"))
    c = Console()

    if efficiency:
        _show_efficiency(c, data, report.parent)
        return

    c.print(
        f"[bold]build report[/]  fingerprint={data.get('fingerprint', '')[:12]}  "
        f"elapsed_ms={data.get('elapsed_ms')}"
    )
    if data.get("incremental_skip"):
        c.print("[yellow]incremental: SKIPPED[/]")

    if srcs := data.get("sources"):
        t = Table(title="sources")
        for col in ("name", "total", "effective", "invalid", "repeat", "dead", "elapsed_ms"):
            t.add_column(col)
        for s in srcs:
            t.add_row(
                s["name"],
                str(s["total"]),
                str(s["effective"]),
                str(s["invalid"]),
                str(s["repeat"]),
                str(s.get("dead", 0)),
                str(s["elapsed_ms"]),
            )
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
        c.print(f"[green]config ok[/] — {len(cfg.input.input)} inputs, {len(cfg.output.files)} outputs")
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
    t.add_column("format")
    t.add_column("input")
    t.add_column("output")
    t.add_column("description")
    known = {
        RuleSet.EASYLIST: "EasyList / ABP / AdGuard",
        RuleSet.DNS: "AdGuard Home",
        RuleSet.DNSMASQ: "dnsmasq address=/…/ip",
        RuleSet.SMARTDNS: "smartdns address /…/#",
        RuleSet.CLASH: "Clash domain rule-provider",
        RuleSet.HOSTS: "/etc/hosts",
        RuleSet.SURGE: "Surge domain-set",
        RuleSet.SINGBOX: "sing-box rule-set (JSON)",
        RuleSet.MIKROTIK: "MikroTik RouterOS /ip dns static",
        RuleSet.UNBOUND: "Unbound local-zone",
        RuleSet.QUANTUMULT: "Quantumult X filter",
        RuleSet.LOON: "Loon plugin rules",
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
        "zsh": 'eval "$(_ADFILTER_COMPLETE=zsh_source adfilter)"',
        "fish": "_ADFILTER_COMPLETE=fish_source adfilter | source",
        "powershell": "Invoke-Expression (& { (_ADFILTER_COMPLETE=powershell_source adfilter) })",
    }.get(shell)
    if not script:
        typer.echo(f"unknown shell: {shell}", err=True)
        raise typer.Exit(code=2)
    typer.echo(script)


def _show_efficiency(c: Console, data: dict, rule_dir: Path) -> None:
    """Display efficiency metrics panel.

    Definitions (matching the build pipeline in ``parser.py``):

    * ``effective`` — rules that parsed, were not duplicates, and (when
      DNS-prober is enabled) resolved successfully. These are the rules
      that actually ended up in the output files.
    * ``invalid``   — rules that the handler could not parse, or that
      were filtered out by length/exclude/empty checks.
    * ``repeat``    — rules whose hash had already been emitted by an
      earlier source. *Cross-source* duplicates, attributed to whichever
      source happened to finish second; NOT internal duplicates.
    * ``dead``      — rules whose target domain returned NXDOMAIN
      during DNS probing. Always 0 unless ``parser.dns_probe.enable``
      is true.

    The denominator for percentages is the *raw input* size:
    ``effective + invalid + repeat + dead``.
    """
    from rich.panel import Panel

    from ..quality.efficiency import EfficiencyMetrics

    sources = data.get("sources", [])
    effective = sum(s.get("effective", 0) for s in sources)
    invalid = sum(s.get("invalid", 0) for s in sources)
    repeat = sum(s.get("repeat", 0) for s in sources)
    dead = sum(s.get("dead", 0) for s in sources)

    raw_total = effective + invalid + repeat + dead
    has_dns_probe = dead > 0

    metrics = EfficiencyMetrics(
        total_rules=raw_total,
        live_domains=effective,  # only "effective" survived all checks
        dead_domains=dead,  # NXDOMAIN, requires DNS probe
        redundant_rules=repeat,  # cross-source duplicates
        unique_rules=effective,
        invalid_rules=invalid,  # parse failures
    )

    # Progress bar helper
    def bar(ratio: float, width: int = 20) -> str:
        ratio = max(0.0, min(1.0, ratio))
        filled = int(ratio * width)
        return "█" * filled + "░" * (width - filled)

    def pct(n: int) -> float:
        return n / raw_total if raw_total else 0.0

    lines = [
        f"  Raw Input:        [bold]{raw_total:,}[/bold] (effective + invalid + repeat + dead)",
        f"  Effective:        [green]{effective:,}[/green] ({pct(effective):.1%})  {bar(pct(effective))}",
        f"  Invalid (parse):  [red]{invalid:,}[/red] ({pct(invalid):.1%})  {bar(pct(invalid))}",
        f"  Repeat (x-src):   [yellow]{repeat:,}[/yellow] ({pct(repeat):.1%})  {bar(pct(repeat))}",
    ]
    if has_dns_probe:
        lines.append(f"  Dead (NXDOMAIN):  [red]{dead:,}[/red] ({pct(dead):.1%})  {bar(pct(dead))}")
    else:
        lines.append("  Dead (NXDOMAIN):  [dim]not measured (enable parser.dns_probe to populate)[/dim]")

    lines += [
        "",
        f"  Efficiency Score: [bold]{metrics.efficiency_score:.1%}[/bold]  {metrics.grade}",
        f"  Bloat Ratio:      {metrics.bloat_ratio:.1%}  (invalid + repeat + dead) / raw",
    ]

    if invalid > 0:
        lines.append(
            f"  [dim]💡 {invalid:,} rules failed to parse — consider auditing the source format.[/dim]"
        )
    if repeat > 0:
        lines.append(
            f"  [dim]💡 {repeat:,} cross-source duplicates: a rule already emitted by an earlier "
            "source. Order-dependent; not an indictment of any single source.[/dim]"
        )
    if has_dns_probe and dead > 0:
        lines.append(f"  [dim]💡 {dead:,} dead domains could be pruned from upstream sources.[/dim]")

    c.print(Panel("\n".join(lines), title="Rule Efficiency Report", border_style="cyan"))
