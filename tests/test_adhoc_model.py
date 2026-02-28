"""Tests for ad-hoc model construction and validation."""

from __future__ import annotations

import pytest

from skilleval.config import build_adhoc_model, filter_available, filter_by_names
from skilleval.models import ModelEntry


class TestAdhocModelEntry:
    def test_classmethod_all_params(self):
        m = ModelEntry.adhoc(
            endpoint="https://api.openai.com/v1",
            api_key="sk-xxx",
            model_name="gpt-4o",
            input_cost=0.1,
            output_cost=0.2,
            context_window=64_000,
        )
        assert m.name == "gpt-4o"
        assert m.provider == "adhoc"
        assert m.endpoint == "https://api.openai.com/v1"
        assert m.input_cost_per_m == 0.1
        assert m.output_cost_per_m == 0.2
        assert m.context_window == 64_000
        assert m.env_key == "_ADHOC_"
        assert m.api_key == "sk-xxx"

    def test_classmethod_defaults(self):
        m = ModelEntry.adhoc(
            endpoint="https://example.com/v1",
            api_key="sk-abc",
            model_name="my-model",
        )
        assert m.input_cost_per_m == 0.0
        assert m.output_cost_per_m == 0.0
        assert m.context_window == 128_000
        assert m.provider == "adhoc"
        assert m.env_key == "_ADHOC_"


class TestBuildAdhocModel:
    def test_build_valid(self):
        m = build_adhoc_model(
            endpoint="https://api.openai.com/v1",
            api_key="sk-xxx",
            model_name="gpt-4o",
        )
        assert isinstance(m, ModelEntry)
        assert m.provider == "adhoc"
        assert m.api_key == "sk-xxx"

    def test_invalid_endpoint_raises(self):
        with pytest.raises(ValueError, match="Invalid endpoint URL"):
            build_adhoc_model(endpoint="not a url", api_key="k", model_name="m")

    def test_missing_model_name_raises(self):
        with pytest.raises(ValueError, match="Model name must be provided"):
            build_adhoc_model(endpoint="https://api.openai.com", api_key="k", model_name="")


class TestFiltersWithAdhoc:
    def test_filter_available_includes_adhoc_with_api_key(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("_ADHOC_", raising=False)
        m = build_adhoc_model(
            endpoint="https://api.openai.com/v1",
            api_key="sk-xyz",
            model_name="gpt-4o-mini",
        )
        result = filter_available([m])
        assert len(result) == 1 and result[0].name == "gpt-4o-mini"

    def test_filter_by_names_with_adhoc(self):
        m = ModelEntry.adhoc(
            endpoint="https://api.example.com/v1",
            api_key="sk-123",
            model_name="x-model",
        )
        result = filter_by_names([m], ["x-model"])
        assert len(result) == 1 and result[0].name == "x-model"

