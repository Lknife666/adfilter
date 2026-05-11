"""CLI entry point.

This file wires together *all* adfilter features. Commands
beyond ``run``/``validate`` are differentiators vs. the upstream Java
project:

  * convert   — one-shot format conversion (no config file needed)
  * diff      — compare two rule files, by rule identity not by text
  * doctor    — environment / config / source health check
  * serve     — tiny local HTTP server that exposes generated files
  * stats     — render the last build report as a table
  * completion— emit shell completion
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from datetime import UTC
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from . import handler as _handler_pkg  # triggers handler registration
from .config import AppConfig, OutputItem
from .constants import RuleSet
from .dns_prober import DnsProber
from .logging_setup import setup_logging
from .optimizer import RuleOptimizer
from .parser import Parser
from .stats import BuildReport, OutputReport, SourceReport
from .writer import (
    Batcher,
    OutputFile,
    create_temp,
    finalise,
    input_fingerprint,
    load_build_cache,
    save_build_cache,
)

app = typer.Typer(
    add_completion=False,
    help="Ad filter rule aggregator & converter — Python edition",
    no_args_is_help=True,
)

console = Console(stderr=True)


# ════════════════════════════ run ═══════════════════════════════════
async def _run(config: AppConfig, *, report_path: Path | None) -> BuildReport:
    report = BuildReport()

    # feature #17 — incremental build
    fingerprint = input_fingerprint([(i.name, i.path) for i in config.input.input])
    report.fingerprint = fingerprint
    cache_path = Path(config.parser.incremental_cache_file)
    if config.parser.incremental_build:
        prev = load_build_cache(cache_path)
        if prev.get("fingerprint") == fingerprint and (
            Path(config.output.path).exists()
            and any(Path(config.output.path).iterdir())
        ):
            logging.info("incremental-build: inputs unchanged, skipping rebuild")
            report.incremental_skip = True
            return report

    # prober (optional)
    prober = DnsProber(config.parser.dns_probe) if config.parser.dns_probe.enable else None

    source_reports: dict[str, SourceReport] = {
        i.name: SourceReport(name=i.name) for i in config.input.input
    }

    def _on_source_done(s) -> None:  # noqa: ANN001
        rep = source_reports.get(s.name)
        if rep:
            rep.total = s.total
            rep.effective = s.effective
            rep.invalid = s.invalid
            rep.repeat = s.repeat
            rep.elapsed_ms = s.elapsed_ms

    parser = Parser(
        fetcher_config=config.fetcher,
        parser_config=config.parser,
        prober=prober,
        normalize_idn=config.optimizer.normalize_idn,
        on_source_done=_on_source_done,
    )

    # staging
    outs: dict[str, OutputFile] = {o.name: create_temp(o) for o in config.output.files}
    batchers: dict[str, Batcher] = {name: Batcher(output=of) for name, of in outs.items()}

    optimizer = RuleOptimizer(config.optimizer) if config.optimizer.enable else None

    t0 = time.monotonic()

    # #12 — bounded concurrency across sources
    sem = asyncio.Semaphore(max(1, config.fetcher.http.max_concurrency))

    # #18 — progress bar
    use_progress = config.parser.progress and sys.stderr.isatty()
    progress: Progress | None = None
    task_id: object | None = None
    if use_progress:
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold]processing sources"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            console=console,
        )
        progress.start()
        task_id = progress.add_task("", total=len(config.input.input))

    async def drain_source(item) -> None:  # noqa: ANN001
        async with sem:
            try:
                async for rule in parser.handle(item):
                    if optimizer is not None:
                        optimizer.feed(rule)
                    else:
                        await _emit(rule, config, batchers)
            finally:
                if progress and task_id is not None:
                    progress.update(task_id, advance=1)

    try:
        async with asyncio.TaskGroup() as tg:
            for item in config.input.input:
                tg.create_task(drain_source(item))

        # optimizer flushes after all sources finish
        if optimizer is not None:
            for r in optimizer.drain():
                await _emit(r, config, batchers)

        for b in batchers.values():
            await b.flush()
    finally:
        if progress:
            progress.stop()

    # finalise
    target_dir = Path(config.output.path).expanduser().resolve()
    for out in outs.values():
        final = await finalise(out, target_dir, config.output.file_header)
        size = final.stat().st_size
        logging.info("wrote %s (%d rules, %d bytes)", final, out.count, size)
        report.outputs.append(OutputReport(
            name=out.item.name, type=out.item.type.value,
            count=out.count, bytes=size, path=str(final),
        ))

    if prober:
        logging.info("dns prober stats: %s", prober.stats())
        await prober.close()

    # persist incremental-build fingerprint (only when outputs were written)
    if config.parser.incremental_build:
        save_build_cache(cache_path, {"fingerprint": fingerprint})

    report.sources = list(source_reports.values())
    report.elapsed_ms = int((time.monotonic() - t0) * 1000)
    from datetime import datetime
    report.finished_at = datetime.now(tz=UTC).isoformat()

    if report_path:
        report.write(report_path)
        logging.info("build report written to %s", report_path)
    return report


async def _emit(rule, config: AppConfig, batchers: dict[str, Batcher]) -> None:  # noqa: ANN001
    for out_item in config.output.files:
        if not _accepts(out_item, rule):
            continue
        handler = _handler_pkg.get_handler(out_item.type)
        line = handler.format(rule)
        if line is None:
            continue
        await batchers[out_item.name].add(line)


def _accepts(out: OutputItem, rule) -> bool:  # noqa: ANN001
    if out.rule and rule.source_name not in out.rule:
        return False
    return not (out.filter and rule.type not in out.filter)


@app.command(name="run")
def cmd_run(
    config: Annotated[Path, typer.Option("--config", "-c")] = Path("config/application.yaml"),
    log_level: Annotated[str, typer.Option("--log-level", "-l")] = "INFO",
    json_logs: Annotated[bool, typer.Option("--json-logs", help="Emit JSON log lines")] = False,
    progress: Annotated[bool, typer.Option("--progress/--no-progress",
                                           help="Show a progress bar")] = False,
    incremental: Annotated[bool, typer.Option("--incremental/--no-incremental",
                                              help="Skip run when inputs are unchanged")] = False,
    report: Annotated[Path | None, typer.Option("--report",
                                                help="Write a JSON build report")] = None,
) -> None:
    """Run the full fetch/parse/emit pipeline."""
    try:
        cfg = AppConfig.from_yaml(config)
    except FileNotFoundError:
        typer.echo(f"config file not found: {config}", err=True)
        raise typer.Exit(code=2) from None
    except Exception as e:  # noqa: BLE001
        typer.echo(f"config error: {e}", err=True)
        raise typer.Exit(code=2) from None

    # CLI flags override config
    cfg.parser.json_logs = json_logs or cfg.parser.json_logs
    cfg.parser.progress = progress or cfg.parser.progress
    cfg.parser.incremental_build = incremental or cfg.parser.incremental_build
    setup_logging(log_level, json_logs=cfg.parser.json_logs)

    try:
        asyncio.run(_run(cfg, report_path=report))
    except KeyboardInterrupt:
        typer.echo("interrupted", err=True)
        sys.exit(130)


@app.command(name="validate")
def cmd_validate(
    config: Annotated[Path, typer.Option("--config", "-c")] = Path("config/application.yaml"),
) -> None:
    """Validate the config file and exit."""
    setup_logging("INFO")
    try:
        cfg = AppConfig.from_yaml(config)
    except Exception as e:  # noqa: BLE001
        typer.echo(f"invalid: {e}", err=True)
        raise typer.Exit(code=1) from None
    typer.echo(f"OK — {len(cfg.input.input)} inputs, {len(cfg.output.files)} outputs")


# ════════════════════════════ convert (#1) ══════════════════════════
@app.command(name="convert")
def cmd_convert(
    source: Annotated[Path, typer.Argument(help="Input file path")],
    target: Annotated[Path, typer.Argument(help="Output file path")],
    from_fmt: Annotated[RuleSet, typer.Option("--from", "-f",
                                              help="Source format")] = RuleSet.EASYLIST,
    to_fmt: Annotated[RuleSet, typer.Option("--to", "-t",
                                            help="Target format")] = RuleSet.HOSTS,
) -> None:
    """One-shot file-to-file conversion between any two formats.

    Example:
        adfilter convert hosts.txt clash.yaml --from hosts --to clash
    """
    setup_logging("WARNING")
    src_handler = _handler_pkg.get_handler(from_fmt)
    dst_handler = _handler_pkg.get_handler(to_fmt)

    count = 0
    with source.open("r", encoding="utf-8", errors="replace") as sf:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as tf:
            if head := dst_handler.head_format():
                tf.write(head + "\n")
            for ln in sf:
                line = ln.rstrip("\r\n")
                if not line or src_handler.is_comment(line):
                    continue
                try:
                    rule = src_handler.parse(line)
                except Exception:  # noqa: BLE001
                    continue
                if rule.is_empty():
                    continue
                out_line = dst_handler.format(rule)
                if out_line is None:
                    continue
                tf.write(out_line)
                tf.write("\n")
                count += 1
    typer.echo(f"converted {count} rules: {source} ({from_fmt.value}) -> "
               f"{target} ({to_fmt.value})")


# ════════════════════════════ diff (#3) ═════════════════════════════
def _collect_hashes(path: Path, fmt: RuleSet) -> set[int]:
    handler = _handler_pkg.get_handler(fmt)
    hashes: set[int] = set()
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for ln in f:
            line = ln.rstrip("\r\n")
            if not line or handler.is_comment(line):
                continue
            try:
                r = handler.parse(line)
            except Exception:  # noqa: BLE001
                continue
            if r.is_empty():
                continue
            hashes.add(r.murmur3_hash())
    return hashes


@app.command(name="diff")
def cmd_diff(
    old: Annotated[Path, typer.Argument(help="Previous rule file")],
    new: Annotated[Path, typer.Argument(help="New rule file")],
    fmt: Annotated[RuleSet, typer.Option("--format", "-f",
                                         help="Format of both files")] = RuleSet.EASYLIST,
) -> None:
    """Compare two rule files by rule identity (not by byte-level text)."""
    setup_logging("WARNING")
    old_h = _collect_hashes(old, fmt)
    new_h = _collect_hashes(new, fmt)
    added = len(new_h - old_h)
    removed = len(old_h - new_h)
    unchanged = len(old_h & new_h)
    table = Table(title="rule diff", show_header=True)
    table.add_column("metric"); table.add_column("count", justify="right")
    table.add_row("unchanged", str(unchanged))
    table.add_row("[green]added[/]", str(added))
    table.add_row("[red]removed[/]", str(removed))
    Console().print(table)


# ════════════════════════════ stats (#4) ════════════════════════════
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


# ════════════════════════════ doctor (#6) ═══════════════════════════
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


# ════════════════════════════ serve (#2) ════════════════════════════
@app.command(name="serve")
def cmd_serve(
    directory: Annotated[Path, typer.Option("--dir", "-d",
                                            help="Directory to serve")] = Path("rule"),
    host: Annotated[str, typer.Option("--host")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", "-p")] = 8787,
) -> None:
    """Serve the generated rule directory over HTTP (handy for LAN subscribe URLs)."""
    import http.server
    import socketserver

    directory = directory.expanduser().resolve()
    if not directory.is_dir():
        typer.echo(f"not a directory: {directory}", err=True)
        raise typer.Exit(code=2)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(directory), **kw)

    with socketserver.ThreadingTCPServer((host, port), Handler) as httpd:
        typer.echo(f"serving {directory} on http://{host}:{port}  (Ctrl-C to stop)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            typer.echo("\nstopped")


# ════════════════════════════ completion (#5) ═══════════════════════
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


# ════════════════════════════ list-formats (bonus) ══════════════════
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
    }
    for rs, desc in known.items():
        t.add_row(rs.value, "✓", "✓", desc)
    c.print(t)


if __name__ == "__main__":
    app()
