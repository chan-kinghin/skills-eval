"""Async OpenAI-compatible API client."""

from __future__ import annotations

import asyncio
import os
import random
import time

import aiohttp

from skilleval.models import ChatResponse, ModelEntry, TaskConfig


class ApiError(Exception):
    """Non-retryable API error (4xx other than 429)."""

    def __init__(self, status: int, message: str) -> None:
        self.status = status
        super().__init__(f"API error {status}: {message}")


class RateLimitError(Exception):
    """429 rate-limit error (retryable)."""


class TimeoutError(Exception):  # noqa: A001
    """Request timed out."""


_MAX_RETRIES = 3
_BACKOFF_BASE = [1, 2, 4]


class ModelClient:
    """Async client for OpenAI-compatible chat completion endpoints."""

    def __init__(self) -> None:
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> ModelClient:
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type: type | None, exc: Exception | None, tb: object) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    async def chat_completion(
        self,
        model: ModelEntry,
        messages: list[dict],
        config: TaskConfig,
    ) -> ChatResponse:
        """Send a chat completion request and return a parsed ChatResponse."""
        if self._session is None:
            raise RuntimeError("ModelClient must be used as an async context manager")

        api_key = os.environ.get(model.env_key)
        if not api_key:
            raise ApiError(
                0,
                f"Missing API key: environment variable '{model.env_key}' is not set",
            )

        url = f"{model.endpoint.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": model.name,
            "messages": messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
        }
        timeout = aiohttp.ClientTimeout(total=config.timeout)

        last_error: Exception | None = None

        for attempt in range(_MAX_RETRIES):
            t0 = time.monotonic()
            try:
                async with self._session.post(
                    url, json=body, headers=headers, timeout=timeout
                ) as resp:
                    latency = time.monotonic() - t0

                    if resp.status == 429:
                        last_error = RateLimitError(f"Rate limited by {model.provider}")
                        await self._backoff(attempt)
                        continue

                    if resp.status >= 500:
                        text = await resp.text()
                        last_error = ApiError(resp.status, text)
                        await self._backoff(attempt)
                        continue

                    if resp.status >= 400:
                        text = await resp.text()
                        raise ApiError(resp.status, text)

                    data = await resp.json()
                    parsed = self._parse_response(data, latency, model)

                    # Some providers (e.g. Zhipu free tier) silently return
                    # empty responses instead of proper 429. Retry these.
                    if not parsed.content.strip() and parsed.output_tokens == 0:
                        last_error = RateLimitError(
                            f"Empty response from {model.provider} (silent rate-limit)"
                        )
                        await self._backoff(attempt)
                        continue

                    return parsed

            except (aiohttp.ServerTimeoutError, asyncio.TimeoutError):
                latency = time.monotonic() - t0
                last_error = TimeoutError(
                    f"Request to {model.name} timed out after {config.timeout}s"
                )
                await self._backoff(attempt)
            except (ApiError, RateLimitError, TimeoutError):
                raise
            except aiohttp.ClientError as e:
                latency = time.monotonic() - t0
                last_error = ApiError(0, f"Connection error: {e}")
                await self._backoff(attempt)

        raise last_error  # type: ignore[misc]

    @staticmethod
    def _parse_response(data: dict, latency: float, model: ModelEntry) -> ChatResponse:
        """Parse an OpenAI-compatible JSON response into ChatResponse.

        Handles reasoning models (e.g., GLM, DeepSeek-R1) that split their response
        into `reasoning_content` (chain-of-thought) and `content` (final answer).
        If `content` is empty but `reasoning_content` exists, the model likely ran
        out of tokens during reasoning — this is reported as a truncation.
        """
        choices = data.get("choices")
        if not choices:
            raise ApiError(0, "No choices in API response")

        choice = choices[0]
        message = choice.get("message", {})
        content = message.get("content", "") or ""
        reasoning = message.get("reasoning_content", "") or ""
        finish_reason = choice.get("finish_reason")

        # Some reasoning models put the answer in content only after reasoning.
        # If content is empty but reasoning exists, the model used all tokens on thinking.
        if not content.strip() and reasoning.strip():
            if finish_reason == "length":
                content = ""  # Will be caught as truncation by the engine
            else:
                # Reasoning finished but content is empty — use reasoning as fallback
                content = reasoning

        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        model_version = data.get("model")

        return ChatResponse(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_seconds=latency,
            model_version=model_version,
            finish_reason=finish_reason,
        )

    @staticmethod
    async def _backoff(attempt: int) -> None:
        """Exponential backoff with jitter."""
        import asyncio

        base = _BACKOFF_BASE[min(attempt, len(_BACKOFF_BASE) - 1)]
        jitter = random.uniform(0, base * 0.5)
        await asyncio.sleep(base + jitter)


def compute_cost(model: ModelEntry, input_tokens: int, output_tokens: int) -> float:
    """Compute the dollar cost for a single API call."""
    return (input_tokens / 1_000_000 * model.input_cost_per_m) + (
        output_tokens / 1_000_000 * model.output_cost_per_m
    )
