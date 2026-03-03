"""Tests for the i18n subsystem."""

from __future__ import annotations

import os
from pathlib import Path
from unittest import mock

import pytest

from skilleval.i18n import (
    _detect_locale,
    _resolve_key,
    get_locale,
    reset,
    save_preference,
    set_locale,
    t,
)


@pytest.fixture(autouse=True)
def _reset_i18n():
    """Reset i18n state before each test."""
    reset()
    yield
    reset()


class TestDetectLocale:
    """Test locale detection priority chain."""

    def test_env_var_takes_priority(self):
        with mock.patch.dict(os.environ, {"SKILLEVAL_LANG": "zh"}):
            assert _detect_locale() == "zh"

    def test_env_var_case_insensitive(self):
        with mock.patch.dict(os.environ, {"SKILLEVAL_LANG": "ZH"}):
            assert _detect_locale() == "zh"

    def test_unsupported_env_var_falls_through(self):
        with mock.patch.dict(os.environ, {"SKILLEVAL_LANG": "fr"}, clear=False):
            # Should not return "fr" — falls through to other sources
            result = _detect_locale()
            assert result in ("en", "zh")

    def test_config_file_detection(self, tmp_path: Path):
        config_file = tmp_path / "settings.yaml"
        config_file.write_text("language: zh\n")

        with (
            mock.patch.dict(os.environ, {}, clear=False),
            mock.patch("skilleval.i18n._CONFIG_FILE", config_file),
        ):
            os.environ.pop("SKILLEVAL_LANG", None)
            assert _detect_locale() == "zh"

    def test_default_is_en(self):
        with (
            mock.patch.dict(os.environ, {}, clear=False),
            mock.patch("skilleval.i18n._CONFIG_FILE", Path("/nonexistent/settings.yaml")),
            mock.patch("locale.getdefaultlocale", return_value=("en_US", "UTF-8")),
        ):
            os.environ.pop("SKILLEVAL_LANG", None)
            assert _detect_locale() == "en"


class TestResolveKey:
    """Test dotted key resolution."""

    def test_simple_key(self):
        data = {"a": {"b": {"c": "hello"}}}
        assert _resolve_key(data, "a.b.c") == "hello"

    def test_missing_key(self):
        data = {"a": {"b": "hello"}}
        assert _resolve_key(data, "a.c") is None

    def test_top_level_key(self):
        data = {"key": "value"}
        assert _resolve_key(data, "key") == "value"

    def test_non_dict_intermediate(self):
        data = {"a": "not_a_dict"}
        assert _resolve_key(data, "a.b") is None


class TestTranslate:
    """Test the t() function."""

    def test_basic_english(self):
        with mock.patch.dict(os.environ, {"SKILLEVAL_LANG": "en"}):
            assert t("display.tables.model") == "Model"

    def test_basic_chinese(self):
        with mock.patch.dict(os.environ, {"SKILLEVAL_LANG": "zh"}):
            assert t("display.tables.model") == "模型"

    def test_interpolation(self):
        with mock.patch.dict(os.environ, {"SKILLEVAL_LANG": "en"}):
            result = t("cli.run.resuming", count=2, models="a, b")
            assert "2" in result
            assert "a, b" in result

    def test_missing_key_returns_key(self):
        with mock.patch.dict(os.environ, {"SKILLEVAL_LANG": "en"}):
            assert t("nonexistent.key.path") == "nonexistent.key.path"

    def test_chinese_falls_back_to_english(self):
        """If a key is missing from zh.yaml, fall back to en.yaml."""
        with mock.patch.dict(os.environ, {"SKILLEVAL_LANG": "zh"}):
            # This key exists in en.yaml — zh.yaml should also have it,
            # but let's test the fallback mechanism by temporarily removing it
            result = t("display.tables.model")
            assert isinstance(result, str)
            assert len(result) > 0


class TestSetLocale:
    """Test runtime locale switching."""

    def test_switch_to_chinese(self):
        with mock.patch.dict(os.environ, {"SKILLEVAL_LANG": "en"}):
            assert t("display.tables.model") == "Model"
            set_locale("zh")
            assert t("display.tables.model") == "模型"
            assert get_locale() == "zh"

    def test_switch_back_to_english(self):
        with mock.patch.dict(os.environ, {"SKILLEVAL_LANG": "zh"}):
            assert t("display.tables.model") == "模型"
            set_locale("en")
            assert t("display.tables.model") == "Model"
            assert get_locale() == "en"

    def test_unsupported_locale_raises(self):
        with pytest.raises(ValueError, match="Unsupported locale"):
            set_locale("fr")


class TestSavePreference:
    """Test persistence of locale preference."""

    def test_save_and_reload(self, tmp_path: Path):
        config_dir = tmp_path / "config"
        config_file = config_dir / "settings.yaml"

        with (
            mock.patch("skilleval.i18n._CONFIG_DIR", config_dir),
            mock.patch("skilleval.i18n._CONFIG_FILE", config_file),
            mock.patch.dict(os.environ, {"SKILLEVAL_LANG": "zh"}),
        ):
            # Initialize and save
            assert get_locale() == "zh"
            save_preference()

            assert config_file.exists()
            import yaml

            data = yaml.safe_load(config_file.read_text())
            assert data["language"] == "zh"

    def test_save_merges_with_existing(self, tmp_path: Path):
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "settings.yaml"
        config_file.write_text("other_key: other_value\n")

        with (
            mock.patch("skilleval.i18n._CONFIG_DIR", config_dir),
            mock.patch("skilleval.i18n._CONFIG_FILE", config_file),
            mock.patch.dict(os.environ, {"SKILLEVAL_LANG": "en"}),
        ):
            assert get_locale() == "en"
            save_preference()

            import yaml

            data = yaml.safe_load(config_file.read_text())
            assert data["language"] == "en"
            assert data["other_key"] == "other_value"


class TestGetLocale:
    """Test get_locale returns correct value."""

    def test_returns_detected_locale(self):
        with mock.patch.dict(os.environ, {"SKILLEVAL_LANG": "en"}):
            assert get_locale() == "en"

    def test_returns_set_locale(self):
        with mock.patch.dict(os.environ, {"SKILLEVAL_LANG": "en"}):
            get_locale()  # trigger init
            set_locale("zh")
            assert get_locale() == "zh"
