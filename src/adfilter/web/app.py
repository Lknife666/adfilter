"""Web application — lightweight dashboard for adfilter.

Provides:
- Rule search and browse interface
- Build status dashboard
- Custom subscription builder
- API endpoints for integration
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

try:
    from aiohttp import web
except ImportError:
    web = None  # type: ignore[assignment]


def create_app(
    *,
    rule_dir: str | Path = "./rule",
    template_dir: str | Path | None = None,
) -> web.Application:
    """Create the aiohttp web application.

    Args:
        rule_dir: directory containing generated rule files
        template_dir: directory containing HTML templates
    """
    if web is None:
        raise ImportError(
            "aiohttp is required for the web dashboard. Install with: pip install adfilter[web]"
        )

    app = web.Application()
    app["rule_dir"] = Path(rule_dir)
    app["template_dir"] = Path(template_dir) if template_dir else _default_template_dir()

    app.router.add_get("/", handle_dashboard)
    app.router.add_get("/api/status", handle_api_status)
    app.router.add_get("/api/search", handle_api_search)
    app.router.add_get("/search", handle_search)

    return app


def _default_template_dir() -> Path:
    return Path(__file__).parent / "templates"


async def handle_dashboard(request: web.Request) -> web.Response:
    """Serve the dashboard page."""
    template_dir = request.app["template_dir"]
    rule_dir = request.app["rule_dir"]

    # Gather stats
    stats = _gather_stats(rule_dir)

    template_path = template_dir / "dashboard.html"
    if template_path.exists():
        html = template_path.read_text(encoding="utf-8")
        # Simple template variable replacement
        html = html.replace("{{ total_rules }}", str(stats.get("total_rules", 0)))
        html = html.replace("{{ file_count }}", str(stats.get("file_count", 0)))
        html = html.replace("{{ last_updated }}", stats.get("last_updated", "unknown"))
        return web.Response(text=html, content_type="text/html")

    return web.Response(
        text=f"<h1>adfilter Dashboard</h1><p>Files: {stats.get('file_count', 0)}</p>",
        content_type="text/html",
    )


async def handle_api_status(request: web.Request) -> web.Response:
    """Return build status as JSON."""
    rule_dir = request.app["rule_dir"]
    stats = _gather_stats(rule_dir)
    return web.json_response(stats)


async def handle_api_search(request: web.Request) -> web.Response:
    """Search rules for a given domain query."""
    query = request.query.get("q", "").strip().lower()
    if not query:
        return web.json_response({"error": "missing query parameter 'q'"}, status=400)

    rule_dir = request.app["rule_dir"]
    results = _search_rules(rule_dir, query)
    return web.json_response({"query": query, "results": results})


async def handle_search(request: web.Request) -> web.Response:
    """Serve the search page."""
    template_dir = request.app["template_dir"]
    template_path = template_dir / "search.html"
    if template_path.exists():
        html = template_path.read_text(encoding="utf-8")
        return web.Response(text=html, content_type="text/html")
    return web.Response(text="<h1>Search</h1>", content_type="text/html")


def _gather_stats(rule_dir: Path) -> dict:
    """Gather statistics from the rule directory."""
    stats: dict = {"total_rules": 0, "file_count": 0, "last_updated": "unknown", "files": []}

    if not rule_dir.exists():
        return stats

    report_path = rule_dir / "build-report.json"
    if report_path.exists():
        try:
            data = json.loads(report_path.read_text(encoding="utf-8"))
            stats["last_updated"] = data.get("timestamp", "unknown")
            stats["total_rules"] = data.get("total_rules", 0)
        except (json.JSONDecodeError, OSError):
            pass

    for f in rule_dir.iterdir():
        if f.is_file() and f.name != "build-report.json":
            stats["file_count"] += 1
            stats["files"].append({"name": f.name, "size": f.stat().st_size})

    return stats


def _search_rules(rule_dir: Path, query: str, max_results: int = 50) -> list[dict]:
    """Search through DNS rule file for matching domains."""
    results: list[dict] = []
    dns_file = rule_dir / "dns.txt"

    if not dns_file.exists():
        return results

    try:
        with dns_file.open("r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith(("!", "#")):
                    continue
                if query in line.lower():
                    results.append({"rule": line, "file": "dns.txt"})
                    if len(results) >= max_results:
                        break
    except OSError:
        pass

    return results
