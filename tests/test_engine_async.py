"""Async tests for skilleval.engine — ExecutionEngine trial execution and batching."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from skilleval.client import ApiError, RateLimitError, TimeoutError
from skilleval.engine import ExecutionEngine, TrialSpec
from skilleval.models import ChatResponse, ModelEntry, TaskConfig, TrialResult


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
    latency: float = 0.5,
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


# ── execute_trial tests ──────────────────────────────────────────────────


class TestExecuteTrialSuccess:
    """Successful trial returns correct TrialResult."""

    async def test_successful_trial(self):
        model = _make_model()
        engine = ExecutionEngine(models=[model])

        mock_response = _make_chat_response(content="Result text")

        with patch.object(engine, "_client") as mock_client:
            mock_client.chat_completion = AsyncMock(return_value=mock_response)

            async with engine:
                # Replace the real client with our mock
                engine._client = mock_client  # type: ignore[assignment]
                result = await engine.execute_trial(
                    model=model,
                    messages=[{"role": "user", "content": "hello"}],
                    config=_make_config(),
                    trial_number=1,
                )

        assert isinstance(result, TrialResult)
        assert result.passed is True
        assert result.model == "test-model"
        assert result.trial_number == 1
        assert result.output_text == "Result text"
        assert result.input_tokens == 10
        assert result.output_tokens == 5
        assert result.latency_seconds == 0.5
        assert result.finish_reason == "stop"
        assert result.error is None
        assert result.cost > 0


class TestExecuteTrialEmptyResponse:
    """Empty content with 0 output_tokens marks trial as failed."""

    async def test_empty_response_detection(self):
        model = _make_model()
        engine = ExecutionEngine(models=[model])

        mock_response = _make_chat_response(content="  ", output_tokens=0)

        async with engine:
            engine._client = AsyncMock()  # type: ignore[assignment]
            engine._client.chat_completion = AsyncMock(return_value=mock_response)

            result = await engine.execute_trial(
                model=model,
                messages=[{"role": "user", "content": "hello"}],
                config=_make_config(),
                trial_number=1,
            )

        assert result.passed is False
        assert "Empty response" in (result.error or "")
        assert "silent rate-limit" in (result.error or "")


class TestExecuteTrialTruncation:
    """finish_reason='length' marks trial as failed with truncation error."""

    async def test_truncation_detection(self):
        model = _make_model()
        engine = ExecutionEngine(models=[model])

        mock_response = _make_chat_response(
            content="Partial output...",
            finish_reason="length",
            output_tokens=4096,
        )

        async with engine:
            engine._client = AsyncMock()  # type: ignore[assignment]
            engine._client.chat_completion = AsyncMock(return_value=mock_response)

            result = await engine.execute_trial(
                model=model,
                messages=[{"role": "user", "content": "hello"}],
                config=_make_config(),
                trial_number=1,
            )

        assert result.passed is False
        assert "truncated" in (result.error or "").lower()
        assert result.finish_reason == "length"
        assert result.output_text == "Partial output..."


class TestExecuteTrialApiError:
    """ApiError is caught and returned as a failed TrialResult."""

    async def test_api_error_handling(self):
        model = _make_model()
        engine = ExecutionEngine(models=[model])

        async with engine:
            engine._client = AsyncMock()  # type: ignore[assignment]
            engine._client.chat_completion = AsyncMock(side_effect=ApiError(403, "Forbidden"))

            result = await engine.execute_trial(
                model=model,
                messages=[{"role": "user", "content": "hello"}],
                config=_make_config(),
                trial_number=2,
            )

        assert result.passed is False
        assert result.trial_number == 2
        assert "403" in (result.error or "")
        assert "Forbidden" in (result.error or "")


class TestExecuteTrialRateLimitError:
    """RateLimitError is caught and returned as a failed TrialResult."""

    async def test_rate_limit_error_handling(self):
        model = _make_model()
        engine = ExecutionEngine(models=[model])

        async with engine:
            engine._client = AsyncMock()  # type: ignore[assignment]
            engine._client.chat_completion = AsyncMock(
                side_effect=RateLimitError("Rate limited by test-provider")
            )

            result = await engine.execute_trial(
                model=model,
                messages=[{"role": "user", "content": "hello"}],
                config=_make_config(),
                trial_number=3,
            )

        assert result.passed is False
        assert "Rate limited" in (result.error or "")


class TestExecuteTrialTimeoutError:
    """TimeoutError is caught and returned as a failed TrialResult."""

    async def test_timeout_error_handling(self):
        model = _make_model()
        engine = ExecutionEngine(models=[model])

        async with engine:
            engine._client = AsyncMock()  # type: ignore[assignment]
            engine._client.chat_completion = AsyncMock(
                side_effect=TimeoutError("Request timed out after 60s")
            )

            result = await engine.execute_trial(
                model=model,
                messages=[{"role": "user", "content": "hello"}],
                config=_make_config(),
                trial_number=1,
            )

        assert result.passed is False
        assert "timed out" in (result.error or "")


# ── execute_batch tests ──────────────────────────────────────────────────


class TestExecuteBatch:
    """execute_batch runs multiple specs and returns results in order."""

    async def test_batch_returns_results_in_spec_order(self):
        model = _make_model()
        engine = ExecutionEngine(models=[model])

        specs = [_make_spec(trial_number=i) for i in range(1, 4)]

        responses = [_make_chat_response(content=f"Response {i}") for i in range(1, 4)]

        call_count = 0

        async def mock_chat(*args, **kwargs):
            nonlocal call_count
            idx = call_count
            call_count += 1
            return responses[idx]

        async with engine:
            engine._client = AsyncMock()  # type: ignore[assignment]
            engine._client.chat_completion = mock_chat

            results = await engine.execute_batch(specs)

        assert len(results) == 3
        for i, result in enumerate(results):
            assert result.trial_number == i + 1
            assert result.passed is True


class TestExecuteBatchWithProgress:
    """on_progress callback is called for each completed trial."""

    async def test_progress_callback_called(self):
        model = _make_model()
        engine = ExecutionEngine(models=[model])

        specs = [_make_spec(trial_number=i) for i in range(1, 4)]
        progress_calls: list[TrialResult] = []

        def on_progress(result: TrialResult) -> None:
            progress_calls.append(result)

        async with engine:
            engine._client = AsyncMock()  # type: ignore[assignment]
            engine._client.chat_completion = AsyncMock(return_value=_make_chat_response())

            await engine.execute_batch(specs, on_progress=on_progress)

        assert len(progress_calls) == 3
        # Each callback should receive a TrialResult
        for call in progress_calls:
            assert isinstance(call, TrialResult)


class TestExecuteBatchMixedResults:
    """Some trials succeed, some fail — verify correct aggregation."""

    async def test_mixed_success_and_failure(self):
        model = _make_model()
        engine = ExecutionEngine(models=[model])

        specs = [_make_spec(trial_number=i) for i in range(1, 4)]

        # Trial 1: success, Trial 2: API error, Trial 3: success
        # Use a lock to assign side_effects deterministically despite
        # concurrent execution from asyncio.gather.
        import asyncio as _asyncio

        _lock = _asyncio.Lock()
        _call_idx = 0
        _side_effects = [
            _make_chat_response(content="OK 1"),
            ApiError(500, "Server error"),
            _make_chat_response(content="OK 3"),
        ]

        async def mock_chat(model_arg, messages, config):
            nonlocal _call_idx
            async with _lock:
                idx = _call_idx
                _call_idx += 1
            effect = _side_effects[idx]
            if isinstance(effect, Exception):
                raise effect
            return effect

        async with engine:
            engine._client = AsyncMock()  # type: ignore[assignment]
            engine._client.chat_completion = mock_chat

            results = await engine.execute_batch(specs)

        assert len(results) == 3
        # Results are in spec order, but which mock each got depends on
        # concurrency. Verify aggregate: 2 passed, 1 failed with 500.
        passed = [r for r in results if r.passed]
        failed = [r for r in results if not r.passed]
        assert len(passed) == 2
        assert len(failed) == 1
        assert "500" in (failed[0].error or "")


# ── Context manager lifecycle ────────────────────────────────────────────


class TestEngineContextManager:
    """Verify __aenter__/__aexit__ manage client lifecycle."""

    async def test_enter_creates_client_and_semaphores(self):
        model_a = _make_model(name="m-a", provider="provider-a")
        model_b = _make_model(name="m-b", provider="provider-b")
        engine = ExecutionEngine(models=[model_a, model_b], max_per_provider=3, max_global=10)

        assert engine._client is None
        assert engine._global_semaphore is None

        async with engine:
            assert engine._client is not None
            assert engine._global_semaphore is not None
            # Semaphores for both providers
            assert "provider-a" in engine._provider_semaphores
            assert "provider-b" in engine._provider_semaphores

        # After exit
        assert engine._client is None

    async def test_execute_without_context_manager_raises(self):
        model = _make_model()
        engine = ExecutionEngine(models=[model])

        with pytest.raises(RuntimeError, match="async context manager"):
            await engine.execute_trial(
                model=model,
                messages=[{"role": "user", "content": "hello"}],
                config=_make_config(),
                trial_number=1,
            )


class TestRateLimitDoesNotTripCircuitBreaker:
    """RateLimitError should NOT increment _failure_counts or trip circuit breaker."""

    async def test_rate_limit_does_not_increment_failure_count(self):
        model = _make_model()
        engine = ExecutionEngine(models=[model])

        async with engine:
            engine._client = AsyncMock()  # type: ignore[assignment]
            engine._client.chat_completion = AsyncMock(
                side_effect=RateLimitError("Rate limited by test-provider")
            )

            await engine.execute_trial(
                model=model,
                messages=[{"role": "user", "content": "hello"}],
                config=_make_config(),
                trial_number=1,
            )

            # Rate limit errors should NOT increment the failure counter
            assert engine._failure_counts.get(model.provider, 0) == 0

    async def test_circuit_breaker_not_tripped_by_rate_limits(self):
        """Even many rate limit errors should not trip the circuit breaker."""
        model = _make_model()
        engine = ExecutionEngine(models=[model])

        async with engine:
            engine._client = AsyncMock()  # type: ignore[assignment]
            engine._client.chat_completion = AsyncMock(side_effect=RateLimitError("Rate limited"))

            # Fire more trials than the circuit breaker threshold
            for i in range(10):
                result = await engine.execute_trial(
                    model=model,
                    messages=[{"role": "user", "content": "hello"}],
                    config=_make_config(),
                    trial_number=i + 1,
                )
                # Should NOT see "Circuit breaker open" error
                assert "Circuit breaker" not in (result.error or "")

    async def test_api_error_still_increments_failure_count(self):
        """ApiError should still increment _failure_counts (real failure)."""
        model = _make_model()
        engine = ExecutionEngine(models=[model])

        async with engine:
            engine._client = AsyncMock()  # type: ignore[assignment]
            engine._client.chat_completion = AsyncMock(side_effect=ApiError(500, "Server error"))

            await engine.execute_trial(
                model=model,
                messages=[{"role": "user", "content": "hello"}],
                config=_make_config(),
                trial_number=1,
            )

            assert engine._failure_counts[model.provider] == 1

    async def test_api_error_trips_circuit_breaker(self):
        """Enough ApiErrors should trip the circuit breaker."""
        model = _make_model()
        engine = ExecutionEngine(models=[model])

        async with engine:
            engine._client = AsyncMock()  # type: ignore[assignment]
            engine._client.chat_completion = AsyncMock(side_effect=ApiError(500, "Server error"))

            # Trip the circuit breaker (default threshold is 5)
            for i in range(6):
                result = await engine.execute_trial(
                    model=model,
                    messages=[{"role": "user", "content": "hello"}],
                    config=_make_config(),
                    trial_number=i + 1,
                )

            # The last trial should see the circuit breaker
            assert "Circuit breaker" in (result.error or "")

    async def test_empty_response_does_not_increment_failure_count(self):
        """Empty responses (silent rate-limits) should not trip circuit breaker."""
        model = _make_model()
        engine = ExecutionEngine(models=[model])

        mock_response = _make_chat_response(content="  ", output_tokens=0)

        async with engine:
            engine._client = AsyncMock()  # type: ignore[assignment]
            engine._client.chat_completion = AsyncMock(return_value=mock_response)

            for i in range(10):
                await engine.execute_trial(
                    model=model,
                    messages=[{"role": "user", "content": "hello"}],
                    config=_make_config(),
                    trial_number=i + 1,
                )

            # Should NOT have incremented _failure_counts
            assert engine._failure_counts.get(model.provider, 0) == 0


class TestConcurrencySemaphores:
    """Verify semaphores are created for unique providers."""

    async def test_unique_provider_semaphores(self):
        models = [
            _make_model(name="m1", provider="alpha"),
            _make_model(name="m2", provider="beta"),
            _make_model(name="m3", provider="alpha"),  # duplicate provider
        ]
        engine = ExecutionEngine(models=models, max_per_provider=5)

        async with engine:
            # Should have exactly 2 unique provider semaphores
            assert len(engine._provider_semaphores) == 2
            assert "alpha" in engine._provider_semaphores
            assert "beta" in engine._provider_semaphores

    async def test_dynamic_provider_semaphore_creation(self):
        """When a trial uses a provider not in the initial model list,
        a semaphore is created dynamically."""
        model_a = _make_model(name="m-a", provider="known-provider")
        model_new = _make_model(name="m-new", provider="new-provider")
        engine = ExecutionEngine(models=[model_a])

        async with engine:
            assert "new-provider" not in engine._provider_semaphores

            engine._client = AsyncMock()  # type: ignore[assignment]
            engine._client.chat_completion = AsyncMock(return_value=_make_chat_response())

            await engine.execute_trial(
                model=model_new,
                messages=[{"role": "user", "content": "hello"}],
                config=_make_config(),
                trial_number=1,
            )

            # Now the provider semaphore should exist
            assert "new-provider" in engine._provider_semaphores
