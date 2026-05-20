"""diff command — compare two rule files by rule identity."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from .. import handler as _handler_pkg
from ..constants import RuleSet
from ..logging_setup import setup_logging
from . import app


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
    fmt: Annotated[RuleSet, typer.Option("--format", "-f", help="Format of both files")] = RuleSet.EASYLIST,
) -> None:
    """Compare two rule files by rule identity (not by byte-level text)."""
    setup_logging("WARNING")
    old_h = _collect_hashes(old, fmt)
    new_h = _collect_hashes(new, fmt)
    added = len(new_h - old_h)
    removed = len(old_h - new_h)
    unchanged = len(old_h & new_h)
    table = Table(title="rule diff", show_header=True)
    table.add_column("metric")
    table.add_column("count", justify="right")
    table.add_row("unchanged", str(unchanged))
    table.add_row("[green]added[/]", str(added))
    table.add_row("[red]removed[/]", str(removed))
    Console().print(table)
