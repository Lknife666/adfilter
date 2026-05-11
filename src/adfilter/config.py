"""Configuration models (pydantic)."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .constants import RuleSet
from .model import RuleType


# ────────────── fetcher ──────────────
class LocalFetcherConfig(BaseModel):
    encoding: str = "utf-8"


class HttpFetcherConfig(BaseModel):
    encoding: str = "utf-8"
    timeout_seconds: int = 30
    max_retries: int = 3
    user_agent: str = "adfilter/0.1"
    headers: dict[str, str] = Field(default_factory=dict)


class FetcherConfig(BaseModel):
    local: LocalFetcherConfig = LocalFetcherConfig()
    http: HttpFetcherConfig = HttpFetcherConfig()


# ────────────── parser ──────────────
class DnsProvider(BaseModel):
    host: str
    port: int | None = None


class DnsProbeConfig(BaseModel):
    enable: bool = False
    timeout_seconds: float = 5.0
    cache_ttl_min_seconds: int = 60
    cache_ttl_max_seconds: int = 86400
    cache_negative_ttl_seconds: int = 30
    provider: list[DnsProvider] = Field(default_factory=list)


class ParserConfig(BaseModel):
    min_length: int = 0
    max_length: int = 0
    alert_length: int = 0
    excludes: set[str] = Field(default_factory=set)
    dns_probe: DnsProbeConfig = DnsProbeConfig()


# ────────────── input ──────────────
class InputItem(BaseModel):
    name: Annotated[str, Field(min_length=1)]
    type: RuleSet = RuleSet.EASYLIST
    path: Annotated[str, Field(min_length=1)]

    def __hash__(self) -> int:
        return hash(self.path)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, InputItem):
            return False
        return self.path == other.path or self.name == other.name


class InputConfig(BaseModel):
    input: set[InputItem] = Field(default_factory=set)
    rule: dict[str, list[InputItem]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def flatten_rule_groups(self) -> "InputConfig":
        # merge "rule: {group: [items]}" into "input"
        for items in self.rule.values():
            for item in items:
                self.input.add(item)
        return self


# ────────────── output ──────────────
class OutputItem(BaseModel):
    name: Annotated[str, Field(min_length=1)]
    type: RuleSet
    desc: str = ""
    file_header: str = ""
    # empty = "accept all"
    filter: set[RuleType] = Field(default_factory=set)
    rule: set[str] = Field(default_factory=set)

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, OutputItem):
            return False
        return self.name == other.name


class OutputConfig(BaseModel):
    path: str = "./dist-rules"
    file_header: str = ""
    files: set[OutputItem] = Field(default_factory=set)


# ────────────── root ──────────────
class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ADFILTER_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    input: InputConfig = InputConfig()
    output: OutputConfig = OutputConfig()
    fetcher: FetcherConfig = FetcherConfig()
    parser: ParserConfig = ParserConfig()

    @field_validator("output", mode="after")
    @classmethod
    def require_outputs(cls, v: OutputConfig) -> OutputConfig:
        if not v.files:
            raise ValueError("output.files must not be empty")
        return v

    @classmethod
    def from_yaml(cls, path: str | Path) -> "AppConfig":
        p = Path(path)
        with p.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        # allow nested under "application.config" like the original project
        if "application" in data and "config" in data.get("application", {}):
            data = data["application"]["config"]
        return cls.model_validate(data)


__all__ = [
    "AppConfig",
    "DnsProbeConfig",
    "DnsProvider",
    "FetcherConfig",
    "HttpFetcherConfig",
    "InputConfig",
    "InputItem",
    "LocalFetcherConfig",
    "OutputConfig",
    "OutputItem",
    "ParserConfig",
]
