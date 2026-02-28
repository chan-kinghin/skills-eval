"""CLI commands for SkillEval."""

from __future__ import annotations

import asyncio
import json
import webbrowser
from pathlib import Path

import click

from skilleval.config import (
    build_adhoc_model,
    filter_available,
    filter_by_names,
    load_catalog,
    load_task,
)
from skilleval.display import (
    console,
    display_catalog,
    display_comparison,
    display_chain_results,
    display_lint_report,
    display_matrix_results,
    display_pre_run_estimate,
    display_run_results,
    display_skill_test_results,
)
from skilleval.models import RunSummary
from skilleval.linter import lint_skill
from skilleval.compare import compare_runs
from skilleval.html_report import generate_html_report
from skilleval.skill_parser import load_test_cases, parse_skill


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
@click.option("--endpoint", default=None, help="Ad-hoc OpenAI-compatible endpoint URL")
@click.option("--api-key", "api_key", default=None, help="API key for ad-hoc endpoint")
@click.option("--model-name", "model_name", default=None, help="Model name for ad-hoc endpoint")
def run(
    task_path: str,
    models: str | None,
    trials: int | None,
    parallel: int,
    catalog_path: str | None,
    endpoint: str | None,
    api_key: str | None,
    model_name: str | None,
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

        # Optional ad-hoc model support
        if endpoint:
            if not model_name:
                raise click.ClickException("When using --endpoint, you must provide --model-name.")
            adhoc = build_adhoc_model(endpoint, api_key or "", model_name)
            selected = [adhoc] + selected

        if not selected:
            raise click.ClickException(
                "No models available. Set API key env vars or use --models to specify."
            )

        console.print("[bold]Mode 1: Skill Evaluation[/bold]")
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
@click.option("--endpoint", default=None, help="Ad-hoc OpenAI-compatible endpoint URL")
@click.option("--api-key", "api_key", default=None, help="API key for ad-hoc endpoint")
@click.option("--model-name", "model_name", default=None, help="Model name for ad-hoc endpoint")
def matrix(
    task_path: str,
    creators: str,
    executors: str,
    trials: int | None,
    parallel: int,
    catalog_path: str | None,
    endpoint: str | None,
    api_key: str | None,
    model_name: str | None,
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

        # Optional ad-hoc model prepended to both creator and executor lists
        if endpoint:
            if not model_name:
                raise click.ClickException("When using --endpoint, you must provide --model-name.")
            adhoc = build_adhoc_model(endpoint, api_key or "", model_name)
            creator_models = [adhoc] + creator_models
            executor_models = [adhoc] + executor_models

        num_calls = len(creator_models) + len(creator_models) * len(executor_models) * task.config.trials
        console.print("[bold]Mode 2: Matrix Evaluation[/bold]")
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
@click.option("--endpoint", default=None, help="Ad-hoc OpenAI-compatible endpoint URL")
@click.option("--api-key", "api_key", default=None, help="API key for ad-hoc endpoint")
@click.option("--model-name", "model_name", default=None, help="Model name for ad-hoc endpoint")
def chain(
    task_path: str,
    meta_skills: str,
    creators: str,
    executors: str,
    trials: int | None,
    parallel: int,
    catalog_path: str | None,
    confirm: bool,
    endpoint: str | None,
    api_key: str | None,
    model_name: str | None,
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

        # Optional ad-hoc model prepended to both creator and executor lists
        if endpoint:
            if not model_name:
                raise click.ClickException("When using --endpoint, you must provide --model-name.")
            adhoc = build_adhoc_model(endpoint, api_key or "", model_name)
            creator_models = [adhoc] + creator_models
            executor_models = [adhoc] + executor_models

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

        console.print("[bold]Mode 3: Chain Evaluation[/bold]")
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
@click.option("--html", "html_path", default=None, help="Generate HTML report at path")
@click.option("--open", "open_browser", is_flag=True, help="Open HTML in browser")
def report(results_path: str, html_path: str | None, open_browser: bool) -> None:
    """Re-render results from a previous run."""
    try:
        path = Path(results_path)
        results_file = path / "results.json" if path.is_dir() else path

        if not results_file.exists():
            raise click.ClickException(f"Results file not found: {results_file}")

        data = json.loads(results_file.read_text())
        summary = RunSummary(**data)

        # Optional HTML report path
        if html_path:
            out = generate_html_report(summary, Path(html_path))
            click.echo(f"HTML report written to: {out}")
            if open_browser:
                try:
                    webbrowser.open(out.as_uri())
                except Exception:
                    # Fall back to path string if as_uri fails
                    webbrowser.open(str(out))
            return

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


# ── Additional Commands ───────────────────────────────────────────────────


@cli.command()
@click.argument("skill_path")
def lint(skill_path: str) -> None:
    """Validate a Claude Code skill structure."""
    try:
        report = lint_skill(Path(skill_path))
        display_lint_report(report)
        if any((iss.severity or "").lower() == "error" for iss in report.issues):
            raise SystemExit(1)
    except (ValueError, FileNotFoundError) as e:
        raise click.ClickException(str(e))


@cli.command()
@click.argument("old_run")
@click.argument("new_run")
def compare(old_run: str, new_run: str) -> None:
    """Compare results from two runs."""
    try:
        report = compare_runs(Path(old_run), Path(new_run))
        display_comparison(report)
    except (ValueError, FileNotFoundError) as e:
        raise click.ClickException(str(e))


@cli.command("skill-test")
@click.argument("skill_path")
@click.option("--test-cases", required=True, help="Path to test case directory")
@click.option("--models", default=None, help="Comma-separated model names")
@click.option("--trials", default=None, type=int, help="Override trial count")
@click.option("--parallel", default=20, type=int, help="Max concurrent API calls")
@click.option("--catalog", "catalog_path", default=None, help="Path to model catalog YAML")
def skill_test(
    skill_path: str,
    test_cases: str,
    models: str | None,
    trials: int | None,
    parallel: int,
    catalog_path: str | None,
) -> None:
    """Test a Claude Code skill against test cases."""
    try:
        skill_prompt = parse_skill(Path(skill_path))
        cases = load_test_cases(Path(test_cases))
        if not cases:
            raise click.ClickException("No valid test cases found in the specified directory")

        # Models selection pattern same as run
        catalog = load_catalog(catalog_path)
        if models:
            selected = filter_by_names(catalog, models.split(","))
        else:
            selected = filter_available(catalog)

        if not selected:
            raise click.ClickException(
                "No models available. Set API key env vars or use --models to specify."
            )

        console.print("[bold]Skill Test[/bold]")
        console.print(f"Skill: {skill_prompt.name or skill_prompt.source_path}")
        console.print(f"Models: {', '.join(m.name for m in selected)}")

        # Execute Mode 1 for each case using the parsed skill core prompt
        aggregated: list[tuple[str, list]] = []
        for case in cases:
            if trials is not None:
                case.config.trials = trials
            case.skill = skill_prompt.core_prompt
            summary = asyncio.run(_run_mode1(case, selected, parallel))
            case_name = Path(case.path).name
            aggregated.append((case_name, summary.model_results))

        display_skill_test_results(skill_prompt.name or "(unnamed skill)", aggregated)

    except (ValueError, FileNotFoundError) as e:
        raise click.ClickException(str(e))
