---

# 一、本章定位
前面我们已经完成了 AI Agent 后端的基础设施：

```plain
第 06 章｜FastAPI 快速入门
第 07 章｜Pydantic 请求参数与响应模型
第 08 章｜FastAPI Router 与项目工程化
第 09 章｜FastAPI Dependency Injection 依赖注入
第 10 章｜Middleware、异常处理与日志
第 11 章｜PostgreSQL + SQLAlchemy 数据库开发
补充小节｜Alembic 数据库迁移入门
第 12 章｜Redis 在 AI 应用中的使用
```

到目前为止，我们已经有了：

```plain
FastAPI 后端骨架
Pydantic 请求响应模型
Router / Service / Repository 分层
Depends 依赖注入
统一异常处理
统一日志 trace_id
PostgreSQL 持久化
Redis 缓存、限流、状态管理
```

但是我们的 AI 回答还是模拟的：

```python
answer = "这是一个模拟回答"
```

从这一章开始，我们进入第三阶段：

# 原生大模型 API 开发
也就是不急着上 LangChain，不急着上 LangGraph。

先把最底层的大模型 API 原理讲清楚。

因为后面不管你用：

```plain
OpenAI
DeepSeek
Qwen
Kimi
Claude
Ollama
LangChain
LangGraph
Agent Framework
```

底层都绕不开这些概念：

```plain
HTTP API
API Key
model
messages
role
prompt
token
temperature
max_tokens
stream
usage
error
retry
timeout
```

这一章的核心目标是：

**让学员真正理解一次大模型 API 调用到底发生了什么。**

---

# 二、本章学习目标
学完这一章以后，学员需要掌握：

```plain
1. 大模型 API 到底是什么
2. 一次 LLM API 请求的完整链路
3. API Key 的作用
4. Base URL / Endpoint 是什么
5. model 参数是什么意思
6. messages / input 是什么
7. system / user / assistant / tool 分别是什么
8. prompt 和 messages 的关系
9. temperature 是什么
10. max_tokens 是什么
11. top_p 是什么
12. stream 是什么
13. SSE 流式输出是什么
14. token 是什么
15. prompt_tokens / completion_tokens / total_tokens 怎么理解
16. usage 在成本统计里的作用
17. 非流式响应怎么解析
18. 流式响应怎么解析
19. OpenAI / DeepSeek / Qwen API 有什么共性
20. OpenAI Responses API 和 Chat Completions 怎么理解
21. OpenAI-compatible API 是什么
22. 大模型 API 常见错误有哪些
23. 如何设计统一 LLM 请求结构
24. 如何为下一章 LLM Provider 封装做准备
```

---

# 三、本章最终项目结构
这一章主要是讲 API 原理和脚本验证，不急着大规模改造业务接口。

本章结束后，项目会新增：

```plain
ai-agent-course/
├── app/
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   └── examples.py
│   │
│   └── ...
│
├── scripts/
│   ├── llm_openai_responses_demo.py
│   ├── llm_openai_compatible_chat_demo.py
│   ├── llm_stream_demo.py
│   └── token_usage_demo.py
│
├── .env
├── .env.example
└── README.md
```

注意：

```plain
第 13 章
= 讲原理 + 脚本跑通

第 14 章
= 正式封装统一 LLM Provider 架构
```

这一章先不要急着写复杂框架。

先把 API 讲明白。

---

# 四、01｜本章开场
## 【重点内容】
大家好，欢迎来到第 13 章。

从这一章开始，我们正式进入大模型 API 开发。

前面我们已经把后端基础设施搭好了。

但是到目前为止，我们的 AI 回答都是模拟的。

比如：

```python
if "AI Agent" in latest_user_message:
    answer = "AI Agent 是能够理解目标、规划步骤、调用工具并根据结果完成任务的智能体。"
else:
    answer = f"这是一个模拟回答：{latest_user_message}"
```

这只是为了让接口先跑起来。

但是从这一章开始，我们要真正理解：

```plain
大模型 API 是怎么调用的
请求体怎么组织
响应体怎么解析
流式输出怎么工作
token 用量怎么统计
错误怎么处理
```

这一章非常关键。

因为后面我们会继续讲：

```plain
统一 LLM Provider
Prompt Engineering
Streaming 流式输出
Structured Output
Function Calling
Tool Calling
LangChain
LangGraph
Agent
```

这些能力的底层，都是大模型 API。

所以大家一定要先把这一章吃透。

---

# 五、02｜大模型 API 到底是什么
## 【实操】
```plain
你的后端服务
    ↓ HTTP 请求
大模型服务商 API
    ↓ 模型推理
返回文本 / JSON / 流式 token
```

---

## 【重点内容】
大模型 API 本质上就是一个 HTTP 接口。

你把问题发给模型服务商。

模型服务商返回回答。

比如用户问：

```plain
什么是 AI Agent？
```

你的后端会把它包装成请求：

```json
{
  "model": "deepseek-chat",
  "messages": [
    {
      "role": "user",
      "content": "什么是 AI Agent？"
    }
  ]
}
```

然后发送给模型 API。

模型返回：

```json
{
  "answer": "AI Agent 是能够理解目标、规划任务并调用工具完成目标的智能体。"
}
```

所以大模型 API 不是玄学。

它就是：

```plain
HTTP 请求
+
JSON 请求体
+
JSON 响应体
```

只不过它背后的服务是大模型。

---

# 六、03｜一次大模型 API 调用完整链路
## 【实操】
```plain
用户输入问题
    ↓
前端发送到 FastAPI
    ↓
FastAPI 组装 LLM Request
    ↓
携带 API Key 请求模型服务商
    ↓
模型生成回答
    ↓
返回 response / stream chunks
    ↓
FastAPI 解析结果
    ↓
保存消息和 usage
    ↓
返回给前端
```

---

## 【重点内容】
真实项目里，一次 AI Chat 请求不是前端直接调模型。

一般是这样：

第一步，用户在前端输入问题。

第二步，前端请求我们的 FastAPI 后端。

第三步，后端做：

```plain
认证
限流
读取历史消息
读取用户配置
组装 messages
```

第四步，后端调用大模型 API。

第五步，模型返回结果。

第六步，后端解析响应。

第七步，保存：

```plain
用户消息
AI 回复
token 用量
trace_id
模型名称
```

第八步，返回给前端。

所以我们的后端在中间非常重要。

它不是简单转发请求。

它要做：

```plain
安全控制
上下文组装
成本统计
日志追踪
缓存
错误处理
数据持久化
```

---

# 七、04｜大模型 API 的通用组成
## 【实操】
一次 API 调用通常包括：

```plain
1. Base URL
2. Endpoint
3. API Key
4. Headers
5. Request Body
6. Response Body
7. Error Response
```

---

## 示例
```plain
POST https://api.deepseek.com/chat/completions
Authorization: Bearer sk-xxxx
Content-Type: application/json
```

请求体：

```json
{
  "model": "deepseek-chat",
  "messages": [
    {
      "role": "user",
      "content": "什么是 AI Agent？"
    }
  ],
  "temperature": 0.7,
  "stream": false
}
```

DeepSeek 官方对话补全接口就是 `/chat/completions`，支持 `messages`、`model`、`stream` 等参数，也会返回用量统计 `usage`。

---

## 【重点内容】
大家先记住一个大模型 API 的标准组成。

第一个是：

```plain
Base URL
```

比如：

```plain
https://api.deepseek.com
```

第二个是：

```plain
Endpoint
```

比如：

```plain
/chat/completions
```

第三个是：

```plain
API Key
```

用来证明你是谁。

第四个是：

```plain
Headers
```

通常会有：

```plain
Authorization
Content-Type
```

第五个是：

```plain
Request Body
```

也就是 JSON 请求体。

第六个是：

```plain
Response Body
```

也就是模型返回的 JSON。

理解这几个东西，后面你看任何模型 API 都不会慌。

---

# 八、05｜API Key 是什么
## 【重点内容】
API Key 可以理解成调用模型服务的钥匙。

没有 API Key，模型服务商不知道你是谁。

也无法计费、限额、鉴权。

通常请求头里会带：

```plain
Authorization: Bearer sk-xxxx
```

代码里千万不要把 API Key 写死：

```python
api_key = "sk-xxxx"
```

正确方式是放到 `.env`：

```plain
OPENAI_API_KEY=你的 OpenAI Key
DEEPSEEK_API_KEY=你的 DeepSeek Key
DASHSCOPE_API_KEY=你的 Qwen / DashScope Key
```

然后代码里读取环境变量。

---

## 【安全提醒】
API Key 不要：

```plain
写死在代码里
提交到 GitHub
发给前端
打印到日志里
放到截图里
发到微信群里
```

因为别人拿到你的 API Key，就可以消耗你的额度。

---

# 九、06｜OpenAI Responses API 和 Chat Completions
## 【重点内容】
现在大模型 API 有两类常见接口形态。

第一类是：

```plain
Responses API
```

这是 OpenAI 当前官方 Quickstart 里重点使用的接口风格，示例里通过创建 response 并读取 `response.output_text` 拿到输出。

第二类是：

```plain
Chat Completions API
```

很多模型厂商都支持 OpenAI-compatible Chat Completions 风格。

比如 DeepSeek 的 `/chat/completions`，Qwen / 阿里云 Model Studio 也提供 OpenAI-compatible 调用方式。

所以这门课会这样安排：

```plain
第 13 章
= 讲通用 API 原理

第 14 章
= 设计统一 LLM Provider，兼容不同接口风格
```

大家不要纠结某一个厂商的接口写法。

重点理解共性。

---

# 十、07｜Chat Completions 请求结构
## 【典型请求】
```json
{
  "model": "deepseek-chat",
  "messages": [
    {
      "role": "system",
      "content": "你是一个专业 AI 助手。"
    },
    {
      "role": "user",
      "content": "什么是 AI Agent？"
    }
  ],
  "temperature": 0.7,
  "max_tokens": 1000,
  "stream": false
}
```

---

## 【字段说明】
| 字段 | 作用 |
| --- | --- |
| `model` | 使用哪个模型 |
| `messages` | 多轮对话消息 |
| `role` | 消息角色 |
| `content` | 消息内容 |
| `temperature` | 控制输出随机性 |
| `max_tokens` | 控制最大输出长度 |
| `stream` | 是否流式输出 |


---

## 【重点内容】
这是最常见的大模型请求结构。

大家要重点掌握几个字段。

```json
model
```

表示你要调用哪个模型。

```json
messages
```

表示对话上下文。

```json
temperature
```

控制模型回答的随机性。

```json
max_tokens
```

控制模型最多输出多少 token。

```json
stream
```

控制是否流式返回。

这个结构后面会贯穿整门课。

---

# 十一、08｜messages 是什么
## 【实操】
```json
[
  {
    "role": "system",
    "content": "你是一个专业 AI 助手。"
  },
  {
    "role": "user",
    "content": "什么是 AI Agent？"
  },
  {
    "role": "assistant",
    "content": "AI Agent 是..."
  },
  {
    "role": "user",
    "content": "它和 RAG 有什么区别？"
  }
]
```

---

## 【重点内容】
messages 表示多轮对话上下文。

它不是单纯一个字符串。

它是一组有顺序的消息。

大模型会根据这些消息理解上下文。

比如：

```plain
system
告诉模型身份和规则

user
表示用户输入

assistant
表示模型之前的回答

tool
表示工具调用结果
```

这也是为什么我们第 07 章设计了：

```python
ChatMessage
MessageRole
ChatRequest
```

因为真实大模型 API 本身就是围绕 messages 设计的。

---

# 十二、09｜role 的作用
## 【实操】
| role | 含义 | 示例 |
| --- | --- | --- |
| `system` | 系统规则 / AI 身份 | 你是一个专业客服助手 |
| `user` | 用户输入 | 我的订单什么时候发货 |
| `assistant` | 模型回复 | 您的订单预计今天发出 |
| `tool` | 工具返回结果 | 订单状态：已发货 |


---

## 【重点内容】
role 非常重要。

不要把所有内容都塞到 user 里面。

比如你想让模型扮演企业客服，不建议这样：

```json
{
  "role": "user",
  "content": "你是一个客服助手。用户问题是：我的订单在哪？"
}
```

更推荐：

```json
{
  "role": "system",
  "content": "你是一个专业电商客服助手。"
},
{
  "role": "user",
  "content": "我的订单在哪？"
}
```

这样结构更清晰。

后面做 Agent 和 Tool Calling 时，role 会更重要。

尤其是：

```plain
tool
```

它表示工具执行后的结果。

比如查订单工具返回：

```json
{
  "order_status": "已发货",
  "tracking_no": "SF123456"
}
```

然后模型再基于 tool 结果组织自然语言回答。

---

# 十三、10｜system prompt 是什么
## 【示例】
```json
{
  "role": "system",
  "content": "你是一个专业的企业 AI 助手。回答要准确、简洁，不要编造事实。"
}
```

---

## 【重点内容】
system prompt 就是系统提示词。

它通常用来定义：

```plain
AI 的角色
回答规则
安全边界
输出格式
业务约束
```

比如电商客服 Agent：

```plain
你是一个跨境电商客服助手。
只能回答订单、物流、售后相关问题。
如果不知道，请引导用户转人工。
不要编造物流单号。
```

比如企业知识库助手：

```plain
你是企业知识库助手。
回答必须基于提供的文档片段。
如果资料中没有答案，请回答“知识库中暂未找到相关信息”。
```

所以 system prompt 是控制模型行为的重要入口。

---

# 十四、11｜prompt 和 messages 的关系
## 【重点内容】
很多同学会把 prompt 理解成一个字符串。

比如：

```plain
请介绍一下 AI Agent
```

这没错。

但是在 Chat API 里，prompt 通常被组织成 messages。

也就是说：

```plain
prompt
是你想让模型看到的内容

messages
是 prompt 的结构化表达方式
```

比如简单 prompt：

```plain
什么是 AI Agent？
```

可以变成：

```json
[
  {
    "role": "user",
    "content": "什么是 AI Agent？"
  }
]
```

复杂 prompt：

```plain
你是客服助手。
用户问题：我的订单在哪？
订单数据：已发货。
```

可以拆成：

```json
[
  {
    "role": "system",
    "content": "你是客服助手。"
  },
  {
    "role": "user",
    "content": "我的订单在哪？"
  },
  {
    "role": "tool",
    "content": "订单数据：已发货。"
  }
]
```

这就是从 prompt 到 messages 的升级。

---

# 十五、12｜temperature 是什么
## 【实操】
```plain
temperature 越低：
回答越稳定、越保守、越确定

temperature 越高：
回答越发散、越随机、越有创造性
```

---

## 【示例】
```json
{
  "temperature": 0.2
}
```

适合：

```plain
客服
知识库问答
代码生成
结构化输出
严肃业务回答
```

```json
{
  "temperature": 0.9
}
```

适合：

```plain
创意写作
营销文案
标题生成
头脑风暴
```

---

## 【重点内容】
temperature 控制模型输出的随机性。

如果你做企业知识库问答，建议 temperature 低一点。

比如：

```plain
0.1
0.2
0.3
```

因为你希望回答稳定，不要发散。

如果你做营销文案，可以高一点：

```plain
0.7
0.8
0.9
```

因为你希望有创意。

在企业 AI Agent 里，很多场景建议默认：

```plain
0.3 ~ 0.7
```

后面我们可以根据不同应用配置不同 temperature。

---

# 十六、13｜max_tokens 是什么
## 【重点内容】
max_tokens 用来限制模型最多输出多少 token。

比如：

```json
{
  "max_tokens": 1000
}
```

表示最多输出大约 1000 个 token。

注意它不是字符数，也不是中文字数。

token 是模型处理文本的基本单位。

不同语言、不同模型的 token 切分方式不完全一样。

但可以先粗略理解为：

```plain
英文：一个单词可能是一个或多个 token
中文：一个字或一个词可能被切成一个或多个 token
```

为什么要限制 max_tokens？

因为它影响：

```plain
输出长度
响应耗时
调用成本
前端展示
```

如果不限制，模型可能输出太长，成本也更高。

---

# 十七、14｜token 和 usage
## 【典型 usage】
```json
{
  "usage": {
    "prompt_tokens": 120,
    "completion_tokens": 80,
    "total_tokens": 200
  }
}
```

---

## 【字段说明】
| 字段 | 含义 |
| --- | --- |
| `prompt_tokens` | 输入消耗 token |
| `completion_tokens` | 输出消耗 token |
| `total_tokens` | 总 token 消耗 |


OpenAI streaming events 文档中也把 usage 描述为包含 input tokens、output tokens 以及 total tokens 的用量详情；DeepSeek Chat Completion 文档同样提供 `usage` 用量统计字段。

---

## 【重点内容】
usage 非常重要。

它关系到：

```plain
成本统计
用户额度
模型调用分析
限流
计费
性能优化
```

比如一次请求：

```plain
prompt_tokens = 120
completion_tokens = 80
total_tokens = 200
```

这表示用户输入和上下文消耗了 120 token。

模型输出消耗了 80 token。

总共消耗 200 token。

后面我们要把 usage 保存到数据库。

比如：

```plain
messages 表
llm_call_logs 表
token_usage 表
```

这就是为什么第 07 章我们提前设计了：

```python
TokenUsage
```

---

# 十八、15｜非流式响应结构
## 【Chat Completions 风格示例】
```json
{
  "id": "chatcmpl_xxx",
  "object": "chat.completion",
  "created": 1720000000,
  "model": "deepseek-chat",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "AI Agent 是能够理解目标、规划任务并调用工具完成目标的智能体。"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 30,
    "completion_tokens": 40,
    "total_tokens": 70
  }
}
```

---

## 【解析方式】
```python
answer = response["choices"][0]["message"]["content"]
usage = response["usage"]
```

---

## 【重点内容】
非流式响应就是一次性返回完整回答。

它的优点：

```plain
代码简单
容易调试
容易保存完整结果
```

缺点：

```plain
用户要等模型全部生成完才能看到结果
长回答体验不好
```

所以非流式适合：

```plain
短文本问答
后台任务
结构化输出
标题生成
分类任务
```

如果是 ChatGPT 这种打字机效果，就要用流式输出。

---

# 十九、16｜流式输出 stream 是什么
## 【实操】
```plain
非流式：
模型生成完整回答后一次性返回

流式：
模型边生成边返回 token/chunk
```

---

## 【重点内容】
stream 表示流式输出。

如果设置：

```json
{
  "stream": true
}
```

模型不是一次性返回完整答案。

而是一小段一小段返回。

前端可以边收边展示。

这就是 ChatGPT 那种逐字输出效果。

DeepSeek 官方文档说明，流式模式下 token 会以 data-only Server-Sent Events 发送，并以 `data: [DONE]` 结束；OpenAI Responses API 的 streaming 文档也说明，设置 `stream=true` 后会通过 server-sent events 发送事件。

---

# 二十、17｜SSE 是什么
## 【实操】
```plain
SSE = Server-Sent Events

服务端持续向客户端发送事件
适合大模型流式输出
```

---

## 【流式返回示意】
```plain
data: {"choices":[{"delta":{"role":"assistant","content":""}}]}

data: {"choices":[{"delta":{"content":"AI"}}]}

data: {"choices":[{"delta":{"content":" Agent"}}]}

data: {"choices":[{"delta":{"content":" 是"}}]}

data: [DONE]
```

---

## 【重点内容】
SSE 是 Server-Sent Events。

它可以让服务端持续向客户端推送数据。

大模型流式输出经常使用 SSE。

每次返回的不是完整 message，而是一个 chunk。

比如：

```json
{
  "delta": {
    "content": "AI"
  }
}
```

下一个 chunk：

```json
{
  "delta": {
    "content": " Agent"
  }
}
```

前端把这些 content 拼起来，就得到完整回答。

---

# 二十一、18｜流式响应怎么解析
## 【伪代码】
```python
full_answer = ""

async for chunk in stream:
    delta = chunk["choices"][0]["delta"]
    content = delta.get("content")

    if content:
        full_answer += content
        yield content
```

---

## 【重点内容】
流式解析的核心就是：

```plain
不断读取 chunk
取 delta.content
拼接到 full_answer
同时把 chunk 推给前端
```

比如：

```plain
chunk1 = "AI"
chunk2 = " Agent"
chunk3 = " 是"
```

拼起来：

```plain
AI Agent 是
```

后面第 16 章我们会专门讲：

```plain
Streaming 流式输出
```

包括 FastAPI 的：

```python
StreamingResponse
```

这一章先讲原理。

---

# 二十二、19｜OpenAI-compatible API 是什么
## 【重点内容】
很多模型厂商会说：

```plain
OpenAI-compatible
```

什么意思？

简单说，就是它们尽量兼容 OpenAI Chat Completions 的接口风格。

比如你可以用类似这样的代码调用不同模型：

```python
client.chat.completions.create(
    model="xxx",
    messages=[...],
)
```

只需要换：

```plain
api_key
base_url
model
```

比如 DeepSeek 官方示例就经常使用 OpenAI SDK 兼容调用方式；Qwen / 阿里云 Model Studio 也提供 OpenAI compatible chat completions 文档。

这对我们设计统一 LLM Provider 非常有帮助。

因为我们可以抽象出：

```plain
统一请求结构
统一响应结构
统一错误处理
统一流式接口
```

不同厂商只在 Provider 内部适配。

---

# 二十三、20｜不同模型 API 的共性
## 【实操】
| 概念 | OpenAI | DeepSeek | Qwen |
| --- | --- | --- | --- |
| API Key | 需要 | 需要 | 需要 |
| model | 需要 | 需要 | 需要 |
| messages / input | 需要 | 需要 | 需要 |
| role | 支持 | 支持 | 支持 |
| temperature | 常见 | 常见 | 常见 |
| stream | 支持 | 支持 | 支持 |
| usage | 支持 | 支持 | 支持 |
| base_url | 官方地址 | DeepSeek 地址 | DashScope / compatible 地址 |


---

## 【重点内容】
不同模型厂商 API 细节会有差异。

但是核心概念是类似的：

```plain
API Key
model
messages
role
temperature
stream
usage
error
```

这就是为什么我们下一章可以封装统一 LLM Provider。

我们不希望业务代码里到处写：

```plain
OpenAI 的请求格式
DeepSeek 的请求格式
Qwen 的请求格式
```

业务代码只应该关心：

```plain
我要调用一个 LLM
传入 messages
拿到 answer 和 usage
```

具体调用哪个厂商，由 Provider 处理。

---

# 二十四、21｜创建 app/llm 目录
## 【屏幕操作】
执行：

```bash
mkdir -p app/llm
touch app/llm/__init__.py
touch app/llm/schemas.py
touch app/llm/examples.py
```

Windows PowerShell：

```powershell
mkdir app\llm
New-Item app\llm\__init__.py
New-Item app\llm\schemas.py
New-Item app\llm\examples.py
```

---

## 【重点内容】
现在我们先创建：

```plain
app/llm
```

目录。

这一章先放基础类型。

下一章会在这里正式扩展：

```plain
base.py
openai_provider.py
deepseek_provider.py
qwen_provider.py
factory.py
```

这一章先不急。

---

# 二十五、22｜定义统一 LLM Schema 雏形
打开：

```plain
app/llm/schemas.py
```

写入：

```python
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class LLMRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class LLMMessage(BaseModel):
    role: LLMRole = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")


class LLMRequest(BaseModel):
    model: str = Field(..., description="模型名称")
    messages: list[LLMMessage] = Field(..., min_length=1, description="消息列表")
    temperature: float = Field(default=0.7, ge=0, le=2, description="温度")
    max_tokens: int | None = Field(default=None, ge=1, description="最大输出 token")
    stream: bool = Field(default=False, description="是否流式输出")
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展信息")


class LLMUsage(BaseModel):
    prompt_tokens: int = Field(default=0, ge=0, description="输入 token")
    completion_tokens: int = Field(default=0, ge=0, description="输出 token")
    total_tokens: int = Field(default=0, ge=0, description="总 token")


class LLMResponse(BaseModel):
    model: str = Field(..., description="模型名称")
    content: str = Field(..., description="模型输出内容")
    usage: LLMUsage = Field(default_factory=LLMUsage, description="Token 用量")
    raw_response: dict[str, Any] = Field(default_factory=dict, description="原始响应")
```

---

## 【重点内容】
现在我们先定义统一 LLM Schema。

注意这还不是最终版本。

它只是下一章 Provider 封装的基础。

我们定义了：

```plain
LLMRole
LLMMessage
LLMRequest
LLMUsage
LLMResponse
```

这个结构跟第 07 章的 ChatRequest / ChatResponse 很像。

但是它更底层。

第 07 章面向业务接口。

这里面向模型调用。

也就是说：

```plain
ChatRequest
= 前端调用我们后端的请求

LLMRequest
= 我们后端调用大模型的请求
```

这两个不是同一层。

---

# 二十六、23｜配置大模型 API Key
打开 `.env`：

```plain
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1

DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com

DASHSCOPE_API_KEY=
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

`.env.example`：

```plain
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1

DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com

DASHSCOPE_API_KEY=
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

---

## 【重点内容】
这里我们先把常见模型服务商配置放到 `.env`。

注意不要把真实 key 提交到 Git。

这里的 base_url 要根据你账号所在平台和地域来调整。

比如 Qwen / 阿里云 Model Studio 有国内地域和国际站差异。

课程里先写一个常见的 compatible mode 示例，实际使用时以官方控制台和文档为准。

---

# 二十七、24｜更新 Settings
打开：

```plain
app/core/config.py
```

增加：

```python
openai_api_key: str = Field(default="")
openai_base_url: str = Field(default="https://api.openai.com/v1")

deepseek_api_key: str = Field(default="")
deepseek_base_url: str = Field(default="https://api.deepseek.com")

dashscope_api_key: str = Field(default="")
qwen_base_url: str = Field(default="https://dashscope.aliyuncs.com/compatible-mode/v1")
```

完整片段：

```python
class Settings(BaseSettings):
    app_name: str = Field(default="AI Agent Course API")
    app_env: str = Field(default="development")
    app_version: str = Field(default="0.1.0")
    api_v1_prefix: str = Field(default="/api/v1")
    debug: bool = Field(default=True)

    app_api_key: str = Field(default="dev-api-key-123")

    default_model: str = Field(default="deepseek-chat")
    supported_models: str = Field(default="deepseek-chat,qwen-plus,gpt-4o-mini")

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/ai_agent_course"
    )

    redis_url: str = Field(default="redis://:redis123@localhost:6379/0")
    redis_default_ttl_seconds: int = Field(default=300)
    rate_limit_window_seconds: int = Field(default=60)
    rate_limit_max_requests: int = Field(default=20)

    openai_api_key: str = Field(default="")
    openai_base_url: str = Field(default="https://api.openai.com/v1")

    deepseek_api_key: str = Field(default="")
    deepseek_base_url: str = Field(default="https://api.deepseek.com")

    dashscope_api_key: str = Field(default="")
    qwen_base_url: str = Field(default="https://dashscope.aliyuncs.com/compatible-mode/v1")
```

---

# 二十八、25｜安装 httpx
如果前面没有安装过：

```bash
uv add httpx
```

或者：

```bash
pip install httpx
```

---

## 【重点内容】
这一章我们先用：

```plain
httpx
```

直接发 HTTP 请求。

为什么不用 SDK？

因为这一章讲 API 原理。

SDK 会帮你隐藏很多细节。

我们先用 httpx 看清楚：

```plain
请求地址
Header
请求体
响应体
错误处理
```

等大家理解原理后，下一章再封装 Provider。

---

# 二十九、26｜脚本一：OpenAI Responses API 示例
创建：

```plain
scripts/llm_openai_responses_demo.py
```

写入：

```python
import asyncio

import httpx

from app.core.config import settings


async def main():
    if not settings.openai_api_key:
        raise RuntimeError("请先在 .env 中配置 OPENAI_API_KEY")

    url = f"{settings.openai_base_url}/responses"

    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "gpt-4.1-mini",
        "input": "请用一句话解释什么是 AI Agent。",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            url,
            headers=headers,
            json=payload,
        )

    print("status_code:", response.status_code)
    print("response:")
    print(response.text)


if __name__ == "__main__":
    asyncio.run(main())
```

运行：

```bash
python scripts/llm_openai_responses_demo.py
```

OpenAI Quickstart 示例展示了通过 `/v1/responses` 创建响应，并读取 `response.output_text` 获取文本输出。

---

## 【重点内容】
这个脚本演示 OpenAI Responses API。

注意它不是 Chat Completions 风格。

它的 endpoint 是：

```plain
/responses
```

请求体里用的是：

```json
{
  "model": "gpt-4.1-mini",
  "input": "..."
}
```

这一章我们不纠结 OpenAI 具体模型名。

实际使用时，你要根据自己账号可用模型选择。

重点是理解：

```plain
URL
Headers
Payload
Response
```

---

# 三十、27｜脚本二：OpenAI-compatible Chat Completions 示例
这个脚本可以用于 DeepSeek，也可以改 base_url 用于 Qwen compatible mode。

创建：

```plain
scripts/llm_openai_compatible_chat_demo.py
```

写入：

```python
import asyncio

import httpx

from app.core.config import settings


async def main():
    if not settings.deepseek_api_key:
        raise RuntimeError("请先在 .env 中配置 DEEPSEEK_API_KEY")

    url = f"{settings.deepseek_base_url}/chat/completions"

    headers = {
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": "你是一个专业的 AI Agent 课程助教。",
            },
            {
                "role": "user",
                "content": "请用一句话解释什么是 AI Agent。",
            },
        ],
        "temperature": 0.7,
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            url,
            headers=headers,
            json=payload,
        )

    print("status_code:", response.status_code)
    print("response:")
    print(response.text)

    if response.status_code == 200:
        data = response.json()
        answer = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        print("answer:", answer)
        print("usage:", usage)


if __name__ == "__main__":
    asyncio.run(main())
```

运行：

```bash
python scripts/llm_openai_compatible_chat_demo.py
```

---

## 【重点内容】
这个脚本是 Chat Completions 风格。

它的请求体里有：

```plain
model
messages
temperature
stream
```

响应解析时，通常从：

```python
data["choices"][0]["message"]["content"]
```

拿到回答。

从：

```python
data["usage"]
```

拿到 token 用量。

这就是很多 OpenAI-compatible 模型的通用解析方式。

---

# 三十一、28｜脚本三：Qwen compatible mode 示例
创建：

```plain
scripts/llm_qwen_compatible_demo.py
```

写入：

```python
import asyncio

import httpx

from app.core.config import settings


async def main():
    if not settings.dashscope_api_key:
        raise RuntimeError("请先在 .env 中配置 DASHSCOPE_API_KEY")

    url = f"{settings.qwen_base_url}/chat/completions"

    headers = {
        "Authorization": f"Bearer {settings.dashscope_api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "qwen-plus",
        "messages": [
            {
                "role": "system",
                "content": "你是一个专业的 AI Agent 课程助教。",
            },
            {
                "role": "user",
                "content": "请用一句话解释 RAG 是什么。",
            },
        ],
        "temperature": 0.7,
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            url,
            headers=headers,
            json=payload,
        )

    print("status_code:", response.status_code)
    print("response:")
    print(response.text)

    if response.status_code == 200:
        data = response.json()
        answer = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        print("answer:", answer)
        print("usage:", usage)


if __name__ == "__main__":
    asyncio.run(main())
```

运行：

```bash
python scripts/llm_qwen_compatible_demo.py
```

Qwen / 阿里云 Model Studio 文档中提供 OpenAI-compatible Chat Completions 调用方式；不同地域和账号体系可能对应不同 base_url，实际项目要以控制台和官方文档为准。

---

## 【重点内容】
这个脚本和 DeepSeek 的脚本非常像。

主要区别是：

```plain
api_key 不同
base_url 不同
model 不同
```

这就说明了为什么我们下一章要封装 Provider。

因为业务层不应该关心这些差异。

业务层只应该写：

```python
response = await llm_provider.chat(messages)
```

---

# 三十二、29｜脚本四：流式输出原理演示
创建：

```plain
scripts/llm_stream_demo.py
```

写入：

```python
import asyncio
import json

import httpx

from app.core.config import settings


async def main():
    if not settings.deepseek_api_key:
        raise RuntimeError("请先在 .env 中配置 DEEPSEEK_API_KEY")

    url = f"{settings.deepseek_base_url}/chat/completions"

    headers = {
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "user",
                "content": "请用三句话解释什么是 AI Agent。",
            }
        ],
        "temperature": 0.7,
        "stream": True,
    }

    full_answer = ""

    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream(
            "POST",
            url,
            headers=headers,
            json=payload,
        ) as response:
            print("status_code:", response.status_code)

            async for line in response.aiter_lines():
                if not line:
                    continue

                if not line.startswith("data:"):
                    continue

                data = line.removeprefix("data:").strip()

                if data == "[DONE]":
                    break

                chunk = json.loads(data)

                delta = chunk["choices"][0].get("delta", {})
                content = delta.get("content")

                if content:
                    full_answer += content
                    print(content, end="", flush=True)

    print("\n\nfull_answer:")
    print(full_answer)


if __name__ == "__main__":
    asyncio.run(main())
```

运行：

```bash
python scripts/llm_stream_demo.py
```

---

## 【重点内容】
这个脚本用来演示流式输出。

重点看：

```python
async with client.stream(...)
```

然后：

```python
async for line in response.aiter_lines():
```

一行一行读取 SSE 数据。

每一行里如果是：

```plain
data: {...}
```

就解析 JSON。

如果是：

```plain
data: [DONE]
```

说明流结束。

然后取：

```python
delta.get("content")
```

拼接成完整回答。

这就是流式输出的底层原理。

---

# 三十三、30｜Qwen 流式 usage 注意点
## 【重点内容】
不同厂商流式 usage 返回方式可能不完全一样。

比如 Qwen / 阿里云 Model Studio 文档提到，流式调用时可以设置 `stream_options={"include_usage": True}`，最后一个 chunk 中可以包含 token usage 信息。

所以统一 Provider 封装时要考虑：

```plain
非流式 usage 从 response.usage 读取

流式 usage 可能在最后一个 chunk

有些模型流式中间 chunk usage 是 null

不同厂商字段名可能不同
```

这也是为什么我们要有统一适配层。

---

# 三十四、31｜大模型 API 常见错误
## 【实操】
| 错误类型 | 常见原因 | 处理方式 |
| --- | --- | --- |
| 401 | API Key 错误 / 未配置 | 检查 key |
| 403 | 无权限 / 模型不可用 | 检查账号权限 |
| 404 | endpoint 或 model 错误 | 检查 URL 和模型名 |
| 429 | 限流 / 额度不足 | 重试、降级、提示用户 |
| 500 | 服务商内部错误 | 重试、降级 |
| timeout | 请求超时 | 设置超时、重试、备用模型 |
| JSON parse error | 响应不是预期 JSON | 打日志、兜底处理 |


---

## 【重点内容】
调用大模型 API 一定要做好错误处理。

常见错误有：

```plain
API Key 错
模型名错
账号没权限
请求太频繁
额度不足
服务商超时
响应格式异常
```

不要直接让异常崩掉接口。

后面我们要把这些错误统一包装成：

```python
AppException(
    code=ErrorCode.LLM_CALL_FAILED,
    message="大模型调用失败"
)
```

这样前端收到的是统一错误格式。

---

# 三十五、32｜错误处理示例
```python
async def call_llm_api():
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(...)
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code
        text = e.response.text

        print("HTTP error:", status_code, text)
        raise

    except httpx.TimeoutException:
        print("LLM request timeout")
        raise

    except httpx.RequestError as e:
        print("Network error:", repr(e))
        raise
```

---

## 【重点内容】
这里先用最简单的错误处理演示。

`HTTPStatusError` 表示 HTTP 状态码不是 2xx。

`TimeoutException` 表示超时。

`RequestError` 表示网络层错误。

下一章封装 Provider 时，我们会把这些错误统一转换成：

```python
AppException
```

---

# 三十六、33｜为什么要设置 timeout
## 【重点内容】
调用 LLM 一定要设置 timeout。

错误示例：

```python
httpx.AsyncClient()
```

没有 timeout，可能一直卡住。

推荐：

```python
httpx.AsyncClient(timeout=30)
```

或者更细：

```python
timeout = httpx.Timeout(
    connect=5,
    read=60,
    write=10,
    pool=5,
)
```

AI 接口经常比普通接口慢。

尤其是：

```plain
长文本生成
RAG 总结
Agent 多步骤任务
Deep Research
```

所以 timeout 要合理设置。

---

# 三十七、34｜为什么要做 retry
## 【重点内容】
大模型服务可能偶尔失败。

比如：

```plain
网络抖动
服务商 500
限流
临时超时
```

所以可以做重试。

但是不能无脑重试。

推荐策略：

```plain
只对临时错误重试
比如 500 / 502 / 503 / timeout

不要对 401 / 403 重试
因为 key 错了重试也没用

429 要根据 Retry-After 或退避策略处理
```

后面 Provider 封装时，我们可以设计：

```plain
max_retries
retry_delay
fallback_model
```

这一章先理解原则。

---

# 三十八、35｜大模型 API 成本意识
## 【重点内容】
大模型 API 调用通常是按 token 计费。

所以后端一定要有成本意识。

影响成本的因素包括：

```plain
输入上下文长度
输出长度
模型价格
调用次数
是否重复请求
是否开启缓存
```

比如：

```plain
上下文越长，prompt_tokens 越多
回答越长，completion_tokens 越多
模型越强，单价通常越高
```

所以后面我们要做：

```plain
usage 记录
Redis 响应缓存
用户限流
max_tokens 限制
历史消息截断
RAG 召回控制
```

这些都和成本有关。

---

# 三十九、36｜token_usage_demo.py
创建：

```plain
scripts/token_usage_demo.py
```

写入：

```python
from app.llm.schemas import LLMUsage


def estimate_cost(
    usage: LLMUsage,
    input_price_per_1k: float,
    output_price_per_1k: float,
) -> float:
    input_cost = usage.prompt_tokens / 1000 * input_price_per_1k
    output_cost = usage.completion_tokens / 1000 * output_price_per_1k

    return input_cost + output_cost


usage = LLMUsage(
    prompt_tokens=1200,
    completion_tokens=800,
    total_tokens=2000,
)

cost = estimate_cost(
    usage=usage,
    input_price_per_1k=0.001,
    output_price_per_1k=0.002,
)

print("usage:", usage.model_dump())
print("cost:", cost)
```

运行：

```bash
python scripts/token_usage_demo.py
```

---

## 【重点内容】
这个脚本只是演示成本计算思路。

公式很简单：

```plain
输入成本 = prompt_tokens / 1000 * 输入单价
输出成本 = completion_tokens / 1000 * 输出单价
总成本 = 输入成本 + 输出成本
```

后面真实项目里，我们会把模型价格配置到数据库或者配置文件里。

然后每次调用后记录 usage 和 cost。

---

# 四十、37｜大模型 API 和我们现有项目的关系
## 【实操】
```plain
POST /api/v1/chat
    ↓
Chat Router
    ↓
ChatService
    ↓
LLM Provider
    ↓
OpenAI / DeepSeek / Qwen API
    ↓
LLMResponse
    ↓
保存 Message + Usage
    ↓
返回 ChatResponse
```

---

## 【重点内容】
现在大家要把大模型 API 放回我们的项目架构里看。

用户不是直接调用模型。

用户调用我们的：

```plain
/api/v1/chat
```

然后 ChatService 调用：

```plain
LLM Provider
```

LLM Provider 再去请求：

```plain
OpenAI
DeepSeek
Qwen
```

拿到结果以后，ChatService 负责：

```plain
保存用户消息
保存 AI 回复
保存 usage
写日志
返回给前端
```

所以 LLM Provider 是我们下一章的重点。

---

# 四十一、38｜为什么不在业务代码里直接调模型
## 【不推荐】
```python
async def chat_with_ai(request):
    response = await httpx.post("https://api.deepseek.com/chat/completions", ...)
    return response.json()
```

---

## 【推荐】
```python
async def chat_with_ai(request):
    response = await llm_provider.chat(messages)
    return response
```

---

## 【重点内容】
不要在 ChatService 里直接写死某个模型厂商。

比如直接写：

```plain
DeepSeek URL
DeepSeek API Key
DeepSeek response 解析逻辑
```

这样后面想换模型会很痛苦。

正确做法是封装 Provider。

业务层只依赖统一接口。

比如：

```plain
LLMProvider.chat()
LLMProvider.stream()
```

具体内部是 OpenAI、DeepSeek、Qwen，由 Provider 自己处理。

这就是下一章要讲的内容。

---

# 四十二、39｜本章知识点和 AI 开发场景对应表
| 知识点 | AI 开发场景 |
| --- | --- |
| API Key | 模型调用鉴权 |
| Base URL | 不同模型服务商地址 |
| Endpoint | `/responses`<br/> / `/chat/completions` |
| model | 选择具体模型 |
| messages | 多轮对话上下文 |
| system role | 定义 AI 行为规则 |
| user role | 用户问题 |
| assistant role | AI 历史回复 |
| tool role | 工具调用结果 |
| temperature | 控制稳定性和创造性 |
| max_tokens | 控制输出长度和成本 |
| stream | 实现打字机效果 |
| SSE | 流式输出底层机制 |
| usage | token 统计和计费 |
| timeout | 防止模型请求卡死 |
| retry | 提升模型调用稳定性 |
| OpenAI-compatible | 统一 Provider 封装基础 |
| LLMRequest | 后端内部统一模型请求 |
| LLMResponse | 后端内部统一模型响应 |


---

# 四十三、40｜本章完整复习
这一章我们完成了：

```plain
1. 理解大模型 API 本质是 HTTP + JSON
2. 理解一次大模型调用完整链路
3. 理解 Base URL / Endpoint / API Key
4. 理解 OpenAI Responses API
5. 理解 Chat Completions API
6. 理解 OpenAI-compatible API
7. 理解 messages 和 prompt 的关系
8. 理解 system / user / assistant / tool
9. 理解 temperature
10. 理解 max_tokens
11. 理解 token 和 usage
12. 理解非流式响应结构
13. 理解流式响应和 SSE
14. 编写 OpenAI Responses API 示例脚本
15. 编写 DeepSeek Chat Completions 示例脚本
16. 编写 Qwen compatible mode 示例脚本
17. 编写流式输出解析脚本
18. 理解大模型 API 常见错误
19. 理解 timeout 和 retry
20. 理解 token 成本计算
21. 创建 app/llm/schemas.py
22. 为下一章 LLM Provider 封装做准备
```

现在我们已经从：

```plain
模拟 AI 回答
```

正式进入：

```plain
真实大模型 API 调用
```

---

# 四十四、41｜常见错误一：API Key 没配
错误：

```plain
401 Unauthorized
```

或者脚本直接报：

```plain
请先在 .env 中配置 API Key
```

检查：

```plain
DEEPSEEK_API_KEY=sk-xxx
OPENAI_API_KEY=sk-xxx
DASHSCOPE_API_KEY=sk-xxx
```

注意不要多空格。

---

# 四十五、42｜常见错误二：base_url 写错
错误：

```plain
404 Not Found
```

或者：

```plain
Connection error
```

检查：

```plain
DEEPSEEK_BASE_URL=https://api.deepseek.com
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

注意不要重复拼：

```plain
/chat/completions/chat/completions
```

---

# 四十六、43｜常见错误三：模型名写错
错误：

```plain
model not found
```

或者：

```plain
无权限访问该模型
```

解决：

```plain
1. 去控制台确认模型名
2. 确认账号是否开通
3. 确认地域是否一致
4. 确认 base_url 是否对应
```

---

# 四十七、44｜常见错误四：stream 解析失败
错误原因：

```plain
把 SSE 当普通 JSON 解析
```

错误写法：

```python
data = response.json()
```

流式时要：

```python
async for line in response.aiter_lines():
    ...
```

---

# 四十八、45｜常见错误五：usage 为空
流式模式下，中间 chunk 的 usage 可能是空。

不要假设每个 chunk 都有 usage。

正确做法：

```plain
非流式：从完整 response 读取 usage

流式：最后一个 chunk 或单独配置 include_usage

没有 usage：先记录 0 或后续补算
```

Qwen 文档就提到流式场景可以通过 `stream_options.include_usage` 让最后一个 chunk 带 usage。

---

# 四十九、46｜常见错误六：把完整 Prompt 打到日志
不推荐：

```python
logger.info(f"prompt={messages}")
```

推荐：

```python
logger.info(
    f"llm_request model={model} message_count={len(messages)}"
)
```

原因：

```plain
messages 里可能包含用户隐私
可能包含企业知识库内容
可能包含内部系统数据
```

日志要记录必要信息，但不要泄露敏感数据。

---

# 五十、47｜课后任务一：跑通一个非流式 API
要求：

```plain
1. 任选 DeepSeek / Qwen / OpenAI
2. 在 .env 配置 API Key
3. 运行对应 demo 脚本
4. 打印 status_code
5. 打印 answer
6. 打印 usage
```

---

# 五十一、48｜课后任务二：跑通一个流式 API
要求：

```plain
1. 使用 scripts/llm_stream_demo.py
2. 设置 stream=True
3. 一边接收一边 print
4. 拼接 full_answer
5. 输出最终 full_answer
```

---

# 五十二、49｜课后任务三：封装一个 parse_chat_completion_response
要求：

创建：

```plain
app/llm/examples.py
```

写入函数：

```python
from app.llm.schemas import LLMResponse, LLMUsage


def parse_chat_completion_response(data: dict) -> LLMResponse:
    choice = data["choices"][0]
    message = choice["message"]
    usage_data = data.get("usage") or {}

    usage = LLMUsage(
        prompt_tokens=usage_data.get("prompt_tokens", 0),
        completion_tokens=usage_data.get("completion_tokens", 0),
        total_tokens=usage_data.get("total_tokens", 0),
    )

    return LLMResponse(
        model=data.get("model", ""),
        content=message.get("content", ""),
        usage=usage,
        raw_response=data,
    )
```

---

# 五十三、50｜课后任务四：设计 LLM 错误码
要求在：

```plain
app/core/exceptions.py
```

补充或整理：

```plain
LLM_API_KEY_MISSING = 50010
LLM_MODEL_NOT_FOUND = 50011
LLM_RATE_LIMITED = 50012
LLM_TIMEOUT = 50013
LLM_RESPONSE_PARSE_FAILED = 50014
LLM_PROVIDER_ERROR = 50015
```

思考：

```plain
哪些错误给用户看
哪些错误只写日志
哪些错误可以重试
哪些错误不能重试
```

---

# 五十四、51｜课后任务五：画出大模型 API 调用链路
画出：

```plain
POST /api/v1/chat
```

未来接入真实模型后的链路：

```plain
HTTP Request
 ↓
Middleware trace_id
 ↓
verify_api_key
 ↓
rate_limit
 ↓
get_current_user
 ↓
get_db_session
 ↓
get_redis_client
 ↓
Chat Router
 ↓
ChatService
 ↓
LLMProvider.chat()
 ↓
DeepSeek / Qwen / OpenAI API
 ↓
LLMResponse
 ↓
保存 Message + Usage
 ↓
返回 ChatResponse
```

---

# 五十五、52｜本章总结
## 【重点内容】
好了，到这里，第 13 章我们就讲完了。

这一章我们正式进入了大模型 API。

这一章大家一定要掌握几个核心概念：

```plain
API Key
Base URL
Endpoint
model
messages
role
temperature
max_tokens
stream
SSE
token
usage
timeout
retry
```

不要一上来就陷入某个 SDK。

SDK 只是封装。

底层本质还是：

```plain
HTTP 请求
+
JSON 请求体
+
JSON 响应体
+
错误处理
+
流式解析
```

我们这一章已经写了几个脚本：

```plain
OpenAI Responses API 示例
DeepSeek Chat Completions 示例
Qwen compatible mode 示例
流式输出示例
token usage 成本示例
```

这些脚本的目标不是做完整业务，而是帮大家理解原理。

下一章我们会把这一章的原理封装起来 
