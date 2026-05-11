"""HTTP fetcher (streaming, line-buffered)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator

import aiohttp

from ..config import HttpFetcherConfig
from .base import Fetcher

log = logging.getLogger(__name__)

_CHUNK = 16 * 1024


class HttpFetcher(Fetcher):
    def __init__(self, config: HttpFetcherConfig) -> None:
        self._config = config

    async def fetch(self, path: str) -> AsyncIterator[str]:
        timeout = aiohttp.ClientTimeout(total=self._config.timeout_seconds)
        headers = {"User-Agent": self._config.user_agent, **self._config.headers}

        attempt = 0
        while True:
            try:
                async for line in self._stream(path, timeout, headers):
                    yield line
                return
            except (TimeoutError, aiohttp.ClientError) as e:
                attempt += 1
                if attempt > self._config.max_retries:
                    log.error("fetch %s failed after %d retries: %s", path, attempt - 1, e)
                    raise
                backoff = min(2**attempt, 30)
                log.warning("fetch %s failed (attempt %d): %s, retrying in %ds",
                            path, attempt, e, backoff)
                await asyncio.sleep(backoff)

    async def _stream(
        self,
        url: str,
        timeout: aiohttp.ClientTimeout,
        headers: dict[str, str],
    ) -> AsyncIterator[str]:
        enc = self._config.encoding
        async with (
            aiohttp.ClientSession(timeout=timeout, headers=headers) as session,
            session.get(url) as resp,
        ):
            resp.raise_for_status()
            buf = ""
            async for chunk in resp.content.iter_chunked(_CHUNK):
                buf += chunk.decode(enc, errors="replace")
                # splitlines(keepends=True) makes it easy to detect incomplete tails
                parts = buf.splitlines(keepends=True)
                buf = parts.pop() if parts and not parts[-1].endswith(("\n", "\r")) else ""
                for p in parts:
                    yield p.rstrip("\r\n")
            if buf:
                yield buf
