"""SHA-256 file hash comparator (byte-identical)."""

from __future__ import annotations

import hashlib
from pathlib import Path

from skilleval.comparators.base import get_file_pairs


class FileHashComparator:
    """Byte-identical comparison via SHA-256.

    CRLF vs LF matters -- this is a raw byte comparison.
    No markdown fence stripping (hash comparison is intentionally strict).
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
                diffs.append(diff)

        if diffs:
            return False, "\n\n".join(diffs)
        return True, None

    def _compare_files(self, output_file: Path, expected_file: Path) -> tuple[bool, str]:
        try:
            expected_hash = self._sha256(expected_file)
        except OSError as e:
            return False, f"Cannot read expected file: {e}"

        try:
            output_hash = self._sha256(output_file)
        except OSError as e:
            return False, f"Cannot read output file: {e}"

        if expected_hash == output_hash:
            return True, ""

        return False, (
            f"Hash mismatch for {expected_file.name}:\n"
            f"  expected: {expected_hash}\n"
            f"  got:      {output_hash}"
        )

    @staticmethod
    def _sha256(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
