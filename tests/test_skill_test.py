from __future__ import annotations

from pathlib import Path

from skilleval.skill_parser import load_test_cases, parse_skill


def _write(p: Path, content: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def test_parse_skill_extracts_core_prompt_and_phases(tmp_path: Path) -> None:
    # Prepare a sample skill with frontmatter, phases, python & bash blocks, and tool scaffolding lines
    skill_md = """---
name: sample-skill
description: Example for testing
---

## Phase 1 — Setup

Use the Bash tool to create directories.
Run this command to initialize the project.

```python
def logic():
    return "ok"
```

```bash
echo "should be removed"
```

## Phase 2 - Analysis

Explain how to reason about inputs and choose actions.

"""
    _write(tmp_path / "skill.md", skill_md)

    sp = parse_skill(tmp_path)

    assert sp.name == "sample-skill"
    assert sp.description == "Example for testing"
    # full_text should include everything after frontmatter
    assert "Use the Bash tool" in sp.full_text
    assert "```bash" in sp.full_text
    # core_prompt should strip bash block and tool/CLI scaffolding lines
    assert "Use the Bash tool" not in sp.core_prompt
    assert "Run this command" not in sp.core_prompt
    assert "```bash" not in sp.core_prompt
    assert "should be removed" not in sp.core_prompt
    # Keep python logic
    assert "def logic():" in sp.core_prompt

    # Extracted phases should capture names
    assert sp.phases and sp.phases[0].lower().startswith("setup")
    assert any(
        p.lower().startswith("phase 2") or p.lower().startswith("analysis") for p in sp.phases
    )

    assert sp.source_path.name in {"skill.md", "SKILL.md"}


def test_load_test_cases_builds_taskfolders(tmp_path: Path) -> None:
    # Shared config
    cfg = """
comparator: json_exact
trials: 2
timeout: 30
    """
    _write(tmp_path / "config.yaml", cfg)

    # case-1
    _write(tmp_path / "case-1" / "input" / "data.json", "{}\n")
    _write(tmp_path / "case-1" / "expected" / "result.json", "{}\n")

    # case-2
    _write(tmp_path / "case-2" / "input" / "doc.txt", "hello\n")
    _write(tmp_path / "case-2" / "expected" / "result.json", '{"ok": true}\n')

    cases = load_test_cases(tmp_path)
    assert len(cases) == 2

    # Sort for predictable assertions
    cases = sorted(cases, key=lambda c: c.path.name)

    assert cases[0].path.name == "case-1"
    assert any(p.name == "data.json" for p in cases[0].input_files)
    assert any(p.name == "result.json" for p in cases[0].expected_files)
    assert cases[0].config.trials == 2
    assert cases[0].config.timeout == 30

    assert cases[1].path.name == "case-2"
    assert any(p.name == "doc.txt" for p in cases[1].input_files)
    assert any(p.name == "result.json" for p in cases[1].expected_files)
    assert cases[1].config.trials == 2
