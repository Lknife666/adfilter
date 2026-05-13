# adfilter Roadmap — "规则中心" 战略

> **定位**：不做 DNS 服务器，做所有 DNS 过滤工具的 **最佳规则供应商**。
>
> adfilter 的核心价值不是拦截 DNS 请求（Pi-hole/AdGuard Home 已经做得很好），而是 **聚合、优化、分发** 高质量广告过滤规则，服务于整个 DNS 过滤生态。
>
> 当前版本：**v0.1.0** | 最后更新：2025-05-13

---

## 目录

- [战略定位](#战略定位)
- [与竞品的关系](#与竞品的关系)
- [版本总览](#版本总览)
- [Phase 1 — 基础加固 (v0.2)](#phase-1--基础加固-v02)
- [Phase 2 — 规则质量引擎 (v0.3)](#phase-2--规则质量引擎-v03)
- [Phase 3 — 订阅服务化 (v0.4)](#phase-3--订阅服务化-v04)
- [Phase 4 — 规则平台 (v0.5)](#phase-4--规则平台-v05)
- [Phase 5 — 生产就绪 (v1.0)](#phase-5--生产就绪-v10)
- [技术难点总览](#技术难点总览)
- [持续迭代方向](#持续迭代方向)
- [里程碑时间线](#里程碑时间线)

---

## 战略定位

### 我们是什么

```
用户的网络设备 ──→ Pi-hole / AdGuard Home / Clash / Surge / 路由器
                              ↑
                    订阅 adfilter 生成的规则
                              ↑
              ┌───────────────────────────────────┐
              │           adfilter                 │
              │  聚合 → 去噪 → 优化 → 质检 → 分发  │
              └───────────────────────────────────┘
                              ↑
              EasyList / anti-AD / URLhaus / 社区规则 / ...
```

### 核心竞争力

| 维度 | Pi-hole / AdGuard Home | adfilter |
|------|----------------------|----------|
| 核心能力 | DNS 拦截 | 规则聚合优化 |
| 输出格式 | 1-2 种 | **12 种**（覆盖所有主流工具） |
| 规则优化 | 无/简单去重 | 子域折叠、多源投票、死域名检测、误杀分析 |
| 目标用户 | 终端用户 | 终端用户 + **其他过滤工具** |
| 部署要求 | 需长期运行的服务 | 无状态、可 CI/CD、可 Serverless |
| 扩展性 | 有限 | 插件化 Handler + 第三方生态 |

### 为什么不做 DNS 服务器

1. **性能天花板**：Python DNS Server 每秒处理 ~5000 查询，Go (AdGuard Home) 可达 10万+，差距 20x
2. **红海竞争**：Pi-hole 有 10 年积累和 5 万+ GitHub stars，AdGuard Home 用 Go 原生高性能
3. **差异化不足**：做 DNS 服务器意味着正面竞争，而非差异化
4. **协同 > 竞争**：做规则中心可以 **服务于** 所有 DNS 过滤工具，市场更大

---

## 与竞品的关系

```
┌─────────────────────────────────────────────────────────────────────┐
│                        广告过滤生态                                    │
│                                                                     │
│  ┌──────────┐     ┌──────────────┐     ┌────────────────────────┐  │
│  │ 规则来源  │────▶│  adfilter    │────▶│  DNS 过滤工具           │  │
│  │          │     │  (规则中心)   │     │                        │  │
│  │ EasyList │     │              │     │  Pi-hole               │  │
│  │ anti-AD  │     │  聚合+优化    │     │  AdGuard Home          │  │
│  │ URLhaus  │     │  质检+分发    │     │  Clash / Surge         │  │
│  │ 社区列表  │     │  12种格式    │     │  sing-box / Loon       │  │
│  │ ...      │     │              │     │  dnsmasq / SmartDNS    │  │
│  └──────────┘     └──────────────┘     │  MikroTik / Unbound   │  │
│                                         └────────────────────────┘  │
│                                                                     │
│  adfilter 不替代任何工具，而是让每个工具都用上最好的规则              │
└─────────────────────────────────────────────────────────────────────┘
```

| 工具 | 与 adfilter 的关系 |
|------|-------------------|
| Pi-hole | 用户订阅 adfilter 的 `hosts.txt` 作为 Adlist |
| AdGuard Home | 用户订阅 adfilter 的 `dns.txt` 作为 DNS 封锁清单 |
| Clash / Clash Meta | 用户在 `rule-providers` 中引用 adfilter 的 `clash.yaml` |
| Surge / Shadowrocket | 用户订阅 adfilter 的 `surge.conf` 作为外部规则集 |
| uBlock Origin | 用户添加 adfilter 的 `easylist.txt` 作为自定义过滤列表 |
| OpenWrt (dnsmasq) | 用户下载 adfilter 的 `dnsmasq.conf` 部署到路由器 |

---

## 版本总览

```
v0.1.0 (当前)     v0.2.0           v0.3.0            v0.4.0           v0.5.0          v1.0.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  12格式输出        基础加固          规则质量引擎       订阅服务化         规则平台         生产就绪
  异步管线          测试+CI           死域名检测         Web Dashboard     个性化订阅       PyPI+Helm
  增量构建          错误降级          误杀分析           CDN 分发          社区贡献         性能基线
  插件系统          Docker优化        规则冲突报告       API 服务          规则市场         安全审计
                                     规则评分                            多租户
```

---


## Phase 1 — 基础加固 (v0.2)

**目标时间**：4-6 周
**核心目标**：建立质量保障体系，为后续快速迭代打下坚实基础。

### 1.1 测试覆盖率 ≥ 80%

#### 实现方案

```
tests/
├── conftest.py                  # 公共 fixtures（mock config、临时目录）
├── unit/
│   ├── test_parser.py           # 每种输入格式解析
│   ├── test_optimizer.py        # 子域折叠、Allow阴影、投票、IDN
│   ├── test_model.py            # Rule 边界条件、murmur3 hash 一致性
│   ├── test_config.py           # 配置加载、校验、环境变量覆盖
│   └── handler/
│       ├── test_easylist.py     # 12 个 handler 各一个测试文件
│       ├── test_dns.py
│       └── ...
├── integration/
│   ├── test_full_pipeline.py    # 端到端：输入 → 解析 → 优化 → 输出
│   ├── test_incremental.py      # 增量构建完整流程
│   └── test_cli.py              # 每个 CLI 子命令
└── fixtures/
    ├── sample_easylist.txt
    ├── sample_hosts.txt
    └── expected_output/         # 快照对比基准
```

#### 技术选型

| 组件 | 选择 | 理由 |
|------|------|------|
| 测试框架 | `pytest` + `pytest-asyncio` | 标准选择，async 支持好 |
| HTTP Mock | `aioresponses` | mock `aiohttp` 请求，消除网络依赖 |
| 快照测试 | `syrupy` | 防止输出格式意外漂移 |
| 覆盖率 | `pytest-cov` → Codecov | CI 可视化覆盖率变化 |

#### 疑难点与解决方案

| 难点 | 描述 | 解决方案 |
|------|------|---------|
| 异步测试 | parser/fetcher 使用 `asyncio` | `pytest-asyncio` 配置 `mode=auto`，所有 async test 函数自动识别 |
| sing-box JSON 验证 | 输出是嵌套结构 | 用 JSON Schema 文件做结构验证，而非字符串匹配 |
| IDN 边界 case | 混合编码、无效 punycode | 准备专门的 IDN 测试数据集，覆盖 10+ 边界情况 |
| 跨平台路径 | Windows vs Linux 路径分隔符 | 使用 `pathlib.Path` + `tmp_path` fixture |

---

### 1.2 CI/CD 完善

#### 实现方案

```yaml
# .github/workflows/ci.yml（已有，增强）
jobs:
  test:
    strategy:
      matrix:
        python-version: ["3.14"]
        os: [ubuntu-latest]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv python install ${{ matrix.python-version }}
      - run: uv sync --group dev
      - run: uv run pytest --cov=adfilter --cov-report=xml -q
      - uses: codecov/codecov-action@v4

  lint:
    steps:
      - run: uvx ruff check src/ tests/
      - run: uvx ruff format --check src/ tests/

  type-check:
    steps:
      - run: uv run mypy src/adfilter --strict
```

#### 新增工作流

| 工作流 | 触发条件 | 职责 |
|--------|---------|------|
| `ci.yml` | PR + push main | 测试 + lint + type-check |
| `security.yml` | push + 每周 | pip-audit + Bandit SAST |
| `auto-update.yml` | 每 8h | 构建规则 → release 分支 |
| `release.yml` | tag `v*` | PyPI + GitHub Release + Docker |

#### 疑难点

- **Python 3.14 Runner**：`setup-python` 可能未支持，依赖 `astral-sh/setup-uv` 的 `uv python install`
- **Codecov**：公开仓库可 tokenless 上传，建议配置 `CODECOV_TOKEN` 更稳定

---

### 1.3 错误处理与降级策略

#### 实现方案

```python
# 三级降级策略
class FailureStrategy(StrEnum):
    FAIL_FAST = "fail_fast"              # 任一源失败则整体失败
    CACHE_THEN_SKIP = "cache_then_skip"  # 失败 → 用缓存 → 跳过
    SKIP_ALWAYS = "skip_always"          # 失败直接跳过

# 规则数骤降告警
class BuildGuard:
    """检测构建结果是否异常"""
    def check(self, current_count: int, last_count: int) -> Alert | None:
        drop_ratio = 1 - (current_count / max(last_count, 1))
        if drop_ratio > 0.3:  # 规则数下降超过 30%
            return Alert(
                level="warning",
                message=f"规则数异常下降 {drop_ratio:.0%}: {last_count} → {current_count}",
                suggestion="可能多个规则源不可达，请检查网络或源状态"
            )
        return None
```

#### 配置

```yaml
fetcher:
  http:
    on_failure: cache_then_skip
    max_cache_age_hours: 72
    max_retries: 3
    retry_backoff_factor: 2

# 构建安全阈值
build_guard:
  enable: true
  max_drop_ratio: 0.3       # 规则数下降超过 30% 告警
  min_total_rules: 10000    # 总规则数低于此值告警
```

#### 疑难点

| 难点 | 解决方案 |
|------|---------|
| 缓存一致性 | 在 build-report 中标记哪些源使用了缓存版本 + 缓存时间 |
| 部分失败 | BuildGuard 检测规则数骤降，触发通知但不阻塞输出 |
| 缓存过期策略 | 默认 72h，超过后标记为 stale 但仍可用，报告中提示 |

---

### 1.4 Docker 镜像优化

#### 当前问题

- 镜像体积可能偏大（包含构建工具链）
- 未充分利用多阶段构建

#### 优化方案

```dockerfile
# ── 构建阶段 ──
FROM python:3.14-slim AS builder
WORKDIR /build
RUN pip install uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-editable
COPY src/ src/

# ── 运行阶段 ──
FROM python:3.14-slim AS runtime
RUN groupadd -r adfilter && useradd -r -g adfilter adfilter
WORKDIR /app
COPY --from=builder /build/.venv /app/.venv
COPY --from=builder /build/src /app/src
ENV PATH="/app/.venv/bin:$PATH"
USER adfilter
HEALTHCHECK --interval=60s --timeout=10s \
  CMD ["adfilter", "doctor", "--quiet"]
ENTRYPOINT ["adfilter"]
CMD ["run", "--config", "/app/config/application.yaml", "--progress"]
```

| 优化点 | 预期效果 |
|--------|---------|
| 多阶段构建 | 镜像体积减少 ~60% |
| 非 root 用户 | 安全加固，符合 K8s PSP |
| Layer 缓存 | 依赖层单独缓存，代码变更不重装依赖 |
| .dockerignore | 排除 .git/tests/rule/，加速上下文传输 |

---

### 1.5 文档体系建设

#### 方案

```
docs/
├── architecture.md        # 模块关系 + 数据流（已有，增强）
├── configuration.md       # 每个配置字段详细说明（已有，增强）
├── formats.md             # 12 种格式的规范 + 兼容性矩阵（已有，增强）
├── contributing.md        # PR 流程 + 代码风格（已有，增强）
├── plugin-development.md  # 第三方 Handler/Notifier 开发指南（新增）
└── deployment.md          # Docker/K8s/CI 部署最佳实践（新增）
```

#### 技术选型

- 使用 `mkdocs-material` 生成文档站点
- 部署到 GitHub Pages（`gh-pages` 分支）
- 配置文档从 Pydantic model 的 `Field(description=...)` 半自动提取

---


## Phase 2 — 规则质量引擎 (v0.3)

**目标时间**：v0.2 后 6-8 周
**核心目标**：从"规则搬运工"进化为"规则质量守门人"——这是对标 Pi-hole/AdGuard Home 时最大的差异化。

> Pi-hole 和 AdGuard Home 只负责"你给我什么规则我就拦什么"，它们从不检查规则本身的质量。
> adfilter 的价值在于：**让每一条送到用户设备的规则都是有效的、必要的、安全的。**

### 2.1 死域名检测与自动清理

#### 问题背景

社区维护的规则列表中，大量域名已经停止解析（过期、注销、被接管），这些"死规则"：
- 增加规则文件体积，拖慢加载
- 浪费 DNS 过滤工具的内存
- 可能产生误报（域名被重新注册为合法站点）

#### 实现方案

```python
# src/adfilter/quality/dead_domain_detector.py
class DeadDomainDetector:
    """异步批量检测域名存活状态"""

    def __init__(self, config: DeadDomainConfig):
        self.resolver = aiodns.DNSResolver(nameservers=config.nameservers)
        self.semaphore = asyncio.Semaphore(config.concurrency)
        self.cache = DiskCache(config.cache_dir, ttl_hours=config.cache_ttl_hours)
        self.consecutive_failures: dict[str, int] = {}

    async def detect_batch(self, domains: list[str]) -> DeadDomainReport:
        """批量检测，返回死域名报告"""
        tasks = [self._check_one(d) for d in domains]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        dead = []
        for domain, result in zip(domains, results):
            if result is False:
                self.consecutive_failures[domain] = \
                    self.consecutive_failures.get(domain, 0) + 1
                # 连续 N 次失败才标记为死域名（避免临时 DNS 故障误判）
                if self.consecutive_failures[domain] >= config.min_consecutive_failures:
                    dead.append(domain)
            else:
                self.consecutive_failures.pop(domain, None)

        return DeadDomainReport(
            total_checked=len(domains),
            dead_count=len(dead),
            dead_domains=dead
        )

    async def _check_one(self, domain: str) -> bool:
        """检测单个域名是否存活（有任何 DNS 记录即为存活）"""
        cached = self.cache.get(domain)
        if cached is not None:
            return cached

        async with self.semaphore:
            for qtype in ("A", "AAAA", "CNAME"):
                try:
                    await asyncio.wait_for(
                        self.resolver.query(domain, qtype),
                        timeout=self.config.timeout_seconds
                    )
                    self.cache.set(domain, True)
                    return True
                except (aiodns.error.DNSError, asyncio.TimeoutError):
                    continue

            self.cache.set(domain, False)
            return False
```

#### 配置

```yaml
quality:
  dead_domain:
    enable: true
    concurrency: 100              # 并行探测数
    timeout_seconds: 3.0          # 单次 DNS 查询超时
    cache_dir: .cache/dns_probe   # 探测结果磁盘缓存
    cache_ttl_hours: 168          # 缓存 7 天
    min_consecutive_failures: 3   # 连续 3 次探测失败才标记
    auto_remove: false            # 是否自动移除死域名（建议先观察）
    report_path: rule/dead-domains.json  # 死域名报告
    nameservers:
      - 8.8.8.8
      - 1.1.1.1
      - 223.5.5.5               # 阿里 DNS（国内快）
```

#### 输出报告示例

```json
{
  "scan_date": "2026-07-01T08:00:00Z",
  "total_rules": 98000,
  "total_checked": 85000,
  "dead_domains": 3200,
  "dead_ratio": "3.76%",
  "top_dead_sources": [
    {"source": "old-community-list", "dead_count": 1200, "dead_ratio": "15%"},
    {"source": "easylist-china", "dead_count": 800, "dead_ratio": "4%"}
  ],
  "samples": [
    {"domain": "defunct-ad-server.com", "last_alive": "2025-12-01", "failures": 5}
  ]
}
```

#### 疑难点与解决方案

| 难点 | 描述 | 解决方案 |
|------|------|---------|
| 大规模探测耗时 | 10 万域名探测需时间 | 增量探测：只检测新增/上次失败的域名；结果缓存 7 天 |
| 误判风险 | 域名 DNS 暂时不可达 ≠ 死亡 | 要求连续 3 次（跨 3 个构建周期）失败才标记 |
| DNS 速率限制 | 部分 DNS 服务器限流 | 多 nameserver 轮询 + 指数退避 |
| CI 环境限制 | GitHub Actions 出站 DNS 可能受限 | CI 中禁用探测，仅本地/自建环境运行 |
| Wildcard DNS | `*.sinkhole.example.com` 返回 A 记录但实际是沉洞 | 检测 sinkhole 特征 IP（如 0.0.0.0、127.0.0.1） |

---

### 2.2 误杀分析引擎

#### 问题背景

广告过滤最大的痛点是"误杀"——正常网站被错误拦截。目前用户只能手动发现并加白名单，体验极差。

#### 实现方案

```python
# src/adfilter/quality/false_positive_analyzer.py
class FalsePositiveAnalyzer:
    """分析规则是否可能误杀合法域名"""

    def __init__(self, config: FalsePositiveConfig):
        # 白名单域名集合（已知合法域名）
        self.known_good: set[str] = self._load_known_good(config.known_good_lists)
        # Tranco Top-1M 排名
        self.popularity_rank: dict[str, int] = self._load_tranco(config.tranco_path)

    def analyze(self, rules: list[Rule]) -> FalsePositiveReport:
        """分析规则集中的潜在误杀"""
        suspects = []

        for rule in rules:
            if rule.mode != Mode.DENY:
                continue

            risk_score = 0
            reasons = []

            # 1. 域名在 Tranco Top-1M 中
            rank = self.popularity_rank.get(rule.target)
            if rank:
                risk_score += max(0, (100000 - rank) / 1000)
                reasons.append(f"Tranco 排名 #{rank}")

            # 2. 域名在已知合法列表中
            if rule.target in self.known_good:
                risk_score += 50
                reasons.append("在已知合法域名列表中")

            # 3. 域名是常见服务的子域名
            if self._is_common_service_subdomain(rule.target):
                risk_score += 30
                reasons.append("属于常见服务的子域名")

            # 4. 规则过于宽泛（影响面大）
            if Control.OVERLAY in rule.controls and rule.target.count(".") == 1:
                risk_score += 20
                reasons.append("二级域名 overlay 规则（影响所有子域名）")

            if risk_score >= config.alert_threshold:
                suspects.append(FalsePositiveSuspect(
                    domain=rule.target,
                    risk_score=risk_score,
                    reasons=reasons,
                    source=rule.source_name
                ))

        return FalsePositiveReport(suspects=sorted(suspects, key=lambda s: -s.risk_score))
```

#### 数据源

| 数据 | 来源 | 用途 |
|------|------|------|
| Tranco Top-1M | https://tranco-list.eu/ | 域名流行度排名 |
| 已知合法域名 | 手动维护 + 社区贡献 | CDN、银行、政府等不应拦截的域名 |
| 常见服务后缀 | 内置列表 | `.cdn.cloudflare.net`、`.googleapis.com` 等 |

#### 配置

```yaml
quality:
  false_positive:
    enable: true
    alert_threshold: 30           # 风险分 ≥ 30 报告
    tranco_path: .cache/tranco.csv
    tranco_update_days: 7         # 每 7 天更新 Tranco 列表
    known_good_lists:
      - https://raw.githubusercontent.com/.../known-good-domains.txt
      - config/known-good.txt
```

#### 疑难点

| 难点 | 解决方案 |
|------|---------|
| Tranco 列表 25MB，加载慢 | 只加载 Top-100K，用 bisect 做 O(log n) 查找 |
| "合法"定义主观 | 提供建议而非自动移除，最终由用户决定 |
| CDN 域名复杂 | 维护 CDN 后缀列表（Cloudflare、Akamai、Fastly 等） |
| 误杀 vs 必要拦截 | 某些域名确实用于跟踪但也提供核心功能，需人工判断 |

---

### 2.3 规则冲突检测

#### 问题背景

多源合并后可能出现逻辑冲突：
- 同一域名同时出现 DENY 和 ALLOW 规则
- 子域 DENY 但父域 ALLOW（或反过来）
- 不同源对同一域名持不同态度

#### 实现方案

```python
# src/adfilter/quality/conflict_detector.py
class ConflictType(StrEnum):
    DENY_ALLOW_SAME_TARGET = "同一域名既DENY又ALLOW"
    PARENT_CHILD_CONFLICT = "父子域名规则方向矛盾"
    SOURCE_DISAGREEMENT = "不同源对同一域名态度不一致"

@dataclass
class Conflict:
    type: ConflictType
    domain: str
    rules: list[Rule]          # 冲突的规则
    resolution: str            # 建议的解决方式
    confidence: float          # 解决方案的置信度 (0-1)

class ConflictDetector:
    def detect(self, rules: list[Rule]) -> list[Conflict]:
        conflicts = []
        conflicts.extend(self._find_deny_allow_conflicts(rules))
        conflicts.extend(self._find_hierarchy_conflicts(rules))
        conflicts.extend(self._find_source_disagreements(rules))
        return conflicts
```

#### 输出报告

```json
{
  "conflicts": [
    {
      "type": "DENY_ALLOW_SAME_TARGET",
      "domain": "tracker.example.com",
      "deny_sources": ["easylist", "anti-ad"],
      "allow_sources": ["user-allowlist"],
      "resolution": "用户白名单优先，移除 DENY 规则",
      "confidence": 0.95
    }
  ],
  "summary": {
    "total_conflicts": 42,
    "auto_resolved": 38,
    "needs_review": 4
  }
}
```

---

### 2.4 规则评分系统

#### 设计思路

为每条规则计算一个综合质量分，帮助用户理解规则集的健康状况：

```python
@dataclass
class RuleScore:
    domain: str
    total_score: float          # 0-100
    components: dict[str, float]  # 各维度得分

class RuleScorer:
    def score(self, rule: Rule) -> RuleScore:
        components = {
            "multi_source": self._source_score(rule),      # 多源确认加分
            "freshness": self._freshness_score(rule),      # 域名活跃度
            "specificity": self._specificity_score(rule),  # 规则精确度
            "no_conflict": self._conflict_score(rule),     # 无冲突加分
            "not_overbroad": self._breadth_score(rule),    # 不过于宽泛
        }
        return RuleScore(
            domain=rule.target,
            total_score=sum(components.values()) / len(components),
            components=components
        )
```

#### 评分维度

| 维度 | 满分条件 | 权重 |
|------|---------|------|
| 多源确认 | 3+ 独立源包含该规则 | 30% |
| 域名活跃 | DNS 探测确认存活 | 25% |
| 精确度 | 精确域名匹配（非通配符） | 20% |
| 无冲突 | 不与其他规则矛盾 | 15% |
| 不宽泛 | 非顶级域名的 overlay | 10% |

#### 应用场景

- **规则精简模式**：只保留评分 > 60 的规则，生成精简版规则集
- **源质量排名**：统计每个源的平均规则评分，指导用户选择高质量源
- **构建报告增强**：展示规则集整体健康分数

---

### 2.5 规则变更智能 Diff

#### 增强现有 `adfilter diff`

```bash
# 基础 diff（已有）
adfilter diff old_dns.txt new_dns.txt --format dns

# 新增：HTML 可视化报告
adfilter diff old_dns.txt new_dns.txt --format dns --html diff_report.html

# 新增：变更影响分析
adfilter diff old_dns.txt new_dns.txt --format dns --impact
```

#### 影响分析输出

```
📊 规则变更分析
━━━━━━━━━━━━━━
新增规则: 1,200 条
  ├─ 广告域名: 800 条
  ├─ 隐私追踪: 350 条
  └─ 恶意软件: 50 条

删除规则: 300 条
  ├─ 死域名清理: 250 条
  └─ 误杀修复: 50 条

⚠️ 高风险变更:
  ├─ 新增 overlay 规则 "example.com" — 影响所有子域名
  └─ 删除 "cdn.important-service.com" — 可能影响服务加载
```

---


## Phase 3 — 订阅服务化 (v0.4)

**目标时间**：v0.3 后 6-8 周
**核心目标**：从"生成文件丢到 GitHub"进化为"用户可以交互的规则订阅服务"。

### 3.1 Web Dashboard

#### 设计理念

不是做一个复杂的管理后台，而是做一个 **规则订阅引导页**：
- 用户 30 秒内找到自己需要的订阅链接
- 可视化展示规则质量和构建状态
- 提供基础的规则搜索功能

#### 技术架构

```
┌─────────────────────────────────────────────────┐
│                  Web Dashboard                    │
│                                                   │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────┐ │
│  │ 订阅引导页   │  │ 构建状态面板  │  │ 规则搜索 │ │
│  │             │  │              │  │         │ │
│  │ 选格式      │  │ 上次构建时间  │  │ 输入域名 │ │
│  │ 复制链接    │  │ 规则总数     │  │ 查看来源 │ │
│  │ 使用教程    │  │ 质量评分     │  │ 在哪个源 │ │
│  └─────────────┘  └──────────────┘  └─────────┘ │
│                                                   │
│  Backend: Litestar (Python)                       │
│  Frontend: Jinja2 + Tailwind CSS + htmx          │
│  Data: build-report.json (无数据库)               │
└─────────────────────────────────────────────────┘
```

#### 实现方案

```python
# src/adfilter/web/app.py
from litestar import Litestar, get
from litestar.response import Template

@get("/")
async def dashboard(state: AppState) -> Template:
    report = state.load_build_report()
    return Template("dashboard.html", context={
        "last_build": report.finished_at,
        "total_rules": sum(o.count for o in report.outputs),
        "outputs": report.outputs,
        "sources": report.sources,
    })

@get("/search")
async def search_domain(domain: str, state: AppState) -> dict:
    """搜索某个域名是否在规则中，来自哪些源"""
    results = state.rule_index.search(domain)
    return {"domain": domain, "found": bool(results), "sources": results}

@get("/api/build", status_code=202)
async def trigger_build(state: AppState) -> dict:
    """手动触发一次构建"""
    state.build_queue.put_nowait("manual")
    return {"status": "queued", "message": "构建已加入队列"}
```

#### 技术选型

| 组件 | 选择 | 理由 |
|------|------|------|
| Web 框架 | Litestar | 比 FastAPI 更轻量、dataclass 原生支持 |
| 模板引擎 | Jinja2 | SSR，无需前端构建步骤 |
| 交互 | htmx | 轻量级动态交互，无需 JS 框架 |
| 样式 | Tailwind CSS (CDN) | 零构建，美观 |
| 数据源 | build-report.json | 无数据库依赖 |

#### 依赖隔离

```toml
# pyproject.toml
[project.optional-dependencies]
web = ["litestar>=2.0", "jinja2>=3.1", "uvicorn>=0.30"]
```

用户只想用 CLI 时不需要安装 web 依赖：
```bash
pip install adfilter       # 仅 CLI
pip install adfilter[web]  # CLI + Web Dashboard
```

#### 疑难点

| 难点 | 解决方案 |
|------|---------|
| 构建时文件锁 | Web 触发构建时，写临时目录 → 构建完成后原子 rename |
| 规则搜索性能 | 预构建倒排索引（domain → sources），加载到内存 |
| 与 serve 命令整合 | Dashboard 和文件服务在同一端口，`/rules/` 路径提供规则文件 |
| 资源消耗 | Jinja2 SSR + htmx 极轻量，不需要 Node.js 构建 |

---

### 3.2 RESTful API

#### 端点设计

```
GET  /api/v1/status              # 构建状态
GET  /api/v1/outputs             # 所有输出文件列表 + 元数据
GET  /api/v1/sources             # 规则源状态
GET  /api/v1/search?domain=x     # 域名搜索
GET  /api/v1/quality/report      # 质量报告摘要
POST /api/v1/build               # 触发构建
GET  /api/v1/subscribe/:format   # 获取订阅链接（可带参数定制）

# 未来（v0.5 个性化订阅）
POST /api/v1/subscribe/custom    # 创建自定义订阅
GET  /api/v1/subscribe/:id       # 获取自定义订阅内容
```

#### 响应示例

```json
// GET /api/v1/status
{
  "version": "0.4.0",
  "last_build": "2026-08-01T08:00:00Z",
  "next_build": "2026-08-01T16:00:00Z",
  "total_rules": 98234,
  "total_outputs": 12,
  "quality_score": 87.5,
  "build_duration_ms": 2900
}
```

---

### 3.3 CDN 分发

#### 问题背景

当前规则文件托管在 GitHub raw（`raw.githubusercontent.com`），存在：
- 国内访问不稳定
- 无自定义 HTTP 头（如 `Cache-Control`）
- 无法统计下载量

#### 解决方案对比

| 方案 | 优点 | 缺点 | 成本 |
|------|------|------|------|
| GitHub Pages | 免费、自动部署 | 无 CORS 控制、国内慢 | 免费 |
| Cloudflare Pages | 免费、全球 CDN、自定义域名 | 需配置 | 免费 |
| Cloudflare Workers | 可编程边缘、自定义逻辑 | 复杂度高 | 免费 (100K/天) |
| Vercel Edge | 简单部署、免费额度足够 | 国内可能受限 | 免费 |
| jsDelivr (npm) | 国内 CDN 镜像、免费 | 需发布 npm 包 | 免费 |

#### 推荐方案：GitHub Pages + Cloudflare CDN

```
用户设备 ──→ Cloudflare CDN ──→ GitHub Pages (release 分支)
                  │
                  ├─ 全球 CDN 加速
                  ├─ 自定义域名 (e.g., rules.adfilter.dev)
                  ├─ 自动 HTTPS
                  └─ 访问统计
```

#### 实现步骤

1. **GitHub Pages**：将 release 分支配置为 Pages 源
2. **自定义域名**：在 release 分支添加 `CNAME` 文件
3. **Cloudflare**：DNS 代理 + Cache Rules 配置
4. **构建后自动部署**：auto-update.yml 已发布到 release 分支，Pages 自动拉取

#### 疑难点

| 难点 | 解决方案 |
|------|---------|
| CORS 限制 | Cloudflare Workers 添加 `Access-Control-Allow-Origin: *` |
| 缓存更新延迟 | 构建完成后调用 Cloudflare Purge API 清除缓存 |
| 国内加速 | 备选：同步发布到 jsDelivr（通过 npm），国内有镜像 |
| 下载量统计 | Cloudflare Analytics 免费提供 |

---

### 3.4 通知系统增强

#### 当前状态

已支持 Telegram / Discord / WeCom，需增强：

#### 新增功能

```python
# 构建摘要增强
@dataclass
class BuildNotification:
    status: Literal["success", "failure", "warning"]
    total_rules: int
    rule_delta: int              # 与上次相比增减
    quality_score: float
    dead_domains_removed: int
    conflicts_found: int
    duration_ms: int
    subscribe_url: str

# 告警通知（新增）
@dataclass
class AlertNotification:
    level: Literal["info", "warning", "critical"]
    message: str
    # 触发条件：规则数骤降、源长期不可达、质量分下降等
```

#### 通知模板

```
✅ adfilter 构建成功
━━━━━━━━━━━━━━━━━━━━━
📅 2026-08-01 16:00 CST
📊 规则总数: 98,234 (+1,200)
⭐ 质量评分: 87.5/100
🗑️ 清理死域名: 250 条
⚠️ 冲突规则: 4 条 (需人工审核)
⏱️ 耗时: 2.9s
🔗 https://rules.adfilter.dev/dns.txt
```

```
⚠️ adfilter 告警
━━━━━━━━━━━━━━━━━━━━━
源 "easylist-china" 已连续 3 次拉取失败
当前使用 48 小时前的缓存版本
建议检查源地址或网络状态
```

---

### 3.5 GitHub Pages 订阅页面

#### 方案

在 auto-update.yml 中，除了规则文件，额外生成一个 `index.html`：

```html
<!-- 自动生成，每次构建更新 -->
<!DOCTYPE html>
<html>
<head><title>adfilter 规则订阅</title></head>
<body>
  <h1>adfilter 规则订阅中心</h1>
  <p>最后更新：2026-08-01 16:00 CST | 规则总数：98,234</p>

  <table>
    <tr>
      <th>格式</th><th>适用工具</th><th>订阅链接</th><th>规则数</th>
    </tr>
    <tr>
      <td>AdGuard DNS</td>
      <td>AdGuard Home</td>
      <td><input value="https://rules.adfilter.dev/dns.txt" readonly>
          <button onclick="copy(this)">复制</button></td>
      <td>98,234</td>
    </tr>
    <!-- ... 12 种格式 ... -->
  </table>
</body>
</html>
```

这个页面可以零成本托管在 GitHub Pages 上，作为项目的"官网"。

---


## Phase 4 — 规则平台 (v0.5)

**目标时间**：v0.4 后 8-12 周
**核心目标**：从"一个人维护的工具"进化为"社区驱动的规则平台"。

### 4.1 个性化订阅

#### 设计理念

不同用户有不同需求：
- 家庭用户：广告 + 恶意软件，不需要隐私追踪（会影响某些功能）
- 极客用户：全部规则，越多越好
- 公司用户：只要恶意软件防护，广告不管
- 中国用户：需要中国区特定源
- 日本用户：需要日本区特定源

#### 实现方案

```
用户选择：
  ☑ 广告拦截 (anti-ad, easylist)
  ☑ 隐私防护 (easyprivacy)
  ☐ 恶意软件 (urlhaus, phishing-army)
  ☑ 中国区补充 (easylist-china, cjx-annoyance)
  输出格式: AdGuard DNS

         │
         ▼

生成个性化订阅链接:
  https://rules.adfilter.dev/custom/a1b2c3d4.txt
```

#### API 设计

```python
# POST /api/v1/subscribe/custom
{
    "categories": ["ads", "privacy"],
    "regions": ["cn"],
    "format": "dns",
    "allowlist": ["example.com", "mybank.com"],
    "quality_threshold": 50  # 可选：只要评分 > 50 的规则
}

# Response
{
    "subscription_id": "a1b2c3d4",
    "url": "https://rules.adfilter.dev/custom/a1b2c3d4.txt",
    "estimated_rules": 75000,
    "expires_at": null,  # 永不过期，随构建更新
    "config_hash": "sha256:..."
}
```

#### 技术方案

```python
# src/adfilter/web/custom_subscription.py
class CustomSubscriptionManager:
    """管理个性化订阅"""

    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.subscriptions: dict[str, SubscriptionConfig] = {}

    def create(self, config: SubscriptionConfig) -> str:
        """创建订阅，返回 ID"""
        # 用配置内容的 hash 作为 ID（相同配置 = 相同 ID）
        config_json = config.model_dump_json(sort_keys=True)
        sub_id = hashlib.sha256(config_json.encode()).hexdigest()[:8]
        self.subscriptions[sub_id] = config
        self._persist(sub_id, config)
        return sub_id

    async def generate(self, sub_id: str) -> str:
        """根据订阅配置生成规则文件内容"""
        config = self.subscriptions[sub_id]
        # 从预构建的分组规则中组合
        rules = set()
        for category in config.categories:
            rules.update(self.rule_store.get_by_category(category))
        for region in config.regions:
            rules.update(self.rule_store.get_by_region(region))
        # 应用白名单
        rules = apply_allowlist(rules, config.allowlist)
        # 应用质量阈值
        if config.quality_threshold:
            rules = {r for r in rules if self.scorer.score(r).total_score >= config.quality_threshold}
        # 格式化输出
        handler = get_handler(config.format)
        return handler.format_all(rules)
```

#### 存储方案

| 规模 | 方案 | 说明 |
|------|------|------|
| < 1000 订阅 | JSON 文件 | `subscriptions/{id}.json`，简单可靠 |
| 1000-10000 | SQLite | 单文件数据库，无需额外服务 |
| > 10000 | PostgreSQL | 需要独立数据库服务 |

初期使用 JSON 文件即可，后续按需迁移。

#### 疑难点

| 难点 | 解决方案 |
|------|---------|
| 动态生成性能 | 预构建按 category/region 的规则索引，组合时直接集合运算 |
| 存储膨胀 | 不存储生成结果，每次请求实时生成（规则在内存中） |
| 缓存策略 | 每次构建后 invalidate 所有订阅缓存；请求级缓存 5 分钟 |
| 订阅 ID 冲突 | 用配置 hash 做 ID，相同配置自动复用 |

---

### 4.2 社区规则贡献

#### 设计理念

让用户可以：
1. 提交新的规则源到 source catalog
2. 报告误杀（自动创建 Issue + 加入白名单候选）
3. 提交自定义规则（社区审核后合并）

#### 实现方案

```yaml
# 社区贡献的规则源格式（通过 PR 提交）
# community/sources/my-custom-list.yaml
id: my-ad-list
name: "My Ad Blocking List"
url: https://example.com/my-rules.txt
format: hosts
region: cn
category: ads
maintainer: "github-username"
description: "个人维护的中国区广告域名列表"
# 以下为审核信息（由维护者填写）
review:
  status: pending          # pending → approved → merged
  reviewed_by: null
  quality_check: null      # 自动质量检测结果
```

#### 自动质量检测（CI 集成）

当有人提交新源 PR 时，自动运行：

```yaml
# .github/workflows/source-review.yml
name: Source Review
on:
  pull_request:
    paths: ["community/sources/*.yaml"]

jobs:
  quality-check:
    steps:
      - name: Fetch and analyze source
        run: |
          uv run adfilter source-check community/sources/${{ steps.changed.outputs.file }}
```

```python
# adfilter source-check 命令
def source_check(source_path: Path):
    """自动检测提交的规则源质量"""
    source = load_source(source_path)
    report = {
        "reachable": check_reachability(source.url),
        "format_valid": validate_format(source.url, source.format),
        "rule_count": count_rules(source.url),
        "overlap_with_existing": calculate_overlap(source.url),
        "dead_domain_ratio": estimate_dead_ratio(source.url),
        "quality_score": calculate_score(source.url),
    }
    # 输出为 PR comment
    post_review_comment(report)
```

---

### 4.3 规则市场 (Source Marketplace)

#### 概念

类似 [FilterLists.com](https://filterlists.com/) 但更聚焦：

```
┌─────────────────────────────────────────────────────────┐
│                  adfilter 规则市场                         │
│                                                           │
│  🔍 搜索规则源...                                         │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ ⭐ anti-AD                              [已启用]     │ │
│  │    中国最流行的广告过滤列表                            │ │
│  │    📊 质量分: 92  📐 规则数: 45,000  🌏 中国          │ │
│  │    🔄 更新频率: 每日  👤 maintainer: privacy-tools    │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ ⭐ EasyPrivacy                          [一键启用]   │ │
│  │    ABP 官方隐私防护列表                               │ │
│  │    📊 质量分: 95  📐 规则数: 18,000  🌏 全球          │ │
│  │    🔄 更新频率: 每日  👤 maintainer: AdbBlock Plus    │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  分类: [广告] [隐私] [恶意软件] [烦人元素]                │
│  地区: [中国] [日本] [全球] [欧洲]                        │
└─────────────────────────────────────────────────────────┘
```

#### 数据模型

```python
@dataclass
class SourceMeta:
    id: str
    name: str
    url: str
    format: str
    region: str
    category: str
    description: str
    maintainer: str
    # 质量指标（自动计算）
    quality_score: float
    rule_count: int
    dead_domain_ratio: float
    overlap_ratio: float         # 与其他源的重复率
    update_frequency: str
    last_checked: datetime
    is_reachable: bool
    # 社区指标
    subscribers: int             # 有多少用户启用了这个源
    reports: int                 # 误杀报告数
```

#### 疑难点

| 难点 | 解决方案 |
|------|---------|
| 源质量实时监控 | 定时 CronJob 检测所有源的可达性和质量指标 |
| 排名算法 | 综合质量分、订阅数、更新频率、误杀报告等多维度 |
| 恶意源防护 | 新源默认 sandbox 状态，经人工审核后才进入正式目录 |
| 目录同步 | 支持远程目录（`adfilter sources update`），但内置目录随版本发布 |

---

### 4.4 多租户支持

#### 场景

- 企业为员工提供定制规则
- ISP 为用户提供 DNS 过滤规则
- 社区维护者为不同地区提供定制版本

#### 实现方案

```yaml
# config/tenants/company-a.yaml
tenant:
  id: company-a
  name: "Company A"
  sources:
    - anti-ad
    - easyprivacy
    - urlhaus
  allowlist:
    - internal.company-a.com
    - *.corp.company-a.com
  output:
    formats: [dns, clash, surge]
    path: ./tenants/company-a/
    base_url: https://rules.company-a.com/
```

```bash
# 为所有租户构建
adfilter run --tenants config/tenants/

# 为特定租户构建
adfilter run --tenant company-a
```

---

### 4.5 插件生态完善

#### 当前状态

已有 `entry_points` 机制支持第三方 Handler 和 Notifier。

#### 需完善

| 扩展点 | 状态 | v0.5 目标 |
|--------|------|----------|
| Handler (输出格式) | ✅ 已支持 | 完善文档 + 示例 |
| Notifier (通知渠道) | ✅ 已支持 | 完善文档 + 示例 |
| Fetcher (数据获取) | ❌ 未支持 | 支持自定义 fetcher（如 S3、FTP） |
| Optimizer (优化器) | ❌ 未支持 | 支持自定义优化步骤 |
| QualityChecker (质检) | ❌ 未支持 | 支持自定义质量检测规则 |

#### 插件开发者体验

```bash
# 创建插件模板
adfilter plugin init --type handler --name my-format

# 生成：
# my-adfilter-plugin/
# ├── pyproject.toml        (预填 entry_points)
# ├── src/my_plugin/
# │   └── handler.py        (Handler 模板代码)
# └── tests/
#     └── test_handler.py   (测试模板)
```

---


## Phase 5 — 生产就绪 (v1.0)

**目标时间**：v0.5 后 8-12 周
**核心目标**：达到生产级品质，支持大规模部署，可信赖地服务于成千上万用户。

### 5.1 PyPI 正式发布

#### 发布策略

```toml
# pyproject.toml
[project]
name = "adfilter"
version = "1.0.0"
requires-python = ">=3.12"   # 放宽到 3.12+ 增加用户覆盖面

[project.optional-dependencies]
web = ["litestar>=2.0", "jinja2>=3.1", "uvicorn>=0.30"]
notify = ["httpx>=0.27"]
quality = ["aiodns>=3.0"]     # 质量引擎依赖
all = ["adfilter[web,notify,quality]"]
```

#### 发布自动化

```yaml
# .github/workflows/release.yml
name: Release
on:
  push:
    tags: ["v*"]

jobs:
  pypi:
    runs-on: ubuntu-latest
    permissions:
      id-token: write  # PyPI Trusted Publisher
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv build
      - uses: pypa/gh-action-pypi-publish@release/v1

  docker:
    steps:
      - uses: docker/build-push-action@v5
        with:
          push: true
          tags: ghcr.io/lknife666/adfilter:${{ github.ref_name }},ghcr.io/lknife666/adfilter:latest

  github-release:
    steps:
      - run: uv run git-cliff --latest > RELEASE_NOTES.md
      - uses: softprops/action-gh-release@v1
        with:
          body_path: RELEASE_NOTES.md
```

#### 疑难点

| 难点 | 解决方案 |
|------|---------|
| Python 版本兼容 | v1.0 放宽到 3.12+，使用 `from __future__ import annotations` 处理类型提示 |
| 依赖冲突 | 核心依赖（pydantic, aiohttp, typer）锁定宽松版本范围 |
| 版本号管理 | 使用 `hatch-vcs` 从 git tag 自动获取版本 |

---

### 5.2 Kubernetes 部署支持

#### Helm Chart

```yaml
# charts/adfilter/values.yaml
replicaCount: 1

image:
  repository: ghcr.io/lknife666/adfilter
  tag: "1.0.0"

service:
  type: ClusterIP
  port: 8787

config:
  # 内嵌到 ConfigMap
  application.yaml: |
    application:
      config:
        input:
          rule:
            default:
              - name: anti-ad
                type: easylist
                path: https://anti-ad.net/easylist.txt
        output:
          path: /data/rules
          files:
            - { name: dns.txt, type: dns }

persistence:
  rules:
    enabled: true
    size: 1Gi
  cache:
    enabled: true
    size: 2Gi

cronJob:
  # 定时重建规则
  schedule: "0 */8 * * *"
  resources:
    limits:
      memory: 512Mi
      cpu: 500m

ingress:
  enabled: true
  className: nginx
  hosts:
    - host: rules.example.com
      paths:
        - path: /
          pathType: Prefix
```

#### 架构

```
┌─────────────────────────────────────────────┐
│                Kubernetes                      │
│                                               │
│  ┌──────────────┐     ┌──────────────────┐  │
│  │  CronJob     │     │   Deployment     │  │
│  │  (定时构建)   │────▶│   (HTTP serve)   │  │
│  │  每8h执行     │     │   Web Dashboard  │  │
│  └──────────────┘     └──────────────────┘  │
│         │                      │             │
│         ▼                      ▼             │
│  ┌──────────────────────────────────────┐   │
│  │           PVC (共享存储)               │   │
│  │  /data/rules/  (规则文件)             │   │
│  │  /data/cache/  (HTTP 缓存)            │   │
│  └──────────────────────────────────────┘   │
│                                               │
│  ┌──────────────┐     ┌──────────────────┐  │
│  │   Ingress    │     │    Service       │  │
│  │  rules.xxx   │────▶│    :8787         │  │
│  └──────────────┘     └──────────────────┘  │
└─────────────────────────────────────────────┘
```

---

### 5.3 性能基准与优化

#### 目标指标

| 场景 | 目标 | 当前估计 |
|------|------|---------|
| 解析 100K 规则 | < 500ms | ~800ms |
| 优化 100K 规则 (含子域折叠) | < 1s | ~1.5s |
| 完整 pipeline (12 格式输出) | < 5s | ~8s |
| 内存峰值 (100K 规则) | < 256MB | ~400MB |
| 增量构建 (无变化) | < 100ms | ~200ms |
| Web API 响应 (规则搜索) | < 50ms | N/A |
| 个性化订阅生成 | < 200ms | N/A |

#### 优化方向

```python
# 1. 子域折叠：用 Trie 替代暴力遍历 O(n²) → O(n)
class DomainTrie:
    """按 label 反向构建的 Trie，用于高效子域查找"""
    def __init__(self):
        self.root: dict = {}

    def insert(self, domain: str) -> None:
        labels = domain.split(".")[::-1]  # 反转：com.example.sub
        node = self.root
        for label in labels:
            node = node.setdefault(label, {})
        node["$"] = True  # 标记终止

    def has_ancestor(self, domain: str) -> bool:
        """检查是否存在更短的祖先域名"""
        labels = domain.split(".")[::-1]
        node = self.root
        for i, label in enumerate(labels):
            if label not in node:
                return False
            node = node[label]
            if "$" in node and i < len(labels) - 1:
                return True  # 找到了更短的祖先
        return False

# 2. Rule 对象内存优化：使用 __slots__ + 对象池
# （已有 slots=True，进一步考虑 intern strings）

# 3. 并行写入：12 个输出文件并行格式化和写入
async def write_all_outputs(rules: list[Rule], outputs: list[OutputConfig]):
    async with asyncio.TaskGroup() as tg:
        for output in outputs:
            tg.create_task(write_single_output(rules, output))
```

#### 基准测试框架

```python
# benchmarks/bench_pipeline.py
import pytest
from pytest_benchmark.fixture import BenchmarkFixture

def test_parse_100k(benchmark: BenchmarkFixture, sample_100k: str):
    benchmark(parse_rules, sample_100k)

def test_optimize_100k(benchmark: BenchmarkFixture, rules_100k: list):
    benchmark(optimize, rules_100k)

def test_trie_collapse_100k(benchmark: BenchmarkFixture, rules_100k: list):
    benchmark(trie_collapse, rules_100k)
```

---

### 5.4 安全加固

#### 安全审计清单

| 风险类别 | 缓解措施 | 实现 |
|---------|---------|------|
| 依赖漏洞 | Dependabot + pip-audit 周扫描 | ✅ security.yml |
| SSRF | Fetcher 禁止 private IP / loopback / link-local | ✅ 已实现 |
| 输入注入 | 规则解析严格校验，拒绝含 shell 特殊字符的域名 | 需增强 |
| 路径遍历 | 输出路径只允许在配置的 output.path 下 | ✅ 已实现 |
| Secret 泄露 | 日志/报告中脱敏 token、webhook URL | 需增强 |
| 恶意规则源 | 规则内容沙箱检查（不执行任何代码） | 需新增 |
| DoS (Web) | 请求速率限制、构建队列深度限制 | 需新增 |
| 供应链攻击 | 使用 lock file (`uv.lock`)、验证 hash | ✅ 已实现 |

#### 新增安全功能

```python
# src/adfilter/security/input_validator.py
class RuleInputValidator:
    """验证规则内容安全性"""

    # 禁止的模式（可能是注入攻击）
    FORBIDDEN_PATTERNS = [
        re.compile(r'[;&|`$]'),           # Shell 特殊字符
        re.compile(r'\.\./'),              # 路径遍历
        re.compile(r'<script', re.I),      # XSS
        re.compile(r'\x00'),              # Null byte
    ]

    def validate_domain(self, domain: str) -> bool:
        """验证域名安全性"""
        if len(domain) > 253:
            return False
        if any(p.search(domain) for p in self.FORBIDDEN_PATTERNS):
            return False
        return True
```

---

### 5.5 可观测性

#### 结构化日志

```python
# 已有 JSON 日志支持，增强 context 信息
{
    "timestamp": "2026-10-01T08:00:00Z",
    "level": "INFO",
    "message": "source fetch completed",
    "source_name": "anti-ad",
    "duration_ms": 1200,
    "rule_count": 45000,
    "cache_hit": false,
    "build_id": "b1a2c3d4"
}
```

#### Metrics (可选，面向大规模部署)

```python
# 如果用户部署了 Prometheus
from prometheus_client import Counter, Histogram, Gauge

BUILD_DURATION = Histogram("adfilter_build_duration_seconds", "Build duration")
RULES_TOTAL = Gauge("adfilter_rules_total", "Total rules in latest build", ["format"])
SOURCE_ERRORS = Counter("adfilter_source_errors_total", "Source fetch errors", ["source"])
SUBSCRIPTIONS_ACTIVE = Gauge("adfilter_subscriptions_active", "Active custom subscriptions")
```

---

### 5.6 国际化 (i18n)

#### 实现方案

```python
# src/adfilter/i18n.py
import gettext
from pathlib import Path

LOCALE_DIR = Path(__file__).parent / "locales"

def setup_i18n(locale: str = "zh_CN") -> None:
    global _
    translation = gettext.translation("adfilter", LOCALE_DIR, [locale], fallback=True)
    _ = translation.gettext

# 使用
from .i18n import _
logger.info(_("构建完成，共 {count} 条规则").format(count=total))
```

#### 优先级

| 内容 | 优先级 | 说明 |
|------|--------|------|
| CLI 输出 (进度条、结果) | P1 | 用户直接看到 |
| 错误消息 | P1 | 排错时需要理解 |
| Web Dashboard | P2 | 可用浏览器翻译插件兜底 |
| 文档 | P3 | 维护两套语言成本高 |
| 代码注释 | P4 | 保持英文 |

支持语言（按用户量排序）：中文、英文、日文

---


## 技术难点总览

汇总各阶段的核心技术挑战和推荐解决方案：

### 架构层面

| 难点 | 影响 | 推荐方案 | 备选方案 |
|------|------|---------|---------|
| Python 性能天花板 | 大规则集处理慢 | Trie 数据结构 + 并行 I/O + 增量构建 | 核心算法用 Rust (PyO3) 重写 |
| 内存占用 | 100K+ 规则内存高 | `__slots__` + string intern + 分批处理 | 流式处理，不一次性加载 |
| 无状态 vs 有状态 | 个性化订阅需要持久化 | SQLite（单文件，无外部依赖） | JSON 文件存储 |
| Web 与 CLI 共存 | 不应强制安装 web 依赖 | `[project.optional-dependencies]` 分组 | 独立包 `adfilter-web` |

### 数据层面

| 难点 | 影响 | 推荐方案 |
|------|------|---------|
| 死域名误判 | 错误移除有效规则 | 连续 N 次失败 + 多 DNS 服务器验证 |
| 规则质量评分主观性 | 用户不信任评分 | 透明公开评分算法 + 各维度可配置权重 |
| Tranco 列表时效性 | 排名过时导致误判 | 每周自动更新 + 只作为参考而非决定因素 |
| 源格式自动检测 | 误判格式导致解析失败 | 多信号投票（文件头 + 行格式统计 + 显式声明优先） |

### 运维层面

| 难点 | 影响 | 推荐方案 |
|------|------|---------|
| CDN 缓存一致性 | 用户获取到旧规则 | 构建后主动 Purge + 文件名含 hash |
| 多环境配置 | 开发/测试/生产配置不同 | 环境变量覆盖 (`ADFILTER_*`) + `.env` 支持 |
| 监控告警 | 构建失败无人知道 | Webhook 通知 + Prometheus metrics |
| 长期运行内存泄漏 | serve 模式 OOM | 定期 GC + 构建完成后释放中间对象 |

### 社区层面

| 难点 | 影响 | 推荐方案 |
|------|------|---------|
| 恶意规则源提交 | 用户被引导到钓鱼站 | 人工审核 + 自动质量检测 + 沙箱期 |
| 插件 API 稳定性 | 第三方插件因接口变更而损坏 | 从 v1.0 起对公开 API 做 SemVer 承诺 |
| 文档多语言维护 | 翻译版本落后 | 以英文为主，中文同步维护，其他语言社区贡献 |

---

## 持续迭代方向

以下方向不绑定特定版本，根据需求和社区反馈随时推进。

### 方向 1：更多输入格式支持

| 格式 | 解析难度 | 优先级 | 说明 |
|------|---------|--------|------|
| uBlock Origin 扩展语法 | ⭐⭐⭐ | P2 | `$domain=`、`$badfilter`（识别并提取域名） |
| Pi-hole 正则 | ⭐⭐ | P2 | `/regex/` 格式 |
| ABP snippet filters | ⭐ | P3 | 仅需识别并跳过 |
| Brave shields | ⭐⭐ | P3 | Brave 浏览器特有格式 |

### 方向 2：更多输出格式支持

| 格式 | 目标用户 | 优先级 |
|------|---------|--------|
| pfBlockerNG | pfSense 防火墙 | P2 |
| AdGuard DNS Rewrite | AdGuard Home 高级用户 | P2 |
| Shadowrocket Module | iOS 用户 | P3 |
| NextDNS 兼容格式 | NextDNS 用户 | P3 |
| Bind RPZ | 企业 DNS | P3 |

### 方向 3：智能规则优化

| 功能 | 说明 | 复杂度 |
|------|------|--------|
| 规则合并 | `a.example.com` + `b.example.com` → `*.example.com` | ⭐⭐ |
| 正则压缩 | 多个相似规则合并为一条正则 | ⭐⭐⭐ |
| 规则拆分建议 | 过于宽泛的规则建议拆分为精确规则 | ⭐⭐ |
| 时间衰减 | 长期未被其他源确认的规则降低评分 | ⭐ |

### 方向 4：集成与生态

| 集成目标 | 方式 | 说明 |
|---------|------|------|
| Pi-hole | Adlist 格式 | 已支持 `hosts.txt` |
| AdGuard Home | DNS filter | 已支持 `dns.txt` |
| OpenWrt | LuCI app | 提供 OpenWrt 插件，一键配置订阅 |
| Home Assistant | Addon | HA 用户一键部署 |
| Synology NAS | Docker Compose | NAS 用户一键部署 |
| VS Code Extension | 规则编辑器 | 语法高亮 + 验证 + 补全 |

### 方向 5：数据分析与洞察

```
┌──────────────────────────────────────────────────────────┐
│                   规则生态洞察面板                          │
│                                                           │
│  📈 规则增长趋势    📊 源质量排名    🌍 地区分布         │
│                                                           │
│  规则总量变化 (30天)                                      │
│  ┌─────────────────────────────────────┐                 │
│  │    .·*·.                            │                 │
│  │  .·     ·*·.                  .*·.  │                 │
│  │ .·          ·*·.          .·*·     │                 │
│  │·                ·*·.  .·*·         │                 │
│  └─────────────────────────────────────┘                 │
│                                                           │
│  源质量 Top 5:                                           │
│  1. EasyPrivacy (95分)  2. anti-AD (92分)  ...           │
│                                                           │
│  本周新增威胁域名: 1,200                                  │
│  本周清理死域名: 300                                      │
│  本周误杀报告: 5                                          │
└──────────────────────────────────────────────────────────┘
```

---

## 里程碑时间线

```
2026 Q2          Q3              Q4              2027 Q1         Q2
  │               │               │               │               │
  ▼               ▼               ▼               ▼               ▼
v0.1.0          v0.2.0          v0.3.0          v0.4.0          v0.5.0 → v1.0.0
(当前)          基础加固         规则质量引擎     订阅服务化       规则平台 → 生产就绪
                4-6 周          6-8 周          6-8 周          8-12 周   8-12 周

关键里程碑:
├─ 2026.06: v0.2.0 — 测试覆盖 80%+，CI 完善，Docker 优化
├─ 2026.08: v0.3.0 — 死域名检测，误杀分析，规则评分
├─ 2026.10: v0.4.0 — Web Dashboard，CDN 分发，API
├─ 2027.01: v0.5.0 — 个性化订阅，社区贡献，规则市场
└─ 2027.03: v1.0.0 — PyPI 正式发布，Helm Chart，安全审计完成
```

---

## 开发优先级矩阵

按 **用户价值** × **实现成本** 排序：

```
                    高用户价值
                        │
     ┌──────────────────┼──────────────────┐
     │                  │                  │
     │  CDN分发          │  个性化订阅      │
     │  构建告警         │  Web Dashboard  │
     │  死域名检测       │  规则市场        │
     │                  │                  │
低成本 ─────────────────┼────────────────── 高成本
     │                  │                  │
     │  Docker优化       │  Helm Chart     │
     │  文档完善         │  国际化          │
     │  测试覆盖         │  Prometheus     │
     │                  │                  │
     └──────────────────┼──────────────────┘
                        │
                    低用户价值
```

**立即启动**（高价值低成本）：
1. 测试覆盖 + CI
2. 死域名检测
3. CDN 分发 (GitHub Pages + Cloudflare)
4. 构建结果通知

**中期投入**（高价值高成本）：
5. Web Dashboard
6. 个性化订阅
7. 规则市场

**按需推进**（低价值低成本）：
8. Docker 优化
9. 文档站点

**远期规划**（低价值高成本）：
10. Helm Chart
11. 国际化
12. Prometheus metrics

---

## 竞品观察清单

持续关注以下项目的动态，及时调整策略：

| 项目 | 关注点 | 我们的应对 |
|------|--------|-----------|
| [Pi-hole](https://github.com/pi-hole/pi-hole) | 是否增加多格式输出 | 保持格式覆盖领先 |
| [AdGuard Home](https://github.com/AdguardTeam/AdGuardHome) | DNS 规则优化能力 | 深耕规则质量（评分、死域名、误杀） |
| [FilterLists](https://filterlists.com/) | 规则目录数据 | 可参考其数据，但我们提供更好的质量分析 |
| [NextDNS](https://nextdns.io/) | 商业化的规则服务 | 保持开源优势，支持更多本地化格式 |
| [sing-box](https://github.com/SagerNet/sing-box) | 规则格式变更 | 及时适配新版本 |
| [Clash Meta](https://github.com/MetaCubeX/mihomo) | 规则语法更新 | 保持兼容 |

---

## 贡献指南

欢迎通过以下方式参与 adfilter 的发展：

1. **Issue 讨论**：对 Roadmap 中的优先级或方向有建议
2. **Pull Request**：实现某个功能或修复 Bug
3. **规则源贡献**：提交新的高质量规则源
4. **误杀报告**：发现误拦截时提 Issue
5. **文档翻译**：帮助翻译文档到其他语言
6. **测试反馈**：在不同环境中测试并报告问题

---

> **许可**：本文档随项目采用 MIT 许可。
>
> **更新日志**：本 Roadmap 会随着项目进展持续更新，重大方向调整会在 Discussion 中公开讨论。
