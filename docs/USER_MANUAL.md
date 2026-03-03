# SkillEval User Manual

[English](USER_MANUAL.md) | [中文](USER_MANUAL_ZH.md)

> Find the cheapest LLM that gets your task 100% right.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Installation](#2-installation)
3. [Quick Start](#3-quick-start)
4. [Core Concepts](#4-core-concepts)
5. [Setting Up a Task](#5-setting-up-a-task)
6. [Mode 1: Skill Evaluation (`run`)](#6-mode-1-skill-evaluation)
7. [Mode 2: Matrix Evaluation (`matrix`)](#7-mode-2-matrix-evaluation)
8. [Mode 3: Chain Evaluation (`chain`)](#8-mode-3-chain-evaluation)
9. [Ad-Hoc Endpoints](#9-ad-hoc-endpoints)
10. [Skill Linting (`lint`)](#10-skill-linting)
11. [Skill Testing (`skill-test`)](#11-skill-testing)
12. [Run Comparison (`compare`)](#12-run-comparison)
13. [HTML Reports](#13-html-reports)
14. [CLI Reference](#14-cli-reference)
15. [Configuration (`config.yaml`)](#15-configuration)
16. [Model Catalog](#16-model-catalog)
17. [Supported Input Files](#17-supported-input-files)
18. [Comparators](#18-comparators)
19. [Results & Output](#19-results--output)
20. [Sample Walkthrough](#20-sample-walkthrough)
21. [Troubleshooting / FAQ](#21-troubleshooting--faq)

---

## 1. Introduction

SkillEval is a CLI tool that helps you find the **cheapest LLM** that achieves **100% accuracy** on deterministic tasks. Rather than manually testing models one by one, SkillEval automates the process: it runs your task across multiple models, compares outputs against expected results, and recommends the most cost-effective option.

### The Problem

You have a repeatable task (e.g., extracting structured data from invoices) and want to use an LLM to automate it. Many models can do the job, but they vary wildly in price. You need to find the cheapest model that gets it right every time.

### The Solution

SkillEval runs your task against multiple models in parallel, automatically comparing each output to your expected result. It supports three evaluation modes of increasing sophistication:

- **Mode 1** — You write the prompt (skill), SkillEval tests it across models.
- **Mode 2** — One model writes the prompt, another executes it.
- **Mode 3** — Chain: a meta-skill guides prompt creation, then execution.

### Supported Providers

| Provider | Platform | Signup |
|----------|----------|--------|
| **Qwen** | Alibaba Cloud / DashScope | https://dashscope.console.aliyun.com/ |
| **GLM** | Zhipu AI / BigModel | https://open.bigmodel.cn/ |
| **MiniMax** | MiniMax | https://platform.minimax.io/ |

All providers use OpenAI-compatible chat completion APIs.

---

## 2. Installation

### Requirements

- **Python 3.11** or later (SkillEval uses `str | None` union syntax)
- At least one provider API key

### Install from Source

```bash
# Clone the repository
git clone <repo-url> && cd skills-eval

# Install in editable mode
pip install -e .
```

### Install with Document Extraction Support

To process PDF, Word, and Excel input files, install the optional `docs` dependencies:

```bash
pip install -e ".[docs]"
```

This installs:
- `pdfplumber` — PDF text and table extraction
- `python-docx` — Word document extraction
- `openpyxl` — Excel spreadsheet extraction

### Set Up API Keys

Set environment variables for the providers you want to use:

```bash
# Qwen (DashScope) — Beijing endpoint
export DASHSCOPE_API_KEY="sk-..."

# GLM (Zhipu AI)
export ZHIPU_API_KEY="..."

# MiniMax
export MINIMAX_API_KEY="..."
```

You only need keys for providers whose models you want to evaluate. SkillEval automatically detects which keys are set and filters the model catalog accordingly.

### Verify Installation

```bash
skilleval --version
skilleval catalog
```

The `catalog` command shows all models and whether each is marked **Ready** (API key found) or **No Key**.

---

## 3. Quick Start

This section walks you through a minimal first evaluation using the bundled sample task.

### Step 1: Check Available Models

```bash
skilleval catalog
```

Verify at least one model shows **Ready**.

### Step 2: Run the Sample Task

```bash
skilleval run sample-tasks/invoice-extraction
```

This runs the invoice-extraction task across all available models using the default settings (5 trials, `json_exact` comparator, temperature 0).

### Step 3: Read the Results

SkillEval prints a results table showing each model's pass rate, average cost, and latency. If any model achieves 100%, it recommends the cheapest one.

Results are also saved to `sample-tasks/invoice-extraction/.skilleval/run-<timestamp>/`.

### Step 4: Create Your Own Task

```bash
skilleval init my-task
```

This creates a task folder with template files. Edit them to define your task, then run `skilleval run my-task`.

---

## 4. Core Concepts

### Task Folder

A task folder contains everything SkillEval needs to evaluate models on your task:

```
my-task/
├── config.yaml          # Task configuration
├── skill.md             # System prompt for Mode 1
├── prompt.md            # Task description for Mode 2/3
├── meta-skill.md        # Meta-skill for Mode 3 (or meta-skill-*.md variants)
├── input/               # Input files sent to the model
│   └── data.txt
├── expected/            # Expected output files for comparison
│   └── result.json
└── .skilleval/          # Results (auto-created by SkillEval)
```

### Skill

A **skill** is the system prompt that instructs the model how to perform the task. In Mode 1, you write it yourself (`skill.md`). In Mode 2/3, a creator model generates it from the task description (`prompt.md`).

### Trial

A **trial** is a single API call to a model. By default, SkillEval runs 5 trials per model. Running multiple trials catches non-deterministic behavior — a model must pass *all* trials to achieve 100%.

### Comparator

A **comparator** is the strategy used to check whether a model's output matches the expected result. SkillEval ships with 6 comparators (see [Comparators](#18-comparators)).

### Modes

| Mode | Command | You Provide | SkillEval Does |
|------|---------|-------------|----------------|
| **1** | `run` | Skill (system prompt) | Tests it across models |
| **2** | `matrix` | Task description | Generates skills with creator models, tests with executor models |
| **3** | `chain` | Meta-skill + task description | Meta-skill guides skill generation, then execution |

---

## 5. Setting Up a Task

### Creating a New Task

```bash
skilleval init my-extraction-task
```

This creates the following structure:

```
my-extraction-task/
├── config.yaml       # Configuration with commented defaults
├── skill.md          # Template for Mode 1 system prompt
├── prompt.md         # Template for Mode 2/3 task description
├── meta-skill.md     # Template for Mode 3 meta-skill
├── input/            # Empty — add your input files here
└── expected/         # Empty — add expected output files here
```

### Preparing Input Files

Place the files your model will process in the `input/` directory. SkillEval supports many formats (see [Supported Input Files](#17-supported-input-files)). All input files are concatenated and sent as part of the prompt.

Input files are formatted for the LLM as:

```
--- File: invoice.txt ---
[file content here]
--- End File ---
```

### Preparing Expected Output

Place the correct output in the `expected/` directory. The filename should match what your comparator expects. For `json_exact`, place the expected JSON in a `.json` file.

### Writing the Skill (Mode 1)

Edit `skill.md` with clear, specific instructions for the model. Be explicit about the output format, field names, and any transformation rules. The skill is sent as the system message in the chat completion request.

### Writing the Prompt (Mode 2/3)

Edit `prompt.md` with a human-readable description of the task. This is used by the creator model to *generate* a skill. Include examples of input/output and any constraints.

### Writing Meta-Skills (Mode 3)

For Mode 3, rename `meta-skill.md` to `meta-skill-<variant>.md`. You can create multiple variants:

```
meta-skill-concise.md      # Variant that asks for brief skills
meta-skill-detailed.md     # Variant that asks for step-by-step skills
meta-skill-structured.md   # Variant that emphasizes output structure
```

Each variant is referenced by its name (e.g., `concise`, `detailed`, `structured`).

---

## 6. Mode 1: Skill Evaluation

**Command:** `skilleval run <task_path>`

Mode 1 is the simplest evaluation mode. You write the skill (system prompt) yourself, and SkillEval tests it across multiple models to find the cheapest one that gets it right.

### How It Works

1. SkillEval reads `skill.md` from your task folder.
2. Input files are extracted and formatted into a user message.
3. For each model, the skill + input are sent as a chat completion request.
4. This is repeated for the configured number of trials.
5. Each output is compared against the expected result using your chosen comparator.
6. Results are aggregated and the cheapest 100%-pass model is recommended.

### Example

```bash
# Run against all available models (5 trials each)
skilleval run my-task

# Run against specific models with 10 trials
skilleval run my-task --models qwen-turbo,glm-4.5-flash --trials 10

# Use a custom model catalog
skilleval run my-task --catalog ./my-models.yaml
```

### Output

SkillEval displays a table with columns:

| Column | Description |
|--------|-------------|
| Model | Model name |
| Pass Rate | Fraction of trials that matched expected output |
| Avg Cost | Average cost per trial in USD |
| Avg Latency | Average response time in seconds |
| Total Cost | Total cost across all trials |
| Rec | Asterisk (`*`) if this is the recommended model |

### Requirements

- `skill.md` must exist in the task folder.
- `input/` and `expected/` must contain at least one file each.

---

## 7. Mode 2: Matrix Evaluation

**Command:** `skilleval matrix <task_path>`

Mode 2 separates skill *creation* from skill *execution*. Creator models generate a skill from your task description, and executor models run that generated skill. This produces a creator-by-executor matrix showing which combinations work best.

### How It Works

**Phase 1 — Skill Generation:**
1. Each creator model receives `prompt.md` plus short descriptions of the input files.
2. The creator generates a skill (system prompt) for the task.
3. Generated skills are saved to disk.

**Phase 2 — Execution:**
1. Each executor model runs trials using each generated skill.
2. Outputs are compared against expected results.
3. Results form a matrix of (creator, executor) pairs.

### Example

```bash
skilleval matrix my-task \
  --creators qwen-max,glm-5 \
  --executors qwen-turbo,glm-4.5-flash,MiniMax-Text-01 \
  --trials 5
```

### Output

SkillEval displays a heatmap-style matrix:

```
              qwen-turbo   glm-4.5-flash   MiniMax-Text-01
qwen-max      100%         80%              100%
glm-5         60%          100%             80%
```

Cells are color-coded: green (100%), yellow (>=80%), red (<80%).

After the matrix, SkillEval reports the best pair and the cheapest pair at 100%.

### Requirements

- `prompt.md` must exist in the task folder.
- Both `--creators` and `--executors` are required.

---

## 8. Mode 3: Chain Evaluation

**Command:** `skilleval chain <task_path>`

Mode 3 adds another layer: a **meta-skill** that instructs the creator model *how* to write a skill. This lets you experiment with different prompting strategies for skill generation.

### How It Works

**Phase 1 — Skill Generation:**
1. For each (meta-skill, creator) pair:
   - The meta-skill is sent as the system message.
   - The creator receives `prompt.md` as the user message.
   - The creator generates a skill guided by the meta-skill.

**Phase 2 — Execution:**
1. Each executor runs trials with each generated skill.
2. Results form a three-dimensional structure: (meta-skill, creator, executor).

### Example

```bash
skilleval chain my-task \
  --meta-skills concise,detailed \
  --creators qwen-max,glm-5 \
  --executors qwen-turbo,glm-4.5-flash \
  --trials 5
```

### Confirmation for Large Runs

If the total number of API calls exceeds 100, SkillEval asks for confirmation before proceeding. Use `--yes` (or `-y`) to skip this prompt:

```bash
skilleval chain my-task \
  --meta-skills a,b,c --creators x,y --executors p,q,r \
  --trials 10 --yes
```

### Output

SkillEval displays:
1. A meta-skill comparison table showing average pass rate per meta-skill variant.
2. The best overall chain (meta-skill / creator / executor).
3. The cheapest chain at 100%.

### Requirements

- `prompt.md` must exist in the task folder.
- `meta-skill-<name>.md` files must exist for each named variant.
- `--meta-skills`, `--creators`, and `--executors` are all required.

---

## 9. Ad-Hoc Endpoints

You can evaluate any OpenAI-compatible model without editing the catalog by passing `--endpoint`, `--api-key`, and `--model-name` to `run`, `matrix`, `chain`, or `skill-test`.

### Example

```bash
# Test a local Ollama model
skilleval run my-task \
  --endpoint http://localhost:11434/v1 \
  --model-name llama3 \
  --api-key ""

# Test an OpenAI model alongside catalog models
skilleval run my-task \
  --endpoint https://api.openai.com/v1 \
  --api-key $OPENAI_API_KEY \
  --model-name gpt-4o \
  --models qwen-turbo,gpt-4o
```

### How It Works

The ad-hoc model is appended to the catalog and treated like any other model. It is automatically included in the `filter_available` set (since it carries an embedded API key). To run it alongside catalog models, include its `--model-name` in `--models`.

### Cost Tracking

Ad-hoc models default to `$0` for input and output costs. Token usage is still tracked, but cost calculations will show `$0`. To get accurate cost tracking, add the model to a `models.yaml` with pricing.

### Flags

| Flag | Required | Description |
|------|----------|-------------|
| `--endpoint` | Yes | OpenAI-compatible API base URL (must be `http://` or `https://`) |
| `--model-name` | Yes (with `--endpoint`) | The model identifier sent in API requests |
| `--api-key` | No | API key for the endpoint (use `""` for keyless endpoints like Ollama) |

---

## 10. Skill Linting

**Command:** `skilleval lint <skill_path>`

Validates the structure of a Claude Code skill directory. Useful for catching common issues before testing.

### What It Checks

| Check | Severity | Description |
|-------|----------|-------------|
| Frontmatter exists | Error | YAML frontmatter (`--- ... ---`) must be present at the top |
| Required fields | Error | Frontmatter must include `name` and `description` |
| Numbered phases | Error | At least one `## Phase N` or `### Step N` heading required |
| Error handling section | Warning | Missing `## Error Handling` heading |
| Rules section | Warning | Missing `## Rules` or `## Important Rules` heading |
| Reference file links | Error | Markdown links to `references/` must point to existing files |
| Python code blocks | Error | Python code blocks must have valid syntax |
| Bash code blocks | Error | Bash code blocks must pass `bash -n` syntax check |

### Quality Score

The linter computes a quality score (0-100):
- Starts at 100
- Each error deducts 20 points
- Each warning deducts 10 points
- Each info-level issue deducts 2 points

### Example

```bash
skilleval lint ~/.claude/skills/my-skill/
```

### Exit Code

Exits with code `1` if any errors are found, `0` otherwise. Warnings do not cause a non-zero exit.

---

## 11. Skill Testing

**Command:** `skilleval skill-test <skill_path> --test-cases <test_dir>`

Tests a Claude Code skill by extracting its core prompt logic and running it through the evaluation engine against multiple test cases.

### How It Works

1. Parses `skill.md` from the skill directory:
   - Strips YAML frontmatter
   - Removes tool-use scaffolding (bash/shell code blocks, CLI instructions)
   - Extracts the core prompt logic
2. Loads test cases from the test directory
3. Runs each test case through Mode 1 evaluation using the extracted prompt

### Test Case Structure

```
test-cases/
├── config.yaml           # Shared configuration (comparator, trials, etc.)
├── case-1/
│   ├── input/            # Input files for this test case
│   └── expected/         # Expected output files
├── case-2/
│   ├── input/
│   └── expected/
```

### Example

```bash
skilleval skill-test ~/.claude/skills/my-skill/ \
  --test-cases ./test-cases/ \
  --models qwen-turbo,glm-4.5-flash \
  --trials 3
```

### Output

Displays a per-case, per-model results table and an overall summary showing how many test cases each model passed.

---

## 12. Run Comparison

**Command:** `skilleval compare <old_run> <new_run>`

Compares results from two evaluation runs to detect improvements and regressions. Useful when iterating on a `skill.md` prompt.

### How It Works

1. Loads `results.json` from both run directories
2. Matches models between runs
3. Computes pass rate deltas
4. Classifies each model as: improved, regressed, unchanged, new, or removed

### Example

```bash
skilleval compare \
  my-task/.skilleval/run-20260227-143052 \
  my-task/.skilleval/run-20260228-091500
```

### Output

Displays a comparison table with columns:

| Column | Description |
|--------|-------------|
| Model | Model name |
| Old Rate | Pass rate from the first run |
| New Rate | Pass rate from the second run |
| Delta | Change in pass rate (e.g., `+20%`, `-40%`) |
| Status | `improved`, `regressed`, `unchanged`, `new`, or `removed` |

---

## 13. HTML Reports

Generate self-contained HTML reports from evaluation results for sharing with stakeholders.

### Usage

```bash
# Generate an HTML report
skilleval report my-task/.skilleval/run-20260227-143052 --html report.html

# Generate and open in browser
skilleval report my-task/.skilleval/run-20260227-143052 --html report.html --open
```

### What's Included

The HTML report is self-contained (inline CSS/JS, no external dependencies) and includes mode-specific visualizations:

**Mode 1 (`run`):**
- Pass rate bar chart per model (color-coded: green/yellow/red)
- Cost comparison table (avg cost, avg latency, total cost)
- Collapsible per-model trial details (with expand/collapse all)

**Mode 2 (`matrix`):**
- Creator x executor heatmap with color-coded cells
- Best pair highlighted with accent outline

**Mode 3 (`chain`):**
- Pass rate bars grouped by meta-skill variant
- Collapsible variant detail tables (creator, executor, pass rate, cost, latency)

### Design

The report uses a dark theme designed for readability. It is fully responsive and works on mobile.

---

## 14. CLI Reference

### `skilleval`

```
Usage: skilleval [OPTIONS] COMMAND [ARGS]...

  SkillEval: Find the cheapest model that gets your task 100% right.

Options:
  --version      Show the version and exit.
  -v, --verbose  Increase verbosity (-v for INFO, -vv for DEBUG).
  --help         Show this message and exit.

Commands:
  catalog     Display model catalog with availability status.
  chain       Mode 3: Meta-skill x creator x executor chain evaluation.
  compare     Compare results from two runs.
  init        Create a new task folder with template files.
  lint        Validate a Claude Code skill structure.
  matrix      Mode 2: Creator x executor matrix evaluation.
  report      Re-render results from a previous run.
  run         Mode 1: Evaluate models with a given skill.
  skill-test  Test a Claude Code skill against test cases.
```

### `skilleval init`

| Argument | Required | Description |
|----------|----------|-------------|
| `NAME` | Yes | Name for the new task folder |

Creates a task folder with template files (`config.yaml`, `skill.md`, `prompt.md`, `meta-skill.md`, `input/`, `expected/`).

### `skilleval run`

| Argument/Option | Required | Default | Description |
|-----------------|----------|---------|-------------|
| `TASK_PATH` | Yes | — | Path to task folder |
| `--models` | No | All available | Comma-separated model names |
| `--trials` | No | From config | Override trial count |
| `--parallel` | No | `20` | Max concurrent API calls |
| `--catalog` | No | Auto-detect | Path to model catalog YAML |
| `--endpoint` | No | — | Ad-hoc OpenAI-compatible endpoint URL |
| `--api-key` | No | — | API key for ad-hoc endpoint |
| `--model-name` | No | — | Model name for ad-hoc endpoint |
| `--json` | No | `false` | Output results as JSON (for piping) |

### `skilleval matrix`

| Argument/Option | Required | Default | Description |
|-----------------|----------|---------|-------------|
| `TASK_PATH` | Yes | — | Path to task folder |
| `--creators` | Yes | — | Comma-separated creator model names |
| `--executors` | Yes | — | Comma-separated executor model names |
| `--trials` | No | From config | Override trial count |
| `--parallel` | No | `20` | Max concurrent API calls |
| `--catalog` | No | Auto-detect | Path to model catalog YAML |
| `--endpoint` | No | — | Ad-hoc OpenAI-compatible endpoint URL |
| `--api-key` | No | — | API key for ad-hoc endpoint |
| `--model-name` | No | — | Model name for ad-hoc endpoint |
| `--json` | No | `false` | Output results as JSON (for piping) |

### `skilleval chain`

| Argument/Option | Required | Default | Description |
|-----------------|----------|---------|-------------|
| `TASK_PATH` | Yes | — | Path to task folder |
| `--meta-skills` | Yes | — | Comma-separated meta-skill variant names |
| `--creators` | Yes | — | Comma-separated creator model names |
| `--executors` | Yes | — | Comma-separated executor model names |
| `--trials` | No | From config | Override trial count |
| `--parallel` | No | `20` | Max concurrent API calls |
| `--catalog` | No | Auto-detect | Path to model catalog YAML |
| `--yes` / `-y` | No | `false` | Skip confirmation for large runs (>100 API calls) |
| `--endpoint` | No | — | Ad-hoc OpenAI-compatible endpoint URL |
| `--api-key` | No | — | API key for ad-hoc endpoint |
| `--model-name` | No | — | Model name for ad-hoc endpoint |
| `--json` | No | `false` | Output results as JSON (for piping) |

### `skilleval catalog`

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--catalog` | No | Auto-detect | Path to model catalog YAML |
| `--json` | No | `false` | Output catalog as JSON |

### `skilleval report`

| Argument/Option | Required | Default | Description |
|-----------------|----------|---------|-------------|
| `RESULTS_PATH` | Yes | — | Path to results directory or `results.json` file |
| `--html` | No | — | Path to write HTML report |
| `--open` | No | `false` | Open HTML report in browser after generation |
| `--json` | No | `false` | Output results as JSON |

Re-renders results from a previous run without making any API calls. Optionally generates a self-contained HTML report.

### `skilleval lint`

| Argument | Required | Description |
|----------|----------|-------------|
| `SKILL_PATH` | Yes | Path to Claude Code skill directory |

Validates skill structure (frontmatter, phases, references, code blocks). Exits with code `1` if errors are found.

### `skilleval compare`

| Argument | Required | Description |
|----------|----------|-------------|
| `OLD_RUN` | Yes | Path to the first (baseline) run results |
| `NEW_RUN` | Yes | Path to the second (updated) run results |

Shows a diff table of pass rate changes between two runs.

### `skilleval skill-test`

| Argument/Option | Required | Default | Description |
|-----------------|----------|---------|-------------|
| `SKILL_PATH` | Yes | — | Path to Claude Code skill directory |
| `--test-cases` | Yes | — | Path to test case directory |
| `--models` | No | All available | Comma-separated model names |
| `--trials` | No | From config | Override trial count |
| `--parallel` | No | `20` | Max concurrent API calls |
| `--catalog` | No | Auto-detect | Path to model catalog YAML |
| `--endpoint` | No | — | Ad-hoc OpenAI-compatible endpoint URL |
| `--api-key` | No | — | API key for ad-hoc endpoint |
| `--model-name` | No | — | Model name for ad-hoc endpoint |

---

## 15. Configuration

Each task folder contains a `config.yaml` file that controls evaluation behavior.

### All Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `comparator` | string | `"json_exact"` | Comparison strategy for output validation |
| `custom_script` | string | `null` | Path to custom comparator script (only used when `comparator: custom`) |
| `trials` | int | `5` | Number of trials per model. Higher values increase confidence but cost more |
| `timeout` | int | `60` | API request timeout in seconds |
| `temperature` | float | `0.0` | Model sampling temperature. Use `0.0` for deterministic output |
| `max_tokens` | int | `4096` | Maximum number of output tokens per request |
| `output_format` | string | `"json"` | Expected output format (for display purposes) |

**Validation:** SkillEval warns if your `config.yaml` contains unknown keys (possible typos). It also validates the `comparator` value at load time, reporting available options if the name is unrecognized.

### Example Configuration

```yaml
# Strict JSON comparison
comparator: json_exact

# 10 trials for high confidence
trials: 10

# Generous timeout for complex tasks
timeout: 120

# Deterministic output
temperature: 0.0

# Allow longer responses
max_tokens: 8192

output_format: json
```

### Comparator Options

| Value | Description |
|-------|-------------|
| `json_exact` | Deep equality check on parsed JSON (default) |
| `csv_ordered` | Row-by-row CSV comparison (order matters) |
| `csv_unordered` | Set-based CSV comparison (order doesn't matter) |
| `field_subset` | Check that expected fields exist in output (extra fields OK) |
| `file_hash` | Byte-identical SHA-256 comparison |
| `custom` | Run a user-provided script (requires `custom_script`) |

See [Comparators](#18-comparators) for detailed descriptions.

---

## 16. Model Catalog

### Default Models

SkillEval ships with a default model catalog covering 3 providers and 10 models:

#### Qwen (DashScope)

| Model | Tier | Input $/M | Output $/M | Context |
|-------|------|-----------|------------|---------|
| `qwen-max` | Frontier | $1.60 | $6.40 | 128K |
| `qwen-plus` | Mid | $0.40 | $1.20 | 128K |
| `qwen-turbo` | Budget | $0.05 | $0.20 | 128K |

#### GLM (Zhipu AI)

| Model | Tier | Input $/M | Output $/M | Context |
|-------|------|-----------|------------|---------|
| `glm-5` | Frontier | $1.00 | $3.20 | 128K |
| `glm-4.5` | Mid | $0.60 | $2.20 | 128K |
| `glm-4.5-air` | Mid-Low | $0.15 | $0.55 | 128K |
| `glm-4.5-flash` | Budget | $0.00 | $0.00 | 128K |

#### MiniMax

| Model | Tier | Input $/M | Output $/M | Context |
|-------|------|-----------|------------|---------|
| `MiniMax-M2.5` | Frontier | $0.30 | $1.20 | 200K |
| `MiniMax-M2` | Mid | $0.26 | $1.00 | 200K |
| `MiniMax-Text-01` | Budget | $0.20 | $1.10 | 200K |

### Catalog Resolution Order

When `--catalog` is not specified, SkillEval searches for a model catalog in this order:

1. **Explicit path** — `--catalog ./my-models.yaml`
2. **Local directory** — `./models.yaml` (current working directory)
3. **User global** — `~/.config/skilleval/models.yaml`
4. **Bundled default** — The built-in catalog shipped with the package

### Custom Catalog

Create a `models.yaml` file to add or override models:

```yaml
- name: my-custom-model
  provider: dashscope
  endpoint: https://dashscope.aliyuncs.com/compatible-mode/v1
  input_cost_per_m: 0.10
  output_cost_per_m: 0.40
  env_key: DASHSCOPE_API_KEY
  context_window: 32768
```

Each entry requires:

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique model identifier |
| `provider` | string | Provider name (used for per-provider rate limiting) |
| `endpoint` | string | OpenAI-compatible API base URL |
| `input_cost_per_m` | float | Cost per million input tokens (USD) |
| `output_cost_per_m` | float | Cost per million output tokens (USD) |
| `env_key` | string | Environment variable containing the API key |
| `context_window` | int | Maximum context length in tokens (default: 128000) |

### Environment Variables

| Provider | Variable | Signup URL |
|----------|----------|------------|
| Qwen (DashScope) | `DASHSCOPE_API_KEY` | https://dashscope.console.aliyun.com/ |
| GLM (Zhipu AI) | `ZHIPU_API_KEY` | https://open.bigmodel.cn/ |
| MiniMax | `MINIMAX_API_KEY` | https://platform.minimax.io/ |

Only models whose `env_key` variable is set in the environment are considered "available." When you run without `--models`, only available models are used.

---

## 17. Supported Input Files

SkillEval extracts text from input files and formats them for the LLM. The following file types are supported:

### Text-Based (No Extra Dependencies)

| Extension | Description |
|-----------|-------------|
| `.txt` | Plain text |
| `.md` | Markdown |
| `.json` | JSON data |
| `.csv` | Comma-separated values |
| `.tsv` | Tab-separated values |
| `.xml` | XML documents |
| `.html` | HTML pages |
| `.yaml`, `.yml` | YAML data |

### Document Formats (Require `pip install -e ".[docs]"`)

| Extension | Library | Description |
|-----------|---------|-------------|
| `.pdf` | `pdfplumber` | PDF text and table extraction. Pages are marked with `[Page N]` headers. Tables are extracted as `[Page N - Table M]`. |
| `.docx` | `python-docx` | Word document extraction. Paragraphs and tables are extracted. Tables marked with `[Table N]`. |
| `.xlsx`, `.xls` | `openpyxl` | Excel spreadsheet extraction. Each sheet is marked with `[Sheet: name]`. Non-empty rows are extracted. |

### Table Formatting

Tables from PDFs, Word documents, and Excel files are rendered as pipe-delimited markdown:

```
| Header1 | Header2 | Header3 |
| ------- | ------- | ------- |
| Value1  | Value2  | Value3  |
```

### Unknown File Types

For files with unrecognized extensions, SkillEval attempts to read them as UTF-8 text. If the file appears to be binary (based on a heuristic check of the first 512 bytes), it raises an error.

### Missing Dependencies

If you try to process a PDF, DOCX, or XLSX file without the optional dependencies installed, SkillEval raises a `RuntimeError` with install instructions:

```
RuntimeError: PDF extraction requires pdfplumber. Install with:
  pip install pdfplumber
```

---

## 18. Comparators

Comparators determine how SkillEval checks whether a model's output matches the expected result. All comparators return a (passed, diff) tuple where `diff` is `None` on success or a descriptive error string on failure.

### Output Preprocessing

Before comparison, SkillEval automatically cleans model output by:
1. **Stripping reasoning tags** — Removes `<think>`, `<thinking>`, `<reasoning>` blocks (common in reasoning models like DeepSeek-R1).
2. **Removing markdown code fences** — Strips `` ```json `` or `` ``` `` wrappers.
3. **Trimming whitespace** — Removes leading/trailing whitespace.

### `json_exact`

**Deep equality comparison for JSON output.**

- Parses both expected and output as JSON.
- Normalizes all integers to floats (so `150` matches `150.0`).
- Canonicalizes with sorted keys for consistent comparison.
- Extra keys in output cause failure — the match must be exact.
- Whitespace and formatting differences are ignored.

**Best for:** Structured data extraction where every field must match exactly.

**Example diff on failure:**
```diff
--- expected
+++ output
@@ -3,3 +3,3 @@
-  "total": 16003.75,
+  "total": 16004.0,
```

### `csv_ordered`

**Row-by-row CSV comparison with strict ordering.**

- Both column order and row order must match.
- Reports the first differing row.

**Best for:** Tabular data where row order is meaningful (e.g., chronological records).

**Example diff on failure:**
```
Row 3 differs:
  expected: ['2026-01-15', 'Invoice', '500.00']
  got:      ['2026-01-15', 'Invoice', '500']
```

### `csv_unordered`

**Set-based CSV comparison (order-independent).**

- Rows are compared as multisets (duplicates count).
- Column order still matters.
- Reports missing and extra rows with counts.

**Best for:** Tabular data where row order is irrelevant (e.g., extracted list of items).

**Example diff on failure:**
```
Missing rows (in expected but not output):
  ['Widget A', '10', '25.00'] (x1)
Extra rows (in output but not expected):
  ['Widget A', '10', '25'] (x1)
```

### `field_subset`

**Recursive subset validation for JSON.**

- Checks that all fields in the expected output exist in the actual output with matching values.
- **Extra fields in the output are allowed** — only expected fields are checked.
- Arrays must have the same length, and items are checked recursively.
- Reports mismatches using JSONPath notation.

**Best for:** Tasks where the model may return additional useful fields beyond what you require.

**Example diff on failure:**
```
$.users[0].name: expected "John", got "Jane"
$.items: expected array length 2, got 3
```

### `file_hash`

**Byte-identical comparison using SHA-256.**

- Compares raw bytes — no parsing or normalization.
- Line ending differences (CRLF vs LF) cause failure.
- Whitespace differences cause failure.

**Best for:** Tasks where output must be exactly reproducible (e.g., code generation, template filling).

**Example diff on failure:**
```
Hash mismatch for output.txt:
  expected: a1b2c3d4e5f6...
  got:      x9y8z7w6v5u4...
```

### `custom`

**User-provided validation script.**

Requires `custom_script` in `config.yaml`:

```yaml
comparator: custom
custom_script: ./compare.py
```

The script is called for each file pair:

```bash
./compare.py <expected_file> <output_file>
```

| Exit Code | Meaning |
|-----------|---------|
| `0` | Pass — output matches expected |
| Non-zero | Fail — stdout becomes the diff text |

The script has a 30-second timeout per invocation.

**Best for:** Complex validation logic that can't be expressed with built-in comparators (e.g., semantic equivalence, numeric tolerance).

**Example custom script:**

```python
#!/usr/bin/env python3
import json, sys

expected = json.load(open(sys.argv[1]))
actual = json.load(open(sys.argv[2]))

# Allow 1% tolerance on numeric fields
for key in expected:
    if isinstance(expected[key], (int, float)):
        if abs(expected[key] - actual.get(key, 0)) / max(abs(expected[key]), 1) > 0.01:
            print(f"{key}: expected {expected[key]}, got {actual.get(key)}")
            sys.exit(1)

sys.exit(0)
```

---

## 19. Results & Output

### Output Directory

Each run creates a timestamped directory under `.skilleval/` in the task folder:

```
my-task/.skilleval/run-20260227-143052/
```

### Directory Structure

The structure varies by mode:

**Mode 1 (`run`):**

```
run-20260227-143052/
├── results.json                     # Machine-readable results
├── summary.txt                      # Human-readable summary
└── trials/
    ├── qwen-turbo/
    │   ├── trial-1/
    │   │   ├── output.txt           # Model's raw output
    │   │   ├── diff.txt             # Comparison diff (only on failure)
    │   │   └── meta.json            # Token counts, cost, latency
    │   ├── trial-2/
    │   │   └── ...
    │   └── ...
    └── glm-4.5-flash/
        └── ...
```

**Mode 2 (`matrix`):**

```
run-20260227-143052/
├── results.json
├── summary.txt
├── generated_skills/
│   ├── qwen-max.md                  # Skill generated by qwen-max
│   └── glm-5.md                     # Skill generated by glm-5
└── trials/
    ├── qwen-max__qwen-turbo/        # creator__executor
    │   └── trial-1/
    │       └── ...
    └── ...
```

**Mode 3 (`chain`):**

```
run-20260227-143052/
├── results.json
├── summary.txt
├── generated_skills/
│   ├── concise__qwen-max.md         # meta-skill__creator
│   └── detailed__glm-5.md
└── trials/
    ├── concise__qwen-max__qwen-turbo/
    │   └── trial-1/
    │       └── ...
    └── ...
```

### `results.json`

The `results.json` file contains the complete `RunSummary` as JSON. Key fields:

```json
{
  "mode": "run",
  "task_path": "my-task",
  "timestamp": "2026-02-27T14:30:52",
  "model_results": [
    {
      "model": "qwen-turbo",
      "pass_rate": 1.0,
      "avg_cost": 0.00012,
      "avg_latency": 1.23,
      "total_cost": 0.0006,
      "trials": [
        {
          "model": "qwen-turbo",
          "trial_number": 1,
          "passed": true,
          "output_text": "{...}",
          "diff": null,
          "input_tokens": 850,
          "output_tokens": 320,
          "cost": 0.00012,
          "latency_seconds": 1.23,
          "error": null,
          "finish_reason": "stop"
        }
      ]
    }
  ],
  "recommendation": "qwen-turbo ($0.00012/run, 100% pass rate)"
}
```

### `meta.json` (Per Trial)

```json
{
  "input_tokens": 850,
  "output_tokens": 320,
  "cost": 0.00012,
  "latency_seconds": 1.23,
  "finish_reason": "stop"
}
```

### Re-rendering Results

Use `skilleval report` to re-display results without making API calls:

```bash
# Point to a results directory
skilleval report my-task/.skilleval/run-20260227-143052

# Or directly to the JSON file
skilleval report my-task/.skilleval/run-20260227-143052/results.json
```

---

## 20. Sample Walkthrough

This walkthrough uses the bundled `invoice-extraction` task to demonstrate an end-to-end Mode 1 evaluation.

### The Task

Extract structured data from a plain-text invoice into JSON. The input is an invoice from "TechBridge Solutions Ltd." with 4 line items, tax, and payment details. The expected output is a JSON object with fields like `vendor`, `invoice_number`, `line_items`, `subtotal`, `tax_rate`, and `total`.

### Task Structure

```
sample-tasks/invoice-extraction/
├── config.yaml          # json_exact comparator, 3 trials, temp 0
├── skill.md             # Detailed extraction instructions with output schema
├── prompt.md            # Human-readable task description
├── input/
│   └── invoice.txt      # Plain-text invoice
└── expected/
    └── result.json      # Expected JSON output
```

### Step 1: Review the Configuration

The task uses:
- `comparator: json_exact` — Output JSON must match expected exactly.
- `trials: 3` — Each model gets 3 attempts.
- `temperature: 0` — Deterministic output.
- `timeout: 120` — 2-minute timeout per request.

### Step 2: Check Available Models

```bash
skilleval catalog
```

Suppose `DASHSCOPE_API_KEY` and `ZHIPU_API_KEY` are set. The catalog shows Qwen and GLM models as "Ready."

### Step 3: Run the Evaluation

```bash
skilleval run sample-tasks/invoice-extraction
```

SkillEval:
1. Loads `skill.md` as the system prompt.
2. Reads `input/invoice.txt` and formats it as the user message.
3. Sends to each available model, 3 times each.
4. Parses each JSON response and compares against `expected/result.json`.
5. Displays results.

### Step 4: Read the Output

```
Mode 1: Skill Evaluation
Task: sample-tasks/invoice-extraction
Models: qwen-max, qwen-plus, qwen-turbo, glm-5, glm-4.5, glm-4.5-air, glm-4.5-flash
Trials: 3

┌──────────────────┬───────────┬──────────┬─────────────┬────────────┬─────┐
│ Model            │ Pass Rate │ Avg Cost │ Avg Latency │ Total Cost │ Rec │
├──────────────────┼───────────┼──────────┼─────────────┼────────────┼─────┤
│ qwen-turbo       │ 100%      │ $0.0001  │ 1.2s        │ $0.0003    │  *  │
│ glm-4.5-flash    │ 100%      │ $0.0000  │ 2.1s        │ $0.0000    │  *  │
│ qwen-plus        │ 100%      │ $0.0008  │ 1.8s        │ $0.0024    │     │
│ glm-4.5-air      │ 67%       │ $0.0003  │ 1.5s        │ $0.0009    │     │
│ qwen-max         │ 100%      │ $0.0040  │ 3.2s        │ $0.0120    │     │
│ glm-5            │ 100%      │ $0.0025  │ 2.8s        │ $0.0075    │     │
│ glm-4.5          │ 33%       │ $0.0015  │ 2.0s        │ $0.0045    │     │
└──────────────────┴───────────┴──────────┴─────────────┴────────────┴─────┘

Recommendation: glm-4.5-flash ($0.0000/run, 100% pass rate)
```

*(Example output — actual results depend on model behavior.)*

### Step 5: Investigate Failures

For models that didn't achieve 100%, check the trial diffs:

```bash
cat sample-tasks/invoice-extraction/.skilleval/run-*/trials/glm-4.5/trial-1/diff.txt
```

This shows exactly where the output diverged from expected.

### Step 6: Iterate

If no model achieves 100%, improve your `skill.md`:
- Add more explicit formatting rules.
- Include edge case handling.
- Provide examples in the prompt.

Then re-run the evaluation.

---

## 21. Troubleshooting / FAQ

### "No models available"

**Cause:** No API key environment variables are set.

**Fix:** SkillEval now shows the exact `export` commands you need. Run `skilleval catalog` to see all models and the env var each one requires.

### "Mode 1 requires skill.md in the task folder"

**Cause:** You ran `skilleval run` but the task folder doesn't contain `skill.md`.

**Fix:** Create `skill.md` with the system prompt for your task. If you want auto-generated skills, use Mode 2 (`matrix`) or Mode 3 (`chain`) instead.

### "Mode 2/3 requires prompt.md in the task folder"

**Cause:** You ran `matrix` or `chain` but the task folder is missing `prompt.md`.

**Fix:** Create `prompt.md` with a human-readable description of the task.

### "Meta-skill 'X' not found"

**Cause:** The `--meta-skills` name doesn't match any `meta-skill-*.md` file.

**Fix:** Ensure your file is named `meta-skill-<name>.md` (e.g., `meta-skill-concise.md` for `--meta-skills concise`). Check available variants:
```bash
ls my-task/meta-skill-*.md
```

### Empty or Truncated Responses

**Symptoms:** Trials fail with empty output or `finish_reason: "length"`.

**Causes and fixes:**
- **Silent rate limiting:** The provider returns an empty response instead of a 429. SkillEval detects this and retries up to 3 times. If it persists, reduce `--parallel` or wait before retrying.
- **Output truncation:** The model's response exceeded `max_tokens`. Increase `max_tokens` in `config.yaml`.
- **Timeout:** The request took longer than `timeout` seconds. Increase `timeout` in `config.yaml`.

### Rate Limit Errors (429)

**Cause:** Too many concurrent requests to a provider.

**Fix:** SkillEval has built-in two-level concurrency control (global + per-provider). If you still hit rate limits:
1. Reduce `--parallel` (e.g., `--parallel 5`).
2. The engine automatically applies exponential backoff (1s, 2s, 4s) with jitter on 429 responses, retrying up to 3 times.

### JSON Comparison Fails Despite Correct Values

**Possible causes:**
- **Integer vs float:** `json_exact` normalizes integers to floats, so `150` and `150.0` match. But `"150"` (string) does not match `150` (number).
- **Extra fields:** `json_exact` requires an exact match. If the model outputs extra fields, use `field_subset` instead.
- **Key ordering:** This is not an issue — SkillEval canonicalizes key order before comparison.

### PDF/DOCX/XLSX Files Not Working

**Cause:** Optional dependencies not installed.

**Fix:**
```bash
pip install -e ".[docs]"
# Or individually:
pip install pdfplumber python-docx openpyxl
```

### Cost Calculation

Cost is computed as:

```
cost = (input_tokens / 1,000,000 x input_cost_per_m)
     + (output_tokens / 1,000,000 x output_cost_per_m)
```

Token counts come from the API response's `usage` field. Costs are approximate since pricing comes from the model catalog, which may be slightly outdated.

### Recommendation Logic

SkillEval recommends the **cheapest model that achieves a 100% pass rate** across all trials. The `recommendation` field in `results.json` is set to the cheapest 100%-pass model, or `null` if none qualify. When displaying results, if no model reaches 100%, SkillEval prints the best pass rate achieved and suggests improving the skill or increasing trials.

If fewer than 10 trials were run, the recommendation includes a warning that confidence may be low.

### How Many Trials Should I Run?

- **3–5 trials** — Quick screening to identify promising models.
- **10–20 trials** — Production confidence. Catches intermittent failures.
- **50+ trials** — Statistical rigor for mission-critical tasks.

Use `temperature: 0.0` for deterministic tasks. Even at temperature 0, models can occasionally produce different outputs due to batching or internal non-determinism, which is why multiple trials matter.

### "Unknown config keys" warning

**Cause:** Your `config.yaml` contains keys that SkillEval doesn't recognize (likely typos).

**Fix:** Check the warning message for the list of valid keys: `comparator`, `custom_script`, `trials`, `timeout`, `temperature`, `max_tokens`, `output_format`.

### Circuit breaker messages

**Cause:** A provider had 5 consecutive failures (errors, timeouts, or empty responses). SkillEval automatically skips remaining trials for that provider to avoid wasting time and money.

**Fix:** Check the provider's status page. If the issue is rate limiting, reduce `--parallel`. The circuit breaker resets on the next successful response.

### Getting machine-readable output

Use `--json` on any command to get JSON output suitable for piping:

```bash
skilleval run my-task --json | jq '.recommendation'
skilleval catalog --json | jq '.[] | select(.available) | .name'
```

### Debugging with verbose mode

Use `-v` for INFO-level logs (shows API request URLs, retry attempts) or `-vv` for DEBUG-level logs (full request/response details). Logs go to stderr so they don't interfere with `--json` output:

```bash
skilleval -vv run my-task --json 2>debug.log | jq .
```
