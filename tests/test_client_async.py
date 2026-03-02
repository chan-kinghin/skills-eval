"""Async tests for skilleval.client — ModelClient.chat_completion() with aioresponses."""

from __future__ import annotations

import re
from unittest.mock import patch

import aiohttp
import pytest
from aioresponses import aioresponses

from skilleval.client import ApiError, ModelClient, RateLimitError, TimeoutError
from skilleval.models import ChatResponse, ModelEntry, TaskConfig


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_model(
    *,
    name: str = "test-model",
    provider: str = "test-provider",
    endpoint: str = "https://api.test.example.com/v1",
    env_key: str = "TEST_API_KEY",
    api_key: str | None = None,
) -> ModelEntry:
    return ModelEntry(
        name=name,
        provider=provider,
        endpoint=endpoint,
        input_cost_per_m=0.5,
        output_cost_per_m=1.5,
        env_key=env_key,
        api_key=api_key,
    )


def _make_config(
    *,
    temperature: float = 0.0,
    max_tokens: int = 4096,
    timeout: int = 60,
) -> TaskConfig:
    return TaskConfig(temperature=temperature, max_tokens=max_tokens, timeout=timeout)


def _success_payload(
    content: str = "Hello world",
    input_tokens: int = 10,
    output_tokens: int = 5,
    finish_reason: str = "stop",
    model_version: str = "test-model-v1",
) -> dict:
    return {
        "choices": [
            {
                "message": {"content": content},
                "finish_reason": finish_reason,
            }
        ],
        "usage": {
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
        },
        "model": model_version,
    }


async def _noop_backoff(*args, **kwargs) -> None:
    """No-op backoff replacement for fast tests.

    Accepts *args because the original is a @staticmethod, but patch.object
    replaces it as a regular class attribute — so Python may pass `self` as
    the first argument when called via `self._backoff(attempt)`.
    """
    pass


_CHAT_URL = re.compile(r"^https://api\.test\.example\.com/v1/chat/completions$")


# ── Tests ────────────────────────────────────────────────────────────────


class TestChatCompletionSuccess:
    """Successful 200 response returns correct ChatResponse fields."""

    async def test_successful_200_response(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("TEST_API_KEY", "sk-test-key")
        model = _make_model()
        config = _make_config()
        messages = [{"role": "user", "content": "Say hello"}]

        with aioresponses() as mocked:
            mocked.post(_CHAT_URL, payload=_success_payload())

            async with ModelClient() as client:
                resp = await client.chat_completion(model, messages, config)

        assert isinstance(resp, ChatResponse)
        assert resp.content == "Hello world"
        assert resp.input_tokens == 10
        assert resp.output_tokens == 5
        assert resp.finish_reason == "stop"
        assert resp.model_version == "test-model-v1"
        assert resp.latency_seconds > 0


class TestRateLimitRetry:
    """429 rate limiting triggers retry; succeeds on second attempt."""

    @patch.object(ModelClient, "_backoff", new=_noop_backoff)
    async def test_429_then_200_retries_and_succeeds(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("TEST_API_KEY", "sk-test-key")
        model = _make_model()
        config = _make_config()
        messages = [{"role": "user", "content": "hello"}]

        with aioresponses() as mocked:
            mocked.post(_CHAT_URL, status=429)
            mocked.post(_CHAT_URL, payload=_success_payload(content="Retried OK"))

            async with ModelClient() as client:
                resp = await client.chat_completion(model, messages, config)

        assert resp.content == "Retried OK"


class TestServerErrorRetry:
    """5xx server error triggers retry; succeeds on second attempt."""

    @patch.object(ModelClient, "_backoff", new=_noop_backoff)
    async def test_500_then_200_retries_and_succeeds(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("TEST_API_KEY", "sk-test-key")
        model = _make_model()
        config = _make_config()
        messages = [{"role": "user", "content": "hello"}]

        with aioresponses() as mocked:
            mocked.post(_CHAT_URL, status=500, body="Internal Server Error")
            mocked.post(_CHAT_URL, payload=_success_payload(content="After 500"))

            async with ModelClient() as client:
                resp = await client.chat_completion(model, messages, config)

        assert resp.content == "After 500"


class TestClientErrorNoRetry:
    """4xx client error (non-429) raises ApiError immediately."""

    @patch.object(ModelClient, "_backoff", new=_noop_backoff)
    async def test_400_raises_api_error_immediately(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("TEST_API_KEY", "sk-test-key")
        model = _make_model()
        config = _make_config()
        messages = [{"role": "user", "content": "hello"}]

        with aioresponses() as mocked:
            mocked.post(_CHAT_URL, status=400, body="Bad Request")

            async with ModelClient() as client:
                with pytest.raises(ApiError, match="400"):
                    await client.chat_completion(model, messages, config)


class TestTimeoutHandling:
    """Timeout exception is raised after all retries are exhausted."""

    @patch.object(ModelClient, "_backoff", new=_noop_backoff)
    async def test_timeout_raises_after_retries(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("TEST_API_KEY", "sk-test-key")
        model = _make_model()
        config = _make_config(timeout=1)
        messages = [{"role": "user", "content": "hello"}]

        with aioresponses() as mocked:
            for _ in range(3):
                mocked.post(_CHAT_URL, exception=aiohttp.ServerTimeoutError())

            async with ModelClient() as client:
                with pytest.raises(TimeoutError, match="timed out"):
                    await client.chat_completion(model, messages, config)


class TestEmptyResponseRetry:
    """Empty response (silent rate-limit) triggers retry; succeeds on second attempt."""

    @patch.object(ModelClient, "_backoff", new=_noop_backoff)
    async def test_empty_content_0_tokens_then_real_response(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("TEST_API_KEY", "sk-test-key")
        model = _make_model()
        config = _make_config()
        messages = [{"role": "user", "content": "hello"}]

        empty_payload = _success_payload(content="", output_tokens=0)
        real_payload = _success_payload(content="Real answer", output_tokens=10)

        with aioresponses() as mocked:
            mocked.post(_CHAT_URL, payload=empty_payload)
            mocked.post(_CHAT_URL, payload=real_payload)

            async with ModelClient() as client:
                resp = await client.chat_completion(model, messages, config)

        assert resp.content == "Real answer"
        assert resp.output_tokens == 10


class TestConnectionErrorRetry:
    """aiohttp.ClientError triggers retry; raises after all attempts fail."""

    @patch.object(ModelClient, "_backoff", new=_noop_backoff)
    async def test_connection_error_retries_then_fails(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("TEST_API_KEY", "sk-test-key")
        model = _make_model()
        config = _make_config()
        messages = [{"role": "user", "content": "hello"}]

        with aioresponses() as mocked:
            for _ in range(3):
                mocked.post(_CHAT_URL, exception=aiohttp.ClientConnectionError("Connection refused"))

            async with ModelClient() as client:
                with pytest.raises(ApiError, match="Connection error"):
                    await client.chat_completion(model, messages, config)


class TestMaxRetriesExhausted:
    """3x 429 exhausts retries and raises RateLimitError."""

    @patch.object(ModelClient, "_backoff", new=_noop_backoff)
    async def test_three_429s_raises_rate_limit_error(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("TEST_API_KEY", "sk-test-key")
        model = _make_model()
        config = _make_config()
        messages = [{"role": "user", "content": "hello"}]

        with aioresponses() as mocked:
            for _ in range(3):
                mocked.post(_CHAT_URL, status=429)

            async with ModelClient() as client:
                with pytest.raises(RateLimitError, match="Rate limited"):
                    await client.chat_completion(model, messages, config)


class TestAdhocModelApiKey:
    """Ad-hoc model with api_key set uses the embedded key, not env var."""

    @patch.object(ModelClient, "_backoff", new=_noop_backoff)
    async def test_adhoc_model_uses_embedded_api_key(self, monkeypatch: pytest.MonkeyPatch):
        # Ensure _ADHOC_ env var is NOT set so the only key source is model.api_key
        monkeypatch.delenv("_ADHOC_", raising=False)

        model = ModelEntry.adhoc(
            endpoint="https://api.test.example.com/v1",
            api_key="sk-adhoc-secret-key",
            model_name="adhoc-test-model",
        )
        config = _make_config()
        messages = [{"role": "user", "content": "hello"}]

        captured_headers: dict[str, str] = {}

        with aioresponses() as mocked:

            def callback(url, **kwargs):
                captured_headers.update(kwargs.get("headers", {}))
                return aioresponses()  # Not used; we return payload below

            mocked.post(
                _CHAT_URL,
                payload=_success_payload(content="Adhoc response"),
            )

            async with ModelClient() as client:
                resp = await client.chat_completion(model, messages, config)

        assert resp.content == "Adhoc response"
        # Verify the key used: since model.api_key is "sk-adhoc-secret-key",
        # the line `api_key = model.api_key or os.environ.get(model.env_key)`
        # should select the embedded key.
        # We verify indirectly: the request succeeded without _ADHOC_ env var.

    @patch.object(ModelClient, "_backoff", new=_noop_backoff)
    async def test_adhoc_model_api_key_sent_in_auth_header(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Verify that the Authorization header contains the embedded api_key."""
        monkeypatch.delenv("_ADHOC_", raising=False)

        model = ModelEntry.adhoc(
            endpoint="https://api.test.example.com/v1",
            api_key="sk-adhoc-secret-key",
            model_name="adhoc-test-model",
        )
        config = _make_config()
        messages = [{"role": "user", "content": "hello"}]

        with aioresponses() as mocked:
            mocked.post(
                _CHAT_URL,
                payload=_success_payload(content="Adhoc response"),
            )

            async with ModelClient() as client:
                await client.chat_completion(model, messages, config)

                # Inspect the request that was made
                # aioresponses stores requests keyed by (method, url_pattern)
                # We need to check another way: iterate all requests
                all_requests = []
                for key, calls in mocked.requests.items():
                    all_requests.extend(calls)

                assert len(all_requests) >= 1
                req_kwargs = all_requests[0][1]  # (url, kwargs)
                auth_header = req_kwargs.get("headers", {}).get("Authorization", "")
                assert auth_header == "Bearer sk-adhoc-secret-key"

    @patch.object(ModelClient, "_backoff", new=_noop_backoff)
    async def test_adhoc_model_prefers_api_key_over_env(self, monkeypatch: pytest.MonkeyPatch):
        """When both api_key and env var are set, api_key takes precedence."""
        monkeypatch.setenv("_ADHOC_", "sk-env-key")

        model = ModelEntry.adhoc(
            endpoint="https://api.test.example.com/v1",
            api_key="sk-embedded-key",
            model_name="adhoc-test-model",
        )
        config = _make_config()
        messages = [{"role": "user", "content": "hello"}]

        with aioresponses() as mocked:
            mocked.post(
                _CHAT_URL,
                payload=_success_payload(content="OK"),
            )

            async with ModelClient() as client:
                await client.chat_completion(model, messages, config)

                all_requests = []
                for key, calls in mocked.requests.items():
                    all_requests.extend(calls)

                assert len(all_requests) >= 1
                req_kwargs = all_requests[0][1]
                auth_header = req_kwargs.get("headers", {}).get("Authorization", "")
                assert auth_header == "Bearer sk-embedded-key"


class TestContextManagerLifecycle:
    """Test __aenter__/__aexit__ work correctly."""

    async def test_enter_creates_session(self):
        client = ModelClient()
        assert client._session is None

        async with client:
            assert client._session is not None
            assert isinstance(client._session, aiohttp.ClientSession)

        # After exit, session should be closed and set to None
        assert client._session is None

    async def test_chat_without_context_manager_raises(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("TEST_API_KEY", "sk-test-key")
        client = ModelClient()
        model = _make_model()
        config = _make_config()

        with pytest.raises(RuntimeError, match="async context manager"):
            await client.chat_completion(model, [{"role": "user", "content": "hi"}], config)

    async def test_missing_api_key_raises(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("TEST_API_KEY", raising=False)
        model = _make_model()  # No api_key, env_key="TEST_API_KEY" which is not set
        config = _make_config()

        async with ModelClient() as client:
            with pytest.raises(ApiError, match="Missing API key"):
                await client.chat_completion(model, [{"role": "user", "content": "hi"}], config)
