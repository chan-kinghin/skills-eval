"""Unordered CSV comparator (multiset of rows)."""

from __future__ import annotations

import csv
import io
from collections import Counter
from pathlib import Path

from skilleval.comparators.base import FileComparator, strip_markdown_fences


class CsvUnorderedComparator(FileComparator):
    """Compare CSV files as multisets of rows.

    Row order is irrelevant, but duplicates matter.
    Column order DOES matter.
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

        expected_counter: Counter[tuple[str, ...]] = Counter(tuple(row) for row in expected_rows)
        output_counter: Counter[tuple[str, ...]] = Counter(tuple(row) for row in output_rows)

        if expected_counter == output_counter:
            return True, ""

        missing = expected_counter - output_counter
        extra = output_counter - expected_counter

        parts: list[str] = []
        if missing:
            parts.append("Missing rows (in expected but not output):")
            for row, count in sorted(missing.items()):
                parts.append(f"  {list(row)} (x{count})")
        if extra:
            parts.append("Extra rows (in output but not expected):")
            for row, count in sorted(extra.items()):
                parts.append(f"  {list(row)} (x{count})")

        return False, "\n".join(parts)

    @staticmethod
    def _parse_csv(text: str) -> list[list[str]]:
        reader = csv.reader(io.StringIO(text))
        return list(reader)
