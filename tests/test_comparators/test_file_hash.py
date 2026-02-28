"""Tests for skilleval.comparators.file_hash — SHA-256 byte comparison."""

from __future__ import annotations

from pathlib import Path

from skilleval.comparators.file_hash import FileHashComparator


def _setup_dirs(
    tmp_path: Path, output_bytes: bytes, expected_bytes: bytes,
) -> tuple[Path, Path]:
    out_dir = tmp_path / "output"
    exp_dir = tmp_path / "expected"
    out_dir.mkdir()
    exp_dir.mkdir()
    (out_dir / "data.bin").write_bytes(output_bytes)
    (exp_dir / "data.bin").write_bytes(expected_bytes)
    return out_dir, exp_dir


class TestFileHashComparator:
    def test_identical_files_pass(self, tmp_path: Path):
        content = b"hello world"
        out, exp = _setup_dirs(tmp_path, content, content)
        passed, diff = FileHashComparator().compare(out, exp)
        assert passed is True
        assert diff is None

    def test_different_content_fails(self, tmp_path: Path):
        out, exp = _setup_dirs(tmp_path, b"hello", b"world")
        passed, diff = FileHashComparator().compare(out, exp)
        assert passed is False
        assert "Hash mismatch" in diff

    def test_diff_includes_hashes(self, tmp_path: Path):
        out, exp = _setup_dirs(tmp_path, b"aaa", b"bbb")
        passed, diff = FileHashComparator().compare(out, exp)
        assert passed is False
        # SHA-256 hashes are 64 hex chars
        lines = diff.split("\n")
        assert any(len(line.strip().split()[-1]) == 64 for line in lines if ":" in line)

    def test_crlf_vs_lf_matters(self, tmp_path: Path):
        """File hash is strict — line ending differences cause failure."""
        out, exp = _setup_dirs(tmp_path, b"line\r\n", b"line\n")
        passed, _ = FileHashComparator().compare(out, exp)
        assert passed is False

    def test_empty_files_pass(self, tmp_path: Path):
        out, exp = _setup_dirs(tmp_path, b"", b"")
        passed, _ = FileHashComparator().compare(out, exp)
        assert passed is True

    def test_binary_content(self, tmp_path: Path):
        data = bytes(range(256))
        out, exp = _setup_dirs(tmp_path, data, data)
        passed, _ = FileHashComparator().compare(out, exp)
        assert passed is True
