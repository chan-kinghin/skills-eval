"""CLI commands for SkillEval."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import click

from skilleval.config import filter_available, filter_by_names, load_catalog, load_task
from skilleval.display import (
    console,
    display_catalog,
    display_chain_results,
    display_matrix_results,
    display_pre_run_estimate,
    display_run_results,
)
from skilleval.models import RunSummary


@click.group()
@click.version_option(package_name="skilleval")
def cli() -> None:
    """SkillEval: Find the cheapest model that gets your task 100% right."""


@cli.command()
@click.argument("name")
def init(name: str) -> None:
    """Create a new task folder with template files."""
    task_path = Path(name)
    if task_path.exists():
        raise click.ClickException(f"Directory '{name}' already exists")

    task_path.mkdir(parents=True)
    (task_path / "input").mkdir()
    (task_path / "expected").mkdir()

    (task_path / "prompt.md").write_text(
        "# Task Description\n\n"
        "Describe what the model should do with the input files.\n"
        "This is used in Mode 2/3 for skill generation.\n"
    )

    (task_path / "skill.md").write_text(
        "# Task Skill\n\n"
        "Write the system prompt / skill that tells the model\n"
        "exactly how to transform the input into the expected output.\n"
        "This is used in Mode 1 (direct evaluation).\n"
    )

    (task_path / "meta-skill.md").write_text(
        "# Meta-Skill\n\n"
        "Write instructions for how a model should write a task skill.\n"
        "This is used in Mode 3 (meta-skill chain evaluation).\n"
        "Rename this file to meta-skill-<variant>.md for multiple variants.\n"
    )

    (task_path / "config.yaml").write_text(
        "# SkillEval task configuration\n"
        "\n"
        "# Comparator: how to check if output matches expected\n"
        "# Options: json_exact, csv_ordered, csv_unordered, field_subset, file_hash, custom\n"
        "comparator: json_exact\n"
        "\n"
        "# For custom comparator, path to the script:\n"
        "# custom_script: ./compare.py\n"
        "\n"
        "# Number of trials per model (higher = more confidence)\n"
        "trials: 5\n"
        "\n"
        "# API timeout in seconds\n"
        "timeout: 60\n"
        "\n"
        "# Model parameters\n"
        "temperature: 0.0\n"
        "max_tokens: 4096\n"
        "\n"
        "# Expected output format (for display purposes)\n"
        "output_format: json\n"
    )

    click.echo(f"Created task folder: {task_path}")
    click.echo()
    click.echo("Next steps:")
    click.echo(f"  1. Add input files to {task_path}/input/")
    click.echo(f"  2. Add expected output files to {task_path}/expected/")
    click.echo(f"  3. Write your skill in {task_path}/skill.md")
    click.echo(f"  4. Edit {task_path}/config.yaml as needed")
    click.echo(f"  5. Run: skilleval run {task_path}")


@cli.command()
@click.argument("task_path")
@click.option("--models", default=None, help="Comma-separated model names (default: all available)")
@click.option("--trials", default=None, type=int, help="Override trial count from config")
@click.option("--parallel", default=20, type=int, help="Max concurrent API calls")
@click.option("--catalog", "catalog_path", default=None, help="Path to model catalog YAML")
def run(
    task_path: str,
    models: str | None,
    trials: int | None,
    parallel: int,
    catalog_path: str | None,
) -> None:
    """Mode 1: Evaluate models with a given skill."""
    try:
        task = load_task(task_path)
        if not task.skill:
            raise click.ClickException("Mode 1 requires skill.md in the task folder")

        if trials is not None:
            task.config.trials = trials

        catalog = load_catalog(catalog_path)
        if models:
            selected = filter_by_names(catalog, models.split(","))
        else:
            selected = filter_available(catalog)

        if not selected:
            raise click.ClickException(
                "No models available. Set API key env vars or use --models to specify."
            )

        console.print(f"[bold]Mode 1: Skill Evaluation[/bold]")
        console.print(f"Task: {task.path}")
        console.print(f"Models: {', '.join(m.name for m in selected)}")
        console.print(f"Trials: {task.config.trials}")

        summary = asyncio.run(_run_mode1(task, selected, parallel))
        display_run_results(summary.model_results, summary.recommendation)

    except (ValueError, FileNotFoundError) as e:
        raise click.ClickException(str(e))


async def _run_mode1(task, selected, parallel):
    from skilleval.engine import ExecutionEngine
    from skilleval.runner import run_mode1

    async with ExecutionEngine(selected, max_global=parallel) as engine:
        return await run_mode1(task, selected, engine, parallel)


@cli.command()
@click.argument("task_path")
@click.option("--creators", required=True, help="Comma-separated creator model names")
@click.option("--executors", required=True, help="Comma-separated executor model names")
@click.option("--trials", default=None, type=int, help="Override trial count from config")
@click.option("--parallel", default=20, type=int, help="Max concurrent API calls")
@click.option("--catalog", "catalog_path", default=None, help="Path to model catalog YAML")
def matrix(
    task_path: str,
    creators: str,
    executors: str,
    trials: int | None,
    parallel: int,
    catalog_path: str | None,
) -> None:
    """Mode 2: Creator x executor matrix evaluation."""
    try:
        task = load_task(task_path)
        if not task.prompt:
            raise click.ClickException("Mode 2 requires prompt.md in the task folder")

        if trials is not None:
            task.config.trials = trials

        catalog = load_catalog(catalog_path)
        creator_models = filter_by_names(catalog, creators.split(","))
        executor_models = filter_by_names(catalog, executors.split(","))

        num_calls = len(creator_models) + len(creator_models) * len(executor_models) * task.config.trials
        console.print(f"[bold]Mode 2: Matrix Evaluation[/bold]")
        console.print(f"Task: {task.path}")
        console.print(f"Creators: {', '.join(m.name for m in creator_models)}")
        console.print(f"Executors: {', '.join(m.name for m in executor_models)}")
        display_pre_run_estimate(num_calls, 0.0)

        summary = asyncio.run(_run_mode2(task, creator_models, executor_models, parallel))
        display_matrix_results(summary.matrix_results)

        if summary.recommendation:
            console.print(f"\n[bold green]Recommendation:[/bold green] {summary.recommendation}")

    except (ValueError, FileNotFoundError) as e:
        raise click.ClickException(str(e))


async def _run_mode2(task, creator_models, executor_models, parallel):
    from skilleval.engine import ExecutionEngine
    from skilleval.runner import run_mode2

    all_models = list({m.name: m for m in creator_models + executor_models}.values())
    async with ExecutionEngine(all_models, max_global=parallel) as engine:
        return await run_mode2(task, creator_models, executor_models, engine)


@cli.command()
@click.argument("task_path")
@click.option("--meta-skills", required=True, help="Comma-separated meta-skill variant names")
@click.option("--creators", required=True, help="Comma-separated creator model names")
@click.option("--executors", required=True, help="Comma-separated executor model names")
@click.option("--trials", default=None, type=int, help="Override trial count from config")
@click.option("--parallel", default=20, type=int, help="Max concurrent API calls")
@click.option("--catalog", "catalog_path", default=None, help="Path to model catalog YAML")
@click.option("--confirm", is_flag=True, help="Skip confirmation for large runs")
def chain(
    task_path: str,
    meta_skills: str,
    creators: str,
    executors: str,
    trials: int | None,
    parallel: int,
    catalog_path: str | None,
    confirm: bool,
) -> None:
    """Mode 3: Meta-skill x creator x executor chain evaluation."""
    try:
        task = load_task(task_path)
        if not task.prompt:
            raise click.ClickException("Mode 3 requires prompt.md in the task folder")

        if trials is not None:
            task.config.trials = trials

        meta_skill_names = meta_skills.split(",")
        catalog = load_catalog(catalog_path)
        creator_models = filter_by_names(catalog, creators.split(","))
        executor_models = filter_by_names(catalog, executors.split(","))

        # Validate meta-skills exist
        for ms_name in meta_skill_names:
            if ms_name not in task.meta_skills:
                available = ", ".join(sorted(task.meta_skills.keys())) if task.meta_skills else "none"
                raise click.ClickException(
                    f"Meta-skill '{ms_name}' not found. Available: {available}"
                )

        # Estimate API calls
        gen_calls = len(meta_skill_names) * len(creator_models)
        exec_calls = len(meta_skill_names) * len(creator_models) * len(executor_models) * task.config.trials
        total_calls = gen_calls + exec_calls

        console.print(f"[bold]Mode 3: Chain Evaluation[/bold]")
        console.print(f"Task: {task.path}")
        console.print(f"Meta-skills: {', '.join(meta_skill_names)}")
        console.print(f"Creators: {', '.join(m.name for m in creator_models)}")
        console.print(f"Executors: {', '.join(m.name for m in executor_models)}")
        display_pre_run_estimate(total_calls, 0.0)

        if total_calls > 100 and not confirm:
            if not click.confirm("Proceed with this run?"):
                click.echo("Aborted.")
                return

        summary = asyncio.run(
            _run_mode3(task, meta_skill_names, creator_models, executor_models, parallel)
        )
        display_chain_results(summary.chain_results)

        if summary.recommendation:
            console.print(f"\n[bold green]Recommendation:[/bold green] {summary.recommendation}")

    except (ValueError, FileNotFoundError) as e:
        raise click.ClickException(str(e))


async def _run_mode3(task, meta_skill_names, creator_models, executor_models, parallel):
    from skilleval.engine import ExecutionEngine
    from skilleval.runner import run_mode3

    all_models = list({m.name: m for m in creator_models + executor_models}.values())
    async with ExecutionEngine(all_models, max_global=parallel) as engine:
        return await run_mode3(task, meta_skill_names, creator_models, executor_models, engine)


@cli.command("catalog")
@click.option("--catalog", "catalog_path", default=None, help="Path to model catalog YAML")
def catalog_cmd(catalog_path: str | None) -> None:
    """Display model catalog with availability status."""
    try:
        catalog = load_catalog(catalog_path)
        available = filter_available(catalog)
        available_names = [m.name for m in available]
        display_catalog(catalog, available_names)

    except (ValueError, FileNotFoundError) as e:
        raise click.ClickException(str(e))


@cli.command()
@click.argument("results_path")
def report(results_path: str) -> None:
    """Re-render results from a previous run."""
    try:
        path = Path(results_path)
        results_file = path / "results.json" if path.is_dir() else path

        if not results_file.exists():
            raise click.ClickException(f"Results file not found: {results_file}")

        data = json.loads(results_file.read_text())
        summary = RunSummary(**data)

        if summary.mode == "run":
            display_run_results(summary.model_results, summary.recommendation)
        elif summary.mode == "matrix":
            display_matrix_results(summary.matrix_results)
        elif summary.mode == "chain":
            display_chain_results(summary.chain_results)
        else:
            click.echo(f"Unknown mode: {summary.mode}")

        if summary.recommendation:
            console.print(f"\n[bold green]Recommendation:[/bold green] {summary.recommendation}")

    except (ValueError, json.JSONDecodeError) as e:
        raise click.ClickException(str(e))
