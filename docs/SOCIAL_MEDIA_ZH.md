# SkillEval 社交媒体发布内容

> 即可发布的中文社交媒体内容合集。根据平台选择对应内容，按需微调后发布。

---

## 微博 / Twitter

### 帖子 1（钩子）

你的大模型任务可能在用 $6.40/M tokens 的旗舰模型，但免费模型就能 100% 做对。问题是你没测过。

开源了一个 CLI 工具 SkillEval，自动帮你找到最便宜的 100% 准确率模型。原生支持通义千问、智谱 GLM、MiniMax，10 个模型并行测试。

GitHub: https://github.com/chan-kinghin/skills-eval

#大模型 #LLM #开源 #降本增效

### 帖子 2（技术向）

做了个开源工具 SkillEval，解决一个很具体的问题：确定性任务（文档提取、数据格式化）该用哪个大模型？

原理：你提供输入 + 预期输出 + 提示词，它并行跑 10 个模型，自动对比结果，推荐最便宜的 100% 通过率模型。

支持 JSON 精确匹配、CSV、子集匹配等 6 种比较策略。带熔断、重试、Ctrl+C 保存。

https://github.com/chan-kinghin/skills-eval

### 帖子 3（场景向）

每次换一个文档处理任务，就要重新试一遍各个大模型，看哪个又便宜又准？

SkillEval 把这个过程自动化了：一条命令测 10 个国产大模型，自动对比输出，告诉你最便宜的 100% 准确率选项。开箱支持 DashScope / 智谱 / MiniMax。

MIT 开源，Python CLI，5 分钟上手 👇
https://github.com/chan-kinghin/skills-eval

### 帖子 4（数据向）

国内大模型 API 定价差多少？

- glm-4.5-flash: 免费
- qwen-turbo: 输出 $0.20/M tokens
- qwen-max: 输出 $6.40/M tokens

差 32 倍。但很多任务，便宜的模型就够了。关键是要测。

SkillEval 帮你自动测：https://github.com/chan-kinghin/skills-eval

---

## 知乎回答 / 文章开头

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

---

## V2EX 帖子

### 标题

SkillEval：开源 CLI，自动找到最便宜的 100% 准确率大模型（原生支持通义千问/智谱/MiniMax）

### 正文

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

---

## 掘金 / InfoQ 摘要

> 用于技术文章发布时的摘要字段（100-150 字）。

SkillEval 是一个开源 Python CLI 工具，帮助开发者找到确定性任务上最便宜的 100% 准确率大模型。它原生支持通义千问（DashScope）、智谱 GLM、MiniMax 三家国内厂商，默认覆盖 10 个模型。提供输入文件和预期输出后，SkillEval 并行测试所有模型，自动对比结果，推荐最具性价比的选项。支持 JSON/CSV/子集等 6 种比较策略，带熔断机制、HTML 报告和 CI/CD 集成。MIT 开源。

---

## 微信公众号推送标题

### 方案 A（痛点切入）

**大模型 API 每月账单太高？因为你没测过便宜模型够不够用**

### 方案 B（数据切入）

**免费模型 vs $6.40/M tokens 旗舰模型：我们用工具测了 10 个国产大模型，结果意外**

### 方案 C（工具切入）

**开源工具 SkillEval：一条命令找到最便宜的 100% 准确率大模型**
