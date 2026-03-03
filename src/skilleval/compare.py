"""Compare two SkillEval run results and summarize changes."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable

from skilleval.models import ChainCell, MatrixCell, RunSummary


@dataclass
class ComparisonEntry:
    model: str
    old_pass_rate: float
    new_pass_rate: float
    old_avg_cost: float
    new_avg_cost: float
    old_avg_latency: float
    new_avg_latency: float
    status: str  # "improved" | "regressed" | "unchanged" | "new" | "removed"


@dataclass
class ComparisonReport:
    old_path: str
    new_path: str
    mode: str
    entries: list[ComparisonEntry]
    summary: str


def _load_summary(path: Path) -> RunSummary:
    results_path = path / "results.json"
    data = json.loads(results_path.read_text())
    return RunSummary(**data)


def _pairs_from_run(summary: RunSummary) -> dict[str, tuple[float, float, float]]:
    return {mr.model: (mr.pass_rate, mr.avg_cost, mr.avg_latency) for mr in summary.model_results}


def _pairs_from_matrix(summary: RunSummary) -> dict[str, tuple[float, float, float]]:
    def label(cell: MatrixCell) -> str:
        return f"{cell.creator} -> {cell.executor}"

    return {
        label(c): (c.result.pass_rate, c.result.avg_cost, c.result.avg_latency)
        for c in summary.matrix_results
    }


def _pairs_from_chain(summary: RunSummary) -> dict[str, tuple[float, float, float]]:
    def label(cell: ChainCell) -> str:
        return f"{cell.meta_skill_name} / {cell.creator} -> {cell.executor}"

    return {
        label(c): (c.result.pass_rate, c.result.avg_cost, c.result.avg_latency)
        for c in summary.chain_results
    }


def _classify(old: float, new: float, eps: float = 1e-9) -> str:
    if new - old > eps:
        return "improved"
    if old - new > eps:
        return "regressed"
    return "unchanged"


def _build_entries(
    old_map: dict[str, tuple[float, float, float]],
    new_map: dict[str, tuple[float, float, float]],
) -> list[ComparisonEntry]:
    entries: list[ComparisonEntry] = []
    all_keys = set(old_map) | set(new_map)

    for key in sorted(all_keys):
        if key in old_map and key in new_map:
            o_rate, o_cost, o_lat = old_map[key]
            n_rate, n_cost, n_lat = new_map[key]
            status = _classify(o_rate, n_rate)
            entries.append(
                ComparisonEntry(
                    model=key,
                    old_pass_rate=o_rate,
                    new_pass_rate=n_rate,
                    old_avg_cost=o_cost,
                    new_avg_cost=n_cost,
                    old_avg_latency=o_lat,
                    new_avg_latency=n_lat,
                    status=status,
                )
            )
        elif key in new_map:
            n_rate, n_cost, n_lat = new_map[key]
            entries.append(
                ComparisonEntry(
                    model=key,
                    old_pass_rate=0.0,
                    new_pass_rate=n_rate,
                    old_avg_cost=0.0,
                    new_avg_cost=n_cost,
                    old_avg_latency=0.0,
                    new_avg_latency=n_lat,
                    status="new",
                )
            )
        else:  # key in old_map only
            o_rate, o_cost, o_lat = old_map[key]
            entries.append(
                ComparisonEntry(
                    model=key,
                    old_pass_rate=o_rate,
                    new_pass_rate=0.0,
                    old_avg_cost=o_cost,
                    new_avg_cost=0.0,
                    old_avg_latency=o_lat,
                    new_avg_latency=0.0,
                    status="removed",
                )
            )

    return entries


def _summarize(entries: Iterable[ComparisonEntry]) -> str:
    improved = sum(1 for e in entries if e.status == "improved")
    regressed = sum(1 for e in entries if e.status == "regressed")
    unchanged = sum(1 for e in entries if e.status == "unchanged")
    return f"{improved} improved, {regressed} regressed, {unchanged} unchanged"


def compare_runs(old_path: Path, new_path: Path) -> ComparisonReport:
    """Compare two SkillEval runs located at directories containing results.json.

    Returns a ComparisonReport with per-entry changes and a short summary.
    Raises ValueError if the run modes don't match.
    """

    old = _load_summary(old_path)
    new = _load_summary(new_path)

    if old.mode != new.mode:
        raise ValueError(f"Mismatched modes: {old.mode} vs {new.mode}")

    if old.mode == "run":
        old_map = _pairs_from_run(old)
        new_map = _pairs_from_run(new)
    elif old.mode == "matrix":
        old_map = _pairs_from_matrix(old)
        new_map = _pairs_from_matrix(new)
    elif old.mode == "chain":
        old_map = _pairs_from_chain(old)
        new_map = _pairs_from_chain(new)
    else:
        raise ValueError(f"Unsupported mode: {old.mode}")

    entries = _build_entries(old_map, new_map)
    summary = _summarize(entries)

    return ComparisonReport(
        old_path=str(old_path),
        new_path=str(new_path),
        mode=old.mode,
        entries=entries,
        summary=summary,
    )
