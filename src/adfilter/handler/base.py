"""Abstract rule handler + central registry."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..constants import RuleSet
from ..model import Rule

_REGISTRY: dict[RuleSet, "Handler"] = {}


class Handler(ABC):
    """Parses/formats rules for a specific rule-set format."""

    rule_set: RuleSet  # must be set by subclasses

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)

    @abstractmethod
    def parse(self, line: str) -> Rule:
        """Parse a line into a Rule (or Rule.empty() for unparseable)."""

    @abstractmethod
    def format(self, rule: Rule) -> str | None:
        """Render a rule back to its on-disk representation. None to skip."""

    def head_format(self) -> str | None:
        """Optional format-specific prelude (e.g. clash's ``payload:``)."""
        return None

    def is_comment(self, line: str) -> bool:
        return line.startswith("#")

    @abstractmethod
    def commented(self, value: str) -> str:
        """Turn an arbitrary text block into a comment block."""


def register_handler(rs: RuleSet, h: Handler) -> None:
    _REGISTRY[rs] = h


def get_handler(rs: RuleSet) -> Handler:
    try:
        return _REGISTRY[rs]
    except KeyError as e:
        raise ValueError(f"no handler registered for {rs}") from e
