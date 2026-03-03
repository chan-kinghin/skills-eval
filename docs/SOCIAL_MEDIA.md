# SkillEval Social Media Posts

Ready-to-post content for each platform. Adapt as needed.

---

## Twitter/X Thread

**Tweet 1 (Hook):**

You are probably spending 10-100x too much on LLM API calls for routine tasks.

I built an open-source tool that tests 10 models in parallel and finds the cheapest one that gets your task 100% right.

It is called SkillEval. Here is how it works:

**Tweet 2:**

The problem: for deterministic tasks (data extraction, formatting, structured output), the "best" model is the cheapest one that works.

But nobody tests this systematically. They pick GPT-4 or Claude and move on.

SkillEval automates the comparison.

**Tweet 3:**

How it works:
- You provide input files + expected output + a prompt
- SkillEval runs it across all models in parallel
- Compares outputs against ground truth
- Recommends the cheapest model at 100% accuracy

5 trials per model, real cost tracking, circuit breaker for flaky APIs.

**Tweet 4:**

Default catalog: 10 models from 3 providers (Qwen, GLM, MiniMax).

Price range: FREE (glm-4.5-flash) to $6.40/M output tokens (qwen-max).

Spoiler: the free model often wins on simple extraction tasks.

Also works with any OpenAI-compatible API via --endpoint flag.

**Tweet 5:**

Three evaluation modes:
1. Run -- you write the prompt, tool tests it
2. Matrix -- one model writes the prompt, another runs it
3. Chain -- meta-prompt guides prompt creation + execution

Plus: HTML reports, JSON output for CI/CD, run comparison, Ctrl+C saves partial results.

**Tweet 6:**

MIT licensed, Python 3.11+, install in 30 seconds:

```
pip install -e .
skilleval init my-task
skilleval run my-task/
```

GitHub: https://github.com/chan-kinghin/skills-eval

Star it if you think model selection should be data-driven, not vibes-driven.

---

## LinkedIn Post

**Stop guessing which LLM to use for production tasks.**

When teams adopt LLMs for document processing, data extraction, or structured output generation, they typically pick a model based on benchmarks or recommendations -- then never revisit that decision. The result: overpaying by 10-100x for tasks that cheaper (or even free) models handle perfectly.

I built SkillEval to solve this. It is an open-source CLI tool that automates LLM model selection for deterministic tasks.

You provide input files, expected output, and a prompt. SkillEval runs the task across multiple models in parallel, compares every output against your ground truth, and recommends the cheapest model that achieves 100% accuracy.

The default catalog includes 10 models from 3 providers (Alibaba's Qwen, Zhipu AI's GLM, and MiniMax), ranging from free to $6.40/M output tokens. It also supports any OpenAI-compatible API, so you can test local models, OpenAI, or any other provider alongside the default catalog.

Key technical features:
- Parallel execution with per-provider rate limiting and circuit breaker
- Six built-in comparators (JSON, CSV, field subset, file hash, regex, custom script)
- Three evaluation modes from simple prompt testing to full pipeline evaluation
- JSON output for CI/CD integration, HTML reports for stakeholders
- Ctrl+C saves partial results; no work is ever lost

For teams running LLM tasks at volume, even a small cost reduction per call compounds into significant savings. SkillEval makes that optimization systematic instead of manual.

MIT licensed. Python 3.11+.

https://github.com/chan-kinghin/skills-eval

---

## Reddit Post (r/MachineLearning or r/LocalLLaMA)

**Title:** I built an open-source tool to find the cheapest LLM that gets your task 100% right

**Body:**

I have been working on a CLI tool called SkillEval that automates LLM model selection for deterministic tasks (data extraction, document processing, structured output).

The idea is simple: you provide input files, expected output, and a prompt. The tool runs your task across multiple models in parallel, compares outputs against ground truth, and tells you which model is cheapest at 100% accuracy.

**Why I built it:** I kept seeing teams use expensive frontier models for simple extraction tasks that cheaper models handle perfectly. Nobody tests this systematically because it is tedious. So I automated it.

**What it does:**
- Tests 10 models across 3 Chinese cloud providers (Qwen/DashScope, GLM/Zhipu, MiniMax) by default
- Also works with any OpenAI-compatible API via `--endpoint` flag (Ollama, OpenAI, etc.)
- Runs trials in parallel with rate limiting and circuit breaker
- Six built-in comparators (json_exact, csv, field_subset, file_hash, custom script)
- Three modes: simple run, creator-executor matrix, and full chain evaluation
- JSON output for CI/CD, HTML reports for sharing

**Price range in default catalog:** Free (glm-4.5-flash) to $6.40/M output tokens (qwen-max). In my testing, the free or budget-tier models often pass on simple extraction tasks.

```bash
pip install -e .
skilleval init my-task
# add input files, expected output, edit skill.md
skilleval run my-task/
```

Python 3.11+, MIT licensed: https://github.com/chan-kinghin/skills-eval

Would appreciate feedback, especially on:
- What comparators would be useful to add
- Whether the three evaluation modes make sense
- Interest in adding more providers to the default catalog

---

## Hacker News

**Title:** Show HN: SkillEval -- Find the cheapest LLM that gets your task 100% right

**Description:**

SkillEval is a CLI tool that automates LLM model selection for deterministic tasks. You provide input files, expected output, and a prompt. It runs your task across 10 models in parallel, compares outputs against ground truth using pluggable comparators (JSON, CSV, field subset, file hash, custom script), and recommends the cheapest model at 100% accuracy.

Default catalog covers 3 Chinese cloud providers (Qwen, GLM, MiniMax) with models from free to $6.40/M output. The --endpoint flag works with any OpenAI-compatible API.

Three evaluation modes: (1) you write the prompt, tool tests it across models; (2) one model writes the prompt, another executes; (3) meta-prompt guides prompt creation then execution.

Built with Python 3.11+, async HTTP with circuit breaker, Ctrl+C saves partial results, --json for CI/CD. MIT licensed.

https://github.com/chan-kinghin/skills-eval

---

## Product Hunt

**Tagline:** Find the cheapest LLM that gets your task 100% right.

**Description:**

SkillEval is an open-source CLI tool that automates LLM model selection for deterministic tasks like data extraction, document processing, and structured output generation.

Give it your input files, expected output, and a prompt. It tests 10+ models in parallel across multiple providers, compares every output against your ground truth, and recommends the cheapest model that achieves 100% accuracy. Includes real cost tracking, parallel execution, CI/CD integration, and HTML reports.

Stop overpaying for LLM API calls. Let the data pick your model.
