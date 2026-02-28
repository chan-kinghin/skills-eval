"""Tests for skilleval.compare — comparing run summaries."""

from __future__ import annotations

import pytest
from pathlib import Path

from skilleval.compare import ComparisonEntry, ComparisonReport, compare_runs
from skilleval.models import (
    ChainCell,
    MatrixCell,
    ModelResult,
    RunSummary,
    TrialResult,
)


def _mr(model: str, pass_rate: float, avg_cost: float, avg_latency: float = 0.0) -> ModelResult:
    return ModelResult(
        model=model,
        pass_rate=pass_rate,
        trials=[TrialResult(model=model, trial_number=1, passed=True)],
        avg_cost=avg_cost,
        avg_latency=avg_latency,
        total_cost=avg_cost,
    )


def _write_summary(dir_path: Path, summary: RunSummary) -> None:
    dir_path.mkdir(parents=True, exist_ok=True)
    (dir_path / "results.json").write_text(summary.model_dump_json(indent=2))


class TestCompareRunMode:
    def test_basic_improved_regressed_new_removed(self, tmp_path: Path) -> None:
        old_dir = tmp_path / "old"
        new_dir = tmp_path / "new"

        old = RunSummary(
            mode="run",
            task_path="/task",
            timestamp="t0",
            model_results=[
                _mr("A", 0.5, 0.010, 1.0),
                _mr("B", 1.0, 0.020, 2.0),
                _mr("D", 0.7, 0.030, 3.0),  # will be removed
            ],
        )
        new = RunSummary(
            mode="run",
            task_path="/task",
            timestamp="t1",
            model_results=[
                _mr("A", 0.8, 0.015, 1.1),  # improved
                _mr("B", 0.9, 0.018, 2.1),  # regressed
                _mr("C", 0.6, 0.025, 1.5),  # new
            ],
        )

        _write_summary(old_dir, old)
        _write_summary(new_dir, new)

        report = compare_runs(old_dir, new_dir)
        assert isinstance(report, ComparisonReport)
        assert report.mode == "run"

        # summary counts only include improved/regressed/unchanged
        assert report.summary == "1 improved, 1 regressed, 0 unchanged"

        statuses = {e.model: e.status for e in report.entries}
        assert statuses["A"] == "improved"
        assert statuses["B"] == "regressed"
        assert statuses["C"] == "new"
        assert statuses["D"] == "removed"

        a_entry = next(e for e in report.entries if e.model == "A")
        assert a_entry.old_pass_rate == pytest.approx(0.5)
        assert a_entry.new_pass_rate == pytest.approx(0.8)
        assert a_entry.old_avg_cost == pytest.approx(0.010)
        assert a_entry.new_avg_cost == pytest.approx(0.015)


class TestCompareMatrixMode:
    def test_labels_and_counts(self, tmp_path: Path) -> None:
        old_dir = tmp_path / "old_m"
        new_dir = tmp_path / "new_m"

        cells_old = [
            MatrixCell(creator="c1", executor="e1", generated_skill="s1", result=_mr("e1", 0.5, 0.01)),
            MatrixCell(creator="c2", executor="e2", generated_skill="s2", result=_mr("e2", 0.9, 0.02)),
            MatrixCell(creator="c3", executor="e3", generated_skill="s3", result=_mr("e3", 0.6, 0.03)),
        ]
        cells_new = [
            MatrixCell(creator="c1", executor="e1", generated_skill="s1", result=_mr("e1", 0.7, 0.011)),  # improved
            MatrixCell(creator="c2", executor="e2", generated_skill="s2", result=_mr("e2", 0.9, 0.019)),  # unchanged rate
            MatrixCell(creator="c4", executor="e4", generated_skill="s4", result=_mr("e4", 0.8, 0.02)),   # new
        ]

        old = RunSummary(mode="matrix", task_path="/t", timestamp="t0", matrix_results=cells_old)
        new = RunSummary(mode="matrix", task_path="/t", timestamp="t1", matrix_results=cells_new)

        _write_summary(old_dir, old)
        _write_summary(new_dir, new)

        report = compare_runs(old_dir, new_dir)
        assert report.mode == "matrix"

        entries_by_model = {e.model: e for e in report.entries}
        assert "c1 -> e1" in entries_by_model
        assert entries_by_model["c1 -> e1"].status == "improved"
        assert entries_by_model["c2 -> e2"].status == "unchanged"
        assert entries_by_model["c3 -> e3"].status == "removed"
        assert entries_by_model["c4 -> e4"].status == "new"

        # 1 improved, 0 regressed, 1 unchanged
        assert report.summary == "1 improved, 0 regressed, 1 unchanged"


class TestCompareChainMode:
    def test_chain_label_and_classification(self, tmp_path: Path) -> None:
        old_dir = tmp_path / "old_c"
        new_dir = tmp_path / "new_c"

        cells_old = [
            ChainCell(
                meta_skill_name="ms1",
                creator="c1",
                executor="e1",
                generated_skill="s1",
                result=_mr("e1", 0.8, 0.01),
            ),
        ]
        cells_new = [
            ChainCell(
                meta_skill_name="ms1",
                creator="c1",
                executor="e1",
                generated_skill="s1",
                result=_mr("e1", 0.7, 0.012),  # regressed
            ),
        ]

        old = RunSummary(mode="chain", task_path="/t", timestamp="t0", chain_results=cells_old)
        new = RunSummary(mode="chain", task_path="/t", timestamp="t1", chain_results=cells_new)

        _write_summary(old_dir, old)
        _write_summary(new_dir, new)

        report = compare_runs(old_dir, new_dir)
        assert report.mode == "chain"
        assert report.summary == "0 improved, 1 regressed, 0 unchanged"

        [entry] = report.entries
        assert entry.model == "ms1 / c1 -> e1"
        assert entry.status == "regressed"


class TestMismatchedModes:
    def test_raises_value_error(self, tmp_path: Path) -> None:
        old_dir = tmp_path / "old_x"
        new_dir = tmp_path / "new_x"

        old = RunSummary(mode="run", task_path="/t", timestamp="t0")
        new = RunSummary(mode="matrix", task_path="/t", timestamp="t1")
        _write_summary(old_dir, old)
        _write_summary(new_dir, new)

        with pytest.raises(ValueError):
            compare_runs(old_dir, new_dir)

