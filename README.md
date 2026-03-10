# SkillEval

[English](README.md) | [中文](README_ZH.md)

[![PyPI version](https://img.shields.io/pypi/v/skilleval.svg)](https://pypi.org/project/skilleval/)
[![PyPI downloads](https://img.shields.io/pypi/dm/skilleval.svg)](https://pypi.org/project/skilleval/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)

**Find the cheapest LLM that gets your task 100% right.**

SkillEval is a CLI tool that automates LLM evaluation for deterministic tasks. It runs your task across multiple models in parallel, compares outputs against expected results, and recommends the most cost-effective option.

## Quick Start

```bash
pip install skilleval

# Set at least one provider API key
export DASHSCOPE_API_KEY="sk-..."   # Qwen (Alibaba DashScope)

# Create a task folder
skilleval init my-task

# Add your input files, expected output, and skill prompt
# Then run the evaluation
skilleval run my-task/

# Machine-readable output
skilleval run my-task/ --json | jq '.recommendation'
```

## Supported Providers

| Provider   | Platform                  | Env Variable         |
|------------|---------------------------|----------------------|
| **Qwen**   | Alibaba Cloud / DashScope | `DASHSCOPE_API_KEY`  |
| **GLM**    | Zhipu AI / BigModel       | `ZHIPU_API_KEY`      |
| **MiniMax** | MiniMax                  | `MINIMAX_API_KEY`    |

## Evaluation Modes

- **Mode 1 (`run`)** — You write the prompt (skill), SkillEval tests it across models.
- **Mode 2 (`matrix`)** — One model writes the prompt, another executes it. Tests all creator x executor combinations.
- **Mode 3 (`chain`)** — A meta-skill guides prompt creation, then another model executes it. Full pipeline evaluation.

## Additional Features

- **Ad-hoc endpoints** — Use any OpenAI-compatible API without editing the catalog: `--endpoint`, `--api-key`, `--model-name`.
- **Skill linting (`lint` / `--skill-format claude`)** — Validate Claude Code skill structure (frontmatter, phases, references, code blocks). Use `--skill-format claude` on `run`/`matrix`/`chain` to get a `lint_score` (0-100) alongside pass rate.
- **Skill testing (`skill-test`)** — Test a skill's core prompt logic against expected outputs.
- **Run comparison (`compare`)** — Diff two runs to detect improvements or regressions.
- **HTML reports (`report --html`)** — Generate self-contained HTML reports for sharing.
- **JSON output (`--json`)** — Machine-readable JSON on `run`, `matrix`, `chain`, `catalog`, and `report` commands for piping into other tools.
- **Verbose logging (`-v` / `-vv`)** — `-v` for INFO, `-vv` for DEBUG. Logs go to stderr so they don't interfere with `--json` output.
- **Auto-confirm (`--yes` / `-y`)** — Skip the confirmation prompt on `chain` (replaces the old `--confirm` flag).
- **Config validation** — Warns on unknown keys in `config.yaml` and validates comparator names at load time.
- **Circuit breaker** — Automatically skips a provider after 5 consecutive failures, avoiding wasted time and cost.
- **Ctrl+C handling** — Saves partial results on interrupt so you never lose a half-finished run.
- **Interactive TUI** — Launch `skilleval` with no arguments for a guided interactive mode.
- **Context window tracking** — Results include each model's context window size for informed comparisons.
- **Internationalization** — Full English and Chinese UI support (`language: zh` in settings or `LANG` env var).
- **Friendly errors** — No raw tracebacks by default; use `-vv` to see full stack traces when debugging.
- **Progress bar** — Shows elapsed time and ETA alongside the completion percentage.

## Documentation

See the [User Manual](docs/USER_MANUAL.md) ([中文](docs/USER_MANUAL_ZH.md)) for detailed setup instructions, configuration options, comparator reference, and walkthroughs.

## Development

```bash
pip install -e ".[dev,docs]"
pytest
ruff check src/ tests/
```

See [CONTRIBUTING.md](CONTRIBUTING.md) ([中文](CONTRIBUTING_ZH.md)) for full contributor guidelines.

## License

[MIT](LICENSE)
