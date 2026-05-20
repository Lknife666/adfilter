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
    # #11 — conditional GET
    cache_dir: str | None = None  # None disables on-disk cache
    # #12 — concurrent fetches
    max_concurrency: int = 8
    # v0.2 — error handling / fallback
    on_failure: str = "cache_then_skip"  # fail_fast | cache_then_skip | skip_always
    max_cache_age_hours: int = 72  # stale cache limit


class FetcherConfig(BaseModel):
    local: LocalFetcherConfig = LocalFetcherConfig()
    http: HttpFetcherConfig = HttpFetcherConfig()


# ────────────── optimizer (differentiators #13-#16) ──────────────
class OptimizerConfig(BaseModel):
    enable: bool = False
    # #13
    collapse_subdomains: bool = False
    # #14
    drop_allow_shadowed_deny: bool = False
    # #15 — keep only rules observed in >=N sources (1 disables)
    min_source_votes: int = 1
    # #16
    normalize_idn: bool = True


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
    # #17 — skip the whole run when the input-hash matches last run's
    incremental_build: bool = False
    incremental_cache_file: str = ".adfilter-build.json"
    # #18 — rich progress bar
    progress: bool = False
    # #19 — json-structured logs
    json_logs: bool = False


# ────────────── input ──────────────
class InputItem(BaseModel):
    name: Annotated[str, Field(min_length=1)]
    type: RuleSet = RuleSet.EASYLIST
    path: Annotated[str, Field(min_length=1)]
    group: str = ""  # v0.3: optional group tag for categorized output

    def __hash__(self) -> int:
        return hash(self.path)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, InputItem):
            return False
        return self.path == other.path or self.name == other.name


class AllowlistItem(BaseModel):
    """An allowlist source (local file or HTTP URL)."""

    path: Annotated[str, Field(min_length=1)]


class InputConfig(BaseModel):
    input: set[InputItem] = Field(default_factory=set)
    rule: dict[str, list[InputItem]] = Field(default_factory=dict)
    allowlist: list[AllowlistItem] = Field(default_factory=list)  # v0.3

    @model_validator(mode="after")
    def flatten_rule_groups(self) -> InputConfig:
        # merge "rule: {group: [items]}" into "input", preserving group name
        for group_name, items in self.rule.items():
            for item in items:
                if not item.group:
                    item.group = group_name
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
    groups: list[str] = Field(default_factory=list)  # v0.3: filter by source group

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


# ────────────── notifier (v0.3) ──────────────
class NotifierChannel(BaseModel):
    type: str  # telegram | discord | wecom
    # Telegram
    bot_token: str = ""
    chat_id: str = ""
    # Discord
    webhook_url: str = ""
    # WeCom
    webhook_key: str = ""


class NotifierConfig(BaseModel):
    enable: bool = False
    on_success: bool = True
    on_failure: bool = True
    channels: list[NotifierChannel] = Field(default_factory=list)


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
    optimizer: OptimizerConfig = OptimizerConfig()
    notifier: NotifierConfig = NotifierConfig()  # v0.3

    @field_validator("output", mode="after")
    @classmethod
    def require_outputs(cls, v: OutputConfig) -> OutputConfig:
        if not v.files:
            raise ValueError("output.files must not be empty")
        return v

    @classmethod
    def from_yaml(cls, path: str | Path) -> AppConfig:
        p = Path(path)
        with p.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        # allow nested under "application.config" like the original project
        if "application" in data and "config" in data.get("application", {}):
            data = data["application"]["config"]
        return cls.model_validate(data)


__all__ = [
    "AllowlistItem",
    "AppConfig",
    "DnsProbeConfig",
    "DnsProvider",
    "FetcherConfig",
    "HttpFetcherConfig",
    "InputConfig",
    "InputItem",
    "LocalFetcherConfig",
    "NotifierChannel",
    "NotifierConfig",
    "OptimizerConfig",
    "OutputConfig",
    "OutputItem",
    "ParserConfig",
]
