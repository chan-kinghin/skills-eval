## Stage 1: TTY Auto-Detection
**Goal**: Suppress Rich progress bars, spinners, and tables when stdout is not a TTY (piped/redirected)
**Success Criteria**:
- `skilleval run my-task --output json 2>/dev/null` produces clean JSON with no ANSI escape codes
- `skilleval run my-task` in a terminal still shows Rich output
- Tests pass: `.venv/bin/python -m pytest tests/ -q`
**Files**:
- `src/skilleval/display.py` (modify)
- `src/skilleval/cli.py` (modify — if Console is created there)
- `tests/test_display.py` (modify — add TTY detection tests)
**Depends on**: —
**Context**: Rich Console accepts `force_terminal=False` to disable ANSI. Check `sys.stdout.isatty()`. Pattern used by cargo, git, rg.
**Status**: Not Started

## Stage 2: Structured JSON Errors
**Goal**: When `--json` or `--output json` is active, emit errors as JSON on stderr instead of human-readable text
**Success Criteria**:
- `skilleval run nonexistent --output json 2>&1` outputs `{"error": "...", "message": "..."}` on stderr
- Exit code is still non-zero
- Human-readable errors still work when `--json` is not active
- `ruff check src/` passes
**Files**:
- `src/skilleval/cli.py` (modify — `_SkillEvalGroup` error handler)
- `tests/test_cli.py` (modify — add structured error tests)
**Depends on**: —
**Context**: `_SkillEvalGroup` in cli.py handles all exceptions. Add JSON error formatting when output format is json. Error shape: `{"error": "<code>", "message": "<human-readable>", "hint": "<optional>"}`
**Status**: Not Started

## Stage 3: `--json` on Remaining Commands
**Goal**: Add `--json` / `--output json` support to `lint`, `compare`, and `analyze` commands
**Success Criteria**:
- `skilleval lint my-skill --json` outputs structured JSON
- `skilleval compare run-a/ run-b/ --json` outputs structured JSON
- `skilleval analyze my-task --json` outputs structured JSON
- All existing tests still pass
**Files**:
- `src/skilleval/cli.py` (modify — lint, compare, analyze commands)
- `src/skilleval/linter.py` (modify — add JSON-serializable return)
- `src/skilleval/compare.py` (modify — add JSON-serializable return)
- `tests/test_cli.py` (modify)
**Depends on**: —
**Context**: Follow existing pattern from `run`/`catalog` commands. Use `_resolve_output_format()` helper. Return Pydantic models or dicts.
**Status**: Not Started

## Stage 4: Better Exit Codes
**Goal**: Use distinct exit codes for different failure types
**Success Criteria**:
- Exit 0: success
- Exit 1: general/unknown error
- Exit 2: usage error (bad arguments, missing required flags)
- Exit 3: config error (bad yaml, missing comparator, missing task files)
- Exit 4: auth error (missing API keys, invalid keys)
- Exit 5: partial failure (some models failed, others passed)
- Exit 130: Ctrl+C interrupt
- `ruff check src/` passes
**Files**:
- `src/skilleval/cli.py` (modify — `_SkillEvalGroup`, command handlers)
- `src/skilleval/models.py` (modify — add exit code enum/constants)
- `tests/test_cli.py` (modify)
**Depends on**: —
**Context**: Define constants in models.py. Map exception types to exit codes in `_SkillEvalGroup`.
**Status**: Not Started

## Stage 5: Documentation & Porcelain Flag
**Goal**: Add `--porcelain` convenience flag and document AI-agent usage patterns in CLAUDE.md
**Success Criteria**:
- `skilleval run my-task --porcelain` is equivalent to `--output json --quiet --no-progress`
- CLAUDE.md has an "AI-Agent Usage" section with example workflows
- Output JSON schemas are informally documented
**Files**:
- `src/skilleval/cli.py` (modify — add --porcelain flag)
- `CLAUDE.md` (modify — add AI usage section)
- `README.md` (modify — mention porcelain flag)
**Depends on**: Stage 1, Stage 2, Stage 3
**Context**: `--porcelain` is Git's convention for machine-readable output. Combines all machine-friendly flags into one.
**Status**: Not Started
