"""Shared fixtures for SkillEval tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from skilleval.models import ModelEntry, TrialResult


@pytest.fixture()
def sample_model() -> ModelEntry:
    """A minimal model entry for testing."""
    return ModelEntry(
        name="test-model",
        provider="test-provider",
        endpoint="https://api.test.example.com/v1",
        input_cost_per_m=0.5,
        output_cost_per_m=1.5,
        env_key="TEST_API_KEY",
    )


@pytest.fixture()
def sample_model_b() -> ModelEntry:
    """A second model entry for multi-model tests."""
    return ModelEntry(
        name="cheap-model",
        provider="test-provider",
        endpoint="https://api.test.example.com/v1",
        input_cost_per_m=0.1,
        output_cost_per_m=0.3,
        env_key="TEST_API_KEY_B",
    )


@pytest.fixture()
def sample_task_dir(tmp_path: Path) -> Path:
    """Create a minimal valid task directory structure."""
    task = tmp_path / "my-task"
    task.mkdir()

    (task / "config.yaml").write_text("comparator: json_exact\ntrials: 3\n")
    (task / "input").mkdir()
    (task / "input" / "data.json").write_text('{"name": "Alice"}')
    (task / "expected").mkdir()
    (task / "expected" / "result.json").write_text('{"greeting": "Hello Alice"}')
    (task / "skill.md").write_text("You are a greeting generator.")

    return task


def make_trial(
    model: str = "test-model",
    trial_number: int = 1,
    passed: bool = True,
    cost: float = 0.001,
    latency: float = 0.5,
    **kwargs,
) -> TrialResult:
    """Helper to build a TrialResult with sensible defaults."""
    return TrialResult(
        model=model,
        trial_number=trial_number,
        passed=passed,
        cost=cost,
        latency_seconds=latency,
        **kwargs,
    )
