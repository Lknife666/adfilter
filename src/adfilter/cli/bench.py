"""bench command — measure rule-set effectiveness against baseline lists."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import app


@app.command(name="bench")
def cmd_bench(
    rule_dir: Annotated[
        Path, typer.Option("--rule-dir", "-d", help="Directory containing generated rule files")
    ] = Path("rule"),
    ad_list: Annotated[
        list[str] | None, typer.Option("--ad-list", "-a", help="URL of known-ad baseline list (repeatable)")
    ] = None,
    legit_list: Annotated[
        list[str] | None,
        typer.Option("--legit-list", "-l", help="URL of known-legit baseline list (repeatable)"),
    ] = None,
    builtin: Annotated[
        bool, typer.Option("--builtin/--no-builtin", help="Include built-in baseline lists")
    ] = True,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output results as JSON")] = False,
    timeout: Annotated[int, typer.Option("--timeout", "-t", help="HTTP timeout per request (seconds)")] = 60,
) -> None:
    """Benchmark rule-set against known-ad and known-legit baseline lists.

    Measures detection rate (how many known ads are blocked) and
    false-positive rate (how many legit domains are incorrectly blocked).

    \b
    Built-in baselines:
      Ad lists:    disconnect-ad, disconnect-tracking, steven-black-hosts
      Legit lists: tranco-10k, anudeep-whitelist

    \b
    Examples:
      adfilter bench --rule-dir rule/
      adfilter bench -d rule/ --ad-list https://example.com/ads.txt
      adfilter bench -d rule/ --no-builtin --ad-list ./my-ads.txt
    """
    from ..bench import (
        BUILTIN_AD_BASELINES,
        BUILTIN_LEGIT_BASELINES,
        run_bench,
    )

    if not rule_dir.exists():
        typer.echo(f"Rule directory not found: {rule_dir}", err=True)
        raise typer.Exit(code=2)

    # Build baseline maps
    ad_baselines: dict[str, str] = {}
    legit_baselines: dict[str, str] = {}

    if builtin:
        ad_baselines.update(BUILTIN_AD_BASELINES)
        legit_baselines.update(BUILTIN_LEGIT_BASELINES)

    # Custom lists from CLI
    if ad_list:
        for i, url in enumerate(ad_list):
            name = f"custom-ad-{i}" if url.startswith("http") else Path(url).stem
            ad_baselines[name] = url
    if legit_list:
        for i, url in enumerate(legit_list):
            name = f"custom-legit-{i}" if url.startswith("http") else Path(url).stem
            legit_baselines[name] = url

    if not ad_baselines and not legit_baselines:
        typer.echo("No baselines configured. Use --builtin or provide --ad-list/--legit-list.", err=True)
        raise typer.Exit(code=2)

    # Run bench
    report = asyncio.run(
        run_bench(
            rule_dir,
            ad_baselines=ad_baselines or None,
            legit_baselines=legit_baselines or None,
            timeout=timeout,
        )
    )

    if json_output:
        typer.echo(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        return

    # Rich output
    c = Console()

    # Summary panel
    def grade_detection(rate: float) -> str:
        if rate >= 0.90:
            return "[green]Excellent[/green]"
        if rate >= 0.75:
            return "[green]Good[/green]"
        if rate >= 0.60:
            return "[yellow]Fair[/yellow]"
        return "[red]Needs Work[/red]"

    def grade_fp(rate: float) -> str:
        if rate <= 0.001:
            return "[green]Excellent[/green]"
        if rate <= 0.005:
            return "[green]Good[/green]"
        if rate <= 0.01:
            return "[yellow]Fair[/yellow]"
        return "[red]Too High[/red]"

    summary_lines = [
        f"  Rules Loaded:       [bold]{report.rule_count:,}[/bold]",
        f"  Duration:           {report.elapsed_ms:,}ms",
        "",
        f"  Detection Rate:     [bold]{report.detection_rate:.1%}[/bold]  {grade_detection(report.detection_rate)}",
        f"  False Positive Rate: [bold]{report.false_positive_rate:.2%}[/bold]  {grade_fp(report.false_positive_rate)}",
    ]
    c.print(Panel("\n".join(summary_lines), title="Bench Summary", border_style="cyan"))

    # Detail table
    t = Table(title="Baseline Results")
    t.add_column("Baseline", style="bold")
    t.add_column("Type")
    t.add_column("Size", justify="right")
    t.add_column("Matched", justify="right")
    t.add_column("Rate", justify="right")
    t.add_column("Grade")

    for r in report.results:
        rate_str = f"{r.rate:.1%}"
        grade = grade_detection(r.rate) if r.baseline_type == "ad" else grade_fp(r.rate)
        t.add_row(
            r.baseline_name,
            r.baseline_type,
            f"{r.baseline_size:,}",
            f"{r.matched:,}",
            rate_str,
            grade,
        )

    c.print(t)

    # Show concerning false positives
    legit_results = [r for r in report.results if r.baseline_type == "legit" and r.sample_matched]
    if legit_results:
        c.print("\n[bold red]⚠ Potential False Positives (legit domains being blocked):[/bold red]")
        for r in legit_results:
            if r.sample_matched:
                c.print(f"  [dim]{r.baseline_name}:[/dim] {', '.join(r.sample_matched[:5])}")

    # Show sample misses from ad lists
    ad_results = [r for r in report.results if r.baseline_type == "ad" and r.rate < 0.95]
    if ad_results:
        c.print("\n[bold yellow]💡 Detection Gaps (known ads not blocked):[/bold yellow]")
        for r in ad_results:
            if r.sample_unmatched:
                c.print(f"  [dim]{r.baseline_name} ({r.rate:.1%}):[/dim] {', '.join(r.sample_unmatched[:5])}")
