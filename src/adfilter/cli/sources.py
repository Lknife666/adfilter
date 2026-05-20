"""sources & init commands — manage rule sources from built-in catalog."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from . import app


@app.command(name="sources")
def cmd_sources(
    action: Annotated[str, typer.Argument(help="list|add|remove")] = "list",
    source_ids: Annotated[list[str] | None, typer.Argument(help="Source IDs to add/remove")] = None,
    region: Annotated[
        str | None, typer.Option("--region", "-r", help="Filter by region (cn, jp, global)")
    ] = None,
    config: Annotated[Path, typer.Option("--config", "-c")] = Path("config/application.yaml"),
) -> None:
    """Manage rule sources from the built-in catalog."""
    import yaml as _yaml

    c = Console()
    catalog_path = Path(__file__).parent.parent / "data" / "source_catalog.yaml"
    if not catalog_path.exists():
        typer.echo("source catalog not found", err=True)
        raise typer.Exit(code=2)
    catalog = _yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    sources = catalog.get("sources", [])

    if action == "list":
        t = Table(title="available sources", show_header=True)
        for col in ("id", "name", "region", "category", "format"):
            t.add_column(col)
        for s in sources:
            if region and s.get("region") != region:
                continue
            t.add_row(s["id"], s["name"], s.get("region", ""), s.get("category", ""), s.get("format", ""))
        c.print(t)
        c.print(f"\n[dim]Total: {len(sources)} sources. Use --region cn|jp|global to filter.[/dim]")

    elif action == "add":
        if not source_ids:
            typer.echo("specify source IDs to add", err=True)
            raise typer.Exit(code=1)
        # Load existing config
        if not config.exists():
            typer.echo(f"config not found: {config}", err=True)
            raise typer.Exit(code=2)
        cfg_data = _yaml.safe_load(config.read_text(encoding="utf-8")) or {}
        inner = cfg_data.setdefault("application", {}).setdefault("config", {})
        inp = inner.setdefault("input", {})
        rules = inp.setdefault("rule", {}).setdefault("default", [])
        existing_names = {r.get("name") for r in rules}
        added = 0
        for sid in source_ids:
            match = next((s for s in sources if s["id"] == sid), None)
            if not match:
                typer.echo(f"unknown source: {sid}", err=True)
                continue
            if match["id"] in existing_names or match["name"] in existing_names:
                typer.echo(f"already exists: {sid}")
                continue
            rules.append({"name": match["id"], "type": match["format"], "path": match["url"]})
            added += 1
            typer.echo(f"added: {match['name']} ({match['url']})")
        config.write_text(
            _yaml.dump(cfg_data, allow_unicode=True, default_flow_style=False), encoding="utf-8"
        )
        typer.echo(f"✓ {added} source(s) added to {config}")

    elif action == "remove":
        if not source_ids:
            typer.echo("specify source IDs to remove", err=True)
            raise typer.Exit(code=1)
        if not config.exists():
            typer.echo(f"config not found: {config}", err=True)
            raise typer.Exit(code=2)
        cfg_data = _yaml.safe_load(config.read_text(encoding="utf-8")) or {}
        inner = cfg_data.get("application", {}).get("config", {})
        rules = inner.get("input", {}).get("rule", {}).get("default", [])
        before = len(rules)
        rules[:] = [r for r in rules if r.get("name") not in source_ids]
        removed = before - len(rules)
        config.write_text(
            _yaml.dump(cfg_data, allow_unicode=True, default_flow_style=False), encoding="utf-8"
        )
        typer.echo(f"✓ {removed} source(s) removed from {config}")

    else:
        typer.echo(f"unknown action: {action}. Use list|add|remove", err=True)
        raise typer.Exit(code=1)


@app.command(name="score")
def cmd_score(
    cache_dir: Annotated[Path, typer.Option("--cache-dir", help="Score cache directory")] = Path(".cache"),
) -> None:
    """Show quality scores for all tracked rule sources."""
    from ..quality.source_scorer import SourceScorer

    c = Console()
    cache_file = cache_dir / "source_scores.json"
    scorer = SourceScorer(cache_file=cache_file)
    scores = scorer.get_scores()

    if not scores:
        c.print("[yellow]No score data found.[/yellow]")
        c.print("Scores are computed during builds. Run `adfilter run` first.")
        c.print(f"Cache file: {cache_file}")
        raise typer.Exit(code=0)

    t = Table(title="Source Quality Scores", show_header=True, header_style="bold cyan")
    t.add_column("Source", style="bold")
    t.add_column("Grade", justify="center")
    t.add_column("Score", justify="right")
    t.add_column("Avail", justify="right")
    t.add_column("Fresh", justify="right")
    t.add_column("Dead%", justify="right")
    t.add_column("FP%", justify="right")
    t.add_column("Uniq%", justify="right")

    grade_colors = {"A": "green", "B": "blue", "C": "yellow", "D": "red", "F": "bold red"}

    for source_id in sorted(scores.keys()):
        s = scores[source_id]
        color = grade_colors.get(s.grade, "white")
        t.add_row(
            source_id,
            f"[{color}]{s.grade}[/{color}]",
            f"{s.overall_score:.1f}",
            f"{s.availability:.0%}",
            f"{s.freshness:.0%}",
            f"{s.dead_domain_ratio:.1%}",
            f"{s.false_positive_rate:.1%}",
            f"{s.unique_contribution:.0%}",
        )

    c.print(t)
    c.print(f"\n[dim]Cache: {cache_file}[/dim]")


@app.command(name="init")
def cmd_init(
    preset: Annotated[str, typer.Option("--preset", "-p", help="Regional preset: cn, jp, global")] = "global",
    output: Annotated[Path, typer.Option("--output", "-o", help="Output config file path")] = Path(
        "config/application.yaml"
    ),
) -> None:
    """Initialize a new configuration from a regional preset."""
    import shutil

    preset_dir = Path(__file__).parent.parent / "data" / "presets"
    preset_file = preset_dir / f"{preset}.yaml"
    if not preset_file.exists():
        available = [p.stem for p in preset_dir.glob("*.yaml")]
        typer.echo(f"unknown preset: {preset}. Available: {', '.join(available)}", err=True)
        raise typer.Exit(code=1)

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        typer.echo(f"config already exists: {output}. Overwriting...", err=True)

    shutil.copy2(preset_file, output)
    typer.echo(f"✓ initialized config from preset '{preset}' → {output}")
