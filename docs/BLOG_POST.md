# Stop Overpaying for LLMs: How SkillEval Finds the Cheapest Model That Actually Works

**You are probably spending 10-100x more than you need to on LLM API calls. Here is how to fix that.**

---

## The Problem Nobody Talks About

If you use LLMs for production tasks -- extracting data from invoices, formatting structured output, parsing documents -- you have probably picked a model based on vibes. Maybe you tried GPT-4o because it is popular. Maybe you went with Claude because a blog post said it was good at structured output. Maybe you just picked the most expensive option and hoped for the best.

Here is the thing: for deterministic tasks where you need a specific, verifiable output, the cheapest model that works is the right model. Not the smartest. Not the most popular. The cheapest one that gets it right 100% of the time.

But finding that model means testing each one manually, comparing outputs, tracking costs, and repeating this every time you change your prompt. It is tedious, error-prone, and nobody does it thoroughly.

That is why I built SkillEval.

## What SkillEval Does

SkillEval is an open-source CLI tool that automates LLM model selection for deterministic tasks. You give it:

1. Input files (the data your model processes)
2. Expected output (what a correct result looks like)
3. A prompt (the instructions for the model)

It runs your task across multiple models in parallel, compares every output against your expected result, and tells you which model is cheapest at 100% accuracy.

```bash
pip install skilleval
export DASHSCOPE_API_KEY="sk-..."
skilleval init my-task
# Add your input files, expected output, and prompt
skilleval run my-task/
```

Five commands. You get a ranked table of every model, their pass rates, costs, and latencies -- with a clear recommendation at the bottom.

## A Concrete Example

Say you need to extract structured data from invoices. You write a prompt, drop an invoice into the `input/` folder, put the expected JSON in `expected/`, and run:

```bash
skilleval run invoice-extraction/
```

SkillEval tests 10 models across 3 providers, running 5 trials each (50 API calls total), all in parallel. A few seconds later:

```
Model              Pass Rate   Avg Cost   Avg Latency
qwen-turbo         100%        $0.0001    1.2s         *
glm-4.5-flash      100%        $0.0000    2.1s         *
qwen-plus          100%        $0.0008    1.8s
qwen-max           100%        $0.0040    3.2s
glm-4.5-air        67%         $0.0003    1.5s

Recommendation: glm-4.5-flash ($0.0000/run, 100% pass rate)
```

In this case, a free-tier model (glm-4.5-flash) does the job perfectly. You were about to use qwen-max at $6.40 per million output tokens. That is not a rounding error -- it is a 100x cost difference on a task that a free model handles correctly.

## Three Ways to Evaluate

SkillEval supports three evaluation modes, each adding a layer of automation:

**Mode 1 -- Run.** You write the prompt. SkillEval tests it across all models. This is the most common workflow: you have a working prompt and want to find the cheapest model that can execute it.

**Mode 2 -- Matrix.** You describe the task in plain language. One set of models writes the prompt, another set executes it. SkillEval tests every creator-executor combination and shows you a heatmap of what works. Useful when you are not sure your prompt is optimal.

**Mode 3 -- Chain.** You write a meta-prompt that guides how prompts should be written. A creator model follows your meta-prompt to generate a task prompt, then an executor runs it. This is for teams that want to systematize their prompt engineering across many tasks.

## What Makes It Different

**Parallel execution with safety nets.** SkillEval runs all API calls concurrently with per-provider rate limiting. A circuit breaker automatically skips providers that are failing (after 5 consecutive errors), so a single flaky API does not stall your entire evaluation. Press Ctrl+C mid-run and it saves partial results instead of throwing them away.

**Real cost tracking.** Every API call logs input tokens, output tokens, and cost. The default catalog includes 10 models from 3 providers, with pricing from free (glm-4.5-flash at $0.00) to premium (qwen-max at $6.40/M output tokens). You see exactly what each model costs for your specific task.

**Strict accuracy, not benchmarks.** SkillEval does not use MMLU scores or chatbot arena rankings. It runs your actual task with your actual data and checks whether the output matches your expected result exactly. Six built-in comparators handle JSON, CSV, file hashes, field subsets, and custom scripts. If you need 100% accuracy, you test for 100% accuracy.

**Works with any OpenAI-compatible API.** The default catalog covers Qwen, GLM, and MiniMax, but the `--endpoint` flag lets you test any model with an OpenAI-compatible API -- including local models via Ollama, OpenAI itself, or any other provider.

```bash
# Test a local Ollama model alongside cloud models
skilleval run my-task \
  --endpoint http://localhost:11434/v1 \
  --model-name llama3 \
  --api-key ""
```

**CI/CD ready.** Every command supports `--json` output for piping into scripts. Run evaluations in your CI pipeline and fail the build if your cheapest model changes or accuracy drops.

## Getting Started

```bash
# Install
pip install skilleval

# Set up a provider (pick at least one)
export DASHSCOPE_API_KEY="sk-..."   # Qwen
export ZHIPU_API_KEY="..."          # GLM (includes a free model)
export MINIMAX_API_KEY="..."        # MiniMax

# See what is available
skilleval catalog

# Create and run your first task
skilleval init my-extraction-task
# Edit input/, expected/, and skill.md
skilleval run my-extraction-task/
```

The [User Manual](https://github.com/chan-kinghin/skills-eval/blob/main/docs/USER_MANUAL.md) covers everything from task setup to advanced features like HTML report generation and run comparison.

## Who Is This For?

- **Teams using LLMs for document processing.** If you run the same extraction or formatting task thousands of times, model cost matters. SkillEval finds the cheapest model that works.
- **Developers building LLM pipelines.** Integrate `skilleval run --json` into your CI to catch accuracy regressions and cost increases automatically.
- **Anyone curious about the Chinese LLM ecosystem.** The default catalog covers 10 models from Alibaba, Zhipu AI, and MiniMax -- providers that are competitive on price and quality but less known outside China.

## Try It

SkillEval is MIT-licensed and available on GitHub:

**https://github.com/chan-kinghin/skills-eval**

If it saves you money or time, consider starring the repo. If you find a bug or want to add a provider, PRs are welcome -- adding a new model is just a YAML entry, no code changes needed.

The cheapest model that works is the right model. Now you have a tool to find it.
