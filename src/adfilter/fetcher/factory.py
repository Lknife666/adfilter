"""Fetcher factory."""

from __future__ import annotations

from ..config import FetcherConfig
from ..constants import HandleType
from .base import Fetcher
from .http import HttpFetcher
from .local import LocalFetcher


def get_fetcher(handle_type: HandleType, config: FetcherConfig) -> Fetcher:
    match handle_type:
        case HandleType.LOCAL:
            return LocalFetcher(config.local)
        case HandleType.REMOTE:
            return HttpFetcher(config.http)
        case _:
            raise ValueError(f"unsupported handle type: {handle_type}")


def detect_handle_type(path: str) -> HandleType:
    lower = path.lower()
    if lower.startswith(("http://", "https://")):
        return HandleType.REMOTE
    return HandleType.LOCAL
