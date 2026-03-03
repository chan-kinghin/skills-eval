"""Tests for skilleval.client — cost computation and response parsing."""

from __future__ import annotations

import pytest

from skilleval.client import ModelClient, compute_cost
from skilleval.models import ModelEntry


# ── compute_cost ─────────────────────────────────────────────────────────


class TestComputeCost:
    @pytest.fixture()
    def model(self) -> ModelEntry:
        return ModelEntry(
            name="m",
            provider="p",
            endpoint="http://x",
            input_cost_per_m=0.5,
            output_cost_per_m=1.5,
            env_key="K",
        )

    def test_zero_tokens(self, model: ModelEntry):
        assert compute_cost(model, 0, 0) == 0.0

    def test_known_amounts(self, model: ModelEntry):
        # 1M input tokens = $0.50, 1M output tokens = $1.50
        cost = compute_cost(model, 1_000_000, 1_000_000)
        assert cost == pytest.approx(2.0)

    def test_small_amounts(self, model: ModelEntry):
        # 1000 input = $0.0005, 500 output = $0.00075
        cost = compute_cost(model, 1000, 500)
        assert cost == pytest.approx(0.0005 + 0.00075)

    def test_only_input_tokens(self, model: ModelEntry):
        cost = compute_cost(model, 1_000_000, 0)
        assert cost == pytest.approx(0.5)

    def test_only_output_tokens(self, model: ModelEntry):
        cost = compute_cost(model, 0, 1_000_000)
        assert cost == pytest.approx(1.5)


# ── _parse_response ──────────────────────────────────────────────────────


class TestParseResponse:
    @pytest.fixture()
    def model(self) -> ModelEntry:
        return ModelEntry(
            name="m",
            provider="p",
            endpoint="http://x",
            input_cost_per_m=0,
            output_cost_per_m=0,
            env_key="K",
        )

    def test_standard_response(self, model: ModelEntry):
        data = {
            "choices": [
                {
                    "message": {"content": "Hello world"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            "model": "m-v1",
        }
        resp = ModelClient._parse_response(data, latency=0.5, model=model)
        assert resp.content == "Hello world"
        assert resp.input_tokens == 10
        assert resp.output_tokens == 5
        assert resp.latency_seconds == 0.5
        assert resp.model_version == "m-v1"
        assert resp.finish_reason == "stop"

    def test_no_choices_raises(self, model: ModelEntry):
        from skilleval.client import ApiError

        with pytest.raises(ApiError, match="No choices"):
            ModelClient._parse_response({"choices": []}, latency=0, model=model)

    def test_missing_choices_key_raises(self, model: ModelEntry):
        from skilleval.client import ApiError

        with pytest.raises(ApiError, match="No choices"):
            ModelClient._parse_response({}, latency=0, model=model)

    def test_empty_content_with_reasoning(self, model: ModelEntry):
        """When content is empty but reasoning exists, use reasoning as fallback."""
        data = {
            "choices": [
                {
                    "message": {
                        "content": "",
                        "reasoning_content": "Let me think... the answer is 42.",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 5, "completion_tokens": 10},
        }
        resp = ModelClient._parse_response(data, latency=0.2, model=model)
        assert resp.content == "Let me think... the answer is 42."

    def test_empty_content_reasoning_truncated(self, model: ModelEntry):
        """When content empty, reasoning exists, and finish_reason=length → truncation."""
        data = {
            "choices": [
                {
                    "message": {
                        "content": "",
                        "reasoning_content": "Thinking...",
                    },
                    "finish_reason": "length",
                }
            ],
            "usage": {"prompt_tokens": 5, "completion_tokens": 100},
        }
        resp = ModelClient._parse_response(data, latency=0.2, model=model)
        assert resp.content == ""
        assert resp.finish_reason == "length"

    def test_missing_usage(self, model: ModelEntry):
        data = {
            "choices": [{"message": {"content": "hi"}, "finish_reason": "stop"}],
        }
        resp = ModelClient._parse_response(data, latency=0.1, model=model)
        assert resp.input_tokens == 0
        assert resp.output_tokens == 0

    def test_none_content_treated_as_empty(self, model: ModelEntry):
        data = {
            "choices": [{"message": {"content": None}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }
        resp = ModelClient._parse_response(data, latency=0.1, model=model)
        assert resp.content == ""
