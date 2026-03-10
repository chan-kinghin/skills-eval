"""Adaptive per-provider rate limiter using AIMD token bucket."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class _ProviderState:
    """Per-provider rate limiter state."""

    current_rate: float  # tokens per second (refill rate)
    initial_rate: float  # cap for additive increase
    min_rate: float  # floor for multiplicative decrease
    tokens: float = 1.0  # available tokens
    last_refill: float = field(default_factory=time.monotonic)
    consecutive_successes: int = 0
    total_rate_limits: int = 0
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


# How many consecutive successes before increasing rate
_SUCCESS_THRESHOLD = 3
# Additive increase step (req/s)
_INCREASE_STEP = 0.1


class AdaptiveRateLimiter:
    """AIMD-based adaptive rate limiter, keyed by provider name.

    - Start at ``initial_rate`` req/s (no throttling by default).
    - On 429: halve the rate (multiplicative decrease), floor at ``min_rate``.
    - After ``_SUCCESS_THRESHOLD`` consecutive successes: increase by
      ``_INCREASE_STEP`` req/s (additive increase), capped at ``initial_rate``.
    - If a ``Retry-After`` header value is provided, derive rate from it.
    """

    def __init__(
        self,
        initial_rate: float = 5.0,
        min_rate: float = 0.2,
    ) -> None:
        self._initial_rate = initial_rate
        self._min_rate = min_rate
        self._providers: dict[str, _ProviderState] = {}

    def _get_state(self, provider: str) -> _ProviderState:
        if provider not in self._providers:
            self._providers[provider] = _ProviderState(
                current_rate=self._initial_rate,
                initial_rate=self._initial_rate,
                min_rate=self._min_rate,
            )
        return self._providers[provider]

    async def acquire(self, provider: str) -> None:
        """Block until a token is available for *provider*."""
        state = self._get_state(provider)

        while True:
            async with state.lock:
                now = time.monotonic()
                elapsed = now - state.last_refill
                state.tokens = min(
                    1.0,
                    state.tokens + elapsed * state.current_rate,
                )
                state.last_refill = now

                if state.tokens >= 1.0:
                    state.tokens -= 1.0
                    return

                # Calculate wait time for next token
                wait = (1.0 - state.tokens) / state.current_rate

            logger.info(
                "Rate limiter throttling %s — waiting %.2fs (rate=%.2f req/s)",
                provider,
                wait,
                state.current_rate,
            )
            await asyncio.sleep(wait)

    def record_success(self, provider: str) -> None:
        """Record a successful request; increase rate after threshold."""
        state = self._get_state(provider)
        state.consecutive_successes += 1

        if state.consecutive_successes >= _SUCCESS_THRESHOLD:
            old_rate = state.current_rate
            state.current_rate = min(
                state.initial_rate,
                state.current_rate + _INCREASE_STEP,
            )
            state.consecutive_successes = 0
            if state.current_rate > old_rate:
                logger.info(
                    "Rate limiter increased %s rate: %.2f → %.2f req/s",
                    provider,
                    old_rate,
                    state.current_rate,
                )

    def record_rate_limit(self, provider: str, retry_after: float | None = None) -> None:
        """Record a rate-limit (429) response; decrease rate."""
        state = self._get_state(provider)
        state.consecutive_successes = 0
        state.total_rate_limits += 1

        old_rate = state.current_rate

        if retry_after is not None and retry_after > 0:
            # Derive rate from Retry-After: 1 request per retry_after seconds
            state.current_rate = max(state.min_rate, 1.0 / retry_after)
        else:
            # Multiplicative decrease: halve the rate
            state.current_rate = max(state.min_rate, state.current_rate / 2.0)

        logger.warning(
            "Rate limiter decreased %s rate: %.2f → %.2f req/s (total 429s: %d)",
            provider,
            old_rate,
            state.current_rate,
            state.total_rate_limits,
        )

    def get_stats(self, provider: str) -> dict[str, float | int]:
        """Return current rate and counters for diagnostics."""
        state = self._get_state(provider)
        return {
            "current_rate": state.current_rate,
            "initial_rate": state.initial_rate,
            "min_rate": state.min_rate,
            "consecutive_successes": state.consecutive_successes,
            "total_rate_limits": state.total_rate_limits,
        }
