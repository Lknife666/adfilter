"""CLI entry point.

Delegates to the cli package which registers all commands on a shared
Typer app instance.
"""

from .cli import app

if __name__ == "__main__":
    app()
