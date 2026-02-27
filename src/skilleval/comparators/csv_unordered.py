"""Unordered CSV comparator (multiset of rows)."""

from __future__ import annotations

import csv
import io
from collections import Counter
from pathlib import Path

from skilleval.comparators.base import get_file_pairs, strip_markdown_fences


class CsvUnorderedComparator:
    """Compare CSV files as multisets of rows.

    Row order is irrelevant, but duplicates matter.
    Column order DOES matter.
    """

    def compare(self, output_dir: Path, expected_dir: Path) -> tuple[bool, str | None]:
        try:
            pairs = get_file_pairs(output_dir, expected_dir)
        except ValueError as e:
            return False, str(e)

        diffs: list[str] = []
        for output_file, expected_file in pairs:
            passed, diff = self._compare_files(output_file, expected_file)
            if not passed:
                diffs.append(f"--- {expected_file.name} vs {output_file.name} ---\n{diff}")

        if diffs:
            return False, "\n\n".join(diffs)
        return True, None

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

        expected_counter: Counter[tuple[str, ...]] = Counter(
            tuple(row) for row in expected_rows
        )
        output_counter: Counter[tuple[str, ...]] = Counter(
            tuple(row) for row in output_rows
        )

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
