"""Skill parsing utilities for extracting core prompt logic and loading tests.

This module focuses on:
- Parsing a Claude Code skill markdown file and extracting its core logic
  while stripping tool-use scaffolding and bash/shell code blocks.
- Loading structured test cases for SkillsEval runs.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import yaml

from skilleval.linter import (
    Heading,
    collect_headings,
    extract_frontmatter,
    find_skill_file,
)
from skilleval.models import TaskConfig, TaskFolder


@dataclass
class SkillPrompt:
    """Parsed representation of a Claude Code skill.

    - `full_text` is the skill body (frontmatter removed)
    - `core_prompt` is the body with tool scaffolding removed
    """

    name: str
    description: str
    full_text: str
    core_prompt: str
    phases: list[str]
    source_path: Path


def parse_skill(skill_dir: Path) -> SkillPrompt:
    """Parse a skill directory and extract its core prompt logic.

    Behavior:
    - Finds `skill.md` or `SKILL.md`
    - Extracts frontmatter (name/description)
    - Builds `full_text` from the body (frontmatter removed)
    - Builds `core_prompt` by stripping tool scaffolding and bash/shell blocks
    - Extracts phase names from headings (e.g., "## Phase 1 — Name")
    """

    skill_file = find_skill_file(skill_dir)
    if skill_file is None:
        raise FileNotFoundError("Skill file not found (skill.md or SKILL.md)")

    text = skill_file.read_text(encoding="utf-8")
    fm, _fm_end, body, body_start = extract_frontmatter(text)

    name = ""
    description = ""
    if isinstance(fm, dict):
        name = str(fm.get("name") or "")
        description = str(fm.get("description") or "")

    full_text = body
    core_prompt = _strip_tool_scaffolding(body)

    # Extract phases from headings in the body
    phases = _extract_phase_names(collect_headings(body, base_line=body_start))

    return SkillPrompt(
        name=name,
        description=description,
        full_text=full_text,
        core_prompt=core_prompt,
        phases=phases,
        source_path=skill_file,
    )


def load_test_cases(test_dir: Path) -> list[TaskFolder]:
    """Load test cases from a directory.

    Structure:
    test_dir/
      config.yaml           # shared TaskConfig
      case-1/
        input/
        expected/
      case-2/
        input/
        expected/
    """

    test_dir = Path(test_dir)
    config_path = test_dir / "config.yaml"
    raw_cfg: dict | None = None
    if config_path.exists():
        raw_cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if not isinstance(raw_cfg, dict):
            raw_cfg = {}
    else:
        raw_cfg = {}

    shared_config = TaskConfig(**raw_cfg)

    cases: list[TaskFolder] = []
    for sub in sorted(p for p in test_dir.iterdir() if p.is_dir()):
        input_dir = sub / "input"
        expected_dir = sub / "expected"
        if not input_dir.exists() or not expected_dir.exists():
            continue

        input_files = sorted([p for p in input_dir.rglob("*") if p.is_file()])
        expected_files = sorted([p for p in expected_dir.rglob("*") if p.is_file()])
        if not input_files or not expected_files:
            # Skip empty cases to keep behavior predictable
            continue

        case = TaskFolder(
            path=sub.resolve(),
            input_files=input_files,
            expected_files=expected_files,
            config=shared_config.model_copy(),
        )
        cases.append(case)

    return cases


def _strip_tool_scaffolding(body: str) -> str:
    """Remove tool-use scaffolding while keeping core reasoning.

    Rules:
    - Remove code blocks tagged as bash/sh/shell (keep others, especially python)
    - Remove single lines that primarily instruct CLI/tool usage, e.g.:
      "Run this command...", "Execute ...", "Use the Bash tool", etc.
    - Remove lines that enumerate tools like "Tools: Bash, Read, Write, Edit"
    """

    out_lines: list[str] = []
    in_code = False
    skip_block = False

    fence_re = re.compile(r"^```(\w+)?\s*$")

    for raw in body.splitlines():
        line = raw.rstrip("\n")
        m = fence_re.match(line.strip())
        if m:
            if not in_code:
                in_code = True
                lang = (m.group(1) or "").lower()
                skip_block = lang in {"bash", "sh", "shell"}
                # Only keep the fence if we are not skipping this block
                if not skip_block:
                    out_lines.append(line)
            else:
                # Closing fence
                if not skip_block:
                    out_lines.append(line)
                in_code = False
                skip_block = False
            continue

        if in_code:
            if not skip_block:
                out_lines.append(raw)
            continue

        # Outside code blocks: apply line-level filters
        if _is_scaffolding_line(line):
            continue

        out_lines.append(line)

    return "\n".join(out_lines).strip()


def _is_scaffolding_line(line: str) -> bool:
    """Heuristically detect CLI/tool scaffolding lines.

    This is intentionally conservative to avoid removing reasoning content.
    """

    s = line.strip()
    if not s:
        return False

    low = s.lower()

    # Common imperative patterns tied to terminal/tool usage
    if re.search(r"\b(run|execute|open|use)\b", low) and re.search(
        r"\b(command|terminal|bash|shell|read|write|edit|glob|grep|tool)\b",
        low,
    ):
        return True

    # Explicit tool enumeration
    if re.search(r"^tools?\s*:\s*", low):
        if re.search(r"\b(bash|read|write|edit|glob|grep)\b", low):
            return True

    # References like "Using the Bash tool" or "Use Read tool to ..."
    if "tool" in low and re.search(r"\b(bash|read|write|edit|glob|grep)\b", low):
        return True

    return False


def _extract_phase_names(headings: list[Heading]) -> list[str]:
    """Extract phase names from headings like '## Phase 1 — Setup'."""

    phases: list[str] = []
    # Accept various dash styles or colon
    re_full = re.compile(r"^phase\s+\d+\s*[—\-:]+\s*(.+)$", re.IGNORECASE)
    re_simple = re.compile(r"^phase\s+\d+\b(.*)$", re.IGNORECASE)

    for h in headings:
        if h.level not in (2, 3):
            continue
        title = h.text.strip()
        m = re_full.match(title)
        if m:
            name = m.group(1).strip()
            if name:
                phases.append(name)
                continue
        m2 = re_simple.match(title)
        if m2:
            # Fallback: if no explicit name after number, keep full title
            fallback = m2.group(0).strip()
            if fallback:
                phases.append(fallback)
    return phases
