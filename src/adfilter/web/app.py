"""Web application — Dashboard + REST API + file serving.

Lightweight Litestar-based application providing:
- Dashboard: build status, rule statistics, subscription links
- API: /api/v1/* endpoints for programmatic access
- File serving: /rules/* for subscription downloads
- Domain search: check if a domain is in the rule set
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from litestar import Litestar, MediaType, Response, get, post
from litestar.config.cors import CORSConfig
from litestar.response import Template
from litestar.static_files import create_static_files_router
from litestar.template import TemplateConfig
from litestar.contrib.jinja import JinjaTemplateEngine

log = logging.getLogger(__name__)


@dataclass
class AppState:
    """Shared application state."""
    rule_dir: Path = field(default_factory=lambda: Path("rule"))
    config_path: Path = field(default_factory=lambda: Path("config/application.yaml"))
    base_url: str = ""
    _build_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def load_build_report(self) -> dict[str, Any]:
        """Load the latest build report."""
        report_path = self.rule_dir / "build-report.json"
        if not report_path.exists():
            return {"finished_at": None, "sources": [], "outputs": [], "elapsed_ms": 0}
        try:
            return json.loads(report_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"finished_at": None, "sources": [], "outputs": [], "elapsed_ms": 0}

    def get_rule_files(self) -> list[dict[str, Any]]:
        """List available rule files with metadata."""
        files = []
        if not self.rule_dir.exists():
            return files
        for f in sorted(self.rule_dir.iterdir()):
            if f.is_file() and f.name != "build-report.json":
                files.append({
                    "name": f.name,
                    "size": f.stat().st_size,
                    "url": f"{self.base_url}/rules/{f.name}" if self.base_url else f"/rules/{f.name}",
                })
        return files

    def search_domain(self, domain: str) -> list[dict[str, str]]:
        """Search for a domain in rule files. Returns list of {file, line}."""
        results = []
        domain_lower = domain.lower().strip()
        if not domain_lower or not self.rule_dir.exists():
            return results

        # Search in text-based rule files
        for f in self.rule_dir.iterdir():
            if not f.is_file():
                continue
            if f.suffix not in (".txt", ".conf", ".rsc"):
                continue
            try:
                for line in f.read_text(encoding="utf-8").splitlines():
                    if domain_lower in line.lower():
                        results.append({"file": f.name, "line": line.strip()})
                        break  # One match per file is enough
            except OSError:
                continue
        return results


# ─── Global state instance ───────────────────────────────────────────
_state = AppState()


def set_state(state: AppState) -> None:
    global _state
    _state = state


# ─── Dashboard Routes ────────────────────────────────────────────────

@get("/", media_type=MediaType.HTML)
async def dashboard() -> Template:
    """Main dashboard page."""
    report = _state.load_build_report()
    outputs = report.get("outputs", [])
    sources = report.get("sources", [])
    total_rules = sum(o.get("count", 0) for o in outputs)
    files = _state.get_rule_files()

    return Template(
        template_name="dashboard.html",
        context={
            "last_build": report.get("finished_at"),
            "elapsed_ms": report.get("elapsed_ms", 0),
            "total_rules": total_rules,
            "total_files": len(outputs),
            "total_sources": len(sources),
            "outputs": outputs,
            "sources": sources,
            "files": files,
            "base_url": _state.base_url,
        },
    )


@get("/search", media_type=MediaType.HTML)
async def search_page(domain: str = "") -> Template:
    """Domain search page."""
    results = _state.search_domain(domain) if domain else []
    return Template(
        template_name="search.html",
        context={"domain": domain, "results": results, "searched": bool(domain)},
    )


# ─── REST API Routes ─────────────────────────────────────────────────

@get("/api/v1/status")
async def api_status() -> dict[str, Any]:
    """Build status and summary."""
    report = _state.load_build_report()
    outputs = report.get("outputs", [])
    total_rules = sum(o.get("count", 0) for o in outputs)
    return {
        "version": "0.4.0",
        "last_build": report.get("finished_at"),
        "total_rules": total_rules,
        "total_outputs": len(outputs),
        "total_sources": len(report.get("sources", [])),
        "build_duration_ms": report.get("elapsed_ms", 0),
    }


@get("/api/v1/outputs")
async def api_outputs() -> list[dict[str, Any]]:
    """List all output files with metadata."""
    return _state.get_rule_files()


@get("/api/v1/sources")
async def api_sources() -> list[dict[str, Any]]:
    """List rule sources from last build."""
    report = _state.load_build_report()
    return report.get("sources", [])


@get("/api/v1/search")
async def api_search(domain: str = "") -> dict[str, Any]:
    """Search for a domain in rule files."""
    if not domain:
        return {"domain": "", "found": False, "results": []}
    results = _state.search_domain(domain)
    return {"domain": domain, "found": bool(results), "results": results}


@post("/api/v1/build", status_code=202)
async def api_trigger_build() -> dict[str, str]:
    """Trigger a rule rebuild (queued)."""
    # In a real implementation, this would queue a build job
    # For now, return acknowledgment
    return {"status": "queued", "message": "Build has been queued. Check /api/v1/status for progress."}


@get("/api/v1/subscribe/{format_name:str}")
async def api_subscribe(format_name: str) -> dict[str, Any]:
    """Get subscription info for a specific format."""
    files = _state.get_rule_files()
    match = next((f for f in files if format_name in f["name"]), None)
    if not match:
        return Response(content={"error": f"Format '{format_name}' not found"}, status_code=404)
    return {
        "format": format_name,
        "url": match["url"],
        "size_bytes": match["size"],
    }


@get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "timestamp": datetime.now(tz=UTC).isoformat()}


# ─── App Factory ─────────────────────────────────────────────────────

def create_app(
    rule_dir: Path = Path("rule"),
    config_path: Path = Path("config/application.yaml"),
    base_url: str = "",
) -> Litestar:
    """Create the Litestar application."""
    global _state
    _state = AppState(rule_dir=rule_dir, config_path=config_path, base_url=base_url)

    template_dir = Path(__file__).parent / "templates"
    static_dir = Path(__file__).parent / "static"

    route_handlers = [
        dashboard,
        search_page,
        api_status,
        api_outputs,
        api_sources,
        api_search,
        api_trigger_build,
        api_subscribe,
        health_check,
    ]

    # Add static file serving for rule directory
    static_routers = []
    if rule_dir.exists():
        static_routers.append(
            create_static_files_router(path="/rules", directories=[rule_dir])
        )
    if static_dir.exists():
        static_routers.append(
            create_static_files_router(path="/static", directories=[static_dir])
        )

    return Litestar(
        route_handlers=route_handlers + static_routers,
        template_config=TemplateConfig(
            directory=template_dir,
            engine=JinjaTemplateEngine,
        ),
        cors_config=CORSConfig(allow_origins=["*"]),
    )
