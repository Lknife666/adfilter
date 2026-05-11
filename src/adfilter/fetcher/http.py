"""HTTP fetcher — streaming, line-buffered, with conditional-GET cache."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from collections.abc import AsyncIterator
from pathlib import Path

import aiohttp

from ..config import HttpFetcherConfig
from .base import Fetcher

log = logging.getLogger(__name__)

_CHUNK = 16 * 1024


def _cache_key(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


class HttpFetcher(Fetcher):
    """Async HTTP fetcher.

    Feature #11 — optional on-disk cache with conditional GET:
    if the server replies 304 Not Modified, we re-read the cached body
    without decoding the (absent) response payload.
    """

    def __init__(self, config: HttpFetcherConfig) -> None:
        self._config = config
        self._cache_dir: Path | None = None
        if config.cache_dir:
            self._cache_dir = Path(config.cache_dir).expanduser()
            self._cache_dir.mkdir(parents=True, exist_ok=True)

    # ── public ──────────────────────────────────────────────────────
    async def fetch(self, path: str) -> AsyncIterator[str]:
        timeout = aiohttp.ClientTimeout(total=self._config.timeout_seconds)
        base_headers = {"User-Agent": self._config.user_agent, **self._config.headers}

        cached_body: str | None = None
        conditional_headers: dict[str, str] = {}
        meta_path, body_path = self._cache_paths(path)
        if meta_path and body_path and meta_path.exists() and body_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                if etag := meta.get("etag"):
                    conditional_headers["If-None-Match"] = etag
                if last_modified := meta.get("last_modified"):
                    conditional_headers["If-Modified-Since"] = last_modified
                cached_body = body_path.read_text(encoding=self._config.encoding, errors="replace")
            except (OSError, json.JSONDecodeError) as e:
                log.debug("cache read failed for %s: %s", path, e)

        attempt = 0
        while True:
            try:
                headers = {**base_headers, **conditional_headers}
                async for line in self._stream(path, timeout, headers, cached_body):
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

    # ── internals ───────────────────────────────────────────────────
    def _cache_paths(self, url: str) -> tuple[Path | None, Path | None]:
        if self._cache_dir is None:
            return None, None
        key = _cache_key(url)
        return (self._cache_dir / f"{key}.meta.json",
                self._cache_dir / f"{key}.body")

    async def _stream(
        self,
        url: str,
        timeout: aiohttp.ClientTimeout,
        headers: dict[str, str],
        cached_body: str | None,
    ) -> AsyncIterator[str]:
        enc = self._config.encoding
        async with (
            aiohttp.ClientSession(timeout=timeout, headers=headers) as session,
            session.get(url) as resp,
        ):
            if resp.status == 304 and cached_body is not None:
                log.info("fetch %s => 304 Not Modified (using cache)", url)
                for ln in cached_body.splitlines():
                    yield ln
                return

            resp.raise_for_status()

            # capture to disk as we stream, so we can cache on success
            body_path = None
            meta_path, body_path = self._cache_paths(url)
            writer = None
            if body_path is not None:
                tmp = body_path.with_suffix(".tmp")
                writer = tmp.open("w", encoding=enc)

            try:
                buf = ""
                async for chunk in resp.content.iter_chunked(_CHUNK):
                    text = chunk.decode(enc, errors="replace")
                    if writer is not None:
                        writer.write(text)
                    buf += text
                    parts = buf.splitlines(keepends=True)
                    buf = parts.pop() if parts and not parts[-1].endswith(("\n", "\r")) else ""
                    for p in parts:
                        yield p.rstrip("\r\n")
                if buf:
                    yield buf
            finally:
                if writer is not None:
                    writer.close()

            # success → commit to cache
            if body_path is not None and meta_path is not None and writer is not None:
                tmp = body_path.with_suffix(".tmp")
                tmp.replace(body_path)
                meta: dict[str, str] = {}
                if etag := resp.headers.get("ETag"):
                    meta["etag"] = etag
                if lm := resp.headers.get("Last-Modified"):
                    meta["last_modified"] = lm
                meta_path.write_text(json.dumps(meta), encoding="utf-8")
