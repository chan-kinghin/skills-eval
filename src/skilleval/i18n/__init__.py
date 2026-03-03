"""Internationalization support for SkillEval.

Public API:
    t(key, **kwargs) — translate a dotted key, e.g. t("display.tables.model")
    get_locale()     — return current locale code ("en" or "zh")
    set_locale(code) — switch locale at runtime
    save_preference()— persist current locale to ~/.config/skilleval/settings.yaml
"""

from __future__ import annotations

import locale
import logging
import os
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_LOCALES_DIR = Path(__file__).parent / "locales"
_SUPPORTED = ("en", "zh")
_CONFIG_DIR = Path.home() / ".config" / "skilleval"
_CONFIG_FILE = _CONFIG_DIR / "settings.yaml"

# Module-level state (singleton, like settings.py)
_current_locale: str | None = None
_strings: dict[str, Any] = {}
_fallback_strings: dict[str, Any] = {}


def _detect_locale() -> str:
    """Detect locale from env → config file → OS locale → default.

    Priority chain:
    1. SKILLEVAL_LANG env var
    2. ~/.config/skilleval/settings.yaml → language key
    3. OS locale (e.g. zh_CN → zh)
    4. Fallback to "en"
    """
    # 1. Environment variable
    env_lang = os.environ.get("SKILLEVAL_LANG", "").strip().lower()
    if env_lang in _SUPPORTED:
        return env_lang

    # 2. Config file
    if _CONFIG_FILE.exists():
        try:
            data = yaml.safe_load(_CONFIG_FILE.read_text())
            if isinstance(data, dict):
                cfg_lang = str(data.get("language", "")).strip().lower()
                if cfg_lang in _SUPPORTED:
                    return cfg_lang
        except Exception:
            pass

    # 3. OS locale
    try:
        os_locale = locale.getlocale()[0] or ""
        lang_prefix = os_locale.split("_")[0].lower()
        if lang_prefix in _SUPPORTED:
            return lang_prefix
    except Exception:
        pass

    # 4. Default
    return "en"


def _load_locale(code: str) -> dict[str, Any]:
    """Load a YAML locale file and return the parsed dict."""
    path = _LOCALES_DIR / f"{code}.yaml"
    if not path.exists():
        logger.warning("Locale file not found: %s", path)
        return {}
    return yaml.safe_load(path.read_text()) or {}


def _ensure_loaded() -> None:
    """Lazy-init: detect locale and load strings on first access."""
    global _current_locale, _strings, _fallback_strings  # noqa: PLW0603
    if _current_locale is not None:
        return
    _current_locale = _detect_locale()
    _strings = _load_locale(_current_locale)
    if _current_locale != "en":
        _fallback_strings = _load_locale("en")
    else:
        _fallback_strings = {}


def _resolve_key(data: dict[str, Any], key: str) -> str | None:
    """Walk a dotted key path through nested dicts.

    Returns the leaf value as a string, or None if any segment is missing.
    """
    parts = key.split(".")
    current: Any = data
    for part in parts:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
        if current is None:
            return None
    return str(current) if current is not None else None


def t(key: str, **kwargs: Any) -> str:
    """Translate a dotted key, with optional keyword interpolation.

    Fallback chain: current locale → English → raw key string.

    Examples:
        t("display.tables.model")           → "Model" / "模型"
        t("cli.run.resuming", count=2, models="a, b")
            → "Resuming: skipping 2 completed model(s): a, b"
    """
    _ensure_loaded()

    result = _resolve_key(_strings, key)
    if result is None and _fallback_strings:
        result = _resolve_key(_fallback_strings, key)
    if result is None:
        return key

    if kwargs:
        try:
            result = result.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            pass
    return result


def get_locale() -> str:
    """Return the current locale code (e.g. 'en' or 'zh')."""
    _ensure_loaded()
    assert _current_locale is not None
    return _current_locale


def set_locale(code: str) -> None:
    """Switch the active locale at runtime."""
    global _current_locale, _strings, _fallback_strings  # noqa: PLW0603
    if code not in _SUPPORTED:
        raise ValueError(f"Unsupported locale: {code!r}. Supported: {_SUPPORTED}")
    _current_locale = code
    _strings = _load_locale(code)
    if code != "en":
        _fallback_strings = _load_locale("en")
    else:
        _fallback_strings = {}


def save_preference() -> None:
    """Persist the current locale to ~/.config/skilleval/settings.yaml."""
    _ensure_loaded()
    assert _current_locale is not None

    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # Merge with existing config if present
    data: dict[str, Any] = {}
    if _CONFIG_FILE.exists():
        try:
            existing = yaml.safe_load(_CONFIG_FILE.read_text())
            if isinstance(existing, dict):
                data = existing
        except Exception:
            pass

    data["language"] = _current_locale
    _CONFIG_FILE.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True))


def reset() -> None:
    """Reset module state (for testing)."""
    global _current_locale, _strings, _fallback_strings  # noqa: PLW0603
    _current_locale = None
    _strings = {}
    _fallback_strings = {}
