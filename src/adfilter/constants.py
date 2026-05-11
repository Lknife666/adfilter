"""Constants, enums and symbol tables."""

from __future__ import annotations

from enum import StrEnum, auto
from typing import Final

# ──────────────────────────── symbols ────────────────────────────
EMPTY: Final = ""
DOT: Final = "."
EXCLAMATION: Final = "!"
HASH: Final = "#"
AT: Final = "@"
DASH: Final = "-"
COMMA: Final = ","
SLASH: Final = "/"
LBRACKET: Final = "["
RBRACKET: Final = "]"
PIPE: Final = "|"
ASTERISK: Final = "*"
CARET: Final = "^"
WHITESPACE: Final = " "
CR: Final = "\r"
LF: Final = "\n"
TAB: Final = "\t"
CRLF: Final = "\r\n"
QUOTE: Final = '"'
SINGLE_QUOTE: Final = "'"
PLUS: Final = "+"
COLON: Final = ":"
DOLLAR: Final = "$"

DOUBLE_AT: Final = "@@"
DOUBLE_PIPE: Final = "||"

# ──────────────────────────── domains ────────────────────────────
LOCAL_IPS: Final = frozenset({"0.0.0.0", "127.0.0.1", "::1"})
LOCAL_DOMAINS: Final = frozenset({
    "localhost", "localhost.localdomain", "local",
    "ip6-localhost", "ip6-loopback",
})
UNKNOWN_IP: Final = "0.0.0.0"
LOCALHOST: Final = "localhost"

# ──────────────────────────── headers ────────────────────────────
PAYLOAD: Final = "payload"
DNSMASQ_HEADER: Final = "address=/"
SMARTDNS_HEADER: Final = "address /"
IMPORTANT: Final = "important"
ALL: Final = "all"


# ──────────────────────────── placeholders ────────────────────────────
class Placeholder(StrEnum):
    DATE = "${date}"
    NAME = "${name}"
    TOTAL = "${total}"
    TYPE = "${type}"
    DESC = "${desc}"


# ──────────────────────────── enums ────────────────────────────
class RuleSet(StrEnum):
    EASYLIST = auto()
    DNS = auto()          # AdGuard Home
    DNSMASQ = auto()
    SMARTDNS = auto()
    CLASH = auto()
    HOSTS = auto()
    # ── differentiators: formats the Java project does not emit ──
    SURGE = auto()        # Surge domain-set
    SINGBOX = auto()      # sing-box JSON ruleset
    MIKROTIK = auto()     # MikroTik RouterOS /ip dns static script
    UNBOUND = auto()      # Unbound local-zone


class HandleType(StrEnum):
    LOCAL = auto()
    REMOTE = auto()
