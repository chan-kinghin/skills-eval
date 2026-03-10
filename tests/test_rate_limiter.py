"""Tests for skilleval.rate_limiter — AdaptiveRateLimiter."""

from __future__ import annotations

import asyncio
import time

import pytest

from skilleval.rate_limiter import AdaptiveRateLimiter, _SUCCESS_THRESHOLD


# ── Basic acquire / release ─────────────────────────────────────────────


class TestAcquireBasics:
    """First acquire should not block; token is immediately available."""

    async def test_first_acquire_returns_immediately(self):
        limiter = AdaptiveRateLimiter(initial_rate=5.0)
        t0 = time.monotonic()
        await limiter.acquire("test-provider")
        elapsed = time.monotonic() - t0
        assert elapsed < 0.1  # should be near-instant

    async def test_acquire_blocks_when_no_tokens(self):
        """After consuming the single token, next acquire should block."""
        limiter = AdaptiveRateLimiter(initial_rate=2.0)  # 1 token per 0.5s
        await limiter.acquire("p")  # consume the token

        t0 = time.monotonic()
        await limiter.acquire("p")  # should block ~0.5s
        elapsed = time.monotonic() - t0
        assert 0.3 < elapsed < 1.5  # allow some tolerance


# ── Rate decrease on 429 ────────────────────────────────────────────────


class TestRateDecrease:
    """record_rate_limit halves the current rate."""

    def test_halves_rate(self):
        limiter = AdaptiveRateLimiter(initial_rate=4.0, min_rate=0.2)
        limiter.record_rate_limit("p")
        stats = limiter.get_stats("p")
        assert stats["current_rate"] == pytest.approx(2.0)

    def test_halves_rate_multiple_times(self):
        limiter = AdaptiveRateLimiter(initial_rate=4.0, min_rate=0.2)
        limiter.record_rate_limit("p")
        limiter.record_rate_limit("p")
        stats = limiter.get_stats("p")
        assert stats["current_rate"] == pytest.approx(1.0)

    def test_rate_floor(self):
        """Rate never drops below min_rate."""
        limiter = AdaptiveRateLimiter(initial_rate=1.0, min_rate=0.5)
        for _ in range(20):
            limiter.record_rate_limit("p")
        stats = limiter.get_stats("p")
        assert stats["current_rate"] == pytest.approx(0.5)

    def test_retry_after_sets_rate(self):
        """Retry-After header directly sets the rate."""
        limiter = AdaptiveRateLimiter(initial_rate=5.0, min_rate=0.2)
        limiter.record_rate_limit("p", retry_after=2.0)
        stats = limiter.get_stats("p")
        # 1 req per 2s = 0.5 req/s
        assert stats["current_rate"] == pytest.approx(0.5)

    def test_retry_after_respects_floor(self):
        limiter = AdaptiveRateLimiter(initial_rate=5.0, min_rate=0.2)
        limiter.record_rate_limit("p", retry_after=10.0)
        stats = limiter.get_stats("p")
        # 1/10 = 0.1, but floor is 0.2
        assert stats["current_rate"] == pytest.approx(0.2)

    def test_resets_consecutive_successes(self):
        limiter = AdaptiveRateLimiter(initial_rate=5.0)
        limiter.record_success("p")
        limiter.record_success("p")
        limiter.record_rate_limit("p")
        stats = limiter.get_stats("p")
        assert stats["consecutive_successes"] == 0

    def test_total_rate_limits_counter(self):
        limiter = AdaptiveRateLimiter(initial_rate=5.0)
        limiter.record_rate_limit("p")
        limiter.record_rate_limit("p")
        limiter.record_rate_limit("p")
        stats = limiter.get_stats("p")
        assert stats["total_rate_limits"] == 3


# ── Rate increase on successes ──────────────────────────────────────────


class TestRateIncrease:
    """After _SUCCESS_THRESHOLD consecutive successes, rate increases."""

    def test_no_increase_below_threshold(self):
        limiter = AdaptiveRateLimiter(initial_rate=5.0)
        # Reduce rate first so there's room to grow
        limiter.record_rate_limit("p")  # 5.0 → 2.5
        for _ in range(_SUCCESS_THRESHOLD - 1):
            limiter.record_success("p")
        stats = limiter.get_stats("p")
        assert stats["current_rate"] == pytest.approx(2.5)

    def test_increases_after_threshold(self):
        limiter = AdaptiveRateLimiter(initial_rate=5.0)
        limiter.record_rate_limit("p")  # 5.0 → 2.5
        for _ in range(_SUCCESS_THRESHOLD):
            limiter.record_success("p")
        stats = limiter.get_stats("p")
        assert stats["current_rate"] == pytest.approx(2.6)

    def test_capped_at_initial_rate(self):
        """Rate never exceeds initial_rate."""
        limiter = AdaptiveRateLimiter(initial_rate=2.0)
        # rate is already at initial, successes shouldn't increase it
        for _ in range(_SUCCESS_THRESHOLD * 5):
            limiter.record_success("p")
        stats = limiter.get_stats("p")
        assert stats["current_rate"] == pytest.approx(2.0)


# ── Provider independence ───────────────────────────────────────────────


class TestProviderIndependence:
    """Each provider has its own state."""

    def test_independent_states(self):
        limiter = AdaptiveRateLimiter(initial_rate=4.0)
        limiter.record_rate_limit("alpha")
        stats_alpha = limiter.get_stats("alpha")
        stats_beta = limiter.get_stats("beta")
        assert stats_alpha["current_rate"] == pytest.approx(2.0)
        assert stats_beta["current_rate"] == pytest.approx(4.0)


# ── Concurrent safety ──────────────────────────────────────────────────


class TestConcurrentAcquire:
    """Multiple concurrent acquires are safe and all complete."""

    async def test_concurrent_acquires_complete(self):
        limiter = AdaptiveRateLimiter(initial_rate=10.0)
        results: list[bool] = []

        async def acquire_one():
            await limiter.acquire("p")
            results.append(True)

        await asyncio.gather(*[acquire_one() for _ in range(5)])
        assert len(results) == 5


# ── get_stats for unknown provider ──────────────────────────────────────


class TestGetStats:
    """get_stats lazily creates state for unknown providers."""

    def test_unknown_provider_returns_defaults(self):
        limiter = AdaptiveRateLimiter(initial_rate=3.0, min_rate=0.5)
        stats = limiter.get_stats("never-seen")
        assert stats["current_rate"] == pytest.approx(3.0)
        assert stats["initial_rate"] == pytest.approx(3.0)
        assert stats["min_rate"] == pytest.approx(0.5)
        assert stats["consecutive_successes"] == 0
        assert stats["total_rate_limits"] == 0
