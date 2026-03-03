"""Tests for skilleval.models — Pydantic models and dataclasses."""

from __future__ import annotations

from skilleval.models import (
    ChatResponse,
    ChainCell,
    MatrixCell,
    ModelEntry,
    ModelResult,
    RunSummary,
    TaskConfig,
    TrialResult,
)


# ── ModelEntry ───────────────────────────────────────────────────────────


class TestModelEntry:
    def test_required_fields(self):
        m = ModelEntry(
            name="qwen-turbo",
            provider="qwen",
            endpoint="https://dashscope.aliyuncs.com/compatible-mode/v1",
            input_cost_per_m=0.3,
            output_cost_per_m=0.6,
            env_key="DASHSCOPE_API_KEY",
        )
        assert m.name == "qwen-turbo"
        assert m.provider == "qwen"

    def test_default_context_window(self):
        m = ModelEntry(
            name="m",
            provider="p",
            endpoint="http://x",
            input_cost_per_m=0,
            output_cost_per_m=0,
            env_key="K",
        )
        assert m.context_window == 128_000

    def test_custom_context_window(self):
        m = ModelEntry(
            name="m",
            provider="p",
            endpoint="http://x",
            input_cost_per_m=0,
            output_cost_per_m=0,
            env_key="K",
            context_window=32_000,
        )
        assert m.context_window == 32_000


# ── TaskConfig ───────────────────────────────────────────────────────────


class TestTaskConfig:
    def test_all_defaults(self):
        c = TaskConfig()
        assert c.comparator == "json_exact"
        assert c.custom_script is None
        assert c.trials == 5
        assert c.timeout == 60
        assert c.temperature == 0.0
        assert c.max_tokens == 4096
        assert c.output_format == "json"

    def test_override_values(self):
        c = TaskConfig(comparator="csv_ordered", trials=10, timeout=120)
        assert c.comparator == "csv_ordered"
        assert c.trials == 10
        assert c.timeout == 120


# ── TrialResult ──────────────────────────────────────────────────────────


class TestTrialResult:
    def test_defaults(self):
        t = TrialResult(model="m", trial_number=1, passed=True)
        assert t.output_text == ""
        assert t.diff is None
        assert t.input_tokens == 0
        assert t.output_tokens == 0
        assert t.cost == 0.0
        assert t.latency_seconds == 0.0
        assert t.error is None
        assert t.finish_reason is None

    def test_with_error(self):
        t = TrialResult(model="m", trial_number=1, passed=False, error="timeout")
        assert not t.passed
        assert t.error == "timeout"


# ── ChatResponse ─────────────────────────────────────────────────────────


class TestChatResponse:
    def test_construction(self):
        r = ChatResponse(
            content="hello",
            input_tokens=10,
            output_tokens=5,
            latency_seconds=0.3,
        )
        assert r.content == "hello"
        assert r.model_version is None
        assert r.finish_reason is None

    def test_with_optional_fields(self):
        r = ChatResponse(
            content="hi",
            input_tokens=1,
            output_tokens=1,
            latency_seconds=0.1,
            model_version="qwen-turbo-2025-01",
            finish_reason="stop",
        )
        assert r.model_version == "qwen-turbo-2025-01"
        assert r.finish_reason == "stop"


# ── RunSummary serialization ─────────────────────────────────────────────


class TestRunSummary:
    def test_serialization_roundtrip(self):
        trial = TrialResult(model="m", trial_number=1, passed=True, cost=0.001)
        mr = ModelResult(
            model="m",
            pass_rate=1.0,
            trials=[trial],
            avg_cost=0.001,
            avg_latency=0.5,
            total_cost=0.001,
        )
        summary = RunSummary(
            mode="run",
            task_path="/tmp/task",
            timestamp="2026-01-01T00:00:00",
            model_results=[mr],
            recommendation="m ($0.001000/run)",
        )
        data = summary.model_dump()
        restored = RunSummary(**data)
        assert restored.mode == "run"
        assert len(restored.model_results) == 1
        assert restored.recommendation == "m ($0.001000/run)"

    def test_empty_defaults(self):
        s = RunSummary(mode="run", task_path="/x", timestamp="t")
        assert s.model_results == []
        assert s.matrix_results == []
        assert s.chain_results == []
        assert s.recommendation is None


# ── MatrixCell / ChainCell ───────────────────────────────────────────────


class TestMatrixCell:
    def test_construction(self):
        trial = TrialResult(model="exec", trial_number=1, passed=True)
        mr = ModelResult(
            model="exec",
            pass_rate=1.0,
            trials=[trial],
            avg_cost=0.0,
            avg_latency=0.0,
            total_cost=0.0,
        )
        cell = MatrixCell(
            creator="creator-m",
            executor="exec",
            generated_skill="do X",
            result=mr,
        )
        assert cell.creator == "creator-m"
        assert cell.executor == "exec"


class TestChainCell:
    def test_construction(self):
        trial = TrialResult(model="exec", trial_number=1, passed=True)
        mr = ModelResult(
            model="exec",
            pass_rate=1.0,
            trials=[trial],
            avg_cost=0.0,
            avg_latency=0.0,
            total_cost=0.0,
        )
        cell = ChainCell(
            meta_skill_name="ms1",
            creator="c",
            executor="exec",
            generated_skill="do Y",
            result=mr,
        )
        assert cell.meta_skill_name == "ms1"
