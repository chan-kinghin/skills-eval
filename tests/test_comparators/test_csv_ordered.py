"""Tests for skilleval.comparators.csv_ordered — row-by-row CSV comparison."""

from __future__ import annotations

from pathlib import Path

from skilleval.comparators.csv_ordered import CsvOrderedComparator


def _setup_dirs(tmp_path: Path, output_csv: str, expected_csv: str) -> tuple[Path, Path]:
    out_dir = tmp_path / "output"
    exp_dir = tmp_path / "expected"
    out_dir.mkdir()
    exp_dir.mkdir()
    (out_dir / "data.csv").write_text(output_csv)
    (exp_dir / "data.csv").write_text(expected_csv)
    return out_dir, exp_dir


class TestCsvOrderedComparator:
    def test_identical_csv_passes(self, tmp_path: Path):
        csv = "a,b,c\n1,2,3\n4,5,6\n"
        out, exp = _setup_dirs(tmp_path, csv, csv)
        passed, diff = CsvOrderedComparator().compare(out, exp)
        assert passed is True
        assert diff is None

    def test_different_row_order_fails(self, tmp_path: Path):
        out, exp = _setup_dirs(
            tmp_path,
            "a,b\n4,5\n1,2\n",
            "a,b\n1,2\n4,5\n",
        )
        passed, diff = CsvOrderedComparator().compare(out, exp)
        assert passed is False
        assert "Row" in diff

    def test_row_count_mismatch(self, tmp_path: Path):
        out, exp = _setup_dirs(
            tmp_path,
            "a,b\n1,2\n",
            "a,b\n1,2\n3,4\n",
        )
        passed, diff = CsvOrderedComparator().compare(out, exp)
        assert passed is False
        assert "Row count mismatch" in diff

    def test_cell_value_difference(self, tmp_path: Path):
        out, exp = _setup_dirs(
            tmp_path,
            "a,b\n1,WRONG\n",
            "a,b\n1,2\n",
        )
        passed, diff = CsvOrderedComparator().compare(out, exp)
        assert passed is False
        assert "Row" in diff
        assert "WRONG" in diff

    def test_single_row_csv(self, tmp_path: Path):
        csv = "header\nvalue\n"
        out, exp = _setup_dirs(tmp_path, csv, csv)
        passed, _ = CsvOrderedComparator().compare(out, exp)
        assert passed is True

    def test_markdown_fences_stripped(self, tmp_path: Path):
        fenced = "```csv\na,b\n1,2\n```"
        plain = "a,b\n1,2\n"
        out, exp = _setup_dirs(tmp_path, fenced, plain)
        passed, _ = CsvOrderedComparator().compare(out, exp)
        assert passed is True
