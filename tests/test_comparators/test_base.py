"""Tests for skilleval.comparators.base — helpers and utilities."""

from __future__ import annotations

from pathlib import Path

import pytest

from skilleval.comparators.base import (
    get_file_pairs,
    strip_markdown_fences,
    strip_reasoning_tags,
)


# ── strip_markdown_fences ────────────────────────────────────────────────


class TestStripMarkdownFences:
    def test_json_fence(self):
        text = "```json\n{\"a\": 1}\n```"
        assert strip_markdown_fences(text) == '{"a": 1}'

    def test_plain_fence(self):
        text = "```\nhello world\n```"
        assert strip_markdown_fences(text) == "hello world"

    def test_no_fence(self):
        text = '{"a": 1}'
        assert strip_markdown_fences(text) == '{"a": 1}'

    def test_empty_string(self):
        assert strip_markdown_fences("") == ""

    def test_csv_fence(self):
        text = "```csv\na,b,c\n1,2,3\n```"
        assert strip_markdown_fences(text) == "a,b,c\n1,2,3"

    def test_multiline_content(self):
        text = "```json\n{\n  \"a\": 1,\n  \"b\": 2\n}\n```"
        result = strip_markdown_fences(text)
        assert '"a": 1' in result
        assert '"b": 2' in result


# ── strip_reasoning_tags ─────────────────────────────────────────────────


class TestStripReasoningTags:
    def test_think_tags(self):
        text = "<think>reasoning here</think>\nfinal answer"
        assert strip_reasoning_tags(text) == "final answer"

    def test_reasoning_tags(self):
        text = "<reasoning>step by step</reasoning>\nresult"
        assert strip_reasoning_tags(text) == "result"

    def test_thinking_tags(self):
        text = "<thinking>hmm...</thinking>\noutput"
        assert strip_reasoning_tags(text) == "output"

    def test_no_tags(self):
        text = "just plain text"
        assert strip_reasoning_tags(text) == "just plain text"

    def test_only_tags_returns_original(self):
        """If stripping tags leaves nothing, return original."""
        text = "<think>everything is reasoning</think>"
        result = strip_reasoning_tags(text)
        # The function returns original when cleaned is empty
        assert result == text

    def test_multiline_reasoning(self):
        text = "<think>\nline 1\nline 2\n</think>\nanswer"
        assert strip_reasoning_tags(text) == "answer"


# ── get_file_pairs ───────────────────────────────────────────────────────


class TestGetFilePairs:
    def test_matching_files(self, tmp_path: Path):
        out_dir = tmp_path / "output"
        exp_dir = tmp_path / "expected"
        out_dir.mkdir()
        exp_dir.mkdir()

        (out_dir / "result.json").write_text("{}")
        (exp_dir / "result.json").write_text("{}")

        pairs = get_file_pairs(out_dir, exp_dir)
        assert len(pairs) == 1
        assert pairs[0][0].name == "result.json"
        assert pairs[0][1].name == "result.json"

    def test_missing_output_file_raises(self, tmp_path: Path):
        out_dir = tmp_path / "output"
        exp_dir = tmp_path / "expected"
        out_dir.mkdir()
        exp_dir.mkdir()

        (exp_dir / "result.json").write_text("{}")
        # No matching file in output

        with pytest.raises(ValueError, match="Missing output files"):
            get_file_pairs(out_dir, exp_dir)

    def test_extra_output_files_ignored(self, tmp_path: Path):
        out_dir = tmp_path / "output"
        exp_dir = tmp_path / "expected"
        out_dir.mkdir()
        exp_dir.mkdir()

        (out_dir / "result.json").write_text("{}")
        (out_dir / "bonus.json").write_text("{}")
        (exp_dir / "result.json").write_text("{}")

        pairs = get_file_pairs(out_dir, exp_dir)
        assert len(pairs) == 1  # bonus.json ignored

    def test_multiple_pairs_sorted(self, tmp_path: Path):
        out_dir = tmp_path / "output"
        exp_dir = tmp_path / "expected"
        out_dir.mkdir()
        exp_dir.mkdir()

        for name in ["b.json", "a.json"]:
            (out_dir / name).write_text("{}")
            (exp_dir / name).write_text("{}")

        pairs = get_file_pairs(out_dir, exp_dir)
        assert len(pairs) == 2
        assert pairs[0][0].name == "a.json"
        assert pairs[1][0].name == "b.json"
