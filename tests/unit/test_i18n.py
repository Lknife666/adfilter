"""Tests for the i18n module."""

from __future__ import annotations

import os
from unittest.mock import patch

from adfilter.i18n import I18n, get_i18n, t, _CATALOG, DEFAULT_LOCALE, SUPPORTED_LOCALES


class TestI18n:
    def test_default_locale(self):
        i = I18n()
        assert i.locale == "en"
        assert i.is_english
        assert not i.is_chinese

    def test_chinese_locale(self):
        i = I18n(locale="zh")
        assert i.locale == "zh"
        assert i.is_chinese
        assert not i.is_english

    def test_unsupported_locale_falls_back(self):
        i = I18n(locale="fr")
        assert i.locale == "en"

    def test_translate_english(self):
        i = I18n(locale="en")
        assert i.t("build.started") == "Build started"

    def test_translate_chinese(self):
        i = I18n(locale="zh")
        assert i.t("build.started") == "构建已启动"

    def test_translate_with_kwargs(self):
        i = I18n(locale="en")
        result = i.t("build.rules_generated", count=100, formats=5)
        assert "100" in result
        assert "5" in result

    def test_translate_missing_key_returns_key(self):
        i = I18n(locale="en")
        assert i.t("nonexistent.key") == "nonexistent.key"

    def test_add_custom_messages(self):
        i = I18n(locale="en")
        i.add_messages({"custom.msg": {"en": "Hello", "zh": "你好"}})
        assert i.t("custom.msg") == "Hello"

    def test_add_custom_messages_chinese(self):
        i = I18n(locale="zh")
        i.add_messages({"custom.msg": {"en": "Hello", "zh": "你好"}})
        assert i.t("custom.msg") == "你好"

    def test_from_env_default(self):
        with patch.dict(os.environ, {}, clear=True):
            i = I18n.from_env()
            assert i.locale == "en"

    def test_from_env_adfilter_locale(self):
        with patch.dict(os.environ, {"ADFILTER_LOCALE": "zh"}):
            i = I18n.from_env()
            assert i.locale == "zh"

    def test_from_env_lang_zh(self):
        with patch.dict(os.environ, {"LANG": "zh_CN.UTF-8"}, clear=True):
            i = I18n.from_env()
            assert i.locale == "zh"

    def test_from_env_lang_en(self):
        with patch.dict(os.environ, {"LANG": "en_US.UTF-8"}, clear=True):
            i = I18n.from_env()
            assert i.locale == "en"

    def test_translate_bad_format_kwargs(self):
        i = I18n(locale="en")
        # Key exists but kwarg key doesn't match template
        result = i.t("build.rules_generated", wrong_key=1)
        # Should return template without crashing
        assert result == "Generated {count} rules in {formats} formats"


class TestModuleLevelFunctions:
    def test_get_i18n_returns_instance(self):
        import adfilter.i18n as i18n_mod
        i18n_mod._default = None
        with patch.dict(os.environ, {}, clear=True):
            inst = get_i18n()
            assert isinstance(inst, I18n)

    def test_t_function(self):
        import adfilter.i18n as i18n_mod
        i18n_mod._default = I18n(locale="en")
        assert t("build.started") == "Build started"
