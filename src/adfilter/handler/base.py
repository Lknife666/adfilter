"""Abstract rule handler + central registry."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from importlib.metadata import entry_points

from ..constants import RuleSet
from ..model import Rule

log = logging.getLogger(__name__)

_REGISTRY: dict[RuleSet, Handler] = {}


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


def discover_plugins() -> None:
    """Load third-party handlers registered via entry_points (v0.4 plugin system).

    Third-party packages declare entry points under the group ``adfilter.handlers``::

        [project.entry-points."adfilter.handlers"]
        my_format = "my_package.handler:MyHandler"

    Each entry point must resolve to a Handler subclass. On load, the class
    is instantiated (which triggers self-registration via register_handler).
    """
    try:
        eps = entry_points(group="adfilter.handlers")
    except TypeError:
        # Python < 3.12 compatibility
        eps = entry_points().get("adfilter.handlers", [])

    for ep in eps:
        try:
            handler_cls = ep.load()
            if not isinstance(handler_cls, type) or not issubclass(handler_cls, Handler):
                # Maybe it's already an instance
                if isinstance(handler_cls, Handler):
                    log.info("loaded plugin handler: %s (%s)", ep.name, handler_cls.rule_set)
                else:
                    log.warning("plugin %s is not a Handler subclass, skipping", ep.name)
                continue
            # Instantiate to trigger registration
            handler_cls()
            log.info("loaded plugin handler: %s", ep.name)
        except Exception as e:  # noqa: BLE001
            log.warning("failed to load plugin %s: %s", ep.name, e)
