"""Logging setup with optional JSON structured output (feature #19)."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime

from rich.logging import RichHandler


class JsonFormatter(logging.Formatter):
    """Render each record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        for k, v in record.__dict__.items():
            if k.startswith("_ctx_"):
                payload[k[5:]] = v
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(level: str, *, json_logs: bool = False) -> None:
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    root.setLevel(level.upper())

    if json_logs:
        handler: logging.Handler = logging.StreamHandler(stream=sys.stderr)
        handler.setFormatter(JsonFormatter())
    else:
        handler = RichHandler(rich_tracebacks=True, markup=True, show_time=True)
        handler.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(handler)
