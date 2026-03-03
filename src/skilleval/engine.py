"""Execution engine with concurrency control."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Callable
from dataclasses import dataclass

from skilleval.client import ApiError, ModelClient, RateLimitError, TimeoutError, compute_cost
from skilleval.models import ModelEntry, TaskConfig, TrialResult
from skilleval.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class TrialSpec:
    """Specification for a single trial to execute."""

    model: ModelEntry
    messages: list[dict[str, str]]
    config: TaskConfig
    trial_number: int


class ExecutionEngine:
    """Runs batches of API calls with two-level concurrency control."""

    def __init__(
        self,
        models: list[ModelEntry],
        max_per_provider: int | None = None,
        max_global: int | None = None,
    ) -> None:
        settings = get_settings()
        self._models = models
        self._max_per_provider = max_per_provider or settings.max_per_provider
        self._max_global = max_global or settings.max_global
        self._circuit_breaker_threshold = settings.circuit_breaker_threshold
        self._client: ModelClient | None = None
        self._exit_stack: contextlib.AsyncExitStack | None = None
        self._global_semaphore: asyncio.Semaphore | None = None
        self._provider_semaphores: dict[str, asyncio.Semaphore] = {}
        self._failure_counts: dict[str, int] = {}

    async def __aenter__(self) -> ExecutionEngine:
        self._exit_stack = contextlib.AsyncExitStack()
        self._client = await self._exit_stack.enter_async_context(ModelClient())
        self._global_semaphore = asyncio.Semaphore(self._max_global)
        self._provider_semaphores = {
            m.provider: asyncio.Semaphore(self._max_per_provider)
            for m in self._models
        }
        return self

    async def __aexit__(self, exc_type: type | None, exc: Exception | None, tb: object) -> None:
        if self._exit_stack:
            await self._exit_stack.aclose()
            self._exit_stack = None
            self._client = None

    async def execute_trial(
        self,
        model: ModelEntry,
        messages: list[dict],
        config: TaskConfig,
        trial_number: int,
    ) -> TrialResult:
        """Execute a single trial with concurrency control."""
        if self._client is None or self._global_semaphore is None:
            raise RuntimeError("ExecutionEngine must be used as an async context manager")

        provider_sem = self._provider_semaphores.get(model.provider)
        if provider_sem is None:
            provider_sem = asyncio.Semaphore(self._max_per_provider)
            self._provider_semaphores[model.provider] = provider_sem

        logger.debug("Starting trial %d for model %s", trial_number, model.name)

        # Circuit breaker: skip remaining trials if a provider has too many consecutive failures
        if self._failure_counts.get(model.provider, 0) >= self._circuit_breaker_threshold:
            logger.warning(
                "Circuit breaker open for %s — skipping trial %d for %s",
                model.provider, trial_number, model.name,
            )
            return TrialResult(
                model=model.name,
                trial_number=trial_number,
                passed=False,
                error=f"Circuit breaker open: {model.provider} had {self._circuit_breaker_threshold} consecutive failures",
            )

        try:
            async with self._global_semaphore:
                async with provider_sem:
                    response = await self._client.chat_completion(model, messages, config)

            cost = compute_cost(model, response.input_tokens, response.output_tokens)

            # Detect empty responses — some providers silently return empty
            # content instead of proper 429/error (e.g. Zhipu free tier)
            if not response.content.strip() and response.output_tokens == 0:
                self._failure_counts[model.provider] = self._failure_counts.get(model.provider, 0) + 1
                logger.warning(
                    "Empty response detected for %s trial %d (consecutive failures: %d)",
                    model.name, trial_number, self._failure_counts[model.provider],
                )
                return TrialResult(
                    model=model.name,
                    trial_number=trial_number,
                    passed=False,
                    output_text=response.content,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    cost=cost,
                    latency_seconds=response.latency_seconds,
                    error="Empty response from API (possible silent rate-limit)",
                    finish_reason=response.finish_reason,
                )

            if response.finish_reason == "length":
                self._failure_counts[model.provider] = self._failure_counts.get(model.provider, 0) + 1
                logger.warning(
                    "Output truncation detected for %s trial %d (consecutive failures: %d)",
                    model.name, trial_number, self._failure_counts[model.provider],
                )
                return TrialResult(
                    model=model.name,
                    trial_number=trial_number,
                    passed=False,
                    output_text=response.content,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    cost=cost,
                    latency_seconds=response.latency_seconds,
                    error="Output truncated (max_tokens reached)",
                    finish_reason=response.finish_reason,
                )

            # Success — reset the failure counter for this provider
            self._failure_counts[model.provider] = 0

            return TrialResult(
                model=model.name,
                trial_number=trial_number,
                passed=True,
                output_text=response.content,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                cost=cost,
                latency_seconds=response.latency_seconds,
                finish_reason=response.finish_reason,
            )

        except (ApiError, RateLimitError, TimeoutError) as e:
            self._failure_counts[model.provider] = self._failure_counts.get(model.provider, 0) + 1
            logger.error(
                "Trial %d failed for %s: %s (consecutive failures: %d)",
                trial_number, model.name, e, self._failure_counts[model.provider],
            )
            return TrialResult(
                model=model.name,
                trial_number=trial_number,
                passed=False,
                error=str(e),
            )

    async def execute_batch(
        self,
        specs: list[TrialSpec],
        on_progress: Callable[[TrialResult], None] | None = None,
    ) -> list[TrialResult]:
        """Run all trial specs concurrently, returning results in spec order."""
        logger.info("Batch execution starting with %d specs", len(specs))

        async def _run_one(spec: TrialSpec) -> TrialResult:
            result = await self.execute_trial(
                model=spec.model,
                messages=spec.messages,
                config=spec.config,
                trial_number=spec.trial_number,
            )
            if on_progress is not None:
                on_progress(result)
            return result

        tasks = [_run_one(spec) for spec in specs]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        results: list[TrialResult] = []
        for i, result in enumerate(raw_results):
            if isinstance(result, Exception):
                results.append(
                    TrialResult(
                        model=specs[i].model.name,
                        trial_number=specs[i].trial_number,
                        passed=False,
                        error=str(result),
                    )
                )
            else:
                results.append(result)

        logger.debug("Batch execution completed: %d results", len(results))
        return results
