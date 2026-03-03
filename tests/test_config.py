"""Tests for skilleval.config — loading tasks and filtering models."""

from __future__ import annotations

from pathlib import Path

import pytest

from skilleval.config import filter_available, filter_by_names, load_task
from skilleval.models import ModelEntry


# ── load_task ────────────────────────────────────────────────────────────


class TestLoadTask:
    def test_valid_task_dir(self, sample_task_dir: Path):
        task = load_task(sample_task_dir)
        assert task.config.comparator == "json_exact"
        assert task.config.trials == 3
        assert len(task.input_files) == 1
        assert len(task.expected_files) == 1
        assert task.skill == "You are a greeting generator."
        assert task.prompt is None

    def test_missing_config_yaml(self, tmp_path: Path):
        task_dir = tmp_path / "bad-task"
        task_dir.mkdir()
        with pytest.raises(FileNotFoundError, match="No config.yaml"):
            load_task(task_dir)

    def test_empty_input_dir(self, tmp_path: Path):
        task_dir = tmp_path / "task"
        task_dir.mkdir()
        (task_dir / "config.yaml").write_text("comparator: json_exact\n")
        (task_dir / "input").mkdir()
        (task_dir / "expected").mkdir()
        (task_dir / "expected" / "out.json").write_text("{}")
        with pytest.raises(ValueError, match="input/ directory missing or empty"):
            load_task(task_dir)

    def test_empty_expected_dir(self, tmp_path: Path):
        task_dir = tmp_path / "task"
        task_dir.mkdir()
        (task_dir / "config.yaml").write_text("comparator: json_exact\n")
        (task_dir / "input").mkdir()
        (task_dir / "input" / "in.json").write_text("{}")
        (task_dir / "expected").mkdir()
        with pytest.raises(ValueError, match="expected/ directory missing or empty"):
            load_task(task_dir)

    def test_with_prompt_md(self, sample_task_dir: Path):
        (sample_task_dir / "prompt.md").write_text("Extract data from the invoice.")
        task = load_task(sample_task_dir)
        assert task.prompt == "Extract data from the invoice."

    def test_with_meta_skills(self, sample_task_dir: Path):
        (sample_task_dir / "meta-skill-concise.md").write_text("Be concise.")
        (sample_task_dir / "meta-skill-detailed.md").write_text("Be detailed.")
        task = load_task(sample_task_dir)
        assert "concise" in task.meta_skills
        assert "detailed" in task.meta_skills
        assert task.meta_skills["concise"] == "Be concise."

    def test_empty_config_yaml_uses_defaults(self, tmp_path: Path):
        task_dir = tmp_path / "task"
        task_dir.mkdir()
        (task_dir / "config.yaml").write_text("")
        (task_dir / "input").mkdir()
        (task_dir / "input" / "in.json").write_text("{}")
        (task_dir / "expected").mkdir()
        (task_dir / "expected" / "out.json").write_text("{}")
        task = load_task(task_dir)
        assert task.config.comparator == "json_exact"
        assert task.config.trials == 5


# ── filter_available ─────────────────────────────────────────────────────


class TestFilterAvailable:
    def test_filters_by_env_var(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("KEY_A", "secret")
        monkeypatch.delenv("KEY_B", raising=False)

        models = [
            ModelEntry(
                name="a",
                provider="p",
                endpoint="http://x",
                input_cost_per_m=0,
                output_cost_per_m=0,
                env_key="KEY_A",
            ),
            ModelEntry(
                name="b",
                provider="p",
                endpoint="http://x",
                input_cost_per_m=0,
                output_cost_per_m=0,
                env_key="KEY_B",
            ),
        ]
        result = filter_available(models)
        assert len(result) == 1
        assert result[0].name == "a"

    def test_no_keys_set(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("NOPE", raising=False)
        models = [
            ModelEntry(
                name="x",
                provider="p",
                endpoint="http://x",
                input_cost_per_m=0,
                output_cost_per_m=0,
                env_key="NOPE",
            ),
        ]
        assert filter_available(models) == []


# ── filter_by_names ──────────────────────────────────────────────────────


class TestFilterByNames:
    def test_matching_names(self):
        models = [
            ModelEntry(
                name="alpha",
                provider="p",
                endpoint="http://x",
                input_cost_per_m=0,
                output_cost_per_m=0,
                env_key="K",
            ),
            ModelEntry(
                name="beta",
                provider="p",
                endpoint="http://x",
                input_cost_per_m=0,
                output_cost_per_m=0,
                env_key="K",
            ),
        ]
        result = filter_by_names(models, ["beta"])
        assert len(result) == 1
        assert result[0].name == "beta"

    def test_missing_name_raises(self):
        models = [
            ModelEntry(
                name="alpha",
                provider="p",
                endpoint="http://x",
                input_cost_per_m=0,
                output_cost_per_m=0,
                env_key="K",
            ),
        ]
        with pytest.raises(ValueError, match="not found in catalog"):
            filter_by_names(models, ["alpha", "gamma"])
