"""Fetcher abstract base."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class Fetcher(ABC):
    """Fetches a stream of text lines from some source."""

    @abstractmethod
    def fetch(self, path: str) -> AsyncIterator[str]:
        """Yield each line (without trailing newline)."""
        ...
