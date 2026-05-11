"""Pre-compiled regex patterns."""

from __future__ import annotations

import re
from typing import Final

# RFC-1123-ish domain
PATTERN_DOMAIN: Final = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
)

# partial domain segment (used for wildcard detection: e.g. "a.b")
DOMAIN_PART: Final = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.?)+[a-zA-Z0-9-]*$"
)

# IPv4 / IPv6 (loose)
PATTERN_IP: Final = re.compile(
    r"^(?:"
    r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)(?:\.(?:25[0-5]|2[0-4]\d|[01]?\d\d?)){3}"
    r"|"
    r"(?:[0-9a-fA-F:]+)"
    r")$"
)

PATTERN_PATH_ABSOLUTE: Final = re.compile(r"^([a-zA-Z]:[\\/]|/).*")
