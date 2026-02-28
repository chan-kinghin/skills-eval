# 贡献指南

[English](CONTRIBUTING.md) | [中文](CONTRIBUTING_ZH.md)

感谢你有兴趣参与贡献！本指南将帮助你快速上手。

## 开发环境搭建

```bash
git clone <repo-url>
cd skills-eval
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,docs]"
```

## 运行测试和代码检查

```bash
pytest                    # 运行所有测试（离线运行，无需 API 密钥）
ruff check src/ tests/    # 代码风格检查
```

提交 PR 前所有测试必须通过。CI 流水线会在 Python 3.11、3.12 和 3.13 上同时运行代码检查和测试。

## 项目结构

```
src/skilleval/
├── cli.py              # Click CLI 命令（init、run、matrix、chain、catalog、report、lint、compare、skill-test）
├── config.py           # 任务文件夹加载、模型目录、过滤、临时模型构建
├── client.py           # 异步 OpenAI 兼容 HTTP 客户端，支持重试
├── engine.py           # 并发控制（全局 + 按供应商信号量）
├── runner.py           # 模式 1/2/3 编排器
├── models.py           # Pydantic 数据模型（共享契约）
├── documents.py        # PDF/DOCX/XLSX 文本提取
├── display.py          # Rich 控制台输出辅助工具
├── results.py          # 结果文件写入器
├── linter.py           # Claude Code 技能结构验证
├── skill_parser.py     # 技能提示词提取和测试用例加载
├── compare.py          # 运行比较 / 退化检测
├── html_report.py      # 独立 HTML 报告生成
├── default_models.yaml # 内置模型目录
└── comparators/
    ├── __init__.py     # 注册表和工厂函数（get_comparator）
    ├── base.py         # 比较器协议，辅助函数（去除代码块/标签、文件配对）
    ├── json_exact.py   # JSON 深度相等比较，支持 int/float 归一化
    ├── csv_ordered.py  # 逐行 CSV 匹配
    ├── csv_unordered.py# 多重集（Counter）CSV 匹配
    ├── field_subset.py # 递归的"预期 ⊆ 输出"子集检查
    ├── file_hash.py    # SHA-256 字节级比较
    └── custom.py       # 运行外部脚本进行比较
```

## 如何添加供应商

无需修改代码。在 `default_models.yaml` 中添加一条记录即可：

```yaml
- name: my-new-model
  provider: my-provider
  endpoint: https://api.example.com/v1
  input_cost_per_m: 0.5
  output_cost_per_m: 1.5
  env_key: MY_PROVIDER_API_KEY
  context_window: 128000
```

接口必须兼容 OpenAI（`/chat/completions`）。设置好环境变量后，模型会自动出现在 `skilleval catalog` 中。

## 如何添加比较器

1. 创建 `src/skilleval/comparators/my_comparator.py`：

```python
from pathlib import Path
from skilleval.comparators.base import get_file_pairs

class MyComparator:
    def compare(self, output_dir: Path, expected_dir: Path) -> tuple[bool, str | None]:
        pairs = get_file_pairs(output_dir, expected_dir)
        # ... 你的比较逻辑 ...
        return True, None  # (是否通过, 差异文本或None)
```

2. 在 `src/skilleval/comparators/__init__.py` 中注册：

```python
from skilleval.comparators.my_comparator import MyComparator

COMPARATORS["my_comparator"] = MyComparator
```

3. 在 `tests/test_comparators/test_my_comparator.py` 中添加测试。

## 代码风格

- 使用 Python 3.11+ 语法（`str | None`，而非 `Optional[str]`）
- 使用 [ruff](https://docs.astral.sh/ruff/) 进行格式化和代码检查
- 行宽限制：100 字符
- 测试使用 `pytest`，配合 `tmp_path` fixture 进行文件系统测试
