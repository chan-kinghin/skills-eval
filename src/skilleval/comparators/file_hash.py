"""SHA-256 file hash comparator (byte-identical)."""

from __future__ import annotations

import hashlib
from pathlib import Path

from skilleval.comparators.base import FileComparator


class FileHashComparator(FileComparator):
    """Byte-identical comparison via SHA-256.

    CRLF vs LF matters -- this is a raw byte comparison.
    No markdown fence stripping (hash comparison is intentionally strict).
    """

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
