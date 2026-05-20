"""Unit tests for config module."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from adfilter.config import (
    AppConfig,
    FetcherConfig,
    HttpFetcherConfig,
    InputConfig,
    InputItem,
    OptimizerConfig,
    OutputConfig,
    OutputItem,
    ParserConfig,
)
from adfilter.constants import RuleSet
from adfilter.model import RuleType


class TestAppConfigFromYaml:
    def test_load_valid_config(self, tmp_path):
        config_data = {
            "application": {
                "config": {
                    "input": {
                        "rule": {
                            "default": [
                                {"name": "test", "type": "easylist", "path": "https://example.com/list.txt"}
                            ]
                        }
                    },
                    "output": {
                        "path": "./out",
                        "files": [{"name": "dns.txt", "type": "dns", "desc": "test"}],
                    },
                }
            }
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config_data), encoding="utf-8")
        cfg = AppConfig.from_yaml(config_file)
        assert len(cfg.input.input) == 1
        assert len(cfg.output.files) == 1

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            AppConfig.from_yaml("/nonexistent/config.yaml")

    def test_empty_outputs_raises(self, tmp_path):
        config_data = {"application": {"config": {"output": {"path": "./out", "files": []}}}}
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config_data), encoding="utf-8")
        with pytest.raises(Exception):
            AppConfig.from_yaml(config_file)


class TestInputConfig:
    def test_flatten_rule_groups(self):
        items = [InputItem(name="a", type=RuleSet.EASYLIST, path="http://a.com/list.txt")]
        cfg = InputConfig(rule={"default": items})
        assert len(cfg.input) == 1

    def test_dedupe_by_path(self):
        item1 = InputItem(name="a", type=RuleSet.EASYLIST, path="http://same.com")
        item2 = InputItem(name="b", type=RuleSet.EASYLIST, path="http://same.com")
        cfg = InputConfig(rule={"default": [item1, item2]})
        assert len(cfg.input) == 1


class TestOptimizerConfig:
    def test_defaults(self):
        cfg = OptimizerConfig()
        assert cfg.enable is False
        assert cfg.collapse_subdomains is False
        assert cfg.min_source_votes == 1
        assert cfg.normalize_idn is True


class TestHttpFetcherConfig:
    def test_defaults(self):
        cfg = HttpFetcherConfig()
        assert cfg.timeout_seconds == 30
        assert cfg.max_retries == 3
        assert cfg.max_concurrency == 8
        assert cfg.cache_dir is None


class TestOutputItem:
    def test_hash_by_name(self):
        o1 = OutputItem(name="dns.txt", type=RuleSet.DNS)
        o2 = OutputItem(name="dns.txt", type=RuleSet.HOSTS)
        assert hash(o1) == hash(o2)

    def test_filter_empty_accepts_all(self):
        o = OutputItem(name="test.txt", type=RuleSet.DNS)
        assert o.filter == set()
