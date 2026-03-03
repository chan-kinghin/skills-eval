# Contributing to SkillEval

[English](CONTRIBUTING.md) | [中文](CONTRIBUTING_ZH.md)

Thanks for your interest in contributing! This guide will help you get set up.

## Dev Setup

```bash
git clone <repo-url>
cd skills-eval
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,docs]"
```

## Running Tests and Linter

```bash
pytest                    # run 200+ offline tests (no API keys needed)
pytest --cov=skilleval    # run tests with coverage
ruff check src/ tests/    # lint
```

All tests must pass before submitting a PR. The CI pipeline runs both lint and tests across Python 3.11, 3.12, and 3.13.

## Project Structure

```
src/skilleval/
├── cli.py              # Click CLI commands (init, run, matrix, chain, catalog, report, lint, compare, skill-test) with --json, -v, --yes flags
├── config.py           # Task folder loading, model catalog, filtering, ad-hoc model builder, config validation
├── client.py           # Async OpenAI-compatible HTTP client with retry
├── engine.py           # Concurrency control (global + per-provider semaphores, circuit breaker)
├── runner.py           # Mode 1/2/3 orchestrators with Ctrl+C handling
├── models.py           # Pydantic data models (shared contracts)
├── documents.py        # PDF/DOCX/XLSX text extraction
├── display.py          # Rich console output helpers, progress bar with ETA
├── results.py          # Result file writer
├── linter.py           # Claude Code skill structure validation
├── skill_parser.py     # Skill prompt extraction and test case loading
├── compare.py          # Run comparison / regression detection
├── html_report.py      # Self-contained HTML report generation
├── default_models.yaml # Bundled model catalog
└── comparators/
    ├── __init__.py     # Registry and factory (get_comparator)
    ├── base.py         # Comparator protocol, helpers (strip fences/tags, file pairs)
    ├── json_exact.py   # Deep-equality JSON with int/float normalization
    ├── csv_ordered.py  # Row-by-row CSV match
    ├── csv_unordered.py# Multiset (Counter-based) CSV match
    ├── field_subset.py # Recursive expected ⊆ output check
    ├── file_hash.py    # SHA-256 byte-identical comparison
    └── custom.py       # Run external script for comparison
```

## How to Add a Provider

No code changes needed. Add an entry to `default_models.yaml`:

```yaml
- name: my-new-model
  provider: my-provider
  endpoint: https://api.example.com/v1
  input_cost_per_m: 0.5
  output_cost_per_m: 1.5
  env_key: MY_PROVIDER_API_KEY
  context_window: 128000
```

The endpoint must be OpenAI-compatible (`/chat/completions`). Set the env var and the model will appear in `skilleval catalog`.

## How to Add a Comparator

1. Create `src/skilleval/comparators/my_comparator.py`:

```python
from pathlib import Path
from skilleval.comparators.base import get_file_pairs

class MyComparator:
    def compare(self, output_dir: Path, expected_dir: Path) -> tuple[bool, str | None]:
        pairs = get_file_pairs(output_dir, expected_dir)
        # ... your comparison logic ...
        return True, None  # (passed, diff_text_or_None)
```

2. Register it in `src/skilleval/comparators/__init__.py`:

```python
from skilleval.comparators.my_comparator import MyComparator

COMPARATORS["my_comparator"] = MyComparator
```

3. Add tests in `tests/test_comparators/test_my_comparator.py`.

## Code Style

- Python 3.11+ syntax (`str | None`, not `Optional[str]`)
- Formatted and linted with [ruff](https://docs.astral.sh/ruff/)
- Line length: 100 characters
- Tests use `pytest` with `tmp_path` fixtures for filesystem tests
- Use `logging.getLogger(__name__)` for module-level loggers. Logging goes to stderr via the CLI's `-v` flag.
