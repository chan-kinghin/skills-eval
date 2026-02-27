"""Rich terminal output for SkillEval results."""

from __future__ import annotations

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table
from rich.text import Text

from skilleval.models import ChainCell, MatrixCell, ModelEntry, ModelResult

console = Console()


def display_run_results(results: list[ModelResult], recommendation: str | None) -> None:
    """Display Mode 1 results as a sorted table."""
    table = Table(title="Evaluation Results", show_lines=True)
    table.add_column("Model", style="bold")
    table.add_column("Pass Rate", justify="right")
    table.add_column("Avg Cost", justify="right")
    table.add_column("Avg Latency", justify="right")
    table.add_column("Total Cost", justify="right")
    table.add_column("Rec", justify="center")

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
        console.print(f"\n[bold green]Recommendation:[/bold green] {recommendation}")
    else:
        best = max(results, key=lambda r: r.pass_rate) if results else None
        if best:
            console.print(
                f"\n[yellow]No model achieved 100% pass rate. "
                f"Best: {best.model} at {best.pass_rate * 100:.0f}%.[/yellow]"
            )
            console.print("[dim]Consider improving the skill or increasing trials.[/dim]")


def display_matrix_results(cells: list[MatrixCell]) -> None:
    """Display Mode 2 results as a creator x executor heatmap table."""
    if not cells:
        console.print("[yellow]No matrix results to display.[/yellow]")
        return

    creators = sorted({c.creator for c in cells})
    executors = sorted({c.executor for c in cells})

    lookup: dict[tuple[str, str], MatrixCell] = {}
    for c in cells:
        lookup[(c.creator, c.executor)] = c

    table = Table(title="Creator x Executor Matrix (Pass Rate %)", show_lines=True)
    table.add_column("Creator \\ Executor", style="bold")
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
        console.print(f"\n[bold]Best pair:[/bold] {best_pair.creator} -> {best_pair.executor} "
                      f"({best_pair.result.pass_rate * 100:.0f}%, "
                      f"${best_pair.result.avg_cost:.6f}/run)")

        perfect = [c for c in cells if c.result.pass_rate == 1.0]
        if perfect:
            cheapest = min(perfect, key=lambda c: c.result.avg_cost)
            console.print(f"[bold green]Cheapest @ 100%:[/bold green] "
                          f"{cheapest.creator} -> {cheapest.executor} "
                          f"(${cheapest.result.avg_cost:.6f}/run)")


def display_chain_results(cells: list[ChainCell]) -> None:
    """Display Mode 3 results with meta-skill comparison."""
    if not cells:
        console.print("[yellow]No chain results to display.[/yellow]")
        return

    # Meta-skill comparison table
    meta_skills = sorted({c.meta_skill_name for c in cells})
    meta_table = Table(title="Meta-Skill Comparison", show_lines=True)
    meta_table.add_column("Meta-Skill", style="bold")
    meta_table.add_column("Avg Pass Rate", justify="right")

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
        f"\n[bold]Best chain:[/bold] {best.meta_skill_name} / {best.creator} -> "
        f"{best.executor} ({best.result.pass_rate * 100:.0f}%, "
        f"${best.result.avg_cost:.6f}/run)"
    )

    perfect = [c for c in cells if c.result.pass_rate == 1.0]
    if perfect:
        cheapest = min(perfect, key=lambda c: c.result.avg_cost)
        console.print(
            f"[bold green]Cheapest @ 100%:[/bold green] "
            f"{cheapest.meta_skill_name} / {cheapest.creator} -> {cheapest.executor} "
            f"(${cheapest.result.avg_cost:.6f}/run)"
        )


def display_catalog(models: list[ModelEntry], available: list[str]) -> None:
    """Display model catalog with availability status."""
    table = Table(title="Model Catalog", show_lines=True)
    table.add_column("Model", style="bold")
    table.add_column("Provider")
    table.add_column("Input $/M", justify="right")
    table.add_column("Output $/M", justify="right")
    table.add_column("Context", justify="right")
    table.add_column("Status", justify="center")

    avail_set = set(available)
    for m in models:
        if m.name in avail_set:
            status = Text("Ready", style="bold green")
        else:
            status = Text("No Key", style="red")

        table.add_row(
            m.name,
            m.provider,
            f"${m.input_cost_per_m:.2f}",
            f"${m.output_cost_per_m:.2f}",
            f"{m.context_window:,}",
            status,
        )

    console.print(table)


def display_pre_run_estimate(num_calls: int, estimated_cost: float) -> None:
    """Show estimated API calls and cost before execution."""
    console.print(
        f"\n[bold]Estimated:[/bold] {num_calls} API calls, "
        f"~${estimated_cost:.2f} total cost"
    )


def create_progress() -> Progress:
    """Create a Rich progress bar for real-time tracking."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("[dim]{task.completed}/{task.total}[/dim]"),
        console=console,
    )
