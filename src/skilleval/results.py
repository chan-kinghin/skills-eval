"""Result storage for SkillEval runs."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from skilleval.models import RunSummary


class ResultWriter:
    """Writes trial outputs, generated skills, and summaries to disk."""

    def __init__(self, task_path: Path, mode: str) -> None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self._skilleval_dir = task_path / ".skilleval"
        self.run_dir = self._skilleval_dir / f"run-{timestamp}"
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.mode = mode
        self._task_name = task_path.name

    def write_trial_output(
        self,
        model: str,
        trial_num: int,
        output_text: str,
        diff: str | None,
        meta: dict,
    ) -> None:
        """Save trial output, diff, and metadata.

        Directory layout: .skilleval/run-XXX/<model>/trial-N/
        """
        trial_dir = self.run_dir / model / f"trial-{trial_num}"
        trial_dir.mkdir(parents=True, exist_ok=True)

        (trial_dir / "output.txt").write_text(output_text)

        if diff is not None:
            (trial_dir / "diff.txt").write_text(diff)

        (trial_dir / "meta.json").write_text(json.dumps(meta, indent=2))

    def write_generated_skill(
        self,
        creator: str,
        skill_text: str,
        meta_skill: str | None = None,
    ) -> None:
        """Save generated skill (Mode 2/3)."""
        skills_dir = self.run_dir / "generated_skills"
        skills_dir.mkdir(parents=True, exist_ok=True)

        if meta_skill:
            filename = f"{meta_skill}__{creator}.md"
        else:
            filename = f"{creator}.md"

        (skills_dir / filename).write_text(skill_text)

    def write_summary(self, summary: RunSummary) -> None:
        """Write results.json, summary.txt, run-config.json, and update latest symlink."""
        # Write results.json — exclude bulky output_text (already in per-trial files)
        results_data = json.loads(summary.model_dump_json())
        _strip_output_text(results_data)
        results_path = self.run_dir / "results.json"
        results_path.write_text(json.dumps(results_data, indent=2))

        # Write run-config.json — records how this run was produced
        run_config = {
            "mode": summary.mode,
            "task": self._task_name,
            "timestamp": summary.timestamp,
        }
        if summary.model_results:
            run_config["models"] = [mr.model for mr in summary.model_results]
            run_config["trials"] = (
                len(summary.model_results[0].trials) if summary.model_results else 0
            )
        (self.run_dir / "run-config.json").write_text(json.dumps(run_config, indent=2))

        # Write human-readable summary.txt
        summary_path = self.run_dir / "summary.txt"
        lines = [
            "SkillEval Run Summary",
            f"Mode: {summary.mode}",
            f"Task: {self._task_name}",
            f"Timestamp: {summary.timestamp}",
            "",
        ]

        if summary.model_results:
            lines.append("Model Results:")
            for mr in sorted(summary.model_results, key=lambda r: (-r.pass_rate, r.avg_cost)):
                lines.append(
                    f"  {mr.model}: {mr.pass_rate * 100:.0f}% pass, "
                    f"${mr.avg_cost:.6f}/run, {mr.avg_latency:.2f}s avg"
                )
            lines.append("")

        if summary.matrix_results:
            lines.append("Matrix Results:")
            for mc in summary.matrix_results:
                lines.append(
                    f"  {mc.creator} -> {mc.executor}: "
                    f"{mc.result.pass_rate * 100:.0f}% pass, "
                    f"${mc.result.avg_cost:.6f}/run"
                )
            lines.append("")

        if summary.chain_results:
            lines.append("Chain Results:")
            for cc in summary.chain_results:
                lines.append(
                    f"  {cc.meta_skill_name} / {cc.creator} -> {cc.executor}: "
                    f"{cc.result.pass_rate * 100:.0f}% pass, "
                    f"${cc.result.avg_cost:.6f}/run"
                )
            lines.append("")

        if summary.recommendation:
            lines.append(f"Recommendation: {summary.recommendation}")

        summary_path.write_text("\n".join(lines))

        # Update .skilleval/latest symlink
        self._update_latest_symlink()

    def _update_latest_symlink(self) -> None:
        """Create or update the 'latest' symlink pointing to this run."""
        latest = self._skilleval_dir / "latest"
        # Use relative target so the symlink is portable
        target = self.run_dir.name
        try:
            if latest.is_symlink() or latest.exists():
                os.remove(latest)
            os.symlink(target, latest)
        except OSError:
            pass  # Symlinks may not be supported (e.g., Windows without privileges)

    async def write_trial_output_async(
        self,
        model: str,
        trial_num: int,
        output_text: str,
        diff: str | None,
        meta: dict,
    ) -> None:
        """Async wrapper for write_trial_output that runs I/O in a thread."""
        import asyncio

        await asyncio.to_thread(
            self.write_trial_output,
            model,
            trial_num,
            output_text,
            diff,
            meta,
        )

    async def write_summary_async(self, summary: RunSummary) -> None:
        """Async wrapper for write_summary that runs I/O in a thread."""
        import asyncio

        await asyncio.to_thread(self.write_summary, summary)


def _strip_output_text(data: dict) -> None:
    """Remove output_text from trial entries in a serialized RunSummary dict.

    The raw output is already stored in per-trial output.txt files, so
    keeping it in results.json doubles the file size for no benefit.
    """
    for mr in data.get("model_results", []):
        for trial in mr.get("trials", []):
            trial.pop("output_text", None)
    for mc in data.get("matrix_results", []):
        for trial in mc.get("result", {}).get("trials", []):
            trial.pop("output_text", None)
    for cc in data.get("chain_results", []):
        for trial in cc.get("result", {}).get("trials", []):
            trial.pop("output_text", None)


def load_run_history(task_path: Path) -> list[dict]:
    """Scan .skilleval/run-* directories and return metadata for each run.

    Returns a list of dicts sorted by timestamp (newest first), each containing:
    - run_dir: directory name (e.g. "run-20260227-153348")
    - mode, timestamp, models, pass_rate, recommendation
    """
    skilleval_dir = task_path / ".skilleval"
    if not skilleval_dir.is_dir():
        return []

    runs: list[dict] = []
    for run_dir in sorted(skilleval_dir.iterdir(), reverse=True):
        if not run_dir.is_dir() or not run_dir.name.startswith("run-"):
            continue

        entry: dict = {"run_dir": run_dir.name, "path": run_dir}

        # Try run-config.json first (new format), then results.json
        config_file = run_dir / "run-config.json"
        results_file = run_dir / "results.json"

        if config_file.exists():
            try:
                config = json.loads(config_file.read_text())
                entry["mode"] = config.get("mode", "?")
                entry["timestamp"] = config.get("timestamp", "")
                entry["models"] = config.get("models", [])
                entry["trials"] = config.get("trials", 0)
            except (json.JSONDecodeError, OSError):
                pass

        if results_file.exists():
            try:
                results = json.loads(results_file.read_text())
                entry.setdefault("mode", results.get("mode", "?"))
                entry.setdefault("timestamp", results.get("timestamp", ""))
                entry["recommendation"] = results.get("recommendation")

                # Compute aggregate pass rate
                model_results = results.get("model_results", [])
                if model_results:
                    entry.setdefault("models", [r["model"] for r in model_results])
                    rates = [r["pass_rate"] for r in model_results]
                    entry["avg_pass_rate"] = sum(rates) / len(rates)
                    entry["model_count"] = len(model_results)

                matrix_results = results.get("matrix_results", [])
                if matrix_results:
                    rates = [c["result"]["pass_rate"] for c in matrix_results]
                    entry["avg_pass_rate"] = sum(rates) / len(rates)
                    entry["model_count"] = len(matrix_results)

                chain_results = results.get("chain_results", [])
                if chain_results:
                    rates = [c["result"]["pass_rate"] for c in chain_results]
                    entry["avg_pass_rate"] = sum(rates) / len(rates)
                    entry["model_count"] = len(chain_results)
            except (json.JSONDecodeError, OSError):
                pass

        runs.append(entry)

    return runs
