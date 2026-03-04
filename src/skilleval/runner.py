"""Mode orchestrators for SkillEval evaluation runs."""

from __future__ import annotations

import asyncio
import logging
import tempfile
from datetime import datetime
from pathlib import Path

from skilleval.comparators import get_comparator
from skilleval.comparators.base import strip_markdown_fences, strip_reasoning_tags
from skilleval.display import console, create_progress, display_results_path
from skilleval.documents import format_input_files, input_descriptions
from skilleval.engine import ExecutionEngine, TrialSpec
from skilleval.i18n import t
from skilleval.models import (
    ChainCell,
    MatrixCell,
    ModelEntry,
    ModelResult,
    RunSummary,
    TaskFolder,
    TrialResult,
)
from skilleval.results import ResultWriter

logger = logging.getLogger(__name__)


# ── Shared helpers ──────────────────────────────────────────────────────


def _clean_output(text: str) -> str:
    """Strip reasoning tags, whitespace, and markdown fences from model output."""
    text = strip_reasoning_tags(text)
    text = strip_markdown_fences(text.strip())
    return text.strip()


def _save_and_compare(
    task: TaskFolder,
    output_text: str,
    comparator_kwargs: dict,
) -> tuple[bool, str | None]:
    """Save output to a temp dir and run the comparator against expected files."""
    comparator = get_comparator(task.config.comparator, **comparator_kwargs)
    cleaned = _clean_output(output_text)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for expected_file in task.expected_files:
            (tmp_dir / expected_file.name).write_text(cleaned)
        return comparator.compare(tmp_dir, task.path / "expected")


def _aggregate_trials(
    model_name: str, trials: list[TrialResult], context_window: int = 0
) -> ModelResult:
    """Aggregate individual trials into a ModelResult."""
    if not trials:
        return ModelResult(
            model=model_name,
            pass_rate=0.0,
            trials=[],
            avg_cost=0.0,
            avg_latency=0.0,
            total_cost=0.0,
            context_window=context_window,
        )

    passed = sum(1 for t in trials if t.passed)
    total_cost = sum(t.cost for t in trials)
    total_latency = sum(t.latency_seconds for t in trials)
    n = len(trials)

    return ModelResult(
        model=model_name,
        pass_rate=passed / n,
        trials=trials,
        avg_cost=total_cost / n,
        avg_latency=total_latency / n,
        total_cost=total_cost,
        context_window=context_window,
    )


def _build_comparator_kwargs(task: TaskFolder) -> dict:
    """Extract comparator kwargs from task config."""
    kwargs: dict = {}
    if task.config.comparator == "custom" and task.config.custom_script:
        kwargs["custom_script"] = task.config.custom_script
    return kwargs


def _compute_recommendation(
    candidates: list[tuple[str, ModelResult]],
    num_trials: int,
) -> str | None:
    """Find the cheapest candidate with 100% pass rate.

    *candidates* is a list of ``(label, ModelResult)`` pairs where *label*
    is a human-readable identifier (model name, creator→executor pair, etc.).

    At equal cost, prefers the model with a larger context window.
    """
    perfect = [(label, r) for label, r in candidates if r.pass_rate == 1.0]
    if not perfect:
        return None

    # Sort by cost ascending, then context_window descending (prefer larger)
    label, result = min(perfect, key=lambda pair: (pair[1].avg_cost, -pair[1].context_window))
    rec = f"{label} (${result.avg_cost:.6f}/run)"
    if result.context_window > 0:
        rec += f" [{result.context_window:,} ctx]"
    if num_trials < 10:
        rec += " [warning: trials < 10, consider increasing for confidence]"
    return rec


async def _execute_with_progress(
    engine: ExecutionEngine,
    specs: list[TrialSpec],
    label: str | None = None,
) -> tuple[list[TrialResult], bool]:
    """Execute specs with a Rich progress bar, handling interrupts.

    Returns ``(results, interrupted)``.
    """
    if label is None:
        label = t("runner.running_trials")
    interrupted = False
    results: list[TrialResult] = []
    try:
        with create_progress() as progress:
            ptask = progress.add_task(label, total=len(specs))

            def on_progress(result: TrialResult) -> None:
                progress.advance(ptask)

            results = await engine.execute_batch(specs, on_progress=on_progress)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.warning("Run interrupted. Saving partial results...")
        interrupted = True
    return results, interrupted


async def _finalize_run(
    writer: ResultWriter,
    summary: RunSummary,
    interrupted: bool,
) -> None:
    """Write summary to disk, display results path, and re-raise if interrupted."""
    await writer.write_summary_async(summary)
    display_results_path(writer.run_dir)
    if interrupted:
        raise KeyboardInterrupt


# ── Mode 1 ──────────────────────────────────────────────────────────────


async def run_mode1(
    task: TaskFolder,
    models: list[ModelEntry],
    engine: ExecutionEngine,
    parallel: int,
) -> RunSummary:
    """Mode 1: Given skill, sweep executor models."""
    if not task.skill:
        raise ValueError("Mode 1 requires skill.md in the task folder")

    logger.info(
        "Mode 1 starting: %d models, %d trials each",
        len(models),
        task.config.trials,
    )

    writer = ResultWriter(task.path, "run")
    user_content = format_input_files(task.input_files)
    comparator_kwargs = _build_comparator_kwargs(task)

    specs: list[TrialSpec] = []
    for model in models:
        for trial_num in range(1, task.config.trials + 1):
            specs.append(
                TrialSpec(
                    model=model,
                    messages=[
                        {"role": "system", "content": task.skill},
                        {"role": "user", "content": user_content},
                    ],
                    config=task.config,
                    trial_number=trial_num,
                )
            )

    results, interrupted = await _execute_with_progress(engine, specs)

    # Compare outputs
    model_trials: dict[str, list[TrialResult]] = {}
    for trial in results:
        if trial.error:
            passed, diff = False, trial.error
        else:
            passed, diff = await asyncio.to_thread(
                _save_and_compare,
                task,
                trial.output_text,
                comparator_kwargs,
            )
        trial.passed = passed
        trial.diff = diff

        model_trials.setdefault(trial.model, []).append(trial)

        await writer.write_trial_output_async(
            model=trial.model,
            trial_num=trial.trial_number,
            output_text=trial.output_text,
            diff=diff,
            meta={
                "input_tokens": trial.input_tokens,
                "output_tokens": trial.output_tokens,
                "cost": trial.cost,
                "latency": trial.latency_seconds,
                "passed": passed,
                "finish_reason": trial.finish_reason,
                "error": trial.error,
            },
        )

    ctx_lookup = {m.name: m.context_window for m in models}
    model_results = [
        _aggregate_trials(name, trials, context_window=ctx_lookup.get(name, 0))
        for name, trials in model_trials.items()
    ]
    candidates = [(r.model, r) for r in model_results]
    recommendation = _compute_recommendation(candidates, task.config.trials)

    total_passed = sum(1 for t in results if t.passed)
    logger.info(
        "Mode 1 %s: %d/%d trials passed across %d models",
        "interrupted" if interrupted else "complete",
        total_passed,
        len(results),
        len(model_results),
    )

    summary = RunSummary(
        mode="run",
        task_path=task.path.name,
        timestamp=datetime.now().isoformat(),
        model_results=model_results,
        recommendation=recommendation,
    )
    await _finalize_run(writer, summary, interrupted)
    return summary


# ── Mode 2 ──────────────────────────────────────────────────────────────


async def run_mode2(
    task: TaskFolder,
    creators: list[ModelEntry],
    executors: list[ModelEntry],
    engine: ExecutionEngine,
) -> RunSummary:
    """Mode 2: Creator x executor matrix."""
    if not task.prompt:
        raise ValueError("Mode 2 requires prompt.md in the task folder")

    logger.info(
        "Mode 2 starting: %d creators, %d executors, %d trials",
        len(creators),
        len(executors),
        task.config.trials,
    )

    writer = ResultWriter(task.path, "matrix")
    user_content = format_input_files(task.input_files)
    input_desc = input_descriptions(task.input_files)
    comparator_kwargs = _build_comparator_kwargs(task)

    # Phase 1: Skill Generation
    console.print(f"[bold]{t('runner.phase1_generating')}[/bold]")
    creator_specs: list[TrialSpec] = []
    for creator in creators:
        creator_specs.append(
            TrialSpec(
                model=creator,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Write a task skill based on this description:\n\n"
                            + task.prompt
                            + "\n\nInput files the executor will receive:\n"
                            + input_desc
                        ),
                    }
                ],
                config=task.config,
                trial_number=1,
            )
        )

    skill_results, interrupted = await _execute_with_progress(
        engine,
        creator_specs,
        t("runner.phase1_generating"),
    )

    generated_skills: dict[str, str] = {}
    for i, creator in enumerate(creators):
        if i >= len(skill_results):
            generated_skills[creator.name] = ""
            continue
        result = skill_results[i]
        if result.error:
            console.print(
                f"[red]{t('display.messages.skill_gen_failed', name=creator.name, error=result.error)}[/red]"
            )
            generated_skills[creator.name] = ""
        else:
            generated_skills[creator.name] = result.output_text
            writer.write_generated_skill(creator.name, result.output_text)

    # Phase 2: Execution
    exec_specs: list[TrialSpec] = []
    spec_keys: list[tuple[str, str]] = []
    exec_results: list[TrialResult] = []

    if not interrupted:
        console.print(f"[bold]{t('runner.phase2_executing')}[/bold]")
        for creator in creators:
            skill_text = generated_skills[creator.name]
            if not skill_text:
                continue
            for executor in executors:
                for trial_num in range(1, task.config.trials + 1):
                    exec_specs.append(
                        TrialSpec(
                            model=executor,
                            messages=[
                                {"role": "system", "content": skill_text},
                                {"role": "user", "content": user_content},
                            ],
                            config=task.config,
                            trial_number=trial_num,
                        )
                    )
                    spec_keys.append((creator.name, executor.name))

        exec_results, exec_interrupted = await _execute_with_progress(
            engine,
            exec_specs,
        )
        interrupted = interrupted or exec_interrupted

    # Compare and aggregate
    pair_trials: dict[tuple[str, str], list[TrialResult]] = {}
    for i, trial in enumerate(exec_results):
        cr_name, ex_name = spec_keys[i]
        if trial.error:
            passed, diff = False, trial.error
        else:
            passed, diff = await asyncio.to_thread(
                _save_and_compare,
                task,
                trial.output_text,
                comparator_kwargs,
            )
        trial.passed = passed
        trial.diff = diff

        pair_trials.setdefault((cr_name, ex_name), []).append(trial)

        await writer.write_trial_output_async(
            model=f"{cr_name}__{ex_name}",
            trial_num=trial.trial_number,
            output_text=trial.output_text,
            diff=diff,
            meta={
                "creator": cr_name,
                "executor": ex_name,
                "input_tokens": trial.input_tokens,
                "output_tokens": trial.output_tokens,
                "cost": trial.cost,
                "latency": trial.latency_seconds,
                "passed": passed,
            },
        )

    ctx_lookup = {m.name: m.context_window for m in creators + executors}
    matrix_results: list[MatrixCell] = []
    for (cr_name, ex_name), trials in pair_trials.items():
        model_result = _aggregate_trials(ex_name, trials, context_window=ctx_lookup.get(ex_name, 0))
        matrix_results.append(
            MatrixCell(
                creator=cr_name,
                executor=ex_name,
                generated_skill=generated_skills[cr_name],
                result=model_result,
            )
        )

    candidates = [(f"{c.creator} -> {c.executor}", c.result) for c in matrix_results]
    recommendation = _compute_recommendation(candidates, task.config.trials)

    total_passed = sum(1 for t in exec_results if t.passed)
    logger.info(
        "Mode 2 %s: %d/%d trials passed across %d pairs",
        "interrupted" if interrupted else "complete",
        total_passed,
        len(exec_results),
        len(matrix_results),
    )

    summary = RunSummary(
        mode="matrix",
        task_path=task.path.name,
        timestamp=datetime.now().isoformat(),
        matrix_results=matrix_results,
        recommendation=recommendation,
    )
    await _finalize_run(writer, summary, interrupted)
    return summary


# ── Mode 3 ──────────────────────────────────────────────────────────────


async def run_mode3(
    task: TaskFolder,
    meta_skill_names: list[str],
    creators: list[ModelEntry],
    executors: list[ModelEntry],
    engine: ExecutionEngine,
) -> RunSummary:
    """Mode 3: Meta-skill x creator x executor chain."""
    if not task.prompt:
        raise ValueError("Mode 3 requires prompt.md in the task folder")

    logger.info(
        "Mode 3 starting: %d meta-skills, %d creators, %d executors, %d trials",
        len(meta_skill_names),
        len(creators),
        len(executors),
        task.config.trials,
    )

    writer = ResultWriter(task.path, "chain")
    user_content = format_input_files(task.input_files)
    input_desc = input_descriptions(task.input_files)
    comparator_kwargs = _build_comparator_kwargs(task)

    # Validate meta-skills
    for ms_name in meta_skill_names:
        if ms_name not in task.meta_skills:
            available = ", ".join(sorted(task.meta_skills.keys())) if task.meta_skills else "none"
            raise ValueError(f"Meta-skill '{ms_name}' not found. Available: {available}")

    # Phase 1: Skill Generation
    interrupted = False
    console.print(f"[bold]{t('runner.phase1_generating_meta')}[/bold]")
    gen_specs: list[TrialSpec] = []
    gen_keys: list[tuple[str, str]] = []

    for ms_name in meta_skill_names:
        ms_content = task.meta_skills[ms_name]
        for creator in creators:
            gen_specs.append(
                TrialSpec(
                    model=creator,
                    messages=[
                        {"role": "system", "content": ms_content},
                        {
                            "role": "user",
                            "content": (
                                "Write a task skill for this task:\n\n"
                                + task.prompt
                                + "\n\nInput files:\n"
                                + input_desc
                            ),
                        },
                    ],
                    config=task.config,
                    trial_number=1,
                )
            )
            gen_keys.append((ms_name, creator.name))

    gen_results, interrupted = await _execute_with_progress(
        engine,
        gen_specs,
        t("runner.phase1_generating"),
    )

    generated_skills: dict[tuple[str, str], str] = {}
    for i, (ms_name, cr_name) in enumerate(gen_keys):
        if i >= len(gen_results):
            generated_skills[(ms_name, cr_name)] = ""
            continue
        result = gen_results[i]
        if result.error:
            console.print(
                f"[red]{t('display.messages.skill_gen_failed', name=f'{ms_name}/{cr_name}', error=result.error)}[/red]"
            )
            generated_skills[(ms_name, cr_name)] = ""
        else:
            generated_skills[(ms_name, cr_name)] = result.output_text
            writer.write_generated_skill(cr_name, result.output_text, meta_skill=ms_name)

    # Phase 2: Execution
    exec_specs: list[TrialSpec] = []
    exec_keys: list[tuple[str, str, str]] = []
    exec_results: list[TrialResult] = []

    if not interrupted:
        console.print(f"[bold]{t('runner.phase2_executing')}[/bold]")
        for ms_name in meta_skill_names:
            for creator in creators:
                skill_text = generated_skills.get((ms_name, creator.name), "")
                if not skill_text:
                    continue
                for executor in executors:
                    for trial_num in range(1, task.config.trials + 1):
                        exec_specs.append(
                            TrialSpec(
                                model=executor,
                                messages=[
                                    {"role": "system", "content": skill_text},
                                    {"role": "user", "content": user_content},
                                ],
                                config=task.config,
                                trial_number=trial_num,
                            )
                        )
                        exec_keys.append((ms_name, creator.name, executor.name))

        exec_results, exec_interrupted = await _execute_with_progress(
            engine,
            exec_specs,
        )
        interrupted = interrupted or exec_interrupted

    # Compare and aggregate
    chain_trials: dict[tuple[str, str, str], list[TrialResult]] = {}
    for i, trial in enumerate(exec_results):
        ms_name, cr_name, ex_name = exec_keys[i]
        if trial.error:
            passed, diff = False, trial.error
        else:
            passed, diff = await asyncio.to_thread(
                _save_and_compare,
                task,
                trial.output_text,
                comparator_kwargs,
            )
        trial.passed = passed
        trial.diff = diff

        chain_trials.setdefault((ms_name, cr_name, ex_name), []).append(trial)

        await writer.write_trial_output_async(
            model=f"{ms_name}__{cr_name}__{ex_name}",
            trial_num=trial.trial_number,
            output_text=trial.output_text,
            diff=diff,
            meta={
                "meta_skill": ms_name,
                "creator": cr_name,
                "executor": ex_name,
                "input_tokens": trial.input_tokens,
                "output_tokens": trial.output_tokens,
                "cost": trial.cost,
                "latency": trial.latency_seconds,
                "passed": passed,
            },
        )

    ctx_lookup = {m.name: m.context_window for m in creators + executors}
    chain_results: list[ChainCell] = []
    for (ms_name, cr_name, ex_name), trials in chain_trials.items():
        model_result = _aggregate_trials(ex_name, trials, context_window=ctx_lookup.get(ex_name, 0))
        chain_results.append(
            ChainCell(
                meta_skill_name=ms_name,
                creator=cr_name,
                executor=ex_name,
                generated_skill=generated_skills.get((ms_name, cr_name), ""),
                result=model_result,
            )
        )

    candidates = [
        (f"{c.meta_skill_name} / {c.creator} -> {c.executor}", c.result) for c in chain_results
    ]
    recommendation = _compute_recommendation(candidates, task.config.trials)

    total_passed = sum(1 for t in exec_results if t.passed)
    logger.info(
        "Mode 3 %s: %d/%d trials passed across %d chains",
        "interrupted" if interrupted else "complete",
        total_passed,
        len(exec_results),
        len(chain_results),
    )

    summary = RunSummary(
        mode="chain",
        task_path=task.path.name,
        timestamp=datetime.now().isoformat(),
        chain_results=chain_results,
        recommendation=recommendation,
    )
    await _finalize_run(writer, summary, interrupted)
    return summary
