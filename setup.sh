#!/usr/bin/env bash
# setup.sh — Interactive local setup for adfilter
# Generates config/application.yaml based on user preferences
set -euo pipefail

CONFIG_DIR="config"
CONFIG_FILE="$CONFIG_DIR/application.yaml"

echo "╔══════════════════════════════════════════════╗"
echo "║       adfilter — Interactive Setup           ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ── Step 1: Rule source selection ────────────────────────────────────
echo "Step 1: Select rule sources"
echo "─────────────────────────────────────────────"
echo "  1) China (anti-ad, easylist-china, cjx-annoyance)"
echo "  2) Japan (280blocker, easylist)"
echo "  3) Global (easylist, easyprivacy, peter-lowe)"
echo "  4) Custom (manual configuration later)"
echo ""
read -rp "Choose preset [1-4, default=3]: " SOURCE_CHOICE
SOURCE_CHOICE="${SOURCE_CHOICE:-3}"

case "$SOURCE_CHOICE" in
  1) PRESET="cn" ;;
  2) PRESET="jp" ;;
  3) PRESET="global" ;;
  4) PRESET="custom" ;;
  *) echo "Invalid choice, using global."; PRESET="global" ;;
esac
echo "→ Selected: $PRESET"
echo ""

# ── Step 2: Output format selection ──────────────────────────────────
echo "Step 2: Select output formats"
echo "─────────────────────────────────────────────"
echo "  Available: dns, easylist, clash, singbox, surge, quantumult,"
echo "             loon, dnsmasq, smartdns, hosts, mikrotik, unbound"
echo ""
read -rp "Formats (comma-separated, default=dns,clash,hosts,surge): " FORMATS_INPUT
FORMATS_INPUT="${FORMATS_INPUT:-dns,clash,hosts,surge}"

IFS=',' read -ra FORMATS <<< "$FORMATS_INPUT"
echo "→ Selected formats: ${FORMATS[*]}"
echo ""

# ── Step 3: Allowlist configuration ──────────────────────────────────
echo "Step 3: Configure allowlist"
echo "─────────────────────────────────────────────"
read -rp "Create allowlist file? [Y/n]: " ALLOWLIST_CHOICE
ALLOWLIST_CHOICE="${ALLOWLIST_CHOICE:-Y}"

ALLOWLIST_ENABLED=false
if [[ "$ALLOWLIST_CHOICE" =~ ^[Yy] ]]; then
  ALLOWLIST_ENABLED=true
  mkdir -p "$CONFIG_DIR"
  if [[ ! -f "$CONFIG_DIR/allowlist.txt" ]]; then
    cat > "$CONFIG_DIR/allowlist.txt" <<'ALLOWEOF'
# adfilter allowlist — one domain per line
# Lines starting with # are comments
# Each domain also matches all subdomains (suffix matching)
#
# Example:
# example.com
# *.internal.company.net
ALLOWEOF
    echo "→ Created $CONFIG_DIR/allowlist.txt (edit to add your domains)"
  else
    echo "→ $CONFIG_DIR/allowlist.txt already exists, keeping it"
  fi
fi
echo ""

# ── Step 4: Cron setup ───────────────────────────────────────────────
echo "Step 4: Schedule automatic updates"
echo "─────────────────────────────────────────────"
echo "  1) Every 8 hours (recommended)"
echo "  2) Every 12 hours"
echo "  3) Daily"
echo "  4) Skip (manual only)"
echo ""
read -rp "Choose schedule [1-4, default=1]: " CRON_CHOICE
CRON_CHOICE="${CRON_CHOICE:-1}"

CRON_EXPR=""
case "$CRON_CHOICE" in
  1) CRON_EXPR="0 */8 * * *" ;;
  2) CRON_EXPR="0 */12 * * *" ;;
  3) CRON_EXPR="0 4 * * *" ;;
  4) CRON_EXPR="" ;;
  *) CRON_EXPR="0 */8 * * *" ;;
esac

if [[ -n "$CRON_EXPR" ]]; then
  ADFILTER_DIR="$(cd "$(dirname "$0")" && pwd)"
  CRON_CMD="$CRON_EXPR cd $ADFILTER_DIR && uv run adfilter run -c $CONFIG_FILE --report rule/build-report.json"
  echo "→ Cron expression: $CRON_EXPR"
  read -rp "Install crontab entry now? [y/N]: " INSTALL_CRON
  INSTALL_CRON="${INSTALL_CRON:-N}"
  if [[ "$INSTALL_CRON" =~ ^[Yy] ]]; then
    (crontab -l 2>/dev/null | grep -v "adfilter run"; echo "$CRON_CMD") | crontab -
    echo "→ Crontab entry installed"
  else
    echo "→ Add manually: $CRON_CMD"
  fi
else
  echo "→ Skipped (run manually with: uv run adfilter run -c $CONFIG_FILE)"
fi
echo ""

# ── Step 5: Generate config/application.yaml ─────────────────────────
echo "Step 5: Generating configuration"
echo "─────────────────────────────────────────────"

mkdir -p "$CONFIG_DIR"

# Build sources section based on preset
generate_sources() {
  case "$PRESET" in
    cn)
      cat <<'SRCEOF'
        default:
          - name: anti-ad
            type: easylist
            path: https://anti-ad.net/easylist.txt
          - name: easylist-china
            type: easylist
            path: https://easylist-downloads.adblockplus.org/easylistchina.txt
          - name: cjx-annoyance
            type: easylist
            path: https://raw.githubusercontent.com/cjx82630/cjxlist/master/cjx-annoyance.txt
SRCEOF
      ;;
    jp)
      cat <<'SRCEOF'
        default:
          - name: easylist
            type: easylist
            path: https://easylist.to/easylist/easylist.txt
          - name: 280blocker
            type: dns
            path: https://280blocker.net/files/280blocker_adblock.txt
SRCEOF
      ;;
    global)
      cat <<'SRCEOF'
        default:
          - name: easylist
            type: easylist
            path: https://easylist.to/easylist/easylist.txt
          - name: easyprivacy
            type: easylist
            path: https://easylist.to/easylist/easyprivacy.txt
          - name: peter-lowe
            type: hosts
            path: https://pgl.yoyo.org/adservers/serverlist.php?hostformat=hosts&showintro=0
SRCEOF
      ;;
    custom)
      cat <<'SRCEOF'
        default:
          - name: example-source
            type: easylist
            path: https://example.com/filters.txt
SRCEOF
      ;;
  esac
}

# Build output files section
generate_outputs() {
  for fmt in "${FORMATS[@]}"; do
    fmt="$(echo "$fmt" | tr -d ' ')"
    case "$fmt" in
      dns)       echo "        - { name: dns.txt, type: dns }" ;;
      easylist)  echo "        - { name: easylist.txt, type: easylist }" ;;
      clash)     echo "        - { name: clash.yaml, type: clash }" ;;
      singbox)   echo "        - { name: singbox.json, type: singbox }" ;;
      surge)     echo "        - { name: surge.conf, type: surge }" ;;
      quantumult) echo "        - { name: quantumult.conf, type: quantumult }" ;;
      loon)      echo "        - { name: loon.conf, type: loon }" ;;
      dnsmasq)   echo "        - { name: dnsmasq.conf, type: dnsmasq }" ;;
      smartdns)  echo "        - { name: smartdns.conf, type: smartdns }" ;;
      hosts)     echo "        - { name: hosts.txt, type: hosts }" ;;
      mikrotik)  echo "        - { name: mikrotik.rsc, type: mikrotik }" ;;
      unbound)   echo "        - { name: unbound.conf, type: unbound }" ;;
      *) echo "        # unknown format: $fmt" ;;
    esac
  done
}

# Generate allowlist section
generate_allowlist() {
  if [[ "$ALLOWLIST_ENABLED" == "true" ]]; then
    echo "      allowlist:"
    echo "        - path: config/allowlist.txt"
  fi
}

cat > "$CONFIG_FILE" <<CFGEOF
# adfilter configuration — generated by setup.sh
# Documentation: https://github.com/Lknife666/adfilter/blob/main/docs/configuration.md

application:
  config:
    input:
      rule:
$(generate_sources)
$(generate_allowlist)

    output:
      path: ./rule
      files:
$(generate_outputs)

    fetcher:
      http:
        timeout_seconds: 60
        max_retries: 3
        max_concurrency: 8
        cache_dir: .cache/http
        on_failure: cache_then_skip
        max_cache_age_hours: 72

    optimizer:
      enable: true
      collapse_subdomains: true
      drop_allow_shadowed_deny: true
      min_source_votes: 1
      normalize_idn: true
CFGEOF

echo "→ Generated $CONFIG_FILE"
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║              Setup Complete!                 ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo "  1. Review: cat $CONFIG_FILE"
echo "  2. Run:    uv run adfilter run -c $CONFIG_FILE --progress"
echo "  3. Serve:  uv run adfilter serve --dir rule/"
echo ""
