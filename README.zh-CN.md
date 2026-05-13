# adfilter 中文使用指南

> **English version**: [README.md](README.md)

<p align="center">
  <strong>广告过滤规则聚合器 & 多格式转换工具</strong><br>
  抓取、解析、去重、优化广告屏蔽规则，输出 12 种格式。
</p>

---

## 目录

- [规则订阅](#规则订阅)
- [快速上手](#快速上手)
- [白名单（Allowlist）](#白名单allowlist)
- [常见问题 / FAQ](#常见问题--faq)

---

## 规则订阅

> 规则每 **8 小时** 通过 GitHub Actions 自动更新，发布到 [`release`](https://github.com/Lknife666/adfilter/tree/release) 分支。

| 格式 | 适用工具 | 订阅链接 |
|------|---------|---------|
| AdGuard Home DNS | AdGuard Home, AdGuard DNS | [`dns.txt`](https://raw.githubusercontent.com/Lknife666/adfilter/release/dns.txt) |
| EasyList / ABP | Adblock Plus, uBlock Origin, AdGuard 扩展 | [`easylist.txt`](https://raw.githubusercontent.com/Lknife666/adfilter/release/easylist.txt) |
| Clash | Clash, Clash Meta, Stash | [`clash.yaml`](https://raw.githubusercontent.com/Lknife666/adfilter/release/clash.yaml) |
| sing-box | sing-box rule-set (v2) | [`singbox.json`](https://raw.githubusercontent.com/Lknife666/adfilter/release/singbox.json) |
| Surge | Surge, Shadowrocket, Stash | [`surge.conf`](https://raw.githubusercontent.com/Lknife666/adfilter/release/surge.conf) |
| Quantumult X | Quantumult X | [`quantumult.conf`](https://raw.githubusercontent.com/Lknife666/adfilter/release/quantumult.conf) |
| Loon | Loon | [`loon.conf`](https://raw.githubusercontent.com/Lknife666/adfilter/release/loon.conf) |
| dnsmasq | dnsmasq, OpenWrt | [`dnsmasq.conf`](https://raw.githubusercontent.com/Lknife666/adfilter/release/dnsmasq.conf) |
| smartdns | SmartDNS | [`smartdns.conf`](https://raw.githubusercontent.com/Lknife666/adfilter/release/smartdns.conf) |
| hosts | 所有操作系统, Pi-hole | [`hosts.txt`](https://raw.githubusercontent.com/Lknife666/adfilter/release/hosts.txt) |
| MikroTik | MikroTik RouterOS v6/v7 | [`mikrotik.rsc`](https://raw.githubusercontent.com/Lknife666/adfilter/release/mikrotik.rsc) |
| Unbound | Unbound DNS resolver | [`unbound.conf`](https://raw.githubusercontent.com/Lknife666/adfilter/release/unbound.conf) |

> **使用方法**：复制对应的订阅链接，粘贴到你的广告屏蔽工具的订阅设置中即可。

---

## 快速上手

### 你属于哪类用户？

| 我的需求 | 推荐方案 | 难度 |
|---------|---------|------|
| 只想用现成的规则，不想折腾 | 直接复制上方 [规则订阅](#规则订阅) 表格中的链接到你的工具即可，**不需要安装任何东西** | 零门槛 |
| 想自定义规则源（选择屏蔽哪些列表） | 用 Docker 一键部署，修改配置文件 | 简单 |
| 想深度定制、二次开发 | 从源码安装 | 需要 Python 基础 |

---

### 方案一：直接使用现成规则（推荐大多数用户）

你不需要安装任何东西！只需要：

1. 找到上方 [规则订阅](#规则订阅) 表格
2. 根据你使用的工具，复制对应的订阅链接
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

### 方案二：Docker 部署（自定义规则源）

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

如果有不想被屏蔽的域名，每行写一个（详见 [白名单](#白名单allowlist) 章节）。

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

### 方案三：从源码安装（高级用户）

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

## 白名单（Allowlist）

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

## 常见问题 / FAQ

### Q: 运行报错 "Connection timeout" 或 "Failed to fetch"

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

### Q: 生成的规则文件是空的 / 规则数量为 0

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

### Q: 某个正常网站被误杀了，打不开

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

详见 [白名单](#白名单allowlist) 章节。

---

### Q: Docker 容器起不来 / 报错退出

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

### Q: 配置文件 YAML 格式报错

**常见错误：**
- 缩进不一致（YAML 必须用空格，不能用 Tab）
- 冒号后面少了空格（正确: `name: value`，错误: `name:value`）
- 特殊字符没有加引号

**建议：** 使用在线 YAML 校验工具（如 [yamllint.com](https://www.yamllint.com/)）检查格式，或者运行：

```bash
uv run adfilter validate --config config/application.yaml
```

---

### Q: 怎么知道一共生成了多少条规则？

```bash
# 方法 1: 使用 stats 命令
uv run adfilter run --config config/application.yaml --report rule/build-report.json
uv run adfilter stats rule/build-report.json

# 方法 2: 直接数行数
wc -l rule/*.txt rule/*.yaml rule/*.conf
```

---

### Q: 如何定时自动更新规则？

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

本项目已配置每 8 小时自动更新，直接订阅 [规则订阅](#规则订阅) 中的链接即可，无需自建。

---

### Q: `uv` 安装失败 / 命令找不到

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

### Q: 局域网其他设备怎么访问我 serve 的规则？

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

### Q: Python 版本要求 3.14+，我装不了怎么办？

推荐使用 Docker 方式运行，无需关心 Python 版本。如果一定要从源码安装：

```bash
# 使用 uv 自动管理 Python 版本（推荐）
uv python install 3.14
uv sync

# 或者使用 pyenv
pyenv install 3.14.0
pyenv local 3.14.0
```
