"""Per-source / per-output build statistics (feature #20)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path


@dataclass(slots=True)
class SourceReport:
    name: str
    total: int = 0
    effective: int = 0
    invalid: int = 0
    repeat: int = 0
    dead: int = 0
    elapsed_ms: int = 0


@dataclass(slots=True)
class OutputReport:
    name: str
    type: str
    count: int
    bytes: int
    path: str


@dataclass(slots=True)
class BuildReport:
    started_at: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())
    finished_at: str | None = None
    elapsed_ms: int = 0
    fingerprint: str = ""
    incremental_skip: bool = False
    sources: list[SourceReport] = field(default_factory=list)
    outputs: list[OutputReport] = field(default_factory=list)

    def write(self, path: Path) -> None:
        from dataclasses import asdict

        path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, object] = {
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "elapsed_ms": self.elapsed_ms,
            "fingerprint": self.fingerprint,
            "incremental_skip": self.incremental_skip,
            "sources": [asdict(s) for s in self.sources],
            "outputs": [asdict(o) for o in self.outputs],
        }
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
