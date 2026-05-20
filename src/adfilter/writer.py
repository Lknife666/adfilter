"""Per-file async batched writer with post-run header prepending."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .config import OutputItem
from .constants import Placeholder, RuleSet
from .handler import get_handler

log = logging.getLogger(__name__)


@dataclass(slots=True)
class OutputFile:
    item: OutputItem
    temp_path: Path
    count: int = 0
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def append(self, batch: list[str]) -> None:
        if not batch:
            return
        data = "\n".join(batch) + "\n"
        async with self._lock:
            await asyncio.to_thread(self._write_text, data)
            self.count += len(batch)

    def _write_text(self, data: str) -> None:
        with self.temp_path.open("a", encoding="utf-8", newline="") as f:
            f.write(data)


@dataclass(slots=True)
class Batcher:
    """Groups rules and flushes by size or timeout."""

    output: OutputFile
    max_size: int = 5000
    max_delay_seconds: float = 1.0
    _buf: list[str] = field(default_factory=list)
    _task: asyncio.Task[None] | None = None
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def add(self, line: str) -> None:
        async with self._lock:
            self._buf.append(line)
            if len(self._buf) >= self.max_size:
                pending, self._buf = self._buf, []
                await self.output.append(pending)
                return
            if self._task is None or self._task.done():
                self._task = asyncio.create_task(self._flush_after())

    async def _flush_after(self) -> None:
        try:
            await asyncio.sleep(self.max_delay_seconds)
            async with self._lock:
                if self._buf:
                    pending, self._buf = self._buf, []
                    await self.output.append(pending)
        except asyncio.CancelledError:
            raise

    async def flush(self) -> None:
        async with self._lock:
            if self._task and not self._task.done():
                self._task.cancel()
            if self._buf:
                pending, self._buf = self._buf, []
                await self.output.append(pending)


def build_header(item: OutputItem, parent_header: str, total: int) -> str:
    handler = get_handler(item.type)
    tpl = item.file_header or parent_header
    out_parts: list[str] = []

    if tpl.strip():
        body = (
            tpl.replace(Placeholder.DATE.value, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            .replace(Placeholder.NAME.value, item.name)
            .replace(Placeholder.DESC.value, item.desc)
            .replace(Placeholder.TYPE.value, item.type.value.lower())
            .replace(Placeholder.TOTAL.value, str(total))
        )
        out_parts.append(handler.commented(body))

    head = handler.head_format()
    if head:
        out_parts.append(head)

    return "\n".join(out_parts) + "\n" if out_parts else ""


def create_temp(item: OutputItem) -> OutputFile:
    fd, path = tempfile.mkstemp(prefix=f"{item.name}-", suffix=".tmp")
    os.close(fd)
    return OutputFile(item=item, temp_path=Path(path))


async def finalise(out: OutputFile, target_dir: Path, parent_header: str) -> Path:
    target = target_dir / out.item.name
    header = build_header(out.item, parent_header, out.count)

    def _merge() -> Path:
        target.parent.mkdir(parents=True, exist_ok=True)
        intermediate = target.with_suffix(target.suffix + ".intermediate")

        # #10 — sing-box requires a JSON-wrapped output
        if out.item.type is RuleSet.SINGBOX:
            _write_singbox(intermediate, out.temp_path, header)
        else:
            _write_plain(intermediate, out.temp_path, header)

        intermediate.replace(target)
        out.temp_path.unlink(missing_ok=True)
        # move the sidecar next to the target too
        sidecar = intermediate.with_suffix(intermediate.suffix + ".about.txt")
        if sidecar.exists():
            sidecar.replace(target.with_suffix(target.suffix + ".about.txt"))
        return target

    return await asyncio.to_thread(_merge)


def _write_plain(intermediate: Path, temp: Path, header: str) -> None:
    with (
        intermediate.open("w", encoding="utf-8", newline="") as w,
        temp.open("r", encoding="utf-8", newline="") as r,
    ):
        if header:
            w.write(header)
        while True:
            chunk = r.read(65536)
            if not chunk:
                break
            w.write(chunk)


def _write_singbox(intermediate: Path, temp: Path, header: str) -> None:
    """Wrap a stream of JSON-line rule fragments into one valid sing-box ruleset."""
    domains: list[str] = []
    domain_suffixes: list[str] = []

    with temp.open("r", encoding="utf-8") as r:
        for raw in r:
            line = raw.strip()
            if not line or line.startswith("//") or line.startswith("#"):
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if vs := obj.get("domain_suffix"):
                domain_suffixes.extend(vs)
            if vs := obj.get("domain"):
                domains.extend(vs)

    rules: list[dict[str, list[str]]] = []
    if domain_suffixes:
        rules.append({"domain_suffix": sorted(set(domain_suffixes))})
    if domains:
        rules.append({"domain": sorted(set(domains))})

    ruleset = {"version": 2, "rules": rules}
    payload = json.dumps(ruleset, ensure_ascii=False, indent=2)

    with intermediate.open("w", encoding="utf-8") as w:
        w.write(payload)
        w.write("\n")

    # sidecar so the human-readable header isn't lost
    if header.strip():
        intermediate.with_suffix(intermediate.suffix + ".about.txt").write_text(header, encoding="utf-8")


# ─────────────── #17 incremental-build fingerprint ───────────────
def input_fingerprint(payload: list[tuple[str, str]]) -> str:
    """Stable hash over (source-name, source-path) pairs."""
    h = hashlib.sha256()
    for name, path in sorted(payload):
        h.update(name.encode("utf-8"))
        h.update(b"\x00")
        h.update(path.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def load_build_cache(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_build_cache(path: Path, data: dict) -> None:
    try:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError as e:
        log.warning("could not persist build cache: %s", e)
