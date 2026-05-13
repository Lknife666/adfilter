"""GitHub Pages index.html generator.

Generates a static subscription landing page from build-report.json,
suitable for publishing to GitHub Pages alongside the rule files.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


def generate_index_html(
    report_path: Path,
    output_path: Path,
    repo: str = "Lknife666/adfilter",
    branch: str = "release",
) -> None:
    """Generate index.html for GitHub Pages from build report.

    Args:
        report_path: Path to build-report.json
        output_path: Path to write index.html
        repo: GitHub repository (owner/name)
        branch: Branch where rules are published
    """
    # Load report
    report: dict = {}
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    outputs = report.get("outputs", [])
    sources = report.get("sources", [])
    total_rules = sum(o.get("count", 0) for o in outputs)
    last_build = report.get("finished_at", datetime.now(tz=UTC).isoformat())
    elapsed_ms = report.get("elapsed_ms", 0)

    base_url = f"https://raw.githubusercontent.com/{repo}/{branch}"

    # Format table
    format_info = {
        "dns.txt": ("AdGuard Home DNS", "AdGuard Home, AdGuard DNS"),
        "easylist.txt": ("EasyList / ABP", "uBlock Origin, Adblock Plus, AdGuard"),
        "clash.yaml": ("Clash", "Clash, Clash Meta, Stash"),
        "singbox.json": ("sing-box", "sing-box rule-set (v2)"),
        "surge.conf": ("Surge", "Surge, Shadowrocket, Stash"),
        "quantumult.conf": ("Quantumult X", "Quantumult X"),
        "loon.conf": ("Loon", "Loon"),
        "dnsmasq.conf": ("dnsmasq", "dnsmasq, OpenWrt"),
        "smartdns.conf": ("SmartDNS", "SmartDNS"),
        "hosts.txt": ("hosts", "All OS, Pi-hole"),
        "mikrotik.rsc": ("MikroTik", "MikroTik RouterOS v6/v7"),
        "unbound.conf": ("Unbound", "Unbound DNS resolver"),
    }

    rows_html = ""
    for out in outputs:
        name = out.get("name", "")
        count = out.get("count", 0)
        fmt_name, apps = format_info.get(name, (name, ""))
        url = f"{base_url}/{name}"
        rows_html += f"""
            <tr>
                <td class="px-4 py-3 font-medium">{fmt_name}</td>
                <td class="px-4 py-3 text-sm text-gray-600">{apps}</td>
                <td class="px-4 py-3 text-sm text-right">{count:,}</td>
                <td class="px-4 py-3">
                    <div class="flex gap-2 items-center">
                        <input type="text" readonly value="{url}"
                               class="flex-1 text-xs bg-gray-100 border rounded px-2 py-1 font-mono"
                               onclick="this.select()">
                        <button onclick="copyUrl(this, '{url}')"
                                class="px-2 py-1 text-xs bg-blue-50 text-blue-600 rounded hover:bg-blue-100">
                            Copy
                        </button>
                    </div>
                </td>
            </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>adfilter — Rule Subscription Center</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 min-h-screen">
    <div class="max-w-4xl mx-auto px-4 py-12">
        <!-- Header -->
        <div class="text-center mb-8">
            <h1 class="text-3xl font-bold text-gray-800">adfilter</h1>
            <p class="text-gray-500 mt-2">Ad-filter rule aggregator & multi-format converter</p>
            <div class="mt-4 flex justify-center gap-4 text-sm text-gray-500">
                <span>Last updated: <strong>{last_build[:19] if last_build else 'N/A'}</strong></span>
                <span>|</span>
                <span>Total rules: <strong>{total_rules:,}</strong></span>
                <span>|</span>
                <span>Build time: <strong>{elapsed_ms}ms</strong></span>
            </div>
        </div>

        <!-- Usage Guide -->
        <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-8">
            <p class="text-sm text-blue-800">
                <strong>Usage:</strong> Copy the subscription URL below and paste it into your ad-blocking tool's
                subscription/filter list settings. Rules are auto-updated every 8 hours.
            </p>
        </div>

        <!-- Subscription Table -->
        <div class="bg-white rounded-lg shadow overflow-hidden">
            <table class="w-full">
                <thead class="bg-gray-50 border-b">
                    <tr>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Format</th>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Compatible With</th>
                        <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Rules</th>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Subscribe URL</th>
                    </tr>
                </thead>
                <tbody class="divide-y">{rows_html}
                </tbody>
            </table>
        </div>

        <!-- Footer -->
        <div class="mt-8 text-center text-sm text-gray-400">
            <p>
                Powered by <a href="https://github.com/{repo}" class="text-blue-500 hover:underline">adfilter</a>
                | Auto-generated every 8 hours via GitHub Actions
                | <a href="{base_url}/build-report.json" class="text-blue-500 hover:underline">Build Report</a>
            </p>
        </div>
    </div>

    <script>
    function copyUrl(btn, url) {{
        navigator.clipboard.writeText(url).then(() => {{
            const orig = btn.textContent;
            btn.textContent = 'Copied!';
            btn.classList.add('bg-green-100');
            setTimeout(() => {{ btn.textContent = orig; btn.classList.remove('bg-green-100'); }}, 1500);
        }});
    }}
    </script>
</body>
</html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
