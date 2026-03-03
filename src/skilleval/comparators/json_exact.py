"""Exact JSON comparator with canonical normalization."""

from __future__ import annotations

import difflib
import json
from pathlib import Path

from skilleval.comparators.base import FileComparator, strip_markdown_fences


def _normalize_numbers(obj: object) -> object:
    """Recursively convert all numeric values to float for consistent comparison.

    This ensures 150 == 150.0, which is correct per JSON RFC 8259
    (JSON makes no distinction between integer and float).
    """
    if isinstance(obj, dict):
        return {k: _normalize_numbers(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_normalize_numbers(item) for item in obj]
    elif isinstance(obj, int) and not isinstance(obj, bool):
        return float(obj)
    return obj


def _canonical(obj: object) -> str:
    """Serialize to canonical JSON (sorted keys, consistent formatting).

    Normalizes int/float so that 150 and 150.0 compare as equal.
    """
    normalized = _normalize_numbers(obj)
    return json.dumps(normalized, sort_keys=True, indent=2, ensure_ascii=False)


class JsonExactComparator(FileComparator):
    """Deep-equality JSON comparison.

    Numbers are normalized: 1 == 1.0 (per JSON RFC 8259).
    Null != missing key. Extra keys in output = fail (must be exact match).
    Whitespace/formatting differences are ignored.
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

        try:
            expected_obj = json.loads(expected_text)
        except json.JSONDecodeError as e:
            return False, f"Expected file is not valid JSON: {e}"

        try:
            output_obj = json.loads(output_text)
        except json.JSONDecodeError as e:
            return False, f"Output file is not valid JSON: {e}"

        expected_canonical = _canonical(expected_obj)
        output_canonical = _canonical(output_obj)

        if expected_canonical == output_canonical:
            return True, ""

        diff_lines = list(difflib.unified_diff(
            expected_canonical.splitlines(keepends=True),
            output_canonical.splitlines(keepends=True),
            fromfile="expected",
            tofile="output",
        ))
        return False, "".join(diff_lines)
