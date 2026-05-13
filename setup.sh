#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# adfilter 一键安装 & 个性化配置脚本
# 支持: Linux / macOS / WSL
#
# 功能:
#   1. 安装 uv + adfilter
#   2. 交互式选择规则源
#   3. 交互式配置白名单
#   4. 选择输出格式
#   5. 可选配置定时任务 (cron)
#   6. 首次构建规则
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

# ─── 颜色 ─────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ─── 检测环境 ─────────────────────────────────────────────────────
check_prerequisites() {
    info "检测系统环境..."

    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        err "此脚本不支持原生 Windows，请使用 WSL 或 Docker"
        exit 1
    fi

    # 检测 curl 或 wget
    if ! command -v curl &>/dev/null && ! command -v wget &>/dev/null; then
        err "需要 curl 或 wget，请先安装"
        exit 1
    fi

    # 检测 git
    if ! command -v git &>/dev/null; then
        err "需要 git，请先安装: https://git-scm.com/downloads"
        exit 1
    fi

    ok "环境检测通过"
}

# ─── 安装 uv ──────────────────────────────────────────────────────
install_uv() {
    if command -v uv &>/dev/null; then
        ok "uv 已安装: $(uv --version)"
        return
    fi

    info "安装 uv (Python 包管理器)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # 加载 PATH
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

    if command -v uv &>/dev/null; then
        ok "uv 安装成功: $(uv --version)"
    else
        err "uv 安装失败，请手动安装: https://docs.astral.sh/uv/"
        exit 1
    fi
}

# ─── 克隆项目 ─────────────────────────────────────────────────────
setup_project() {
    local install_dir="${1:-$HOME/adfilter}"

    echo ""
    echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}     adfilter 一键安装 & 个性化配置${NC}"
    echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
    echo ""

    read -rp "$(echo -e ${BLUE}安装目录${NC} [$install_dir]: )" user_dir
    install_dir="${user_dir:-$install_dir}"

    if [[ -d "$install_dir/.git" ]]; then
        info "检测到已有安装，更新中..."
        git -C "$install_dir" pull --ff-only 2>/dev/null || true
    else
        info "克隆 adfilter 到 $install_dir ..."
        git clone --depth=1 https://github.com/Lknife666/adfilter.git "$install_dir"
    fi

    cd "$install_dir"
    ok "项目就绪: $install_dir"
}

# ─── 安装依赖 ─────────────────────────────────────────────────────
install_deps() {
    info "安装 Python 依赖..."
    uv python install 3.14 2>/dev/null || uv python install 3.13 2>/dev/null || uv python install 3.12
    uv sync --frozen --no-dev 2>/dev/null || uv sync --no-dev
    ok "依赖安装完成"
}

# ─── 选择规则源 ───────────────────────────────────────────────────
declare -A SOURCES
select_sources() {
    echo ""
    echo -e "${CYAN}────────────── 选择规则源 ──────────────${NC}"
    echo ""
    echo "可用的规则源（输入序号，多个用空格分隔）:"
    echo ""
    echo -e "  ${GREEN}[广告拦截]${NC}"
    echo "  1) anti-AD          — 中国最流行的广告过滤列表（推荐）"
    echo "  2) EasyList         — ABP 官方广告列表"
    echo "  3) EasyList China   — EasyList 中国区补充"
    echo "  4) Peter Lowe       — 轻量级广告服务器列表"
    echo ""
    echo -e "  ${GREEN}[隐私防护]${NC}"
    echo "  5) EasyPrivacy      — ABP 官方隐私追踪列表（推荐）"
    echo ""
    echo -e "  ${GREEN}[安全防护]${NC}"
    echo "  6) URLhaus          — 恶意软件域名"
    echo "  7) Phishing Army    — 钓鱼网站"
    echo ""
    echo -e "  ${GREEN}[地区专用]${NC}"
    echo "  8) CJX Annoyance   — 中文烦人元素"
    echo "  9) 280blocker       — 日本广告列表"
    echo ""
    echo -e "  ${YELLOW}推荐中国用户选择: 1 3 5${NC}"
    echo -e "  ${YELLOW}推荐国际用户选择: 2 5 6${NC}"
    echo ""

    read -rp "$(echo -e ${BLUE}请输入序号${NC} [默认: 1 3 5]: )" choices
    choices="${choices:-1 3 5}"

    SELECTED_SOURCES=()
    for c in $choices; do
        case $c in
            1) SELECTED_SOURCES+=("anti-ad|easylist|https://anti-ad.net/easylist.txt") ;;
            2) SELECTED_SOURCES+=("easylist|easylist|https://easylist.to/easylist/easylist.txt") ;;
            3) SELECTED_SOURCES+=("easylist-china|easylist|https://easylist-downloads.adblockplus.org/easylistchina.txt") ;;
            4) SELECTED_SOURCES+=("peter-lowe|hosts|https://pgl.yoyo.org/adservers/serverlist.php?hostformat=hosts&showintro=0&mimetype=plaintext") ;;
            5) SELECTED_SOURCES+=("easyprivacy|easylist|https://easylist.to/easylist/easyprivacy.txt") ;;
            6) SELECTED_SOURCES+=("urlhaus|hosts|https://urlhaus.abuse.ch/downloads/hostfile/") ;;
            7) SELECTED_SOURCES+=("phishing-army|easylist|https://phishing.army/download/phishing_army_blocklist.txt") ;;
            8) SELECTED_SOURCES+=("cjx-annoyance|easylist|https://raw.githubusercontent.com/cjx82630/cjxlist/master/cjx-annoyance.txt") ;;
            9) SELECTED_SOURCES+=("280blocker|easylist|https://280blocker.net/files/280blocker_adblock.txt") ;;
            *) warn "未知选项: $c，已跳过" ;;
        esac
    done

    ok "已选择 ${#SELECTED_SOURCES[@]} 个规则源"
}

# ─── 选择输出格式 ─────────────────────────────────────────────────
select_outputs() {
    echo ""
    echo -e "${CYAN}────────────── 选择输出格式 ──────────────${NC}"
    echo ""
    echo "你的工具需要哪些格式？（输入序号，多个用空格分隔）:"
    echo ""
    echo "  1) AdGuard Home DNS   (dns.txt)"
    echo "  2) EasyList / ABP     (easylist.txt)"
    echo "  3) Clash              (clash.yaml)"
    echo "  4) sing-box           (singbox.json)"
    echo "  5) Surge              (surge.conf)"
    echo "  6) Quantumult X       (quantumult.conf)"
    echo "  7) Loon               (loon.conf)"
    echo "  8) dnsmasq            (dnsmasq.conf)"
    echo "  9) SmartDNS           (smartdns.conf)"
    echo " 10) hosts              (hosts.txt)"
    echo " 11) MikroTik           (mikrotik.rsc)"
    echo " 12) Unbound            (unbound.conf)"
    echo ""
    echo -e "  ${YELLOW}全部输出: all${NC}"
    echo ""

    read -rp "$(echo -e ${BLUE}请输入序号${NC} [默认: all]: )" fmt_choices
    fmt_choices="${fmt_choices:-all}"

    SELECTED_OUTPUTS=()
    if [[ "$fmt_choices" == "all" ]]; then
        SELECTED_OUTPUTS=(
            "dns.txt|dns|AdGuard Home DNS"
            "easylist.txt|easylist|EasyList / ABP"
            "clash.yaml|clash|Clash"
            "singbox.json|singbox|sing-box rule-set"
            "surge.conf|surge|Surge"
            "quantumult.conf|quantumult|Quantumult X"
            "loon.conf|loon|Loon"
            "dnsmasq.conf|dnsmasq|dnsmasq"
            "smartdns.conf|smartdns|SmartDNS"
            "hosts.txt|hosts|hosts"
            "mikrotik.rsc|mikrotik|MikroTik"
            "unbound.conf|unbound|Unbound"
        )
    else
        for c in $fmt_choices; do
            case $c in
                1)  SELECTED_OUTPUTS+=("dns.txt|dns|AdGuard Home DNS") ;;
                2)  SELECTED_OUTPUTS+=("easylist.txt|easylist|EasyList / ABP") ;;
                3)  SELECTED_OUTPUTS+=("clash.yaml|clash|Clash") ;;
                4)  SELECTED_OUTPUTS+=("singbox.json|singbox|sing-box rule-set") ;;
                5)  SELECTED_OUTPUTS+=("surge.conf|surge|Surge") ;;
                6)  SELECTED_OUTPUTS+=("quantumult.conf|quantumult|Quantumult X") ;;
                7)  SELECTED_OUTPUTS+=("loon.conf|loon|Loon") ;;
                8)  SELECTED_OUTPUTS+=("dnsmasq.conf|dnsmasq|dnsmasq") ;;
                9)  SELECTED_OUTPUTS+=("smartdns.conf|smartdns|SmartDNS") ;;
                10) SELECTED_OUTPUTS+=("hosts.txt|hosts|hosts") ;;
                11) SELECTED_OUTPUTS+=("mikrotik.rsc|mikrotik|MikroTik") ;;
                12) SELECTED_OUTPUTS+=("unbound.conf|unbound|Unbound") ;;
                *)  warn "未知选项: $c，已跳过" ;;
            esac
        done
    fi

    ok "已选择 ${#SELECTED_OUTPUTS[@]} 种输出格式"
}

# ─── 配置白名单 ───────────────────────────────────────────────────
configure_allowlist() {
    echo ""
    echo -e "${CYAN}────────────── 配置白名单 ──────────────${NC}"
    echo ""
    echo "白名单中的域名不会被屏蔽。"
    echo "输入需要放行的域名（每行一个，输入空行结束）:"
    echo -e "${YELLOW}  示例: mybank.com${NC}"
    echo ""

    mkdir -p config
    : > config/allowlist.txt

    while true; do
        read -rp "  域名 (回车结束): " domain
        if [[ -z "$domain" ]]; then
            break
        fi
        echo "$domain" >> config/allowlist.txt
    done

    local count
    count=$(wc -l < config/allowlist.txt | tr -d ' ')
    if [[ "$count" -gt 0 ]]; then
        ok "白名单已保存: $count 个域名"
    else
        info "白名单为空（可以之后编辑 config/allowlist.txt）"
    fi
}

# ─── 生成配置文件 ─────────────────────────────────────────────────
generate_config() {
    info "生成配置文件 config/application.yaml ..."

    mkdir -p config

    cat > config/application.yaml << 'HEADER'
# ─── adfilter 个性化配置 ───
# 由 setup.sh 自动生成，你可以随时手动修改
application:
  config:
    input:
      rule:
        default:
HEADER

    # 写入规则源
    for src in "${SELECTED_SOURCES[@]}"; do
        IFS='|' read -r name type url <<< "$src"
        cat >> config/application.yaml << EOF
          - name: "$name"
            type: $type
            path: "$url"
EOF
    done

    # 白名单
    cat >> config/application.yaml << 'EOF'

      allowlist:
        - path: config/allowlist.txt

    output:
      path: ./rule
      file_header: |
        ADFS AdBlock ${type}
        Last Modified: ${date}
        Total Size: ${total}
      files:
EOF

    # 写入输出文件
    for out in "${SELECTED_OUTPUTS[@]}"; do
        IFS='|' read -r fname ftype fdesc <<< "$out"
        echo "        - { name: \"$fname\", type: $ftype, desc: \"$fdesc\" }" >> config/application.yaml
    done

    # 优化器
    cat >> config/application.yaml << 'EOF'

    optimizer:
      enable: true
      collapse_subdomains: true
      drop_allow_shadowed_deny: true
      normalize_idn: true
      min_source_votes: 1

    fetcher:
      http:
        timeout_seconds: 60
        max_retries: 3
        max_concurrency: 8
        on_failure: cache_then_skip
        cache_dir: .cache/http
        max_cache_age_hours: 72
EOF

    ok "配置文件已生成: config/application.yaml"
}

# ─── 首次构建 ─────────────────────────────────────────────────────
first_build() {
    echo ""
    read -rp "$(echo -e ${BLUE}立即执行首次构建？${NC} [Y/n]: )" do_build
    do_build="${do_build:-Y}"

    if [[ "${do_build,,}" == "y" ]]; then
        info "正在构建规则..."
        uv run adfilter run --config config/application.yaml --progress --report rule/build-report.json
        echo ""
        ok "构建完成！规则文件在 ./rule/ 目录下："
        ls -lh rule/ 2>/dev/null || true
    fi
}

# ─── 配置定时任务 ─────────────────────────────────────────────────
setup_cron() {
    echo ""
    echo -e "${CYAN}────────────── 定时自动更新 ──────────────${NC}"
    echo ""
    echo "是否配置定时任务（cron），自动更新规则？"
    echo ""
    echo "  1) 每 8 小时更新一次（推荐）"
    echo "  2) 每天凌晨 3 点更新"
    echo "  3) 每 4 小时更新一次"
    echo "  4) 不配置定时任务"
    echo ""

    read -rp "$(echo -e ${BLUE}选择${NC} [默认: 1]: )" cron_choice
    cron_choice="${cron_choice:-1}"

    local cron_expr
    case $cron_choice in
        1) cron_expr="0 */8 * * *" ;;
        2) cron_expr="0 3 * * *" ;;
        3) cron_expr="0 */4 * * *" ;;
        4) info "跳过定时任务配置"; return ;;
        *) info "跳过定时任务配置"; return ;;
    esac

    local project_dir
    project_dir="$(pwd)"
    local uv_path
    uv_path="$(command -v uv)"
    local cron_cmd="$cron_expr $uv_path run --project $project_dir adfilter run --config $project_dir/config/application.yaml --report $project_dir/rule/build-report.json"

    # 检查是否已有 adfilter cron
    if crontab -l 2>/dev/null | grep -q "adfilter"; then
        warn "检测到已有 adfilter 定时任务，将替换..."
        crontab -l 2>/dev/null | grep -v "adfilter" | crontab -
    fi

    # 添加 cron
    (crontab -l 2>/dev/null; echo "$cron_cmd  # adfilter auto-update") | crontab -

    ok "定时任务已配置: $cron_expr"
    info "查看当前 cron: crontab -l"
    info "删除定时任务: crontab -l | grep -v adfilter | crontab -"
}

# ─── HTTP 服务提示 ────────────────────────────────────────────────
show_serve_hint() {
    echo ""
    echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  安装完成！${NC}"
    echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "规则文件目录: $(pwd)/rule/"
    echo ""
    echo "如需在局域网提供 HTTP 订阅服务:"
    echo -e "  ${YELLOW}uv run adfilter serve --dir rule/ --host 0.0.0.0 --port 8787${NC}"
    echo ""
    echo "然后其他设备可通过以下地址订阅:"
    echo "  http://你的IP:8787/dns.txt"
    echo "  http://你的IP:8787/clash.yaml"
    echo "  ..."
    echo ""
    echo "更多用法请参考: https://github.com/Lknife666/adfilter"
    echo ""
}

# ─── 主流程 ───────────────────────────────────────────────────────
main() {
    check_prerequisites
    install_uv
    setup_project "$@"
    install_deps
    select_sources
    select_outputs
    configure_allowlist
    generate_config
    first_build
    setup_cron
    show_serve_hint
}

main "$@"
