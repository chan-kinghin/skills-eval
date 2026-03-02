"""CLI commands for SkillEval."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
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
    display_chain_results,
    display_comparison,
    display_lint_report,
    display_matrix_results,
    display_pre_run_estimate,
    display_run_results,
    display_skill_test_results,
)
from skilleval.models import ModelEntry, ModelResult, RunSummary


# ── Helpers ──────────────────────────────────────────────────────────────


def _inject_adhoc(
    catalog: list[ModelEntry],
    endpoint: str | None,
    api_key: str | None,
    model_name: str | None,
) -> None:
    """Append an ad-hoc model to *catalog* when ``--endpoint`` is provided.

    Mutates *catalog* in place so the model is discoverable by
    ``filter_available`` (picks it up via its embedded ``api_key``) and
    ``filter_by_names`` (user references it by ``--model-name``).
    """
    if not endpoint:
        return
    if not model_name:
        raise click.ClickException("--endpoint requires --model-name.")
    catalog.append(build_adhoc_model(endpoint, api_key or "", model_name))


# ── CLI Group ────────────────────────────────────────────────────────────


def _configure_logging(verbosity: int) -> None:
    """Configure the logging level and format based on CLI verbosity.

    Logging output goes to stderr so it does not interfere with Rich console
    output on stdout.
    """
    if verbosity == 0:
        level = logging.WARNING
    elif verbosity == 1:
        level = logging.INFO
    else:
        level = logging.DEBUG

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root_logger = logging.getLogger("skilleval")
    root_logger.setLevel(level)
    # Avoid duplicate handlers if the CLI group is invoked more than once
    # (e.g. in tests using CliRunner).
    if not root_logger.handlers:
        root_logger.addHandler(handler)
    else:
        root_logger.handlers[0] = handler
        root_logger.setLevel(level)


@click.group()
@click.version_option(package_name="skilleval")
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Increase verbosity (-v for INFO, -vv for DEBUG).",
)
@click.pass_context
def cli(ctx: click.Context, verbose: int) -> None:
    """SkillEval: Find the cheapest model that gets your task 100% right."""
    ctx.ensure_object(dict)
    ctx.obj["verbosity"] = verbose
    _configure_logging(verbose)


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


# ── Mode 1: Skill Evaluation ────────────────────────────────────────────


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
        _inject_adhoc(catalog, endpoint, api_key, model_name)

        if models:
            selected = filter_by_names(catalog, models.split(","))
        else:
            selected = filter_available(catalog)

        if not selected:
            raise click.ClickException(
                "No models available. Set API key env vars or use --models to specify."
            )

        num_calls = len(selected) * task.config.trials
        avg_input_cost = sum(m.input_cost_per_m for m in selected) / len(selected)
        avg_output_cost = sum(m.output_cost_per_m for m in selected) / len(selected)
        estimated_cost = num_calls * (
            1000 / 1_000_000 * avg_input_cost + 4000 / 1_000_000 * avg_output_cost
        )

        console.print("[bold]Mode 1: Skill Evaluation[/bold]")
        console.print(f"Task: {task.path}")
        console.print(f"Models: {', '.join(m.name for m in selected)}")
        console.print(f"Trials: {task.config.trials}")
        display_pre_run_estimate(num_calls, estimated_cost)

        summary = asyncio.run(_run_mode1(task, selected, parallel))
        display_run_results(summary.model_results, summary.recommendation)

    except (ValueError, FileNotFoundError) as e:
        raise click.ClickException(str(e))


async def _run_mode1(task, selected, parallel):
    from skilleval.engine import ExecutionEngine
    from skilleval.runner import run_mode1

    async with ExecutionEngine(selected, max_global=parallel) as engine:
        return await run_mode1(task, selected, engine, parallel)


# ── Mode 2: Matrix Evaluation ───────────────────────────────────────────


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
        _inject_adhoc(catalog, endpoint, api_key, model_name)

        creator_models = filter_by_names(catalog, creators.split(","))
        executor_models = filter_by_names(catalog, executors.split(","))

        num_calls = len(creator_models) + len(creator_models) * len(executor_models) * task.config.trials
        all_models = creator_models + executor_models
        avg_input_cost = sum(m.input_cost_per_m for m in all_models) / len(all_models)
        avg_output_cost = sum(m.output_cost_per_m for m in all_models) / len(all_models)
        estimated_cost = num_calls * (
            1000 / 1_000_000 * avg_input_cost + 4000 / 1_000_000 * avg_output_cost
        )

        console.print("[bold]Mode 2: Matrix Evaluation[/bold]")
        console.print(f"Task: {task.path}")
        console.print(f"Creators: {', '.join(m.name for m in creator_models)}")
        console.print(f"Executors: {', '.join(m.name for m in executor_models)}")
        display_pre_run_estimate(num_calls, estimated_cost)

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


# ── Mode 3: Chain Evaluation ────────────────────────────────────────────


@cli.command()
@click.argument("task_path")
@click.option("--meta-skills", required=True, help="Comma-separated meta-skill variant names")
@click.option("--creators", required=True, help="Comma-separated creator model names")
@click.option("--executors", required=True, help="Comma-separated executor model names")
@click.option("--trials", default=None, type=int, help="Override trial count from config")
@click.option("--parallel", default=20, type=int, help="Max concurrent API calls")
@click.option("--catalog", "catalog_path", default=None, help="Path to model catalog YAML")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation for large runs")
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
    yes: bool,
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
        _inject_adhoc(catalog, endpoint, api_key, model_name)

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
        all_models = creator_models + executor_models
        avg_input_cost = sum(m.input_cost_per_m for m in all_models) / len(all_models)
        avg_output_cost = sum(m.output_cost_per_m for m in all_models) / len(all_models)
        estimated_cost = total_calls * (
            1000 / 1_000_000 * avg_input_cost + 4000 / 1_000_000 * avg_output_cost
        )

        console.print("[bold]Mode 3: Chain Evaluation[/bold]")
        console.print(f"Task: {task.path}")
        console.print(f"Meta-skills: {', '.join(meta_skill_names)}")
        console.print(f"Creators: {', '.join(m.name for m in creator_models)}")
        console.print(f"Executors: {', '.join(m.name for m in executor_models)}")
        display_pre_run_estimate(total_calls, estimated_cost)

        if total_calls > 100 and not yes:
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


# ── Utility Commands ─────────────────────────────────────────────────────


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

        if html_path:
            from skilleval.html_report import generate_html_report

            out = generate_html_report(summary, Path(html_path))
            click.echo(f"HTML report written to: {out}")
            if open_browser:
                webbrowser.open(out.resolve().as_uri())
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


@cli.command()
@click.argument("skill_path")
@click.pass_context
def lint(ctx: click.Context, skill_path: str) -> None:
    """Validate a Claude Code skill structure."""
    try:
        from skilleval.linter import lint_skill

        result = lint_skill(Path(skill_path))
        display_lint_report(result)
        if any(iss.severity == "error" for iss in result.issues):
            ctx.exit(1)
    except (ValueError, FileNotFoundError) as e:
        raise click.ClickException(str(e))


@cli.command()
@click.argument("old_run")
@click.argument("new_run")
def compare(old_run: str, new_run: str) -> None:
    """Compare results from two runs."""
    try:
        from skilleval.compare import compare_runs

        result = compare_runs(Path(old_run), Path(new_run))
        display_comparison(result)
    except (ValueError, FileNotFoundError) as e:
        raise click.ClickException(str(e))


@cli.command("skill-test")
@click.argument("skill_path")
@click.option("--test-cases", required=True, help="Path to test case directory")
@click.option("--models", default=None, help="Comma-separated model names")
@click.option("--trials", default=None, type=int, help="Override trial count")
@click.option("--parallel", default=20, type=int, help="Max concurrent API calls")
@click.option("--catalog", "catalog_path", default=None, help="Path to model catalog YAML")
@click.option("--endpoint", default=None, help="Ad-hoc OpenAI-compatible endpoint URL")
@click.option("--api-key", "api_key", default=None, help="API key for ad-hoc endpoint")
@click.option("--model-name", "model_name", default=None, help="Model name for ad-hoc endpoint")
def skill_test(
    skill_path: str,
    test_cases: str,
    models: str | None,
    trials: int | None,
    parallel: int,
    catalog_path: str | None,
    endpoint: str | None,
    api_key: str | None,
    model_name: str | None,
) -> None:
    """Test a Claude Code skill against test cases."""
    try:
        from skilleval.skill_parser import load_test_cases, parse_skill

        skill_prompt = parse_skill(Path(skill_path))
        cases = load_test_cases(Path(test_cases))
        if not cases:
            raise click.ClickException("No valid test cases found in the specified directory")

        catalog = load_catalog(catalog_path)
        _inject_adhoc(catalog, endpoint, api_key, model_name)

        if models:
            selected = filter_by_names(catalog, models.split(","))
        else:
            selected = filter_available(catalog)

        if not selected:
            raise click.ClickException(
                "No models available. Set API key env vars or use --models to specify."
            )

        for case in cases:
            if trials is not None:
                case.config.trials = trials
            case.skill = skill_prompt.core_prompt

        console.print("[bold]Skill Test[/bold]")
        console.print(f"Skill: {skill_prompt.name or skill_prompt.source_path}")
        console.print(f"Models: {', '.join(m.name for m in selected)}")
        console.print(f"Test cases: {len(cases)}")

        summaries = asyncio.run(_run_skill_test(cases, selected, parallel))

        aggregated: list[tuple[str, list[ModelResult]]] = [
            (Path(case.path).name, summary.model_results)
            for case, summary in zip(cases, summaries)
        ]
        display_skill_test_results(skill_prompt.name or "(unnamed skill)", aggregated)

    except (ValueError, FileNotFoundError) as e:
        raise click.ClickException(str(e))


async def _run_skill_test(cases, selected, parallel):
    """Run all test cases through Mode 1 with a single shared engine."""
    from skilleval.engine import ExecutionEngine
    from skilleval.runner import run_mode1

    async with ExecutionEngine(selected, max_global=parallel) as engine:
        return [await run_mode1(case, selected, engine, parallel) for case in cases]
