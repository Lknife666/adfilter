"""Unit tests for logging setup."""

from __future__ import annotations

import json
import logging

import pytest

from adfilter.logging_setup import JsonFormatter, setup_logging


class TestSetupLogging:
    def test_standard_logging(self):
        setup_logging("DEBUG")
        root = logging.getLogger()
        assert root.level == logging.DEBUG
        assert len(root.handlers) == 1

    def test_json_logging(self):
        setup_logging("INFO", json_logs=True)
        root = logging.getLogger()
        assert root.level == logging.INFO
        assert len(root.handlers) == 1
        handler = root.handlers[0]
        assert isinstance(handler.formatter, JsonFormatter)

    def test_level_case_insensitive(self):
        setup_logging("warning")
        root = logging.getLogger()
        assert root.level == logging.WARNING


class TestJsonFormatter:
    def test_format_basic_record(self):
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="hello %s",
            args=("world",),
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert data["msg"] == "hello world"
        assert data["level"] == "INFO"
        assert data["logger"] == "test"
        assert "ts" in data

    def test_format_with_context(self):
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="msg",
            args=(),
            exc_info=None,
        )
        record._ctx_source = "anti-ad"  # type: ignore[attr-defined]
        output = formatter.format(record)
        data = json.loads(output)
        assert data["source"] == "anti-ad"
