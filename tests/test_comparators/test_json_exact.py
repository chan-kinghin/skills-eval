"""Tests for skilleval.comparators.json_exact — deep-equality JSON comparison."""

from __future__ import annotations

import json
from pathlib import Path

from skilleval.comparators.json_exact import JsonExactComparator, _canonical, _normalize_numbers


# ── _normalize_numbers ───────────────────────────────────────────────────


class TestNormalizeNumbers:
    def test_int_to_float(self):
        assert _normalize_numbers(150) == 150.0

    def test_float_unchanged(self):
        assert _normalize_numbers(3.14) == 3.14

    def test_bool_not_converted(self):
        """Booleans are a subclass of int but should NOT be converted."""
        assert _normalize_numbers(True) is True
        assert _normalize_numbers(False) is False

    def test_nested_dict(self):
        obj = {"a": 1, "b": {"c": 2}}
        result = _normalize_numbers(obj)
        assert result == {"a": 1.0, "b": {"c": 2.0}}

    def test_list(self):
        assert _normalize_numbers([1, 2, 3]) == [1.0, 2.0, 3.0]

    def test_string_unchanged(self):
        assert _normalize_numbers("hello") == "hello"

    def test_none_unchanged(self):
        assert _normalize_numbers(None) is None


# ── _canonical ───────────────────────────────────────────────────────────


class TestCanonical:
    def test_sorted_keys(self):
        result = _canonical({"b": 1, "a": 2})
        lines = result.strip().split("\n")
        assert '"a"' in lines[1]  # "a" comes before "b"

    def test_int_float_equivalence(self):
        assert _canonical({"x": 150}) == _canonical({"x": 150.0})


# ── JsonExactComparator ──────────────────────────────────────────────────


def _setup_dirs(tmp_path: Path, output_content: str, expected_content: str) -> tuple[Path, Path]:
    out_dir = tmp_path / "output"
    exp_dir = tmp_path / "expected"
    out_dir.mkdir()
    exp_dir.mkdir()
    (out_dir / "result.json").write_text(output_content)
    (exp_dir / "result.json").write_text(expected_content)
    return out_dir, exp_dir


class TestJsonExactComparator:
    def test_identical_json_passes(self, tmp_path: Path):
        out, exp = _setup_dirs(tmp_path, '{"a": 1}', '{"a": 1}')
        comp = JsonExactComparator()
        passed, diff = comp.compare(out, exp)
        assert passed is True
        assert diff is None

    def test_different_key_order_passes(self, tmp_path: Path):
        out, exp = _setup_dirs(
            tmp_path,
            '{"b": 2, "a": 1}',
            '{"a": 1, "b": 2}',
        )
        passed, diff = JsonExactComparator().compare(out, exp)
        assert passed is True

    def test_int_float_equivalence(self, tmp_path: Path):
        """150 == 150.0 per JSON RFC 8259."""
        out, exp = _setup_dirs(tmp_path, '{"x": 150}', '{"x": 150.0}')
        passed, diff = JsonExactComparator().compare(out, exp)
        assert passed is True

    def test_missing_key_fails(self, tmp_path: Path):
        out, exp = _setup_dirs(tmp_path, '{"a": 1}', '{"a": 1, "b": 2}')
        passed, diff = JsonExactComparator().compare(out, exp)
        assert passed is False
        assert diff is not None

    def test_extra_key_fails(self, tmp_path: Path):
        out, exp = _setup_dirs(tmp_path, '{"a": 1, "b": 2}', '{"a": 1}')
        passed, diff = JsonExactComparator().compare(out, exp)
        assert passed is False

    def test_markdown_fenced_output_passes(self, tmp_path: Path):
        fenced = '```json\n{"a": 1}\n```'
        out, exp = _setup_dirs(tmp_path, fenced, '{"a": 1}')
        passed, diff = JsonExactComparator().compare(out, exp)
        assert passed is True

    def test_invalid_json_in_output(self, tmp_path: Path):
        out, exp = _setup_dirs(tmp_path, "not json", '{"a": 1}')
        passed, diff = JsonExactComparator().compare(out, exp)
        assert passed is False
        assert "not valid JSON" in diff

    def test_invalid_json_in_expected(self, tmp_path: Path):
        out, exp = _setup_dirs(tmp_path, '{"a": 1}', "not json either")
        passed, diff = JsonExactComparator().compare(out, exp)
        assert passed is False
        assert "not valid JSON" in diff

    def test_diff_contains_unified_format(self, tmp_path: Path):
        out, exp = _setup_dirs(
            tmp_path,
            '{"a": "wrong"}',
            '{"a": "right"}',
        )
        passed, diff = JsonExactComparator().compare(out, exp)
        assert passed is False
        assert "---" in diff  # unified diff header

    def test_nested_objects(self, tmp_path: Path):
        obj = {"outer": {"inner": [1, 2, 3]}}
        out, exp = _setup_dirs(
            tmp_path,
            json.dumps(obj),
            json.dumps(obj),
        )
        passed, _ = JsonExactComparator().compare(out, exp)
        assert passed is True
