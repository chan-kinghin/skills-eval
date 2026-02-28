# SkillEval

[English](README.md) | [中文](README_ZH.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)

**找到能 100% 完成你任务的最便宜的大模型。**

SkillEval 是一个 CLI 工具，用于自动化评估大语言模型在确定性任务上的表现。它会并行地将你的任务发送给多个模型，将输出与预期结果进行对比，并推荐最具性价比的选项。

## 快速开始

```bash
pip install -e .

# 设置至少一个供应商的 API 密钥
export DASHSCOPE_API_KEY="sk-..."   # 通义千问（阿里云 DashScope）

# 创建任务文件夹
skilleval init my-task

# 添加输入文件、预期输出和技能提示词
# 然后运行评估
skilleval run my-task/
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
