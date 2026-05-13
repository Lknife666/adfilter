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
    <a href="https://github.com/Lknife666/adfilter/blob/main/LICENSE"><img src="https://img.shields.io/github/license/Lknife666/adfilter" alt="License"></a>
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

- [中文快速上手教程](#中文快速上手教程)
- [Features](#features)
- [Supported Formats](#supported-formats)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [CLI Commands](#cli-commands)
- [Configuration](#configuration)
- [Allowlist (白名单)](#allowlist-白名单)
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

---

## 中文快速上手教程

> 本节面向 **零基础用户**，手把手教你从零开始搭建属于自己的广告过滤规则。

### 你属于哪类用户？

| 我的需求 | 推荐方案 | 难度 |
|---------|---------|------|
| 只想用现成的规则，不想折腾 | 直接复制上方 [Rule Subscription](#rule-subscription) 表格中的链接到你的工具即可，**不需要安装任何东西** | 零门槛 |
| 想自定义规则源 + 白名单，每天自动更新 | **Fork 本仓库 + GitHub Actions 自动构建**（强烈推荐） | 简单 |
| 想在自己局域网搭建 HTTP 订阅服务 | Docker 部署 | 中等 |
| 想深度定制、二次开发 | 从源码安装 或 一键脚本 | 需要 Python 基础 |

---

### 方案一：直接使用现成规则（推荐大多数用户）

你不需要安装任何东西！只需要：

1. 找到上方 [Rule Subscription](#rule-subscription) 表格
2. 根据你使用的工具，复制对应的 Subscribe URL
3. 粘贴到你的广告屏蔽工具里

**常见工具的操作方法：**

| 工具 | 操作步骤 |
|------|---------|
| **AdGuard Home** | 进入后台 → 过滤器 → DNS 封锁清单 → 添加封锁清单 → 粘贴 `dns.txt` 链接 |
| **Clash / Clash Meta** | 在配置文件的 `rule-providers` 中添加 `clash.yaml` 链接，格式参考 Clash 文档 |
| **Surge / Shadowrocket** | 配置 → 规则 → 外部规则集 → 粘贴 `surge.conf` 链接 |
| **Quantumult X** | 配置文件 → `[filter_remote]` 区块 → 添加 `quantumult.conf` 链接 |
| **Loon** | 配置 → 插件/规则 → 远程规则 → 粘贴 `loon.conf` 链接 |
| **Pi-hole** | Admin Panel → Adlists → 粘贴 `hosts.txt` 链接 → 点击 Add → 执行 `pihole -g` 更新 |
| **浏览器插件 (uBlock Origin / Adblock Plus)** | 设置 → 过滤列表 → 自定义 → 粘贴 `easylist.txt` 链接 |

---

### 方案二：Fork 仓库 + GitHub Actions 自动构建（强烈推荐）

> **这是最推荐的个性化方案**：无需服务器、无需安装任何东西、免费、每天自动更新。
> 你只需要一个 GitHub 账号。

#### 原理

```
你 Fork 本仓库 → 修改配置文件 → GitHub Actions 每天自动构建
                                         ↓
                            你的私有 release 分支（规则文件）
                                         ↓
                         你的工具订阅你自己仓库的链接
```

#### 第 1 步：Fork 仓库

1. 点击本页面右上角的 **Fork** 按钮
2. 创建你自己的副本：`https://github.com/你的用户名/adfilter`

#### 第 2 步：启用 GitHub Actions

Fork 后默认 Actions 可能是禁用的：

1. 进入你 fork 的仓库
2. 点击顶部 **Actions** 标签
3. 点击 **"I understand my workflows, go ahead and enable them"**

#### 第 3 步：修改配置文件

编辑 `config/application.yaml`（直接在 GitHub 网页上编辑即可）：

```yaml
application:
  config:
    input:
      rule:
        default:
          # ===== 在这里选择你想要的规则源 =====
          # 去广告（推荐）
          - name: anti-ad
            type: easylist
            path: https://anti-ad.net/easylist.txt

          # 隐私防护（推荐）
          - name: easyprivacy
            type: easylist
            path: https://easylist.to/easylist/easyprivacy.txt

          # 中国区补充（中国用户推荐）
          - name: easylist-china
            type: easylist
            path: https://easylist-downloads.adblockplus.org/easylistchina.txt

          # 恶意软件防护（可选）
          - name: urlhaus
            type: hosts
            path: https://urlhaus.abuse.ch/downloads/hostfile/

          # ===== 删除不需要的源，或添加你自己的 =====

      # 白名单：把你不想被屏蔽的域名写在这里
      allowlist:
        - path: config/allowlist.txt

    output:
      path: ./rule
      files:
        - { name: dns.txt,          type: dns,        desc: "AdGuard Home DNS" }
        - { name: easylist.txt,     type: easylist,   desc: "EasyList / ABP" }
        - { name: clash.yaml,       type: clash,      desc: "Clash 规则" }
        - { name: singbox.json,     type: singbox,    desc: "sing-box rule-set" }
        - { name: surge.conf,       type: surge,      desc: "Surge 规则" }
        - { name: quantumult.conf,  type: quantumult, desc: "Quantumult X" }
        - { name: loon.conf,        type: loon,       desc: "Loon" }
        - { name: dnsmasq.conf,     type: dnsmasq,    desc: "dnsmasq" }
        - { name: smartdns.conf,    type: smartdns,   desc: "SmartDNS" }
        - { name: hosts.txt,        type: hosts,      desc: "hosts 文件" }
        - { name: mikrotik.rsc,     type: mikrotik,   desc: "MikroTik" }
        - { name: unbound.conf,     type: unbound,    desc: "Unbound" }

    optimizer:
      enable: true
      collapse_subdomains: true
      drop_allow_shadowed_deny: true
      normalize_idn: true
```

#### 第 4 步：创建白名单文件（可选）

创建 `config/allowlist.txt`，写入不想被屏蔽的域名（每行一个）：

```text
# 被误杀的网站
mybank.com
login.partner-site.com

# 开发需要
localhost
```

#### 第 5 步：等待自动构建

提交修改后，GitHub Actions 会：
- **立即触发**一次构建（push 到 main 时）
- 之后每 **8 小时**自动构建一次

你也可以手动触发：进入 Actions → "Update Filters" → Run workflow

#### 第 6 步：获取你的个人订阅链接

构建完成后，规则文件发布到你仓库的 `release` 分支。订阅链接格式：

```
https://raw.githubusercontent.com/你的用户名/adfilter/release/dns.txt
https://raw.githubusercontent.com/你的用户名/adfilter/release/clash.yaml
https://raw.githubusercontent.com/你的用户名/adfilter/release/hosts.txt
... (其他格式同理)
```

将这些链接粘贴到你的广告屏蔽工具中即可。

#### 如何同步上游更新？

当本仓库有新功能或 Bug 修复时，你可以同步：

1. 在你的 Fork 仓库页面，点击 **Sync fork** 按钮
2. 或者使用 GitHub CLI：`gh repo sync 你的用户名/adfilter`

> 同步不会覆盖你的配置文件（只要你只修改了 `config/` 目录）。

#### 进阶：修改构建频率

编辑 `.github/workflows/auto-update.yml`，修改 `cron` 表达式：

```yaml
on:
  schedule:
    - cron: "0 */8 * * *"    # 每 8 小时（默认）
    # - cron: "0 2 * * *"    # 每天凌晨 2 点
    # - cron: "0 */4 * * *"  # 每 4 小时
```

---

### 方案三：Docker 部署（自定义规则源）

适合想自己选择屏蔽哪些列表、或在局域网内给多台设备提供规则的用户。

#### 第 1 步：安装 Docker

如果你还没有 Docker，参考官方安装指南：
- Windows / Mac: 安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- Linux: `curl -fsSL https://get.docker.com | sh`

#### 第 2 步：创建项目目录

```bash
mkdir adfilter && cd adfilter
mkdir config rule
```

#### 第 3 步：创建配置文件

创建 `config/application.yaml`，以下是一个适合中国用户的示例：

```yaml
application:
  config:
    input:
      rule:
        default:
          # anti-AD — 国内最流行的广告过滤列表
          - name: anti-ad
            type: easylist
            path: https://anti-ad.net/easylist.txt

          # EasyList China — 补充国内网站规则
          - name: easylist-china
            type: easylist
            path: https://easylist-downloads.adblockplus.org/easylistchina.txt

          # EasyPrivacy — 隐私追踪防护
          - name: easyprivacy
            type: easylist
            path: https://easylist.to/easylist/easyprivacy.txt

      # 白名单：在这里添加你不想被屏蔽的网站
      allowlist:
        - path: config/allowlist.txt

    output:
      path: ./rule
      files:
        - { name: dns.txt,       type: dns,       desc: "AdGuard Home DNS" }
        - { name: clash.yaml,    type: clash,     desc: "Clash 规则" }
        - { name: hosts.txt,     type: hosts,     desc: "hosts 文件" }
        - { name: easylist.txt,  type: easylist,  desc: "EasyList 格式" }
        - { name: surge.conf,    type: surge,     desc: "Surge 规则" }
        - { name: dnsmasq.conf,  type: dnsmasq,   desc: "dnsmasq 规则" }

    optimizer:
      enable: true
      collapse_subdomains: true
```

#### 第 4 步：创建白名单文件（可选）

```bash
touch config/allowlist.txt
```

如果有不想被屏蔽的域名，每行写一个（详见 [Allowlist 白名单](#allowlist-白名单) 章节）。

#### 第 5 步：运行！

**一次性生成规则：**

```bash
docker run --rm \
  -v ./config:/app/config:ro \
  -v ./rule:/app/rule \
  ghcr.io/lknife666/adfilter run --config /app/config/application.yaml --progress
```

运行完成后，`rule/` 目录下就会出现生成好的规则文件。

**长期运行（HTTP 服务 + 自动更新）：**

创建 `docker-compose.yml`：

```yaml
services:
  adfilter:
    image: ghcr.io/lknife666/adfilter:latest
    volumes:
      - ./config:/app/config:ro
      - ./rule:/app/rule
    environment:
      - TZ=Asia/Shanghai
    ports:
      - "8787:8787"
    command: ["serve", "--dir", "/app/rule", "--host", "0.0.0.0",
              "--auto-refresh", "--refresh-interval", "480",
              "--config", "/app/config/application.yaml"]
    restart: unless-stopped
```

```bash
docker compose up -d
```

现在你的规则文件可以通过 `http://你的IP:8787/dns.txt` 等地址访问了！  
局域网内的 AdGuard Home、Clash 等工具都可以指向这个地址。

---

### 方案四：从源码安装（高级用户）

#### 一键脚本安装（推荐）

我们提供了一个交互式安装脚本，会引导你完成规则源选择、白名单配置、输出格式选择、定时任务设置：

```bash
# 下载并运行一键安装脚本
curl -fsSL https://raw.githubusercontent.com/Lknife666/adfilter/main/setup.sh | bash

# 或者指定安装目录
curl -fsSL https://raw.githubusercontent.com/Lknife666/adfilter/main/setup.sh | bash -s -- ~/my-adfilter
```

脚本会自动：
1. 安装 `uv`（Python 包管理器）
2. 克隆项目并安装依赖
3. 通过交互式菜单让你选择规则源、输出格式
4. 配置白名单
5. 生成个性化 `config/application.yaml`
6. 执行首次构建
7. 可选配置 cron 定时任务（每天自动更新）

#### 手动安装

#### 什么是 uv？

[uv](https://docs.astral.sh/uv/) 是一个极速的 Python 包管理器（类似 pip，但快 10-100 倍）。adfilter 推荐使用 uv 来安装依赖。

#### 第 1 步：安装 uv

```bash
# Linux / macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 验证安装
uv --version
```

> 如果你不想安装 uv，也可以用传统的 `pip`，见下方替代方案。

#### 第 2 步：克隆项目

```bash
git clone https://github.com/Lknife666/adfilter.git
cd adfilter
```

#### 第 3 步：安装依赖

```bash
# 使用 uv（推荐）
uv sync

# 或者使用 pip（替代方案）
pip install -e .
```

#### 第 4 步：初始化配置

```bash
# 使用中国区预设（会自动添加适合国内的规则源）
uv run adfilter init --preset cn --output config/application.yaml

# 也可以选择其他预设：
# uv run adfilter init --preset global   # 国际通用
# uv run adfilter init --preset jp       # 日本
```

#### 第 5 步：运行规则生成

```bash
uv run adfilter run --config config/application.yaml --progress
```

你会看到进度条，完成后在 `rule/` 目录下找到所有生成的规则文件。

#### 第 6 步：查看生成结果

```bash
# 查看构建报告
uv run adfilter run --config config/application.yaml --progress --report rule/build-report.json
uv run adfilter stats rule/build-report.json

# 在局域网中提供 HTTP 服务（其他设备可通过 http://你的IP:8787/ 访问）
uv run adfilter serve --dir rule/
```

---

### 如何添加/删除规则源？

**命令行方式（推荐）：**

```bash
# 查看所有可用的规则源
uv run adfilter sources list

# 添加规则源
uv run adfilter sources add anti-ad easyprivacy urlhaus

# 删除规则源
uv run adfilter sources remove urlhaus
```

**手动编辑配置文件：**

在 `config/application.yaml` 的 `input.rule.default` 列表中添加/删除条目：

```yaml
- name: 我的自定义源       # 给它起个名字（不要重复）
  type: easylist          # 规则格式（easylist/dns/hosts/clash/dnsmasq 等）
  path: https://example.com/my-rules.txt   # 规则文件的网址
```

修改配置后，重新运行 `adfilter run` 即可生效。

---

## Features

| Category | Highlights |
|----------|-----------|
| **Formats** | 12 output formats including Surge, sing-box, MikroTik, Unbound, Quantumult X, Loon |
| **CLI** | 9 commands: `run`, `validate`, `convert`, `diff`, `stats`, `doctor`, `serve`, `sources`, `init` |
| **Performance** | Async concurrent HTTP fetching, conditional-GET cache, incremental builds |
| **Quality** | Subdomain collapse, allow-shadow elimination, multi-source voting, IDN normalization |
| **Observability** | JSON structured logs, Rich progress bar, build reports |
| **Extensibility** | Plugin system via `entry_points` for handlers and notifiers |
| **Security** | SSRF protection, non-root Docker, Bandit SAST, dependency auditing |
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
| `adfilter doctor` | Environment + config health check |
| `adfilter serve --dir rule/` | Serve generated files over HTTP |
| `adfilter sources list\|add\|remove` | Manage rule sources from built-in catalog |
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

## Allowlist (白名单)

白名单用于排除被误杀的域名——当某个网站被错误屏蔽时，把它加入白名单即可恢复访问。

### 基本用法

#### 第 1 步：在配置文件中启用白名单

在 `config/application.yaml` 中添加 `allowlist` 配置：

```yaml
application:
  config:
    input:
      rule:
        default:
          - name: anti-ad
            type: easylist
            path: https://anti-ad.net/easylist.txt
      # ↓↓↓ 添加这一段 ↓↓↓
      allowlist:
        - path: config/allowlist.txt
```

#### 第 2 步：创建白名单文件

创建 `config/allowlist.txt`，每行写一个要放行的域名：

```text
# 白名单文件 - 每行一个域名
# 以 # 开头的行是注释，会被忽略

# 示例：某个被误杀的购物网站
shop.example.com

# 示例：某个被误杀的视频网站
video.example.cn

# 示例：公司内部域名
*.internal.mycompany.com
```

#### 第 3 步：重新生成规则

```bash
# Docker 用户
docker run --rm -v ./config:/app/config:ro -v ./rule:/app/rule \
  ghcr.io/lknife666/adfilter run --config /app/config/application.yaml

# 源码用户
uv run adfilter run --config config/application.yaml
```

白名单生效后，匹配的域名会从所有输出规则中移除。

### 白名单格式说明

| 写法 | 含义 | 示例 |
|------|------|------|
| `example.com` | 精确匹配该域名 **及其所有子域名** | 放行 `example.com`、`www.example.com`、`sub.example.com` |
| `*.example.com` | 通配符，匹配所有子域名（等同于上面的后缀匹配） | 放行 `a.example.com`、`b.c.example.com` |
| `# 注释` | 以 `#` 开头的行会被忽略 | 用来写备注 |
| 空行 | 会被自动跳过 | 用来分组、增加可读性 |

### 常见场景示例

```text
# ━━━ 被误杀的网站 ━━━
# 某电商平台的统计域名被误伤，导致无法正常下单
analytics.shop.com

# ━━━ 公司/学校内部域名 ━━━
*.corp.mycompany.cn
oa.myschool.edu.cn

# ━━━ 开发调试需要 ━━━
localhost
*.local
*.test
```

### 注意事项

- 白名单文件修改后，需要重新运行 `adfilter run` 才能生效
- 白名单是 **后缀匹配** 的：写 `example.com` 会同时放行 `sub.example.com`
- 如果你使用 Docker Compose 的 `--auto-refresh` 模式，白名单会在下次自动刷新时生效
- 白名单只影响 **输出结果**，不会修改原始规则源

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

### 常见问题

#### Q: 运行报错 "Connection timeout" 或 "Failed to fetch"

**原因：** 部分规则源服务器在国外，网络不通或超时。

**解决方案：**

```yaml
# 在 config/application.yaml 中增加超时时间和重试次数
fetcher:
  http:
    timeout_seconds: 120      # 默认 60，改大一些
    max_retries: 5            # 默认 3，多重试几次
    on_failure: cache_then_skip  # 失败时使用缓存或跳过，不中断整个构建
    cache_dir: .cache/http    # 启用缓存，下次即使超时也能用上次的结果
```

如果长期无法访问某个源，考虑把它从配置中删除，或者换用国内镜像地址。

---

#### Q: 生成的规则文件是空的 / 规则数量为 0

**可能原因：**
1. 所有规则源都拉取失败了（检查网络）
2. 配置文件中 `input.rule` 为空
3. `output.files` 中的 `filter` 设置过于严格

**排查步骤：**

```bash
# 1. 检查配置是否正确
uv run adfilter validate --config config/application.yaml

# 2. 运行时加 --progress 看具体进度
uv run adfilter run --config config/application.yaml --progress

# 3. 生成 build-report 查看详情
uv run adfilter run --config config/application.yaml --report rule/build-report.json
uv run adfilter stats rule/build-report.json
```

---

#### Q: 某个正常网站被误杀了，打不开

**解决方案：** 将该域名加入白名单。

1. 打开 `config/allowlist.txt`（没有就创建一个）
2. 添加被误杀的域名，例如：
   ```text
   被误杀的网站.com
   ```
3. 确保配置文件中启用了 allowlist：
   ```yaml
   input:
     allowlist:
       - path: config/allowlist.txt
   ```
4. 重新运行 `adfilter run`

详见 [Allowlist (白名单)](#allowlist-白名单) 章节。

---

#### Q: Docker 容器起不来 / 报错退出

**排查步骤：**

```bash
# 查看容器日志
docker logs adfilter

# 常见原因 1: 配置文件路径不对
# 确保 volumes 映射正确，容器内路径是 /app/config/application.yaml
docker run --rm -v ./config:/app/config:ro ghcr.io/lknife666/adfilter validate --config /app/config/application.yaml

# 常见原因 2: 权限问题
# rule 目录需要可写
chmod 777 ./rule

# 常见原因 3: 端口被占用（serve 模式）
# 改用其他端口
docker run --rm -p 9999:8787 ...
```

---

#### Q: 配置文件 YAML 格式报错

**常见错误：**
- 缩进不一致（YAML 必须用空格，不能用 Tab）
- 冒号后面少了空格（正确: `name: value`，错误: `name:value`）
- 特殊字符没有加引号

**建议：** 使用在线 YAML 校验工具（如 [yamllint.com](https://www.yamllint.com/)）检查格式，或者运行：

```bash
uv run adfilter validate --config config/application.yaml
```

---

#### Q: 怎么知道一共生成了多少条规则？

```bash
# 方法 1: 使用 stats 命令
uv run adfilter run --config config/application.yaml --report rule/build-report.json
uv run adfilter stats rule/build-report.json

# 方法 2: 直接数行数
wc -l rule/*.txt rule/*.yaml rule/*.conf
```

---

#### Q: 如何定时自动更新规则？

**方案 1：Docker Compose + auto-refresh（推荐）**

```yaml
command: ["serve", "--dir", "/app/rule", "--host", "0.0.0.0",
          "--auto-refresh", "--refresh-interval", "480",
          "--config", "/app/config/application.yaml"]
```

这样每 480 分钟（8 小时）会自动重新拉取并生成规则。

**方案 2：Linux crontab**

```bash
# 每 8 小时执行一次
0 */8 * * * cd /path/to/adfilter && uv run adfilter run --config config/application.yaml
```

**方案 3：直接使用 GitHub Actions 自动发布的规则**

本项目已配置每 8 小时自动更新，直接订阅 [Rule Subscription](#rule-subscription) 中的链接即可，无需自建。

---

#### Q: `uv` 安装失败 / 命令找不到

```bash
# 重新安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 如果提示命令找不到，需要重新加载 shell 配置
source ~/.bashrc    # 或 source ~/.zshrc

# 验证
uv --version

# 如果实在装不上 uv，可以用 pip 替代：
pip install -e .
adfilter run --config config/application.yaml
```

---

#### Q: 局域网其他设备怎么访问我 serve 的规则？

1. 确认运行 adfilter serve 的机器 IP（例如 `192.168.1.100`）
2. 确认防火墙允许 8787 端口访问
3. 在其他设备的广告屏蔽工具中，使用如下地址订阅：
   ```
   http://192.168.1.100:8787/dns.txt
   http://192.168.1.100:8787/clash.yaml
   http://192.168.1.100:8787/hosts.txt
   ```

**防火墙放行（Linux）：**
```bash
# ufw
sudo ufw allow 8787/tcp

# firewalld
sudo firewall-cmd --add-port=8787/tcp --permanent && sudo firewall-cmd --reload
```

---

#### Q: Python 版本要求 3.14+，我装不了怎么办？

推荐使用 Docker 方式运行，无需关心 Python 版本。如果一定要从源码安装：

```bash
# 使用 uv 自动管理 Python 版本（推荐）
uv python install 3.14
uv sync

# 或者使用 pyenv
pyenv install 3.14.0
pyenv local 3.14.0
```

---

## Roadmap

See [`ROADMAP.md`](ROADMAP.md) for the detailed iteration plan including:

- **v0.4** (current) — Plugin system, source catalog, regional presets, Quantumult X & Loon formats
- **v1.0** — PyPI release, Helm chart, performance benchmarks, security hardening, i18n

---

## Security

- **SSRF Protection**: HTTP fetcher blocks requests to private/reserved IP ranges (RFC 1918, loopback, link-local)
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
