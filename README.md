<p align="center">
  <h1 align="center">adfilter</h1>
  <p align="center">
    <strong>Ad-filter rule aggregator & multi-format converter</strong><br>
    Fetch, parse, deduplicate, optimize, and emit ad-blocking rules across 12 output formats.
  </p>
  <p align="center">
    <a href="https://github.com/Lknife666/adfilter/actions/workflows/ci.yml"><img src="https://github.com/Lknife666/adfilter/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
    <a href="https://github.com/Lknife666/adfilter/actions/workflows/auto-update.yml"><img src="https://github.com/Lknife666/adfilter/actions/workflows/auto-update.yml/badge.svg" alt="Auto Update"></a>
    <a href="https://github.com/Lknife666/adfilter/pkgs/container/adfilter"><img src="https://img.shields.io/badge/ghcr.io-adfilter-blue" alt="Docker"></a>
    <a href="https://github.com/Lknife666/adfilter/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="License"></a>
    <img src="https://img.shields.io/badge/python-3.14%2B-blue" alt="Python">
  </p>
</p>

---

## Rule Subscription

> Rules are auto-generated every **8 hours** via GitHub Actions and published to the [`release`](https://github.com/Lknife666/adfilter/tree/release) branch.
>
> Last updated: ![Auto Update](https://github.com/Lknife666/adfilter/actions/workflows/auto-update.yml/badge.svg)

| Format | Application | Subscribe URL |
|--------|-------------|---------------|
| AdGuard Home DNS | AdGuard Home, AdGuard DNS | [`dns.txt`](https://raw.githubusercontent.com/Lknife666/adfilter/release/dns.txt) |
| EasyList / ABP | Adblock Plus, uBlock Origin, AdGuard Extension | [`easylist.txt`](https://raw.githubusercontent.com/Lknife666/adfilter/release/easylist.txt) |
| Clash | Clash, Clash Meta, Stash | [`clash.yaml`](https://raw.githubusercontent.com/Lknife666/adfilter/release/clash.yaml) |
| sing-box | sing-box rule-set (v2) | [`singbox.json`](https://raw.githubusercontent.com/Lknife666/adfilter/release/singbox.json) |
| Surge | Surge, Shadowrocket, Stash | [`surge.conf`](https://raw.githubusercontent.com/Lknife666/adfilter/release/surge.conf) |
| Quantumult X | Quantumult X | [`quantumult.conf`](https://raw.githubusercontent.com/Lknife666/adfilter/release/quantumult.conf) |
| Loon | Loon | [`loon.conf`](https://raw.githubusercontent.com/Lknife666/adfilter/release/loon.conf) |
| dnsmasq | dnsmasq, OpenWrt | [`dnsmasq.conf`](https://raw.githubusercontent.com/Lknife666/adfilter/release/dnsmasq.conf) |
| smartdns | SmartDNS | [`smartdns.conf`](https://raw.githubusercontent.com/Lknife666/adfilter/release/smartdns.conf) |
| hosts | All OS, Pi-hole | [`hosts.txt`](https://raw.githubusercontent.com/Lknife666/adfilter/release/hosts.txt) |
| MikroTik | MikroTik RouterOS v6/v7 | [`mikrotik.rsc`](https://raw.githubusercontent.com/Lknife666/adfilter/release/mikrotik.rsc) |
| Unbound | Unbound DNS resolver | [`unbound.conf`](https://raw.githubusercontent.com/Lknife666/adfilter/release/unbound.conf) |

> **Usage**: Copy the subscribe URL and paste it into your ad-blocking tool's subscription settings.  
> See [`release` branch `build-report.json`](https://raw.githubusercontent.com/Lknife666/adfilter/release/build-report.json) for per-file statistics.

---

## Table of Contents

- [Features](#features)
- [Supported Formats](#supported-formats)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [CLI Commands](#cli-commands)
- [Configuration](#configuration)
- [Allowlist](#allowlist)
- [Optimizer](#optimizer)
- [Notifications](#notifications)
- [Docker Deployment](#docker-deployment)
- [CI / Auto-update](#ci--auto-update)
- [Plugin System](#plugin-system)
- [Development](#development)
- [Troubleshooting / FAQ](#troubleshooting--faq)
- [Roadmap](#roadmap)
- [Security](#security)
- [License](#license)
- [Acknowledgments](#acknowledgments)

> **中文文档 / Chinese Documentation**: [README.zh-CN.md](README.zh-CN.md)

---

## Fork + GitHub Actions (Recommended Personalization)

The easiest way to get **your own customized filter list** — no server required:

1. **Fork** this repository on GitHub
2. **Edit** `config/application.yaml` — choose your rule sources, output formats, and allowlist
3. **Enable** GitHub Actions in your fork (Settings → Actions → Allow all actions)
4. **Wait** for the scheduled workflow (every 8 hours) or trigger manually via Actions → "Update Filters" → Run workflow
5. **Subscribe** using your fork's `release` branch URLs:
   ```
   https://raw.githubusercontent.com/<you>/adfilter/release/dns.txt
   ```
6. **(Optional)** Add secrets for notifications: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `DISCORD_WEBHOOK_URL`

> All 12 output formats are generated automatically. Edit `config/application.yaml` to add/remove sources or change formats.

---

## Features

| Category | Highlights |
|----------|-----------|
| **Formats** | 12 output formats including Surge, sing-box, MikroTik, Unbound, Quantumult X, Loon |
| **CLI** | 11 commands: `run`, `validate`, `convert`, `diff`, `stats`, `doctor`, `serve`, `sources`, `init`, `score`, `playground` |
| **Performance** | Async concurrent HTTP fetching, conditional-GET cache, incremental builds |
| **Quality** | Source quality scoring (A–F), efficiency metrics, dead domain detection, subdomain collapse |
| **Security** | Content auditor, protected domains, SSRF protection, build manifest, supply chain guards |
| **Observability** | JSON structured logs, Rich progress bar, build reports, efficiency panels |
| **Extensibility** | Plugin system via `entry_points` for handlers and notifiers |
| **Automation** | Fully unattended: build → audit → publish → GitHub Release (every 8h) |
| **Notifications** | Telegram, Discord, WeCom webhook alerts on build success/failure |

---

## Supported Formats

| Format | Extension | Compatibility | Input | Output |
|--------|-----------|---------------|:-----:|:------:|
| EasyList / ABP | `.txt` | Adblock Plus, uBlock Origin, AdGuard | Yes | Yes |
| AdGuard Home DNS | `.txt` | AdGuard Home, AdGuard DNS | Yes | Yes |
| dnsmasq | `.conf` | dnsmasq, OpenWrt, Pi-hole | Yes | Yes |
| smartdns | `.conf` | SmartDNS | Yes | Yes |
| Clash | `.yaml` | Clash, Clash Meta, Stash | Yes | Yes |
| hosts | `.txt` | All OS, Pi-hole, StevenBlack/hosts | Yes | Yes |
| Surge | `.conf` | Surge, Shadowrocket, Stash | Yes | Yes |
| sing-box | `.json` | sing-box rule-set (v2) | Yes | Yes |
| MikroTik | `.rsc` | MikroTik RouterOS v6/v7 | Yes | Yes |
| Unbound | `.conf` | Unbound DNS resolver | Yes | Yes |
| Quantumult X | `.conf` | Quantumult X | Yes | Yes |
| Loon | `.conf` | Loon | Yes | Yes |

---

## Architecture

```
Config (YAML)
    |
    v
[Parser] ─── Fetcher (HTTP/Local) ─── Handler.parse() ── Rule objects
    |                                                          |
    v                                                          v
[Optimizer] ── subdomain collapse, voting, IDN, allowlist ── optimized Rules
    |
    v
[Writer] ── Handler.format() ── per-format output files
    |
    +── dns.txt
    +── clash.yaml
    +── singbox.json
    +── surge.conf
    +── ...
```

**Key design decisions:**
- **Unified Rule model** — all formats parse into one `Rule` dataclass enabling cross-format conversion
- **Streaming pipeline** — `AsyncIterator[Rule]` keeps memory constant regardless of source size
- **Handler registry** — new formats require only one file + `register_handler()` call
- **Plugin architecture** — third-party handlers/notifiers via Python `entry_points`

See [`docs/architecture.md`](docs/architecture.md) for the complete design document.

---

## Quick Start

```bash
# Install with uv (recommended)
uv sync
uv run adfilter run --config config/application.yaml --progress --report rule/build-report.json

# View the build report
uv run adfilter stats rule/build-report.json

# Serve rules over HTTP for LAN devices
uv run adfilter serve --dir rule/
```

**Without uv:**

```bash
pip install -e .
adfilter run -c config/application.yaml
```

**One-shot format conversion (no config needed):**

```bash
adfilter convert hosts.txt clash.yaml --from hosts --to clash
```

---

## Installation

### From source (recommended)

```bash
git clone https://github.com/Lknife666/adfilter.git
cd adfilter
uv sync            # or: pip install -e .
```

### From PyPI

```bash
pip install adfilter
```

### Docker

```bash
docker pull ghcr.io/lknife666/adfilter:latest
docker run --rm -v ./config:/app/config -v ./rule:/app/rule \
  ghcr.io/lknife666/adfilter run --config /app/config/application.yaml
```

### Requirements

- Python **3.14+**
- Dependencies: `aiohttp`, `pydantic`, `pyyaml`, `typer`, `rich`, `mmh3`, `aiodns`

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `adfilter run` | Run the full fetch/parse/optimize/emit pipeline |
| `adfilter validate` | Validate config file and exit |
| `adfilter convert <src> <dst>` | One-shot file-to-file format conversion |
| `adfilter diff <old> <new>` | Compare two rule files by rule identity |
| `adfilter stats <report.json>` | Pretty-print a build report |
| `adfilter stats <report> -e` | Show rule efficiency metrics (liveness, bloat) |
| `adfilter doctor` | Environment + config health check |
| `adfilter serve --dir rule/` | Serve generated files over HTTP |
| `adfilter sources list\|add\|remove` | Manage rule sources from built-in catalog |
| `adfilter score` | Display source quality scores (A–F grade) |
| `adfilter playground` | Interactive rule debugger (query/whatif) |
| `adfilter init --preset cn\|jp\|global` | Initialize config from a regional preset |
| `adfilter formats` | List all supported formats |
| `adfilter completion bash\|zsh\|fish` | Print shell completion script |

### Examples

```bash
# Full pipeline with progress bar and JSON report
adfilter run -c config/application.yaml --progress --report rule/build-report.json

# Incremental build (skip if inputs unchanged)
adfilter run -c config/application.yaml --incremental

# JSON structured logs for production
adfilter run -c config/application.yaml --json-logs --log-level INFO

# Convert between formats
adfilter convert easylist.txt surge.conf --from easylist --to surge

# Semantic diff (by rule identity, not text)
adfilter diff old_dns.txt new_dns.txt --format dns

# Initialize config for Chinese users
adfilter init --preset cn --output config/application.yaml

# Add sources from the built-in catalog
adfilter sources add anti-ad easyprivacy urlhaus

# View source quality scores
adfilter score

# Interactive rule debugger
adfilter playground --rule-dir rule/

# Efficiency metrics
adfilter stats rule/build-report.json --efficiency
```

---

## Configuration

Config file: `config/application.yaml` (see [`config/application-example.yaml`](config/application-example.yaml) for full reference)

### Minimal Config

```yaml
application:
  config:
    input:
      rule:
        default:
          - name: anti-ad
            type: easylist
            path: https://anti-ad.net/easylist.txt

    output:
      path: ./rule
      files:
        - { name: dns.txt, type: dns }
        - { name: clash.yaml, type: clash }
        - { name: hosts.txt, type: hosts }
```

### Full Config Structure

```yaml
application:
  config:
    input:
      rule:
        <group_name>:
          - name: <unique_id>
            type: easylist|dns|dnsmasq|smartdns|clash|hosts|surge|singbox|mikrotik|unbound|quantumult|loon
            path: <http_url_or_local_path>
            group: <optional_group_tag>
      allowlist:
        - path: config/allowlist.txt

    output:
      path: ./rule
      file_header: |
        ADFS AdBlock ${type}
        Last Modified: ${date}
        Total Size: ${total}
      files:
        - name: dns.txt
          type: dns
          desc: "AdGuard Home DNS filter"
          filter: [basic, wildcard]
          rule: [source1, source2]
          groups: [ads, privacy]

    fetcher:
      http:
        timeout_seconds: 60
        max_retries: 3
        max_concurrency: 8
        cache_dir: .cache/http
        on_failure: cache_then_skip
        max_cache_age_hours: 72

    parser:
      min_length: 4
      max_length: 1024
      alert_length: 6
      incremental_build: false
      progress: false
      json_logs: false
      dns_probe:
        enable: false
        timeout_seconds: 5.0

    optimizer:
      enable: true
      collapse_subdomains: true
      drop_allow_shadowed_deny: true
      min_source_votes: 1
      normalize_idn: true

    notifier:
      enable: false
      on_success: true
      on_failure: true
      channels:
        - type: telegram
          bot_token: ${TELEGRAM_BOT_TOKEN}
          chat_id: ${TELEGRAM_CHAT_ID}
```

### Environment Variable Override

All config values can be overridden via environment variables with `ADFILTER_` prefix:

```bash
export ADFILTER_OUTPUT__PATH=./dist
export ADFILTER_FETCHER__HTTP__TIMEOUT_SECONDS=120
```

### Regional Presets

```bash
adfilter init --preset cn      # Chinese users (anti-ad, easylist-china, cjx-annoyance)
adfilter init --preset jp      # Japanese users (280blocker)
adfilter init --preset global  # International (easylist, easyprivacy, peter-lowe)
```

---

## Allowlist

The allowlist excludes specific domains from being blocked — use it when a website is incorrectly blocked by the filter rules.

### Setup

1. Add the allowlist path to your `config/application.yaml`:

```yaml
application:
  config:
    input:
      allowlist:
        - path: config/allowlist.txt
```

2. Create `config/allowlist.txt` with one domain per line:

```text
# Lines starting with # are comments
# Each domain also matches all its subdomains (suffix matching)

example.com
*.internal.company.net
```

3. Re-run `adfilter run` to regenerate rules with the allowlist applied.

### Format Reference

| Syntax | Meaning | Example |
|--------|---------|---------|
| `example.com` | Exact domain **and all subdomains** | Unblocks `example.com`, `www.example.com`, `sub.example.com` |
| `*.example.com` | Wildcard — matches all subdomains (equivalent to suffix match above) | Unblocks `a.example.com`, `b.c.example.com` |
| `# comment` | Lines starting with `#` are ignored | Use for notes |
| Empty lines | Automatically skipped | Use for readability |

### Notes

- Changes to the allowlist require re-running `adfilter run` to take effect
- Matching is **suffix-based**: adding `example.com` also unblocks `sub.example.com`
- In Docker Compose `--auto-refresh` mode, allowlist changes apply on the next refresh cycle
- The allowlist only affects **output files** — original rule sources are never modified

> For a detailed Chinese walkthrough with more examples, see [README.zh-CN.md](README.zh-CN.md#白名单allowlist).

---

## Optimizer

The optimizer runs after parsing and before writing. All optimizations are optional and configurable:

| Optimization | Config Key | Description |
|-------------|------------|-------------|
| Subdomain collapse | `collapse_subdomains` | Drop `sub.example.com` when `example.com` (overlay) already covers it |
| Allow-shadow elimination | `drop_allow_shadowed_deny` | Remove DENY rules shadowed by an equivalent ALLOW rule |
| Multi-source voting | `min_source_votes` | Only keep rules appearing in N+ distinct sources |
| IDN normalization | `normalize_idn` | Normalize unicode domains to ASCII punycode before dedup |
| Allowlist | `input.allowlist` | Remove DENY rules matching allowlisted domains (exact + suffix) |

---

## Notifications

Get notified when builds succeed or fail via webhook:

| Channel | Config Fields |
|---------|--------------|
| Telegram | `bot_token`, `chat_id` |
| Discord | `webhook_url` |
| WeCom | `webhook_key` |

All sensitive values support `${ENV_VAR}` syntax for safe secret management.

**Third-party notifiers** can be added via the `adfilter.notifiers` entry point (see [Plugin System](#plugin-system)).

---

## Docker Deployment

### Docker Compose (recommended)

```yaml
services:
  adfilter:
    image: ghcr.io/lknife666/adfilter:latest
    volumes:
      - ./config:/app/config:ro
      - rule_data:/app/rule
      - cache_data:/app/.cache
    environment:
      - TZ=Asia/Shanghai
    ports:
      - "8787:8787"
    command: ["serve", "--dir", "/app/rule", "--host", "0.0.0.0",
              "--auto-refresh", "--refresh-interval", "480",
              "--config", "/app/config/application.yaml"]
    healthcheck:
      test: ["CMD", "adfilter", "doctor", "--config", "/app/config/application.yaml"]
      interval: 60s
    restart: unless-stopped

volumes:
  rule_data:
  cache_data:
```

### One-shot Build

```bash
docker run --rm \
  -v ./config:/app/config:ro \
  -v ./rule:/app/rule \
  ghcr.io/lknife666/adfilter run --config /app/config/application.yaml --progress
```

### Image Features

- Multi-stage build (slim runtime image)
- Non-root user (`adfilter`)
- Built-in healthcheck (`adfilter doctor`)
- Auto-published on every push to `main`

---

## CI / Auto-update

| Workflow | Trigger | Purpose |
|---------|---------|---------|
| [`ci.yml`](.github/workflows/ci.yml) | PR + push to main | Run tests + coverage |
| [`auto-update.yml`](.github/workflows/auto-update.yml) | Every 8h + push to main | Build rules, publish to `release` branch, push Docker image |
| [`release.yml`](.github/workflows/release.yml) | Tag `v*` | Publish to PyPI + GitHub Release |
| [`security.yml`](.github/workflows/security.yml) | Push/PR + weekly | pip-audit + Bandit SAST |

The auto-update workflow:
1. Lints the source code
2. Builds all 12 output format files
3. Publishes them to the orphan `release` branch (no source code leak)
4. Uploads debugging artifact (7-day retention)
5. Pushes Docker image to GHCR

---

## Plugin System

### Custom Handlers

Third-party packages can register format handlers:

```toml
# In your package's pyproject.toml
[project.entry-points."adfilter.handlers"]
my_format = "my_package.handler:MyFormatHandler"
```

```python
# my_package/handler.py
from adfilter.handler.base import Handler, register_handler
from adfilter.constants import RuleSet
from adfilter.model import Rule

class MyFormatHandler(Handler):
    rule_set = RuleSet.MY_FORMAT

    def __init__(self):
        register_handler(self.rule_set, self)

    def parse(self, line: str) -> Rule: ...
    def format(self, rule: Rule) -> str | None: ...
    def is_comment(self, line: str) -> bool: ...
    def commented(self, value: str) -> str: ...
```

### Custom Notifiers

```toml
[project.entry-points."adfilter.notifiers"]
slack = "my_package.notifier:SlackNotifier"
```

```python
from adfilter.notifier.base import Notifier, NotifyPayload, register_notifier

class SlackNotifier(Notifier):
    def __init__(self, webhook_url: str):
        self._url = webhook_url

    async def send(self, payload: NotifyPayload) -> bool:
        # Send to Slack...
        return True

register_notifier("slack", SlackNotifier)
```

---

## Development

### Prerequisites

- Python **3.14+**
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Setup

```bash
git clone https://github.com/Lknife666/adfilter.git
cd adfilter
uv sync --group dev
```

### Running Tests

```bash
uv run pytest                              # All tests
uv run pytest --cov=adfilter --cov-report=term  # With coverage
uv run pytest tests/unit/test_optimizer.py  # Specific file
```

### Linting

```bash
uvx ruff check src/
uvx ruff format --check src/
```

### Project Structure

```
src/adfilter/
├── __init__.py             # Version (importlib.metadata)
├── __main__.py             # Entry point (delegates to cli/)
├── cli/                    # CLI commands (Typer)
│   ├── __init__.py         # App instance + command registration
│   ├── run.py              # run + validate commands + pipeline
│   ├── convert.py          # convert command
│   ├── diff.py             # diff command
│   ├── info.py             # stats, doctor, formats, completion
│   ├── serve.py            # serve command
│   └── sources.py          # sources + init commands
├── config.py               # Pydantic configuration models
├── constants.py            # Enums, symbols
├── model.py                # Rule data model (unified)
├── parser.py               # Fetch -> parse -> filter -> dedupe
├── optimizer.py            # Post-parse optimizations
├── writer.py               # Output file writing + sing-box assembly
├── stats.py                # Build report model
├── logging_setup.py        # JSON/Rich log configuration
├── dns_prober.py           # Async DNS existence checker
├── util.py                 # String utilities
├── regex_patterns.py       # Compiled regex patterns
├── fetcher/                # Input fetchers
│   ├── base.py             # Abstract Fetcher
│   ├── factory.py          # Fetcher selection
│   ├── http.py             # HTTP (cache, retry, SSRF guard)
│   └── local.py            # Local filesystem
├── handler/                # Format handlers (12 formats)
│   ├── base.py             # Abstract Handler + registry
│   ├── easylist_handler.py
│   ├── dns_handler.py
│   └── ...                 # (12 handlers total)
├── notifier/               # Webhook notifications
│   ├── base.py             # Abstract + registry + dispatcher
│   ├── telegram.py
│   ├── discord.py
│   └── wecom.py
└── data/                   # Built-in data
    ├── source_catalog.yaml # Known rule sources
    └── presets/            # Regional config presets
        ├── cn.yaml
        ├── jp.yaml
        └── global.yaml
```

### Adding a New Output Format

1. Create `src/adfilter/handler/yourformat_handler.py`
2. Subclass `Handler`, implement `parse()`, `format()`, `is_comment()`, `commented()`
3. Call `register_handler(RuleSet.YOURFORMAT, self)` in `__init__`
4. Add `RuleSet.YOURFORMAT` to `constants.py`
5. Import in `handler/__init__.py`
6. Add tests in `tests/unit/handler/test_yourformat.py`
7. Document in `docs/formats.md`

### Commit Convention

```
feat: new feature
fix: bug fix
perf: performance improvement
docs: documentation
refactor: code refactoring
test: add/update tests
chore: build/CI changes
```

---

## Troubleshooting / FAQ

### Connection timeout / Failed to fetch

Some rule sources are hosted overseas and may be slow or inaccessible. Increase timeout and enable cache fallback:

```yaml
fetcher:
  http:
    timeout_seconds: 120
    max_retries: 5
    on_failure: cache_then_skip
    cache_dir: .cache/http
```

### Empty output files (0 rules)

1. Validate your config: `adfilter validate --config config/application.yaml`
2. Run with `--progress` to see fetch status for each source
3. Generate a build report: `adfilter run --report rule/build-report.json` then `adfilter stats rule/build-report.json`

### A legitimate website is blocked

Add the domain to your allowlist file. See the [Allowlist](#allowlist) section above.

### Docker container won't start

```bash
docker logs adfilter                    # Check logs
# Common fixes:
# - Verify volume mounts point to correct paths
# - Ensure rule/ directory is writable: chmod 777 ./rule
# - Check port conflicts: use -p 9999:8787 if 8787 is taken
```

### YAML config parse error

- Use spaces, not tabs (YAML requires spaces for indentation)
- Ensure a space after colons: `name: value` (not `name:value`)
- Run `adfilter validate --config config/application.yaml` to check

### How to schedule automatic rule updates?

- **Docker Compose**: Use `--auto-refresh --refresh-interval 480` in the command (updates every 8h)
- **Cron**: `0 */8 * * * cd /path/to/adfilter && uv run adfilter run -c config/application.yaml`
- **No self-hosting**: Just subscribe to the [Rule Subscription](#rule-subscription) URLs (auto-updated every 8h via GitHub Actions)

### How to access `adfilter serve` from LAN devices?

Use `http://<your-machine-ip>:8787/<filename>` (e.g. `http://192.168.1.100:8787/dns.txt`). Ensure port 8787 is open in your firewall.

### Python 3.14+ is too new, can't install

Use Docker instead (no Python required). Or use `uv python install 3.14` to manage Python versions automatically.

### `uv` command not found

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc   # or ~/.zshrc
uv --version
# Alternative: use pip instead of uv
pip install -e . && adfilter run -c config/application.yaml
```

> For more detailed troubleshooting in Chinese, see [README.zh-CN.md](README.zh-CN.md#常见问题--faq).

---

## Roadmap

See [`ROADMAP.md`](ROADMAP.md) for the detailed iteration plan. Current status:

- **v0.5** ✅ Security — Content auditor, build manifest, protected domains, supply chain guards
- **v0.6** ✅ Quality — Source quality scoring (A–F), rule efficiency metrics, health dashboard
- **v0.7** ✅ DX — Interactive playground, JSON Schema for IDE, `stats --efficiency`
- **v1.0** ✅ Production — Fully autonomous pipeline, audit-gated releases, 7 sources

---

## Security

- **Content Auditor**: Checks rules against a protected domains list before publishing; blocks releases that would break critical infrastructure (google.com, github.com, etc.)
- **Build Guard**: Detects anomalous rule count drops (>30%), source failure ratios, and output file size anomalies
- **Build Manifest**: Every release includes `manifest.json` with SHA-256 hashes for integrity verification
- **SSRF Protection**: HTTP fetcher blocks requests to private/reserved IP ranges (RFC 1918, loopback, link-local)
- **Supply Chain**: Audit-gated publishing — CI won't publish if content audit fails
- **Non-root Docker**: Container runs as unprivileged `adfilter` user
- **SAST**: Weekly Bandit scans via CI
- **Dependency Audit**: Weekly pip-audit + Dependabot auto-updates
- **Secret Management**: All tokens support `${ENV_VAR}` syntax, never hardcoded

---

## License

[MIT](LICENSE) — Copyright (c) 2024-2026 Lknife666

---

## Acknowledgments

adfilter aggregates and converts rules from the following outstanding open-source filter lists. Huge thanks to their maintainers:

| Project | Description | Repository |
|---------|-------------|------------|
| **anti-AD** | Chinese ad filter list | [privacy-protection-tools/anti-AD](https://github.com/privacy-protection-tools/anti-AD) |
| **EasyList** | ABP official ad blocking list | [easylist/easylist](https://github.com/easylist/easylist) |
| **EasyList China** | EasyList supplement for China | [easylist/easylistchina](https://github.com/easylist/easylistchina) |
| **EasyPrivacy** | ABP official privacy/tracking list | [easylist/easylist](https://github.com/easylist/easylist) |
| **CJX's Annoyance List** | Chinese anti-annoyance filters | [cjx82630/cjxlist](https://github.com/cjx82630/cjxlist) |
| **AdGuard DNS Filter** | AdGuard official DNS filter | [AdguardTeam/AdGuardSDNSFilter](https://github.com/AdguardTeam/AdGuardSDNSFilter) |
| **Peter Lowe's List** | Ad/tracking server list | [pgl.yoyo.org](https://pgl.yoyo.org/adservers/) |
| **URLhaus** | Malicious URL blocklist | [abuse.ch/urlhaus](https://urlhaus.abuse.ch/) |
| **Phishing Army** | Phishing domain blocklist | [phishing-army](https://github.com/phishing-army/phishing_army_blocklist) |
| **280blocker** | Japanese ad blocking list | [280blocker.net](https://280blocker.net/) |

> Without these community-maintained filter lists, adfilter would have nothing to aggregate. Thank you!
