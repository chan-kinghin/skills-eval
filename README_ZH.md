# SkillEval

[English](README.md) | [中文](README_ZH.md)

[![PyPI version](https://img.shields.io/pypi/v/skilleval.svg)](https://pypi.org/project/skilleval/)
[![PyPI downloads](https://img.shields.io/pypi/dm/skilleval.svg)](https://pypi.org/project/skilleval/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)

**找到能 100% 完成你任务的最便宜的大模型。**

SkillEval 是一个 CLI 工具，用于自动化评估大语言模型在确定性任务上的表现。它会并行地将你的任务发送给多个模型，将输出与预期结果进行对比，并推荐最具性价比的选项。

## 快速开始

```bash
pip install skilleval

# 设置至少一个供应商的 API 密钥
export DASHSCOPE_API_KEY="sk-..."   # 通义千问（阿里云 DashScope）

# 创建任务文件夹
skilleval init my-task

# 添加输入文件、预期输出和技能提示词
# 然后运行评估
skilleval run my-task/

# 机器可读输出
skilleval run my-task/ --json | jq '.recommendation'
```

## 支持的供应商

| 供应商      | 平台                       | 环境变量               |
|------------|---------------------------|----------------------|
| **通义千问** | 阿里云 / DashScope         | `DASHSCOPE_API_KEY`  |
| **智谱 GLM** | 智谱 AI / BigModel        | `ZHIPU_API_KEY`      |
| **MiniMax** | MiniMax                   | `MINIMAX_API_KEY`    |

## 评估模式

- **模式 1（`run`）** — 你编写提示词（skill），SkillEval 在多个模型上测试它。
- **模式 2（`matrix`）** — 一个模型编写提示词，另一个模型执行。测试所有创建者 x 执行者的组合。
- **模式 3（`chain`）** — 元技能（meta-skill）指导提示词的创建，然后由另一个模型执行。完整流水线评估。

## 附加功能

- **临时端点** — 无需修改模型目录即可使用任何 OpenAI 兼容 API：`--endpoint`、`--api-key`、`--model-name`。
- **技能检查（`lint` / `--skill-format claude`）** — 验证 Claude Code 技能结构（frontmatter、阶段、引用、代码块）。在 `run`/`matrix`/`chain` 上使用 `--skill-format claude` 可同时获得 `lint_score`（0-100）。
- **技能测试（`skill-test`）** — 将技能的核心提示逻辑与预期输出进行测试。
- **运行比较（`compare`）** — 对比两次运行结果以检测改进或退化。
- **HTML 报告（`report --html`）** — 生成独立的 HTML 报告以便分享。
- **JSON 输出（`--json`）** — 在 `run`、`matrix`、`chain`、`catalog` 和 `report` 命令上输出机器可读的 JSON，方便与其他工具管道对接。
- **详细日志（`-v` / `-vv`）** — `-v` 显示 INFO 级别，`-vv` 显示 DEBUG 级别。日志输出到 stderr，不会干扰 `--json` 输出。
- **自动确认（`--yes` / `-y`）** — 跳过 `chain` 命令的确认提示（替代原来的 `--confirm` 参数）。
- **配置校验** — 对 `config.yaml` 中的未知键发出警告，并在加载时验证比较器名称。
- **熔断机制** — 某个供应商连续失败 5 次后自动跳过，避免浪费时间和费用。
- **Ctrl+C 处理** — 中断时保存已有结果，避免丢失未完成的运行数据。
- **交互式 TUI** — 不带参数运行 `skilleval` 即可进入引导式交互模式。
- **上下文窗口追踪** — 结果包含每个模型的上下文窗口大小，便于比较。
- **国际化** — 完整支持中英文界面（在设置中配置 `language: zh` 或通过 `LANG` 环境变量）。
- **友好的错误提示** — 默认不显示原始堆栈信息；使用 `-vv` 可查看完整的错误追踪。
- **进度条** — 显示已用时间和预计剩余时间。

## 文档

详细的安装说明、配置选项、比较器参考和操作指南，请参阅[用户手册](docs/USER_MANUAL_ZH.md)（[English](docs/USER_MANUAL.md)）。

## 开发

```bash
pip install -e ".[dev,docs]"
pytest
ruff check src/ tests/
```

完整的贡献指南请参阅 [CONTRIBUTING_ZH.md](CONTRIBUTING_ZH.md)（[English](CONTRIBUTING.md)）。

## 许可证

[MIT](LICENSE)
