"""Tests for skilleval.documents — text extraction and formatting."""

from __future__ import annotations

from pathlib import Path

from skilleval.documents import format_input_files, input_descriptions


# ── format_input_files ───────────────────────────────────────────────────


class TestFormatInputFiles:
    def test_single_file(self, tmp_path: Path):
        f = tmp_path / "data.json"
        f.write_text('{"name": "Alice"}')
        result = format_input_files([f])
        assert "--- File: data.json ---" in result
        assert '{"name": "Alice"}' in result
        assert "--- End File ---" in result

    def test_multiple_files(self, tmp_path: Path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("first")
        f2.write_text("second")
        result = format_input_files([f1, f2])
        assert "--- File: a.txt ---" in result
        assert "--- File: b.txt ---" in result
        assert "first" in result
        assert "second" in result

    def test_empty_file(self, tmp_path: Path):
        f = tmp_path / "empty.txt"
        f.write_text("")
        result = format_input_files([f])
        assert "--- File: empty.txt ---" in result


# ── input_descriptions ───────────────────────────────────────────────────


class TestInputDescriptions:
    def test_type_labels(self, tmp_path: Path):
        for name, label in [
            ("data.json", "JSON"),
            ("data.csv", "CSV"),
            ("readme.txt", "text"),
        ]:
            f = tmp_path / name
            f.write_text("content here")
            desc = input_descriptions([f])
            assert label in desc

    def test_truncation_at_max_chars(self, tmp_path: Path):
        f = tmp_path / "big.txt"
        f.write_text("x" * 500)
        desc = input_descriptions([f], max_chars=50)
        assert "..." in desc

    def test_no_truncation_for_short_content(self, tmp_path: Path):
        f = tmp_path / "small.txt"
        f.write_text("short")
        desc = input_descriptions([f], max_chars=200)
        assert "..." not in desc

    def test_preview_replaces_newlines(self, tmp_path: Path):
        f = tmp_path / "multi.txt"
        f.write_text("line1\nline2\nline3")
        desc = input_descriptions([f])
        # newlines should be replaced with spaces in preview
        assert "line1 line2" in desc
