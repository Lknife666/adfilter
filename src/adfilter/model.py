"""Rule data model."""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from enum import StrEnum, auto

import mmh3

from .constants import RuleSet


class Mode(StrEnum):
    DENY = auto()
    ALLOW = auto()
    REWRITE = auto()


class Scope(StrEnum):
    DOMAIN = auto()
    IP = auto()
    URL = auto()


class RuleType(StrEnum):
    BASIC = auto()
    WILDCARD = auto()
    REGEX = auto()
    UNKNOWN = auto()


class Control(StrEnum):
    OVERLAY = auto()  # ||  (match subdomains)
    QUALIFIER = auto()  # ^
    IMPORTANT = auto()  # $important
    ALL = auto()  # $all


@dataclass(slots=True)
class Rule:
    origin: str = ""
    target: str = ""
    dest: str | None = None
    source_type: RuleSet | None = None
    source_name: str = ""
    source_group: str = ""
    mode: Mode | None = None
    scope: Scope | None = None
    type: RuleType | None = None
    controls: set[Control] = field(default_factory=set)

    # sentinel for "could not parse at all"
    @classmethod
    def empty(cls) -> Rule:
        return _EMPTY

    def is_empty(self) -> bool:
        return self is _EMPTY or (not self.origin and not self.target and self.type is None)

    def murmur3_hash(self) -> int:
        """Stable 128-bit hash used for dedupe (returns the low 64 bits)."""
        if self.type is RuleType.UNKNOWN:
            payload = self.origin.encode("utf-8") + struct.pack(">I", len(self.origin))
        else:
            mode_ord = _ordinal(Mode, self.mode)
            scope_ord = _ordinal(Scope, self.scope)
            type_ord = _ordinal(RuleType, self.type)
            payload = self.target.encode("utf-8") + struct.pack(">iii", mode_ord, scope_ord, type_ord)
        low, _high = mmh3.hash64(payload, signed=True)
        return low


def _ordinal(cls: type[StrEnum], value: StrEnum | None) -> int:
    if value is None:
        return -1
    return list(cls).index(value)


_EMPTY = Rule()
