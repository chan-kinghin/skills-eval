# SkillEval

[English](README.md) | [中文](README_ZH.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)

**Find the cheapest LLM that gets your task 100% right.**

SkillEval is a CLI tool that automates LLM evaluation for deterministic tasks. It runs your task across multiple models in parallel, compares outputs against expected results, and recommends the most cost-effective option.

## Quick Start

```bash
pip install -e .

# Set at least one provider API key
export DASHSCOPE_API_KEY="sk-..."   # Qwen (Alibaba DashScope)

# Create a task folder
skilleval init my-task

# Add your input files, expected output, and skill prompt
# Then run the evaluation
skilleval run my-task/
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
- **Skill linting (`lint`)** — Validate Claude Code skill structure (frontmatter, phases, references, code blocks).
- **Skill testing (`skill-test`)** — Test a skill's core prompt logic against expected outputs.
- **Run comparison (`compare`)** — Diff two runs to detect improvements or regressions.
- **HTML reports (`report --html`)** — Generate self-contained HTML reports for sharing.

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
