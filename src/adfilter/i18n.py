"""Internationalization (i18n) support for CLI output.

Provides a simple translation system for user-facing messages.
Supports: zh_CN (Chinese), en_US (English), ja_JP (Japanese).

Usage:
    from adfilter.i18n import t, set_locale

    set_locale("zh_CN")
    print(t("build.started"))         # → "开始构建规则..."
    print(t("build.done", count=100)) # → "构建完成，共 100 条规则"
"""

from __future__ import annotations

import locale as sys_locale
import os
from typing import Any

# Current locale
_current_locale: str = "zh_CN"

# Translation dictionaries
_TRANSLATIONS: dict[str, dict[str, str]] = {
    "zh_CN": {
        "build.started": "开始构建规则...",
        "build.done": "构建完成，共 {count:,} 条规则",
        "build.failed": "构建失败: {error}",
        "build.source_fetching": "正在拉取规则源: {name}",
        "build.source_done": "源 {name}: {effective:,} 有效 / {total:,} 总计 ({elapsed}ms)",
        "build.source_failed": "源 {name} 拉取失败: {error}",
        "build.optimizing": "正在优化规则...",
        "build.writing": "正在写入 {count} 个输出文件...",
        "build.report_saved": "构建报告已保存: {path}",
        "optimizer.collapse": "子域折叠: 移除 {count:,} 条冗余规则",
        "optimizer.voting": "多源投票 (n≥{threshold}): 保留 {kept:,}/{total:,}",
        "optimizer.allowlist": "白名单: 移除 {count:,} 条规则",
        "optimizer.done": "优化完成: {before:,} → {after:,} ({delta:+,})",
        "serve.starting": "启动 HTTP 服务: http://{host}:{port}",
        "serve.auto_refresh": "自动刷新已启用: 每 {interval} 分钟",
        "serve.stopped": "HTTP 服务已停止",
        "validate.ok": "配置文件验证通过",
        "validate.error": "配置文件错误: {error}",
        "guard.drop_warning": "规则数异常下降 {ratio}: {last:,} → {current:,}",
        "guard.min_warning": "规则总数 ({count:,}) 低于最小阈值 ({min:,})",
        "guard.source_failure": "{failed}/{total} 个规则源拉取失败",
        "quality.dead_domains": "死域名检测: {dead:,}/{total:,} ({ratio})",
        "quality.false_positives": "误杀分析: 发现 {count:,} 个疑似误杀",
        "quality.conflicts": "冲突检测: {count:,} 个冲突 ({resolved} 已自动解决)",
        "quality.score": "规则质量评分: 平均 {score:.1f}/100 (等级 {grade})",
    },
    "en_US": {
        "build.started": "Starting rule build...",
        "build.done": "Build complete: {count:,} rules",
        "build.failed": "Build failed: {error}",
        "build.source_fetching": "Fetching source: {name}",
        "build.source_done": "Source {name}: {effective:,} effective / {total:,} total ({elapsed}ms)",
        "build.source_failed": "Source {name} fetch failed: {error}",
        "build.optimizing": "Optimizing rules...",
        "build.writing": "Writing {count} output files...",
        "build.report_saved": "Build report saved: {path}",
        "optimizer.collapse": "Subdomain collapse: removed {count:,} redundant rules",
        "optimizer.voting": "Multi-source voting (n≥{threshold}): kept {kept:,}/{total:,}",
        "optimizer.allowlist": "Allowlist: removed {count:,} rules",
        "optimizer.done": "Optimization done: {before:,} → {after:,} ({delta:+,})",
        "serve.starting": "Starting HTTP server: http://{host}:{port}",
        "serve.auto_refresh": "Auto-refresh enabled: every {interval} minutes",
        "serve.stopped": "HTTP server stopped",
        "validate.ok": "Configuration file is valid",
        "validate.error": "Configuration error: {error}",
        "guard.drop_warning": "Rule count dropped {ratio}: {last:,} → {current:,}",
        "guard.min_warning": "Total rules ({count:,}) below minimum threshold ({min:,})",
        "guard.source_failure": "{failed}/{total} sources failed to fetch",
        "quality.dead_domains": "Dead domain scan: {dead:,}/{total:,} ({ratio})",
        "quality.false_positives": "False positive analysis: {count:,} suspects found",
        "quality.conflicts": "Conflict detection: {count:,} conflicts ({resolved} auto-resolved)",
        "quality.score": "Rule quality score: avg {score:.1f}/100 (grade {grade})",
    },
    "ja_JP": {
        "build.started": "ルール構築を開始...",
        "build.done": "構築完了: {count:,} ルール",
        "build.failed": "構築失敗: {error}",
        "build.source_fetching": "ソース取得中: {name}",
        "build.source_done": "ソース {name}: {effective:,} 有効 / {total:,} 合計 ({elapsed}ms)",
        "build.source_failed": "ソース {name} 取得失敗: {error}",
        "build.optimizing": "ルールを最適化中...",
        "build.writing": "{count} 個の出力ファイルを書き込み中...",
        "build.report_saved": "ビルドレポート保存: {path}",
        "optimizer.collapse": "サブドメイン折りたたみ: {count:,} 個の冗長ルールを削除",
        "optimizer.voting": "マルチソース投票 (n≥{threshold}): {kept:,}/{total:,} 保持",
        "optimizer.allowlist": "ホワイトリスト: {count:,} ルール削除",
        "optimizer.done": "最適化完了: {before:,} → {after:,} ({delta:+,})",
        "serve.starting": "HTTPサーバー起動: http://{host}:{port}",
        "serve.auto_refresh": "自動更新有効: {interval} 分ごと",
        "serve.stopped": "HTTPサーバー停止",
        "validate.ok": "設定ファイル検証OK",
        "validate.error": "設定エラー: {error}",
        "guard.drop_warning": "ルール数異常減少 {ratio}: {last:,} → {current:,}",
        "guard.min_warning": "ルール総数 ({count:,}) が最小閾値 ({min:,}) を下回っています",
        "guard.source_failure": "{failed}/{total} ソース取得失敗",
        "quality.dead_domains": "無効ドメイン検出: {dead:,}/{total:,} ({ratio})",
        "quality.false_positives": "誤検知分析: {count:,} 件の疑い",
        "quality.conflicts": "競合検出: {count:,} 件 ({resolved} 自動解決)",
        "quality.score": "ルール品質スコア: 平均 {score:.1f}/100 (グレード {grade})",
    },
}


def set_locale(locale: str) -> None:
    """Set the current locale for translations."""
    global _current_locale
    if locale in _TRANSLATIONS:
        _current_locale = locale
    elif locale.split("_")[0] in ("zh", "cn"):
        _current_locale = "zh_CN"
    elif locale.split("_")[0] in ("ja",):
        _current_locale = "ja_JP"
    else:
        _current_locale = "en_US"


def detect_locale() -> str:
    """Auto-detect locale from environment."""
    # Check ADFILTER_LANG first
    lang = os.environ.get("ADFILTER_LANG", "")
    if lang:
        return lang

    # Check LANG / LC_ALL
    env_lang = os.environ.get("LANG", "") or os.environ.get("LC_ALL", "")
    if "zh" in env_lang or "CN" in env_lang:
        return "zh_CN"
    if "ja" in env_lang or "JP" in env_lang:
        return "ja_JP"
    if "en" in env_lang:
        return "en_US"

    # Fall back to system locale
    try:
        sys_loc = sys_locale.getdefaultlocale()[0] or ""
        if "zh" in sys_loc:
            return "zh_CN"
        if "ja" in sys_loc:
            return "ja_JP"
    except (ValueError, TypeError):
        pass

    return "zh_CN"  # Default to Chinese (primary user base)


def get_locale() -> str:
    """Get the current locale."""
    return _current_locale


def t(key: str, **kwargs: Any) -> str:
    """Translate a message key with optional format arguments.

    Args:
        key: Dot-separated message key (e.g., "build.done")
        **kwargs: Format arguments to substitute

    Returns:
        Translated and formatted string, or key itself if not found
    """
    messages = _TRANSLATIONS.get(_current_locale, _TRANSLATIONS["en_US"])
    template = messages.get(key, key)
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, ValueError, IndexError):
            return template
    return template


# Auto-detect on import
set_locale(detect_locale())
