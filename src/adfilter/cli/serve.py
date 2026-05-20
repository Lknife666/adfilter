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
        """Run a rebuild and atomically swap the output.

        Uses a temp directory on the same filesystem as the target to
        ensure os.rename() works (avoids EXDEV on cross-device rename).
        The swap order is: tmp→target_new, target→backup, target_new→target
        so that if any step fails the original directory remains intact.
        """
        try:
            from .run import _run

            cfg = AppConfig.from_yaml(config)
            # Create temp dir on SAME filesystem as directory (avoids EXDEV)
            import tempfile

            tmp_dir = Path(
                tempfile.mkdtemp(prefix="adfilter-serve-", dir=str(directory.parent))
            )
            cfg.output.path = str(tmp_dir)
            asyncio.run(_run(cfg, report_path=None))

            # Safe atomic swap — never leave directory in a broken state
            # Step 1: rename tmp to a staging name next to target
            staging = directory.with_suffix(".new")
            if staging.exists():
                shutil.rmtree(staging)
            tmp_dir.rename(staging)

            # Step 2: move current directory to backup
            backup = directory.with_suffix(".old")
            if backup.exists():
                shutil.rmtree(backup)
            directory.rename(backup)

            # Step 3: promote staging to the real directory
            try:
                staging.rename(directory)
            except OSError:
                # Rollback: restore backup if promotion fails
                backup.rename(directory)
                raise

            # Cleanup
            shutil.rmtree(backup, ignore_errors=True)
            logging.info("auto-refresh: rebuild complete, directory swapped")
        except Exception as e:  # noqa: BLE001
            logging.error("auto-refresh rebuild failed: %s", e)
            # Clean up any leftover temp/staging dirs
            for leftover in (tmp_dir, staging):
                try:
                    if leftover.exists():
                        shutil.rmtree(leftover)
                except Exception:  # noqa: BLE001
                    pass

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
