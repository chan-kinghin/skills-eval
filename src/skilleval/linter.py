"""Linter for Claude Code skill structure and quality."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Iterable

import yaml


# -----------------------------
# Public data structures
# -----------------------------


@dataclass
class LintIssue:
    """A single lint issue discovered when checking a skill.

    Severity is one of: "error", "warning", "info".
    """

    severity: str
    message: str
    line: int | None = None


@dataclass
class LintReport:
    """Summary of lint results for a skill directory."""

    issues: list[LintIssue] = field(default_factory=list)
    quality_score: int = 100
    skill_path: Path | None = None


# -----------------------------
# Core linter entry point
# -----------------------------


def lint_skill(skill_dir: Path) -> LintReport:
    """Lint a skill directory containing `skill.md` or `SKILL.md`.

    Validates:
    - YAML frontmatter has required fields
    - Phase/step structure with numbered headings
    - Reference files under `references/` exist if linked
    - Presence of error-handling and rules sections
    - Syntax of code blocks (python via compile, bash via `bash -n`)
    """

    issues: list[LintIssue] = []

    # 1) Locate the skill file
    skill_file = find_skill_file(skill_dir)
    if skill_file is None:
        issues.append(LintIssue("error", "Skill file not found (skill.md or SKILL.md)."))
        return _finalize_report(issues, skill_dir)

    # 2) Read content
    try:
        text = skill_file.read_text(encoding="utf-8")
    except Exception as e:  # pragma: no cover - unlikely
        issues.append(LintIssue("error", f"Failed to read skill file: {e}"))
        return _finalize_report(issues, skill_file)

    # 3) Extract frontmatter and body
    fm, fm_end_line, body, body_start_line = extract_frontmatter(text)
    if fm is None:
        issues.append(LintIssue("error", "Missing YAML frontmatter (--- ... ---) at top of file.", line=1))
    else:
        # Validate required fields
        if not isinstance(fm, dict):
            issues.append(LintIssue("error", "Frontmatter must be a YAML mapping.", line=1))
        else:
            if not fm.get("name"):
                issues.append(LintIssue("error", "Frontmatter missing required field: name", line=1))
            if not fm.get("description"):
                issues.append(
                    LintIssue("error", "Frontmatter missing required field: description", line=1)
                )

    # 4) Parse body for headings and code blocks (ignoring code fence contents for headings)
    headings = collect_headings(body, base_line=body_start_line)
    code_blocks = _collect_code_blocks(body, base_line=body_start_line)

    # 5) Phase/step structure
    if not _has_numbered_phases(headings):
        issues.append(
            LintIssue(
                "error",
                "No numbered phases/steps found (e.g., '## Phase 1 — Name' or '### Step 1:').",
            )
        )

    # 6) Required sections: Error Handling and Rules
    if not _has_error_handling_section(headings):
        issues.append(LintIssue("warning", "Missing an Error Handling section (## Error Handling)."))
    if not _has_rules_section(headings):
        issues.append(LintIssue("warning", "Missing a Rules section (## Rules or ## Important Rules)."))

    # 7) Reference links
    missing_refs = _check_references_safe(skill_dir, body, base_line=body_start_line)
    issues.extend(missing_refs)

    # 8) Code block validation
    for block in code_blocks:
        if block.language in {"python", "py"}:
            err = _check_python_block(block.code)
            if err is not None:
                issues.append(
                    LintIssue(
                        "error",
                        f"Invalid Python code block: {err.message}",
                        line=block.start_line + (err.line_offset or 0),
                    )
                )
        elif block.language in {"bash", "sh", "shell"}:
            msg = _check_bash_block(block.code)
            if msg is not None:
                issues.append(
                    LintIssue(
                        "error",
                        f"Invalid Bash code block: {msg}",
                        line=block.start_line,
                    )
                )

    # 9) Compute quality score
    report = _finalize_report(issues, skill_file)
    return report


# -----------------------------
# Helpers
# -----------------------------


def find_skill_file(skill_dir: Path) -> Path | None:
    # Use directory listing for case-sensitive matching (macOS FS is case-insensitive)
    try:
        entries = {e.name: e for e in skill_dir.iterdir() if e.is_file()}
    except OSError:
        return None
    for name in ("skill.md", "SKILL.md"):
        if name in entries:
            return entries[name]
    return None


def extract_frontmatter(text: str) -> tuple[dict | None, int, str, int]:
    """Extract YAML frontmatter and return (frontmatter, fm_end_line, body, body_start_line).

    If no frontmatter is found at the top, returns (None, 0, original_text, 1).
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, 0, text, 1

    # Find closing '---'
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        # Unterminated frontmatter; treat as missing to avoid YAML errors
        return None, 0, text, 1

    yaml_text = "\n".join(lines[1:end_idx])
    try:
        data = yaml.safe_load(yaml_text)
    except yaml.YAMLError:
        data = None

    body_lines = lines[end_idx + 1 :]
    body = "\n".join(body_lines)
    return data, end_idx + 1, body, end_idx + 2  # end_idx is 0-based; body starts next line (1-based)


@dataclass
class Heading:
    level: int
    text: str
    line: int


@dataclass
class _CodeBlock:
    language: str
    code: str
    start_line: int


def collect_headings(text: str, base_line: int = 1) -> list[Heading]:
    headings: list[Heading] = []
    in_code = False
    line_no = base_line - 1
    for raw_line in text.splitlines():
        line_no += 1
        line = raw_line.rstrip("\n")
        if line.strip().startswith("```"):
            if not in_code:
                in_code = True
            else:
                # Close only if the same fence type (```)
                in_code = False
            continue
        if in_code:
            continue
        m = re.match(r"^(#{2,6})\s+(.+)$", line)
        if m:
            level = len(m.group(1))
            text_content = m.group(2).strip()
            headings.append(Heading(level=level, text=text_content, line=line_no))
    return headings


def _collect_code_blocks(text: str, base_line: int = 1) -> list[_CodeBlock]:
    blocks: list[_CodeBlock] = []
    in_code = False
    code_lang = ""
    buf: list[str] = []
    start_line = base_line
    line_no = base_line - 1
    for raw_line in text.splitlines():
        line_no += 1
        line = raw_line.rstrip("\n")
        fence_match = re.match(r"^```(\w+)?\s*$", line.strip())
        if fence_match:
            if not in_code:
                in_code = True
                code_lang = (fence_match.group(1) or "").lower()
                buf = []
                start_line = line_no + 1  # First code line is next line
            else:
                blocks.append(_CodeBlock(language=code_lang, code="\n".join(buf), start_line=start_line))
                in_code = False
                code_lang = ""
                buf = []
            continue
        if in_code:
            buf.append(raw_line)
    return blocks


def _has_numbered_phases(headings: Iterable[Heading]) -> bool:
    phase_re = re.compile(r"^(?:phase|step)\s+\d+\b", re.IGNORECASE)
    for h in headings:
        if h.level in (2, 3) and phase_re.search(h.text):
            return True
    return False


def _has_error_handling_section(headings: Iterable[Heading]) -> bool:
    err_re = re.compile(r"error\s+handling", re.IGNORECASE)
    for h in headings:
        if h.level in (2, 3) and err_re.search(h.text):
            return True
    return False


def _has_rules_section(headings: Iterable[Heading]) -> bool:
    rules_re = re.compile(r"\brules\b", re.IGNORECASE)
    for h in headings:
        if h.level in (2, 3) and rules_re.search(h.text):
            return True
    return False


@dataclass
class _PyErr:
    message: str
    line_offset: int | None = None


def _check_python_block(code: str) -> _PyErr | None:
    try:
        compile(code, filename="<skill-python-block>", mode="exec")
        return None
    except SyntaxError as e:
        # Compute a relative offset (within the code block)
        return _PyErr(message=str(e), line_offset=getattr(e, "lineno", None))
    except Exception as e:  # pragma: no cover - rare
        return _PyErr(message=str(e))


def _check_bash_block(code: str) -> str | None:
    # Prefer using bash -n if available, else do a basic balance check
    if _bash_available():
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".sh") as f:
            f.write(code)
            tmp_path = f.name
        try:
            result = subprocess.run(
                ["bash", "-n", tmp_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if result.returncode != 0:
                err = (result.stderr or result.stdout).strip()
                return err or "bash -n reported a syntax error"
            return None
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    # Fallback: very basic check for balanced quotes and brackets
    if not _balanced(code):
        return "Unbalanced quotes or brackets in bash code"
    return None


def _bash_available() -> bool:
    from shutil import which

    return which("bash") is not None


def _balanced(s: str) -> bool:
    stack: list[str] = []
    quotes = {"'": "'", '"': '"', "`": "`"}
    pairs = {"(": ")", "[": "]", "{": "}"}
    for ch in s:
        if stack and stack[-1] in quotes:
            # Inside a quote block
            if ch == stack[-1]:
                stack.pop()
            continue
        if ch in quotes:
            stack.append(ch)
        elif ch in pairs:
            stack.append(pairs[ch])
        elif ch in pairs.values():
            if not stack or stack.pop() != ch:
                return False
    return not stack


def _finalize_report(issues: list[LintIssue], skill_path: Path | None) -> LintReport:
    # Quality score computation
    score = 100
    for iss in issues:
        sev = iss.severity.lower()
        if sev == "error":
            score -= 20
        elif sev == "warning":
            score -= 10
        elif sev == "info":
            score -= 2
    score = max(0, score)
    return LintReport(issues=issues, quality_score=score, skill_path=skill_path)


# New safe reference checker used by the linter
def _check_references_safe(skill_dir: Path, body: str, base_line: int = 1) -> list[LintIssue]:
    """Scan markdown for reference links and verify files exist.

    Accepts links like [text](references/file.md) or [text](./references/file.md).
    """
    issues: list[LintIssue] = []
    pattern = re.compile(r"\[[^\]]*\]\((?:\./)?references/[^)]+\)")
    base = skill_dir.resolve()
    for idx, raw_line in enumerate(body.splitlines(), start=base_line):
        for m in pattern.finditer(raw_line):
            link = m.group(0)
            p_m = re.search(r"\(([^)]+)\)", link)
            if not p_m:
                continue
            rel_path = p_m.group(1)
            # Strip optional matching quotes
            if rel_path.startswith(("'", '"')) and rel_path.endswith(rel_path[0]):
                rel_path = rel_path[1:-1]
            target = (skill_dir / rel_path).resolve()
            try:
                target.relative_to(base)
            except Exception:
                issues.append(LintIssue("warning", f"Reference escapes skill directory: {rel_path}", line=idx))
                continue
            if not target.exists():
                issues.append(LintIssue("error", f"Missing reference file: {rel_path}", line=idx))
    return issues
