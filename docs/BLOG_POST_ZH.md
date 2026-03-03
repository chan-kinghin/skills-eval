# 别再为大模型多花冤枉钱了：SkillEval 帮你找到最便宜的 100% 准确率模型

> 开源 CLI 工具，原生支持通义千问、智谱 GLM、MiniMax，自动化评估确定性任务的最优模型。

---

## 痛点：你可能每天都在为大模型多付几倍的钱

如果你的团队在用大模型做文档提取、数据格式化、结构化输出这类任务，你大概率遇到过这些问题：

**1. 你不知道该用哪个模型。** 通义千问有 3 个档次，智谱 GLM 有 4 个，MiniMax 有 3 个——光国内主流厂商就有 10 个模型可选。旗舰模型输出价格 $6.40/M tokens，而免费模型（glm-4.5-flash）可能就够用了。差距是几十倍。

**2. 手动测试太慢。** 你写好提示词，复制到一个模型的 playground 里试一下，再换一个模型试，对比输出，记录结果。一个任务测下来半天就没了。

**3. 最便宜的模型因任务而异。** 发票提取可能 qwen-turbo 就够了，但合同条款解析可能得用 qwen-max。没有统一答案，只能逐个任务测。

## 解决方案：让机器替你测

[SkillEval](https://github.com/chan-kinghin/skills-eval) 是一个开源 CLI 工具，专门解决这个问题。你提供输入文件、预期输出和提示词，它会：

- **并行测试所有模型**（10 个模型同时跑，带并发控制）
- **自动对比输出与标准答案**（支持 JSON 精确匹配、CSV、子集匹配等 6 种比较策略）
- **追踪每个模型的费用和延迟**
- **推荐达到 100% 准确率的最低成本模型**

核心理念很简单：对于确定性任务，模型要么做对，要么做错。不需要人工评判，机器就能自动验证。

## 30 秒看懂工作流程

```bash
# 安装
pip install -e .

# 设置 API 密钥（设哪个就测哪家）
export DASHSCOPE_API_KEY="sk-..."
export ZHIPU_API_KEY="..."

# 创建任务
skilleval init invoice-extraction

# 编辑 input/、expected/ 和 skill.md，然后运行
skilleval run invoice-extraction
```

SkillEval 会输出一张清晰的结果表：每个模型的通过率、平均费用、延迟，以及最终推荐。如果 glm-4.5-flash（免费）就能 100% 完成你的任务，它会告诉你——不用再花钱用旗舰模型了。

## 三种评估模式，覆盖不同场景

**模式 1（run）** 最常用：你写好提示词，SkillEval 跨 10 个模型测试，找到最便宜的能做对的。

**模式 2（matrix）** 更进一步：让一个模型写提示词，另一个执行。测试所有"创建者 x 执行者"组合，发现你可能想不到的最优搭配。

**模式 3（chain）** 完整流水线：元技能指导提示词创建，再由另一个模型执行。当你想自动化整个流程时使用。

## 原生支持国内三大模型厂商

这是 SkillEval 对中文开发者最直接的价值：**开箱即用支持通义千问（DashScope）、智谱 GLM、MiniMax**。

不需要自己封装 API，不需要处理各家的认证差异。设置环境变量，直接 `skilleval run`。默认模型目录已经包含 10 个模型的完整定价信息，从免费到旗舰全覆盖。

同时支持任何 OpenAI 兼容 API（通过 `--endpoint` 参数），包括本地部署的 Ollama 模型。

## 生产级可靠性

SkillEval 不是一个玩具项目。它考虑了实际生产环境的需求：

- **熔断机制**：某个厂商连续失败 5 次后自动跳过，不浪费时间和钱
- **Ctrl+C 处理**：中断时保存已有结果，不丢失半完成的运行
- **--json 输出**：直接接入 CI/CD 流水线
- **HTML 报告**：生成独立的可视化报告，方便分享给非技术同事
- **进度条带 ETA**：跑大规模评估时心里有数
- **友好的错误提示**：默认不输出堆栈，`-vv` 才会显示调试信息

## 快速开始（5 行搞定）

```bash
git clone https://github.com/chan-kinghin/skills-eval && cd skills-eval
pip install -e .
export DASHSCOPE_API_KEY="sk-..."        # 或 ZHIPU_API_KEY / MINIMAX_API_KEY
skilleval init my-task                    # 创建任务模板
# 编辑 input/、expected/、skill.md 后：
skilleval run my-task
```

## 试一试，给个 Star

SkillEval 是 MIT 许可的开源项目，Python 3.11+，无重型依赖。

- GitHub: https://github.com/chan-kinghin/skills-eval
- 完整中文文档和用户手册已就绪
- 欢迎提 Issue、PR，或在 GitHub 上 Star 支持

如果你的团队每天都在调用大模型 API，花 10 分钟跑一次 SkillEval，可能每月能省下不少费用。试试看。
