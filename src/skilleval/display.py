"""Rich terminal output for SkillEval results."""

from __future__ import annotations

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.text import Text

from typing import TYPE_CHECKING

from skilleval.i18n import t
from skilleval.models import ChainCell, MatrixCell, ModelEntry, ModelResult

if TYPE_CHECKING:
    from skilleval.compare import ComparisonReport
    from skilleval.linter import LintReport

console = Console()


def display_run_results(results: list[ModelResult], recommendation: str | None) -> None:
    """Display Mode 1 results as a sorted table."""
    table = Table(title=t("display.tables.evaluation_results"), show_lines=True)
    table.add_column(t("display.tables.model"), style="bold")
    table.add_column(t("display.tables.pass_rate"), justify="right")
    table.add_column(t("display.tables.avg_cost"), justify="right")
    table.add_column(t("display.tables.avg_latency"), justify="right")
    table.add_column(t("display.tables.total_cost"), justify="right")
    table.add_column(t("display.tables.rec"), justify="center")

    sorted_results = sorted(results, key=lambda r: (-r.pass_rate, r.avg_cost))

    for r in sorted_results:
        rate_pct = f"{r.pass_rate * 100:.0f}%"
        if r.pass_rate == 1.0:
            rate_style = "green"
        elif r.pass_rate >= 0.8:
            rate_style = "yellow"
        else:
            rate_style = "red"

        is_rec = recommendation is not None and r.model in recommendation
        row_style = "on green" if is_rec else ""
        rec_mark = "*" if is_rec else ""

        table.add_row(
            r.model,
            Text(rate_pct, style=rate_style),
            f"${r.avg_cost:.6f}",
            f"{r.avg_latency:.2f}s",
            f"${r.total_cost:.6f}",
            rec_mark,
            style=row_style,
        )

    console.print(table)

    if recommendation:
        console.print(
            f"\n[bold green]{t('display.messages.recommendation')}[/bold green] {recommendation}"
        )
    else:
        best = max(results, key=lambda r: r.pass_rate) if results else None
        if best:
            console.print(
                f"\n[yellow]{t('display.messages.no_perfect', model=best.model, rate=f'{best.pass_rate * 100:.0f}%')}[/yellow]"
            )
            console.print(f"[dim]{t('display.messages.consider_improving')}[/dim]")


def display_matrix_results(cells: list[MatrixCell]) -> None:
    """Display Mode 2 results as a creator x executor heatmap table."""
    if not cells:
        console.print(f"[yellow]{t('display.messages.no_matrix_results')}[/yellow]")
        return

    creators = sorted({c.creator for c in cells})
    executors = sorted({c.executor for c in cells})

    lookup: dict[tuple[str, str], MatrixCell] = {}
    for c in cells:
        lookup[(c.creator, c.executor)] = c

    table = Table(title=t("display.tables.creator_executor_matrix"), show_lines=True)
    table.add_column(t("display.tables.creator_executor"), style="bold")
    for ex in executors:
        table.add_column(ex, justify="center")

    for cr in creators:
        row: list[str | Text] = [cr]
        for ex in executors:
            cell = lookup.get((cr, ex))
            if cell is None:
                row.append("-")
                continue
            pct = f"{cell.result.pass_rate * 100:.0f}%"
            if cell.result.pass_rate == 1.0:
                row.append(Text(pct, style="bold green"))
            elif cell.result.pass_rate >= 0.8:
                row.append(Text(pct, style="yellow"))
            else:
                row.append(Text(pct, style="red"))
        table.add_row(*row)

    console.print(table)

    # Summary stats
    if cells:
        best_pair = max(cells, key=lambda c: (c.result.pass_rate, -c.result.avg_cost))
        console.print(
            f"\n[bold]{t('display.messages.best_pair')}[/bold] {best_pair.creator} -> {best_pair.executor} "
            f"({best_pair.result.pass_rate * 100:.0f}%, "
            f"${best_pair.result.avg_cost:.6f}/run)"
        )

        perfect = [c for c in cells if c.result.pass_rate == 1.0]
        if perfect:
            cheapest = min(perfect, key=lambda c: c.result.avg_cost)
            console.print(
                f"[bold green]{t('display.messages.cheapest_perfect')}[/bold green] "
                f"{cheapest.creator} -> {cheapest.executor} "
                f"(${cheapest.result.avg_cost:.6f}/run)"
            )


def display_chain_results(cells: list[ChainCell]) -> None:
    """Display Mode 3 results with meta-skill comparison."""
    if not cells:
        console.print(f"[yellow]{t('display.messages.no_chain_results')}[/yellow]")
        return

    # Meta-skill comparison table
    meta_skills = sorted({c.meta_skill_name for c in cells})
    meta_table = Table(title=t("display.tables.meta_skill_comparison"), show_lines=True)
    meta_table.add_column(t("display.tables.meta_skill"), style="bold")
    meta_table.add_column(t("display.tables.avg_pass_rate"), justify="right")

    for ms in meta_skills:
        ms_cells = [c for c in cells if c.meta_skill_name == ms]
        avg_rate = sum(c.result.pass_rate for c in ms_cells) / len(ms_cells) if ms_cells else 0
        pct = f"{avg_rate * 100:.1f}%"
        style = "green" if avg_rate == 1.0 else "yellow" if avg_rate >= 0.8 else "red"
        meta_table.add_row(ms, Text(pct, style=style))

    console.print(meta_table)

    # Best chain
    best = max(cells, key=lambda c: (c.result.pass_rate, -c.result.avg_cost))
    console.print(
        f"\n[bold]{t('display.messages.best_chain')}[/bold] {best.meta_skill_name} / {best.creator} -> "
        f"{best.executor} ({best.result.pass_rate * 100:.0f}%, "
        f"${best.result.avg_cost:.6f}/run)"
    )

    perfect = [c for c in cells if c.result.pass_rate == 1.0]
    if perfect:
        cheapest = min(perfect, key=lambda c: c.result.avg_cost)
        console.print(
            f"[bold green]{t('display.messages.cheapest_perfect')}[/bold green] "
            f"{cheapest.meta_skill_name} / {cheapest.creator} -> {cheapest.executor} "
            f"(${cheapest.result.avg_cost:.6f}/run)"
        )


def display_catalog(models: list[ModelEntry], available: list[str]) -> None:
    """Display model catalog with availability status."""
    table = Table(title=t("display.tables.model_catalog"), show_lines=True)
    table.add_column(t("display.tables.model"), style="bold")
    table.add_column(t("display.tables.provider"))
    table.add_column(t("display.tables.input_cost"), justify="right")
    table.add_column(t("display.tables.output_cost"), justify="right")
    table.add_column(t("display.tables.context"), justify="right")
    table.add_column(t("display.tables.env_var"))
    table.add_column(t("display.tables.status"), justify="center")

    avail_set = set(available)
    for m in models:
        if m.name in avail_set:
            status = Text(t("display.tables.ready"), style="bold green")
        else:
            status = Text(t("display.tables.no_key"), style="red")

        table.add_row(
            m.name,
            m.provider,
            f"${m.input_cost_per_m:.2f}",
            f"${m.output_cost_per_m:.2f}",
            f"{m.context_window:,}",
            Text(m.env_key, style="dim"),
            status,
        )

    console.print(table)

    # Show a hint if some models lack keys
    missing = [m for m in models if m.name not in avail_set]
    if missing:
        env_keys = sorted({m.env_key for m in missing})
        console.print(
            f"\n[dim]{t('display.messages.tip_env_vars', keys=', '.join(env_keys))}[/dim]"
        )


def display_pre_run_estimate(num_calls: int, estimated_cost: float) -> None:
    """Show estimated API calls and cost before execution."""
    console.print(
        f"\n[bold]{t('display.messages.estimated')}[/bold] "
        f"{t('display.messages.estimated_detail', num_calls=num_calls, cost=estimated_cost)}"
    )


def display_results_path(run_dir: str | object) -> None:
    """Show where results are saved with actionable follow-up commands."""
    from pathlib import Path

    console.print(f"\n[bold green]{t('display.messages.results_saved')}[/bold green] {run_dir}")
    run_path = Path(str(run_dir))
    task_path = run_path.parent.parent  # .skilleval/run-XXX -> task_dir
    console.print(f"[dim]  {t('display.messages.view_again', task_path=task_path)}[/dim]")
    console.print(f"[dim]  {t('display.messages.html_report_hint', task_path=task_path)}[/dim]")
    console.print(f"[dim]  {t('display.messages.run_history_hint', task_path=task_path)}[/dim]")


def display_history(runs: list[dict], task_path: str) -> None:
    """Display a table of past evaluation runs."""
    table = Table(title=f"{t('display.tables.run_history')} \u2014 {task_path}", show_lines=True)
    table.add_column(t("display.tables.run"), style="bold")
    table.add_column(t("display.tables.mode"))
    table.add_column(t("display.tables.models"), justify="right")
    table.add_column(t("display.tables.avg_pass_rate"), justify="right")
    table.add_column(t("display.tables.recommendation"))

    for i, r in enumerate(runs):
        run_name = r.get("run_dir", "?")
        mode = r.get("mode", "?")
        model_count = str(r.get("model_count", len(r.get("models", []))))
        avg_rate = r.get("avg_pass_rate")
        rec = r.get("recommendation")

        if avg_rate is not None:
            rate_pct = f"{avg_rate * 100:.0f}%"
            if avg_rate == 1.0:
                rate_style = "green"
            elif avg_rate >= 0.8:
                rate_style = "yellow"
            else:
                rate_style = "red"
            rate_text = Text(rate_pct, style=rate_style)
        else:
            rate_text = Text("-", style="dim")

        rec_text = rec[:50] + "..." if rec and len(rec) > 53 else (rec or "")

        # Mark the latest run
        label = run_name
        if i == 0:
            label = f"{run_name} [bold cyan]{t('display.tables.latest')}[/bold cyan]"

        table.add_row(label, mode, model_count, rate_text, rec_text)

    console.print(table)
    console.print(f"\n[dim]{t('display.messages.view_run', task_path=task_path)}[/dim]")


def create_progress() -> Progress:
    """Create a Rich progress bar with elapsed time and ETA."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("[dim]{task.completed}/{task.total}[/dim]"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    )


def display_lint_report(report: "LintReport") -> None:
    """Render linter results as a table with severity coloring."""
    if not report.issues:
        console.print(f"[bold green]{t('display.messages.no_issues')}[/bold green]")
        console.print(f"{t('display.messages.quality_score')} [bold]{report.quality_score}[/bold]")
        return

    table = Table(title=t("display.tables.skill_lint_report"), show_lines=True)
    table.add_column(t("display.tables.severity"), style="bold")
    table.add_column(t("display.tables.line"), justify="right")
    table.add_column(t("display.tables.message"))

    for issue in report.issues:
        sev = issue.severity.lower()
        style = "red" if sev == "error" else "yellow" if sev == "warning" else "blue"
        line = str(issue.line) if issue.line is not None else "-"
        table.add_row(Text(sev, style=style), line, issue.message)

    console.print(table)
    console.print(f"{t('display.messages.quality_score')} [bold]{report.quality_score}[/bold]")


def display_comparison(report: "ComparisonReport") -> None:
    """Render comparison between two runs (old vs new)."""
    table = Table(title=t("display.tables.run_comparison"), show_lines=True)
    table.add_column(t("display.tables.model"), style="bold")
    table.add_column(t("display.tables.old_rate"), justify="right")
    table.add_column(t("display.tables.new_rate"), justify="right")
    table.add_column(t("display.tables.delta"), justify="right")
    table.add_column(t("display.tables.status"), justify="center")

    # Sort by delta descending, then model name
    entries = sorted(
        report.entries,
        key=lambda e: (e.new_pass_rate - e.old_pass_rate, e.model),
        reverse=True,
    )

    for e in entries:
        delta = e.new_pass_rate - e.old_pass_rate
        delta_txt = f"{delta * 100:+.0f}%"
        status_style = {
            "improved": "green",
            "regressed": "red",
            "unchanged": "dim",
            "new": "cyan",
            "removed": "magenta",
        }.get(e.status, "")

        table.add_row(
            e.model,
            f"{e.old_pass_rate * 100:.0f}%",
            f"{e.new_pass_rate * 100:.0f}%",
            Text(delta_txt, style=status_style if e.status in {"improved", "regressed"} else ""),
            Text(e.status, style=status_style),
        )

    console.print(table)
    console.print(f"{t('display.messages.summary')} {report.summary}")


def display_skill_test_results(
    skill_name: str, results: list[tuple[str, list[ModelResult]]]
) -> None:
    """Display results of testing a skill against multiple test cases."""
    table = Table(title=f"{t('display.tables.skill_test')} \u2014 {skill_name}", show_lines=True)
    table.add_column(t("display.tables.test_case"), style="bold")
    table.add_column(t("display.tables.model"))
    table.add_column(t("display.tables.pass_rate"), justify="right")
    table.add_column(t("display.tables.avg_cost"), justify="right")

    per_model_totals: dict[str, tuple[int, int]] = {}

    for case_name, model_results in results:
        for r in sorted(model_results, key=lambda x: (-x.pass_rate, x.avg_cost, x.model)):
            rate_pct = f"{r.pass_rate * 100:.0f}%"
            if r.pass_rate == 1.0:
                rate_style = "green"
            elif r.pass_rate >= 0.8:
                rate_style = "yellow"
            else:
                rate_style = "red"

            table.add_row(
                case_name, r.model, Text(rate_pct, style=rate_style), f"${r.avg_cost:.6f}"
            )

            ok, total = per_model_totals.get(r.model, (0, 0))
            per_model_totals[r.model] = (ok + (1 if r.pass_rate == 1.0 else 0), total + 1)

    console.print(table)

    if per_model_totals:
        console.print(f"\n[bold]{t('display.tables.overall_summary')}:[/bold]")
        sum_table = Table(show_lines=True)
        sum_table.add_column(t("display.tables.model"), style="bold")
        sum_table.add_column(t("display.tables.cases_passing"), justify="right")
        for model, (ok, total) in sorted(per_model_totals.items()):
            sum_table.add_row(model, f"{ok}/{total}")
        console.print(sum_table)
