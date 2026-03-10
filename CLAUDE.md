# SkillsEval

CLI tool to find the cheapest LLM that achieves 100% on deterministic tasks.

## Commands

```bash
# Dev setup
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,docs]"

# Test & lint (always use .venv python, system Python is 3.9)
.venv/bin/python -m pytest tests/ -q
ruff check src/ tests/
ruff format src/ tests/
```

## Architecture

Package at `src/skilleval/`, entry point `skilleval.cli:cli` (Click).

Key modules:
- `models.py` — Pydantic contracts (all modules depend on this)
- `client.py` — async HTTP client with retry + circuit breaker
- `engine.py` — concurrency control (global + per-provider semaphores)
- `runner.py` — mode 1/2/3 orchestrators with Ctrl+C handling
- `config.py` — task folder loading, model catalog, config validation
- `comparators/` — pluggable comparison strategies (registry in `__init__.py`)
- `display.py` — Rich terminal output, progress bars
- `html_report.py` — self-contained HTML report generation
- `linter.py` — Claude Code skill structure validation
- `tui.py` — interactive TUI mode (prompt_toolkit)
- `compare.py` — run-to-run diffing / regression detection
- `i18n/` — bilingual support (en/zh yaml locale files)

## Code Style

- CLI subcommands: `init`, `run`, `matrix`, `chain`, `catalog`, `report`, `lint`, `compare`, `skill-test`
- Most commands support `--json` for machine-readable output
- Python 3.11+ (uses `str | None` union syntax)
- Formatter: ruff (line-length=100)
- Async tests use `pytest-asyncio` with `asyncio_mode = "auto"`
- Commit messages in English

## Gotchas

- **System Python is 3.9** — always use `.venv/bin/python` for running/testing
- **Version is git-tag-derived** (hatch-vcs) — no hardcoded version; `_version.py` is auto-generated and gitignored
- **API keys**: `DASHSCOPE_API_KEY` (Qwen, Beijing endpoint), `ZHIPU_API_KEY` (GLM), `MINIMAX_API_KEY`
- **All 197+ tests run offline** — no API keys needed for testing
- **Format before committing** — CI enforces `ruff format`; run `ruff format src/ tests/` before commits

## Release

- `git tag v0.x.0 && git push origin v0.x.0` — triggers CI → PyPI publish (trusted publisher OIDC)
- CI runs lint + tests on Python 3.11, 3.12, 3.13 on every push/PR
