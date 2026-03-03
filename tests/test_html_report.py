"""Tests for HTML report generation (src/skilleval/html_report.py)."""

from __future__ import annotations

from pathlib import Path

from skilleval.html_report import generate_html_report
from skilleval.models import (
    ChainCell,
    MatrixCell,
    ModelResult,
    RunSummary,
    TrialResult,
)


def _mr(
    model: str,
    pass_rate: float,
    trials: list[TrialResult],
    avg_cost=0.0,
    avg_latency=0.0,
    total_cost=0.0,
) -> ModelResult:
    return ModelResult(
        model=model,
        pass_rate=pass_rate,
        trials=trials,
        avg_cost=avg_cost,
        avg_latency=avg_latency,
        total_cost=total_cost,
    )


def test_generate_html_report_run_mode(tmp_path: Path) -> None:
    t1 = TrialResult(
        model="modelA",
        trial_number=1,
        passed=True,
        output_text="ok",
        cost=0.001,
        latency_seconds=0.4,
    )
    t2 = TrialResult(
        model="modelA",
        trial_number=2,
        passed=True,
        output_text="ok2",
        cost=0.001,
        latency_seconds=0.5,
    )
    r1 = _mr("modelA", 1.0, [t1, t2], avg_cost=0.001, avg_latency=0.45, total_cost=0.002)

    u1 = TrialResult(
        model="modelB",
        trial_number=1,
        passed=False,
        output_text="no",
        cost=0.002,
        latency_seconds=0.6,
    )
    u2 = TrialResult(
        model="modelB",
        trial_number=2,
        passed=True,
        output_text="ok",
        cost=0.002,
        latency_seconds=0.7,
    )
    r2 = _mr("modelB", 0.5, [u1, u2], avg_cost=0.002, avg_latency=0.65, total_cost=0.004)

    summary = RunSummary(
        mode="run",
        task_path="/tmp/task",
        timestamp="2026-01-01T00:00:00",
        model_results=[r1, r2],
        recommendation="modelA ($0.001000/run)",
    )

    out = generate_html_report(summary, tmp_path / "report_run.html")
    assert out.exists()
    html = out.read_text(encoding="utf-8")

    assert "Task:" in html and "/tmp/task" in html
    assert "Mode:" in html and "run" in html
    assert "Cost Comparison" in html
    assert "Per-Model Trials" in html
    assert "modelA" in html and "modelB" in html
    assert "details" in html  # collapsible sections


def test_generate_html_report_matrix_mode(tmp_path: Path) -> None:
    # Three cells, best should be C1 -> E2 with 90%
    r_a = _mr("E1", 0.4, [TrialResult(model="E1", trial_number=1, passed=False)], avg_cost=0.003)
    r_b = _mr("E2", 0.9, [TrialResult(model="E2", trial_number=1, passed=True)], avg_cost=0.001)
    r_c = _mr("E1", 0.8, [TrialResult(model="E1", trial_number=1, passed=True)], avg_cost=0.002)

    c1 = MatrixCell(creator="C1", executor="E1", generated_skill="s1", result=r_a)
    c2 = MatrixCell(creator="C1", executor="E2", generated_skill="s2", result=r_b)
    c3 = MatrixCell(creator="C2", executor="E1", generated_skill="s3", result=r_c)

    summary = RunSummary(
        mode="matrix",
        task_path="/tmp/task2",
        timestamp="t",
        matrix_results=[c1, c2, c3],
    )

    out = generate_html_report(summary, tmp_path / "report_matrix.html")
    assert out.exists()
    html = out.read_text(encoding="utf-8")

    assert "Creator × Executor Heatmap" in html
    assert "Best Pair:" in html
    assert "C1 → E2" in html  # best pair
    # Ensure cells render with identifying attributes
    assert 'data-creator="C1"' in html and 'data-executor="E2"' in html


def test_generate_html_report_chain_mode(tmp_path: Path) -> None:
    # Two meta-skill variants with differing averages
    r1 = _mr(
        "exec",
        1.0,
        [TrialResult(model="exec", trial_number=1, passed=True)],
        avg_cost=0.001,
        avg_latency=0.5,
    )
    r2 = _mr(
        "exec",
        0.8,
        [TrialResult(model="exec", trial_number=1, passed=True)],
        avg_cost=0.002,
        avg_latency=0.6,
    )
    r3 = _mr(
        "exec",
        0.5,
        [TrialResult(model="exec", trial_number=1, passed=False)],
        avg_cost=0.003,
        avg_latency=0.7,
    )

    a = ChainCell(
        meta_skill_name="ms1", creator="c1", executor="e1", generated_skill="g1", result=r1
    )
    b = ChainCell(
        meta_skill_name="ms1", creator="c2", executor="e2", generated_skill="g2", result=r2
    )
    c = ChainCell(
        meta_skill_name="ms2", creator="c1", executor="e1", generated_skill="g3", result=r3
    )

    summary = RunSummary(
        mode="chain",
        task_path="/tmp/task3",
        timestamp="t",
        chain_results=[a, b, c],
    )

    out = generate_html_report(summary, tmp_path / "report_chain.html")
    assert out.exists()
    html = out.read_text(encoding="utf-8")

    assert "Chain Results" in html
    assert "Pass Rate by Variant" in html
    assert "Variant Details" in html
    assert "ms1" in html and "ms2" in html
