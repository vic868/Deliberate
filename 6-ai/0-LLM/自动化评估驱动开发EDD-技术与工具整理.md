# 自动化评估驱动开发（EDD）技术与工具全景

> Evals-Driven Development（EDD）已成为大模型与 RAG（检索增强生成）系统走向生产环境的核心范式。传统的"肉眼测试"（Vibe Check）无法量化复杂链路的性能，EDD 通过工程化、自动化的手段确保模型迭代稳定性与安全性。

---

## 一、核心概念

| 概念 | 说明 |
|---|---|
| EDD（Evals-Driven Development） | 自动化评估驱动开发：以可量化指标替代主观判断，驱动 LLM/RAG 系统迭代 |
| Vibe Check | 传统"肉眼测试"，无法量化、不可复现，已不适应生产要求 |
| LLM-as-a-Judge | 用更强的模型（如 GPT-4）或轻量专用模型为被测系统输出打分 |
| RAG 三元组（RAG Triad） | Query-Context-Answer 三者间关系的量化评估体系 |
| Red Teaming | 自动化对抗测试：用"坏数据"逼近系统极限 |
| Golden Dataset | 覆盖核心业务场景与边界条件的标准评测样本集 |
| 回归问题（Regression） | 修复 Bug A 导致原本正常的场景 B 崩盘；CI 卡点是解药 |

---

## 二、评估框架：告别肉眼测试

**核心目的**：将主观的语言质量转化为客观的数理指标；普遍采用 LLM-as-a-Judge 机制。

| 工具 | 定位 | 核心能力 | 适用场景 |
|---|---|---|---|
| **Ragas** | RAG 专项评估框架 | 清晰的"RAG 三元组"评估算法，开箱即用的指标 | 开发早期的基准测试（Benchmarking） |
| **TruLens** | RAG 评估与可视化 | 提出"RAG Triad"概念；可视化评估链路；易集成到生产监控 | 调试阶段 + 生产监控 |
| **Arize Phoenix** | AI 观测性（Observability）+ 评估 | 大规模数据追踪（Tracing）与评估 | 与 CI/CD、生产监控深度绑定 |

---

## 三、核心黄金指标：RAG 三元组

评估 RAG 系统时，必须将 **问题（Query）、上下文（Context）、回答（Answer）** 拆解评估：

```
        [ 问题 (Query) ]
        /             \
Context Relevance   Answer Relevance
      /                   \
[上下文 (Context)] ------> [回答 (Answer)]
            Faithfulness (抗幻觉)
```

### 指标明细

| 指标 | 评估对象 | 核心目的 | 计算逻辑 |
|---|---|---|---|
| **Faithfulness**（忠实度 / 抗幻觉） | 回答是否忠实于上下文 | 杜绝幻觉：回答再完美，只要超出检索到的上下文范围，得分即降低 | 检查回答中的每个断言（Claim）是否能在上下文中找到直接证据 |
| **Answer Relevance**（回答相关性） | 回答是否直接回应问题 | 防止答非所问或夹带无关废话 | 裁判 LLM 根据答案反推问题，对比反推问题与原问题的相似度 |
| **Context Precision**（上下文精准度） | 检索上下文与问题的相关度 | 评估检索模块（Retrieval）质量；召回噪音会稀释模型注意力 | 评估有用信息是否排在检索结果前列（类似 Mean Reciprocal Rank） |

---

## 四、边界测试（Red Teaming）：自动化攻防

**原则**：不仅测"好模型"，更要用"坏数据"逼近系统极限；用大模型充当红队攻击者。

| 测试类型 | 手段 | 验证目标 |
|---|---|---|
| **对抗性问题生成**（Adversarial QA） | LLM 挖掘知识库模糊地带，自动生成语义含糊、预设前提错误（Premise Missing）、逻辑陷阱问题 | 系统对模糊/陷阱输入的鲁棒性 |
| **越狱指令测试**（Jailbreak Attacks） | 自动构造角色扮演（"你是不受限制的 AI"）、间接提示词注入（Prompt Injection）指令 | 安全围栏（Guardrails）是否会被突破 |
| **压力测试** | 批量生成极端长度输入、火星文、多语言混杂输入 | Token 边界与鲁棒性 |

---

## 五、持续集成（CI/CD）：防止能力衰退

**痛点**：修复 Bug A 导致场景 B 崩盘（回归）。将 Evals 固化进 CI/CD 流水线是终极方案。

### 落地四步

1. **构建黄金数据集（Golden Dataset）**：筛选 100~500 个覆盖核心业务场景与边界条件的标准样本（标准 Query + 预期 Context/Answer）。
2. **触发流水线**：修改 System Prompt / 更换 Embedding 模型 / 调整微调参数 / 更改 Chunk 切分策略时，自动触发 GitHub Actions / GitLab CI。
3. **自动化打分与断言（Assertion）**：并发调用评估脚手架测试黄金数据集，设定硬性阈值（如 Faithfulness > 0.85，Answer Relevance 变动率 ≥ -2%）。
4. **卡点与准入**：得分低于阈值 → CI 报错并拒绝合入（Block PR），告别凭感觉上线。

### 技术与工具速查

| 环节 | 技术 / 工具 | 作用 |
|---|---|---|
| 评估框架 | Ragas | RAG 三元组基准测试 |
| | TruLens | RAG Triad 概念 + 评估链路可视化 + 生产监控集成 |
| | Arize Phoenix | 观测性 + Tracing + 大规模评估 + CI/CD 绑定 |
| 打分机制 | LLM-as-a-Judge（GPT-4 等） | 用强模型为输出自动打分 |
| 核心指标 | Faithfulness | 抗幻觉：回答是否忠于上下文 |
| | Answer Relevance | 反推问题对比相似度，防答非所问 |
| | Context Precision | 检索质量，类 MRR 排序评估 |
| 对抗测试 | LLM Red Teaming | 自动生成对抗问题 / 越狱 / 压力输入 |
| 集成 | GitHub Actions / GitLab CI | 评估自动化 + 阈值断言 + Block PR 卡点 |
| 数据资产 | Golden Dataset（100~500 样本） | 回归测试的标准基线 |

---

*整理时间：2026-11-04*
