"""Text-contains comparator (substring or regex match)."""

from __future__ import annotations

import re
from pathlib import Path

from skilleval.comparators.base import FileComparator, strip_markdown_fences


class TextContainsComparator(FileComparator):
    """Check that expected text appears in output.

    If the expected file content starts with ``re:`` the remainder is
    treated as a regex pattern and matched against the full output.
    Otherwise a plain substring check is performed.
    """

    def _compare_files(self, output_file: Path, expected_file: Path) -> tuple[bool, str]:
        try:
            expected_text = expected_file.read_text(encoding="utf-8").strip()
        except OSError as e:
            return False, f"Cannot read expected file: {e}"

        try:
            output_text = output_file.read_text(encoding="utf-8")
        except OSError as e:
            return False, f"Cannot read output file: {e}"

        output_text = strip_markdown_fences(output_text).strip()

        if expected_text.startswith("re:"):
            pattern = expected_text[3:]
            if re.search(pattern, output_text):
                return True, ""
            return False, f"Regex pattern not found in output: {pattern}"

        if expected_text in output_text:
            return True, ""

        return False, (
            f"Expected substring not found in output.\n"
            f"  expected: {expected_text[:200]}\n"
            f"  output:   {output_text[:200]}"
        )
