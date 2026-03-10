"""CLI commands for SkillEval."""

from __future__ import annotations

import asyncio
import csv
import io
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
    display_history,
    display_lint_report,
    display_matrix_results,
    display_pre_run_estimate,
    display_run_results,
    display_skill_test_results,
)
from skilleval.i18n import t
from skilleval.models import ModelEntry, ModelResult, RunSummary


def _no_models_error(catalog: list[ModelEntry]) -> click.ClickException:
    """Build an actionable error when no models have API keys configured."""
    env_keys = sorted({m.env_key for m in catalog if m.env_key != "_ADHOC_"})
    hint = (
        t("cli.errors.no_models")
        + "\n"
        + "\n".join(f"  export {k}=<your-key>" for k in env_keys)
        + "\n\n"
        + t("cli.errors.or_endpoint")
    )
    return click.ClickException(hint)


# ── Helpers ──────────────────────────────────────────────────────────────


def _inject_adhoc(
    catalog: list[ModelEntry],
    endpoint: str | None,
    api_key: str | None,
    model_name: str | None,
) -> None:
    """Append an ad-hoc model to *catalog* when ``--endpoint`` is provided."""
    if not endpoint:
        return
    if not model_name:
        raise click.ClickException(t("cli.errors.endpoint_requires_model"))
    catalog.append(build_adhoc_model(endpoint, api_key or "", model_name))


def _resolve_output_format(output: str | None, json_output: bool) -> str:
    """Resolve the effective output format from --output and --json flags."""
    if output is not None:
        return output
    return "json" if json_output else "rich"


def _write_run_csv(results: list[ModelResult]) -> str:
    """Serialize Mode 1 results to CSV."""
    buf = io.StringIO(newline="")
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(
        [
            "model",
            "pass_rate",
            "avg_cost",
            "avg_latency",
            "total_cost",
            "context_window",
            "lint_score",
        ]
    )
    for r in sorted(results, key=lambda x: (-x.pass_rate, x.avg_cost)):
        writer.writerow(
            [
                r.model,
                f"{r.pass_rate:.4f}",
                f"{r.avg_cost:.6f}",
                f"{r.avg_latency:.2f}",
                f"{r.total_cost:.6f}",
                r.context_window,
                r.lint_score if r.lint_score is not None else "",
            ]
        )
    return buf.getvalue()


def _write_matrix_csv(cells: list) -> str:
    """Serialize Mode 2 matrix results to CSV."""
    buf = io.StringIO(newline="")
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(
        [
            "creator",
            "executor",
            "pass_rate",
            "avg_cost",
            "total_cost",
            "context_window",
            "lint_score",
        ]
    )
    for c in cells:
        writer.writerow(
            [
                c.creator,
                c.executor,
                f"{c.result.pass_rate:.4f}",
                f"{c.result.avg_cost:.6f}",
                f"{c.result.total_cost:.6f}",
                c.result.context_window,
                c.lint_score if c.lint_score is not None else "",
            ]
        )
    return buf.getvalue()


def _write_chain_csv(cells: list) -> str:
    """Serialize Mode 3 chain results to CSV."""
    buf = io.StringIO(newline="")
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(
        [
            "meta_skill",
            "creator",
            "executor",
            "pass_rate",
            "avg_cost",
            "total_cost",
            "context_window",
            "lint_score",
        ]
    )
    for c in cells:
        writer.writerow(
            [
                c.meta_skill_name,
                c.creator,
                c.executor,
                f"{c.result.pass_rate:.4f}",
                f"{c.result.avg_cost:.6f}",
                f"{c.result.total_cost:.6f}",
                c.result.context_window,
                c.lint_score if c.lint_score is not None else "",
            ]
        )
    return buf.getvalue()


# ── CLI Group ────────────────────────────────────────────────────────────


def _configure_logging(verbosity: int) -> None:
    """Configure the logging level and format based on CLI verbosity."""
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
    if not root_logger.handlers:
        root_logger.addHandler(handler)
    else:
        root_logger.handlers[0] = handler
        root_logger.setLevel(level)


class _SkillEvalGroup(click.Group):
    """Custom Click group with user-friendly exception handling."""

    def invoke(self, ctx: click.Context) -> None:
        try:
            return super().invoke(ctx)
        except click.exceptions.Exit:
            raise
        except click.ClickException:
            raise
        except KeyboardInterrupt:
            console.print(f"\n[yellow]{t('display.messages.interrupted')}[/yellow]")
            ctx.exit(130)
        except Exception as e:
            verbosity = ctx.obj.get("verbosity", 0) if ctx.obj else 0
            if verbosity >= 2:
                raise
            console.print(
                f"\n[red]{t('display.messages.error_prefix')}[/red] {type(e).__name__}: {e}"
            )
            console.print(f"[dim]{t('display.messages.use_vv')}[/dim]")
            ctx.exit(1)


@click.group(cls=_SkillEvalGroup, invoke_without_command=True)
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

    # If no subcommand is given, launch the interactive TUI
    if ctx.invoked_subcommand is None:
        from skilleval.tui import interactive_session

        interactive_session(ctx)


@cli.command()
@click.argument("name")
def init(name: str) -> None:
    """Create a new task folder with template files.

    \b
    Creates the following structure:
        <name>/
            config.yaml      # comparator, trials, model params
            skill.md          # system prompt for Mode 1
            prompt.md         # task description for Mode 2/3
            meta-skill.md     # meta-skill for Mode 3
            input/            # input files the model receives
            expected/         # expected output for comparison
    """
    task_path = Path(name)
    if task_path.exists():
        raise click.ClickException(t("cli.init.dir_exists", name=name))

    task_path.mkdir(parents=True)
    (task_path / "input").mkdir()
    (task_path / "expected").mkdir()

    (task_path / "input" / "example.txt").write_text(
        "Replace this file with your actual input data.\n"
        "You can have multiple input files — they will all be sent to the model.\n"
    )
    (task_path / "expected" / "example.txt").write_text(
        "Replace this file with the expected output.\n"
        "File names must match between input/ and expected/ directories.\n"
    )

    (task_path / "prompt.md").write_text(
        "# Task Description\n\n"
        "Describe what the model should do with the input files.\n"
        "Used in Mode 2 (matrix) and Mode 3 (chain) for skill generation.\n"
    )

    (task_path / "skill.md").write_text(
        "# Task Skill\n\n"
        "Write the system prompt that tells the model\n"
        "exactly how to transform the input into the expected output.\n"
        "Used in Mode 1: `skilleval run " + name + "`\n"
    )

    (task_path / "meta-skill.md").write_text(
        "# Meta-Skill\n\n"
        "Write instructions for how a model should write a task skill.\n"
        "Used in Mode 3: `skilleval chain " + name + " --meta-skills default ...`\n"
        "\n"
        "Tip: Rename to meta-skill-<variant>.md for multiple variants.\n"
    )

    (task_path / "config.yaml").write_text(
        "# SkillEval task configuration\n"
        "\n"
        "# Comparator: how to check if output matches expected\n"
        "# Options: json_exact, csv_ordered, csv_unordered, field_subset,\n"
        "#          text_exact, text_contains, file_hash, custom\n"
        "comparator: json_exact\n"
        "\n"
        "# For custom comparator, path to the script:\n"
        "# custom_script: ./compare.py\n"
        "\n"
        "# Number of trials per model (higher = more confidence, 10+ recommended)\n"
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

    console.print(f"\n[bold green]{t('cli.init.created')}[/bold green] {task_path}/")
    console.print()
    console.print(f"  [dim]config.yaml[/dim]      {t('cli.init.config_desc')}")
    console.print(f"  [dim]skill.md[/dim]          {t('cli.init.skill_desc')}")
    console.print(f"  [dim]prompt.md[/dim]         {t('cli.init.prompt_desc')}")
    console.print(f"  [dim]meta-skill.md[/dim]     {t('cli.init.meta_skill_desc')}")
    console.print(f"  [dim]input/[/dim]            {t('cli.init.input_desc')}")
    console.print(f"  [dim]expected/[/dim]         {t('cli.init.expected_desc')}")
    console.print()
    console.print(f"[bold]{t('cli.init.next_steps')}[/bold]")
    console.print(f"  {t('cli.init.step1', path=task_path)}")
    console.print(f"  {t('cli.init.step2', path=task_path)}")
    console.print(f"  {t('cli.init.step3', path=task_path)}")
    console.print(f"  {t('cli.init.step4', path=task_path)}")
    console.print()
    console.print(f"[dim]{t('cli.init.see_models')}[/dim]")


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
@click.option(
    "--output",
    "output_fmt",
    type=click.Choice(["rich", "json", "csv"]),
    default=None,
    help="Output format (default: rich)",
)
@click.option("--json", "json_output", is_flag=True, hidden=True, help="Alias for --output json")
@click.option(
    "--resume", "resume_dir", default=None, help="Resume a previous run from a checkpoint directory"
)
@click.option(
    "--skill-format",
    "skill_format",
    type=click.Choice(["plain", "claude", "openclaw"]),
    default="plain",
    help="Skill format: 'plain', 'claude', or 'openclaw' (lint + strip scaffolding)",
)
def run(
    task_path: str,
    models: str | None,
    trials: int | None,
    parallel: int,
    catalog_path: str | None,
    endpoint: str | None,
    api_key: str | None,
    model_name: str | None,
    output_fmt: str | None,
    json_output: bool,
    resume_dir: str | None,
    skill_format: str,
) -> None:
    """Mode 1: Evaluate models with a given skill."""
    try:
        fmt = _resolve_output_format(output_fmt, json_output)

        # Load checkpoint if resuming
        completed_models: set[str] = set()
        if resume_dir:
            checkpoint_file = Path(resume_dir) / "checkpoint.json"
            if checkpoint_file.exists():
                checkpoint = json.loads(checkpoint_file.read_text())
                completed_models = set(checkpoint.get("completed_models", []))
                if fmt == "rich":
                    console.print(
                        f"[bold]{t('cli.run.resuming', count=len(completed_models), models=', '.join(sorted(completed_models)))}[/bold]"
                    )
            else:
                if fmt == "rich":
                    console.print(f"[yellow]{t('cli.run.no_checkpoint')}[/yellow]")

        task = load_task(task_path)
        if not task.skill:
            raise click.ClickException(t("cli.run.requires_skill"))

        if trials is not None:
            task.config.trials = trials

        catalog = load_catalog(catalog_path)
        _inject_adhoc(catalog, endpoint, api_key, model_name)

        if models:
            selected = filter_by_names(catalog, models.split(","))
        else:
            selected = filter_available(catalog)

        if not selected:
            raise _no_models_error(catalog)

        # Filter out already-completed models when resuming
        if completed_models:
            selected = [m for m in selected if m.name not in completed_models]
            if not selected:
                if fmt == "rich":
                    console.print(f"[bold green]{t('cli.run.all_completed')}[/bold green]")
                return

        num_calls = len(selected) * task.config.trials
        avg_input_cost = sum(m.input_cost_per_m for m in selected) / len(selected)
        avg_output_cost = sum(m.output_cost_per_m for m in selected) / len(selected)
        estimated_cost = num_calls * (
            1000 / 1_000_000 * avg_input_cost + 4000 / 1_000_000 * avg_output_cost
        )

        if fmt == "rich":
            console.print(f"[bold]{t('cli.run.title')}[/bold]")
            console.print(f"{t('cli.run.task_label')} {task.path}")
            console.print(f"{t('cli.run.models_label')} {', '.join(m.name for m in selected)}")
            console.print(f"{t('cli.run.trials_label')} {task.config.trials}")
            display_pre_run_estimate(num_calls, estimated_cost)

        summary = asyncio.run(_run_mode1(task, selected, parallel, skill_format))

        if fmt == "json":
            click.echo(summary.model_dump_json(indent=2))
        elif fmt == "csv":
            click.echo(_write_run_csv(summary.model_results), nl=False)
        else:
            display_run_results(summary.model_results, summary.recommendation)

    except (ValueError, FileNotFoundError) as e:
        raise click.ClickException(str(e))


async def _run_mode1(task, selected, parallel, skill_format="plain"):
    from skilleval.engine import ExecutionEngine
    from skilleval.runner import run_mode1

    async with ExecutionEngine(selected, max_global=parallel) as engine:
        return await run_mode1(task, selected, engine, parallel, skill_format=skill_format)


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
@click.option(
    "--output",
    "output_fmt",
    type=click.Choice(["rich", "json", "csv"]),
    default=None,
    help="Output format (default: rich)",
)
@click.option("--json", "json_output", is_flag=True, hidden=True, help="Alias for --output json")
@click.option(
    "--skill-format",
    "skill_format",
    type=click.Choice(["plain", "claude", "openclaw"]),
    default="plain",
    help="Skill format: 'plain', 'claude', or 'openclaw' (lint + strip scaffolding)",
)
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
    output_fmt: str | None,
    json_output: bool,
    skill_format: str,
) -> None:
    """Mode 2: Creator x executor matrix evaluation."""
    try:
        fmt = _resolve_output_format(output_fmt, json_output)

        task = load_task(task_path)
        if not task.prompt:
            raise click.ClickException(t("cli.matrix.requires_prompt"))

        if trials is not None:
            task.config.trials = trials

        catalog = load_catalog(catalog_path)
        _inject_adhoc(catalog, endpoint, api_key, model_name)

        creator_models = filter_by_names(catalog, creators.split(","))
        executor_models = filter_by_names(catalog, executors.split(","))

        num_calls = (
            len(creator_models) + len(creator_models) * len(executor_models) * task.config.trials
        )
        all_models = creator_models + executor_models
        avg_input_cost = sum(m.input_cost_per_m for m in all_models) / len(all_models)
        avg_output_cost = sum(m.output_cost_per_m for m in all_models) / len(all_models)
        estimated_cost = num_calls * (
            1000 / 1_000_000 * avg_input_cost + 4000 / 1_000_000 * avg_output_cost
        )

        if fmt == "rich":
            console.print(f"[bold]{t('cli.matrix.title')}[/bold]")
            console.print(f"{t('cli.run.task_label')} {task.path}")
            console.print(
                f"{t('cli.matrix.creators_label')} {', '.join(m.name for m in creator_models)}"
            )
            console.print(
                f"{t('cli.matrix.executors_label')} {', '.join(m.name for m in executor_models)}"
            )
            display_pre_run_estimate(num_calls, estimated_cost)

        summary = asyncio.run(
            _run_mode2(task, creator_models, executor_models, parallel, skill_format)
        )

        if fmt == "json":
            click.echo(summary.model_dump_json(indent=2))
        elif fmt == "csv":
            click.echo(_write_matrix_csv(summary.matrix_results), nl=False)
        else:
            display_matrix_results(summary.matrix_results)
            if summary.recommendation:
                console.print(
                    f"\n[bold green]{t('display.messages.recommendation')}[/bold green] {summary.recommendation}"
                )

    except (ValueError, FileNotFoundError) as e:
        raise click.ClickException(str(e))


async def _run_mode2(task, creator_models, executor_models, parallel, skill_format="plain"):
    from skilleval.engine import ExecutionEngine
    from skilleval.runner import run_mode2

    all_models = list({m.name: m for m in creator_models + executor_models}.values())
    async with ExecutionEngine(all_models, max_global=parallel) as engine:
        return await run_mode2(
            task, creator_models, executor_models, engine, skill_format=skill_format
        )


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
@click.option(
    "--output",
    "output_fmt",
    type=click.Choice(["rich", "json", "csv"]),
    default=None,
    help="Output format (default: rich)",
)
@click.option("--json", "json_output", is_flag=True, hidden=True, help="Alias for --output json")
@click.option(
    "--skill-format",
    "skill_format",
    type=click.Choice(["plain", "claude", "openclaw"]),
    default="plain",
    help="Skill format: 'plain', 'claude', or 'openclaw' (lint + strip scaffolding)",
)
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
    output_fmt: str | None,
    json_output: bool,
    skill_format: str,
) -> None:
    """Mode 3: Meta-skill x creator x executor chain evaluation."""
    try:
        fmt = _resolve_output_format(output_fmt, json_output)

        task = load_task(task_path)
        if not task.prompt:
            raise click.ClickException(t("cli.chain.requires_prompt"))

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
                available = (
                    ", ".join(sorted(task.meta_skills.keys())) if task.meta_skills else "none"
                )
                raise click.ClickException(
                    t("cli.errors.meta_skill_not_found", name=ms_name, available=available)
                )

        # Estimate API calls
        gen_calls = len(meta_skill_names) * len(creator_models)
        exec_calls = (
            len(meta_skill_names) * len(creator_models) * len(executor_models) * task.config.trials
        )
        total_calls = gen_calls + exec_calls
        all_models = creator_models + executor_models
        avg_input_cost = sum(m.input_cost_per_m for m in all_models) / len(all_models)
        avg_output_cost = sum(m.output_cost_per_m for m in all_models) / len(all_models)
        estimated_cost = total_calls * (
            1000 / 1_000_000 * avg_input_cost + 4000 / 1_000_000 * avg_output_cost
        )

        if fmt == "rich":
            console.print(f"[bold]{t('cli.chain.title')}[/bold]")
            console.print(f"{t('cli.run.task_label')} {task.path}")
            console.print(f"{t('cli.chain.meta_skills_label')} {', '.join(meta_skill_names)}")
            console.print(
                f"{t('cli.matrix.creators_label')} {', '.join(m.name for m in creator_models)}"
            )
            console.print(
                f"{t('cli.matrix.executors_label')} {', '.join(m.name for m in executor_models)}"
            )
            display_pre_run_estimate(total_calls, estimated_cost)

        if total_calls > 100 and not yes:
            if not click.confirm(t("cli.chain.proceed_confirm")):
                click.echo(t("cli.chain.aborted"))
                return

        summary = asyncio.run(
            _run_mode3(
                task, meta_skill_names, creator_models, executor_models, parallel, skill_format
            )
        )

        if fmt == "json":
            click.echo(summary.model_dump_json(indent=2))
        elif fmt == "csv":
            click.echo(_write_chain_csv(summary.chain_results), nl=False)
        else:
            display_chain_results(summary.chain_results)
            if summary.recommendation:
                console.print(
                    f"\n[bold green]{t('display.messages.recommendation')}[/bold green] {summary.recommendation}"
                )

    except (ValueError, FileNotFoundError) as e:
        raise click.ClickException(str(e))


async def _run_mode3(
    task, meta_skill_names, creator_models, executor_models, parallel, skill_format="plain"
):
    from skilleval.engine import ExecutionEngine
    from skilleval.runner import run_mode3

    all_models = list({m.name: m for m in creator_models + executor_models}.values())
    async with ExecutionEngine(all_models, max_global=parallel) as engine:
        return await run_mode3(
            task,
            meta_skill_names,
            creator_models,
            executor_models,
            engine,
            skill_format=skill_format,
        )


# ── Utility Commands ─────────────────────────────────────────────────────


@cli.command("catalog")
@click.option("--catalog", "catalog_path", default=None, help="Path to model catalog YAML")
@click.option("--json", "json_output", is_flag=True, help="Output catalog as JSON")
def catalog_cmd(catalog_path: str | None, json_output: bool) -> None:
    """Display model catalog with availability status."""
    try:
        catalog = load_catalog(catalog_path)
        available = filter_available(catalog)
        available_names = [m.name for m in available]

        if json_output:
            import json as json_mod

            data = [
                {
                    "name": m.name,
                    "provider": m.provider,
                    "input_cost_per_m": m.input_cost_per_m,
                    "output_cost_per_m": m.output_cost_per_m,
                    "context_window": m.context_window,
                    "env_key": m.env_key,
                    "available": m.name in set(available_names),
                }
                for m in catalog
            ]
            click.echo(json_mod.dumps(data, indent=2))
        else:
            display_catalog(catalog, available_names)

    except (ValueError, FileNotFoundError) as e:
        raise click.ClickException(str(e))


@cli.command()
@click.argument("results_path")
@click.option("--html", "html_path", default=None, help="Generate HTML report at path")
@click.option("--open", "open_browser", is_flag=True, help="Open HTML in browser")
@click.option("--json", "json_output", is_flag=True, help="Output results as JSON")
def report(results_path: str, html_path: str | None, open_browser: bool, json_output: bool) -> None:
    """Re-render results from a previous run."""
    try:
        path = Path(results_path)

        # Support "skilleval report ./my-task" → resolve .skilleval/latest
        if path.is_dir() and not (path / "results.json").exists():
            latest = path / ".skilleval" / "latest"
            if latest.is_symlink() or latest.is_dir():
                path = latest.resolve()
            elif (path / ".skilleval").is_dir():
                runs = sorted(
                    (d for d in (path / ".skilleval").iterdir() if d.name.startswith("run-")),
                    reverse=True,
                )
                if runs:
                    path = runs[0]
                else:
                    raise click.ClickException(t("cli.report.no_runs_in", path=path / ".skilleval"))
            else:
                raise click.ClickException(t("cli.report.no_results", path=path))

        results_file = path / "results.json" if path.is_dir() else path

        if not results_file.exists():
            raise click.ClickException(t("cli.report.not_found", path=results_file))

        data = json.loads(results_file.read_text())
        summary = RunSummary(**data)

        if json_output:
            click.echo(summary.model_dump_json(indent=2))
            return

        if html_path:
            from skilleval.html_report import generate_html_report

            out = generate_html_report(summary, Path(html_path))
            click.echo(t("cli.report.html_written", path=out))
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
            click.echo(t("cli.report.unknown_mode", mode=summary.mode))

        if summary.recommendation:
            console.print(
                f"\n[bold green]{t('display.messages.recommendation')}[/bold green] {summary.recommendation}"
            )

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


@cli.command()
@click.argument("task_path")
@click.option("--json", "json_output", is_flag=True, help="Output history as JSON")
def history(task_path: str, json_output: bool) -> None:
    """List past evaluation runs for a task."""
    try:
        from skilleval.results import load_run_history

        runs = load_run_history(Path(task_path))
        if not runs:
            console.print(f"[yellow]{t('cli.history.no_runs', path=task_path)}[/yellow]")
            console.print(f"[dim]{t('cli.history.create_hint', path=task_path)}[/dim]")
            return

        if json_output:
            out = []
            for r in runs:
                entry = {k: v for k, v in r.items() if k != "path"}
                out.append(entry)
            click.echo(json.dumps(out, indent=2))
        else:
            display_history(runs, task_path)
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
            raise click.ClickException(t("cli.skill_test.no_cases"))

        catalog = load_catalog(catalog_path)
        _inject_adhoc(catalog, endpoint, api_key, model_name)

        if models:
            selected = filter_by_names(catalog, models.split(","))
        else:
            selected = filter_available(catalog)

        if not selected:
            raise _no_models_error(catalog)

        for case in cases:
            if trials is not None:
                case.config.trials = trials
            case.skill = skill_prompt.core_prompt

        console.print(f"[bold]{t('cli.skill_test.title')}[/bold]")
        console.print(
            f"{t('cli.skill_test.skill_label')} {skill_prompt.name or skill_prompt.source_path}"
        )
        console.print(f"{t('cli.run.models_label')} {', '.join(m.name for m in selected)}")
        console.print(f"{t('cli.skill_test.test_cases_label')} {len(cases)}")

        summaries = asyncio.run(_run_skill_test(cases, selected, parallel))

        aggregated: list[tuple[str, list[ModelResult]]] = [
            (Path(case.path).name, summary.model_results) for case, summary in zip(cases, summaries)
        ]
        display_skill_test_results(skill_prompt.name or "(unnamed skill)", aggregated)

    except (ValueError, FileNotFoundError) as e:
        raise click.ClickException(str(e))


async def _run_skill_test(cases, selected, parallel):
    """Run all test cases through Mode 1 concurrently with a single shared engine."""
    from skilleval.engine import ExecutionEngine
    from skilleval.runner import run_mode1

    async with ExecutionEngine(selected, max_global=parallel) as engine:
        return await asyncio.gather(
            *(run_mode1(case, selected, engine, parallel) for case in cases)
        )
