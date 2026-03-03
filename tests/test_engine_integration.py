"""Integration tests for engine: concurrency, circuit breaker, interrupts."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

from skilleval.client import ApiError
from skilleval.engine import ExecutionEngine, TrialSpec
from skilleval.settings import get_settings
from skilleval.models import ChatResponse, ModelEntry, TaskConfig


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_model(
    name: str = "test-model",
    provider: str = "test-provider",
) -> ModelEntry:
    return ModelEntry(
        name=name,
        provider=provider,
        endpoint="https://api.test.example.com/v1",
        input_cost_per_m=0.5,
        output_cost_per_m=1.5,
        env_key="TEST_API_KEY",
    )


def _make_config() -> TaskConfig:
    return TaskConfig(temperature=0.0, max_tokens=4096, timeout=60)


def _make_chat_response(
    content: str = "Hello world",
    input_tokens: int = 10,
    output_tokens: int = 5,
    latency: float = 0.1,
    finish_reason: str = "stop",
) -> ChatResponse:
    return ChatResponse(
        content=content,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_seconds=latency,
        model_version="test-v1",
        finish_reason=finish_reason,
    )


def _make_spec(
    model: ModelEntry | None = None,
    trial_number: int = 1,
) -> TrialSpec:
    return TrialSpec(
        model=model or _make_model(),
        messages=[{"role": "user", "content": "hello"}],
        config=_make_config(),
        trial_number=trial_number,
    )


# ── Concurrent execution with mocked responses ──────────────────────────


class TestConcurrentExecution:
    """Verify that multiple trials run concurrently via the engine."""

    async def test_concurrent_trials_all_succeed(self):
        """All trials in a batch complete successfully and concurrently."""
        model_a = _make_model(name="model-a", provider="provider-a")
        model_b = _make_model(name="model-b", provider="provider-b")
        engine = ExecutionEngine(models=[model_a, model_b], max_global=10)

        specs = [
            _make_spec(model=model_a, trial_number=i) for i in range(1, 4)
        ] + [
            _make_spec(model=model_b, trial_number=i) for i in range(1, 4)
        ]

        async with engine:
            engine._client = AsyncMock()
            engine._client.chat_completion = AsyncMock(
                return_value=_make_chat_response(content="concurrent result")
            )

            results = await engine.execute_batch(specs)

        assert len(results) == 6
        assert all(r.passed for r in results)
        assert all(r.output_text == "concurrent result" for r in results)
        models_used = {r.model for r in results}
        assert models_used == {"model-a", "model-b"}

    async def test_global_semaphore_limits_concurrency(self):
        """Global semaphore limits how many trials run simultaneously."""
        model = _make_model()
        max_concurrent = 2
        engine = ExecutionEngine(models=[model], max_global=max_concurrent)

        concurrent_count = 0
        max_observed = 0

        async def mock_chat(*args, **kwargs):
            nonlocal concurrent_count, max_observed
            concurrent_count += 1
            max_observed = max(max_observed, concurrent_count)
            await asyncio.sleep(0.05)
            concurrent_count -= 1
            return _make_chat_response()

        specs = [_make_spec(trial_number=i) for i in range(1, 6)]

        async with engine:
            engine._client = AsyncMock()
            engine._client.chat_completion = mock_chat

            results = await engine.execute_batch(specs)

        assert len(results) == 5
        assert all(r.passed for r in results)
        assert max_observed <= max_concurrent

    async def test_provider_semaphore_limits_per_provider(self):
        """Per-provider semaphore limits concurrency within one provider."""
        model = _make_model(name="m", provider="slow-provider")
        max_per_provider = 2
        engine = ExecutionEngine(
            models=[model], max_per_provider=max_per_provider, max_global=10
        )

        concurrent_count = 0
        max_observed = 0

        async def mock_chat(*args, **kwargs):
            nonlocal concurrent_count, max_observed
            concurrent_count += 1
            max_observed = max(max_observed, concurrent_count)
            await asyncio.sleep(0.05)
            concurrent_count -= 1
            return _make_chat_response()

        specs = [_make_spec(model=model, trial_number=i) for i in range(1, 6)]

        async with engine:
            engine._client = AsyncMock()
            engine._client.chat_completion = mock_chat

            results = await engine.execute_batch(specs)

        assert len(results) == 5
        assert max_observed <= max_per_provider


# ── Circuit breaker ─────────────────────────────────────────────────────


class TestCircuitBreaker:
    """Circuit breaker opens after N consecutive failures for a provider."""

    async def test_circuit_breaker_trips_after_threshold(self):
        """After get_settings().circuit_breaker_threshold consecutive failures,
        subsequent trials are skipped with a circuit breaker error."""
        model = _make_model(name="m-fail", provider="failing-provider")
        engine = ExecutionEngine(models=[model], max_global=1)

        total_trials = get_settings().circuit_breaker_threshold + 3
        specs = [_make_spec(model=model, trial_number=i) for i in range(1, total_trials + 1)]

        async with engine:
            engine._client = AsyncMock()
            engine._client.chat_completion = AsyncMock(
                side_effect=ApiError(500, "Internal Server Error")
            )

            results = await engine.execute_batch(specs)

        assert len(results) == total_trials
        assert all(not r.passed for r in results)

        circuit_breaker_results = [
            r for r in results if r.error and "Circuit breaker" in r.error
        ]
        assert len(circuit_breaker_results) >= 1

    async def test_circuit_breaker_resets_on_success(self):
        """A successful response resets the failure counter."""
        model = _make_model(name="m-flaky", provider="flaky-provider")
        engine = ExecutionEngine(models=[model], max_global=1)

        call_count = 0

        async def flaky_response(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise ApiError(500, "temporary error")
            elif call_count == 4:
                return _make_chat_response(content="recovered")
            else:
                raise ApiError(500, "another error")

        specs = [_make_spec(model=model, trial_number=i) for i in range(1, 7)]

        async with engine:
            engine._client = AsyncMock()
            engine._client.chat_completion = flaky_response

            results = await engine.execute_batch(specs)

        assert results[3].passed is True
        assert results[3].output_text == "recovered"

        for r in results[4:]:
            assert r.passed is False
            if r.error:
                assert "Circuit breaker" not in r.error


# ── Interrupt / error handling ──────────────────────────────────────────


class TestInterruptHandling:
    """Error handling during batch execution."""

    async def test_runtime_error_during_batch_produces_failed_result(self):
        """An unexpected RuntimeError in a trial is captured as a failed TrialResult."""
        model = _make_model()
        engine = ExecutionEngine(models=[model], max_global=5)

        call_count = 0

        async def mock_chat_with_error(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 3:
                raise RuntimeError("Unexpected failure during execution")
            return _make_chat_response(content=f"result-{call_count}")

        specs = [_make_spec(trial_number=i) for i in range(1, 6)]

        async with engine:
            engine._client = AsyncMock()
            engine._client.chat_completion = mock_chat_with_error

            results = await engine.execute_batch(specs)

        assert len(results) == 5
        errors = [r for r in results if r.error and not r.passed]
        assert len(errors) >= 1
        error_msgs = [r.error for r in errors]
        assert any("Unexpected failure" in e for e in error_msgs)

    async def test_mixed_errors_in_batch(self):
        """A mix of successes and ApiError failures produces correct results."""
        model = _make_model()
        engine = ExecutionEngine(models=[model], max_global=5)

        call_count = 0

        async def mock_chat_mixed(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise ApiError(503, "Service Unavailable")
            return _make_chat_response(content=f"ok-{call_count}")

        specs = [_make_spec(trial_number=i) for i in range(1, 4)]

        async with engine:
            engine._client = AsyncMock()
            engine._client.chat_completion = mock_chat_mixed

            results = await engine.execute_batch(specs)

        assert len(results) == 3
        failed = [r for r in results if not r.passed]
        assert len(failed) == 1
        assert "503" in (failed[0].error or "")
        passed = [r for r in results if r.passed]
        assert len(passed) == 2
