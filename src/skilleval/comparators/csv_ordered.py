"""Ordered CSV comparator (exact row-by-row match)."""

from __future__ import annotations

import csv
import io
from pathlib import Path

from skilleval.comparators.base import FileComparator, strip_markdown_fences


class CsvOrderedComparator(FileComparator):
    """Compare CSV files row by row in order.

    Column order matters, row order matters.
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

        expected_rows = self._parse_csv(expected_text)
        output_rows = self._parse_csv(output_text)

        if len(expected_rows) != len(output_rows):
            return False, (
                f"Row count mismatch: expected {len(expected_rows)}, got {len(output_rows)}"
            )

        for i, (exp_row, out_row) in enumerate(zip(expected_rows, output_rows)):
            if exp_row != out_row:
                return False, (f"Row {i} differs:\n  expected: {exp_row}\n  got:      {out_row}")

        return True, ""

    @staticmethod
    def _parse_csv(text: str) -> list[list[str]]:
        reader = csv.reader(io.StringIO(text))
        return list(reader)
