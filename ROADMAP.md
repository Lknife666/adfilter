# adfilter Roadmap

> 本文档为 adfilter 项目的详细迭代计划，聚焦安全合规、智能质量评估、开发者体验三大主线。
>
> 当前版本：**v0.4.0** | 最后更新：2026-05-20

---

## 目录

- [版本总览](#版本总览)
- [v0.5.0 — 安全基建](#v050--安全基建)
- [v0.6.0 — 智能质量引擎](#v060--智能质量引擎)
- [v0.7.0 — 开发者体验](#v070--开发者体验)
- [v1.0.0 — 生产就绪](#v100--生产就绪)
- [设计原则](#设计原则)

---

## 版本总览



```
v0.4.0 (当前)  ──▶  v0.5.0 (短期)  ──▶  v0.6.0 (中期)  ──▶  v0.7.0 (中长期)  ──▶  v1.0.0 (长期)
   │                    │                    │                     │                     │
   │  12格式+插件系统   │  签名验证          │  质量评分引擎       │  Playground 调试器   │  全链路安全审计
   │  通知+白名单       │  内容安全审计      │  规则效率指标       │  IDE/LSP 支持        │  合规标签体系
   │  源目录+预设       │  供应链防护        │  源健康度仪表盘     │  WASM 在线转换       │  企业级部署
```

---

## v0.5.0 — 安全基建

**目标时间**：v0.4.0 发布后 4-6 周
**核心目标**：建立规则来源信任链，防范供应链攻击，确保构建产物可信。

### 1. 规则来源签名验证

#### 问题背景

远程规则源通过 HTTP/HTTPS 拉取，存在以下风险：
- 中间人攻击篡改规则内容（特别是仍使用 HTTP 的源）
- 源服务器被入侵，规则被植入恶意条目
- CDN 缓存污染导致用户拿到错误版本

#### 实现方案



```python
# src/adfilter/security/signature.py
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


@dataclass
class SourceSignature:
    """规则源的签名元数据"""
    source_id: str
    content_hash: str          # SHA-256 of content
    signature: bytes           # Ed25519 signature
    signed_at: str             # ISO 8601 timestamp
    signer_fingerprint: str    # 签名者公钥指纹


class SignatureVerifier:
    """验证规则源内容签名"""

    def __init__(self, trusted_keys_dir: Path) -> None:
        self._trusted_keys: dict[str, Ed25519PublicKey] = {}
        self._load_trusted_keys(trusted_keys_dir)

    def verify(self, content: bytes, sig: SourceSignature) -> VerifyResult:
        """验证内容签名，返回验证结果"""
        # 1. 计算内容哈希
        actual_hash = hashlib.sha256(content).hexdigest()
        if actual_hash != sig.content_hash:
            return VerifyResult(valid=False, reason="content hash mismatch")

        # 2. 查找对应公钥
        pubkey = self._trusted_keys.get(sig.signer_fingerprint)
        if not pubkey:
            return VerifyResult(valid=False, reason="unknown signer")

        # 3. 验证签名
        try:
            pubkey.verify(sig.signature, content)
            return VerifyResult(valid=True)
        except InvalidSignature:
            return VerifyResult(valid=False, reason="invalid signature")
```

#### 配置

```yaml
security:
  signature:
    enable: true
    trusted_keys_dir: config/trusted_keys/   # 存放可信公钥
    on_failure: cache_fallback               # verify_fail 时策略
    # 可选: reject (拒绝) | warn (告警但继续) | cache_fallback (回退缓存)
    sources_requiring_signature:             # 强制要求签名的源
      - anti-ad
      - easylist
```



#### 签名工作流

```
规则源维护者                          adfilter 用户
─────────────                        ─────────────
1. 生成 Ed25519 密钥对
2. 发布公钥 (公钥指纹)  ──────────▶  3. 将公钥加入 trusted_keys/
4. 发布规则文件
5. 发布 .sig 签名文件   ──────────▶  6. 下载规则 + 签名
                                     7. 自动验签
                                     8. 验签通过 → 正常构建
                                        验签失败 → 策略处理
```

#### 技术要点

| 要点 | 方案 |
|------|------|
| 签名算法 | Ed25519（快速、安全、签名短） |
| 签名文件格式 | `<source_url>.sig` (detached signature) |
| 密钥分发 | 初始版本内置于 `source_catalog.yaml`，未来支持 TOFU |
| 向后兼容 | 未配置签名的源正常工作，不强制 |

#### 疑难点

1. **第三方源不提供签名**：绝大多数开源规则源不会提供签名。解决：adfilter 自身可以在拉取后"加签"（签名内容 + 时间戳），下次构建对比签名检测内容是否异常变动。
2. **密钥轮换**：需要支持多个有效公钥并存，旧公钥设过期时间。
3. **CI 集成**：auto-update workflow 中如果验签失败，需要通知维护者但不中断其他源的构建。

---

### 2. 规则内容安全审计

#### 问题背景

即使来源可信，规则源也可能意外或恶意地引入危险条目：
- 阻断关键基础设施域名（google.com, github.com, microsoft.com）
- 单次更新新增数量异常（正常每次新增几十条，突然新增上万条）
- 出现重定向到恶意 IP 的规则（hosts 格式中非 0.0.0.0/127.0.0.1 的目标）

#### 实现方案



```python
# src/adfilter/security/audit.py
@dataclass
class AuditPolicy:
    """安全审计策略"""
    # 关键域名保护列表（永远不应被阻断）
    protected_domains: frozenset[str]
    # 单源单次更新新增规则数上限
    max_new_rules_per_source: int = 5000
    # 单源单次更新新增规则占比上限
    max_new_rules_ratio: float = 0.5
    # hosts 格式中允许的目标 IP 白名单
    allowed_hosts_targets: frozenset[str] = frozenset({"0.0.0.0", "127.0.0.1", "::1"})
    # 可疑模式正则（如: 阻断整个 TLD）
    suspicious_patterns: list[re.Pattern]


class ContentAuditor:
    """规则内容安全审计器"""

    def __init__(self, policy: AuditPolicy, previous_state: BuildState | None = None):
        self.policy = policy
        self.previous = previous_state
        self._alerts: list[SecurityAlert] = []

    def audit_source(self, source_name: str, rules: list[Rule]) -> AuditResult:
        """审计单个源的规则集"""
        # 检查 1: 保护域名
        self._check_protected_domains(source_name, rules)
        # 检查 2: 数量异常
        self._check_volume_anomaly(source_name, rules)
        # 检查 3: hosts 目标 IP 安全
        self._check_hosts_targets(source_name, rules)
        # 检查 4: 可疑模式
        self._check_suspicious_patterns(source_name, rules)
        # 检查 5: 与上次构建的差异分析
        self._check_delta_anomaly(source_name, rules)

        return AuditResult(
            source=source_name,
            passed=not any(a.severity == "critical" for a in self._alerts),
            alerts=self._alerts.copy(),
        )

    def _check_protected_domains(self, source: str, rules: list[Rule]) -> None:
        """检测是否阻断了受保护的关键域名"""
        for rule in rules:
            if rule.target in self.policy.protected_domains:
                self._alerts.append(SecurityAlert(
                    severity="critical",
                    source=source,
                    message=f"尝试阻断受保护域名: {rule.target}",
                    rule=rule.origin,
                ))

    def _check_volume_anomaly(self, source: str, rules: list[Rule]) -> None:
        """检测规则数量异常激增"""
        if not self.previous:
            return
        prev_count = self.previous.get_rule_count(source)
        new_count = len(rules) - prev_count
        if new_count > self.policy.max_new_rules_per_source:
            self._alerts.append(SecurityAlert(
                severity="warning",
                source=source,
                message=f"新增规则异常: +{new_count} (阈值: {self.policy.max_new_rules_per_source})",
            ))
```

#### 配置

```yaml
security:
  audit:
    enable: true
    protected_domains_file: config/protected_domains.txt
    max_new_rules_per_source: 5000
    max_new_rules_ratio: 0.5
    on_critical: abort          # critical 级别告警时中断构建
    on_warning: notify          # warning 级别告警时通知但继续
    suspicious_patterns:
      - '^\w{1,2}\.\w{2,3}$'   # 疑似阻断整个短域名/TLD
```



#### 保护域名列表（内置默认）

```text
# config/protected_domains.txt — 关键基础设施域名
# 这些域名被阻断将导致严重的功能故障

# 搜索引擎
google.com
bing.com
baidu.com

# 开发平台
github.com
gitlab.com
stackoverflow.com

# 云服务
amazonaws.com
cloudflare.com
azure.com
googleapis.com

# 操作系统更新
windowsupdate.com
apple.com
download.microsoft.com

# CDN
cdn.jsdelivr.net
cdnjs.cloudflare.com
unpkg.com
```

#### 疑难点

1. **误报率控制**：过于严格会导致正常更新也触发告警。解决：引入"源信誉分"机制，高信誉源阈值放宽。
2. **增量状态存储**：需要持久化上一次构建的状态（规则数、哈希等）。方案：存储在 `.cache/audit_state.json`。
3. **性能影响**：审计逻辑在 parse 后、optimize 前执行，需确保不成为瓶颈。保护域名使用 frozenset O(1) 查找。

---

### 3. 供应链防护（Build Guard 增强）

#### 问题背景

现有 `build_guard.py` 已有基础检查，但需要增强为完整的供应链安全防线：
- 构建产物完整性校验
- 输出文件不应包含非预期内容
- 防止"投毒"规则通过构建管道进入发布

#### 实现方案

```python
# src/adfilter/security/supply_chain.py
class SupplyChainGuard:
    """构建供应链完整性守卫"""

    def pre_build_checks(self, config: AppConfig) -> list[GuardAlert]:
        """构建前检查"""
        alerts = []
        # 检查配置文件完整性（与上次 commit 对比）
        # 检查依赖是否被篡改（pip freeze hash 校验）
        # 检查运行环境安全（非 root、tmpdir 权限等）
        return alerts

    def post_build_checks(self, output_dir: Path, report: BuildReport) -> list[GuardAlert]:
        """构建后检查"""
        alerts = []
        # 输出文件大小合理性（不应比上次缩小超过 50% 或膨胀超过 200%）
        # 输出文件不包含可执行代码片段
        # 所有输出文件格式校验（clash.yaml 必须是合法 YAML 等）
        # 生成构建产物清单（SBOM-like manifest）
        return alerts

    def generate_manifest(self, output_dir: Path) -> BuildManifest:
        """生成构建产物清单"""
        manifest = BuildManifest(
            build_time=datetime.now(UTC).isoformat(),
            git_commit=get_git_sha(),
            files=[]
        )
        for f in output_dir.iterdir():
            if f.is_file():
                manifest.files.append(FileEntry(
                    name=f.name,
                    sha256=sha256_file(f),
                    size=f.stat().st_size,
                    line_count=count_lines(f),
                ))
        return manifest
```



#### 构建产物清单（Build Manifest）

每次构建在 release 分支额外生成 `manifest.json`：

```json
{
  "build_time": "2026-05-20T08:00:00Z",
  "git_commit": "abc1234",
  "adfilter_version": "0.5.0",
  "sources_fetched": 7,
  "sources_verified": 5,
  "audit_alerts": 0,
  "files": [
    {
      "name": "dns.txt",
      "sha256": "e3b0c44298fc...",
      "size": 1048576,
      "line_count": 98234,
      "rule_count": 95012
    }
  ]
}
```

用户可通过 `adfilter verify --manifest <url>` 校验本地下载的文件完整性。

---

### 4. GDPR / 隐私合规标签

#### 问题背景

企业用户在部署广告过滤时需要了解：
- 规则阻断了哪些类别的追踪器
- 是否符合所在地区的合规要求
- 如何向审计人员证明过滤行为的正当性

#### 实现方案

为每条规则引入分类标签：

```python
class RuleCategory(StrEnum):
    """规则分类标签"""
    ADS = "ads"                    # 广告
    TRACKING = "tracking"          # 用户追踪
    MALWARE = "malware"            # 恶意软件
    PHISHING = "phishing"          # 钓鱼
    SOCIAL_TRACKING = "social"     # 社交追踪（FB pixel 等）
    FINGERPRINT = "fingerprint"    # 浏览器指纹
    CRYPTOMINER = "cryptominer"    # 挖矿脚本
    ANNOYANCE = "annoyance"        # 烦扰元素（弹窗、通知请求）
    TELEMETRY = "telemetry"        # 遥测/诊断数据
```

#### 标签来源

| 标签方式 | 说明 |
|---------|------|
| 源级标签 | 整个源打标签（如 URLhaus → malware） |
| 规则级标签 | EasyList 分区注释提取（`! Title: EasyPrivacy` → tracking） |
| 智能推断 | 基于域名特征自动分类（含 `track`/`pixel`/`analytics` 的域名 → tracking） |



#### 按类别输出

```yaml
output:
  files:
    # 全量输出
    - { name: dns.txt, type: dns }
    # 仅恶意软件 + 钓鱼（企业安全场景）
    - { name: security-only.txt, type: dns, categories: [malware, phishing] }
    # 隐私保护（不含广告）
    - { name: privacy.txt, type: dns, categories: [tracking, social, fingerprint] }
    # 广告过滤（不含安全规则）
    - { name: ads-only.txt, type: dns, categories: [ads, annoyance] }
```

#### 合规报告

构建时可生成合规附录文档：

```markdown
# adfilter Compliance Report
Generated: 2026-05-20 08:00 UTC

## Rule Categories Breakdown
| Category      | Count  | Percentage |
|---------------|--------|-----------|
| Ads           | 45,230 | 47.6%     |
| Tracking      | 28,150 | 29.6%     |
| Malware       | 12,340 | 13.0%     |
| Phishing      |  5,210 |  5.5%     |
| Social        |  3,082 |  3.2%     |
| Other         |  1,000 |  1.1%     |

## Data Sources
All rules are sourced from community-maintained open-source filter lists.
No user browsing data is collected or transmitted.

## Blocking Mechanism
DNS-level blocking returns NXDOMAIN/0.0.0.0 for matched domains.
No traffic inspection or content modification is performed.
```

---

## v0.6.0 — 智能质量引擎

**目标时间**：v0.5.0 发布后 6-8 周
**核心目标**：从"机械聚合"升级为"智能评估"，构建规则源信誉体系和效率度量。

### 1. 规则源质量评分系统

#### 设计理念

类似 PageRank 思想：一条规则被越多高质量源同时收录，可信度越高；一个源包含越多"独占"且"被证实有效"的规则，评分越高。

#### 评分维度



```python
@dataclass
class SourceQualityScore:
    """规则源质量评分"""
    source_id: str
    overall_score: float          # 0.0 - 100.0 综合评分

    # 各维度分数
    freshness: float              # 更新时效性（最后更新距今时间）
    availability: float           # 可用性（过去30天成功拉取率）
    dead_domain_ratio: float      # 死链率（规则中已无法解析的域名占比）
    false_positive_rate: float    # 误杀率（命中受保护域名的规则占比）
    overlap_ratio: float          # 冗余率（与其他源重复规则的占比）
    unique_contribution: float    # 独占贡献率（只有该源提供的有效规则占比）
    stability: float              # 稳定性（每次更新变化幅度的方差）
    community_trust: float        # 社区信任度（GitHub stars、引用数等）

    @property
    def grade(self) -> str:
        """A/B/C/D/F 等级"""
        if self.overall_score >= 90: return "A"
        if self.overall_score >= 75: return "B"
        if self.overall_score >= 60: return "C"
        if self.overall_score >= 40: return "D"
        return "F"
```

#### 评分算法

```
overall_score = (
    freshness        * 0.15 +
    availability     * 0.20 +
    (1 - dead_ratio) * 0.15 +
    (1 - fp_rate)    * 0.20 +
    unique_contrib   * 0.15 +
    stability        * 0.10 +
    community_trust  * 0.05
) * 100
```

#### CLI 集成

```bash
# 查看所有源的质量评分
$ adfilter sources score

┌─────────────────┬───────┬───────┬───────┬───────┬───────┬───────┐
│ Source          │ Grade │ Avail │ Fresh │ Dead% │ FP%   │ Uniq% │
├─────────────────┼───────┼───────┼───────┼───────┼───────┼───────┤
│ anti-ad         │  A    │ 99.8% │ 2h    │ 1.2%  │ 0.0%  │ 34.5% │
│ easylist        │  A    │ 99.9% │ 6h    │ 2.1%  │ 0.1%  │ 28.2% │
│ peter-lowe      │  B    │ 98.5% │ 24h   │ 5.3%  │ 0.0%  │ 8.7%  │
│ urlhaus         │  B    │ 97.2% │ 1h    │ 8.7%  │ 0.0%  │ 45.1% │
│ phishing-army   │  C    │ 95.0% │ 48h   │ 12.4% │ 0.2%  │ 22.3% │
└─────────────────┴───────┴───────┴───────┴───────┴───────┴───────┘
```



#### 评分数据存储

```json
// .cache/source_scores.json — 持久化历史评分数据
{
  "version": 1,
  "last_updated": "2026-05-20T08:00:00Z",
  "history_window_days": 30,
  "scores": {
    "anti-ad": {
      "current_score": 92.5,
      "grade": "A",
      "trend": "+0.3",
      "fetch_history": [
        {"date": "2026-05-19", "success": true, "duration_ms": 1200},
        {"date": "2026-05-20", "success": true, "duration_ms": 980}
      ],
      "dead_domain_samples": ["old-tracker.defunct.com", "..."],
      "dimensions": { ... }
    }
  }
}
```

#### 与构建流程集成

- **自动降权**：评分低于 40 (D级) 的源在多源投票时权重减半
- **自动告警**：源评分下降超过 15 分触发通知
- **自动禁用**：连续 7 天不可达的源自动标记为 `disabled`，从构建中移除
- **报告集成**：`build-report.json` 中包含每个源的当次评分快照

#### 疑难点

1. **冷启动问题**：新添加的源没有历史数据。解决：首次评估给予"中立分"(60)，后续通过实际数据修正。
2. **DNS Probe 成本**：死链率检测需要大量 DNS 查询。解决：采样检测（每次只检查 10% 的随机域名），利用缓存积累完整画像。
3. **时间序列存储**：评分需要 30 天滑动窗口。方案：本地 JSON 文件足够（源数量 < 100），无需数据库。

---

### 2. 规则效率指标

#### 设计理念

一个好的规则集应该是"精炼"的——每条规则都应该实际发挥作用。指标帮助用户理解：
- 规则集的有效率是多少？
- 有多少"僵尸规则"（阻断的域名已经不存在了）？
- 与竞品相比，规则集的效率如何？

#### 效率指标定义



```python
@dataclass
class EfficiencyMetrics:
    """规则集效率指标"""
    total_rules: int              # 总规则数
    live_domains: int             # 域名仍可解析的规则数
    dead_domains: int             # 域名已死（NXDOMAIN）的规则数
    redundant_rules: int          # 被父域名规则覆盖的冗余子域名规则
    unique_rules: int             # 去重后的独立规则数

    @property
    def liveness_rate(self) -> float:
        """存活率：仍在线的域名占比"""
        return self.live_domains / self.total_rules if self.total_rules else 0

    @property
    def efficiency_score(self) -> float:
        """效率评分：有效且非冗余的规则占比"""
        effective = self.live_domains - self.redundant_rules
        return effective / self.total_rules if self.total_rules else 0

    @property
    def bloat_ratio(self) -> float:
        """膨胀率：无效规则占比（死链 + 冗余）"""
        return (self.dead_domains + self.redundant_rules) / self.total_rules
```

#### CLI 输出

```bash
$ adfilter stats --efficiency rule/build-report.json

╭──────────────── Rule Efficiency Report ─────────────────╮
│                                                         │
│  Total Rules:     95,012                                │
│  Live Domains:    87,234 (91.8%)  ████████████████░░    │
│  Dead Domains:     5,421 (5.7%)   █░░░░░░░░░░░░░░░░    │
│  Redundant:        2,357 (2.5%)   ░░░░░░░░░░░░░░░░░    │
│                                                         │
│  Efficiency Score: 89.3%  ⭐ Excellent                  │
│  Bloat Ratio:      8.2%                                 │
│                                                         │
│  💡 Tip: Run `adfilter optimize --prune-dead` to       │
│     remove 5,421 dead domain rules (-5.7% file size)   │
│                                                         │
╰─────────────────────────────────────────────────────────╯
```

#### 自动清理模式

```bash
# 移除死域名规则（生成精简版本）
adfilter optimize --prune-dead --input rule/dns.txt --output rule/dns-lean.txt

# 在构建配置中启用自动清理
# application.yaml
optimizer:
  prune_dead_domains: true
  dead_domain_probe_sample_rate: 0.1  # 每次采样 10% 检测
```

#### 效率追踪（趋势图数据）

每次构建将效率指标写入历史记录：

```json
// .cache/efficiency_history.json
{
  "history": [
    {"date": "2026-05-18", "total": 94800, "live": 87100, "dead": 5400, "efficiency": 0.891},
    {"date": "2026-05-19", "total": 94950, "live": 87200, "dead": 5380, "efficiency": 0.893},
    {"date": "2026-05-20", "total": 95012, "live": 87234, "dead": 5421, "efficiency": 0.893}
  ]
}
```

---

### 3. 源健康度仪表盘

#### 设计理念

将评分系统和效率指标整合为一个可视化仪表盘，以 JSON API + 静态 HTML 双形态提供。

#### API 端点

```
GET /api/health
GET /api/health/{source_id}
GET /api/efficiency
GET /api/trends?days=30
```



#### 静态报告（GitHub Pages 集成）

在 `release` 分支生成 `health.html`：

```
┌─────────────────────────────────────────────────────────────┐
│  adfilter Source Health Dashboard                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Overall Health: 🟢 92/100                                  │
│  Sources Active: 7/7  |  Last Build: 2h ago                │
│                                                             │
│  ┌─── Source Scores ────────────────────────────────────┐   │
│  │  🟢 anti-ad .......... A (92.5) ████████████████████ │   │
│  │  🟢 easylist ......... A (91.8) ████████████████████ │   │
│  │  🟢 easyprivacy ...... A (90.2) ████████████████████ │   │
│  │  🟡 peter-lowe ....... B (78.5) ████████████████░░░░ │   │
│  │  🟡 urlhaus .......... B (75.2) ███████████████░░░░░ │   │
│  │  🟡 adguard-dns ...... B (72.8) ███████████████░░░░░ │   │
│  │  🟠 phishing-army .... C (61.0) ████████████░░░░░░░░ │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─── Efficiency Trend (30 days) ───────────────────────┐   │
│  │  91% ─·─·─·─·─·─·─·─·─·─·─·─·─·─·─·─·─·─·─·─     │   │
│  │  89% ─────────────────────────────────────────────── │   │
│  │  87% ─────────────────────────────────────────────── │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 疑难点

1. **数据积累周期**：有意义的趋势需要至少 7 天数据。首次部署时显示 "Collecting data..."。
2. **GitHub Pages 限制**：只能提供静态内容。API 端点仅在 `adfilter serve` 模式下可用。
3. **数据隐私**：仪表盘不应暴露用户的自定义源 URL 或白名单内容。

---

## v0.7.0 — 开发者体验

**目标时间**：v0.6.0 发布后 6-8 周
**核心目标**：让 adfilter 不仅是一个 CLI 工具，更是一个开发者友好的平台。

### 1. adfilter playground — 交互式规则调试器

#### 设计理念

用户常见的问题是："为什么 xxx.com 被阻断了？" 或 "如果我添加这条规则会影响什么？"
Playground 提供即时反馈的调试体验。

#### 实现方案



```python
# src/adfilter/cli/playground.py
"""交互式规则调试器"""

class RuleDebugger:
    """加载已构建的规则集，提供实时查询"""

    def __init__(self, rule_dir: Path, config: AppConfig):
        self.trie = DomainTrie()
        self.rule_index: dict[str, list[RuleMatch]] = {}
        self._load_rules(rule_dir)

    def query(self, domain: str) -> QueryResult:
        """查询域名是否会被阻断，以及详细原因"""
        result = QueryResult(domain=domain, blocked=False)

        # 精确匹配
        if self.trie.contains(domain):
            result.blocked = True
            result.match_type = "exact"
            result.matching_rules = self.rule_index.get(domain, [])

        # 后缀匹配
        elif self.trie.matches(domain):
            parent = self.trie.find_parent(domain)
            result.blocked = True
            result.match_type = "suffix"
            result.matching_parent = parent
            result.matching_rules = self.rule_index.get(parent, [])

        # 填充规则来源信息
        for match in result.matching_rules:
            match.source_name = ...
            match.source_score = ...
            match.category = ...

        return result

    def what_if_add(self, rule: str) -> ImpactAnalysis:
        """模拟添加一条规则，分析影响范围"""
        ...

    def what_if_remove(self, domain: str) -> ImpactAnalysis:
        """模拟移除一条规则，分析会放行什么"""
        ...
```

#### CLI 交互模式

```bash
$ adfilter playground --rule-dir rule/

🎮 adfilter Playground (type 'help' for commands, 'quit' to exit)

> query ads.google.com
✅ BLOCKED
  Match type: suffix (parent: google.com... wait, not blocked)
  Actually: exact match on "ads.google.com"
  Sources:  anti-ad (A), easylist (A), adguard-dns (B)
  Category: ads
  Added:    2024-03-15 (via anti-ad)

> query github.com
🟢 NOT BLOCKED
  Protected: yes (in protected_domains.txt)

> whatif-add "tracker.example.com"
  Impact: would block 1 domain
  No conflicts with allowlist
  Similar existing rules: tracker.example.org, tracker2.example.com

> whatif-remove "ads.doubleclick.net"
  Impact: would unblock ads.doubleclick.net + 0 subdomains
  Warning: this domain appears in 4/7 sources (high confidence block)

> quit
```

#### 疑难点

1. **内存占用**：加载完整规则集到内存（10 万域名的 Trie）需要 ~50MB。对 CLI 可接受，Web 模式需要限制并发。
2. **规则溯源**：需要在构建时保留"每条规则来自哪个源"的映射。方案：构建时输出 `rule_origins.json` 索引文件。
3. **实时性**：Playground 使用的是上一次构建的快照，不实时反映正在进行的规则更新。

---

### 2. IDE / LSP 支持

#### 设计理念

`application.yaml` 是 adfilter 的核心配置文件，但目前编辑体验很差：
- 不知道有哪些合法字段
- 源名称需要记忆或查文档
- 配置错误只有运行时才发现

#### 实现方案

##### 方案 A：JSON Schema（低成本，高收益）

从 Pydantic model 自动导出 JSON Schema：

```python
# scripts/generate_schema.py
from adfilter.config import AppConfig
import json

schema = AppConfig.model_json_schema()

# 注入自定义元数据
schema["$schema"] = "http://json-schema.org/draft-07/schema#"
schema["title"] = "adfilter configuration"

with open("config/schema.json", "w") as f:
    json.dump(schema, f, indent=2)
```



用户在 VS Code 中配置 `yaml.schemas`：

```json
// .vscode/settings.json
{
  "yaml.schemas": {
    "./config/schema.json": "config/application*.yaml"
  }
}
```

即可获得：
- ✅ 字段自动补全
- ✅ 值域校验（如 `type` 字段只能是 12 种格式之一）
- ✅ 悬停文档
- ✅ 错误标红

##### 方案 B：Language Server（高成本，极致体验）

```python
# src/adfilter/lsp/server.py
"""adfilter YAML Language Server"""
from pygls.server import LanguageServer

class AdfilterLanguageServer(LanguageServer):
    """为 application.yaml 提供智能编辑支持"""

    def completion(self, params) -> list[CompletionItem]:
        # 源名称补全（从 source_catalog.yaml 读取）
        # 格式类型补全（dns, clash, surge, ...）
        # 配置路径补全
        ...

    def diagnostics(self, params) -> list[Diagnostic]:
        # 实时配置校验
        # URL 可达性检查（后台异步）
        # 源名称拼写检查
        ...

    def hover(self, params) -> Hover:
        # 源名称 → 显示源描述、URL、评分
        # 格式类型 → 显示兼容应用列表
        ...
```

#### 优先级建议

先实现方案 A（JSON Schema），投入 1-2 天即可获得 80% 的体验提升。
方案 B 作为 v1.0 长期目标。

---

### 3. WebAssembly 在线转换工具

#### 设计理念

用户想快速将一份规则文件从 hosts 格式转为 clash 格式，但不想安装 Python 和 adfilter。
一个纯浏览器端的转换工具可以零门槛使用。

#### 技术方案

```
┌─────────────────────────────────────────────────────┐
│  浏览器                                              │
│                                                     │
│  ┌─────────────────────┐    ┌──────────────────┐    │
│  │  用户粘贴/上传规则   │───▶│  Pyodide (WASM)  │    │
│  │  选择目标格式        │    │  运行 adfilter   │    │
│  │                     │◀───│  parse+format    │    │
│  │  输出转换结果        │    └──────────────────┘    │
│  └─────────────────────┘                            │
│                                                     │
│  零服务器、零安装、纯客户端                            │
└─────────────────────────────────────────────────────┘
```

#### 实现步骤

1. **精简核心模块**：提取 `handler/` + `model.py` + `optimizer.py` 为无外部依赖的子包
2. **Pyodide 打包**：将精简包通过 Pyodide 加载到浏览器 (`micropip.install`)
3. **前端 UI**：单页应用（Vue/Svelte/纯 HTML），提供：
   - 输入框（粘贴/文件上传）
   - 格式选择器（from → to）
   - 输出区域（带语法高亮 + 复制按钮 + 下载按钮）
   - 转换统计（处理行数、有效规则数、耗时）

#### 替代方案：Rust 核心 + WASM

如果性能要求高（如处理 50 万行规则），可以将核心的 parse/format 用 Rust 重写：

```rust
// adfilter-core/src/lib.rs
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub fn convert(input: &str, from_format: &str, to_format: &str) -> String {
    let rules = parse(input, from_format);
    format_rules(&rules, to_format)
}
```

性能预估：Rust WASM 方案处理 10 万行 < 100ms，Pyodide 方案 < 2s。

#### 疑难点

1. **依赖精简**：核心功能不应依赖 `aiohttp`、`typer` 等重型库。需要拆分为 `adfilter-core`（纯逻辑）和 `adfilter`（CLI + IO）。
2. **Pyodide 包大小**：Pyodide 运行时 ~10MB，首次加载较慢。方案：使用 Service Worker 缓存。
3. **格式兼容性**：浏览器环境无文件系统，需要全部通过字符串 IO。

---



## v1.0.0 — 生产就绪

**目标时间**：v0.7.0 发布后 8-12 周
**核心目标**：整合所有安全、质量、体验特性，达到企业级部署标准。

### 核心交付物

| 特性 | 描述 |
|------|------|
| 全链路安全审计 | 从拉取到发布的每一步都有安全检查和审计日志 |
| 合规标签体系 | 所有规则分类标注，支持按类别输出和合规报告 |
| 企业级部署 | Helm Chart + RBAC + 审计日志 + 秘钥管理集成 |
| PyPI 稳定发布 | 语义版本、自动 changelog、Trusted Publisher |
| 性能基线 | 标准化 benchmark，每次发布附带性能报告 |
| 文档站点 | MkDocs Material 驱动的完整文档 + 在线转换工具 |

### 安全成熟度矩阵

```
Level 1 (v0.4 当前):
  ✅ SSRF 防护
  ✅ 非 root Docker
  ✅ 基础 build guard

Level 2 (v0.5 目标):
  ⬜ 规则源签名验证
  ⬜ 内容安全审计
  ⬜ 供应链防护 + 构建清单
  ⬜ GDPR 合规标签

Level 3 (v1.0 目标):
  ⬜ 端到端签名链（源 → 构建 → 发布）
  ⬜ 构建可重现性（reproducible builds）
  ⬜ 安全事件响应自动化
  ⬜ 第三方安全审计报告
```

### 企业部署增强

```yaml
# charts/adfilter/values.yaml 增强
security:
  podSecurityContext:
    runAsNonRoot: true
    seccompProfile:
      type: RuntimeDefault
  rbac:
    create: true
    rules:
      - apiGroups: [""]
        resources: ["configmaps", "secrets"]
        verbs: ["get", "list"]

audit:
  enable: true
  storage: persistent    # 审计日志持久化
  retention_days: 90
  export:
    type: syslog         # 支持 syslog / elasticsearch / loki
    endpoint: "..."

secrets:
  provider: vault        # 支持 vault / aws-secrets-manager / k8s-secrets
  path: "secret/adfilter"
```

---

## 设计原则

贯穿所有版本迭代的设计原则：

### 1. 安全优先（Security First）

```
永远假设输入不可信：
  - 规则源内容可能被篡改
  - 配置文件可能包含注入
  - 用户输入可能触发路径遍历
  - 网络请求可能被重定向到内网

防御策略：
  - 输入验证在最外层
  - 权限最小化（non-root、只读挂载）
  - 失败安全（验签失败 → 拒绝，而非忽略）
  - 审计可追溯（每个操作有日志）
```

### 2. 渐进式安全（Progressive Security）

```
不强制所有用户承担安全成本：
  - 签名验证默认关闭，enable: true 开启
  - 内容审计默认 warning 级别，不中断构建
  - 保护域名列表可自定义增减
  - 企业特性通过配置层层递进
```

### 3. 可观测性（Observability）

```
每个决策都应该可解释：
  - 为什么这条规则被保留/丢弃？
  - 为什么这个源被降权？
  - 为什么这次构建比上次多了 5000 条规则？
  - Playground 提供完整的决策链路追溯
```



### 4. 开发者友好（Developer-First）

```
降低使用门槛，提升反馈速度：
  - JSON Schema 让编辑器"懂"配置文件
  - Playground 让调试零延迟
  - WASM 转换让试用零安装
  - 清晰的错误消息指向修复方案
```

---

## 里程碑时间线

```
2026 Q2          Q3                Q4              2027 Q1
  │               │                 │               │
  ▼               ▼                 ▼               ▼
v0.5.0          v0.6.0            v0.7.0          v1.0.0
安全基建        智能质量引擎      开发者体验      生产就绪
4-6 周          6-8 周            6-8 周          8-12 周
  │               │                 │               │
  ├─签名验证      ├─质量评分        ├─Playground    ├─全链路审计
  ├─内容审计      ├─效率指标        ├─JSON Schema   ├─合规标签 v2
  ├─供应链防护    ├─健康仪表盘      ├─WASM 转换     ├─企业 Helm
  └─合规标签      └─自动降权        └─LSP 原型      └─文档站点
```

---

## 版本间依赖关系

```
v0.5.0 (安全基建)
  │
  │  提供: 签名验证框架、审计策略引擎、保护域名机制
  │
  ▼
v0.6.0 (智能质量引擎)
  │  依赖: 利用审计框架的"保护域名"计算误杀率
  │  依赖: 利用供应链防护的"历史状态"计算变化趋势
  │
  │  提供: 源评分数据、效率指标、规则溯源索引
  │
  ▼
v0.7.0 (开发者体验)
  │  依赖: Playground 使用评分数据展示源可信度
  │  依赖: Playground 使用规则溯源索引实现 query
  │  依赖: JSON Schema 从 Pydantic model 导出
  │
  │  提供: 交互式验证能力、在线转换、配置编辑增强
  │
  ▼
v1.0.0 (生产就绪)
     整合所有能力，面向企业级场景打磨
```

---

## 技术选型参考

| 组件 | 选型 | 理由 |
|------|------|------|
| 签名算法 | Ed25519 | 快速、签名短（64 bytes）、无专利 |
| 签名库 | `cryptography` | Python 生态标准、已审计 |
| JSON Schema | Pydantic `.model_json_schema()` | 零额外依赖、与配置模型同源 |
| WASM 运行时 | Pyodide 0.26+ | 成熟、支持 micropip、社区活跃 |
| 效率检测 DNS | `aiodns` (已有依赖) | 异步、高并发、可复用 |
| 仪表盘 | 静态 HTML + Chart.js (CDN) | 零构建、GitHub Pages 兼容 |
| 审计日志 | JSON Lines (`.jsonl`) | 可追加、可 grep、可对接 ELK |

---

## 社区贡献指南

### 如何参与各阶段开发

| 阶段 | 适合的贡献方式 |
|------|---------------|
| v0.5 安全 | 提交保护域名列表、测试 SSRF 边界、审计策略 review |
| v0.6 质量 | 提供规则源可用性数据、DNS 探测基础设施优化 |
| v0.7 体验 | UI 设计、前端开发（WASM 工具）、LSP 协议实现 |
| 全阶段 | 文档翻译、Bug 报告、性能测试、安全审计 |

### Issue 标签体系

```
area/security     - 安全相关
area/quality      - 质量评估相关
area/dx           - 开发者体验相关
priority/critical - 安全漏洞，立即修复
priority/high     - 核心功能阻塞
priority/medium   - 版本目标内
priority/low      - Nice to have
good-first-issue  - 适合新贡献者
help-wanted       - 需要社区帮助
```

---

> **贡献**：欢迎通过 Issue 讨论优先级或提出新的方向建议。
>
> **许可**：本文档随项目采用 MIT 许可。
