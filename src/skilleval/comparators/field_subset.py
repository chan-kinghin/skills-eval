"""Field subset JSON comparator (expected is a subset of output)."""

from __future__ import annotations

import json
from pathlib import Path

from skilleval.comparators.base import FileComparator, strip_markdown_fences


class FieldSubsetComparator(FileComparator):
    """Check that all fields in expected exist in output with matching values.

    Deep/recursive check for nested objects.
    Extra fields in output are OK -- this is a subset check.
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

        errors: list[str] = []
        self._check_subset(expected_obj, output_obj, path="$", errors=errors)

        if errors:
            return False, "\n".join(errors)
        return True, ""

    def _check_subset(
        self,
        expected: object,
        output: object,
        path: str,
        errors: list[str],
    ) -> None:
        if isinstance(expected, dict):
            if not isinstance(output, dict):
                errors.append(f"{path}: expected object, got {type(output).__name__}")
                return
            for key in expected:
                if key not in output:
                    errors.append(f"{path}.{key}: missing in output")
                else:
                    self._check_subset(expected[key], output[key], f"{path}.{key}", errors)

        elif isinstance(expected, list):
            if not isinstance(output, list):
                errors.append(f"{path}: expected array, got {type(output).__name__}")
                return
            if len(expected) != len(output):
                errors.append(
                    f"{path}: expected array length {len(expected)}, got {len(output)}"
                )
                return
            for i, (exp_item, out_item) in enumerate(zip(expected, output)):
                self._check_subset(exp_item, out_item, f"{path}[{i}]", errors)

        else:
            # Scalar comparison: normalize int/float per JSON RFC 8259
            exp_val = float(expected) if isinstance(expected, int) and not isinstance(expected, bool) else expected
            out_val = float(output) if isinstance(output, int) and not isinstance(output, bool) else output
            if type(exp_val) is not type(out_val) or exp_val != out_val:
                errors.append(
                    f"{path}: expected {json.dumps(expected)}, got {json.dumps(output)}"
                )
