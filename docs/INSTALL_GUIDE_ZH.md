# SkillEval 安装指南

[English](INSTALL_GUIDE.md) | [中文](INSTALL_GUIDE_ZH.md)

> 找到能 100% 完成你任务的最便宜 LLM。

---

## 1. 环境要求

- **Python 3.11 或更高版本**（使用了 `str | None` 联合类型语法）
- **pip**（Python 3.11+ 自带）

检查 Python 版本：

```bash
python3 --version
# 需要 Python 3.11.0 或更高版本
```

如果需要安装 Python 3.11+，访问 [python.org/downloads](https://www.python.org/downloads/) 或使用包管理器：

```bash
# macOS (Homebrew)
brew install python@3.12

# Ubuntu/Debian
sudo apt install python3.12

# Windows (winget)
winget install Python.Python.3.12
```

---

## 2. 安装

```bash
pip install skilleval
```

验证安装：

```bash
skilleval --version
```

### 可选：文档提取支持

如需处理 PDF、Word 和 Excel 输入文件：

```bash
pip install "skilleval[docs]"
```

这会额外安装 `pdfplumber`、`python-docx` 和 `openpyxl`。

---

## 3. 快速配置

### 设置 API 密钥

SkillEval 至少需要一个服务商的 API 密钥。设置你拥有的密钥：

```bash
# 通义千问（阿里云 DashScope）
export DASHSCOPE_API_KEY="sk-..."

# 智谱 GLM
export ZHIPU_API_KEY="..."

# MiniMax
export MINIMAX_API_KEY="..."

# OpenAI（可选）
export OPENAI_API_KEY="sk-..."

# DeepSeek（可选）
export DEEPSEEK_API_KEY="..."
```

建议将以上配置添加到你的 shell 配置文件（`~/.bashrc`、`~/.zshrc` 等），使其持久生效。

### 验证模型可用性

```bash
skilleval catalog
```

拥有有效 API 密钥的模型显示为 **Ready**，没有密钥的显示为 **No Key**。至少需要一个 Ready 状态的模型才能运行评估。

---

## 4. 第一次评估

下面完整演示一个示例：从文本中提取发票信息。

### 第 1 步：创建任务目录

```bash
skilleval init invoice-demo
```

生成以下结构：

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

### 第 2 步：创建输入文件

用实际输入替换占位文件：

```bash
cat > invoice-demo/input/invoice.txt << 'EOF'
发票
公司名称：极光科技有限公司
发票编号：INV-2026-0042
日期：2026-03-01
金额：¥8,750.00

明细：
- 组件 A（x10）：¥3,500.00
- 组件 B（x5）：¥5,250.00

付款条件：30 天内付款
EOF
```

删除占位文件：

```bash
rm invoice-demo/input/sample.txt
```

### 第 3 步：创建期望输出

```bash
cat > invoice-demo/expected/invoice.txt << 'EOF'
{"invoice_number": "INV-2026-0042", "company": "极光科技有限公司", "date": "2026-03-01", "total": 8750.00, "items": [{"name": "组件 A", "quantity": 10, "amount": 3500.00}, {"name": "组件 B", "quantity": 5, "amount": 5250.00}]}
EOF
```

删除占位文件：

```bash
rm invoice-demo/expected/sample.txt
```

### 第 4 步：编写技能提示词（Skill）

编辑 `invoice-demo/skill.md`：

```markdown
# 发票信息提取

从发票文本中提取结构化数据。返回一个 JSON 对象，包含以下字段：

- `invoice_number`（字符串）：发票编号
- `company`（字符串）：公司名称
- `date`（字符串）：发票日期，格式为 YYYY-MM-DD
- `total`（数字）：总金额（不含货币符号）
- `items`（数组）：每项包含 `name`（字符串）、`quantity`（数字）、`amount`（数字）

仅返回 JSON 对象。不要 markdown、不要解释、不要代码围栏。
```

### 第 5 步：配置比较器

编辑 `invoice-demo/config.yaml`：

```yaml
comparator: json_exact
trials: 3
timeout: 60
temperature: 0.0
max_tokens: 4096
output_format: json
```

### 第 6 步：运行评估

```bash
skilleval run invoice-demo
```

SkillEval 将你的技能提示词和输入发送给每个可用模型，每个模型运行 3 次，并将每次响应与期望输出进行比较。

---

## 5. 理解结果

运行结束后，SkillEval 显示如下表格：

```
┌──────────────────┬───────────┬──────────┬─────────────┬────────────┬─────┐
│ Model            │ Pass Rate │ Avg Cost │ Avg Latency │ Total Cost │ Rec │
├──────────────────┼───────────┼──────────┼─────────────┼────────────┼─────┤
│ glm-4.5-flash    │ 100%      │ $0.0000  │ 1.8s        │ $0.0000    │  *  │
│ qwen-turbo       │ 100%      │ $0.0001  │ 1.1s        │ $0.0003    │     │
│ qwen-plus        │ 67%       │ $0.0008  │ 1.9s        │ $0.0024    │     │
└──────────────────┴───────────┴──────────┴─────────────┴────────────┴─────┘

推荐：glm-4.5-flash（$0.0000/次，100% 通过率）
```

| 列 | 含义 |
|------|------|
| **Pass Rate** | 与期望输出完全匹配的试验占比 |
| **Avg Cost** | 每次试验的平均费用（美元） |
| **Avg Latency** | 每次试验的平均响应时间 |
| **Total Cost** | 该模型所有试验的总费用 |
| **Rec** | `*` 标记推荐的模型 |

**推荐逻辑**：SkillEval 选择通过率为 100% 的最便宜模型。如果没有模型达到 100%，则不给出推荐——请改进你的技能提示词后重新运行。

结果保存在 `invoice-demo/.skilleval/run-<时间戳>/` 目录下，方便后续查看。

---

## 6. 三种评估模式

### 模式 1：技能评估（`run`）

你编写提示词，SkillEval 在多个模型上测试。

```bash
skilleval run my-task
skilleval run my-task --models qwen-turbo,glm-4.5-flash --trials 10
```

**适用场景**：你已有一个好的提示词，想找到最便宜的可用模型。

### 模式 2：矩阵评估（`matrix`）

创作模型编写提示词，执行模型运行提示词，结果形成矩阵。

```bash
skilleval matrix my-task \
  --creators qwen-max,glm-5 \
  --executors qwen-turbo,glm-4.5-flash
```

**适用场景**：探索是否可以用廉价模型编写提示词，让更廉价的模型执行。

**需要**：`prompt.md`（任务描述）代替 `skill.md`。

### 模式 3：链式评估（`chain`）

元技能指导创作模型如何编写提示词，增加一层优化。

```bash
skilleval chain my-task \
  --meta-skills concise,detailed \
  --creators qwen-max \
  --executors qwen-turbo,glm-4.5-flash
```

**适用场景**：测试不同的提示词生成策略。

**需要**：`prompt.md` 和 `meta-skill-<名称>.md` 文件。

---

## 7. 高级用法

### JSON 输出用于管道

所有命令支持 `--output json`（或 `--json` 简写）输出机器可读的 JSON：

```bash
skilleval run my-task --output json | jq '.recommendation'
skilleval catalog --json | jq '.[] | select(.available) | .name'
```

也支持 CSV 输出（`run`、`matrix`、`chain` 命令）：

```bash
skilleval run my-task --output csv > results.csv
```

### 自定义 OpenAI 兼容接口

无需修改目录即可测试任意模型：

```bash
# 本地 Ollama 模型
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

### HTML 报告

从任何历史运行生成独立 HTML 报告：

```bash
skilleval report my-task/.skilleval/run-20260301-120000 --html report.html --open
```

### 比较两次运行

调整技能提示词后，比较前后结果：

```bash
skilleval compare \
  my-task/.skilleval/run-20260301-120000 \
  my-task/.skilleval/run-20260302-090000
```

显示每个模型的通过率变化（改善、退步、不变）。

### 详细 / 调试模式

```bash
skilleval -v run my-task      # INFO 级别日志
skilleval -vv run my-task     # DEBUG 级别日志（完整请求/响应）
```

日志输出到 stderr，不影响 `--json` 输出：

```bash
skilleval -vv run my-task --output json 2>debug.log | jq .
```

---

## 8. 配置参考

每个任务目录包含一个 `config.yaml` 控制评估行为。

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `comparator` | string | `json_exact` | 输出与期望的比较方式 |
| `custom_script` | string | `null` | 自定义比较器脚本路径 |
| `trials` | int | `5` | 每个模型的试验次数 |
| `timeout` | int | `60` | API 请求超时（秒） |
| `temperature` | float | `0.0` | 采样温度（`0.0` = 确定性输出） |
| `max_tokens` | int | `4096` | 每次请求的最大输出 token 数 |
| `output_format` | string | `json` | 期望输出格式（用于显示） |

### 比较器

| 比较器 | 说明 |
|--------|------|
| `json_exact` | JSON 深度相等（默认）。整数/浮点数自动转换。键必须完全匹配。 |
| `csv_ordered` | 逐行 CSV 比较。行序有关。 |
| `csv_unordered` | 集合式 CSV 比较。行序无关。 |
| `field_subset` | 检查期望字段是否存在于输出中。允许额外字段。 |
| `file_hash` | 字节级 SHA-256 比较。 |
| `custom` | 运行用户脚本。需在配置中设置 `custom_script`。 |

### config.yaml 示例

```yaml
comparator: json_exact
trials: 10
timeout: 120
temperature: 0.0
max_tokens: 8192
output_format: json
```

---

## 9. 常见问题排查

### "No models available"

没有设置 API 密钥。运行 `skilleval catalog` 查看需要哪些环境变量，然后至少导出一个：

```bash
export ZHIPU_API_KEY="your-key-here"
```

### Python 版本错误

SkillEval 需要 Python 3.11+。使用 `python3 --version` 检查。如果有多个版本：

```bash
python3.12 -m pip install skilleval
```

### 网络 / 超时错误

- 在 `config.yaml` 中增加 `timeout`（默认 60 秒）
- 如遇到频率限制，减小 `--parallel`（默认 20）
- 检查服务商状态页面是否有故障

### JSON 比较失败但输出看起来正确

- `json_exact` 要求所有键匹配。输出中的额外键会导致失败。如果允许额外键，使用 `field_subset`。
- 字符串 `"150"` 和数字 `150` 不匹配。检查期望输出的类型。

### PDF/DOCX/XLSX 文件无法处理

安装可选文档依赖：

```bash
pip install "skilleval[docs]"
```

### 空响应

- 模型可能被静默限流。减小 `--parallel`。
- 检查试验结果中的 `finish_reason`——`length` 表示输出被截断。增加 `max_tokens`。

---

## 10. 升级

```bash
pip install --upgrade skilleval
```

检查新版本：

```bash
skilleval --version
```

---

## 11. 卸载

```bash
pip uninstall skilleval
```

这只移除 `skilleval` CLI 和 Python 包。你的任务目录和运行结果不受影响。

---

## 链接

- **GitHub**: [github.com/chan-kinghin/skills-eval](https://github.com/chan-kinghin/skills-eval)
- **PyPI**: [pypi.org/project/skilleval](https://pypi.org/project/skilleval/)
- **完整用户手册**: [docs/USER_MANUAL_ZH.md](USER_MANUAL_ZH.md)
- **问题反馈**: [github.com/chan-kinghin/skills-eval/issues](https://github.com/chan-kinghin/skills-eval/issues)
