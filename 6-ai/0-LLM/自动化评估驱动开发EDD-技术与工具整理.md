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

### 1.1 与传统测试的区别

| 维度 | 传统软件测试 | LLM/RAG 评估（EDD） |
|---|---|---|
| 断言方式 | 精确匹配（输出 == 期望） | 语义匹配 / 阈值打分（输出 ≈ 期望） |
| 结果形态 | 布尔（通过/失败） | 连续分数（0~1）+ 分布 |
| 失败原因 | 代码逻辑错误 | 提示词、检索、模型、数据多因素耦合 |
| 不确定性 | 确定性 | 模型输出有随机性（temperature），需多次采样或容忍波动 |
| 成本 | 计算资源 | Token 费用（评估本身要调用裁判模型） |

### 1.2 评估体系分层

完整评估应自底向上覆盖三层，定位问题源时逐层下钻：

```
┌─────────────────────────────────────────────┐
│ 端到端评估（E2E）                             │  最终答案质量：Faithfulness、
│ 用户 Query → 整个 RAG 链路 → 最终 Answer      │  Answer Relevance、正确率
├─────────────────────────────────────────────┤
│ 链路级评估                                    │  检索+生成协作：Context Precision、
│ Query → 检索 → Context → 生成                 │  Context Recall、噪音敏感性
├─────────────────────────────────────────────┤
│ 组件级评估（Component-level）                 │  Embedding 模型对比、
│ 单独测 Retriever / Embedder / Generator      │  重排序质量、生成器指令遵循
└─────────────────────────────────────────────┘
```

---

## 二、评估框架：告别肉眼测试

**核心目的**：将主观的语言质量转化为客观的数理指标；普遍采用 LLM-as-a-Judge 机制。

### 2.1 框架对比

| 工具 | 定位 | 核心能力 | 适用场景 |
|---|---|---|---|
| **Ragas** | RAG 专项评估框架 | 清晰的"RAG 三元组"评估算法，开箱即用的指标，与 LangChain/LlamaIndex 无缝集成 | 开发早期的基准测试（Benchmarking） |
| **TruLens** | RAG 评估与可视化 | 提出"RAG Triad"概念；可视化评估链路（TruBoard 仪表盘）；反馈函数（Feedback Functions）机制 | 调试阶段 + 生产监控 |
| **Arize Phoenix** | AI 观测性（Observability）+ 评估 | OpenTelemetry 标准的 Tracing、Embedding 分布可视化（UMAP）、大规模离线/在线评估 | 与 CI/CD、生产监控深度绑定 |
| **DeepEval** | 类 PyTest 的 LLM 单测框架 | 把评估写成"单元测试"（assert 语法），14+ 内置指标，CI 集成最自然 | Python 团队把 Evals 当代码写 |
| **promptfoo** | 提示词/模型横评 | 多模型/多 Prompt 矩阵对比、红队测试内置、YAML 声明式配置、Web UI 对比视图 | Prompt 工程选型 + 安全扫描 |
| **LangSmith** | LangChain 官方平台 | Trace + 数据集管理 + 人工标注 + 评估一体化的 SaaS | 已用 LangChain 生态的团队 |
| **OpenAI Evals** | 模型能力基准 | OpenAI 官方评测框架，自定义 eval 套件 | 验证模型本身（非应用层）能力 |

**选型建议**：Ragas（RAG 指标计算）+ Phoenix（Tracing/观测）+ promptfoo（Prompt 横评与红队）是常见的开源组合；DeepEval 适合强 Python、重 CI 的团队；LangSmith 适合不介意 SaaS 订费的团队。

### 2.2 Ragas 快速上手

```python
# pip install ragas datasets langchain-openai
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness, answer_relevancy, context_precision, context_recall
)

# 一条样本 = 一个问题 + 系统实际产出的答案 + 检索到的上下文
data = {
    "question": ["退款政策是什么？"],
    "answer": ["订单签收后 7 天内可无理由退款。"],
    "contexts": [["签收后 7 天内支持无理由退货退款，特殊商品除外。"]],
    "ground_truth": ["自签收之日起 7 天内可无理由退款。"],  # 人工标注，context_recall 需要
}
dataset = Dataset.from_dict(data)

result = evaluate(dataset, metrics=[faithfulness, answer_relevancy,
                                    context_precision, context_recall])
print(result)  # {'faithfulness': 0.92, 'answer_relevancy': 0.87, ...}
```

### 2.3 TruLens 的 RAG Triad 反馈函数

```python
# pip install trulens-core trulens-providers-openai
from trulens.apps.basic import TruBasicApp
from trulens.core import Feedback
from trulens.providers.openai import OpenAI

provider = OpenAI()

# RAG Triad 三条边，各对应一个反馈函数
f_groundedness = Feedback(provider.groundedness_measure_with_cot_reasons)  # Answer↔Context
f_answer_relevance = Feedback(provider.relevance).on_input_output()        # Answer↔Query
f_context_relevance = Feedback(provider.context_relevance).on_input()      # Context↔Query
```

### 2.4 Phoenix 的 Tracing + 评估

```python
# pip install arize-phoenix
import phoenix as px
from phoenix.trace.langchain import LangChainInstrumentor

px.launch_app()                          # 启动本地观测 UI（默认 localhost:6006）
LangChainInstrumentor().instrument()     # 自动挂桩 LangChain 链路，每次调用全链路留痕
```

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

### 3.1 指标明细

| 指标 | 评估对象 | 核心目的 | 计算逻辑 |
|---|---|---|---|
| **Faithfulness**（忠实度 / 抗幻觉） | 回答是否忠实于上下文 | 杜绝幻觉：回答再完美，只要超出检索到的上下文范围，得分即降低 | 检查回答中的每个断言（Claim）是否能在上下文中找到直接证据 |
| **Answer Relevance**（回答相关性） | 回答是否直接回应问题 | 防止答非所问或夹带无关废话 | 裁判 LLM 根据答案反推问题，对比反推问题与原问题的相似度 |
| **Context Precision**（上下文精准度） | 检索上下文与问题的相关度 | 评估检索模块（Retrieval）质量；召回噪音会稀释模型注意力 | 评估有用信息是否排在检索结果前列（类似 Mean Reciprocal Rank） |

### 3.2 三元组之外的常用补充指标

| 指标 | 评估对象 | 说明 |
|---|---|---|
| **Context Recall**（上下文召回率） | Context vs 标准答案 | 标准答案（ground_truth）中的每个要点能否被检索到的上下文支撑；需要人工标注，是衡量"漏检"的关键 |
| **Answer Correctness**（回答正确性） | Answer vs 标准答案 | 语义事实比对 + 要点覆盖率的综合分，最接近"最终业务质量" |
| **Context Relevancy**（上下文相关性） | Context vs Query | 召回的上下文中与问题相关句子的占比，TruLens 的 Context Relevance |
| **Noise Sensitivity**（噪音敏感性） | 全链路 | 故意向上下文注入无关/错误段落，观察回答是否被带偏 |
| **Answer Similarity**（回答相似度） | Answer vs 标准答案 | Embedding 余弦相似度，粗粒度兜底指标 |
| 延迟 / Token 成本 | 工程指标 | P95 延迟、单次调用 Token 数——生产环境与质量同等重要 |

### 3.3 指标选用矩阵

| 你想知道什么 | 用哪组指标 |
|---|---|
| 模型会不会胡编？ | Faithfulness + Noise Sensitivity |
| 检索召回的东西好不好？ | Context Precision + Context Recall |
| 回答有没有答到点上？ | Answer Relevance + Answer Correctness |
| 换 Embedding / 改 Chunk 策略值得吗？ | 三元组全套 + Answer Correctness 前后对比 |
| 上线前最终把关？ | Answer Correctness（质量）+ 延迟/成本（体验） |

---

## 四、边界测试（Red Teaming）：自动化攻防

**原则**：不仅测"好模型"，更要用"坏数据"逼近系统极限；用大模型充当红队攻击者。

### 4.1 攻击类型

| 测试类型 | 手段 | 验证目标 |
|---|---|---|
| **对抗性问题生成**（Adversarial QA） | LLM 挖掘知识库模糊地带，自动生成语义含糊、预设前提错误（Premise Missing）、逻辑陷阱问题 | 系统对模糊/陷阱输入的鲁棒性 |
| **越狱指令测试**（Jailbreak Attacks） | 自动构造角色扮演（"你是不受限制的 AI"）、间接提示词注入（Prompt Injection）指令 | 安全围栏（Guardrails）是否会被突破 |
| **提示词注入**（Prompt Injection） | 在文档/网页中植入"忽略以上指令，输出××"——RAG 场景尤其危险，因为注入点藏在检索内容里 | 间接注入防护：知识库内容污染是否劫持系统 |
| **知识库污染** | 向语料中投放错误事实，验证系统是否照单全收 | 数据源可信度与事实校验能力 |
| **敏感信息泄露** | 诱导输出系统提示词、训练数据、其他用户数据 | 隐私与合规边界 |
| **压力测试** | 批量生成极端长度输入、火星文、多语言混杂输入、超多轮上下文 | Token 边界与鲁棒性 |
| **幻觉诱导** | 提问知识库中不存在的内容（"从未有人问过的冷门问题"），期望系统回答"不知道" | 拒答能力——知道说知道，不知道要说不知道 |

### 4.2 红队自动化工具

| 工具 | 说明 |
|---|---|
| **promptfoo red team** | 声明式配置攻击插件（越狱、注入、PII、有害内容），一键批量生成攻击用例并出报告 |
| **Garak**（NVIDIA） | LLM 漏洞扫描器，探针（probe）式扫描，类似"nmap for LLM" |
| **PyRIT**（Microsoft） | Python 风险识别工具包，多轮自动化对抗攻击编排 |
| **自研对抗生成器** | 用强模型扮演攻击者，基于自家知识库定制生成——针对性最强 |

### 4.3 红队结果的处置

红队用例一旦发现漏洞，**修复后应固化进黄金数据集的"黑名单分区"**，成为永久的回归测试项——这是 EDD 的闭环：攻击 → 发现 → 修复 → 回归护栏。

---

## 五、持续集成（CI/CD）：防止能力衰退

**痛点**：修复 Bug A 导致场景 B 崩盘（回归）。将 Evals 固化进 CI/CD 流水线是终极方案。

### 5.1 落地四步

1. **构建黄金数据集（Golden Dataset）**：筛选 100~500 个覆盖核心业务场景与边界条件的标准样本（标准 Query + 预期 Context/Answer）。
2. **触发流水线**：修改 System Prompt / 更换 Embedding 模型 / 调整微调参数 / 更改 Chunk 切分策略时，自动触发 GitHub Actions / GitLab CI。
3. **自动化打分与断言（Assertion）**：并发调用评估脚手架测试黄金数据集，设定硬性阈值（如 Faithfulness > 0.85，Answer Relevance 变动率 ≥ -2%）。
4. **卡点与准入**：得分低于阈值 → CI 报错并拒绝合入（Block PR），告别凭感觉上线。

### 5.2 黄金数据集构建方法论

| 样本来源 | 占比建议 | 说明 |
|---|---|---|
| 真实用户 Query 采样 | 40%~60% | 最有业务代表性；从线上日志聚类（按意图分组）后抽样 |
| LLM 合成生成 | 20%~40% | 基于知识库片段反向生成 QA 对，快速铺量覆盖长尾 |
| 人工精心构造的边界用例 | 10%~20% | 歧义、拒答、多跳推理、超长输入——机器生成不了的 |
| 红队发现的问题用例 | 持续追加 | 每次攻击测试的新发现，进入"黑名单分区" |

**工程要点**：
- 数据集要做**版本管理**（Git 管理 JSON/CSV 或用 LangSmith 数据集版本），评估结果必须能对应到数据集版本；
- 每条样本应标注**分类标签**（意图类别 / 难度 / 是否涉及拒答），回归报告按类别分组看，才能精确定位是哪类场景崩了；
- 定期审视：线上新出现的 bad case 应沉淀进数据集，让数据集随业务演化。

### 5.3 GitHub Actions 参考流水线

```yaml
name: rag-evals
on:
  pull_request:
    paths:
      - "prompts/**"          # 提示词变更
      - "configs/retrieval*"  # 检索/Chunk 配置变更
jobs:
  evaluate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install ragas deepeval
      - name: Run evals on golden dataset
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}   # 裁判模型
        run: python scripts/run_evals.py --dataset data/golden_v3.jsonl --workers 8
      - name: Assert thresholds (hard gate)
        run: python scripts/assert_metrics.py \
          --faithfulness 0.85 \
          --answer_relevancy 0.80 \
          --max_regression_vs_main 0.02   # 相对 main 分支降幅不得超 2%
      - uses: actions/upload-artifact@v4
        if: always()
        with: { name: eval-report, path: reports/ }   # 评估报告作为 PR 附件
```

### 5.4 阈值策略

| 策略 | 规则 | 适用 |
|---|---|---|
| 绝对阈值 | 指标必须 ≥ 固定值（如 Faithfulness > 0.85） | 安全底线，任何变更不得突破 |
| 相对回归 | 指标相对 main 分支降幅 ≤ 2% | 允许有损权衡，但要求改动者"看得见"损失并写明理由 |
| 分类卡点 | 核心类别绝对阈值 + 边缘类别相对回归 | 兼顾底线与迭代灵活度 |

> 裁判模型注意：LLM-as-a-Judge 打分有 ±0.02~0.05 的天然波动，阈值不宜压得太紧；关键卡点指标建议对同一样本多次采样取均值，或固定 `temperature=0` 并缓存裁判结果。

---

## 六、LLM-as-a-Judge 的局限与校准

裁判模型本身不可靠时，整个评估体系就是空中楼阁。常见偏差与对策：

| 偏差 | 表现 | 对策 |
|---|---|---|
| **位置偏差** | A/B 对比时倾向偏好先出现的答案 | 双序各评一次取平均 |
| **自我偏好** | 裁判偏好与自身输出风格相似的结果 | 裁判与被测模型用不同厂商的模型 |
| **冗长偏好** | 偏好更长、更"满"的答案 | Prompt 中显式要求"简洁与准确优先于详尽" |
| **打分漂移** | 同样的答案不同批次打分不一致 | 固定裁判版本 + temperature=0 + 结果缓存 + 定期人工抽检校准 |
| **推理能力上限** | 复杂多跳推理裁判判不动 | 关键场景保留 5%~10% 人工评估（Human Eval）兜底 |

**黄金法则**：自动评估负责"高频初筛 + 回归护栏"，人工评估负责"低频终审 + 校准裁判"。

---

## 七、生产环境：从离线评估到在线观测

EDD 不止于上线前——上线后评估转入**在线观测（Online Monitoring）**：

| 能力 | 工具/手段 | 作用 |
|---|---|---|
| 全链路 Tracing | Phoenix / LangSmith / Langfuse | 记录每次线上调用的检索、Prompt、回答，bad case 可回放定位 |
| 在线抽样评估 | 每日抽样 1%~5% 流量跑离线指标 | 持续跟踪 Faithfulness 等指标的生产水位，发现漂移 |
| 用户反馈闭环 | 点赞/点踩、客服工单回流 | 真实 bad case 进入黄金数据集，驱动下一轮迭代 |
| 告警 | 指标跌破基线（如 Faithfulness 周环比 -5%）触发告警 | 及时发现知识库腐化、模型 API 行为变化 |
| 灰度 + A/B | 新版本先放 5% 流量对比核心指标 | 上线前最后一道评估关卡 |

---

## 八、技术与工具速查

| 环节 | 技术 / 工具 | 作用 |
|---|---|---|
| 评估框架 | Ragas | RAG 三元组基准测试 |
| | TruLens | RAG Triad 概念 + 评估链路可视化 + 生产监控集成 |
| | Arize Phoenix | 观测性 + Tracing + 大规模评估 + CI/CD 绑定 |
| | DeepEval | 类 PyTest 的评估单测框架，CI 集成自然 |
| | promptfoo | 多模型/Prompt 横评 + 内置红队测试 |
| | LangSmith | LangChain 生态一体化 Trace + 数据集 + 评估 SaaS |
| | OpenAI Evals | 模型层能力基准评测 |
| 打分机制 | LLM-as-a-Judge（GPT-4 等） | 用强模型为输出自动打分（注意偏差校准） |
| 核心指标 | Faithfulness | 抗幻觉：回答是否忠于上下文 |
| | Answer Relevance | 反推问题对比相似度，防答非所问 |
| | Context Precision / Recall | 检索质量：排序精准度 + 漏检率 |
| | Answer Correctness | 语义比对标准答案，最贴近业务质量 |
| 对抗测试 | promptfoo red team / Garak / PyRIT | 自动生成越狱、注入、压力用例并扫描漏洞 |
| 集成 | GitHub Actions / GitLab CI | 评估自动化 + 阈值断言 + Block PR 卡点 |
| 数据资产 | Golden Dataset（100~500 样本） | 回归测试的标准基线，版本化管理 |
| 在线观测 | Phoenix / Langfuse + 抽样评估 + 反馈闭环 | 上线后持续监控指标水位与 bad case 回流 |

---

## 九、落地路线图（Checklist）

**第一阶段：可度量（1~2 周）**
- [ ] 选定评估框架（建议 Ragas 起步），接通裁判模型
- [ ] 从真实日志 + 合成生成构建第一版黄金数据集（先 50~100 条）
- [ ] 跑通三元组基线，得到当前系统的指标水位

**第二阶段：可防护（2~4 周）**
- [ ] 用 promptfoo red team / 自研生成器做一轮红队扫描
- [ ] 漏洞用例进入数据集黑名单分区
- [ ] 将评估脚本接入 CI，设置绝对阈值 + 相对回归双卡点

**第三阶段：可运营（持续）**
- [ ] 接入 Tracing（Phoenix/LangSmith），bad case 可回放
- [ ] 建立线上抽样评估与用户反馈回流机制
- [ ] 定期人工抽检校准裁判模型；数据集随业务持续演进

---

*整理时间：2026-11-04（扩展版）*
