"""Fetcher package."""

from .base import Fetcher
from .factory import get_fetcher
from .http import HttpFetcher
from .local import LocalFetcher

__all__ = ["Fetcher", "HttpFetcher", "LocalFetcher", "get_fetcher"]
