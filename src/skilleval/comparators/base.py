"""Base protocol and helpers for comparators."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Protocol


class Comparator(Protocol):
    """Protocol that all comparators must implement."""

    def compare(self, output_dir: Path, expected_dir: Path) -> tuple[bool, str | None]:
        """Compare output against expected.

        Returns (passed, diff_text). diff_text is None on pass.
        """
        ...


def get_file_pairs(
    output_dir: Path, expected_dir: Path
) -> list[tuple[Path, Path]]:
    """Match files from output_dir to expected_dir by filename.

    Returns list of (output_file, expected_file) pairs.
    Raises ValueError if expected files are missing from output.
    """
    expected_files = {f.name: f for f in expected_dir.iterdir() if f.is_file()}
    output_files = {f.name: f for f in output_dir.iterdir() if f.is_file()}

    missing = set(expected_files) - set(output_files)
    if missing:
        raise ValueError(f"Missing output files: {', '.join(sorted(missing))}")

    pairs = []
    for name in sorted(expected_files):
        pairs.append((output_files[name], expected_files[name]))
    return pairs


_FENCE_RE = re.compile(
    r"^\s*```[a-zA-Z]*\s*\n(.*?)\n\s*```\s*$",
    re.DOTALL,
)

# Reasoning tags used by various models:
# MiniMax: <think>...</think>
# DeepSeek-R1: <think>...</think>
# Some models: <reasoning>...</reasoning>
_THINK_RE = re.compile(
    r"<(?:think|thinking|reasoning)>.*?</(?:think|thinking|reasoning)>",
    re.DOTALL,
)


def strip_markdown_fences(text: str) -> str:
    """Strip common markdown code fences (```json, ```) from text.

    LLMs often wrap output in fences; remove them before comparison.
    """
    m = _FENCE_RE.match(text.strip())
    if m:
        return m.group(1)
    return text


def strip_reasoning_tags(text: str) -> str:
    """Strip <think>/<reasoning> tags that reasoning models emit.

    Models like MiniMax, DeepSeek-R1 wrap chain-of-thought in tags.
    The actual output follows after the closing tag.
    """
    cleaned = _THINK_RE.sub("", text).strip()
    return cleaned if cleaned else text
