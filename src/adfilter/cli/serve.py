"""serve command — local HTTP server with optional auto-refresh."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Annotated

import typer

from ..config import AppConfig
from ..logging_setup import setup_logging
from . import app


@app.command(name="serve")
def cmd_serve(
    directory: Annotated[Path, typer.Option("--dir", "-d", help="Directory to serve")] = Path("rule"),
    host: Annotated[str, typer.Option("--host")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", "-p")] = 8787,
    auto_refresh: Annotated[
        bool, typer.Option("--auto-refresh/--no-auto-refresh", help="Periodically rebuild rules")
    ] = False,
    refresh_interval: Annotated[
        int, typer.Option("--refresh-interval", help="Minutes between rebuilds")
    ] = 480,
    config: Annotated[Path, typer.Option("--config", "-c")] = Path("config/application.yaml"),
) -> None:
    """Serve the generated rule directory over HTTP (handy for LAN subscribe URLs).

    With --auto-refresh, periodically re-runs the pipeline and atomically
    swaps the output directory so downloads are never interrupted.
    """
    import http.server
    import shutil
    import socketserver
    import threading

    directory = directory.expanduser().resolve()
    if not directory.is_dir():
        typer.echo(f"not a directory: {directory}", err=True)
        raise typer.Exit(code=2)

    def _rebuild() -> None:
        """Run a rebuild and atomically swap the output."""
        try:
            from .run import _run

            cfg = AppConfig.from_yaml(config)
            # Write to a temp dir, then swap
            import tempfile

            tmp_dir = Path(tempfile.mkdtemp(prefix="adfilter-serve-"))
            cfg.output.path = str(tmp_dir)
            asyncio.run(_run(cfg, report_path=None))
            # Atomic swap: rename temp to target
            backup = directory.with_suffix(".old")
            if backup.exists():
                shutil.rmtree(backup)
            directory.rename(backup)
            tmp_dir.rename(directory)
            shutil.rmtree(backup, ignore_errors=True)
            logging.info("auto-refresh: rebuild complete, directory swapped")
        except Exception as e:  # noqa: BLE001
            logging.error("auto-refresh rebuild failed: %s", e)

    if auto_refresh:
        setup_logging("INFO")

        def _scheduler() -> None:
            import time as _time

            while True:
                _time.sleep(refresh_interval * 60)
                _rebuild()

        t = threading.Thread(target=_scheduler, daemon=True)
        t.start()
        typer.echo(f"auto-refresh enabled: every {refresh_interval} min")

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(directory), **kw)

    with socketserver.ThreadingTCPServer((host, port), Handler) as httpd:
        typer.echo(f"serving {directory} on http://{host}:{port}  (Ctrl-C to stop)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            typer.echo("\nstopped")
