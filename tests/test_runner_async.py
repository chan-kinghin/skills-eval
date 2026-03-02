"""Async tests for skilleval.runner — run_mode1, run_mode2, run_mode3 orchestrators."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from skilleval.engine import ExecutionEngine
from skilleval.models import ModelEntry, TaskConfig, TaskFolder, TrialResult


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


def _make_trial_result(
    model: str = "test-model",
    trial_number: int = 1,
    passed: bool = True,
    output_text: str = '{"greeting": "Hello Alice"}',
    cost: float = 0.001,
    latency: float = 0.5,
    error: str | None = None,
    finish_reason: str = "stop",
    input_tokens: int = 10,
    output_tokens: int = 5,
) -> TrialResult:
    return TrialResult(
        model=model,
        trial_number=trial_number,
        passed=passed,
        output_text=output_text,
        cost=cost,
        latency_seconds=latency,
        error=error,
        finish_reason=finish_reason,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


def _make_task_folder_mode1(tmp_path: Path) -> TaskFolder:
    """Create a Mode 1 task folder (with skill.md)."""
    task = tmp_path / "task-m1"
    task.mkdir()
    (task / "config.yaml").write_text("comparator: json_exact\ntrials: 3\n")
    (task / "input").mkdir()
    (task / "input" / "data.json").write_text('{"name": "Alice"}')
    (task / "expected").mkdir()
    (task / "expected" / "result.json").write_text('{"greeting": "Hello Alice"}')
    (task / "skill.md").write_text("You are a greeting generator.")

    return TaskFolder(
        path=task,
        input_files=[task / "input" / "data.json"],
        expected_files=[task / "expected" / "result.json"],
        config=TaskConfig(comparator="json_exact", trials=3),
        skill="You are a greeting generator.",
    )


def _make_task_folder_mode2(tmp_path: Path) -> TaskFolder:
    """Create a Mode 2 task folder (with prompt.md, no skill.md)."""
    task = tmp_path / "task-m2"
    task.mkdir()
    (task / "config.yaml").write_text("comparator: json_exact\ntrials: 2\n")
    (task / "input").mkdir()
    (task / "input" / "data.json").write_text('{"name": "Alice"}')
    (task / "expected").mkdir()
    (task / "expected" / "result.json").write_text('{"greeting": "Hello Alice"}')
    (task / "prompt.md").write_text("Generate a greeting for the given name.")

    return TaskFolder(
        path=task,
        input_files=[task / "input" / "data.json"],
        expected_files=[task / "expected" / "result.json"],
        config=TaskConfig(comparator="json_exact", trials=2),
        prompt="Generate a greeting for the given name.",
    )


def _make_task_folder_mode3(tmp_path: Path) -> TaskFolder:
    """Create a Mode 3 task folder (with prompt.md and meta-skills)."""
    task = tmp_path / "task-m3"
    task.mkdir()
    (task / "config.yaml").write_text("comparator: json_exact\ntrials: 2\n")
    (task / "input").mkdir()
    (task / "input" / "data.json").write_text('{"name": "Alice"}')
    (task / "expected").mkdir()
    (task / "expected" / "result.json").write_text('{"greeting": "Hello Alice"}')
    (task / "prompt.md").write_text("Generate a greeting for the given name.")
    (task / "meta-skill-concise.md").write_text("Write concise skills.")
    (task / "meta-skill-verbose.md").write_text("Write detailed verbose skills.")

    return TaskFolder(
        path=task,
        input_files=[task / "input" / "data.json"],
        expected_files=[task / "expected" / "result.json"],
        config=TaskConfig(comparator="json_exact", trials=2),
        prompt="Generate a greeting for the given name.",
        meta_skills={
            "concise": "Write concise skills.",
            "verbose": "Write detailed verbose skills.",
        },
    )


# ── Mode 1 tests ─────────────────────────────────────────────────────────


class TestRunMode1:
    """Tests for run_mode1 — given skill, sweep executor models."""

    @patch("skilleval.runner.ResultWriter")
    @patch("skilleval.runner.console")
    @patch("skilleval.runner.create_progress")
    async def test_basic_flow_correct_output(
        self,
        mock_progress: MagicMock,
        mock_console: MagicMock,
        mock_writer_cls: MagicMock,
        tmp_path: Path,
    ):
        """Mode 1 with correct output should yield 100% pass rate."""
        from skilleval.runner import run_mode1

        task = _make_task_folder_mode1(tmp_path)
        model = _make_model()

        # 3 trials, all return the expected output
        trial_results = [
            _make_trial_result(trial_number=i, output_text='{"greeting": "Hello Alice"}')
            for i in range(1, 4)
        ]

        mock_engine = AsyncMock(spec=ExecutionEngine)
        mock_engine.execute_batch = AsyncMock(return_value=trial_results)

        # Mock progress context manager
        mock_progress_instance = MagicMock()
        mock_progress_instance.__enter__ = MagicMock(return_value=mock_progress_instance)
        mock_progress_instance.__exit__ = MagicMock(return_value=False)
        mock_progress_instance.add_task = MagicMock(return_value=0)
        mock_progress.return_value = mock_progress_instance

        # Mock ResultWriter instance
        mock_writer = MagicMock()
        mock_writer.run_dir = tmp_path / ".skilleval" / "run-test"
        mock_writer_cls.return_value = mock_writer

        summary = await run_mode1(task, [model], mock_engine, parallel=5)

        assert summary.mode == "run"
        assert len(summary.model_results) == 1
        mr = summary.model_results[0]
        assert mr.model == "test-model"
        assert mr.pass_rate == 1.0
        assert mr.trials[0].passed is True
        mock_engine.execute_batch.assert_awaited_once()

    @patch("skilleval.runner.ResultWriter")
    @patch("skilleval.runner.console")
    @patch("skilleval.runner.create_progress")
    async def test_comparison_failure_reduces_pass_rate(
        self,
        mock_progress: MagicMock,
        mock_console: MagicMock,
        mock_writer_cls: MagicMock,
        tmp_path: Path,
    ):
        """Mode 1 with wrong output should yield reduced pass rate."""
        from skilleval.runner import run_mode1

        task = _make_task_folder_mode1(tmp_path)
        model = _make_model()

        # 3 trials: 1 correct, 2 wrong
        trial_results = [
            _make_trial_result(trial_number=1, output_text='{"greeting": "Hello Alice"}'),
            _make_trial_result(trial_number=2, output_text='{"greeting": "Wrong"}'),
            _make_trial_result(trial_number=3, output_text='{"greeting": "Also Wrong"}'),
        ]

        mock_engine = AsyncMock(spec=ExecutionEngine)
        mock_engine.execute_batch = AsyncMock(return_value=trial_results)

        mock_progress_instance = MagicMock()
        mock_progress_instance.__enter__ = MagicMock(return_value=mock_progress_instance)
        mock_progress_instance.__exit__ = MagicMock(return_value=False)
        mock_progress_instance.add_task = MagicMock(return_value=0)
        mock_progress.return_value = mock_progress_instance

        mock_writer = MagicMock()
        mock_writer.run_dir = tmp_path / ".skilleval" / "run-test"
        mock_writer_cls.return_value = mock_writer

        summary = await run_mode1(task, [model], mock_engine, parallel=5)

        assert len(summary.model_results) == 1
        mr = summary.model_results[0]
        # Only trial 1 matches expected, trials 2 and 3 do not
        assert mr.pass_rate < 1.0
        # At least one trial should have passed
        passed_count = sum(1 for t in mr.trials if t.passed)
        assert passed_count == 1

    async def test_missing_skill_raises_value_error(self, tmp_path: Path):
        """Mode 1 without skill.md should raise ValueError."""
        from skilleval.runner import run_mode1

        task = TaskFolder(
            path=tmp_path,
            input_files=[tmp_path / "input" / "data.json"],
            expected_files=[tmp_path / "expected" / "result.json"],
            config=TaskConfig(),
            skill=None,  # No skill!
        )
        model = _make_model()
        mock_engine = AsyncMock(spec=ExecutionEngine)

        with pytest.raises(ValueError, match="Mode 1 requires skill.md"):
            await run_mode1(task, [model], mock_engine, parallel=5)


# ── Mode 2 tests ─────────────────────────────────────────────────────────


class TestRunMode2:
    """Tests for run_mode2 — creator x executor matrix."""

    @patch("skilleval.runner.ResultWriter")
    @patch("skilleval.runner.console")
    @patch("skilleval.runner.create_progress")
    async def test_basic_flow(
        self,
        mock_progress: MagicMock,
        mock_console: MagicMock,
        mock_writer_cls: MagicMock,
        tmp_path: Path,
    ):
        """Mode 2 basic flow: skill generation + execution."""
        from skilleval.runner import run_mode2

        task = _make_task_folder_mode2(tmp_path)
        creator = _make_model(name="creator-model")
        executor = _make_model(name="executor-model")

        # Phase 1: Skill generation (1 creator = 1 result)
        skill_result = _make_trial_result(
            model="creator-model",
            output_text="You are a greeting generator. Output JSON with key 'greeting'.",
        )
        # Phase 2: Execution (1 creator x 1 executor x 2 trials)
        exec_results = [
            _make_trial_result(
                model="executor-model",
                trial_number=i,
                output_text='{"greeting": "Hello Alice"}',
            )
            for i in range(1, 3)
        ]

        call_count = 0

        async def mock_execute_batch(specs, on_progress=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Phase 1: skill generation
                if on_progress:
                    on_progress(skill_result)
                return [skill_result]
            else:
                # Phase 2: execution
                for r in exec_results:
                    if on_progress:
                        on_progress(r)
                return exec_results

        mock_engine = AsyncMock(spec=ExecutionEngine)
        mock_engine.execute_batch = AsyncMock(side_effect=mock_execute_batch)

        mock_progress_instance = MagicMock()
        mock_progress_instance.__enter__ = MagicMock(return_value=mock_progress_instance)
        mock_progress_instance.__exit__ = MagicMock(return_value=False)
        mock_progress_instance.add_task = MagicMock(return_value=0)
        mock_progress.return_value = mock_progress_instance

        mock_writer = MagicMock()
        mock_writer.run_dir = tmp_path / ".skilleval" / "run-test"
        mock_writer_cls.return_value = mock_writer

        summary = await run_mode2(task, [creator], [executor], mock_engine)

        assert summary.mode == "matrix"
        assert len(summary.matrix_results) == 1
        cell = summary.matrix_results[0]
        assert cell.creator == "creator-model"
        assert cell.executor == "executor-model"
        assert cell.result.pass_rate == 1.0

    async def test_missing_prompt_raises_value_error(self, tmp_path: Path):
        """Mode 2 without prompt.md should raise ValueError."""
        from skilleval.runner import run_mode2

        task = TaskFolder(
            path=tmp_path,
            input_files=[tmp_path / "input" / "data.json"],
            expected_files=[tmp_path / "expected" / "result.json"],
            config=TaskConfig(),
            prompt=None,  # No prompt!
        )
        creator = _make_model(name="creator")
        executor = _make_model(name="executor")
        mock_engine = AsyncMock(spec=ExecutionEngine)

        with pytest.raises(ValueError, match="Mode 2 requires prompt.md"):
            await run_mode2(task, [creator], [executor], mock_engine)


# ── Mode 3 tests ─────────────────────────────────────────────────────────


class TestRunMode3:
    """Tests for run_mode3 — meta-skill x creator x executor chain."""

    @patch("skilleval.runner.ResultWriter")
    @patch("skilleval.runner.console")
    @patch("skilleval.runner.create_progress")
    async def test_basic_flow(
        self,
        mock_progress: MagicMock,
        mock_console: MagicMock,
        mock_writer_cls: MagicMock,
        tmp_path: Path,
    ):
        """Mode 3 basic flow: meta-skill guided skill generation + execution."""
        from skilleval.runner import run_mode3

        task = _make_task_folder_mode3(tmp_path)
        creator = _make_model(name="creator-model")
        executor = _make_model(name="executor-model")

        # Phase 1: Skill generation (2 meta-skills x 1 creator = 2 results)
        skill_results = [
            _make_trial_result(
                model="creator-model",
                output_text="Concise greeting skill.",
            ),
            _make_trial_result(
                model="creator-model",
                output_text="Verbose greeting skill with detailed instructions.",
            ),
        ]
        # Phase 2: Execution (2 meta-skills x 1 creator x 1 executor x 2 trials = 4)
        exec_results = [
            _make_trial_result(
                model="executor-model",
                trial_number=i,
                output_text='{"greeting": "Hello Alice"}',
            )
            for i in range(1, 5)
        ]

        call_count = 0

        async def mock_execute_batch(specs, on_progress=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Phase 1: skill generation
                for r in skill_results:
                    if on_progress:
                        on_progress(r)
                return skill_results
            else:
                # Phase 2: execution
                for r in exec_results:
                    if on_progress:
                        on_progress(r)
                return exec_results

        mock_engine = AsyncMock(spec=ExecutionEngine)
        mock_engine.execute_batch = AsyncMock(side_effect=mock_execute_batch)

        mock_progress_instance = MagicMock()
        mock_progress_instance.__enter__ = MagicMock(return_value=mock_progress_instance)
        mock_progress_instance.__exit__ = MagicMock(return_value=False)
        mock_progress_instance.add_task = MagicMock(return_value=0)
        mock_progress.return_value = mock_progress_instance

        mock_writer = MagicMock()
        mock_writer.run_dir = tmp_path / ".skilleval" / "run-test"
        mock_writer_cls.return_value = mock_writer

        summary = await run_mode3(
            task,
            meta_skill_names=["concise", "verbose"],
            creators=[creator],
            executors=[executor],
            engine=mock_engine,
        )

        assert summary.mode == "chain"
        assert len(summary.chain_results) == 2
        # Check that both meta-skills are represented
        ms_names = {c.meta_skill_name for c in summary.chain_results}
        assert ms_names == {"concise", "verbose"}
        for cell in summary.chain_results:
            assert cell.creator == "creator-model"
            assert cell.executor == "executor-model"
            assert cell.result.pass_rate == 1.0

    async def test_missing_prompt_raises_value_error(self, tmp_path: Path):
        """Mode 3 without prompt.md should raise ValueError."""
        from skilleval.runner import run_mode3

        task = TaskFolder(
            path=tmp_path,
            input_files=[tmp_path / "input" / "data.json"],
            expected_files=[tmp_path / "expected" / "result.json"],
            config=TaskConfig(),
            prompt=None,  # No prompt!
        )
        mock_engine = AsyncMock(spec=ExecutionEngine)

        with pytest.raises(ValueError, match="Mode 3 requires prompt.md"):
            await run_mode3(
                task,
                meta_skill_names=["test"],
                creators=[_make_model()],
                executors=[_make_model()],
                engine=mock_engine,
            )

    async def test_missing_meta_skill_raises_value_error(self, tmp_path: Path):
        """Mode 3 with unknown meta-skill name should raise ValueError."""
        from skilleval.runner import run_mode3

        task = _make_task_folder_mode3(tmp_path)
        mock_engine = AsyncMock(spec=ExecutionEngine)

        with pytest.raises(ValueError, match="Meta-skill 'nonexistent' not found"):
            await run_mode3(
                task,
                meta_skill_names=["nonexistent"],
                creators=[_make_model()],
                executors=[_make_model()],
                engine=mock_engine,
            )
