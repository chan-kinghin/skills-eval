"""Tests for skilleval.comparators.field_subset — expected ⊆ output."""

from __future__ import annotations

import json
from pathlib import Path

from skilleval.comparators.field_subset import FieldSubsetComparator


def _setup_dirs(tmp_path: Path, output_json: str, expected_json: str) -> tuple[Path, Path]:
    out_dir = tmp_path / "output"
    exp_dir = tmp_path / "expected"
    out_dir.mkdir()
    exp_dir.mkdir()
    (out_dir / "result.json").write_text(output_json)
    (exp_dir / "result.json").write_text(expected_json)
    return out_dir, exp_dir


class TestFieldSubsetComparator:
    def test_superset_passes(self, tmp_path: Path):
        """Output has more fields than expected — OK for subset check."""
        out, exp = _setup_dirs(
            tmp_path,
            '{"a": 1, "b": 2, "c": 3}',
            '{"a": 1, "b": 2}',
        )
        passed, diff = FieldSubsetComparator().compare(out, exp)
        assert passed is True
        assert diff is None

    def test_exact_match_passes(self, tmp_path: Path):
        obj = '{"a": 1, "b": 2}'
        out, exp = _setup_dirs(tmp_path, obj, obj)
        passed, _ = FieldSubsetComparator().compare(out, exp)
        assert passed is True

    def test_missing_field_fails(self, tmp_path: Path):
        out, exp = _setup_dirs(
            tmp_path,
            '{"a": 1}',
            '{"a": 1, "b": 2}',
        )
        passed, diff = FieldSubsetComparator().compare(out, exp)
        assert passed is False
        assert "$.b" in diff
        assert "missing" in diff

    def test_type_mismatch_fails(self, tmp_path: Path):
        out, exp = _setup_dirs(
            tmp_path,
            '{"a": "1"}',
            '{"a": 1}',
        )
        passed, diff = FieldSubsetComparator().compare(out, exp)
        assert passed is False
        assert "$.a" in diff

    def test_nested_subset(self, tmp_path: Path):
        output = {"outer": {"a": 1, "b": 2, "extra": 99}}
        expected = {"outer": {"a": 1, "b": 2}}
        out, exp = _setup_dirs(
            tmp_path,
            json.dumps(output),
            json.dumps(expected),
        )
        passed, _ = FieldSubsetComparator().compare(out, exp)
        assert passed is True

    def test_nested_missing_field_fails(self, tmp_path: Path):
        output = {"outer": {"a": 1}}
        expected = {"outer": {"a": 1, "b": 2}}
        out, exp = _setup_dirs(
            tmp_path,
            json.dumps(output),
            json.dumps(expected),
        )
        passed, diff = FieldSubsetComparator().compare(out, exp)
        assert passed is False
        assert "$.outer.b" in diff

    def test_array_subset(self, tmp_path: Path):
        output = {"items": [{"id": 1, "name": "A", "extra": True}]}
        expected = {"items": [{"id": 1, "name": "A"}]}
        out, exp = _setup_dirs(
            tmp_path,
            json.dumps(output),
            json.dumps(expected),
        )
        passed, _ = FieldSubsetComparator().compare(out, exp)
        assert passed is True

    def test_array_length_mismatch_fails(self, tmp_path: Path):
        output = {"items": [1]}
        expected = {"items": [1, 2]}
        out, exp = _setup_dirs(
            tmp_path,
            json.dumps(output),
            json.dumps(expected),
        )
        passed, diff = FieldSubsetComparator().compare(out, exp)
        assert passed is False
        assert "array length" in diff

    def test_markdown_fences_stripped(self, tmp_path: Path):
        fenced = '```json\n{"a": 1, "b": 2}\n```'
        out, exp = _setup_dirs(tmp_path, fenced, '{"a": 1}')
        passed, _ = FieldSubsetComparator().compare(out, exp)
        assert passed is True

    def test_expected_type_mismatch_object_vs_array(self, tmp_path: Path):
        out, exp = _setup_dirs(tmp_path, '["a"]', '{"a": 1}')
        passed, diff = FieldSubsetComparator().compare(out, exp)
        assert passed is False
        assert "expected object" in diff
