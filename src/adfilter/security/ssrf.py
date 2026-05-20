"""Security utilities for adfilter.

Provides SSRF protection, input validation, and safe URL handling
to prevent security issues in the fetcher pipeline.
"""

from __future__ import annotations

import ipaddress
import logging
import re
from urllib.parse import urlparse

log = logging.getLogger(__name__)

# Private/reserved IP ranges (RFC 1918, RFC 6890, etc.)
_PRIVATE_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),  # CGNAT
    ipaddress.ip_network("198.18.0.0/15"),  # benchmark
    ipaddress.ip_network("::1/128"),  # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),  # IPv6 ULA
    ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
]

# Dangerous URL schemes
_BLOCKED_SCHEMES = frozenset({"file", "ftp", "gopher", "data", "javascript"})

# Domain validation pattern
_DOMAIN_PATTERN = re.compile(
    r"^[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)*$"
)

# Maximum URL length to prevent abuse
MAX_URL_LENGTH = 4096


class SSRFError(Exception):
    """Raised when a URL is suspected of SSRF."""


class ValidationError(Exception):
    """Raised when input validation fails."""


def is_private_ip(ip_str: str) -> bool:
    """Check if an IP address belongs to a private/reserved range."""
    try:
        addr = ipaddress.ip_address(ip_str)
        return any(addr in network for network in _PRIVATE_RANGES)
    except ValueError:
        return False


def validate_url(url: str) -> str:
    """Validate a URL for safe fetching.

    Checks:
    - Length limits
    - Allowed schemes (http/https only)
    - No private/reserved IP targets
    - No suspicious hostnames

    Returns the validated URL.
    Raises SSRFError if the URL is unsafe.
    """
    if not url or not url.strip():
        raise ValidationError("Empty URL")

    if len(url) > MAX_URL_LENGTH:
        raise ValidationError(f"URL exceeds maximum length ({MAX_URL_LENGTH})")

    parsed = urlparse(url)

    # Check scheme
    scheme = parsed.scheme.lower()
    if scheme in _BLOCKED_SCHEMES:
        raise SSRFError(f"Blocked URL scheme: {scheme}")
    if scheme not in ("http", "https"):
        raise SSRFError(f"Only http/https schemes allowed, got: {scheme}")

    # Check hostname
    hostname = parsed.hostname
    if not hostname:
        raise SSRFError("URL has no hostname")

    # Check for IP-based URLs
    try:
        ip = ipaddress.ip_address(hostname)
        if any(ip in network for network in _PRIVATE_RANGES):
            raise SSRFError(f"URL targets private/reserved IP: {hostname}")
    except ValueError:
        # Not an IP address — it's a domain name, which is fine
        pass

    # Block localhost variations
    if hostname.lower() in ("localhost", "localhost.localdomain"):
        raise SSRFError("URL targets localhost")

    return url


def validate_domain(domain: str) -> bool:
    """Check if a domain string is syntactically valid.

    Does NOT check existence, only format.
    """
    if not domain or len(domain) > 253:
        return False
    # Remove trailing dot
    domain = domain.rstrip(".")
    if not domain:
        return False
    # Check each label
    labels = domain.split(".")
    if len(labels) < 2:
        return False
    for label in labels:
        if not label or len(label) > 63:
            return False
        if label.startswith("-") or label.endswith("-"):
            return False
    return bool(_DOMAIN_PATTERN.match(domain))


def sanitize_path(path: str) -> str:
    """Sanitize a file path to prevent directory traversal.

    Removes ../ sequences and ensures the path stays within bounds.
    """
    # Remove null bytes
    path = path.replace("\x00", "")
    # Normalize separators
    path = path.replace("\\", "/")
    # Remove path traversal attempts
    parts = []
    for part in path.split("/"):
        if part in ("..", ""):
            continue
        if part == ".":
            continue
        parts.append(part)
    return "/".join(parts)


def mask_secret(value: str, *, visible_chars: int = 4) -> str:
    """Mask a secret value for safe logging.

    Shows only the first N characters, replaces the rest with asterisks.
    """
    if not value:
        return "***"
    if len(value) <= visible_chars:
        return "*" * len(value)
    return value[:visible_chars] + "*" * (len(value) - visible_chars)
