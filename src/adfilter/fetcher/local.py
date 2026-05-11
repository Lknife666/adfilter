"""Local filesystem fetcher."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

from ..config import LocalFetcherConfig
from .base import Fetcher


class LocalFetcher(Fetcher):
    def __init__(self, config: LocalFetcherConfig) -> None:
        self._encoding = config.encoding

    async def fetch(self, path: str) -> AsyncIterator[str]:
        full = Path(path).expanduser().resolve()

        # Read in a worker thread to avoid blocking the event loop.
        def _read_lines() -> list[str]:
            with full.open("r", encoding=self._encoding, errors="replace", newline="") as f:
                return [ln.rstrip("\r\n") for ln in f]

        lines = await asyncio.to_thread(_read_lines)
        for line in lines:
            yield line
