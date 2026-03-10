"""Centralized configuration constants with env var overrides."""

from __future__ import annotations

import os


class Settings:
    """Runtime settings with SKILLEVAL_* env var overrides."""

    def __init__(self) -> None:
        self.max_retries: int = int(os.environ.get("SKILLEVAL_MAX_RETRIES", "3"))
        self.backoff_base: list[int] = [1, 2, 4]
        self.circuit_breaker_threshold: int = int(
            os.environ.get("SKILLEVAL_CIRCUIT_BREAKER_THRESHOLD", "5")
        )
        self.max_per_provider: int = int(os.environ.get("SKILLEVAL_MAX_PER_PROVIDER", "5"))
        self.max_global: int = int(os.environ.get("SKILLEVAL_MAX_GLOBAL", "20"))
        self.rate_initial: float = float(os.environ.get("SKILLEVAL_RATE_INITIAL", "5.0"))
        self.rate_min: float = float(os.environ.get("SKILLEVAL_RATE_MIN", "0.2"))

        backoff_env = os.environ.get("SKILLEVAL_BACKOFF_BASE")
        if backoff_env:
            self.backoff_base = [int(x) for x in backoff_env.split(",")]


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the singleton Settings instance."""
    global _settings  # noqa: PLW0603
    if _settings is None:
        _settings = Settings()
    return _settings
