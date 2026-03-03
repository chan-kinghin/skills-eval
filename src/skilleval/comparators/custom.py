"""Custom script comparator (user-provided validation script)."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from skilleval.comparators.base import get_file_pairs

logger = logging.getLogger(__name__)


class CustomComparator:
    """Run a user-provided script for comparison.

    The script receives two arguments: expected_file output_file
    Exit code 0 = pass, non-zero = fail.
    Stdout is captured as diff text on failure.
    """

    def __init__(self, *, custom_script: str, task_dir: Path | None = None) -> None:
        self.script = custom_script
        self.task_dir = task_dir

    def compare(self, output_dir: Path, expected_dir: Path) -> tuple[bool, str | None]:
        script_path = Path(self.script)

        # Resolve relative paths against task_dir (if provided) or cwd
        if not script_path.is_absolute():
            base = self.task_dir if self.task_dir is not None else Path.cwd()
            script_path = (base / script_path).resolve()
        else:
            script_path = script_path.resolve()

        # Warn if the resolved path escapes via '..' traversal
        sandbox = (self.task_dir if self.task_dir is not None else Path.cwd()).resolve()
        try:
            script_path.relative_to(sandbox)
        except ValueError:
            logger.warning(
                "Custom script path '%s' is outside the sandbox directory '%s'. "
                "Proceeding anyway since the user owns this system.",
                script_path,
                sandbox,
            )

        if not script_path.exists():
            return False, f"Custom script not found: {self.script}"

        try:
            pairs = get_file_pairs(output_dir, expected_dir)
        except ValueError as e:
            return False, str(e)

        diffs: list[str] = []
        for output_file, expected_file in pairs:
            passed, diff = self._run_script(script_path, output_file, expected_file)
            if not passed:
                diffs.append(f"--- {expected_file.name} vs {output_file.name} ---\n{diff}")

        if diffs:
            return False, "\n\n".join(diffs)
        return True, None

    def _run_script(self, script: Path, output_file: Path, expected_file: Path) -> tuple[bool, str]:
        try:
            result = subprocess.run(
                [str(script), str(expected_file), str(output_file)],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            return False, "Custom script timed out (30s limit)"
        except OSError as e:
            return False, f"Failed to run custom script: {e}"

        if result.returncode == 0:
            return True, ""

        output = result.stdout.strip()
        if not output:
            output = f"Script exited with code {result.returncode}"
            stderr = result.stderr.strip()
            if stderr:
                output += f"\nstderr: {stderr}"

        return False, output
