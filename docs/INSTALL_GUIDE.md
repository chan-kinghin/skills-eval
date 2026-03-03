# SkillEval Installation Guide

[English](INSTALL_GUIDE.md) | [中文](INSTALL_GUIDE_ZH.md)

> Find the cheapest LLM that gets your task 100% right.

---

## 1. Prerequisites

- **Python 3.11 or later** (uses `str | None` union syntax)
- **pip** (included with Python 3.11+)

Check your Python version:

```bash
python3 --version
# Python 3.11.0 or higher required
```

If you need to install Python 3.11+, visit [python.org/downloads](https://www.python.org/downloads/) or use your package manager:

```bash
# macOS (Homebrew)
brew install python@3.12

# Ubuntu/Debian
sudo apt install python3.12

# Windows (winget)
winget install Python.Python.3.12
```

---

## 2. Installation

```bash
pip install skilleval
```

Verify it worked:

```bash
skilleval --version
```

### Optional: Document Extraction Support

To process PDF, Word, and Excel input files:

```bash
pip install "skilleval[docs]"
```

This adds `pdfplumber`, `python-docx`, and `openpyxl`.

---

## 3. Quick Setup

### Set API Keys

SkillEval needs at least one provider API key. Set the ones you have:

```bash
# Qwen (Alibaba DashScope)
export DASHSCOPE_API_KEY="sk-..."

# GLM (Zhipu AI)
export ZHIPU_API_KEY="..."

# MiniMax
export MINIMAX_API_KEY="..."

# OpenAI (optional)
export OPENAI_API_KEY="sk-..."

# DeepSeek (optional)
export DEEPSEEK_API_KEY="..."
```

Add these to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.) so they persist across sessions.

### Verify Models Are Available

```bash
skilleval catalog
```

Models with a valid API key show as **Ready**. Models without a key show as **No Key**. You need at least one Ready model to run evaluations.

---

## 4. Your First Evaluation

Let's walk through a complete example: extracting an invoice number from a text document.

### Step 1: Scaffold a Task

```bash
skilleval init invoice-demo
```

This creates:

```
invoice-demo/
├── config.yaml
├── skill.md
├── prompt.md
├── meta-skill.md
├── input/
│   └── sample.txt
└── expected/
    └── sample.txt
```

### Step 2: Create an Input File

Replace the placeholder with your actual input:

```bash
cat > invoice-demo/input/invoice.txt << 'EOF'
INVOICE
Company: Acme Corp
Invoice Number: INV-2026-0042
Date: 2026-03-01
Amount: $1,250.00

Items:
- Widget A (x10): $500.00
- Widget B (x5): $750.00

Payment Terms: Net 30
EOF
```

Remove the placeholder:

```bash
rm invoice-demo/input/sample.txt
```

### Step 3: Create the Expected Output

```bash
cat > invoice-demo/expected/invoice.txt << 'EOF'
{"invoice_number": "INV-2026-0042", "company": "Acme Corp", "date": "2026-03-01", "total": 1250.00, "items": [{"name": "Widget A", "quantity": 10, "amount": 500.00}, {"name": "Widget B", "quantity": 5, "amount": 750.00}]}
EOF
```

Remove the placeholder:

```bash
rm invoice-demo/expected/sample.txt
```

### Step 4: Write the Skill (System Prompt)

Edit `invoice-demo/skill.md`:

```markdown
# Invoice Extraction

Extract structured data from the invoice text. Return a JSON object with these exact fields:

- `invoice_number` (string): The invoice ID
- `company` (string): The company name
- `date` (string): The invoice date in YYYY-MM-DD format
- `total` (number): The total amount as a number (no currency symbol)
- `items` (array): Each item with `name` (string), `quantity` (number), `amount` (number)

Return ONLY the JSON object. No markdown, no explanation, no code fences.
```

### Step 5: Configure the Comparator

Edit `invoice-demo/config.yaml`:

```yaml
comparator: json_exact
trials: 3
timeout: 60
temperature: 0.0
max_tokens: 4096
output_format: json
```

### Step 6: Run the Evaluation

```bash
skilleval run invoice-demo
```

SkillEval sends your skill + input to every available model, 3 times each, and compares every response against your expected output.

---

## 5. Understanding Results

After a run, SkillEval displays a table like this:

```
┌──────────────────┬───────────┬──────────┬─────────────┬────────────┬─────┐
│ Model            │ Pass Rate │ Avg Cost │ Avg Latency │ Total Cost │ Rec │
├──────────────────┼───────────┼──────────┼─────────────┼────────────┼─────┤
│ glm-4.5-flash    │ 100%      │ $0.0000  │ 1.8s        │ $0.0000    │  *  │
│ qwen-turbo       │ 100%      │ $0.0001  │ 1.1s        │ $0.0003    │     │
│ qwen-plus        │ 67%       │ $0.0008  │ 1.9s        │ $0.0024    │     │
└──────────────────┴───────────┴──────────┴─────────────┴────────────┴─────┘

Recommendation: glm-4.5-flash ($0.0000/run, 100% pass rate)
```

| Column | Meaning |
|--------|---------|
| **Pass Rate** | Fraction of trials that matched expected output exactly |
| **Avg Cost** | Average cost per trial in USD |
| **Avg Latency** | Average response time per trial |
| **Total Cost** | Sum of all trial costs for this model |
| **Rec** | `*` marks the recommended model |

**Recommendation logic**: SkillEval picks the cheapest model with a 100% pass rate. If no model hits 100%, no recommendation is given -- improve your skill and re-run.

Results are saved to `invoice-demo/.skilleval/run-<timestamp>/` for later review.

---

## 6. Three Evaluation Modes

### Mode 1: Skill Evaluation (`run`)

You write the prompt. SkillEval tests it across models.

```bash
skilleval run my-task
skilleval run my-task --models qwen-turbo,glm-4.5-flash --trials 10
```

**Use when**: You already have a good prompt and want to find the cheapest model.

### Mode 2: Matrix Evaluation (`matrix`)

Creator models write the prompt. Executor models run it. Results form a matrix.

```bash
skilleval matrix my-task \
  --creators qwen-max,glm-5 \
  --executors qwen-turbo,glm-4.5-flash
```

**Use when**: You want to explore whether a cheaper model can write a good prompt for an even cheaper executor.

**Requires**: `prompt.md` (task description) instead of `skill.md`.

### Mode 3: Chain Evaluation (`chain`)

A meta-skill guides how the creator writes the prompt, adding another layer of optimization.

```bash
skilleval chain my-task \
  --meta-skills concise,detailed \
  --creators qwen-max \
  --executors qwen-turbo,glm-4.5-flash
```

**Use when**: You want to test different prompting strategies for prompt generation.

**Requires**: `prompt.md` and `meta-skill-<name>.md` files.

---

## 7. Advanced Usage

### JSON Output for Piping

Any command supports `--output json` (or the `--json` shorthand) for machine-readable output:

```bash
skilleval run my-task --output json | jq '.recommendation'
skilleval catalog --json | jq '.[] | select(.available) | .name'
```

CSV output is also available for `run`, `matrix`, and `chain`:

```bash
skilleval run my-task --output csv > results.csv
```

### Custom OpenAI-Compatible Endpoints

Test any model without editing the catalog:

```bash
# Local Ollama model
skilleval run my-task \
  --endpoint http://localhost:11434/v1 \
  --model-name llama3 \
  --api-key ""

# OpenAI GPT-4o
skilleval run my-task \
  --endpoint https://api.openai.com/v1 \
  --api-key $OPENAI_API_KEY \
  --model-name gpt-4o
```

### HTML Reports

Generate a self-contained HTML report from any previous run:

```bash
skilleval report my-task/.skilleval/run-20260301-120000 --html report.html --open
```

### Compare Two Runs

After tweaking your skill, compare results:

```bash
skilleval compare \
  my-task/.skilleval/run-20260301-120000 \
  my-task/.skilleval/run-20260302-090000
```

Shows per-model pass rate deltas (improved, regressed, unchanged).

### Verbose / Debug Mode

```bash
skilleval -v run my-task      # INFO-level logs
skilleval -vv run my-task     # DEBUG-level logs (full request/response)
```

Logs go to stderr, so they do not interfere with `--json` output:

```bash
skilleval -vv run my-task --output json 2>debug.log | jq .
```

---

## 8. Configuration Reference

Each task folder has a `config.yaml` controlling evaluation behavior.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `comparator` | string | `json_exact` | How to compare output vs expected |
| `custom_script` | string | `null` | Path to custom comparator script |
| `trials` | int | `5` | Number of trials per model |
| `timeout` | int | `60` | API request timeout (seconds) |
| `temperature` | float | `0.0` | Sampling temperature (`0.0` = deterministic) |
| `max_tokens` | int | `4096` | Max output tokens per request |
| `output_format` | string | `json` | Expected output format (for display) |

### Comparators

| Comparator | Description |
|------------|-------------|
| `json_exact` | Deep JSON equality (default). Normalizes int/float. Exact key match. |
| `csv_ordered` | Row-by-row CSV comparison. Order matters. |
| `csv_unordered` | Set-based CSV comparison. Order does not matter. |
| `field_subset` | Checks expected fields exist in output. Extra fields allowed. |
| `file_hash` | Byte-identical SHA-256 comparison. |
| `custom` | Runs a user script. Requires `custom_script` in config. |

### Example config.yaml

```yaml
comparator: json_exact
trials: 10
timeout: 120
temperature: 0.0
max_tokens: 8192
output_format: json
```

---

## 9. Troubleshooting

### "No models available"

No API keys are set. Run `skilleval catalog` to see which environment variables are needed, then export at least one:

```bash
export ZHIPU_API_KEY="your-key-here"
```

### Python version error

SkillEval requires Python 3.11+. Check with `python3 --version`. If you have multiple versions, use:

```bash
python3.12 -m pip install skilleval
```

### Network / timeout errors

- Increase `timeout` in `config.yaml` (default: 60 seconds)
- Reduce `--parallel` if hitting rate limits (default: 20)
- Check provider status pages for outages

### JSON comparison fails but output looks correct

- `json_exact` requires all keys to match. Extra keys in output cause failure. Use `field_subset` if extra keys are acceptable.
- String `"150"` does not match number `150`. Check your expected output types.

### PDF/DOCX/XLSX files not working

Install the optional docs dependencies:

```bash
pip install "skilleval[docs]"
```

### Empty responses

- The model may be rate-limited silently. Reduce `--parallel`.
- Check `finish_reason` in trial results -- `length` means output was truncated. Increase `max_tokens`.

---

## 10. Upgrading

```bash
pip install --upgrade skilleval
```

Check the new version:

```bash
skilleval --version
```

---

## 11. Uninstalling

```bash
pip uninstall skilleval
```

This removes the `skilleval` CLI and Python package. Your task folders and results are not affected.

---

## Links

- **GitHub**: [github.com/chan-kinghin/skills-eval](https://github.com/chan-kinghin/skills-eval)
- **PyPI**: [pypi.org/project/skilleval](https://pypi.org/project/skilleval/)
- **Full User Manual**: [docs/USER_MANUAL.md](USER_MANUAL.md)
- **Issues**: [github.com/chan-kinghin/skills-eval/issues](https://github.com/chan-kinghin/skills-eval/issues)
