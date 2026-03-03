"""Base protocol and helpers for comparators."""

from __future__ import annotations

import abc
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


class FileComparator(abc.ABC):
    """Base class for file-based comparators using the template method pattern.

    Subclasses only need to implement ``_compare_files``.  The shared
    ``compare`` method handles file pairing and diff collection.
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
                diffs.append(f"--- {expected_file.name} vs {output_file.name} ---\n{diff}")

        if diffs:
            return False, "\n\n".join(diffs)
        return True, None

    @abc.abstractmethod
    def _compare_files(self, output_file: Path, expected_file: Path) -> tuple[bool, str]:
        """Compare a single pair of files. Return (passed, diff_text)."""
        ...


def get_file_pairs(output_dir: Path, expected_dir: Path) -> list[tuple[Path, Path]]:
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
