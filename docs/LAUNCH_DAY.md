# Product Hunt Launch Day Playbook

Single reference for SkillEval's Product Hunt launch. Everything you need in one place.

---

## Product Hunt Listing Details

| Field | Value |
|-------|-------|
| Name | SkillEval |
| Tagline | Find the cheapest LLM that gets your task 100% right |
| Description | SkillEval is an open-source CLI tool that automates LLM model selection for deterministic tasks like data extraction, document processing, and structured output generation. Give it your input files, expected output, and a prompt. It tests 10+ models in parallel across multiple providers, compares every output against your ground truth, and recommends the cheapest model that achieves 100% accuracy. Includes real cost tracking, parallel execution, CI/CD integration, and HTML reports. Stop overpaying for LLM API calls. Let the data pick your model. |
| Topics | Developer Tools, Open Source, Artificial Intelligence, CLI |
| Website | https://github.com/chan-kinghin/skills-eval |
| Pricing | Free |

---

## Maker Comment

Hey Product Hunt! 👋 I'm King, the maker of SkillEval.

**The backstory:** I kept seeing teams (including my own) use GPT-4 or Claude for simple extraction tasks — pulling fields from invoices, formatting structured output — without ever testing whether a cheaper model could do the same job. The answer was almost always yes, sometimes by 100x.

The problem is that nobody tests this systematically because it's tedious: you have to call each API, compare outputs, track costs, and repeat for every prompt change.

**So I automated it.** SkillEval runs your task across 10+ models in parallel, compares every output against your expected result, and tells you which model is cheapest at 100% accuracy.

**A real example:** For an invoice data extraction task, I was about to use qwen-max ($6.40/M output tokens). SkillEval found that glm-4.5-flash — a free-tier model — passed 100% of the time. That's not a rounding error.

**What makes it different:**
- Tests with your actual data, not benchmarks
- 6 built-in comparators (JSON, CSV, field subset, file hash, custom script)
- Works with any OpenAI-compatible API (cloud or local via Ollama)
- `--json` output for CI/CD — fail your build if accuracy drops
- Ctrl+C saves partial results, circuit breaker skips flaky APIs

It's MIT licensed, Python 3.11+, and installs in one line: `pip install skilleval`

Would love your feedback — especially on what comparators or providers to add next. Happy to answer any questions here!

---

## Twitter/X Thread

> **Note:** Post tweet 1 with the PH link. Add 🔗 Product Hunt link at the end of tweet 6.

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
pip install skilleval
skilleval init my-task
skilleval run my-task/
```

GitHub: https://github.com/chan-kinghin/skills-eval

Star it if you think model selection should be data-driven, not vibes-driven.

🔗 [Product Hunt link here]

---

## LinkedIn Post

> **Note:** Include PH link at the bottom.

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

```
pip install skilleval
```

https://github.com/chan-kinghin/skills-eval

---

## Hacker News

> **Note:** DO NOT mention Product Hunt on HN.

**Title:** Show HN: SkillEval -- Find the cheapest LLM that gets your task 100% right

**Description:**

SkillEval is a CLI tool that automates LLM model selection for deterministic tasks. You provide input files, expected output, and a prompt. It runs your task across 10 models in parallel, compares outputs against ground truth using pluggable comparators (JSON, CSV, field subset, file hash, custom script), and recommends the cheapest model at 100% accuracy.

Default catalog covers 3 Chinese cloud providers (Qwen, GLM, MiniMax) with models from free to $6.40/M output. The --endpoint flag works with any OpenAI-compatible API.

Three evaluation modes: (1) you write the prompt, tool tests it across models; (2) one model writes the prompt, another executes; (3) meta-prompt guides prompt creation then execution.

Built with Python 3.11+, async HTTP with circuit breaker, Ctrl+C saves partial results, --json for CI/CD. MIT licensed.

```bash
pip install skilleval
```

https://github.com/chan-kinghin/skills-eval

---

## Reddit Posts

> **Note:** Stagger posts by 2-4 hours. Subreddits: r/MachineLearning, r/Python, r/LocalLLaMA

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
pip install skilleval
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

## Chinese Platforms (Days 2-3)

> **Platforms:** V2EX, Juejin (掘金), Zhihu (知乎)

### V2EX

**标题：** SkillEval：开源 CLI，自动找到最便宜的 100% 准确率大模型（原生支持通义千问/智谱/MiniMax）

**正文：**

做了一个开源 CLI 工具，解决一个日常痛点：确定性任务（发票提取、数据格式化、结构化输出）应该用哪个大模型？

**背景：** 国内大模型定价差异很大。glm-4.5-flash 免费，qwen-max 输出 $6.40/M tokens，差 32 倍。但很多任务用便宜模型就够了，关键是你得测。

**SkillEval 做的事：** 你提供输入文件 + 预期输出 + 提示词，它并行跑所有模型，自动对比结果与标准答案，推荐最便宜的 100% 通过率模型。

**技术栈：** Python 3.11+，Click CLI，aiohttp 异步并行，Pydantic 数据模型，Rich 终端 UI。

**功能：**
- 3 种评估模式（你写提示词 / 模型写提示词 / 链式流水线）
- 6 种比较器（json_exact、csv、field_subset、regex、file_hash、custom）
- 原生支持通义千问（DashScope）、智谱 GLM、MiniMax
- 任何 OpenAI 兼容 API 也行（--endpoint 参数）
- 熔断机制、Ctrl+C 保存部分结果、HTML 报告、--json 接 CI/CD
- 进度条带 ETA、友好错误提示

**快速开始：**

```bash
pip install skilleval
export DASHSCOPE_API_KEY="sk-..."
skilleval init my-task
# 编辑 input/、expected/、skill.md
skilleval run my-task
```

MIT 许可，欢迎 Star / Issue / PR。

GitHub: https://github.com/chan-kinghin/skills-eval

### 知乎

> 适合回答"如何降低大模型 API 成本""大模型选型怎么做""国产大模型哪个性价比高"等问题。

降低大模型 API 成本，核心不是砍功能，而是**选对模型**。

很多团队默认用旗舰模型跑所有任务，但实际上大量确定性任务（文档提取、数据格式化、结构化输出）根本不需要最贵的模型。问题是：怎么知道便宜的模型够不够用？手动测太慢，逐个对比不现实。

我最近开源了 [SkillEval](https://github.com/chan-kinghin/skills-eval)，专门解决这个问题。它是一个 Python CLI 工具，你提供输入文件、预期输出和提示词，它自动并行测试多个模型，逐一对比输出与标准答案，最后推荐达到 100% 准确率的最便宜模型。

几个关键点：
- **原生支持国内三大厂商**：通义千问（DashScope）、智谱 GLM、MiniMax，设置 API Key 就能跑
- **默认 10 个模型**，从免费（glm-4.5-flash）到旗舰（qwen-max，$6.40/M tokens）
- **6 种比较策略**：JSON 精确匹配、CSV、子集匹配、正则、文件哈希、自定义脚本
- **生产级特性**：熔断机制、并发控制、Ctrl+C 保存、JSON 输出接 CI/CD、HTML 报告
- 同时支持任何 OpenAI 兼容 API（本地 Ollama 也行）

实际使用中，我们发现很多任务在免费或低价模型上就能 100% 通过，完全不需要用旗舰模型。关键是你得有工具去系统地测，而不是靠直觉选。

### 掘金 / InfoQ 摘要

> 用于技术文章发布时的摘要字段（100-150 字）。

SkillEval 是一个开源 Python CLI 工具，帮助开发者找到确定性任务上最便宜的 100% 准确率大模型。它原生支持通义千问（DashScope）、智谱 GLM、MiniMax 三家国内厂商，默认覆盖 10 个模型。提供输入文件和预期输出后，SkillEval 并行测试所有模型，自动对比结果，推荐最具性价比的选项。支持 JSON/CSV/子集等 6 种比较策略，带熔断机制、HTML 报告和 CI/CD 集成。MIT 开源。

### 微信公众号推送标题

- **方案 A（痛点切入）：** 大模型 API 每月账单太高？因为你没测过便宜模型够不够用
- **方案 B（数据切入）：** 免费模型 vs $6.40/M tokens 旗舰模型：我们用工具测了 10 个国产大模型，结果意外
- **方案 C（工具切入）：** 开源工具 SkillEval：一条命令找到最便宜的 100% 准确率大模型

### 微博

**帖子 1（钩子）：**

你的大模型任务可能在用 $6.40/M tokens 的旗舰模型，但免费模型就能 100% 做对。问题是你没测过。

开源了一个 CLI 工具 SkillEval，自动帮你找到最便宜的 100% 准确率模型。原生支持通义千问、智谱 GLM、MiniMax，10 个模型并行测试。

GitHub: https://github.com/chan-kinghin/skills-eval

#大模型 #LLM #开源 #降本增效

**帖子 2（技术向）：**

做了个开源工具 SkillEval，解决一个很具体的问题：确定性任务（文档提取、数据格式化）该用哪个大模型？

原理：你提供输入 + 预期输出 + 提示词，它并行跑 10 个模型，自动对比结果，推荐最便宜的 100% 通过率模型。

支持 JSON 精确匹配、CSV、子集匹配等 6 种比较策略。带熔断、重试、Ctrl+C 保存。

https://github.com/chan-kinghin/skills-eval

---

## Visual Assets Checklist

- [ ] Logo/thumbnail (240x240 PNG) — simple terminal icon, flat design, dark bg
- [ ] Gallery image 1: Hero — tool name + tagline + `skilleval run` results table
- [ ] Gallery image 2: Catalog — `skilleval catalog` showing models with prices
- [ ] Gallery image 3: Three Modes — visual diagram of Run / Matrix / Chain
- [ ] Gallery image 4: HTML Report — screenshot of generated HTML report
- [ ] Gallery image 5: Cost Savings — before/after cost comparison
- [ ] GitHub social preview (1280x640) — reuse hero image, resized
- Recommended tools: carbon.now.sh or ray.so for terminal screenshots, Figma/Canva for logo

---

## Launch Day Timeline

1. PH listing goes live → post maker comment immediately
2. Share PH link on Twitter/X (use thread above)
3. Post on LinkedIn
4. Share in relevant Discord/Slack communities
5. Publish blog post on dev.to (link to PH in post)
6. Respond to EVERY PH comment within 30 minutes
7. Submit to Hacker News as Show HN (do NOT mention PH)
8. Stagger Reddit posts by 2-4 hours

---

## Post-Launch (Days 2-7)

- Day 2-3: Chinese platform launch (V2EX, Juejin, Zhihu)
- Day 2-3: Cross-post blog to Medium, Hashnode, SegmentFault
- Day 7: Check GitHub traffic/referrer stats, collect feature requests
