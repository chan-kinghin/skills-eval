from __future__ import annotations

from pathlib import Path

from skilleval.linter import LintReport, lint_skill, lint_skill_text


def write(p: Path, content: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def test_missing_skill_file_reports_error(tmp_path: Path) -> None:
    report = lint_skill(tmp_path)
    assert isinstance(report, LintReport)
    assert any(
        iss.severity == "error" and "Skill file not found" in iss.message for iss in report.issues
    )
    assert report.quality_score < 100


def test_valid_skill_passes_all_checks(tmp_path: Path) -> None:
    # Create references
    write(tmp_path / "references" / "plan-format.md", "# Plan Format\n")

    skill_md = """---
name: codex-dispatch
description: Dispatch plan stages to Codex CLI
disable-model-invocation: true
---

## Phase 1 — Setup

Run initial setup.

```python
def ok():
    return 1
```

```bash
echo "hello"
```

See [plan format](references/plan-format.md).

## Error Handling

Describe error handling here.

## Rules

- Always validate inputs
"""
    write(tmp_path / "skill.md", skill_md)

    report = lint_skill(tmp_path)
    assert report.issues == []
    assert report.quality_score == 100
    assert report.skill_path and report.skill_path.name == "skill.md"


def test_frontmatter_missing_fields(tmp_path: Path) -> None:
    skill_md = """---
name: only-name
---

## Phase 1 - Do
"""
    write(tmp_path / "skill.md", skill_md)
    report = lint_skill(tmp_path)
    msgs = [i.message for i in report.issues]
    assert any("Frontmatter missing required field: description" in m for m in msgs)


def test_missing_numbered_phases(tmp_path: Path) -> None:
    skill_md = """---
name: a
description: b
---

## Overview

No phases here.
"""
    write(tmp_path / "skill.md", skill_md)
    report = lint_skill(tmp_path)
    assert any(
        "No numbered phases/steps" in i.message for i in report.issues if i.severity == "error"
    )


def test_missing_reference_files_reported(tmp_path: Path) -> None:
    skill_md = """---
name: a
description: b
---

## Phase 1 - Do

See [missing](references/not-there.md).
"""
    write(tmp_path / "skill.md", skill_md)
    report = lint_skill(tmp_path)
    assert any(
        i.severity == "error" and "Missing reference file" in i.message for i in report.issues
    )


def test_invalid_python_block_reports_error(tmp_path: Path) -> None:
    skill_md = """---
name: a
description: b
---

## Phase 1 - Do

```python
a = (
```

## Error Handling

## Rules
"""
    write(tmp_path / "skill.md", skill_md)
    report = lint_skill(tmp_path)
    assert any(
        i.severity == "error" and i.message.startswith("Invalid Python code block")
        for i in report.issues
    )


def test_invalid_bash_block_reports_error(tmp_path: Path) -> None:
    skill_md = """---
name: a
description: b
---

## Phase 1 - Do

```bash
echo "unterminated
```

## Error Handling

## Rules
"""
    write(tmp_path / "skill.md", skill_md)
    report = lint_skill(tmp_path)
    assert any(
        i.severity == "error" and i.message.startswith("Invalid Bash code block")
        for i in report.issues
    )


def test_rules_and_error_handling_warnings_affect_score(tmp_path: Path) -> None:
    # Has frontmatter and a numbered phase but no required sections
    skill_md = """---
name: a
description: b
---

## Phase 1 - Do

Content only.
"""
    write(tmp_path / "skill.md", skill_md)
    report = lint_skill(tmp_path)
    # Expect two warnings: missing Error Handling and missing Rules
    warnings = [i for i in report.issues if i.severity == "warning"]
    assert len(warnings) == 2
    assert report.quality_score == 80


def test_accepts_uppercase_skill_filename(tmp_path: Path) -> None:
    skill_md = """---
name: a
description: b
---

## Phase 1 - Do

## Error Handling
## Rules
"""
    write(tmp_path / "SKILL.md", skill_md)
    report = lint_skill(tmp_path)
    assert report.skill_path and report.skill_path.name == "SKILL.md"
    # No errors expected (has phase, error handling, rules)
    errs = [i for i in report.issues if i.severity == "error"]
    assert not errs


# ── lint_skill_text tests ─────────────────────────────────────────────


def test_lint_skill_text_valid() -> None:
    """Full valid skill text should score 100."""
    text = """---
name: test-skill
description: A test skill for validation
---

## Phase 1 — Setup

Do initial setup.

```python
x = 1 + 2
```

## Error Handling

Handle errors gracefully.

## Rules

- Always validate inputs
"""
    report = lint_skill_text(text)
    assert report.issues == []
    assert report.quality_score == 100
    assert report.skill_path is None  # No filesystem path


def test_lint_skill_text_missing_frontmatter() -> None:
    """Text without frontmatter should produce an error."""
    text = "## Phase 1 — Do\n\nSome content.\n"
    report = lint_skill_text(text)
    assert any(
        iss.severity == "error" and "Missing YAML frontmatter" in iss.message
        for iss in report.issues
    )


def test_lint_skill_text_missing_name() -> None:
    """Frontmatter missing the 'name' field should produce an error."""
    text = """---
description: only description
---

## Phase 1 — Do

Content.
"""
    report = lint_skill_text(text)
    assert any(
        iss.severity == "error" and "Frontmatter missing required field: name" in iss.message
        for iss in report.issues
    )


def test_lint_skill_text_skips_references() -> None:
    """Broken reference links should NOT error when linting text (no directory)."""
    text = """---
name: a
description: b
---

## Phase 1 — Do

See [missing](references/not-there.md).

## Error Handling
## Rules
"""
    report = lint_skill_text(text)
    # Reference checks are skipped — no "Missing reference file" errors
    ref_errors = [iss for iss in report.issues if "Missing reference file" in iss.message]
    assert ref_errors == []


def test_lint_skill_text_catches_bad_python() -> None:
    """Invalid Python in a code block should still be caught."""
    text = """---
name: a
description: b
---

## Phase 1 — Do

```python
a = (
```

## Error Handling
## Rules
"""
    report = lint_skill_text(text)
    assert any(
        iss.severity == "error" and iss.message.startswith("Invalid Python code block")
        for iss in report.issues
    )


# ── OpenClaw format lint tests ────────────────────────────────────────


def test_openclaw_valid_no_phases_required(tmp_path: Path) -> None:
    """OpenClaw skills don't need numbered phases or error handling/rules sections."""
    skill_md = """---
name: todoist-cli
description: Manage Todoist tasks from the CLI.
---

# Todoist CLI Skill

When the user asks to manage tasks, use the Todoist API.

## Setup

Configure the API key.

## Usage

Create, update, and delete tasks.
"""
    write(tmp_path / "SKILL.md", skill_md)
    report = lint_skill(tmp_path, skill_format="openclaw")
    errors = [i for i in report.issues if i.severity == "error"]
    assert not errors
    assert report.quality_score == 100


def test_openclaw_valid_with_metadata(tmp_path: Path) -> None:
    """OpenClaw skill with full metadata.openclaw block passes cleanly."""
    skill_md = """---
name: todoist-cli
description: Manage Todoist tasks.
version: 1.2.0
metadata:
  openclaw:
    requires:
      env:
        - TODOIST_API_KEY
      bins:
        - curl
    primaryEnv: TODOIST_API_KEY
    emoji: "✅"
---

# Todoist CLI

Manage tasks via API.
"""
    write(tmp_path / "SKILL.md", skill_md)
    report = lint_skill(tmp_path, skill_format="openclaw")
    assert report.issues == []
    assert report.quality_score == 100


def test_openclaw_invalid_requires_env_type() -> None:
    """metadata.openclaw.requires.env must be a list."""
    text = """---
name: a
description: b
metadata:
  openclaw:
    requires:
      env: NOT_A_LIST
---

# Skill

Content.
"""
    report = lint_skill_text(text, skill_format="openclaw")
    assert any(
        "requires.env must be a list" in i.message for i in report.issues if i.severity == "warning"
    )


def test_openclaw_invalid_requires_bins_type() -> None:
    """metadata.openclaw.requires.bins must be a list."""
    text = """---
name: a
description: b
metadata:
  openclaw:
    requires:
      bins: just-a-string
---

# Skill

Content.
"""
    report = lint_skill_text(text, skill_format="openclaw")
    assert any(
        "requires.bins must be a list" in i.message
        for i in report.issues
        if i.severity == "warning"
    )


def test_openclaw_missing_frontmatter() -> None:
    """OpenClaw skills still require frontmatter."""
    text = "# No frontmatter\n\nJust content.\n"
    report = lint_skill_text(text, skill_format="openclaw")
    assert any(
        iss.severity == "error" and "Missing YAML frontmatter" in iss.message
        for iss in report.issues
    )


def test_openclaw_missing_name() -> None:
    """OpenClaw skills still require name in frontmatter."""
    text = """---
description: only description
---

# Skill

Content.
"""
    report = lint_skill_text(text, skill_format="openclaw")
    assert any(
        iss.severity == "error" and "missing required field: name" in iss.message
        for iss in report.issues
    )


def test_openclaw_catches_bad_code_blocks() -> None:
    """Code block validation still applies for openclaw format."""
    text = """---
name: a
description: b
---

# Skill

```python
a = (
```
"""
    report = lint_skill_text(text, skill_format="openclaw")
    assert any(
        iss.severity == "error" and "Invalid Python code block" in iss.message
        for iss in report.issues
    )


def test_openclaw_accepts_clawdbot_alias() -> None:
    """metadata.clawdbot is accepted as alias for metadata.openclaw."""
    text = """---
name: a
description: b
metadata:
  clawdbot:
    requires:
      env:
        - MY_KEY
---

# Skill

Content.
"""
    report = lint_skill_text(text, skill_format="openclaw")
    assert report.issues == []
    assert report.quality_score == 100
