"""Tests for skilleval.runner — helper functions (no async, no I/O)."""

from __future__ import annotations

import pytest

from skilleval.models import ModelResult
from skilleval.runner import _aggregate_trials, _clean_output, _compute_recommendation

from conftest import make_trial


# ── _clean_output ────────────────────────────────────────────────────────


class TestCleanOutput:
    def test_strips_think_tags(self):
        text = '<think>reasoning here</think>\n{"answer": 42}'
        assert _clean_output(text) == '{"answer": 42}'

    def test_strips_reasoning_tags(self):
        text = '<reasoning>chain of thought</reasoning>\n{"answer": 42}'
        assert _clean_output(text) == '{"answer": 42}'

    def test_strips_thinking_tags(self):
        text = "<thinking>deep thought</thinking>\nresult"
        assert _clean_output(text) == "result"

    def test_strips_markdown_fences(self):
        text = '```json\n{"a": 1}\n```'
        assert _clean_output(text) == '{"a": 1}'

    def test_strips_plain_fences(self):
        text = "```\nhello\n```"
        assert _clean_output(text) == "hello"

    def test_strips_tags_then_fences(self):
        text = '<think>thought</think>\n```json\n{"a": 1}\n```'
        assert _clean_output(text) == '{"a": 1}'

    def test_strips_whitespace(self):
        text = "  \n  answer  \n  "
        assert _clean_output(text) == "answer"

    def test_empty_string(self):
        assert _clean_output("") == ""

    def test_no_cleanup_needed(self):
        text = '{"key": "value"}'
        assert _clean_output(text) == '{"key": "value"}'


# ── _aggregate_trials ────────────────────────────────────────────────────


class TestAggregateTrials:
    def test_empty_list(self):
        result = _aggregate_trials("m", [])
        assert result.model == "m"
        assert result.pass_rate == 0.0
        assert result.trials == []
        assert result.avg_cost == 0.0

    def test_all_passing(self):
        trials = [
            make_trial(passed=True, cost=0.002, latency=0.5),
            make_trial(passed=True, cost=0.004, latency=1.0),
        ]
        result = _aggregate_trials("m", trials)
        assert result.pass_rate == 1.0
        assert result.avg_cost == pytest.approx(0.003)
        assert result.avg_latency == pytest.approx(0.75)
        assert result.total_cost == pytest.approx(0.006)

    def test_mixed_results(self):
        trials = [
            make_trial(passed=True, cost=0.001, latency=0.5),
            make_trial(passed=False, cost=0.001, latency=0.5),
            make_trial(passed=True, cost=0.001, latency=0.5),
        ]
        result = _aggregate_trials("m", trials)
        assert result.pass_rate == pytest.approx(2 / 3)

    def test_all_failing(self):
        trials = [make_trial(passed=False), make_trial(passed=False)]
        result = _aggregate_trials("m", trials)
        assert result.pass_rate == 0.0

    def test_cost_and_latency_averages(self):
        trials = [
            make_trial(cost=0.010, latency=1.0),
            make_trial(cost=0.020, latency=2.0),
            make_trial(cost=0.030, latency=3.0),
        ]
        result = _aggregate_trials("m", trials)
        assert result.avg_cost == pytest.approx(0.020)
        assert result.avg_latency == pytest.approx(2.0)
        assert result.total_cost == pytest.approx(0.060)


# ── _compute_recommendation ──────────────────────────────────────────────


def _make_model_result(
    model: str,
    pass_rate: float,
    avg_cost: float,
    context_window: int = 0,
) -> ModelResult:
    return ModelResult(
        model=model,
        pass_rate=pass_rate,
        trials=[],
        avg_cost=avg_cost,
        avg_latency=0.0,
        total_cost=0.0,
        context_window=context_window,
    )


def _to_candidates(results: list[ModelResult]) -> list[tuple[str, ModelResult]]:
    """Convert a list of ModelResults to (label, result) pairs for _compute_recommendation."""
    return [(r.model, r) for r in results]


class TestComputeRecommendation:
    def test_no_results(self):
        assert _compute_recommendation([], num_trials=5) is None

    def test_no_perfect_model(self):
        results = [_make_model_result("m1", 0.8, 0.001)]
        assert _compute_recommendation(_to_candidates(results), num_trials=5) is None

    def test_one_perfect_model(self):
        results = [_make_model_result("m1", 1.0, 0.005)]
        rec = _compute_recommendation(_to_candidates(results), num_trials=10)
        assert rec is not None
        assert "m1" in rec
        assert "$0.005000" in rec

    def test_cheapest_of_multiple_perfect(self):
        results = [
            _make_model_result("expensive", 1.0, 0.010),
            _make_model_result("cheap", 1.0, 0.002),
            _make_model_result("mid", 1.0, 0.005),
        ]
        rec = _compute_recommendation(_to_candidates(results), num_trials=10)
        assert rec is not None
        assert "cheap" in rec

    def test_warning_when_trials_under_10(self):
        results = [_make_model_result("m1", 1.0, 0.001)]
        rec = _compute_recommendation(_to_candidates(results), num_trials=5)
        assert rec is not None
        assert "warning" in rec.lower()
        assert "trials < 10" in rec

    def test_no_warning_at_10_trials(self):
        results = [_make_model_result("m1", 1.0, 0.001)]
        rec = _compute_recommendation(_to_candidates(results), num_trials=10)
        assert rec is not None
        assert "warning" not in rec.lower()

    def test_imperfect_ignored(self):
        results = [
            _make_model_result("bad", 0.9, 0.0001),
            _make_model_result("good", 1.0, 0.010),
        ]
        rec = _compute_recommendation(_to_candidates(results), num_trials=10)
        assert rec is not None
        assert "good" in rec

    def test_tiebreaker_prefers_larger_context_at_equal_cost(self):
        results = [
            _make_model_result("small-ctx", 1.0, 0.005, context_window=32_000),
            _make_model_result("large-ctx", 1.0, 0.005, context_window=128_000),
        ]
        rec = _compute_recommendation(_to_candidates(results), num_trials=10)
        assert rec is not None
        assert "large-ctx" in rec

    def test_recommendation_includes_context_window_info(self):
        results = [_make_model_result("m1", 1.0, 0.005, context_window=131_072)]
        rec = _compute_recommendation(_to_candidates(results), num_trials=10)
        assert rec is not None
        assert "131,072 ctx" in rec

    def test_recommendation_no_context_when_zero(self):
        results = [_make_model_result("m1", 1.0, 0.005, context_window=0)]
        rec = _compute_recommendation(_to_candidates(results), num_trials=10)
        assert rec is not None
        assert "ctx" not in rec


class TestAggregateTrialsContextWindow:
    def test_aggregate_with_context_window(self):
        trials = [make_trial(passed=True, cost=0.002, latency=0.5)]
        result = _aggregate_trials("m", trials, context_window=64_000)
        assert result.context_window == 64_000

    def test_aggregate_without_context_window_defaults_to_zero(self):
        trials = [make_trial(passed=True, cost=0.002, latency=0.5)]
        result = _aggregate_trials("m", trials)
        assert result.context_window == 0

    def test_aggregate_empty_with_context_window(self):
        result = _aggregate_trials("m", [], context_window=128_000)
        assert result.context_window == 128_000
