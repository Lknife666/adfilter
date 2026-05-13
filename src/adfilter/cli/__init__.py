"""CLI package — all commands registered on a shared Typer app."""

from __future__ import annotations

import typer
from rich.console import Console

app = typer.Typer(
    add_completion=False,
    help="Ad filter rule aggregator & converter — Python edition",
    no_args_is_help=True,
)

console = Console(stderr=True)

# Import command modules to register them on `app`.
from . import convert, diff, info, run, serve, sources  # noqa: E402, F401

__all__ = ["app", "console"]
