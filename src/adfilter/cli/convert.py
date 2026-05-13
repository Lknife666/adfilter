"""convert command — one-shot file-to-file format conversion."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from .. import handler as _handler_pkg
from ..constants import RuleSet
from ..logging_setup import setup_logging
from . import app


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
