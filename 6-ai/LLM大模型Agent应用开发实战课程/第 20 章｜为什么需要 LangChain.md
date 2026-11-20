---

# 一、本章定位
前面我们已经完成了项目一：

```plain
第 19 章｜项目一：AI Chat 聊天系统
```

到目前为止，我们已经用原生代码实现了：

```plain
1. FastAPI 后端接口
2. PostgreSQL 会话消息持久化
3. Redis 缓存和限流
4. 统一 LLM Provider
5. Prompt 工程化
6. Streaming 流式输出
7. Structured Output 结构化输出
8. Tool Calling 工具调用
9. 项目一 AI Chat 系统整合
```

这条路线非常重要。

因为我们不是一上来就用框架。

而是先用原生方式把底层能力手写了一遍。

这样学员才知道：

```plain
LangChain 到底帮我们封装了什么
LangChain 不是魔法
LangChain 不是大模型
LangChain 也不是 Agent 本身
```

从第 20 章开始，我们正式进入 LangChain 阶段。

这一章不急着写复杂 RAG，也不急着写 Agent。

先解决一个核心问题：

# 为什么需要 LangChain？
---

# 二、本章学习目标
学完这一章以后，学员需要掌握：

```plain
1. LangChain 到底是什么
2. LangChain 不是大模型，也不是 Agent 本身
3. 原生 LLM 应用开发会遇到哪些重复问题
4. LangChain 解决了哪些工程化问题
5. LangChain 和我们前面 LLM Provider 的关系
6. LangChain 里的 ChatModel 对应我们之前的什么
7. LangChain 里的 PromptTemplate 对应我们之前的什么
8. LangChain 里的 OutputParser 对应我们之前的什么
9. LangChain 里的 Tool 对应我们之前的什么
10. LangChain 里的 Chain / Runnable 是什么
11. LCEL 是什么
12. LangChain 和 LangGraph 的关系
13. 什么场景适合用 LangChain
14. 什么场景不一定要用 LangChain
15. 为什么学 LangChain 前先学原生 API 很重要
16. 如何在现有 FastAPI 项目里逐步引入 LangChain
```

---

# 三、本章最终项目结构
这一章不大规模重构项目，只新增 LangChain 学习示例。

本章结束后新增：

```plain
ai-agent-course/
├── app/
│   ├── langchain_demo/
│   │   ├── __init__.py
│   │   ├── 01_basic_chat_model.py
│   │   ├── 02_prompt_template.py
│   │   ├── 03_simple_chain.py
│   │   ├── 04_output_parser.py
│   │   ├── 05_tool_demo.py
│   │   └── 06_compare_with_native.py
│   │
│   └── ...
│
├── scripts/
│   ├── test_langchain_basic.py
│   ├── test_langchain_prompt_chain.py
│   └── test_langchain_vs_native.py
│
└── README.md
```

这一章重点是：

```plain
先理解 LangChain 为什么出现
再用几个小脚本建立手感
不急着改造第 19 章项目
```

后面几章会逐步进入：

```plain
第 21 章｜LangChain 核心架构
第 22 章｜LangChain Model 与 Message
第 23 章｜LangChain Prompt
第 24 章｜LangChain Structured Output
第 25 章｜LangChain Tool
第 26 章｜LangChain Agent
第 27 章｜LangChain RAG
第 28 章｜LangChain Agent + RAG
```

---

# 四、01｜本章开场
## 【重点内容】
大家好，欢迎来到第 20 章。

从这一章开始，我们进入 LangChain 阶段。

但是我先强调一句：

LangChain 不是大模型。

LangChain 本身不会生成答案。

真正生成答案的，还是 OpenAI、DeepSeek、Qwen、Claude、本地 Ollama 这些模型。

LangChain 也不是 Agent 本身。

它更像是一个 LLM 应用开发框架。

它帮我们把前面手写的很多重复能力抽象出来。

比如我们前面写过：

```plain
LLMProvider
PromptService
StructuredOutputService
ToolRegistry
ToolExecutor
Streaming
RAG 预留
Agent 规划
```

这些能力在 LangChain 里都有对应抽象。

比如：

```plain
ChatModel
PromptTemplate
OutputParser
Tool
Runnable
Agent
Retriever
```

所以这一章的目标不是背 LangChain API。

而是让大家理解：

为什么我们已经会原生开发了，还需要 LangChain？

---

# 五、02｜先回顾：原生开发我们已经写了什么
前面我们自己写了一套 AI 应用底层能力。

## 统一模型调用
```plain
BaseLLMProvider
DeepSeekProvider
QwenProvider
OpenAIProvider
LLMProviderFactory
```

## Prompt 工程化
```plain
PromptTemplate
PromptRegistry
PromptService
render_prompt
```

## 结构化输出
```plain
IntentClassificationOutput
RAGStructuredAnswerOutput
AgentPlanOutput
parse_structured_output
response_format
repair retry
```

## 工具调用
```plain
ToolDefinition
ToolRegistry
ToolExecutor
query_order
query_logistics
ToolCallingService
```

## 流式输出
```plain
StreamingResponse
format_sse
stream_chat_with_ai
LLMProvider.stream_chat
```

---

## 【重点内容】
大家看，前面我们其实已经手写了很多框架能力。

这些代码非常有价值。

因为它让我们理解了底层原理。

但是随着项目继续变复杂，会有一个问题：

很多能力每个项目都要重复写一遍。

比如你做 AI Chat 要写 Prompt。

做 RAG 也要写 Prompt。

做 Agent 还是要写 Prompt。

你做结构化输出要写 parser。

做工具调用要写 tool schema。

做 RAG 要写 retriever。

做 Agent 要写 tool execution loop。

这些东西如果每个项目都手写，开发效率会越来越低。

所以就出现了 LangChain 这样的框架。

---

# 六、03｜LangChain 到底是什么
## 【实操】
```plain
LangChain
=
LLM 应用开发框架

它帮你组织：
Model
Prompt
Output Parser
Tool
Retriever
Chain
Agent
Memory
Callback
```

LangChain 官方概览把 LangChain 描述为一个用于构建 Agent 和 LLM 应用的开源框架，并提供模型、工具、Agent 架构和集成能力。

---

## 【重点内容】
LangChain 可以理解成：

**一套帮助你开发 LLM 应用的工程化框架。**

它不是模型。

它不负责训练模型。

它也不是唯一的 Agent 框架。

它的价值在于把常见 LLM 应用开发模式抽象出来。

比如：

```plain
调用模型
组织 Prompt
解析输出
绑定工具
执行 Chain
构建 Agent
接入 Retriever
跟踪调用链路
```

这些东西你都可以手写。

我们前面已经证明了。

但是如果项目复杂度上来，框架会提升效率。

---

# 七、04｜一句话解释 LangChain
## 【重点内容】
如果用一句话解释 LangChain，我会这么说：

LangChain 是一个把模型、Prompt、工具、检索器和业务流程串起来的 LLM 应用开发框架。

再口语一点：

```plain
原生开发：
你自己拼 HTTP、Prompt、JSON、Tool、Parser。

LangChain：
它提供统一抽象，让你更快把这些东西组合起来。
```

但是要注意：

```plain
LangChain 帮你提效
不代表你不用懂底层
```

你如果不懂：

```plain
messages
role
tool_calls
response_format
stream
usage
RAG
Agent loop
```

直接用 LangChain，很容易只会复制代码，不会排错。

这就是为什么我们先讲了 19 章原生开发。

---

# 八、05｜为什么不一开始就学 LangChain
## 【重点内容】
很多课程一上来就教：

```python
from langchain_openai import ChatOpenAI
```

然后直接：

```python
llm.invoke("你好")
```

看起来很快。

但是学员会有几个问题：

```plain
不知道底层发了什么请求
不知道 messages 是什么
不知道 role 是什么
不知道 token usage 怎么来
不知道 tool_calls 怎么解析
不知道流式输出怎么接
不知道为什么 Agent 会乱调用工具
不知道 RAG 为什么会答错
```

所以我们这门课反过来：

```plain
先原生
再框架
```

先用原生代码手写一遍。

再学习 LangChain。

这样你会清楚知道：

```plain
LangChain 封装的是哪一层
它帮你省了什么
它没有帮你解决什么
出了问题该从哪里排查
```

这才是比较扎实的学习路线。

---

# 九、06｜原生开发的问题一：模型适配重复
## 原生写法
```python
class DeepSeekProvider:
    async def chat(self, request):
        ...

class QwenProvider:
    async def chat(self, request):
        ...

class OpenAIProvider:
    async def chat(self, request):
        ...
```

---

## 问题
```plain
不同模型厂商都要自己适配
base_url 要自己管
api_key 要自己管
响应结构要自己解析
stream chunk 要自己解析
tool_calls 要自己解析
usage 要自己解析
```

---

## LangChain 对应能力
```plain
ChatModel
```

比如：

```python
from langchain_openai import ChatOpenAI

model = ChatOpenAI(
    model="deepseek-chat",
    api_key="xxx",
    base_url="https://api.deepseek.com",
)
```

LangChain 通过模型集成包提供不同模型接入能力；它的 Python API Reference 也把 `langchain-core` 描述为核心接口抽象，把集成能力拆到多个集成包中。

---

## 【重点内容】
我们前面自己封装了 LLM Provider。

这很好。

但是如果接更多模型，比如：

```plain
OpenAI
DeepSeek
Qwen
Kimi
Claude
Gemini
Ollama
智谱
火山
```

就会发现适配工作很多。

LangChain 的 Model 抽象可以帮我们少写一部分适配代码。

它把不同模型封装成相似的调用方式。

比如：

```python
model.invoke(messages)
model.stream(messages)
```

这样业务侧更统一。

---

# 十、07｜原生开发的问题二：Prompt 组织重复
## 原生写法
```python
messages = [
    LLMMessage(
        role=LLMRole.SYSTEM,
        content="你是一个专业客服助手..."
    ),
    LLMMessage(
        role=LLMRole.USER,
        content=f"用户问题：{question}"
    )
]
```

我们还写了：

```plain
PromptTemplate
PromptRegistry
PromptService
render_prompt
```

---

## LangChain 对应能力
```plain
ChatPromptTemplate
PromptTemplate
MessagesPlaceholder
```

示例：

```python
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个专业客服助手。"),
    ("human", "用户问题：{question}"),
])

messages = prompt.invoke({
    "question": "我的订单到哪了？"
})
```

---

## 【重点内容】
我们前面自己写了 Prompt 工程化。

LangChain 里也有 PromptTemplate。

它可以帮你做变量替换、消息组织、组合调用。

尤其是后面 Chain 里，它可以直接和模型组合：

```python
chain = prompt | model
```

这个写法就是 LangChain Expression Language，也就是 LCEL 的常见组合方式。

---

# 十一、08｜原生开发的问题三：输出解析重复
## 原生写法
我们前面写了：

```plain
parse_structured_output
extract_json_text
IntentClassificationOutput
RAGStructuredAnswerOutput
AgentPlanOutput
repair retry
```

---

## LangChain 对应能力
```plain
OutputParser
Structured Output
PydanticOutputParser
JsonOutputParser
```

示例：

```python
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser


class IntentResult(BaseModel):
    intent: str = Field(..., description="用户意图")
    confidence: float = Field(..., description="置信度")


parser = PydanticOutputParser(pydantic_object=IntentResult)
```

LangChain 的模型文档也把结构化输出列为模型能力相关内容，官方上下文工程文档也说明 structured output 可以把非结构文本转换成经过校验的结构化数据。

---

## 【重点内容】
结构化输出如果纯手写，需要考虑很多事。

比如：

```plain
模型输出 JSON
模型输出 Markdown 代码块
字段缺失
字段类型错误
枚举值错误
解析失败重试
```

LangChain 里有 OutputParser，可以帮我们统一处理一部分解析逻辑。

但是我还是要强调：

```plain
后端校验不能省
业务兜底不能省
```

框架不是安全保证。

---

# 十二、09｜原生开发的问题四：工具调用重复
## 原生写法
我们前面写了：

```plain
ToolDefinition
ToolRegistry
ToolExecutor
tool_schema
tool_calls parser
tool result message
```

---

## LangChain 对应能力
```plain
Tool
@tool
StructuredTool
create_agent
```

示例：

```python
from langchain_core.tools import tool


@tool
def query_order(order_id: str) -> str:
    """根据订单号查询订单状态和物流信息。"""
    return f"订单 {order_id} 已发货。"
```

LangChain 官方工具文档说明，工具可以用普通 Python 函数或协程定义，也可以通过 `@tool` 装饰器定制工具名称、描述、参数 schema 等信息。

---

## 【重点内容】
我们前面自己写 ToolRegistry 和 ToolExecutor，是为了理解工具调用底层。

LangChain 里，工具可以直接用函数定义。

它会把函数名、docstring、参数信息转换成工具描述。

这能减少很多样板代码。

但真实项目里，工具权限、脱敏、确认机制，还是要自己设计。

比如：

```plain
退款工具能不能自动执行？
删除数据工具要不要二次确认？
用户有没有权限查这个订单？
```

这些不是 LangChain 自动帮你判断的。

---

# 十三、10｜原生开发的问题五：流程编排复杂
## 原生写法
如果你要做一个完整链路：

```plain
Prompt 渲染
 ↓
调用模型
 ↓
解析输出
 ↓
判断是否调用工具
 ↓
执行工具
 ↓
再次调用模型
 ↓
保存结果
```

原生代码会越来越长。

---

## LangChain 对应能力
```plain
Runnable
Chain
LCEL
Agent
```

LCEL 可以用管道式写法组合：

```python
chain = prompt | model | parser
```

LangChain Reference 中的 Runnable 示例展示了可以把多个 Runnable 通过 `|` 组合成序列，并支持 `invoke`、`ainvoke`、`batch`、`astream` 等调用方式。

---

## 【重点内容】
LangChain 很重要的一个设计是 Runnable。

你可以把：

```plain
Prompt
Model
Parser
Tool
Retriever
```

都看成可以运行的组件。

然后用：

```python
|
```

组合起来。

比如：

```python
chain = prompt | model | parser
```

这就比我们手写：

```python
messages = render_prompt(...)
response = await provider.chat(...)
result = parse_output(...)
```

更简洁。

当然，简洁不代表简单。

底层逻辑还是那些。

---

# 十四、11｜LangChain 和我们前面代码的对应关系
## 【实操】
| 我们前面手写的能力 | LangChain 对应能力 |
| --- | --- |
| `BaseLLMProvider` | `ChatModel` |
| `LLMMessage` | `SystemMessage`<br/> / `HumanMessage`<br/> / `AIMessage`<br/> / `ToolMessage` |
| `PromptTemplate` | `ChatPromptTemplate` |
| `PromptService` | Prompt 组合和 Registry，可自建 |
| `parse_structured_output` | `OutputParser`<br/> / structured output |
| `ToolDefinition` | `Tool`<br/> / `StructuredTool` |
| `ToolRegistry` | tools list / agent tools |
| `ToolExecutor` | Agent tool execution loop |
| `stream_chat` | `stream`<br/> / `astream` |
| `chat_with_ai` | Chain |
| `ToolCallingService` | Agent |
| `RAGService` | Retriever + Chain |
| `trace_id / logging` | Callback / LangSmith / 自建日志 |


---

## 【重点内容】
这张表非常重要。

学员不要把 LangChain 当成新世界。

它其实就是把我们前面手写过的能力换了一套抽象。

比如我们自己的：

```python
BaseLLMProvider.chat()
```

对应 LangChain 里的：

```python
model.invoke()
```

我们自己的：

```python
PromptService.render_by_scenario()
```

对应 LangChain 里的：

```python
ChatPromptTemplate.invoke()
```

我们自己的：

```python
ToolDefinition
```

对应 LangChain 的：

```python
@tool
```

理解了这张表，后面学习 LangChain 就不会乱。

---

# 十五、12｜LangChain 不是万能的
## 【重点内容】
虽然我们开始学 LangChain，但要先讲清楚：

LangChain 不是万能的。

它解决的是常见 LLM 应用开发抽象问题。

但它不能替你解决所有业务问题。

比如下面这些，仍然要你自己设计：

```plain
业务权限
用户体系
数据库表设计
成本控制
安全审计
工具调用权限
Prompt 策略
模型选择策略
异常兜底
高风险操作确认
前端体验
生产部署
```

所以 LangChain 是工具，不是银弹。

真实项目里，经常是：

```plain
业务系统自己写
LangChain 负责 LLM 编排
LangGraph 负责复杂 Agent 状态流转
```

不要把所有代码都塞进 LangChain。

---

# 十六、13｜什么时候适合用 LangChain
## 【适合场景】
```plain
1. 需要快速接入多个模型
2. 需要组合 Prompt + Model + Parser
3. 需要做 RAG
4. 需要接 Retriever
5. 需要使用工具调用
6. 需要构建 Agent
7. 需要复用社区生态
8. 需要和 LangGraph / LangSmith 配合
9. 需要快速验证 AI 应用原型
```

---

## 【重点内容】
LangChain 很适合用于 LLM 应用层。

比如：

```plain
企业知识库
客服 Agent
数据分析助手
代码助手
文档总结
智能问答
工具调用 Agent
```

这些场景都有很多重复模式。

LangChain 可以让开发速度更快。

特别是 RAG 和 Agent 场景，框架价值更明显。

---

# 十七、14｜什么时候不一定要用 LangChain
## 【不一定需要】
```plain
1. 只是简单调用一次模型
2. 只有一个 Prompt
3. 不需要 RAG
4. 不需要 Agent
5. 不需要工具调用
6. 对依赖体积非常敏感
7. 团队更希望完全掌控底层实现
8. 已经有成熟自研 Provider 架构
```

---

## 【重点内容】
不是所有项目都必须用 LangChain。

如果你的需求只是：

```plain
用户输入一句话
模型返回一句话
```

那原生 API 或我们前面写的 Provider 就够了。

用 LangChain 反而可能增加理解成本。

所以是否使用 LangChain，要看项目复杂度。

简单项目：

```plain
原生 Provider 足够
```

复杂项目：

```plain
LangChain / LangGraph 更有价值
```

---

# 十八、15｜LangChain 和 LangGraph 的关系
## 【实操】
```plain
LangChain
偏 LLM 应用组件和 Agent 快速开发

LangGraph
偏复杂 Agent 状态图、可控流程、多步骤执行
```

---

## 【重点内容】
很多同学会问：

```plain
LangChain 和 LangGraph 到底什么关系？
```

简单理解：

```plain
LangChain 更像组件库和应用框架
LangGraph 更像 Agent 状态机 / 工作流图
```

LangChain 适合快速组合：

```plain
Model
Prompt
Tool
Retriever
Parser
Agent
```

LangGraph 更适合复杂流程：

```plain
多步骤
可中断
可恢复
Human-in-the-loop
状态持久化
多 Agent 协作
```

LangChain 官方 Agent 文档也说明 LangChain Agent 构建在 LangGraph 之上，以获得持久化、流式、人类介入等能力。

所以我们课程顺序是：

```plain
先 LangChain
再 LangGraph
```

先掌握组件，再掌握复杂编排。

---

# 十九、16｜安装 LangChain
LangChain 当前安装文档要求 Python 3.10+，并且很多模型集成需要额外安装对应 provider 包，例如 `langchain-openai`。

执行：

```bash
uv add langchain langchain-core langchain-openai
```

或者：

```bash
pip install -U langchain langchain-core langchain-openai
```

如果后面用社区集成：

```bash
uv add langchain-community
```

---

## 【重点内容】
这里我们先安装三个包：

```plain
langchain
langchain-core
langchain-openai
```

为什么有这么多包？

因为现在 LangChain 生态是拆分的。

`langchain-core` 放核心抽象。

`langchain-openai` 放 OpenAI 兼容模型集成。

`langchain` 放主要入口和 Agent 等能力。

后面如果要接更多生态工具，再安装 `langchain-community`。

---

# 二十、17｜创建 langchain_demo 目录
执行：

```bash
mkdir -p app/langchain_demo

touch app/langchain_demo/__init__.py
touch app/langchain_demo/01_basic_chat_model.py
touch app/langchain_demo/02_prompt_template.py
touch app/langchain_demo/03_simple_chain.py
touch app/langchain_demo/04_output_parser.py
touch app/langchain_demo/05_tool_demo.py
touch app/langchain_demo/06_compare_with_native.py
```

Windows PowerShell：

```powershell
mkdir app\langchain_demo

New-Item app\langchain_demo\__init__.py
New-Item app\langchain_demo\01_basic_chat_model.py
New-Item app\langchain_demo\02_prompt_template.py
New-Item app\langchain_demo\03_simple_chain.py
New-Item app\langchain_demo\04_output_parser.py
New-Item app\langchain_demo\05_tool_demo.py
New-Item app\langchain_demo\06_compare_with_native.py
```

---

## 【重点内容】
这一章我们不改业务代码。

先创建一个：

```plain
app/langchain_demo
```

目录。

所有 LangChain 入门示例都放这里。

这样不会影响第 19 章已经跑通的项目一。

等后面第 21、22、23 章再慢慢把 LangChain 接入业务层。

---

# 二十一、18｜示例一：最小 ChatModel 调用
打开：

```plain
app/langchain_demo/01_basic_chat_model.py
```

写入：

```python
from langchain_openai import ChatOpenAI

from app.core.config import settings


def create_deepseek_chat_model():
    if not settings.deepseek_api_key:
        raise RuntimeError("请先在 .env 中配置 DEEPSEEK_API_KEY")

    return ChatOpenAI(
        model="deepseek-chat",
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=0.7,
    )


def run_basic_chat():
    model = create_deepseek_chat_model()

    response = model.invoke("请用一句话解释什么是 LangChain。")

    print("response type:", type(response))
    print("content:")
    print(response.content)


if __name__ == "__main__":
    run_basic_chat()
```

运行：

```bash
python app/langchain_demo/01_basic_chat_model.py
```

---

## 【重点内容】
这是最小 LangChain 模型调用。

大家看，LangChain 调模型不是直接写 httpx。

而是：

```python
model.invoke(...)
```

返回结果通常是一个 Message 对象。

真正文本在：

```python
response.content
```

这和我们之前的：

```python
llm_response.content
```

很像。

这说明我们前面设计的 Provider 思路是对的。

---

# 二十二、19｜示例二：使用 Message 调用
继续修改：

```plain
app/langchain_demo/01_basic_chat_model.py
```

增加：

```python
from langchain_core.messages import HumanMessage, SystemMessage
```

新增函数：

```python
def run_chat_with_messages():
    model = create_deepseek_chat_model()

    messages = [
        SystemMessage(content="你是一个专业 AI Agent 课程助教。"),
        HumanMessage(content="LangChain 和直接调用大模型 API 有什么区别？"),
    ]

    response = model.invoke(messages)

    print(response.content)
```

底部改成：

```python
if __name__ == "__main__":
    run_chat_with_messages()
```

---

## 【重点内容】
LangChain 也支持 messages。

比如：

```plain
SystemMessage
HumanMessage
AIMessage
ToolMessage
```

这和我们第 13 章讲的 role 是一一对应的。

所以大家不要觉得 LangChain 是新东西。

它只是把：

```json
{
  "role": "system",
  "content": "..."
}
```

封装成了：

```python
SystemMessage(content="...")
```

底层仍然是 messages。

---

# 二十三、20｜示例三：PromptTemplate
打开：

```plain
app/langchain_demo/02_prompt_template.py
```

写入：

```python
from langchain_core.prompts import ChatPromptTemplate


def run_prompt_template():
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "你是一个专业的 {role_name}，回答要简洁、准确。",
        ),
        (
            "human",
            "请解释一下：{question}",
        ),
    ])

    result = prompt.invoke({
        "role_name": "AI Agent 课程助教",
        "question": "为什么需要 LangChain？",
    })

    print("prompt result type:", type(result))
    print("messages:")
    for message in result.messages:
        print(message.type, ":", message.content)


if __name__ == "__main__":
    run_prompt_template()
```

运行：

```bash
python app/langchain_demo/02_prompt_template.py
```

---

## 【重点内容】
这个例子就是 LangChain 的 PromptTemplate。

它和我们之前的 PromptService 很像。

我们之前写：

```python
prompt_service.render_by_scenario(...)
```

LangChain 写：

```python
prompt.invoke(...)
```

变量替换由 LangChain 处理。

渲染结果是 messages。

这个结果可以继续传给 model。

---

# 二十四、21｜示例四：Prompt + Model 组成 Chain
打开：

```plain
app/langchain_demo/03_simple_chain.py
```

写入：

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import settings


def create_model():
    return ChatOpenAI(
        model="deepseek-chat",
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=0.7,
    )


def run_simple_chain():
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "你是一个专业 AI Agent 课程助教。",
        ),
        (
            "human",
            "请用三句话解释：{topic}",
        ),
    ])

    model = create_model()

    chain = prompt | model

    response = chain.invoke({
        "topic": "LangChain 的价值",
    })

    print(response.content)


if __name__ == "__main__":
    run_simple_chain()
```

---

## 【重点内容】
这里出现了 LangChain 里非常经典的写法：

```python
chain = prompt | model
```

这个 `|` 不是随便写的。

它表示把前一个组件的输出传给后一个组件。

也就是：

```plain
PromptTemplate 输出 messages
 ↓
ChatModel 接收 messages
 ↓
返回 AIMessage
```

这就是最简单的 Chain。

后面我们会继续加 parser：

```python
chain = prompt | model | parser
```

这就是 LangChain 的组合能力。

---

# 二十五、22｜示例五：Prompt + Model + OutputParser
打开：

```plain
app/langchain_demo/04_output_parser.py
```

写入：

```python
from typing import Literal

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.core.config import settings


class IntentResult(BaseModel):
    intent: Literal[
        "query_order",
        "refund",
        "product_question",
        "other",
    ] = Field(..., description="用户意图")

    confidence: float = Field(
        ...,
        ge=0,
        le=1,
        description="置信度",
    )


def create_model():
    return ChatOpenAI(
        model="deepseek-chat",
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=0,
    )


def run_parser_chain():
    parser = PydanticOutputParser(pydantic_object=IntentResult)

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            (
                "你是一个电商客服意图识别器。\n"
                "你必须按照下面的格式要求输出。\n"
                "{format_instructions}"
            ),
        ),
        (
            "human",
            "用户问题：{question}",
        ),
    ])

    prompt = prompt.partial(
        format_instructions=parser.get_format_instructions()
    )

    model = create_model()

    chain = prompt | model | parser

    result = chain.invoke({
        "question": "我的订单怎么还没发货？",
    })

    print(type(result))
    print(result.model_dump())


if __name__ == "__main__":
    run_parser_chain()
```

---

## 【重点内容】
这个例子对应第 17 章结构化输出。

我们之前自己写：

```python
parse_structured_output(...)
```

现在 LangChain 写：

```python
PydanticOutputParser
```

然后：

```python
chain = prompt | model | parser
```

最终拿到的不是字符串，而是：

```python
IntentResult
```

也就是 Pydantic 对象。

这就是 Chain 的价值。

---

# 二十六、23｜示例六：Tool 定义
打开：

```plain
app/langchain_demo/05_tool_demo.py
```

写入：

```python
from langchain_core.tools import tool


@tool
def query_order(order_id: str) -> str:
    """根据订单号查询订单状态和物流信息。"""
    if order_id == "10001":
        return "订单 10001 已发货，物流公司顺丰，物流单号 SF10001。"

    return f"未查询到订单 {order_id}。"


def run_tool_demo():
    print("tool name:", query_order.name)
    print("tool description:", query_order.description)
    print("tool args:", query_order.args)

    result = query_order.invoke({
        "order_id": "10001",
    })

    print("tool result:", result)


if __name__ == "__main__":
    run_tool_demo()
```

运行：

```bash
python app/langchain_demo/05_tool_demo.py
```

---

## 【重点内容】
这个例子对应第 18 章 Tool Calling。

我们之前手写：

```python
ToolDefinition
ToolRegistry
ToolExecutor
```

LangChain 里可以用：

```python
@tool
```

快速把一个 Python 函数变成工具。

它会读取函数名、参数和 docstring。

然后模型或 Agent 就可以使用这个工具。

但是再次强调：

```plain
权限控制
敏感信息脱敏
高风险确认
业务规则
```

这些还要我们自己设计。

---

# 二十七、24｜示例七：原生写法 vs LangChain 写法
打开：

```plain
app/langchain_demo/06_compare_with_native.py
```

写入：

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.llm.providers.deepseek import DeepSeekProvider
from app.llm.schemas import LLMMessage, LLMRequest, LLMRole


async def native_version():
    provider = DeepSeekProvider()

    request = LLMRequest(
        model="deepseek-chat",
        messages=[
            LLMMessage(
                role=LLMRole.SYSTEM,
                content="你是一个专业 AI Agent 课程助教。",
            ),
            LLMMessage(
                role=LLMRole.USER,
                content="请用一句话解释 LangChain。",
            ),
        ],
        temperature=0.7,
    )

    response = await provider.chat(request)

    return response.content


def langchain_version():
    model = ChatOpenAI(
        model="deepseek-chat",
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=0.7,
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个专业 AI Agent 课程助教。"),
        ("human", "请用一句话解释 {topic}。"),
    ])

    chain = prompt | model

    response = chain.invoke({
        "topic": "LangChain",
    })

    return response.content
```

创建脚本：

```plain
scripts/test_langchain_vs_native.py
```

写入：

```python
import asyncio

from app.langchain_demo.06_compare_with_native import (
    langchain_version,
    native_version,
)


async def main():
    native_answer = await native_version()
    print("native answer:")
    print(native_answer)

    print("=" * 80)

    langchain_answer = langchain_version()
    print("langchain answer:")
    print(langchain_answer)


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 【重点内容】
这个对比很直观。

原生写法更底层，控制力强。

LangChain 写法更简洁，更适合组合。

两者不是谁取代谁。

真实项目里可以混用。

比如：

```plain
业务 API、权限、数据库、缓存
继续用我们自己的 FastAPI 架构

LLM 编排、Prompt 组合、RAG、Agent
逐步使用 LangChain / LangGraph
```

这就是比较合理的工程策略。

---

# 二十八、25｜LangChain 和第 19 章项目怎么结合
## 【架构图】
```plain
FastAPI Router
  ↓
ChatService
  ↓
LangChainChainService
  ↓
PromptTemplate | ChatModel | OutputParser
  ↓
LLM Provider / LangChain Model
  ↓
返回结果
  ↓
PostgreSQL / Redis / Response
```

---

## 【重点内容】
第 19 章项目不需要推倒重来。

我们可以逐步引入 LangChain。

比如第一步：

```plain
只用 LangChain PromptTemplate
```

第二步：

```plain
用 LangChain ChatModel 替代一部分 Provider
```

第三步：

```plain
用 OutputParser 替代结构化输出解析
```

第四步：

```plain
用 LangChain Tool 替代自定义 ToolDefinition
```

第五步：

```plain
用 LangChain Agent 做工具调用
```

这样项目平滑升级，不会一下子重构崩掉。

---

# 二十九、26｜建议不要立刻重构项目一
## 【重点内容】
这一章我们只是理解 LangChain。

不要立刻把第 19 章项目全部重构成 LangChain。

为什么？

因为刚开始学 LangChain，如果直接全量重构，很容易乱。

推荐做法是：

```plain
第 20 章：理解为什么需要 LangChain
第 21 章：理解核心架构
第 22 章：替换 Model 层
第 23 章：替换 Prompt 层
第 24 章：替换 Structured Output
第 25 章：替换 Tool
第 26 章：实现 LangChain Agent
第 27 章：实现 LangChain RAG
第 28 章：Agent + RAG 整合
```

这样节奏更稳。

---

# 三十、27｜LangChain 学习的正确姿势
## 【重点内容】
学习 LangChain 不要死记 API。

因为版本会变，API 也会调整。

正确学习方式是理解抽象：

```plain
Model：模型调用
Prompt：提示词模板
Parser：输出解析
Tool：工具能力
Retriever：检索能力
Runnable：可执行组件
Chain：组件组合
Agent：模型驱动工具选择和执行
Callback：过程观测
```

只要这些抽象理解了，API 变化也不怕。

你知道它要解决什么问题，就能看懂新版本文档。

---

# 三十一、28｜LangChain 常见误区一：以为 LangChain 是模型
错误理解：

```plain
用了 LangChain 就不用 OpenAI / DeepSeek / Qwen 了
```

正确理解：

```plain
LangChain 是框架
模型还是模型服务商提供
```

---

## 【重点内容】
LangChain 不提供模型能力。

它只是帮你调用模型、组织流程、组合工具。

你还是需要：

```plain
API Key
模型名称
模型服务商
或者本地模型
```

就像 FastAPI 不提供数据库。

FastAPI 只是帮你写 Web API。

数据库还是 PostgreSQL / MySQL。

---

# 三十二、29｜LangChain 常见误区二：以为用了 LangChain 就不用架构设计
错误理解：

```plain
用了 LangChain，业务代码随便写就行
```

正确理解：

```plain
LangChain 解决 LLM 编排问题
业务系统架构仍然要自己设计
```

---

## 【重点内容】
LangChain 不会自动帮你设计：

```plain
用户权限
数据库表
缓存策略
限流策略
成本统计
审计日志
后台管理
前端交互
```

这些仍然是企业系统工程问题。

所以我们课程前半段讲 FastAPI、数据库、Redis，是有必要的。

---

# 三十三、30｜LangChain 常见误区三：所有东西都用 Chain
错误做法：

```plain
所有业务逻辑都塞进一个超长 chain
```

问题：

```plain
难调试
难测试
难插入业务规则
难做权限控制
难做异常处理
```

推荐：

```plain
业务逻辑留在 Service
LLM 编排用 Chain
复杂状态流转交给 LangGraph
```

---

# 三十四、31｜LangChain 常见误区四：不看底层 messages
## 【重点内容】
即使用 LangChain，也要知道底层 messages 长什么样。

因为很多问题都和 messages 有关。

比如：

```plain
system prompt 没生效
history 没带上
tool message 格式错
上下文太长
模型不按格式输出
```

这些都要回到底层：

```plain
messages
role
content
tool_calls
tool_call_id
```

去排查。

---

# 三十五、32｜LangChain 常见误区五：忽略版本变化
## 【重点内容】
LangChain 生态迭代很快。

包名、导入路径、推荐写法都有可能变化。

所以学习时要养成两个习惯：

```plain
1. 看官方文档
2. 固定项目依赖版本
```

比如项目里可以在 `pyproject.toml` 固定版本范围：

```toml
dependencies = [
    "langchain>=0.3,<0.4",
    "langchain-core>=0.3,<0.4",
    "langchain-openai>=0.2,<0.3",
]
```

实际版本以安装时官方文档和兼容性为准。

---

# 三十六、33｜本章知识点和前面章节对应表
| 第 13～19 章原生能力 | 第 20 章 LangChain 视角 |
| --- | --- |
| 大模型 API | ChatModel |
| messages / role | Message Types |
| Prompt Engineering | PromptTemplate |
| Streaming | stream / astream |
| Structured Output | OutputParser / structured output |
| Tool Calling | Tool / Agent |
| LLM Provider | Model Integration |
| Redis / PostgreSQL | 业务基础设施，不由 LangChain 替代 |
| ChatService | Chain / Service 编排 |
| ToolCallingService | Agent 执行流程 |
| 项目一 AI Chat | 后续 LangChain 改造目标 |


---

# 三十七、34｜本章完整复习
这一章我们完成了：

```plain
1. 理解为什么第 20 章开始讲 LangChain
2. 回顾前 19 章原生开发能力
3. 理解 LangChain 是 LLM 应用开发框架
4. 理解 LangChain 不是大模型
5. 理解为什么不一开始就学 LangChain
6. 理解原生模型适配的重复问题
7. 理解 LangChain ChatModel
8. 理解原生 Prompt 组织的重复问题
9. 理解 LangChain PromptTemplate
10. 理解原生输出解析的重复问题
11. 理解 LangChain OutputParser
12. 理解原生工具调用的重复问题
13. 理解 LangChain Tool
14. 理解 Chain / Runnable / LCEL 的价值
15. 理解 LangChain 和 LangGraph 的关系
16. 理解什么时候适合用 LangChain
17. 理解什么时候不一定要用 LangChain
18. 安装 LangChain 相关依赖
19. 创建 langchain_demo 目录
20. 编写 ChatModel 示例
21. 编写 Message 调用示例
22. 编写 PromptTemplate 示例
23. 编写 Prompt + Model Chain 示例
24. 编写 Prompt + Model + Parser 示例
25. 编写 Tool 示例
26. 对比原生写法和 LangChain 写法
27. 明确第 19 章项目后续如何逐步接入 LangChain
28. 总结 LangChain 常见误区
```

---

# 三十八、35｜课后任务一：跑通 LangChain ChatModel
要求：

```plain
1. 安装 langchain / langchain-core / langchain-openai
2. 配置 DEEPSEEK_API_KEY
3. 运行 01_basic_chat_model.py
4. 输出 response.content
```

---

# 三十九、36｜课后任务二：把通用聊天 Prompt 改成 ChatPromptTemplate
要求：

```plain
1. 创建一个 ChatPromptTemplate
2. system 内容使用第 15 章 GENERAL_CHAT_PROMPT_V1
3. human 内容使用 {user_question}
4. invoke 后打印 messages
```

---

# 四十、37｜课后任务三：写一个 Prompt | Model | Parser Chain
要求：

```plain
1. 定义 IntentResult Pydantic 模型
2. 使用 PydanticOutputParser
3. 使用 ChatPromptTemplate
4. 组成 chain = prompt | model | parser
5. 输入“我的订单怎么还没发货？”
6. 输出 intent 和 confidence
```

---

# 四十一、38｜课后任务四：把 query_order 改成 LangChain Tool
要求：

```plain
1. 使用 @tool 定义 query_order
2. 参数 order_id: str
3. docstring 写清楚工具用途
4. 调用 query_order.invoke({"order_id": "10001"})
5. 打印工具结果
```

---

# 四十二、39｜课后任务五：画出原生代码和 LangChain 的对应图
要求画出：

```plain
第 19 章项目一
```

和：

```plain
LangChain 抽象
```

之间的映射关系。

必须包含：

```plain
LLMProvider -> ChatModel
PromptService -> ChatPromptTemplate
StructuredOutputService -> OutputParser
ToolRegistry -> Tool
ToolCallingService -> Agent
ChatService -> Chain
```

---

# 四十三、40｜课后任务六：思考是否应该全量重构项目一
要求回答：

```plain
1. 哪些部分适合交给 LangChain？
2. 哪些部分仍然应该保留在 FastAPI 业务层？
3. Redis 和 PostgreSQL 是否应该由 LangChain 接管？
4. Tool 权限和高风险确认是否应该交给模型？
5. 如果只改一部分，你会先改哪一层？
```

参考答案方向：

```plain
LangChain 适合接管 LLM 编排层；
FastAPI、数据库、缓存、权限、审计、成本控制仍然应该由业务系统负责。
```

---

# 四十四、41｜本章总结
## 【最终重点内容】
好了，到这里，第 20 章我们就讲完了。

这一章我们正式进入 LangChain 阶段。

但是这一章最重要的不是某一个 API。

而是理解：

```plain
为什么需要 LangChain
```

前面我们已经用原生代码写过：

```plain
LLM Provider
Prompt
Streaming
Structured Output
Tool Calling
AI Chat 项目
```

所以现在再看 LangChain，就会非常清楚。

LangChain 不是大模型。

LangChain 也不是万能框架。

它的核心价值是：

```plain
把 LLM 应用开发里的常见组件抽象出来
让模型、Prompt、Parser、Tool、Retriever、Agent 更容易组合
```

但是企业项目里的：

```plain
权限
数据库
缓存
限流
审计
成本
部署
```

仍然需要我们自己设计。

所以后面的学习方式是：

```plain
不要迷信 LangChain
也不要排斥 LangChain

先理解底层
再使用框架提效
```

---
