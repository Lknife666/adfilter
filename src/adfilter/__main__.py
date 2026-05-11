"""CLI entry point."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.logging import RichHandler

from . import handler as _handler_pkg  # noqa: F401 - trigger handler registration
from .config import AppConfig, OutputItem
from .dns_prober import DnsProber
from .parser import Parser
from .writer import Batcher, OutputFile, create_temp, finalise

app = typer.Typer(add_completion=False, help="Ad filter rule aggregator & converter")


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, markup=True)],
    )


async def _run(config: AppConfig) -> None:
    # prober
    prober = DnsProber(config.parser.dns_probe) if config.parser.dns_probe.enable else None

    parser = Parser(
        fetcher_config=config.fetcher,
        parser_config=config.parser,
        prober=prober,
    )

    # one temp-file per output
    outs: dict[str, OutputFile] = {
        o.name: create_temp(o) for o in config.output.files
    }
    # one batcher per output file (writes to the same file must serialise anyway).
    batchers: dict[str, Batcher] = {
        name: Batcher(output=of) for name, of in outs.items()
    }

    t0 = asyncio.get_event_loop().time()

    async def drain_source(item):  # noqa: ANN001
        async for rule in parser.handle(item):
            for out_item in config.output.files:
                if not _accepts(out_item, rule):
                    continue
                handler = _handler_pkg.get_handler(out_item.type)
                line = handler.format(rule)
                if line is None:
                    continue
                await batchers[out_item.name].add(line)

    # run all sources concurrently
    async with asyncio.TaskGroup() as tg:
        for item in config.input.input:
            tg.create_task(drain_source(item))

    # flush batchers
    for b in batchers.values():
        await b.flush()

    # prepend headers & move into place
    target_dir = Path(config.output.path).expanduser().resolve()
    for out in outs.values():
        final = await finalise(out, target_dir, config.output.file_header)
        logging.info("wrote %s (%d rules)", final, out.count)

    # stats
    if prober:
        logging.info("dns prober stats: %s", prober.stats())
        await prober.close()

    dt_ms = int((asyncio.get_event_loop().time() - t0) * 1000)
    logging.info("all done in %d ms", dt_ms)


def _accepts(out: OutputItem, rule) -> bool:  # noqa: ANN001
    if out.rule and rule.source_name not in out.rule:
        return False
    return not (out.filter and rule.type not in out.filter)


@app.command()
def run(
    config: Annotated[
        Path,
        typer.Option("--config", "-c", help="Path to YAML config."),
    ] = Path("config/application.yaml"),
    log_level: Annotated[
        str,
        typer.Option("--log-level", "-l", help="DEBUG/INFO/WARNING/ERROR"),
    ] = "INFO",
) -> None:
    """Run the full fetch/parse/emit pipeline."""
    _setup_logging(log_level)
    try:
        cfg = AppConfig.from_yaml(config)
    except FileNotFoundError:
        typer.echo(f"config file not found: {config}", err=True)
        raise typer.Exit(code=2) from None
    except Exception as e:  # noqa: BLE001
        typer.echo(f"config error: {e}", err=True)
        raise typer.Exit(code=2) from None

    try:
        asyncio.run(_run(cfg))
    except KeyboardInterrupt:
        typer.echo("interrupted", err=True)
        sys.exit(130)


@app.command()
def validate(
    config: Annotated[Path, typer.Option("--config", "-c")] = Path("config/application.yaml"),
) -> None:
    """Validate the config file and exit."""
    _setup_logging("INFO")
    try:
        cfg = AppConfig.from_yaml(config)
    except Exception as e:  # noqa: BLE001
        typer.echo(f"invalid: {e}", err=True)
        raise typer.Exit(code=1) from None
    typer.echo(
        f"OK — {len(cfg.input.input)} inputs, {len(cfg.output.files)} outputs"
    )


if __name__ == "__main__":
    app()
