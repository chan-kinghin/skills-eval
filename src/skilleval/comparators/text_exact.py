"""Exact text comparator with whitespace normalization."""

from __future__ import annotations

import difflib
import re
from pathlib import Path

from skilleval.comparators.base import FileComparator, strip_markdown_fences


class TextExactComparator(FileComparator):
    """Normalized plain-text comparison.

    Strips leading/trailing whitespace and collapses internal whitespace
    runs to single spaces before comparing.
    """

    def _compare_files(self, output_file: Path, expected_file: Path) -> tuple[bool, str]:
        try:
            expected_text = expected_file.read_text(encoding="utf-8")
        except OSError as e:
            return False, f"Cannot read expected file: {e}"

        try:
            output_text = output_file.read_text(encoding="utf-8")
        except OSError as e:
            return False, f"Cannot read output file: {e}"

        output_text = strip_markdown_fences(output_text)

        expected_norm = self._normalize(expected_text)
        output_norm = self._normalize(output_text)

        if expected_norm == output_norm:
            return True, ""

        diff_lines = list(difflib.unified_diff(
            expected_norm.splitlines(keepends=True),
            output_norm.splitlines(keepends=True),
            fromfile="expected",
            tofile="output",
        ))
        return False, "".join(diff_lines)

    @staticmethod
    def _normalize(text: str) -> str:
        """Strip and collapse whitespace."""
        return re.sub(r"\s+", " ", text.strip())
