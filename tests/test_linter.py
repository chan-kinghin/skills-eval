from __future__ import annotations

from pathlib import Path

from skilleval.linter import LintReport, lint_skill


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
