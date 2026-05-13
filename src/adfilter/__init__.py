"""adfilter - aggregate & convert ad-filter rules across formats."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("adfilter")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"
