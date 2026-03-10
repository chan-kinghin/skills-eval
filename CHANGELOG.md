# Changelog

All notable changes to SkillEval will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-03

Initial public release.

### Evaluation Modes
- **Mode 1 (`run`)** — Test your prompt across all models and find the cheapest at 100% accuracy
- **Mode 2 (`matrix`)** — Cross-evaluate creator × executor model combinations
- **Mode 3 (`chain`)** — Meta-prompt guided prompt creation + execution pipeline

### Providers & Models
- 10 models from 3 providers: Qwen (DashScope), GLM (Zhipu AI), MiniMax
- Ad-hoc endpoint support for any OpenAI-compatible API (`--endpoint`, `--api-key`, `--model-name`)
- Context window tracking for all models

### Comparators
- Six built-in comparators: `json_exact`, `csv_ordered`, `csv_unordered`, `field_subset`, `file_hash`, `custom`
- Pluggable comparator registry for custom comparison strategies

### CLI Features
- `skilleval init` — Scaffold a new task folder
- `skilleval catalog` — List available models with pricing
- `skilleval report` — Generate evaluation reports
- `skilleval report --html` — Self-contained HTML reports
- `skilleval lint` — Validate Claude Code skill structure
- `skilleval skill-test` — Test skill prompt logic against expected outputs
- `skilleval compare` — Diff two runs for regressions or improvements
- Interactive TUI mode (launch `skilleval` with no arguments)
- `--json` output on all major commands for CI/CD integration
- `-v` / `-vv` verbose logging (INFO / DEBUG to stderr)
- `--yes` / `-y` auto-confirm for `chain` mode

### Reliability
- Async parallel execution with per-provider rate limiting
- Circuit breaker — auto-skips providers after 5 consecutive failures
- Ctrl+C handling — saves partial results on interrupt
- Config validation with unknown-key warnings

### Internationalization
- Full English and Chinese UI support
- Bilingual documentation (README, User Manual, Contributing Guide, Install Guide)

### Developer Experience
- `--skill-format claude` flag for integrated skill linting alongside evaluation
- Friendly error messages (no raw tracebacks by default)
- Progress bar with elapsed time and ETA

[0.1.0]: https://github.com/chan-kinghin/skills-eval/releases/tag/v0.1.0
