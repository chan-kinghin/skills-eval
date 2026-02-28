"""Tests for skilleval.comparators.csv_unordered — multiset CSV comparison."""

from __future__ import annotations

from pathlib import Path

from skilleval.comparators.csv_unordered import CsvUnorderedComparator


def _setup_dirs(tmp_path: Path, output_csv: str, expected_csv: str) -> tuple[Path, Path]:
    out_dir = tmp_path / "output"
    exp_dir = tmp_path / "expected"
    out_dir.mkdir()
    exp_dir.mkdir()
    (out_dir / "data.csv").write_text(output_csv)
    (exp_dir / "data.csv").write_text(expected_csv)
    return out_dir, exp_dir


class TestCsvUnorderedComparator:
    def test_same_rows_different_order_passes(self, tmp_path: Path):
        out, exp = _setup_dirs(
            tmp_path,
            "a,b\n4,5\n1,2\n",
            "a,b\n1,2\n4,5\n",
        )
        passed, diff = CsvUnorderedComparator().compare(out, exp)
        assert passed is True
        assert diff is None

    def test_identical_csv_passes(self, tmp_path: Path):
        csv = "x,y\n1,2\n3,4\n"
        out, exp = _setup_dirs(tmp_path, csv, csv)
        passed, _ = CsvUnorderedComparator().compare(out, exp)
        assert passed is True

    def test_missing_row_fails(self, tmp_path: Path):
        out, exp = _setup_dirs(
            tmp_path,
            "a,b\n1,2\n",
            "a,b\n1,2\n3,4\n",
        )
        passed, diff = CsvUnorderedComparator().compare(out, exp)
        assert passed is False
        assert "Missing rows" in diff

    def test_extra_row_fails(self, tmp_path: Path):
        out, exp = _setup_dirs(
            tmp_path,
            "a,b\n1,2\n3,4\n5,6\n",
            "a,b\n1,2\n3,4\n",
        )
        passed, diff = CsvUnorderedComparator().compare(out, exp)
        assert passed is False
        assert "Extra rows" in diff

    def test_duplicate_rows_tracked(self, tmp_path: Path):
        out, exp = _setup_dirs(
            tmp_path,
            "a\n1\n1\n",
            "a\n1\n1\n",
        )
        passed, _ = CsvUnorderedComparator().compare(out, exp)
        assert passed is True

    def test_duplicate_count_mismatch_fails(self, tmp_path: Path):
        out, exp = _setup_dirs(
            tmp_path,
            "a\n1\n1\n1\n",
            "a\n1\n1\n",
        )
        passed, diff = CsvUnorderedComparator().compare(out, exp)
        assert passed is False
        assert "Extra rows" in diff

    def test_markdown_fences_stripped(self, tmp_path: Path):
        fenced = "```\na,b\n1,2\n```"
        plain = "a,b\n1,2\n"
        out, exp = _setup_dirs(tmp_path, fenced, plain)
        passed, _ = CsvUnorderedComparator().compare(out, exp)
        assert passed is True
