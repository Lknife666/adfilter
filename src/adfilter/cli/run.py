"""run & validate commands — the core build pipeline."""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from datetime import UTC
from pathlib import Path
from typing import Annotated

import typer
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from .. import handler as _handler_pkg  # triggers handler registration
from ..config import AppConfig, OutputItem
from ..dns_prober import DnsProber
from ..logging_setup import setup_logging
from ..notifier.base import NotifyPayload, send_notifications
from ..optimizer import RuleOptimizer
from ..parser import Parser
from ..stats import BuildReport, OutputReport, SourceReport
from ..writer import (
    Batcher,
    OutputFile,
    create_temp,
    finalise,
    input_fingerprint,
    load_build_cache,
    save_build_cache,
)
from . import app, console


# ════════════════════════════ pipeline ══════════════════════════════
async def _run(config: AppConfig, *, report_path: Path | None) -> BuildReport:
    report = BuildReport()

    # feature #17 — incremental build
    fingerprint = input_fingerprint([(i.name, i.path) for i in config.input.input])
    report.fingerprint = fingerprint
    cache_path = Path(config.parser.incremental_cache_file)
    if config.parser.incremental_build:
        prev = load_build_cache(cache_path)
        if prev.get("fingerprint") == fingerprint and (
            Path(config.output.path).exists() and any(Path(config.output.path).iterdir())
        ):
            logging.info("incremental-build: inputs unchanged, skipping rebuild")
            report.incremental_skip = True
            return report

    # prober (optional)
    prober = DnsProber(config.parser.dns_probe) if config.parser.dns_probe.enable else None

    source_reports: dict[str, SourceReport] = {i.name: SourceReport(name=i.name) for i in config.input.input}

    def _on_source_done(s: object) -> None:
        rep = source_reports.get(s.name)  # type: ignore[attr-defined]
        if rep:
            rep.total = s.total  # type: ignore[attr-defined]
            rep.effective = s.effective  # type: ignore[attr-defined]
            rep.invalid = s.invalid  # type: ignore[attr-defined]
            rep.repeat = s.repeat  # type: ignore[attr-defined]
            rep.dead = s.dead  # type: ignore[attr-defined]
            rep.elapsed_ms = s.elapsed_ms  # type: ignore[attr-defined]

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

    # v0.3: load allowlist domains
    allowlist_domains: set[str] = set()
    if config.input.allowlist:
        for al_item in config.input.allowlist:
            try:
                al_path = Path(al_item.path)
                if al_path.exists():
                    for raw_line in al_path.read_text(encoding="utf-8").splitlines():
                        stripped = raw_line.strip()
                        if stripped and not stripped.startswith("#"):
                            allowlist_domains.add(stripped.lower())
            except Exception as e:  # noqa: BLE001
                logging.warning("allowlist load error %s: %s", al_item.path, e)
        if allowlist_domains:
            logging.info("loaded %d allowlist domains", len(allowlist_domains))

    # v0.3: build source→group mapping
    source_groups: dict[str, str] = {}
    for item in config.input.input:
        if item.group:
            source_groups[item.name] = item.group

    optimizer = (
        RuleOptimizer(config.optimizer, allowlist=allowlist_domains or None)
        if config.optimizer.enable
        else None
    )

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

    async def drain_source(item: object) -> None:
        async with sem:
            try:
                async for rule in parser.handle(item):  # type: ignore[arg-type]
                    # v0.3: attach source group to rule for filtering
                    rule.source_group = source_groups.get(item.name, "")  # type: ignore[attr-defined]
                    if optimizer is not None:
                        optimizer.feed(rule)
                    else:
                        await _emit(rule, config, batchers)
            except Exception as e:  # noqa: BLE001
                logging.error("[%s] source failed: %s", item.name, e)  # type: ignore[attr-defined]
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
        report.outputs.append(
            OutputReport(
                name=out.item.name,
                type=out.item.type.value,
                count=out.count,
                bytes=size,
                path=str(final),
            )
        )

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

    # v0.3: send success notifications
    if config.notifier.enable:
        payload = NotifyPayload(success=True, report=report)
        await send_notifications(config.notifier, payload)

    if report_path:
        report.write(report_path)
        logging.info("build report written to %s", report_path)
    return report


async def _emit(rule: object, config: AppConfig, batchers: dict[str, Batcher]) -> None:
    for out_item in config.output.files:
        if not _accepts(out_item, rule):
            continue
        handler = _handler_pkg.get_handler(out_item.type)
        line = handler.format(rule)  # type: ignore[arg-type]
        if line is None:
            continue
        await batchers[out_item.name].add(line)


def _accepts(out: OutputItem, rule: object) -> bool:
    if out.rule and rule.source_name not in out.rule:  # type: ignore[attr-defined]
        return False
    # v0.3: group-based filtering
    if out.groups and rule.source_name:  # type: ignore[attr-defined]
        rule_group = rule.source_group  # type: ignore[attr-defined]
        if rule_group and rule_group not in out.groups:
            return False
    return not (out.filter and rule.type not in out.filter)  # type: ignore[attr-defined]


# ════════════════════════════ commands ══════════════════════════════


@app.command(name="run")
def cmd_run(
    config: Annotated[Path, typer.Option("--config", "-c")] = Path("config/application.yaml"),
    log_level: Annotated[str, typer.Option("--log-level", "-l")] = "INFO",
    json_logs: Annotated[bool, typer.Option("--json-logs", help="Emit JSON log lines")] = False,
    progress: Annotated[bool, typer.Option("--progress/--no-progress", help="Show a progress bar")] = False,
    incremental: Annotated[
        bool, typer.Option("--incremental/--no-incremental", help="Skip run when inputs are unchanged")
    ] = False,
    report: Annotated[Path | None, typer.Option("--report", help="Write a JSON build report")] = None,
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

    async def _run_with_notifications() -> None:
        try:
            await _run(cfg, report_path=report)
        except Exception as e:  # noqa: BLE001
            # v0.3: send failure notifications within the same event loop
            if cfg.notifier.enable:
                payload = NotifyPayload(success=False, report=None, error_message=str(e))
                try:
                    await send_notifications(cfg.notifier, payload)
                except Exception:  # noqa: BLE001
                    pass
            raise

    try:
        asyncio.run(_run_with_notifications())
    except KeyboardInterrupt:
        typer.echo("interrupted", err=True)
        sys.exit(130)
    except Exception as e:  # noqa: BLE001
        typer.echo(f"build failed: {e}", err=True)
        raise typer.Exit(code=1) from None


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
