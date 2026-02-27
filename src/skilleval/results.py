"""Result storage for SkillEval runs."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from skilleval.models import RunSummary


class ResultWriter:
    """Writes trial outputs, generated skills, and summaries to disk."""

    def __init__(self, task_path: Path, mode: str) -> None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.run_dir = task_path / ".skilleval" / f"run-{timestamp}"
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.mode = mode

    def write_trial_output(
        self,
        model: str,
        trial_num: int,
        output_text: str,
        diff: str | None,
        meta: dict,
    ) -> None:
        """Save trial output, diff, and metadata."""
        trial_dir = self.run_dir / "trials" / model / f"trial-{trial_num}"
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
        """Write results.json and summary.txt."""
        results_path = self.run_dir / "results.json"
        results_path.write_text(summary.model_dump_json(indent=2))

        summary_path = self.run_dir / "summary.txt"
        lines = [
            f"SkillEval Run Summary",
            f"Mode: {summary.mode}",
            f"Task: {summary.task_path}",
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
