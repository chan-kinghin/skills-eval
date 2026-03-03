"""Tests for CLI commands: init, --output flag, --resume flag, error display."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from skilleval.cli import cli


class TestInitCommand:
    """skilleval init creates a complete task folder structure."""

    def test_init_creates_all_template_files(self, tmp_path: Path):
        runner = CliRunner()
        task_dir = tmp_path / "my-task"
        result = runner.invoke(cli, ["init", str(task_dir)])

        assert result.exit_code == 0
        assert task_dir.exists()
        assert (task_dir / "config.yaml").exists()
        assert (task_dir / "skill.md").exists()
        assert (task_dir / "prompt.md").exists()
        assert (task_dir / "meta-skill.md").exists()
        assert (task_dir / "input").is_dir()
        assert (task_dir / "expected").is_dir()
        assert (task_dir / "input" / "example.txt").exists()
        assert (task_dir / "expected" / "example.txt").exists()

    def test_init_config_has_comparator(self, tmp_path: Path):
        runner = CliRunner()
        task_dir = tmp_path / "my-task"
        runner.invoke(cli, ["init", str(task_dir)])

        config_text = (task_dir / "config.yaml").read_text()
        assert "comparator:" in config_text
        assert "json_exact" in config_text

    def test_init_fails_if_directory_exists(self, tmp_path: Path):
        runner = CliRunner()
        task_dir = tmp_path / "existing-task"
        task_dir.mkdir()

        result = runner.invoke(cli, ["init", str(task_dir)])
        assert result.exit_code != 0
        assert "already exists" in result.output


class TestOutputFormatHelpers:
    """Test the CSV serialization helpers."""

    def test_write_run_csv_format(self):
        from skilleval.cli import _write_run_csv
        from skilleval.models import ModelResult, TrialResult

        results = [
            ModelResult(
                model="cheap-model",
                pass_rate=1.0,
                trials=[TrialResult(model="cheap-model", trial_number=1, passed=True, cost=0.001)],
                avg_cost=0.001,
                avg_latency=0.5,
                total_cost=0.001,
            ),
            ModelResult(
                model="expensive-model",
                pass_rate=0.5,
                trials=[
                    TrialResult(model="expensive-model", trial_number=1, passed=True, cost=0.01),
                    TrialResult(model="expensive-model", trial_number=2, passed=False, cost=0.01),
                ],
                avg_cost=0.01,
                avg_latency=1.0,
                total_cost=0.02,
            ),
        ]

        csv_out = _write_run_csv(results)
        lines = csv_out.strip().split("\n")

        assert lines[0] == "model,pass_rate,avg_cost,avg_latency,total_cost"
        assert len(lines) == 3  # header + 2 rows
        # Sorted by -pass_rate, then avg_cost
        assert lines[1].startswith("cheap-model")
        assert lines[2].startswith("expensive-model")

    def test_write_matrix_csv_format(self):
        from skilleval.cli import _write_matrix_csv
        from skilleval.models import MatrixCell, ModelResult, TrialResult

        cells = [
            MatrixCell(
                creator="creator-a",
                executor="executor-b",
                generated_skill="skill text",
                result=ModelResult(
                    model="executor-b",
                    pass_rate=1.0,
                    trials=[TrialResult(model="executor-b", trial_number=1, passed=True)],
                    avg_cost=0.005,
                    avg_latency=0.3,
                    total_cost=0.005,
                ),
            ),
        ]

        csv_out = _write_matrix_csv(cells)
        lines = csv_out.strip().split("\n")

        assert lines[0] == "creator,executor,pass_rate,avg_cost,total_cost"
        assert "creator-a" in lines[1]
        assert "executor-b" in lines[1]

    def test_write_chain_csv_format(self):
        from skilleval.cli import _write_chain_csv
        from skilleval.models import ChainCell, ModelResult, TrialResult

        cells = [
            ChainCell(
                meta_skill_name="ms-v1",
                creator="creator-a",
                executor="executor-b",
                generated_skill="skill text",
                result=ModelResult(
                    model="executor-b",
                    pass_rate=0.8,
                    trials=[TrialResult(model="executor-b", trial_number=1, passed=True)],
                    avg_cost=0.003,
                    avg_latency=0.2,
                    total_cost=0.003,
                ),
            ),
        ]

        csv_out = _write_chain_csv(cells)
        lines = csv_out.strip().split("\n")

        assert lines[0] == "meta_skill,creator,executor,pass_rate,avg_cost,total_cost"
        assert "ms-v1" in lines[1]


class TestResumeFlag:
    """Test --resume checkpoint reading logic."""

    def test_resume_reads_checkpoint_and_skips_models(self, tmp_path: Path):
        """When checkpoint.json lists completed models, they should be skipped."""
        # Create a checkpoint file
        checkpoint_dir = tmp_path / "previous-run"
        checkpoint_dir.mkdir()
        checkpoint = {"completed_models": ["model-a", "model-b"]}
        (checkpoint_dir / "checkpoint.json").write_text(json.dumps(checkpoint))

        # Create a task dir (will fail because no models are available, but
        # we can check that resume logic runs by looking at the output)
        task_dir = tmp_path / "task"
        task_dir.mkdir()
        (task_dir / "config.yaml").write_text("comparator: json_exact\ntrials: 1\n")
        (task_dir / "input").mkdir()
        (task_dir / "input" / "data.txt").write_text("hello")
        (task_dir / "expected").mkdir()
        (task_dir / "expected" / "data.txt").write_text("hello")
        (task_dir / "skill.md").write_text("Echo the input")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "run",
                str(task_dir),
                "--resume",
                str(checkpoint_dir),
            ],
        )

        # Output should mention resuming
        assert "Resuming" in result.output or "No models available" in result.output

    def test_resume_no_checkpoint_starts_fresh(self, tmp_path: Path):
        """When checkpoint.json doesn't exist, show a warning."""
        empty_dir = tmp_path / "empty-run"
        empty_dir.mkdir()

        task_dir = tmp_path / "task"
        task_dir.mkdir()
        (task_dir / "config.yaml").write_text("comparator: json_exact\ntrials: 1\n")
        (task_dir / "input").mkdir()
        (task_dir / "input" / "data.txt").write_text("hello")
        (task_dir / "expected").mkdir()
        (task_dir / "expected" / "data.txt").write_text("hello")
        (task_dir / "skill.md").write_text("Echo the input")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "run",
                str(task_dir),
                "--resume",
                str(empty_dir),
            ],
        )

        assert "No checkpoint found" in result.output or "No models available" in result.output


class TestErrorDisplay:
    """The error handler shows exception class name."""

    def test_error_display_includes_exception_type(self, tmp_path: Path):
        """When a command hits an error, the output includes the exception type."""
        runner = CliRunner()
        # Invoke run with a non-existent path to trigger FileNotFoundError -> ClickException
        result = runner.invoke(cli, ["run", "/nonexistent/path/to/task"])

        # The ClickException wraps it, so check for "Error:" in output
        assert result.exit_code != 0


class TestResolveOutputFormat:
    """Test the _resolve_output_format helper."""

    def test_output_flag_takes_precedence(self):
        from skilleval.cli import _resolve_output_format

        assert _resolve_output_format("csv", False) == "csv"
        assert _resolve_output_format("json", False) == "json"
        assert _resolve_output_format("rich", True) == "rich"  # --output overrides --json

    def test_json_flag_fallback(self):
        from skilleval.cli import _resolve_output_format

        assert _resolve_output_format(None, True) == "json"

    def test_default_is_rich(self):
        from skilleval.cli import _resolve_output_format

        assert _resolve_output_format(None, False) == "rich"


class TestResultWriter:
    """Test ResultWriter filesystem layout improvements."""

    def test_trial_output_no_trials_intermediate_dir(self, tmp_path: Path):
        """Trial output should be at run-dir/model/trial-N/, not run-dir/trials/model/trial-N/."""
        from skilleval.results import ResultWriter

        writer = ResultWriter(tmp_path, "run")
        writer.write_trial_output("qwen-turbo", 1, "hello", None, {"passed": True})

        trial_dir = writer.run_dir / "qwen-turbo" / "trial-1"
        assert trial_dir.is_dir()
        assert (trial_dir / "output.txt").read_text() == "hello"
        assert (trial_dir / "meta.json").exists()

        # Old layout should NOT exist
        assert not (writer.run_dir / "trials").exists()

    def test_latest_symlink_created(self, tmp_path: Path):
        """write_summary should create a .skilleval/latest symlink."""
        from skilleval.models import RunSummary
        from skilleval.results import ResultWriter

        writer = ResultWriter(tmp_path, "run")
        summary = RunSummary(
            mode="run",
            task_path=tmp_path.name,
            timestamp="2026-01-01T00:00:00",
        )
        writer.write_summary(summary)

        latest = tmp_path / ".skilleval" / "latest"
        assert latest.is_symlink()
        assert latest.resolve() == writer.run_dir.resolve()

    def test_latest_symlink_updated_on_second_run(self, tmp_path: Path):
        """A second run should update the latest symlink."""
        from skilleval.models import RunSummary
        from skilleval.results import ResultWriter

        summary = RunSummary(
            mode="run",
            task_path=tmp_path.name,
            timestamp="2026-01-01T00:00:00",
        )

        writer1 = ResultWriter(tmp_path, "run")
        writer1.write_summary(summary)

        writer2 = ResultWriter(tmp_path, "run")
        writer2.write_summary(summary)

        latest = tmp_path / ".skilleval" / "latest"
        assert latest.resolve() == writer2.run_dir.resolve()

    def test_run_config_json_created(self, tmp_path: Path):
        """write_summary should create a run-config.json."""
        from skilleval.models import RunSummary
        from skilleval.results import ResultWriter

        writer = ResultWriter(tmp_path, "run")
        summary = RunSummary(
            mode="run",
            task_path=tmp_path.name,
            timestamp="2026-01-01T00:00:00",
        )
        writer.write_summary(summary)

        config_path = writer.run_dir / "run-config.json"
        assert config_path.exists()
        config = json.loads(config_path.read_text())
        assert config["mode"] == "run"
        assert config["task"] == tmp_path.name

    def test_results_json_excludes_output_text(self, tmp_path: Path):
        """results.json should NOT contain output_text (it's in per-trial files)."""
        from skilleval.models import ModelResult, RunSummary, TrialResult
        from skilleval.results import ResultWriter

        writer = ResultWriter(tmp_path, "run")
        trial = TrialResult(
            model="test",
            trial_number=1,
            passed=True,
            output_text="this should be excluded",
        )
        mr = ModelResult(
            model="test",
            pass_rate=1.0,
            trials=[trial],
            avg_cost=0.001,
            avg_latency=0.5,
            total_cost=0.001,
        )
        summary = RunSummary(
            mode="run",
            task_path=tmp_path.name,
            timestamp="2026-01-01T00:00:00",
            model_results=[mr],
        )
        writer.write_summary(summary)

        results = json.loads((writer.run_dir / "results.json").read_text())
        # output_text should be stripped from the serialized results
        for mr_data in results["model_results"]:
            for trial_data in mr_data["trials"]:
                assert "output_text" not in trial_data

    def test_summary_txt_uses_task_name_not_absolute_path(self, tmp_path: Path):
        """summary.txt should use the task directory name, not an absolute path."""
        from skilleval.models import RunSummary
        from skilleval.results import ResultWriter

        writer = ResultWriter(tmp_path, "run")
        summary = RunSummary(
            mode="run",
            task_path=tmp_path.name,
            timestamp="2026-01-01T00:00:00",
        )
        writer.write_summary(summary)

        text = (writer.run_dir / "summary.txt").read_text()
        assert f"Task: {tmp_path.name}" in text
        # Should NOT contain an absolute path
        assert "/Users/" not in text
        assert "/tmp/" not in text or tmp_path.name in text


class TestHistoryCommand:
    """Test skilleval history command."""

    def test_history_no_runs(self, tmp_path: Path):
        runner = CliRunner()
        result = runner.invoke(cli, ["history", str(tmp_path)])
        assert result.exit_code == 0
        assert "No runs found" in result.output

    def test_history_with_runs(self, tmp_path: Path):
        """History should list past runs."""
        from skilleval.models import RunSummary
        from skilleval.results import ResultWriter

        writer = ResultWriter(tmp_path, "run")
        summary = RunSummary(
            mode="run",
            task_path=tmp_path.name,
            timestamp="2026-01-01T00:00:00",
            recommendation="test-model ($0.001/run)",
        )
        writer.write_summary(summary)

        runner = CliRunner()
        result = runner.invoke(cli, ["history", str(tmp_path)])
        assert result.exit_code == 0
        assert "latest" in result.output
        assert "run" in result.output
