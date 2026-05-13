# adfilter Roadmap

> 本文档为 adfilter 项目的详细迭代计划，涵盖各版本里程碑的具体实现方案、技术难点与解决思路。
>
> 当前版本：**v0.1.0** | 最后更新：2026-05-13

---

## 目录

- [版本总览](#版本总览)
- [v0.2.0 — 稳定性 & 测试](#v020--稳定性--测试)
- [v0.3.0 — 订阅体验](#v030--订阅体验)
- [v0.4.0 — 生态扩展](#v040--生态扩展)
- [v1.0.0 — 生产就绪](#v100--生产就绪)
- [持续迭代方向](#持续迭代方向横向)

---

## 版本总览

```
v0.1.0 (当前)  ──▶  v0.2.0 (短期)  ──▶  v0.3.0 (中期)  ──▶  v0.4.0 (中长期)  ──▶  v1.0.0 (长期)
   │                    │                    │                     │                     │
   │  20个差异化功能     │  测试+CI+文档      │  Web面板+通知       │  插件化+新格式       │  PyPI+K8s+安全
   │  10种输出格式       │  错误降级策略      │  白名单+分类输出    │  规则源市场          │  性能基线
   │  增量构建           │  Docker优化        │  热更新             │  多语言/地区         │  国际化
```

---

## v0.2.0 — 稳定性 & 测试

**目标时间**：v0.1.0 发布后 4-6 周
**核心目标**：建立质量保障体系，确保后续迭代不引入回归。

### 1. 测试覆盖

#### 实现方案

```
tests/
├── conftest.py                  # 公共 fixtures（临时目录、mock 配置等）
├── unit/
│   ├── test_parser.py           # 每种输入格式的解析逻辑
│   ├── test_optimizer.py        # 子域折叠、Allow阴影、多源投票、IDN
│   ├── test_model.py            # Rule 数据模型边界条件
│   ├── test_config.py           # 配置加载、默认值、校验
│   └── handler/
│       ├── test_easylist.py
│       ├── test_dns.py
│       ├── test_clash.py
│       ├── test_surge.py
│       ├── test_singbox.py
│       ├── test_mikrotik.py
│       ├── test_unbound.py
│       ├── test_dnsmasq.py
│       ├── test_smartdns.py
│       └── test_hosts.py
├── integration/
│   ├── test_full_pipeline.py    # 端到端：输入 → 解析 → 优化 → 输出
│   ├── test_incremental.py      # 增量构建完整流程
│   └── test_cli.py              # 每个 CLI 子命令的集成测试
└── fixtures/
    ├── sample_easylist.txt
    ├── sample_hosts.txt
    └── expected_output/
```

#### 技术要点

| 要点 | 方案 |
|------|------|
| 测试框架 | `pytest` + `pytest-asyncio`（fetcher 是 async） |
| Mock HTTP | `aioresponses` mock 外部 HTTP 请求，避免网络依赖 |
| 临时文件 | `tmp_path` fixture 确保测试隔离 |
| 覆盖率 | `pytest-cov`，目标 ≥ 80% 行覆盖 |
| 快照测试 | 对输出文件使用 `syrupy` 做快照断言，防止格式漂移 |

#### 疑难点

1. **异步测试**：parser/fetcher 大量使用 `asyncio`，需要正确配置 `pytest-asyncio` 的 `mode=auto`，避免 event loop 冲突。
2. **sing-box JSON 结构验证**：输出是嵌套 JSON，需要用 JSON Schema 验证结构而非简单字符串匹配。
3. **IDN 测试数据**：需要覆盖各种边界 case（混合中英文域名、已经是 punycode 的输入、无效 punycode）。

---

### 2. CI 完善

#### 实现方案

在 `auto-update.yml` 中新增 `test` job，或创建独立的 `ci.yml`：

```yaml
# .github/workflows/ci.yml
name: CI
on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.14"]  # 未来扩展到 3.15
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv python install ${{ matrix.python-version }}
      - run: uv sync
      - run: uv run pytest --cov=adfilter --cov-report=xml -q
      - uses: codecov/codecov-action@v4
        with:
          files: coverage.xml
          token: ${{ secrets.CODECOV_TOKEN }}
```

#### 疑难点

1. **Python 3.14 可用性**：GitHub Actions 的 `setup-python` 可能尚未支持 3.14，需依赖 `astral-sh/setup-uv` 的 `uv python install`。
2. **Codecov Token**：公开仓库可以用 tokenless 上传，但私有仓库需配置 secret。

---

### 3. 文档体系

#### 实现方案

```
docs/
├── configuration.md       # 每个配置字段的详细说明 + 示例
├── formats.md             # 10 种输出格式的规范、兼容性说明
├── contributing.md        # 开发环境搭建、代码风格、PR 流程
├── architecture.md        # 模块关系图、数据流
└── changelog.md           # 手动维护 或 用 git-cliff 自动生成
```

#### 技术要点

- 使用 `mkdocs` + `mkdocs-material` 生成文档站点
- 可部署到 GitHub Pages（`gh-pages` 分支）
- 配置字段文档从 Pydantic model 的 `Field(description=...)` 自动提取

---

### 4. 错误处理 & 降级策略

#### 实现方案

```python
# fetcher/http.py 增强
class FetchResult:
    content: str | None
    source: Literal["network", "cache", "skip"]
    error: Exception | None

async def fetch_with_fallback(url: str) -> FetchResult:
    try:
        resp = await conditional_get(url)
        return FetchResult(content=resp, source="network", error=None)
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        # 降级 1：尝试使用本地缓存
        cached = load_from_cache(url)
        if cached:
            logger.warning(f"源不可达，使用缓存: {url}")
            return FetchResult(content=cached, source="cache", error=e)
        # 降级 2：跳过该源
        logger.error(f"源不可达且无缓存，跳过: {url}")
        return FetchResult(content=None, source="skip", error=e)
```

#### 配置项

```yaml
fetcher:
  http:
    on_failure: cache_then_skip  # 可选: fail_fast | cache_then_skip | skip_always
    max_cache_age_hours: 72      # 缓存超过此时间视为过期
```

#### 疑难点

1. **缓存一致性**：缓存文件可能很旧，需要在构建报告中标记哪些源用了缓存版本。
2. **部分失败的构建**：如果 3/5 源失败，输出文件的规则数骤降，需要告警机制（规则数下降超过阈值时报警）。

---

### 5. Dockerfile 优化

#### 实现方案

```dockerfile
# ── 构建阶段 ──
FROM python:3.14-slim AS builder
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen --no-dev --no-editable
COPY src/ src/

# ── 运行阶段 ──
FROM python:3.14-slim AS runtime
RUN useradd -r -s /bin/false adfilter
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY config/ config/
ENV PATH="/app/.venv/bin:$PATH"
USER adfilter
HEALTHCHECK --interval=60s --timeout=10s \
  CMD adfilter doctor --quiet || exit 1
ENTRYPOINT ["adfilter"]
CMD ["run", "--config", "config/application.yaml", "--progress"]
```

#### 优化点

| 优化 | 效果 |
|------|------|
| 多阶段构建 | 镜像体积减少 ~60%（不含编译工具链） |
| 非 root 用户 | 安全加固 |
| HEALTHCHECK | 容器编排平台可感知健康状态 |
| `.dockerignore` | 排除 `.git`、`rule/`、`tests/`，加速构建上下文传输 |

---


## v0.3.0 — 订阅体验

**目标时间**：v0.2.0 后 6-8 周
**核心目标**：提升终端用户订阅规则的体验，从"裸文件"进化到"产品化服务"。

### 1. Web Dashboard

#### 实现方案

```
src/adfilter/web/
├── __init__.py
├── app.py              # Litestar/FastAPI 应用入口
├── routes/
│   ├── dashboard.py    # 首页：构建状态、规则统计卡片
│   ├── subscribe.py    # 订阅链接生成器（按格式/分组）
│   └── api.py          # REST API：触发构建、查询状态
├── templates/
│   └── index.html      # Jinja2 模板（或前端 SPA）
└── static/
    └── style.css
```

#### 技术选型

| 组件 | 选择 | 理由 |
|------|------|------|
| Web 框架 | Litestar | 比 FastAPI 更轻量、原生支持 dataclass、性能更好 |
| 模板 | Jinja2 | 服务端渲染，不需要前端构建步骤 |
| 样式 | Tailwind CSS (CDN) | 零构建配置，UI 美观 |
| 数据 | 读取 `build-report.json` | 无需数据库 |

#### 功能点

1. **构建状态卡片**：最后构建时间、规则总数、各文件行数
2. **一键订阅**：根据用户选择的格式 + base URL 生成可复制的订阅链接
3. **规则搜索**：输入域名，查看是否在当前规则中（哪些源贡献了它）
4. **手动触发构建**：POST `/api/build` 触发一次完整 pipeline

#### 疑难点

1. **与 CLI 共存**：Web 是可选功能，不引入 CLI-only 场景的额外依赖。使用 `extras` 分组：
   ```toml
   [project.optional-dependencies]
   web = ["litestar>=2.0", "jinja2>=3.1", "uvicorn>=0.30"]
   ```
2. **并发安全**：Web 触发构建时，需要文件锁或队列防止同时写入输出文件。
3. **静态文件服务**：生产环境应通过 Nginx/Caddy 代理，Dashboard 只做管理。

---

### 2. Webhook 通知

#### 实现方案

```python
# src/adfilter/notifier/
├── __init__.py
├── base.py          # NotifierProtocol
├── telegram.py      # Telegram Bot API
├── discord.py       # Discord Webhook
├── wecom.py         # 企业微信群机器人
└── factory.py       # 根据配置创建 notifier 实例
```

#### 配置

```yaml
notifier:
  enable: true
  on_success: true       # 构建成功是否通知
  on_failure: true       # 构建失败是否通知
  channels:
    - type: telegram
      bot_token: ${TELEGRAM_BOT_TOKEN}
      chat_id: "-100xxxxxxxxxx"
    - type: discord
      webhook_url: ${DISCORD_WEBHOOK_URL}
    - type: wecom
      webhook_key: ${WECOM_KEY}
```

#### 消息模板

```
✅ adfilter 构建成功
━━━━━━━━━━━━━━━━
📅 2026-05-13 16:00 CST
📊 规则总数: 100,309
📂 输出文件: 10
⏱️ 耗时: 2.9s
🔗 订阅: https://raw.githubusercontent.com/.../release/dns.txt
```

#### 疑难点

1. **Secret 管理**：Token 不能硬编码，支持环境变量占位符 `${VAR}` 和 `.env` 文件。
2. **速率限制**：Telegram Bot API 有每秒 30 条限制，Discord 每分钟 30 条。需要重试 + backoff。
3. **CI 集成**：GitHub Actions 中作为构建后步骤执行，失败不应阻塞主流程。

---

### 3. 自定义白名单

#### 实现方案

```yaml
# config/application.yaml
input:
  allowlist:
    - path: config/allowlist.txt       # 本地白名单
    - path: https://example.com/my-allow.txt  # 远程白名单
```

```python
# optimizer.py 增强
def apply_allowlist(rules: set[Rule], allowlist: set[str]) -> set[Rule]:
    """移除被白名单覆盖的规则"""
    return {r for r in rules if r.domain not in allowlist
            and not any(r.domain.endswith('.' + a) for a in allowlist)}
```

#### 疑难点

1. **白名单粒度**：需要支持精确匹配（`ads.example.com`）和通配符匹配（`*.example.com`）。
2. **白名单 vs Allow 规则**：EasyList 格式的 `@@` 规则是格式内的概念，白名单是全局过滤，两者处理时机不同。白名单在 optimizer 阶段最后应用。
3. **性能**：白名单通常较小（< 1000 条），直接集合查找即可，无需额外优化。

---

### 4. 分类输出

#### 实现方案

```yaml
input:
  rule:
    groups:
      - name: anti-ad
        sources:
          - { name: anti-ad, type: easylist, path: https://anti-ad.net/easylist.txt }
      - name: privacy
        sources:
          - { name: easyprivacy, type: easylist, path: https://easylist.to/... }
      - name: malware
        sources:
          - { name: urlhaus, type: hosts, path: https://urlhaus.abuse.ch/... }

output:
  files:
    # 全量合并输出
    - { name: dns.txt, type: dns, groups: [anti-ad, privacy, malware] }
    # 分组独立输出
    - { name: anti-ad.dns.txt, type: dns, groups: [anti-ad] }
    - { name: privacy.dns.txt, type: dns, groups: [privacy] }
```

#### 数据流

```
源A ─┐                ┌─ 全量 dns.txt (A∪B∪C)
源B ─┼─▶ 解析+分组 ──┼─ anti-ad.dns.txt (A)
源C ─┘                ├─ privacy.dns.txt (B)
                      └─ malware.dns.txt (C)
```

#### 疑难点

1. **交叉去重**：同一规则出现在多个组中，全量输出只保留一份，但分组输出各自独立包含。
2. **优化器作用域**：子域折叠、多源投票等优化是在全量上做还是每个组独立做？建议：全量优化后再按组拆分。
3. **构建报告**：报告需要按组统计规则来源、数量。

---

### 5. 规则热更新

#### 实现方案

```python
# serve 命令增强
@app.command()
def serve(
    dir: Path,
    port: int = 8080,
    auto_refresh: bool = False,
    refresh_interval: int = 480,  # 分钟，默认 8 小时
):
    if auto_refresh:
        scheduler = BackgroundScheduler()
        scheduler.add_job(rebuild, 'interval', minutes=refresh_interval)
        scheduler.start()
    uvicorn.run(file_server, host="0.0.0.0", port=port)
```

#### 疑难点

1. **原子写入**：重建过程中，正在被下载的文件不能是写到一半的状态。使用"写临时目录 → 原子 rename"策略。
2. **内存占用**：长期运行的 serve 进程需要注意内存泄漏（特别是 aiohttp session 复用）。
3. **信号处理**：支持 `SIGHUP` 触发立即重建，`SIGTERM` 优雅停止。

---


## v0.4.0 — 生态扩展

**目标时间**：v0.3.0 后 8-12 周
**核心目标**：从"工具"进化为"平台"，支持第三方扩展和更广泛的用户群。

### 1. 更多输入格式

#### 新增支持

| 格式 | 说明 | 解析难度 |
|------|------|----------|
| uBlock Origin 语法 | `$domain=`、`$badfilter`、script injection | ⭐⭐⭐ |
| ABP snippet filters | `#$#abort-on-property-read` | ⭐⭐（仅需识别并跳过） |
| Quantumult X | `host, domain, reject` | ⭐⭐ |
| Surge ruleset | `DOMAIN,xxx` / `DOMAIN-SUFFIX,xxx` | ⭐ |
| Pi-hole regex | `/regex/` 格式 | ⭐⭐ |

#### 实现方案

```python
# parser.py 扩展识别逻辑
class InputFormat(StrEnum):
    EASYLIST = "easylist"
    HOSTS = "hosts"
    DOMAIN_LIST = "domain_list"
    UBLOCK = "ublock"          # 新增
    QUANTUMULT_X = "quantumult_x"  # 新增
    SURGE_RULESET = "surge_ruleset"  # 新增

def detect_format(content: str) -> InputFormat:
    """自动检测输入格式"""
    if content.startswith("[Adblock Plus"):
        return InputFormat.EASYLIST
    if "host," in content.lower() and "reject" in content.lower():
        return InputFormat.QUANTUMULT_X
    ...
```

#### 疑难点

1. **uBlock 语法复杂度**：uBlock 扩展了大量 ABP 不支持的语法（`$badfilter`、`$removeparam`、cosmetic filters），需要明确哪些"解析但忽略"、哪些"提取域名"。
2. **格式自动检测**：多种格式可能有相似行（如纯域名列表），需要多信号综合判断（文件头注释、行格式统计）。

---

### 2. 更多输出格式

#### 新增支持

| 格式 | 目标用户 | 实现复杂度 |
|------|---------|-----------|
| pfBlockerNG (pfSense) | 防火墙用户 | ⭐（纯域名列表） |
| Pi-hole regex | Pi-hole 用户 | ⭐⭐（需生成正则） |
| AdGuard DNS rewrites | AdGuard Home 高级用户 | ⭐ |
| Quantumult X filter | iOS 用户 | ⭐⭐ |
| Shadowrocket module | iOS 用户 | ⭐⭐ |
| Loon plugin | iOS 用户 | ⭐⭐ |

#### Handler 模板

```python
# handler/quantumult_handler.py
class QuantumultHandler(BaseHandler):
    format_name = "quantumult_x"
    file_extension = ".conf"

    def format_rule(self, rule: Rule) -> str | None:
        if rule.type == RuleType.BASIC:
            return f"host, {rule.domain}, reject"
        elif rule.type == RuleType.WILDCARD:
            return f"host-suffix, {rule.domain}, reject"
        return None

    def wrap_output(self, lines: list[str]) -> str:
        header = "[filter_remote]\n"
        return header + "\n".join(lines)
```

---

### 3. 插件化 Handler 系统

#### 实现方案

使用 Python `entry_points` 机制：

```toml
# 第三方包的 pyproject.toml
[project.entry-points."adfilter.handlers"]
my_custom_format = "my_package.handler:MyCustomHandler"
```

```python
# handler/factory.py
from importlib.metadata import entry_points

def discover_handlers() -> dict[str, type[BaseHandler]]:
    """发现所有已注册的 handler（内置 + 第三方插件）"""
    handlers = {h.format_name: h for h in BUILTIN_HANDLERS}

    # 加载第三方插件
    eps = entry_points(group="adfilter.handlers")
    for ep in eps:
        handler_cls = ep.load()
        handlers[handler_cls.format_name] = handler_cls

    return handlers
```

#### 插件开发者接口

```python
from adfilter.handler.base import BaseHandler, Rule, RuleType

class MyHandler(BaseHandler):
    format_name = "my_format"       # 必须唯一
    file_extension = ".myext"

    def format_rule(self, rule: Rule) -> str | None:
        """将单条规则转为目标格式的字符串，返回 None 表示跳过"""
        ...

    def wrap_output(self, lines: list[str]) -> str:
        """可选：为输出添加头尾包装"""
        return "\n".join(lines)
```

#### 疑难点

1. **版本兼容性**：`BaseHandler` 接口变更会破坏第三方插件，需要从 v0.4.0 起对接口做 SemVer 承诺。
2. **安全性**：加载第三方代码有风险，需要在文档中声明"仅安装可信插件"。
3. **配置集成**：第三方 handler 的配置项如何注入 `application.yaml`？方案：handler 类声明自己的 Pydantic config model，由框架动态合并。

---

### 4. 规则来源市场

#### 实现方案

内置一个规则源目录（JSON/YAML），用户通过 CLI 管理：

```bash
# 列出可用源
adfilter sources list

# 按地区筛选
adfilter sources list --region cn

# 添加源到配置
adfilter sources add anti-ad easylist-china

# 移除源
adfilter sources remove easylist-china
```

#### 源目录结构

```yaml
# src/adfilter/data/source_catalog.yaml
sources:
  - id: anti-ad
    name: "anti-AD"
    url: https://anti-ad.net/easylist.txt
    format: easylist
    region: cn
    category: ads
    description: "国内最流行的广告过滤列表"
    maintainer: "privacy-protection-tools"
    update_frequency: "daily"

  - id: easylist
    name: "EasyList"
    url: https://easylist.to/easylist/easylist.txt
    format: easylist
    region: global
    category: ads
    description: "ABP 官方广告过滤列表"
    ...
```

#### 疑难点

1. **目录更新**：内置目录会过时，需要支持从远程拉取最新目录（`adfilter sources update`）。
2. **源可用性**：目录中的源可能失效，需要定期检查（可集成到 `doctor` 命令）。
3. **冲突检测**：添加新源后，可能与已有源规则大量重复，应提示用户。

---

### 5. 多语言/地区预设

#### 实现方案

```bash
# 快速初始化中国地区配置
adfilter init --preset cn

# 快速初始化日本地区配置
adfilter init --preset jp
```

生成的配置预装该地区常用的规则源：

```yaml
# presets/cn.yaml
application:
  config:
    input:
      rule:
        default:
          - { name: anti-ad, type: easylist, path: "https://anti-ad.net/easylist.txt" }
          - { name: easylist-china, type: easylist, path: "https://easylist-downloads.adblockplus.org/easylistchina.txt" }
          - { name: cjx-annoyance, type: easylist, path: "https://raw.githubusercontent.com/cjx82630/cjxlist/master/cjx-annoyance.txt" }
```

---


## v1.0.0 — 生产就绪

**目标时间**：v0.4.0 后 8-12 周
**核心目标**：达到生产级品质，支持大规模部署和社区贡献。

### 1. 语义版本 & Changelog

#### 实现方案

- 使用 [git-cliff](https://github.com/orhun/git-cliff) 自动从 Conventional Commits 生成 CHANGELOG
- CI 中在 tag 创建时自动生成 GitHub Release + changelog

```toml
# cliff.toml
[changelog]
header = "# Changelog\n"
body = """
{% for group, commits in commits | group_by(attribute="group") %}
### {{ group | upper_first }}
{% for commit in commits %}
- {{ commit.message | upper_first }} ({{ commit.id | truncate(length=7) }})
{% endfor %}
{% endfor %}
"""
```

#### Commit 规范

```
feat: 新功能
fix: Bug 修复
perf: 性能优化
docs: 文档
refactor: 重构
test: 测试
chore: 构建/CI
BREAKING CHANGE: 不兼容变更（footer）
```

---

### 2. PyPI 发布

#### 实现方案

```yaml
# .github/workflows/release.yml
name: Release to PyPI
on:
  push:
    tags: ["v*"]

jobs:
  publish:
    runs-on: ubuntu-latest
    permissions:
      id-token: write  # Trusted Publisher
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv build
      - uses: pypa/gh-action-pypi-publish@release/v1
```

#### 疑难点

1. **版本同步**：`pyproject.toml` 中的 version 需要与 git tag 一致。使用 `hatch-vcs` 或手动 bump。
2. **依赖声明**：区分核心依赖（CLI）和可选依赖（web、通知）：
   ```toml
   [project.optional-dependencies]
   web = ["litestar", "jinja2", "uvicorn"]
   notify = ["httpx"]
   all = ["adfilter[web,notify]"]
   ```
3. **Python 3.14 限制**：PyPI 上依赖库可能尚未全部支持 3.14，需要验证 wheel 可用性。

---

### 3. Helm Chart / Docker Compose

#### Docker Compose

```yaml
# docker-compose.yml
services:
  adfilter:
    image: ghcr.io/lknife666/adfilter:latest
    volumes:
      - ./config:/app/config:ro
      - ./rule:/app/rule
      - ./cache:/app/.cache
    environment:
      - TZ=Asia/Shanghai
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
    ports:
      - "8080:8080"
    command: ["serve", "--dir", "rule/", "--auto-refresh", "--port", "8080"]
    healthcheck:
      test: ["CMD", "adfilter", "doctor", "--quiet"]
      interval: 60s
      timeout: 10s
    restart: unless-stopped
```

#### Helm Chart 结构

```
charts/adfilter/
├── Chart.yaml
├── values.yaml
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── configmap.yaml      # 挂载 application.yaml
│   ├── cronjob.yaml        # 定时构建（替代 serve --auto-refresh）
│   └── ingress.yaml        # 可选：暴露订阅端点
```

#### 疑难点

1. **持久化存储**：缓存和输出文件需要 PVC，CronJob 和 Serve Pod 共享同一 volume。
2. **配置热更新**：ConfigMap 变更后 Pod 需要重启，考虑用 `reloader` 或 `sha256` annotation。
3. **资源限制**：默认 128Mi memory + 100m CPU，大规则集构建时可能需要 512Mi。

---

### 4. 性能基准

#### 实现方案

```python
# benchmarks/bench_pipeline.py
"""用 pytest-benchmark 或 pyperf 做基准测试"""

def bench_parse_100k_rules(benchmark):
    content = load_fixture("100k_easylist.txt")
    benchmark(parse_rules, content)

def bench_optimize_100k_rules(benchmark):
    rules = generate_rules(100_000)
    benchmark(optimize, rules)

def bench_full_pipeline_100k(benchmark):
    benchmark(run_pipeline, config="bench_config.yaml")
```

#### 基准指标

| 场景 | 目标 |
|------|------|
| 解析 100k 规则 | < 500ms |
| 优化 100k 规则（含子域折叠） | < 1s |
| 完整 pipeline（10 输出格式） | < 5s |
| 内存峰值（100k 规则） | < 256MB |
| 增量构建（无变化） | < 100ms |
| 1M 规则完整 pipeline | < 30s |

#### 疑难点

1. **CI 中的性能噪声**：GitHub Actions runner 性能波动大，基准测试结果不稳定。方案：只在本地跑，CI 中只做"不超过上限"的断言。
2. **内存分析**：使用 `memray` 或 `tracemalloc` 定位内存热点，特别是 Rule 对象的存储效率。
3. **优化方向**：如果 100k+ 瓶颈在子域折叠，考虑用 Trie 结构替代暴力遍历。

---

### 5. 安全审计

#### 实现方案

```yaml
# .github/workflows/security.yml
name: Security
on:
  push:
    branches: [main]
  schedule:
    - cron: "0 6 * * 1"  # 每周一

jobs:
  deps:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pypa/gh-action-pip-audit@v1
        with:
          inputs: requirements.txt

  sast:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: PyCQA/bandit-action@v1
        with:
          targets: src/
```

#### 安全关注点

| 风险 | 缓解措施 |
|------|---------|
| 依赖漏洞 | Dependabot + pip-audit 周扫描 |
| 输入注入 | 规则解析时严格校验，拒绝包含 shell 特殊字符的域名 |
| SSRF | fetcher 限制只允许 HTTP/HTTPS 协议，禁止 `file://`、`ftp://` |
| 路径遍历 | 输出路径只允许在配置的 output.path 下，禁止 `..` |
| Secret 泄露 | 不在日志/报告中打印 token、webhook URL |

---

### 6. 国际化 (i18n)

#### 实现方案

```python
# src/adfilter/i18n.py
import gettext
from pathlib import Path

LOCALE_DIR = Path(__file__).parent / "locales"
_translation = gettext.translation("adfilter", LOCALE_DIR, fallback=True)
_ = _translation.gettext

# 使用示例
logger.info(_("开始构建规则列表..."))
console.print(_("✅ 构建完成，共 {count} 条规则").format(count=total))
```

#### 目录结构

```
src/adfilter/locales/
├── zh_CN/LC_MESSAGES/adfilter.po
├── en_US/LC_MESSAGES/adfilter.po
└── ja_JP/LC_MESSAGES/adfilter.po
```

#### 疑难点

1. **Rich 格式化字符串**：Rich markup（`[bold]`）和 gettext 占位符混用时需注意转义。
2. **CLI 错误消息**：Typer 框架本身的帮助文本也需要翻译，复杂度较高。
3. **优先级**：i18n 是"锦上添花"，建议只翻译用户可见的输出（日志、CLI 输出），内部代码注释保持英文。

---


## 持续迭代方向（横向）

以下方向不绑定特定版本，根据需求和社区反馈随时推进。

### 1. DNS Probe 增强

#### 当前状态

现有 `dns_probe` 可选检测域名存活性，但是串行且无缓存。

#### 增强方案

```python
# dns_prober.py 重构
class EnhancedDNSProber:
    def __init__(self, config: DNSProbeConfig):
        self.semaphore = asyncio.Semaphore(config.concurrency)  # 并行度
        self.cache = DiskCache(config.cache_dir, ttl=config.cache_ttl_hours)
        self.dead_domains: set[str] = set()

    async def probe_batch(self, domains: list[str]) -> dict[str, bool]:
        tasks = [self._probe_one(d) for d in domains]
        results = await asyncio.gather(*tasks)
        return dict(zip(domains, results))

    async def _probe_one(self, domain: str) -> bool:
        # 缓存命中
        cached = self.cache.get(domain)
        if cached is not None:
            return cached

        async with self.semaphore:
            alive = await self._resolve(domain)
            self.cache.set(domain, alive)
            if not alive:
                self.dead_domains.add(domain)
            return alive
```

#### 配置

```yaml
dns_probe:
  enable: true
  concurrency: 50            # 并行探测数
  timeout_ms: 3000           # 单次超时
  cache_dir: .cache/dns      # 探测结果缓存
  cache_ttl_hours: 168       # 7 天缓存
  auto_remove_dead: true     # 自动移除死域名
  nameservers:               # 自定义 DNS 服务器
    - 8.8.8.8
    - 1.1.1.1
```

#### 疑难点

1. **大量域名探测耗时**：10 万域名即使 50 并发也需要 ~10 分钟。建议仅对新增规则做探测，已缓存的跳过。
2. **误判**：某些域名 DNS 暂时不可达但实际存在，需要"连续 N 次探测失败才标记为死域名"的策略。
3. **CI 环境限制**：GitHub Actions 可能限制出站 DNS 查询频率。

---

### 2. 规则去重策略可配置

#### 方案

```yaml
optimizer:
  dedup_strategy: domain_first  # 可选: domain_first | full_rule | source_priority

  # source_priority 模式下的源优先级
  source_priority:
    - anti-ad        # 最高优先
    - easylist
    - easylist-china # 最低优先
```

| 策略 | 说明 |
|------|------|
| `domain_first` | 同域名只保留第一个遇到的规则（默认） |
| `full_rule` | 按完整规则文本去重（允许同域名不同修饰符共存） |
| `source_priority` | 同域名冲突时，按源优先级决定保留哪条 |

---

### 3. 可视化 Diff 报告

#### 方案

`adfilter diff` 增加 `--html` 输出：

```bash
adfilter diff old_dns.txt new_dns.txt --format dns --html diff_report.html
```

生成的 HTML 包含：
- 新增规则列表（绿色）
- 删除规则列表（红色）
- 统计摘要（新增 N 条、删除 M 条、净变化）
- 按域名层级分组展示

#### 技术选型

使用 Jinja2 模板 + 内嵌 CSS，生成单文件 HTML（无外部依赖），可直接浏览器打开或作为 CI artifact。

---

### 4. GitHub Pages 订阅页面

#### 方案

在 `release` 分支额外生成一个 `index.html`：

```html
<!-- 自动生成的订阅引导页 -->
<h1>adfilter 规则订阅</h1>
<p>最后更新：2026-05-13 16:00 CST</p>

<table>
  <tr><td>AdGuard Home</td><td><input value="https://...dns.txt" readonly><button>复制</button></td></tr>
  <tr><td>Clash</td><td><input value="https://...clash.yaml" readonly><button>复制</button></td></tr>
  ...
</table>
```

配合 GitHub Pages 配置（Settings → Pages → Source: release branch），即可自动部署。

#### 疑难点

1. **自定义域名**：如果用户想用自己的域名，需要在 release 分支添加 `CNAME` 文件。
2. **CORS**：某些客户端订阅时需要 CORS 头，GitHub raw 不支持，Pages 也不支持自定义头。可能需要 Cloudflare Workers 中转。

---

## 优先级排序建议

根据用户价值和实现复杂度，建议优先级：

```
高优先级（立即启动）：
├── 测试覆盖 ← 一切迭代的基础
├── CI 完善 ← 保障质量
└── Dockerfile 优化 ← 已有 Docker 发布，优化成本低

中优先级（v0.2 完成后）：
├── 错误降级策略 ← 生产环境必需
├── 自定义白名单 ← 用户呼声最高
├── 分类输出 ← 差异化竞争力
└── Webhook 通知 ← 运维友好

低优先级（按需启动）：
├── Web Dashboard ← 投入大，非核心
├── 插件化系统 ← 需要社区规模支撑
├── 国际化 ← 当前用户群以中文为主
└── Helm Chart ← 用户规模达到一定量级再做
```

---

## 里程碑时间线

```
2026 Q2        Q3              Q4              2027 Q1
  │             │               │               │
  ▼             ▼               ▼               ▼
v0.2.0        v0.3.0          v0.4.0          v1.0.0
测试+CI        订阅体验        生态扩展        生产就绪
4-6 周         6-8 周          8-12 周         8-12 周
```

---

> **贡献**：欢迎通过 Issue 讨论优先级或提出新的方向建议。
>
> **许可**：本文档随项目采用 MIT 许可。
