# SkillEval 用户手册

[English](USER_MANUAL.md) | [中文](USER_MANUAL_ZH.md)

> 找到能 100% 完成你任务的最便宜的大模型。

---

## 目录

1. [简介](#1-简介)
2. [安装](#2-安装)
3. [快速开始](#3-快速开始)
4. [核心概念](#4-核心概念)
5. [设置任务](#5-设置任务)
6. [模式 1：技能评估（`run`）](#6-模式-1技能评估)
7. [模式 2：矩阵评估（`matrix`）](#7-模式-2矩阵评估)
8. [模式 3：链式评估（`chain`）](#8-模式-3链式评估)
9. [临时端点](#9-临时端点)
10. [技能检查（`lint`）](#10-技能检查)
11. [技能测试（`skill-test`）](#11-技能测试)
12. [运行比较（`compare`）](#12-运行比较)
13. [HTML 报告](#13-html-报告)
14. [交互式 TUI 模式](#14-交互式-tui-模式)
15. [运行历史（`history`）](#15-运行历史)
16. [国际化（i18n）](#16-国际化)
17. [CLI 参考](#17-cli-参考)
18. [配置（`config.yaml`）](#18-配置)
19. [模型目录](#19-模型目录)
20. [支持的输入文件](#20-支持的输入文件)
21. [比较器](#21-比较器)
22. [结果与输出](#22-结果与输出)
23. [测试用例演练](#23-测试用例演练)
24. [示例演练](#24-示例演练)
25. [故障排除 / 常见问题](#25-故障排除--常见问题)

---

## 1. 简介

SkillEval 是一个 CLI 工具，帮助你找到在确定性任务上达到 **100% 准确率**的**最便宜的大语言模型**。不再需要逐个手动测试模型，SkillEval 自动化完成整个流程：将你的任务并行发送给多个模型，将输出与预期结果对比，并推荐最具性价比的选项。

### 问题

你有一个可重复的任务（例如从发票中提取结构化数据），想用大模型来自动化处理。很多模型都能胜任，但价格差异很大。你需要找到每次都能做对的最便宜的模型。

### 解决方案

SkillEval 将你的任务并行发送给多个模型，自动将每个输出与预期结果进行比较。它支持三种复杂度递增的评估模式：

- **模式 1** — 你编写提示词（skill），SkillEval 在多个模型上测试。
- **模式 2** — 一个模型编写提示词，另一个模型执行。
- **模式 3** — 链式：元技能指导提示词的创建，然后执行。

### 支持的供应商

| 供应商 | 平台 | 注册地址 |
|--------|------|---------|
| **通义千问** | 阿里云 / DashScope | https://dashscope.console.aliyun.com/ |
| **智谱 GLM** | 智谱 AI / BigModel | https://open.bigmodel.cn/ |
| **MiniMax** | MiniMax | https://platform.minimax.io/ |
| **OpenAI** | OpenAI | https://platform.openai.com/ |
| **DeepSeek** | 深度求索 | https://platform.deepseek.com/ |

所有供应商使用 OpenAI 兼容的 Chat Completion API。

---

## 2. 安装

### 环境要求

- **Python 3.11** 或更高版本（SkillEval 使用 `str | None` 联合类型语法）
- 至少一个供应商的 API 密钥

### 从 PyPI 安装（推荐）

```bash
pip install skilleval
```

### 从源码安装

```bash
# 克隆仓库
git clone <repo-url> && cd skills-eval

# 以可编辑模式安装
pip install -e .
```

### 安装文档提取支持

要处理 PDF、Word 和 Excel 输入文件，请安装可选的 `docs` 依赖：

```bash
pip install -e ".[docs]"
```

这会安装：
- `pdfplumber` — PDF 文本和表格提取
- `python-docx` — Word 文档提取
- `openpyxl` — Excel 电子表格提取

### 设置 API 密钥

为你要使用的供应商设置环境变量：

```bash
# 通义千问（DashScope）— 北京端点
export DASHSCOPE_API_KEY="sk-..."

# 智谱 GLM
export ZHIPU_API_KEY="..."

# MiniMax
export MINIMAX_API_KEY="..."

# OpenAI
export OPENAI_API_KEY="sk-..."

# DeepSeek
export DEEPSEEK_API_KEY="sk-..."
```

你只需要设置想要评估的供应商的密钥。SkillEval 会自动检测哪些密钥已设置，并据此过滤模型目录。

### 验证安装

```bash
skilleval --version
skilleval catalog
```

`catalog` 命令显示所有模型以及每个模型的状态：**Ready**（已找到 API 密钥）或 **No Key**（未设置密钥）。

---

## 3. 快速开始

本节将引导你使用内置的示例任务完成首次评估。

### 第 1 步：检查可用模型

```bash
skilleval catalog
```

确认至少有一个模型显示 **Ready**。

### 第 2 步：运行示例任务

```bash
skilleval run sample-tasks/invoice-extraction
```

这会使用默认设置（5 次试验、`json_exact` 比较器、temperature 0）在所有可用模型上运行发票提取任务。

### 第 3 步：查看结果

SkillEval 会打印一个结果表格，显示每个模型的通过率、平均费用和延迟。如果有模型达到 100%，它会推荐最便宜的那个。

结果同时保存到 `sample-tasks/invoice-extraction/.skilleval/run-<时间戳>/`。

### 第 4 步：创建你自己的任务

```bash
skilleval init my-task
```

这会创建一个包含模板文件的任务文件夹。编辑它们来定义你的任务，然后运行 `skilleval run my-task`。

---

## 4. 核心概念

### 任务文件夹

任务文件夹包含 SkillEval 评估模型所需的一切：

```
my-task/
├── config.yaml          # 任务配置
├── skill.md             # 模式 1 的系统提示词
├── prompt.md            # 模式 2/3 的任务描述
├── meta-skill.md        # 模式 3 的元技能（或 meta-skill-*.md 变体）
├── input/               # 发送给模型的输入文件
│   └── data.txt
├── expected/            # 用于比较的预期输出文件
│   └── result.json
└── .skilleval/          # 结果（由 SkillEval 自动创建）
```

### 技能（Skill）

**技能**是指示模型如何执行任务的系统提示词。在模式 1 中，你自己编写（`skill.md`）。在模式 2/3 中，创建者模型会根据任务描述（`prompt.md`）生成它。

### 试验（Trial）

**试验**是对模型的一次 API 调用。默认情况下，SkillEval 为每个模型运行 5 次试验。多次试验可以捕获非确定性行为——模型必须通过*所有*试验才能达到 100%。

### 比较器（Comparator）

**比较器**是用于检查模型输出是否与预期结果匹配的策略。SkillEval 内置了 8 种比较器（参见[比较器](#21-比较器)）。

### 模式

| 模式 | 命令 | 你提供的 | SkillEval 做的 |
|------|------|---------|---------------|
| **1** | `run` | 技能（系统提示词） | 在多个模型上测试 |
| **2** | `matrix` | 任务描述 | 用创建者模型生成技能，用执行者模型测试 |
| **3** | `chain` | 元技能 + 任务描述 | 元技能指导技能生成，然后执行 |

---

## 5. 设置任务

### 创建新任务

```bash
skilleval init my-extraction-task
```

这会创建以下结构：

```
my-extraction-task/
├── config.yaml       # 带注释默认值的配置文件
├── skill.md          # 模式 1 系统提示词模板
├── prompt.md         # 模式 2/3 任务描述模板
├── meta-skill.md     # 模式 3 元技能模板
├── input/            # 空目录——在此添加你的输入文件
└── expected/         # 空目录——在此添加预期输出文件
```

### 准备输入文件

将模型需要处理的文件放在 `input/` 目录中。SkillEval 支持多种格式（参见[支持的输入文件](#20-支持的输入文件)）。所有输入文件会被拼接并作为提示词的一部分发送。

输入文件以如下格式发送给大模型：

```
--- File: invoice.txt ---
[文件内容]
--- End File ---
```

### 准备预期输出

将正确的输出放在 `expected/` 目录中。文件名应与比较器的要求匹配。对于 `json_exact`，将预期的 JSON 放在 `.json` 文件中。

### 编写技能（模式 1）

编辑 `skill.md`，为模型写入清晰、具体的指令。明确输出格式、字段名称和任何转换规则。技能作为 Chat Completion 请求中的系统消息发送。

### 编写提示词（模式 2/3）

编辑 `prompt.md`，写入人类可读的任务描述。这会被创建者模型用来*生成*技能。包含输入/输出示例和任何约束条件。

### 编写元技能（模式 3）

对于模式 3，将 `meta-skill.md` 重命名为 `meta-skill-<变体名>.md`。你可以创建多个变体：

```
meta-skill-concise.md      # 要求简洁技能的变体
meta-skill-detailed.md     # 要求详细步骤技能的变体
meta-skill-structured.md   # 强调输出结构的变体
```

每个变体通过其名称引用（例如 `concise`、`detailed`、`structured`）。

---

## 6. 模式 1：技能评估

**命令：** `skilleval run <task_path>`

模式 1 是最简单的评估模式。你自己编写技能（系统提示词），SkillEval 在多个模型上测试它，找到最便宜的能做对的模型。

### 工作原理

1. SkillEval 从任务文件夹读取 `skill.md`。
2. 输入文件被提取并格式化为用户消息。
3. 对每个模型，将技能 + 输入作为 Chat Completion 请求发送。
4. 按配置的试验次数重复。
5. 每个输出使用你选择的比较器与预期结果进行比较。
6. 汇总结果并推荐最便宜的 100% 通过率模型。

### 示例

```bash
# 在所有可用模型上运行（每个 5 次试验）
skilleval run my-task

# 在指定模型上运行 10 次试验
skilleval run my-task --models qwen-turbo,glm-4.5-flash --trials 10

# 使用自定义模型目录
skilleval run my-task --catalog ./my-models.yaml
```

### 输出

SkillEval 显示的表格包含以下列：

| 列名 | 说明 |
|------|------|
| Model | 模型名称 |
| Pass Rate | 匹配预期输出的试验占比 |
| Avg Cost | 每次试验的平均费用（美元） |
| Avg Latency | 平均响应时间（秒） |
| Total Cost | 所有试验的总费用 |
| Context Window | 模型的最大上下文长度（token 数） |
| Lint Score | 技能质量评分 0-100（仅在 `--skill-format claude` 时显示） |
| Rec | 星号（`*`）表示推荐模型 |

### 要求

- 任务文件夹中必须存在 `skill.md`。
- `input/` 和 `expected/` 各至少包含一个文件。

---

## 7. 模式 2：矩阵评估

**命令：** `skilleval matrix <task_path>`

模式 2 将技能*创建*与技能*执行*分离。创建者模型根据任务描述生成技能，执行者模型运行生成的技能。这会产生一个创建者-执行者矩阵，显示哪些组合效果最好。

### 工作原理

**第一阶段 — 技能生成：**
1. 每个创建者模型接收 `prompt.md` 加上输入文件的简短描述。
2. 创建者为任务生成一个技能（系统提示词）。
3. 生成的技能保存到磁盘。

**第二阶段 — 执行：**
1. 每个执行者模型使用每个生成的技能运行试验。
2. 输出与预期结果进行比较。
3. 结果形成（创建者, 执行者）对的矩阵。

### 示例

```bash
skilleval matrix my-task \
  --creators qwen-max,glm-5 \
  --executors qwen-turbo,glm-4.5-flash,MiniMax-Text-01 \
  --trials 5
```

### 输出

SkillEval 显示热力图风格的矩阵：

```
              qwen-turbo   glm-4.5-flash   MiniMax-Text-01
qwen-max      100%         80%              100%
glm-5         60%          100%             80%
```

单元格按颜色编码：绿色（100%）、黄色（>=80%）、红色（<80%）。

矩阵之后，SkillEval 会报告最佳组合和 100% 通过率中最便宜的组合。

### 要求

- 任务文件夹中必须存在 `prompt.md`。
- `--creators` 和 `--executors` 都是必需的。

---

## 8. 模式 3：链式评估

**命令：** `skilleval chain <task_path>`

模式 3 增加了另一层：**元技能（meta-skill）**，它指示创建者模型*如何*编写技能。这让你可以尝试不同的技能生成策略。

### 工作原理

**第一阶段 — 技能生成：**
1. 对每个（元技能, 创建者）对：
   - 元技能作为系统消息发送。
   - 创建者接收 `prompt.md` 作为用户消息。
   - 创建者在元技能指导下生成技能。

**第二阶段 — 执行：**
1. 每个执行者使用每个生成的技能运行试验。
2. 结果形成三维结构：（元技能, 创建者, 执行者）。

### 示例

```bash
skilleval chain my-task \
  --meta-skills concise,detailed \
  --creators qwen-max,glm-5 \
  --executors qwen-turbo,glm-4.5-flash \
  --trials 5
```

### 大规模运行确认

如果 API 调用总数超过 100 次，SkillEval 会在执行前请求确认。使用 `--yes`（或 `-y`）跳过此提示：

```bash
skilleval chain my-task \
  --meta-skills a,b,c --creators x,y --executors p,q,r \
  --trials 10 --yes
```

### 输出

SkillEval 显示：
1. 元技能对比表，展示每个元技能变体的平均通过率。
2. 最佳整体链（元技能 / 创建者 / 执行者）。
3. 100% 通过率中最便宜的链。

### 要求

- 任务文件夹中必须存在 `prompt.md`。
- 每个命名的变体都必须存在对应的 `meta-skill-<name>.md` 文件。
- `--meta-skills`、`--creators` 和 `--executors` 都是必需的。

---

## 9. 临时端点

你可以通过 `--endpoint`、`--api-key` 和 `--model-name` 参数，在不修改模型目录的情况下评估任何 OpenAI 兼容模型。这些参数适用于 `run`、`matrix`、`chain` 和 `skill-test` 命令。

### 示例

```bash
# 测试本地 Ollama 模型
skilleval run my-task \
  --endpoint http://localhost:11434/v1 \
  --model-name llama3 \
  --api-key ""

# 将 OpenAI 模型与目录模型一起测试
skilleval run my-task \
  --endpoint https://api.openai.com/v1 \
  --api-key $OPENAI_API_KEY \
  --model-name gpt-4o \
  --models qwen-turbo,gpt-4o
```

### 工作原理

临时模型会被追加到模型目录中，与其他模型同等对待。由于它内嵌了 API 密钥，会自动被 `filter_available` 识别为可用。如果要与目录模型一起运行，请在 `--models` 中包含其 `--model-name`。

### 费用追踪

临时模型的输入和输出费用默认为 `$0`。Token 使用仍会被追踪，但费用计算将显示 `$0`。要获得准确的费用追踪，请将模型添加到包含定价的 `models.yaml` 中。

### 参数

| 参数 | 必需 | 说明 |
|------|------|------|
| `--endpoint` | 是 | OpenAI 兼容的 API 基础 URL（必须为 `http://` 或 `https://`） |
| `--model-name` | 是（与 `--endpoint` 一起使用时） | API 请求中发送的模型标识符 |
| `--api-key` | 否 | 端点的 API 密钥（无密钥端点如 Ollama 可使用 `""`） |

---

## 10. 技能检查

**命令：** `skilleval lint <skill_path>`

验证 Claude Code 技能目录的结构。在测试前用于发现常见问题。

### 检查项目

| 检查项 | 严重性 | 说明 |
|--------|--------|------|
| Frontmatter 存在 | 错误 | 文件顶部必须有 YAML frontmatter（`--- ... ---`） |
| 必需字段 | 错误 | Frontmatter 必须包含 `name` 和 `description` |
| 编号阶段 | 错误 | 至少需要一个 `## Phase N` 或 `### Step N` 标题 |
| 错误处理部分 | 警告 | 缺少 `## Error Handling` 标题 |
| 规则部分 | 警告 | 缺少 `## Rules` 或 `## Important Rules` 标题 |
| 引用文件链接 | 错误 | 指向 `references/` 的 Markdown 链接必须指向存在的文件 |
| Python 代码块 | 错误 | Python 代码块必须有有效语法 |
| Bash 代码块 | 错误 | Bash 代码块必须通过 `bash -n` 语法检查 |

### 质量分数

检查器计算质量分数（0-100）：
- 起始分数 100
- 每个错误扣 20 分
- 每个警告扣 10 分
- 每个提示级别问题扣 2 分

### 示例

```bash
skilleval lint ~/.claude/skills/my-skill/
```

### 退出码

如果发现错误，退出码为 `1`；否则为 `0`。警告不会导致非零退出码。

---

## 11. 技能测试

**命令：** `skilleval skill-test <skill_path> --test-cases <test_dir>`

通过提取技能的核心提示逻辑并将其在评估引擎中运行，来测试 Claude Code 技能。

### 工作原理

1. 从技能目录解析 `skill.md`：
   - 去除 YAML frontmatter
   - 移除工具使用指令（bash/shell 代码块、CLI 指令）
   - 提取核心提示逻辑
2. 从测试目录加载测试用例
3. 使用提取的提示词对每个测试用例运行模式 1 评估

### 测试用例结构

```
test-cases/
├── config.yaml           # 共享配置（比较器、试验次数等）
├── case-1/
│   ├── input/            # 此测试用例的输入文件
│   └── expected/         # 预期输出文件
├── case-2/
│   ├── input/
│   └── expected/
```

### 示例

```bash
skilleval skill-test ~/.claude/skills/my-skill/ \
  --test-cases ./test-cases/ \
  --models qwen-turbo,glm-4.5-flash \
  --trials 3
```

### 输出

显示按测试用例和模型分组的结果表格，以及每个模型通过了多少测试用例的总体摘要。

---

## 12. 运行比较

**命令：** `skilleval compare <old_run> <new_run>`

比较两次评估运行的结果以检测改进和退化。在迭代 `skill.md` 提示词时非常有用。

### 工作原理

1. 从两个运行目录加载 `results.json`
2. 在运行之间匹配模型
3. 计算通过率变化
4. 将每个模型分类为：改进、退化、未变、新增或已移除

### 示例

```bash
skilleval compare \
  my-task/.skilleval/run-20260227-143052 \
  my-task/.skilleval/run-20260228-091500
```

### 输出

显示比较表格，包含以下列：

| 列名 | 说明 |
|------|------|
| Model | 模型名称 |
| Old Rate | 第一次运行的通过率 |
| New Rate | 第二次运行的通过率 |
| Delta | 通过率变化（例如 `+20%`、`-40%`） |
| Status | `improved`、`regressed`、`unchanged`、`new` 或 `removed` |

---

## 13. HTML 报告

从评估结果生成独立的 HTML 报告，用于与相关人员分享。

### 使用方法

```bash
# 生成 HTML 报告
skilleval report my-task/.skilleval/run-20260227-143052 --html report.html

# 生成并在浏览器中打开
skilleval report my-task/.skilleval/run-20260227-143052 --html report.html --open
```

### 报告内容

HTML 报告是独立的（内联 CSS/JS，无外部依赖），包含按模式的可视化：

**模式 1（`run`）：**
- 每个模型的通过率条形图（颜色编码：绿/黄/红）
- 费用对比表（平均费用、平均延迟、总费用）
- 可折叠的每模型试验详情（支持全部展开/折叠）

**模式 2（`matrix`）：**
- 创建者 x 执行者热力图，带颜色编码的单元格
- 最佳组合以强调轮廓高亮

**模式 3（`chain`）：**
- 按元技能变体分组的通过率条形图
- 可折叠的变体详情表（创建者、执行者、通过率、费用、延迟）

### 设计

报告使用深色主题设计，注重可读性。完全响应式，支持移动设备。

---

## 14. 交互式 TUI 模式

**命令：** `skilleval`（无参数）

不带参数运行 `skilleval` 时，会启动一个交互式终端界面（TUI），支持斜杠命令导航和 Tab 补全。

### 启动方式

```bash
skilleval
```

### 可用命令

| 命令 | 说明 |
|------|------|
| `/run` | 启动模式 1 评估（提示输入任务路径、模型、试验次数） |
| `/matrix` | 交互式矩阵评估设置 |
| `/chain` | 交互式链式评估设置 |
| `/catalog` | 显示可用模型及状态 |
| `/init` | 创建新任务文件夹（提示输入名称） |
| `/report` | 重新渲染之前运行的结果 |
| `/history` | 查看任务的历史运行记录 |
| `/lint` | 验证 Claude Code 技能结构 |
| `/compare` | 比较两次评估运行 |
| `/language` | 在中文和英文之间切换 |
| `/help` | 显示所有可用命令 |
| `/quit` | 退出 TUI |

### Tab 补全

输入 `/` 后按 `Tab` 可查看所有可用命令。TUI 支持部分匹配——输入前几个字符后按 `Tab` 即可自动补全。

---

## 15. 运行历史

**命令：** `skilleval history <task_path>`

列出任务的所有历史评估运行，显示每次运行的元数据。

### 示例

```bash
skilleval history sample-tasks/invoice-extraction
skilleval history my-task --json
```

### 输出

显示包含以下列的表格：

| 列名 | 说明 |
|------|------|
| Run | 目录名称（如 `run-20260227-143052`），最新运行标记 `[LATEST]` |
| Mode | 评估模式（`run`、`matrix` 或 `chain`） |
| Models | 评估的模型数量 |
| Avg Pass Rate | 所有模型的平均通过率（颜色编码） |
| Recommendation | 推荐的模型（截断至 50 个字符） |

### 参数

| 参数 | 说明 |
|------|------|
| `--json` | 以 JSON 格式输出历史记录 |

---

## 16. 国际化

SkillEval 在 CLI 和 TUI 中全面支持英文和简体中文。

### 设置语言

有三种方式设置语言，按以下优先级检查：

**1. 环境变量（最高优先级）：**

```bash
export SKILLEVAL_LANG=zh
skilleval run my-task
```

**2. 设置文件：**

```bash
# 创建或编辑 ~/.config/skilleval/settings.yaml
echo "language: zh" > ~/.config/skilleval/settings.yaml
```

**3. 系统语言环境自动检测（回退）：**

如果系统语言环境以 `zh` 开头（如 `zh_CN`、`zh_TW`），SkillEval 默认使用中文。否则默认英文。

### 在 TUI 中切换

在交互式 TUI 中输入 `/language` 可在中文和英文之间切换。语言偏好保存到 `~/.config/skilleval/settings.yaml`，跨会话持久化。

### 支持的语言

| 代码 | 语言 |
|------|------|
| `en` | 英文（默认） |
| `zh` | 简体中文 |

---

## 17. CLI 参考

### `skilleval`

```
用法: skilleval [OPTIONS] COMMAND [ARGS]...

  SkillEval: 找到能 100% 完成你任务的最便宜的大模型。

选项:
  --version      显示版本并退出。
  -v, --verbose  增加日志详细程度（-v 为 INFO，-vv 为 DEBUG）。
  --help         显示帮助信息并退出。

命令:
  catalog     显示模型目录及可用状态。
  chain       模式 3: 元技能 x 创建者 x 执行者链式评估。
  compare     比较两次运行的结果。
  history     列出任务的历史评估运行。
  init        创建包含模板文件的新任务文件夹。
  lint        验证 Claude Code 技能结构。
  matrix      模式 2: 创建者 x 执行者矩阵评估。
  report      重新渲染之前运行的结果。
  run         模式 1: 使用给定技能评估模型。
  skill-test  使用测试用例测试 Claude Code 技能。
```

不带参数运行时，SkillEval 会启动[交互式 TUI 模式](#14-交互式-tui-模式)。

### `skilleval init`

| 参数 | 必需 | 说明 |
|------|------|------|
| `NAME` | 是 | 新任务文件夹的名称 |

创建包含模板文件的任务文件夹（`config.yaml`、`skill.md`、`prompt.md`、`meta-skill.md`、`input/`、`expected/`）。

### `skilleval run`

| 参数/选项 | 必需 | 默认值 | 说明 |
|-----------|------|--------|------|
| `TASK_PATH` | 是 | — | 任务文件夹路径 |
| `--models` | 否 | 所有可用模型 | 逗号分隔的模型名称 |
| `--trials` | 否 | 取自配置 | 覆盖试验次数 |
| `--parallel` | 否 | `20` | 最大并发 API 调用数 |
| `--catalog` | 否 | 自动检测 | 模型目录 YAML 文件路径 |
| `--resume` | 否 | — | 用于恢复的上次运行目录路径 |
| `--output` | 否 | `rich` | 输出格式：`rich`（表格）、`json` 或 `csv` |
| `--endpoint` | 否 | — | 临时 OpenAI 兼容端点 URL |
| `--api-key` | 否 | — | 临时端点的 API 密钥 |
| `--model-name` | 否 | — | 临时端点的模型名称 |
| `--skill-format` | 否 | `plain` | 技能格式：`plain`（默认）或 `claude`（检查 + 去除脚手架） |
| `--json` | 否 | `false` | 以 JSON 格式输出结果（`--output json` 的别名） |

**恢复运行：** 传入 `--resume <run_dir>` 可跳过上次运行中已完成的模型。SkillEval 从给定目录读取 `checkpoint.json`，跳过 `completed_models` 中列出的模型。

**技能格式：** 使用 `--skill-format claude` 时，模式 1 会按照 Claude Code 技能规范检查 skill.md，去除工具脚手架，并在结果中报告 `lint_score`（0-100）。

### `skilleval matrix`

| 参数/选项 | 必需 | 默认值 | 说明 |
|-----------|------|--------|------|
| `TASK_PATH` | 是 | — | 任务文件夹路径 |
| `--creators` | 是 | — | 逗号分隔的创建者模型名称 |
| `--executors` | 是 | — | 逗号分隔的执行者模型名称 |
| `--trials` | 否 | 取自配置 | 覆盖试验次数 |
| `--parallel` | 否 | `20` | 最大并发 API 调用数 |
| `--catalog` | 否 | 自动检测 | 模型目录 YAML 文件路径 |
| `--output` | 否 | `rich` | 输出格式：`rich`（表格）、`json` 或 `csv` |
| `--endpoint` | 否 | — | 临时 OpenAI 兼容端点 URL |
| `--api-key` | 否 | — | 临时端点的 API 密钥 |
| `--model-name` | 否 | — | 临时端点的模型名称 |
| `--skill-format` | 否 | `plain` | 技能格式：`plain`（默认）或 `claude`（检查 + 去除脚手架） |
| `--json` | 否 | `false` | 以 JSON 格式输出结果（`--output json` 的别名） |

### `skilleval chain`

| 参数/选项 | 必需 | 默认值 | 说明 |
|-----------|------|--------|------|
| `TASK_PATH` | 是 | — | 任务文件夹路径 |
| `--meta-skills` | 是 | — | 逗号分隔的元技能变体名称 |
| `--creators` | 是 | — | 逗号分隔的创建者模型名称 |
| `--executors` | 是 | — | 逗号分隔的执行者模型名称 |
| `--trials` | 否 | 取自配置 | 覆盖试验次数 |
| `--parallel` | 否 | `20` | 最大并发 API 调用数 |
| `--catalog` | 否 | 自动检测 | 模型目录 YAML 文件路径 |
| `--yes` / `-y` | 否 | `false` | 跳过大规模运行（>100 次 API 调用）的确认 |
| `--output` | 否 | `rich` | 输出格式：`rich`（表格）、`json` 或 `csv` |
| `--endpoint` | 否 | — | 临时 OpenAI 兼容端点 URL |
| `--api-key` | 否 | — | 临时端点的 API 密钥 |
| `--model-name` | 否 | — | 临时端点的模型名称 |
| `--skill-format` | 否 | `plain` | 技能格式：`plain`（默认）或 `claude`（检查 + 去除脚手架） |
| `--json` | 否 | `false` | 以 JSON 格式输出结果（`--output json` 的别名） |

### `skilleval catalog`

| 选项 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `--catalog` | 否 | 自动检测 | 模型目录 YAML 文件路径 |
| `--json` | 否 | `false` | 以 JSON 格式输出目录 |

### `skilleval history`

| 参数/选项 | 必需 | 默认值 | 说明 |
|-----------|------|--------|------|
| `TASK_PATH` | 是 | — | 任务文件夹路径 |
| `--json` | 否 | `false` | 以 JSON 格式输出历史记录 |

列出任务 `.skilleval/` 目录中的所有历史运行，按时间从新到旧排序。最近一次运行标记为 `[LATEST]`。

### `skilleval report`

| 参数/选项 | 必需 | 默认值 | 说明 |
|-----------|------|--------|------|
| `RESULTS_PATH` | 是 | — | 结果目录或 `results.json` 文件的路径 |
| `--html` | 否 | — | HTML 报告输出路径 |
| `--open` | 否 | `false` | 生成后在浏览器中打开 HTML 报告 |
| `--json` | 否 | `false` | 以 JSON 格式输出结果 |

重新渲染之前运行的结果，不会发起任何 API 调用。可选生成独立的 HTML 报告。

### `skilleval lint`

| 参数 | 必需 | 说明 |
|------|------|------|
| `SKILL_PATH` | 是 | Claude Code 技能目录路径 |

验证技能结构（frontmatter、阶段、引用、代码块）。如果发现错误，退出码为 `1`。

### `skilleval compare`

| 参数 | 必需 | 说明 |
|------|------|------|
| `OLD_RUN` | 是 | 第一次（基准）运行结果的路径 |
| `NEW_RUN` | 是 | 第二次（更新后）运行结果的路径 |

显示两次运行之间通过率变化的对比表格。

### `skilleval skill-test`

| 参数/选项 | 必需 | 默认值 | 说明 |
|-----------|------|--------|------|
| `SKILL_PATH` | 是 | — | Claude Code 技能目录路径 |
| `--test-cases` | 是 | — | 测试用例目录路径 |
| `--models` | 否 | 所有可用模型 | 逗号分隔的模型名称 |
| `--trials` | 否 | 取自配置 | 覆盖试验次数 |
| `--parallel` | 否 | `20` | 最大并发 API 调用数 |
| `--catalog` | 否 | 自动检测 | 模型目录 YAML 文件路径 |
| `--endpoint` | 否 | — | 临时 OpenAI 兼容端点 URL |
| `--api-key` | 否 | — | 临时端点的 API 密钥 |
| `--model-name` | 否 | — | 临时端点的模型名称 |

---

## 18. 配置

每个任务文件夹包含一个 `config.yaml` 文件，用于控制评估行为。

### 所有字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `comparator` | string | `"json_exact"` | 输出验证的比较策略 |
| `custom_script` | string | `null` | 自定义比较器脚本路径（仅在 `comparator: custom` 时使用） |
| `trials` | int | `5` | 每个模型的试验次数。更高的值增加置信度但费用更高 |
| `timeout` | int | `60` | API 请求超时时间（秒） |
| `temperature` | float | `0.0` | 模型采样温度。使用 `0.0` 获得确定性输出 |
| `max_tokens` | int | `4096` | 每次请求的最大输出 token 数 |
| `output_format` | string | `"json"` | 预期的输出格式（用于显示） |

**验证：** SkillEval 会在 `config.yaml` 包含未知键名时发出警告（可能是拼写错误）。它还会在加载时验证 `comparator` 值，如果名称无法识别则报告可用选项。

### 配置示例

```yaml
# 严格 JSON 比较
comparator: json_exact

# 10 次试验以获得高置信度
trials: 10

# 复杂任务的宽松超时
timeout: 120

# 确定性输出
temperature: 0.0

# 允许更长的响应
max_tokens: 8192

output_format: json
```

### 比较器选项

| 值 | 说明 |
|----|------|
| `json_exact` | 解析后的 JSON 深度相等检查（默认） |
| `csv_ordered` | 逐行 CSV 比较（顺序敏感） |
| `csv_unordered` | 基于集合的 CSV 比较（顺序无关） |
| `field_subset` | 检查预期字段是否存在于输出中（额外字段允许） |
| `file_hash` | 字节级 SHA-256 比较 |
| `text_exact` | 空白归一化后的精确文本比较 |
| `text_contains` | 检查预期文本是否作为子串出现在输出中（支持 `re:` 前缀使用正则表达式） |
| `custom` | 运行用户提供的脚本（需要 `custom_script`） |

详情参见[比较器](#21-比较器)。

---

## 19. 模型目录

### 默认模型

SkillEval 内置了一个涵盖 5 个供应商、14 个模型的默认模型目录：

#### 通义千问（DashScope）

| 模型 | 档次 | 输入 $/M | 输出 $/M | 上下文 |
|------|------|----------|----------|--------|
| `qwen-max` | 旗舰 | $1.60 | $6.40 | 128K |
| `qwen-plus` | 中档 | $0.40 | $1.20 | 128K |
| `qwen-turbo` | 经济 | $0.05 | $0.20 | 128K |

#### 智谱 GLM

| 模型 | 档次 | 输入 $/M | 输出 $/M | 上下文 |
|------|------|----------|----------|--------|
| `glm-5` | 旗舰 | $1.00 | $3.20 | 128K |
| `glm-4.5` | 中档 | $0.60 | $2.20 | 128K |
| `glm-4.5-air` | 中低档 | $0.15 | $0.55 | 128K |
| `glm-4.5-flash` | 经济 | $0.00 | $0.00 | 128K |

#### MiniMax

| 模型 | 档次 | 输入 $/M | 输出 $/M | 上下文 |
|------|------|----------|----------|--------|
| `MiniMax-M2.5` | 旗舰 | $0.30 | $1.20 | 200K |
| `MiniMax-M2` | 中档 | $0.26 | $1.00 | 200K |
| `MiniMax-Text-01` | 经济 | $0.20 | $1.10 | 200K |

#### OpenAI

| 模型 | 档次 | 输入 $/M | 输出 $/M | 上下文 |
|------|------|----------|----------|--------|
| `gpt-4o` | 旗舰 | $2.50 | $10.00 | 128K |
| `gpt-4o-mini` | 经济 | $0.15 | $0.60 | 128K |

#### DeepSeek（深度求索）

| 模型 | 档次 | 输入 $/M | 输出 $/M | 上下文 |
|------|------|----------|----------|--------|
| `deepseek-chat` | 通用 | $0.14 | $0.28 | 128K |
| `deepseek-reasoner` | 推理 | $0.55 | $2.19 | 128K |

### 目录解析顺序

当未指定 `--catalog` 时，SkillEval 按以下顺序搜索模型目录：

1. **显式路径** — `--catalog ./my-models.yaml`
2. **本地目录** — `./models.yaml`（当前工作目录）
3. **用户全局** — `~/.config/skilleval/models.yaml`
4. **内置默认** — 随包发布的内置目录

### 自定义目录

创建 `models.yaml` 文件来添加或覆盖模型：

```yaml
- name: my-custom-model
  provider: dashscope
  endpoint: https://dashscope.aliyuncs.com/compatible-mode/v1
  input_cost_per_m: 0.10
  output_cost_per_m: 0.40
  env_key: DASHSCOPE_API_KEY
  context_window: 32768
```

每条记录需要以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | 唯一的模型标识符 |
| `provider` | string | 供应商名称（用于按供应商限流） |
| `endpoint` | string | OpenAI 兼容的 API 基础 URL |
| `input_cost_per_m` | float | 每百万输入 token 的费用（美元） |
| `output_cost_per_m` | float | 每百万输出 token 的费用（美元） |
| `env_key` | string | 包含 API 密钥的环境变量 |
| `context_window` | int | 最大上下文长度（token 数，默认：128000） |

### 环境变量

| 供应商 | 变量 | 注册地址 |
|--------|------|---------|
| 通义千问（DashScope） | `DASHSCOPE_API_KEY` | https://dashscope.console.aliyun.com/ |
| 智谱 GLM | `ZHIPU_API_KEY` | https://open.bigmodel.cn/ |
| MiniMax | `MINIMAX_API_KEY` | https://platform.minimax.io/ |
| OpenAI | `OPENAI_API_KEY` | https://platform.openai.com/ |
| DeepSeek | `DEEPSEEK_API_KEY` | https://platform.deepseek.com/ |

只有 `env_key` 环境变量已设置的模型才被视为"可用"。不指定 `--models` 运行时，只使用可用的模型。

---

## 20. 支持的输入文件

SkillEval 从输入文件中提取文本并格式化发送给大模型。支持以下文件类型：

### 文本类（无需额外依赖）

| 扩展名 | 说明 |
|--------|------|
| `.txt` | 纯文本 |
| `.md` | Markdown |
| `.json` | JSON 数据 |
| `.csv` | 逗号分隔值 |
| `.tsv` | 制表符分隔值 |
| `.xml` | XML 文档 |
| `.html` | HTML 页面 |
| `.yaml`、`.yml` | YAML 数据 |

### 文档格式（需要 `pip install -e ".[docs]"`）

| 扩展名 | 依赖库 | 说明 |
|--------|--------|------|
| `.pdf` | `pdfplumber` | PDF 文本和表格提取。页面标记为 `[Page N]`，表格标记为 `[Page N - Table M]`。 |
| `.docx` | `python-docx` | Word 文档提取。段落和表格被提取，表格标记为 `[Table N]`。 |
| `.xlsx`、`.xls` | `openpyxl` | Excel 电子表格提取。每个工作表标记为 `[Sheet: name]`，提取非空行。 |

### 表格格式化

PDF、Word 和 Excel 中的表格以管道分隔的 Markdown 格式渲染：

```
| 表头1 | 表头2 | 表头3 |
| ----- | ----- | ----- |
| 值1   | 值2   | 值3   |
```

### 未知文件类型

对于扩展名未识别的文件，SkillEval 会尝试以 UTF-8 文本读取。如果文件看起来是二进制的（基于前 512 字节的启发式检查），则会报错。

### 缺少依赖

如果你尝试处理 PDF、DOCX 或 XLSX 文件但未安装可选依赖，SkillEval 会抛出 `RuntimeError` 并附带安装说明：

```
RuntimeError: PDF 提取需要 pdfplumber。请安装：
  pip install pdfplumber
```

---

## 21. 比较器

比较器决定 SkillEval 如何检查模型输出是否与预期结果匹配。所有比较器返回 (passed, diff) 元组，其中 `diff` 在成功时为 `None`，失败时为描述性错误字符串。

### 输出预处理

比较前，SkillEval 会自动清理模型输出：
1. **去除推理标签** — 移除 `<think>`、`<thinking>`、`<reasoning>` 块（在 DeepSeek-R1 等推理模型中常见）。
2. **移除 Markdown 代码块** — 去除 `` ```json `` 或 `` ``` `` 包裹。
3. **修剪空白** — 移除首尾空白字符。

### `json_exact`

**JSON 输出的深度相等比较。**

- 将预期和输出都解析为 JSON。
- 将所有整数归一化为浮点数（因此 `150` 匹配 `150.0`）。
- 使用排序键进行标准化以实现一致比较。
- 输出中的额外键会导致失败——必须精确匹配。
- 空白和格式差异被忽略。

**适用场景：** 每个字段都必须精确匹配的结构化数据提取。

**失败时的差异示例：**
```diff
--- expected
+++ output
@@ -3,3 +3,3 @@
-  "total": 16003.75,
+  "total": 16004.0,
```

### `csv_ordered`

**严格顺序的逐行 CSV 比较。**

- 列顺序和行顺序都必须匹配。
- 报告第一个不同的行。

**适用场景：** 行顺序有意义的表格数据（例如按时间排序的记录）。

**失败时的差异示例：**
```
Row 3 differs:
  expected: ['2026-01-15', 'Invoice', '500.00']
  got:      ['2026-01-15', 'Invoice', '500']
```

### `csv_unordered`

**基于集合的 CSV 比较（顺序无关）。**

- 行作为多重集比较（重复计数）。
- 列顺序仍然敏感。
- 报告缺少和多余的行及其计数。

**适用场景：** 行顺序无关的表格数据（例如提取的项目列表）。

**失败时的差异示例：**
```
Missing rows (in expected but not output):
  ['Widget A', '10', '25.00'] (x1)
Extra rows (in output but not expected):
  ['Widget A', '10', '25'] (x1)
```

### `field_subset`

**JSON 的递归子集验证。**

- 检查预期输出中的所有字段是否存在于实际输出中，且值匹配。
- **输出中的额外字段是允许的** — 只检查预期的字段。
- 数组必须具有相同长度，项目递归检查。
- 使用 JSONPath 记法报告不匹配。

**适用场景：** 模型可能返回超出你要求的额外有用字段的任务。

**失败时的差异示例：**
```
$.users[0].name: expected "John", got "Jane"
$.items: expected array length 2, got 3
```

### `file_hash`

**使用 SHA-256 的字节级比较。**

- 比较原始字节——不进行解析或归一化。
- 行尾差异（CRLF vs LF）会导致失败。
- 空白差异会导致失败。

**适用场景：** 输出必须完全可复现的任务（例如代码生成、模板填充）。

**失败时的差异示例：**
```
Hash mismatch for output.txt:
  expected: a1b2c3d4e5f6...
  got:      x9y8z7w6v5u4...
```

### `text_exact`

**空白归一化后的精确文本比较。**

- 去除两端的前导/尾随空白。
- 将连续空白字符折叠为单个空格。
- 归一化后进行精确字符串比较。
- 失败时显示统一差异（unified diff）便于调试。

**适用场景：** 纯文本输出中允许轻微空白差异（多余空格、尾随换行符），但实际内容必须完全匹配的任务。

**失败时的差异示例：**
```
--- expected
+++ actual
@@ -1,3 +1,3 @@
 The capital of France
-is Paris.
+is Lyon.
```

### `text_contains`

**子串检查，支持可选的正则表达式。**

- 检查预期文本是否作为子串出现在模型的输出中。
- 当预期值以 `re:` 为前缀时支持正则表达式匹配（例如 `re:\d{4}-\d{2}-\d{2}` 匹配日期格式）。
- 不带 `re:` 前缀时执行普通子串搜索。
- 比较前会去除预期文本和实际文本两端的空白。

**适用场景：** 模型的输出应包含特定文本或匹配某个模式，但可能还包含其他内容的任务（例如检查回答中是否包含关键短语）。

**失败时的差异示例：**
```
Expected substring not found in output:
  expected: "Paris"
  output:   "The capital of France is Lyon, a major city."
```

### `custom`

**用户提供的验证脚本。**

需要在 `config.yaml` 中配置 `custom_script`：

```yaml
comparator: custom
custom_script: ./compare.py
```

脚本会为每对文件调用：

```bash
./compare.py <expected_file> <output_file>
```

| 退出码 | 含义 |
|--------|------|
| `0` | 通过——输出匹配预期 |
| 非零 | 失败——stdout 内容成为差异文本 |

脚本每次调用有 30 秒超时。

**适用场景：** 内置比较器无法表达的复杂验证逻辑（例如语义等价、数值容差）。

**自定义脚本示例：**

```python
#!/usr/bin/env python3
import json, sys

expected = json.load(open(sys.argv[1]))
actual = json.load(open(sys.argv[2]))

# 数值字段允许 1% 容差
for key in expected:
    if isinstance(expected[key], (int, float)):
        if abs(expected[key] - actual.get(key, 0)) / max(abs(expected[key]), 1) > 0.01:
            print(f"{key}: expected {expected[key]}, got {actual.get(key)}")
            sys.exit(1)

sys.exit(0)
```

---

## 22. 结果与输出

### 输出目录

每次运行在任务文件夹的 `.skilleval/` 下创建一个带时间戳的目录：

```
my-task/.skilleval/run-20260227-143052/
```

每次运行完成后，SkillEval 还会创建（或更新）一个 `latest` 符号链接：

```
my-task/.skilleval/latest -> run-20260227-143052
```

这让你无需知道确切的时间戳就能引用最新的运行：

```bash
skilleval report my-task/.skilleval/latest
```

### `run-config.json`

每个运行目录还包含一个轻量级的 `run-config.json` 文件，记录运行的产生方式：

```json
{
  "mode": "run",
  "task": "my-task",
  "timestamp": "2026-02-27T14:30:52",
  "models": ["qwen-turbo", "glm-4.5-flash"],
  "trials": 5
}
```

此文件被 `history` 命令用于快速加载运行元数据，无需解析完整的 `results.json`。

### 目录结构

结构因模式而异：

**模式 1（`run`）：**

```
run-20260227-143052/
├── results.json                     # 机器可读的结果
├── run-config.json                  # 轻量级运行元数据
├── summary.txt                      # 人类可读的摘要
└── trials/
    ├── qwen-turbo/
    │   ├── trial-1/
    │   │   ├── output.txt           # 模型的原始输出
    │   │   ├── diff.txt             # 比较差异（仅失败时）
    │   │   └── meta.json            # token 计数、费用、延迟
    │   ├── trial-2/
    │   │   └── ...
    │   └── ...
    └── glm-4.5-flash/
        └── ...
```

**模式 2（`matrix`）：**

```
run-20260227-143052/
├── results.json
├── summary.txt
├── generated_skills/
│   ├── qwen-max.md                  # qwen-max 生成的技能
│   └── glm-5.md                     # glm-5 生成的技能
└── trials/
    ├── qwen-max__qwen-turbo/        # 创建者__执行者
    │   └── trial-1/
    │       └── ...
    └── ...
```

**模式 3（`chain`）：**

```
run-20260227-143052/
├── results.json
├── summary.txt
├── generated_skills/
│   ├── concise__qwen-max.md         # 元技能__创建者
│   └── detailed__glm-5.md
└── trials/
    ├── concise__qwen-max__qwen-turbo/
    │   └── trial-1/
    │       └── ...
    └── ...
```

### `results.json`

`results.json` 文件包含完整的 `RunSummary`（JSON 格式）。关键字段：

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

### `meta.json`（每次试验）

```json
{
  "input_tokens": 850,
  "output_tokens": 320,
  "cost": 0.00012,
  "latency_seconds": 1.23,
  "finish_reason": "stop"
}
```

### 重新渲染结果

使用 `skilleval report` 重新显示结果，无需发起 API 调用：

```bash
# 指向结果目录
skilleval report my-task/.skilleval/run-20260227-143052

# 或直接指向 JSON 文件
skilleval report my-task/.skilleval/run-20260227-143052/results.json
```

---

### 输出格式

使用 `--output` 控制结果的显示方式：

```bash
# Rich 表格（默认）
skilleval run my-task

# JSON 用于脚本处理
skilleval run my-task --output json | jq '.recommendation'

# CSV 用于电子表格
skilleval run my-task --output csv > results.csv
```

各模式的 CSV 列：
- **模式 1：** `model, pass_rate, avg_cost, avg_latency, total_cost`
- **模式 2：** `creator, executor, pass_rate, avg_cost, total_cost`
- **模式 3：** `meta_skill, creator, executor, pass_rate, avg_cost, total_cost`

---

## 23. 测试用例演练

本节提供一个完整的、独立的测试用例，你可以从零开始创建，用于验证 SkillEval 的安装和理解评估流程。

### 任务：邮件联系人提取

我们将构建一个从纯文本邮件中提取联系信息为结构化 JSON 的任务。

### 第 1 步：创建任务文件夹

```bash
skilleval init email-extraction
```

### 第 2 步：编写输入

将 `email-extraction/input/example.txt` 替换为：

```
email-extraction/input/email.txt
```

```text
From: David Park <david.park@novacorp.io>
To: support@acmewidgets.com
Date: March 1, 2026
Subject: Partnership Inquiry

Hi Team,

I'm the Head of Business Development at NovaCorp Industries.
We're interested in exploring a partnership for your
enterprise widget platform.

Could we schedule a call next week? My direct line is
+1 (415) 555-0192 and I'm available Tuesday or Thursday
between 10am and 3pm PST.

Best regards,
David Park
Head of Business Development
NovaCorp Industries
500 Market Street, Suite 1200
San Francisco, CA 94105
```

### 第 3 步：定义预期输出

创建 `email-extraction/expected/result.json`：

```json
{
  "sender_name": "David Park",
  "sender_email": "david.park@novacorp.io",
  "sender_title": "Head of Business Development",
  "sender_company": "NovaCorp Industries",
  "sender_phone": "+1 (415) 555-0192",
  "sender_address": "500 Market Street, Suite 1200, San Francisco, CA 94105",
  "recipient_email": "support@acmewidgets.com",
  "date": "2026-03-01",
  "subject": "Partnership Inquiry"
}
```

### 第 4 步：编写技能

将 `email-extraction/skill.md` 替换为：

```markdown
You are an email contact extraction system. Extract structured contact
information from the email provided and return ONLY valid JSON with no
additional text.

## Output Schema

Return a JSON object with exactly these fields:

- `sender_name` (string): Full name of the email sender
- `sender_email` (string): Email address of the sender
- `sender_title` (string): Job title of the sender
- `sender_company` (string): Company name of the sender
- `sender_phone` (string): Phone number exactly as written
- `sender_address` (string): Full mailing address on a single line,
  comma-separated
- `recipient_email` (string): Email address of the recipient
- `date` (string): Email date in YYYY-MM-DD format
- `subject` (string): Email subject line

## Rules

- Return ONLY the JSON object. No markdown fences, no explanation.
- Dates must be in YYYY-MM-DD format.
- The address should combine street, suite, city, state, and ZIP into
  one comma-separated string.
- Phone numbers should be kept in their original format.
```

### 第 5 步：配置任务

将 `email-extraction/config.yaml` 替换为：

```yaml
comparator: json_exact
trials: 3
timeout: 60
temperature: 0
max_tokens: 1024
output_format: json
```

### 第 6 步：验证任务结构

你的任务文件夹现在应该如下：

```
email-extraction/
├── config.yaml
├── skill.md
├── prompt.md              # init 生成的模板（模式 1 不使用）
├── meta-skill.md          # init 生成的模板（模式 1 不使用）
├── input/
│   ├── example.txt        # init 生成的模板（可删除）
│   └── email.txt          # 你的输入
└── expected/
    ├── example.txt        # init 生成的模板（可删除）
    └── result.json        # 你的预期输出
```

> **提示：** 删除 `input/` 和 `expected/` 中的模板 `example.txt` 文件，只保留你的实际测试文件。SkillEval 会拼接 `input/` 中的所有文件，多余的文件会给提示词添加噪音。

### 第 7 步：运行评估

```bash
# 在所有可用模型上运行
skilleval run email-extraction

# 或指定模型
skilleval run email-extraction --models qwen-turbo,glm-4.5-flash --trials 5
```

### 第 8 步：查看结果

```bash
# 查看运行历史
skilleval history email-extraction

# 重新渲染最近一次运行
skilleval report email-extraction/.skilleval/latest

# 导出为 CSV
skilleval report email-extraction/.skilleval/latest --output csv
```

### 第 9 步：调查失败

如果某个模型未达到 100%，检查差异：

```bash
cat email-extraction/.skilleval/latest/qwen-turbo/trial-1/diff.txt
```

此任务常见的失败模式：
- **日期格式：** 模型返回 "March 1, 2026" 而非 "2026-03-01"
- **地址格式：** 逗号位置不同或缺少套房号
- **电话格式：** 模型规范化为不同格式

### 第 10 步：迭代改进技能

如果失败是一致的，改进 `skill.md`：
- 添加明确的日期格式示例
- 展示地址转换的样例
- 添加关于电话号码保留原始格式的约束

然后重新运行并比较：

```bash
skilleval run email-extraction
skilleval compare \
  email-extraction/.skilleval/run-<旧时间戳> \
  email-extraction/.skilleval/latest
```

### 为什么这个测试用例有效

这个任务是很好的验证用例，因为：
- **确定性：** 只有一个正确答案
- **非平凡：** 需要日期解析、地址组装和字段映射
- **字段多样：** 测试字符串提取、格式化和结构化输出
- **运行便宜：** 输入内容少，token 使用（和费用）极低

---

## 24. 示例演练

本演练使用内置的 `invoice-extraction` 任务演示端到端的模式 1 评估。

### 任务说明

从纯文本发票中提取结构化数据为 JSON。输入是一张来自"TechBridge Solutions Ltd."的发票，包含 4 个行项目、税金和付款明细。预期输出是包含 `vendor`、`invoice_number`、`line_items`、`subtotal`、`tax_rate` 和 `total` 等字段的 JSON 对象。

### 任务结构

```
sample-tasks/invoice-extraction/
├── config.yaml          # json_exact 比较器，3 次试验，温度 0
├── skill.md             # 带输出 schema 的详细提取指令
├── prompt.md            # 人类可读的任务描述
├── input/
│   └── invoice.txt      # 纯文本发票
└── expected/
    └── result.json      # 预期的 JSON 输出
```

### 第 1 步：查看配置

任务使用：
- `comparator: json_exact` — 输出 JSON 必须与预期精确匹配。
- `trials: 3` — 每个模型 3 次尝试。
- `temperature: 0` — 确定性输出。
- `timeout: 120` — 每次请求 2 分钟超时。

### 第 2 步：检查可用模型

```bash
skilleval catalog
```

假设 `DASHSCOPE_API_KEY` 和 `ZHIPU_API_KEY` 已设置。目录显示通义千问和智谱 GLM 模型为"Ready"。

### 第 3 步：运行评估

```bash
skilleval run sample-tasks/invoice-extraction
```

SkillEval 执行流程：
1. 加载 `skill.md` 作为系统提示词。
2. 读取 `input/invoice.txt` 并格式化为用户消息。
3. 发送给每个可用模型，每个 3 次。
4. 解析每个 JSON 响应并与 `expected/result.json` 比较。
5. 显示结果。

### 第 4 步：查看输出

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

*（示例输出——实际结果取决于模型行为。）*

### 第 5 步：调查失败

对于未达到 100% 的模型，检查试验差异：

```bash
cat sample-tasks/invoice-extraction/.skilleval/run-*/trials/glm-4.5/trial-1/diff.txt
```

这会精确显示输出在哪里偏离了预期。

### 第 6 步：迭代

如果没有模型达到 100%，改进你的 `skill.md`：
- 添加更明确的格式规则。
- 包含边界情况处理。
- 在提示词中提供示例。

然后重新运行评估。

---

## 25. 故障排除 / 常见问题

### "No models available"

**原因：** 未设置任何 API 密钥环境变量。

**解决方法：** SkillEval 现在会显示你需要的确切 `export` 命令。运行 `skilleval catalog` 可查看所有模型及其所需的环境变量。

### "Mode 1 requires skill.md in the task folder"

**原因：** 你运行了 `skilleval run`，但任务文件夹中没有 `skill.md`。

**解决方法：** 创建 `skill.md` 并写入任务的系统提示词。如果你想自动生成技能，请使用模式 2（`matrix`）或模式 3（`chain`）。

### "Mode 2/3 requires prompt.md in the task folder"

**原因：** 你运行了 `matrix` 或 `chain`，但任务文件夹缺少 `prompt.md`。

**解决方法：** 创建 `prompt.md` 并写入人类可读的任务描述。

### "Meta-skill 'X' not found"

**原因：** `--meta-skills` 中的名称与 `meta-skill-*.md` 文件不匹配。

**解决方法：** 确保文件命名为 `meta-skill-<name>.md`（例如 `meta-skill-concise.md` 对应 `--meta-skills concise`）。检查可用变体：
```bash
ls my-task/meta-skill-*.md
```

### 空响应或截断响应

**症状：** 试验以空输出或 `finish_reason: "length"` 失败。

**原因和解决方法：**
- **静默限流：** 供应商返回空响应而非 429。SkillEval 会检测并重试最多 3 次。如果持续发生，减少 `--parallel` 或等待后重试。
- **输出截断：** 模型的响应超过了 `max_tokens`。在 `config.yaml` 中增加 `max_tokens`。
- **超时：** 请求超过了 `timeout` 秒。在 `config.yaml` 中增加 `timeout`。

### 限流错误（429）

**原因：** 对供应商的并发请求过多。

**解决方法：** SkillEval 内置了两级并发控制（全局 + 按供应商）。如果仍然遇到限流：
1. 减少 `--parallel`（例如 `--parallel 5`）。
2. 引擎在收到 429 响应时会自动应用指数退避（1秒、2秒、4秒）加随机抖动，最多重试 3 次。

### JSON 比较失败，但值看起来正确

**可能的原因：**
- **整数 vs 浮点数：** `json_exact` 会将整数归一化为浮点数，因此 `150` 和 `150.0` 匹配。但 `"150"`（字符串）不匹配 `150`（数字）。
- **额外字段：** `json_exact` 要求精确匹配。如果模型输出了额外字段，请改用 `field_subset`。
- **键顺序：** 这不是问题——SkillEval 在比较前会对键进行标准化排序。

### PDF/DOCX/XLSX 文件无法使用

**原因：** 未安装可选依赖。

**解决方法：**
```bash
pip install -e ".[docs]"
# 或单独安装：
pip install pdfplumber python-docx openpyxl
```

### 费用计算

费用计算公式：

```
费用 = (输入 token 数 / 1,000,000 × 每百万输入 token 费用)
     + (输出 token 数 / 1,000,000 × 每百万输出 token 费用)
```

Token 计数来自 API 响应的 `usage` 字段。费用是近似值，因为定价来自模型目录，可能略有过时。

### 推荐逻辑

SkillEval 推荐在所有试验中达到 **100% 通过率**的**最便宜的模型**。`results.json` 中的 `recommendation` 字段设置为最便宜的 100% 通过模型，如果没有符合条件的模型则为 `null`。显示结果时，如果没有模型达到 100%，SkillEval 会打印最佳通过率并建议改进技能或增加试验次数。

如果试验次数少于 10 次，推荐中会包含置信度可能较低的警告。

### 应该运行多少次试验？

- **3–5 次** — 快速筛选，识别有潜力的模型。
- **10–20 次** — 生产级置信度。捕获间歇性失败。
- **50+ 次** — 面向关键任务的统计严谨性。

使用 `temperature: 0.0` 进行确定性任务。即使在温度 0 下，模型偶尔也会由于批处理或内部非确定性而产生不同的输出，这就是多次试验的意义所在。

### "Unknown config keys" 警告

**原因：** 你的 `config.yaml` 包含 SkillEval 无法识别的键名（可能是拼写错误）。

**解决方法：** 查看警告消息中列出的有效键名：`comparator`、`custom_script`、`trials`、`timeout`、`temperature`、`max_tokens`、`output_format`。

### 断路器消息

**原因：** 某个供应商连续出现 5 次失败（错误、超时或空响应）。SkillEval 会自动跳过该供应商的剩余试验，以避免浪费时间和费用。

**解决方法：** 检查供应商的状态页面。如果是限流问题，减少 `--parallel`。断路器会在下一次成功响应时重置。

### 获取机器可读输出

在任何命令上使用 `--json` 可获取适合管道传输的 JSON 输出：

```bash
skilleval run my-task --json | jq '.recommendation'
skilleval catalog --json | jq '.[] | select(.available) | .name'
```

### 使用详细模式调试

使用 `-v` 获取 INFO 级别日志（显示 API 请求 URL、重试尝试），使用 `-vv` 获取 DEBUG 级别日志（完整的请求/响应详情）。日志输出到 stderr，不会干扰 `--json` 输出：

```bash
skilleval -vv run my-task --json 2>debug.log | jq .
```
