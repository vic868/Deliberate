---
title: "第 01 章｜为什么 Python 是 AI Agent 开发的核心语言"
chapter: "01"
source: "第 01 章：为什么 Python 是 AI Agent 开发的核心语言.md"
type: obsidian-note
created: 2026-11-22
status: 整理中
tags:
  - course/llm-agent
  - python
  - ai-agent
  - 技术栈
---

# 第 01 章｜为什么 Python 是 AI Agent 开发的核心语言

> [!abstract] 本章重点
>
> - ==AI 生态本身就是 Python 生态== — PyTorch、Transformers、LangChain 的源码都是 Python，要读要改就绕不开。
> - ==Python + FastAPI 负责后端这一层== — 模型和前端之间的服务，用 FastAPI 来写。
> - ==LangChain 管组件，LangGraph 管流程== — 前者把模型、工具、提示拼起来，后者控制多步流程怎么走、怎么回退。
> - ==RAG / Tool / MCP / Multi-Agent== — 分别解决：查资料、调外部函数、工具协议、多个 Agent 分工协作。
>
> [!note] 大白话
>
> - **AI Agent**：让大模型自己决定下一步干什么，必要时调用工具，直到把事情办完。
> - **DeepAgents**：在 LangGraph 之上再封一层，用于更长、更复杂的任务规划。
>
> [!info] 导航与来源
> - 原始讲义：[[第 01 章：为什么 Python 是 AI Agent 开发的核心语言|打开原始讲义]]
> - [[第 02 章｜Python AI 开发环境搭建|下一章｜第 02 章]]
> - 本章所有内容均保留，未删改原文。

## 本章导航

- [[#课程目标]]
- [[#1-1 为什么现在做 AI Agent 必须掌握 Python]]
- [[#1-2 前端/后端开发者为什么学 Python 并不难]]
- [[#1-3 Python 在 AI Agent 技术栈中的位置]]
- [[#1-4 为什么不直接调用大模型？]]
- [[#原生开发阶段]]
- [[#1-5 LangChain 是干什么的？]]
- [[#1-6 LangGraph 又是干什么的？]]
- [[#LangGraph]]
- [[#1-7 那 DeepAgents 又是什么？]]
- [[#DeepAgents]]
- [[#1-8 RAG 是什么？]]
- [[#Retrieval Augmented Generation]]
- [[#1-9 Tool Calling 是什么？]]

---
**“我为什么要学 Python？Python 和 AI 到底是什么关系？这门课最终能让我做到什么？”**

---

## 课程目标
能够回答下面 5 个问题：

```text
1. 为什么 AI 开发大量使用 Python？

2. 为什么做AI Agent开发，推荐先学 Python？

3. Python + FastAPI 在 AI 应用里面负责什么？

4. LangChain / LangGraph / DeepAgents 分别解决什么问题？

5. 学完这门课，我最终到底能够开发什么？
```

---

## 目录
```text
第一章 为什么 Python 是 AI Agent 开发的核心语言

1-1 为什么现在做 AI Agent 要掌握 Python
1-2 Python 和前端 JavaScript / TypeScript、Java有什么关系
1-3 Python 在 AI Agent 技术栈中的位置
1-4 这门课到底学什么
1-5 AI Agent 开发完整技术栈
1-6 为什么选择 FastAPI
1-7 LangChain / LangGraph / DeepAgents 是什么
1-8 RAG / Tool / MCP / Multi-Agent 是什么
1-9 第一个 AI Agent 项目最终长什么样
1-10 本课程最终能做什么
```

---

## 1-1 为什么现在做 AI Agent 必须掌握 Python
---

### 第一个原因：AI 生态本身就是 Python 生态
我们打开 GitHub 或者 AI 相关项目的时候，会发现一个非常明显的现象。

大量 AI 项目：

```text
PyTorch
Transformers
Hugging Face
LangChain
LangGraph
DeepAgents
LlamaIndex
```

背后都大量使用 Python。

==所以你以后真正进入 AI 开发之后，会发现一个问题：==

你可能不只是需要：

```text
调用一个 API
```

而是需要：

```text
阅读源码
修改代码
调试代码
扩展框架
实现自己的 Agent
```

这个时候 Python 就不是一个“可选项”了。

---

## 1-2 前端/后端开发者为什么学 Python 并不难
因为你的课程非常适合：

```text
前端开发者
Node.js 开发者
Java 后端
传统后端
AI 转型人员
```

---



## 【展示】
| TypeScript | Python |
| --- | --- |
| `string` | `str` |
| `number` | `int / float` |
| `boolean` | `bool` |
| `null` | `None` |
| `undefined` | `None / Optional` |
| `Array` | `list` |
| `Object` | `dict` |
| `function` | `def` |
| `class` | `class` |
| `this` | `self` |
| `async/await` | `async/await` |
| `for...of` | `for...in` |
| `try/catch` | `try/except` |


这个对比方式也与你提供的参考材料保持一致。

---

## 【内容】
比如 TypeScript 我们写一个函数：

```json
function greet(name: string): string {
  return `你好，${name}`;
}
```

Python：

```python
def greet(name: str) -> str:
    return f"你好，{name}"
```

其实你仔细看一下：

```markdown
function
↓
def

string
↓
str

return
↓
return
```

核心思想没有变化。

再比如 TypeScript：

```javascript
const users = ["张三", "李四", "王五"];

for (const user of users) {
  console.log(user);
}
```

Python：

```javascript
users = ["张三", "李四", "王五"]

for user in users:
print(user)
```

是不是非常像？

==所以对于已经有开发经验的人来说：==

**你不是从零学习编程，而是在学习另外一种语言。**

这一点大家一定要建立信心。

---

## 1-3 Python 在 AI Agent 技术栈中的位置
这一节开始建立整套课程的技术地图。

---

## 【完整技术架构】
```text
               用户
                 ↓
              前端 Web
                 ↓
              FastAPI 
                 ↓
        ┌────────┴────────┐
        ↓                 ↓
      AI Chat           Agent
        ↓                 ↓
      LLM API        LangChain
                         ↓
                    LangGraph
                         ↓
                    DeepAgents
                         ↓
                 ┌───────┴───────┐
                 ↓               ↓
                RAG             Tools
                 ↓               ↓
            pgvector            MCP
                 │               │
                 └───────┬───────┘
                         ↓
                   Multi-Agent
                         ↓
                      企业系统
```

---

## 1-4 为什么不直接调用大模型？
这里建议你专门讲一下。

---

这个时候很多同学可能会问：

那我直接用 Python 调用 DeepSeek 或者 OpenAI 不就行了吗？

当然可以。

事实上我们课程前面就会这么干。

我们会先使用：

```text
Python
+
FastAPI
+
LLM API
```

自己开发一个 AI Chat。

为什么？

因为我希望大家先理解：

**大模型应用到底是怎么工作的。**

而不是一上来就：

```python
from langchain import ...
```

然后复制粘贴代码。

---

## 原生开发阶段
我们会先自己实现：

```text
用户问题
 ↓
FastAPI
 ↓
LLM
 ↓
Response
```

然后进一步实现：

```text
用户问题
 ↓
FastAPI
 ↓
LLM
 ↓
Streaming
 ↓
SSE
 ↓
前端
```

再进一步：

```text
用户问题
 ↓
LLM
 ↓
Tool Calling
 ↓
调用业务 API
 ↓
Tool Result
 ↓
LLM
 ↓
最终回答
```

做到这里以后，你就会发现：

Agent 的代码开始越来越复杂。

这时候：

**LangChain 才真正有意义。**

---

## 1-5 LangChain 是干什么的？
---

## 【核心内容】

> [!important] 重点标记
> 这一节是本章核心，建议慢读。

我们来看 LangChain。

大家不要把 LangChain 理解成：

“一个调用大模型的 SDK。”

这个理解太浅了。

LangChain 更重要的价值是：

**把大模型应用开发里面大量重复的能力抽象出来。**

比如：

```text
Model
Prompt
Message
Tool
Retriever
Structured Output
Agent
```

这些东西我们以后都会用到。

---

## 【实操】
```text
原生开发：

Python
 ↓
LLM API
 ↓
自己处理 Prompt
自己处理 Tool
自己处理 Message
自己处理 RAG
自己处理 Agent Loop
```

然后：

```text
LangChain：

Python
 ↓
LangChain
 ├── Model
 ├── Prompt
 ├── Message
 ├── Tool
 ├── Retriever
 └── Agent
```

---

## 【核心】

> [!important] 重点标记
> 这一节是本章核心，建议慢读。

==所以 LangChain 解决的是：==

**AI 应用开发的工程抽象问题。**

---

## 1-6 LangGraph 又是干什么的？
---

## 【核心内容】
当我们使用 LangChain 开发 Agent 之后，会遇到一个新的问题。

比如一个简单客服 Agent：

```text
用户
 ↓
Agent
 ↓
查询订单
 ↓
返回
```

非常简单。

但是企业里面真实的流程可能是：

```text
用户
 ↓
意图识别
 ↓
判断问题类型
 ↓
查询订单
 ↓
判断是否需要退款
 ↓
判断金额
 ↓
超过 1000 元
 ↓
人工审批
 ↓
继续执行
 ↓
生成最终回答
```

这个时候你会发现：

它已经不是简单的一次 Tool Calling 了。

它其实是一个：

**有状态、有条件、有分支、有人工介入的执行流程。**

所以我们就需要：

## LangGraph
---

## 实操
```text
START
  ↓
Intent
  ↓
Router
  ├────→ Order
  │
  ├────→ Product
  │
  └────→ RAG
          ↓
        Review
          ↓
        Human
          ↓
        Answer
          ↓
         END
```

---

## 【核心】

> [!important] 重点标记
> 这一节是本章核心，建议慢读。

==LangGraph 的核心概念非常简单：==

```text
State
Node
Edge
```

你可以把它理解成：

**用一个图来描述 Agent 的执行过程。**

所以：

```text
LangChain
```

更多解决：

模型、Prompt、Tool、Agent 等基础能力。

而：

```text
LangGraph
```

更适合解决：

**复杂、有状态、可控制的 Agent 工作流。**

---

## 1-7 那 DeepAgents 又是什么？
这一节一定要讲。

因为这是你这套课程和普通 LangChain 课程的一个明显差异。

---

## 【核心内容】

> [!important] 重点标记
> 这一节是本章核心，建议慢读。

如果 Agent 再复杂一点呢？

比如用户告诉 Agent：

“帮我分析一下 AI Agent 行业，研究国内外主要厂商、技术路线、开源项目，最后给我生成一份行业分析报告。”

大家想一下。

这个任务不是：

```text
调用一次 LLM
```

也不是：

```text
调用一个 Tool
```

它实际上需要：

```text
制定计划
 ↓
拆分任务
 ↓
搜索资料
 ↓
分析公司
 ↓
分析技术
 ↓
汇总结果
 ↓
生成报告
 ↓
检查报告
 ↓
最终输出
```

这就是所谓的：

**复杂 Agent / Deep Agent。**

---

## 【实操】
```text
                    Main Agent
                        │
                     Planning
                        │
        ┌───────────────┼───────────────┐
        ↓               ↓               ↓
   Research Agent   Data Agent     Analysis Agent
        │               │               │
        └───────────────┼───────────────┘
                        ↓
                   Report Agent
                        ↓
                    Final Report
```

---

## 【内容】
这时候我们课程会进入：

## DeepAgents
重点学习：

```text
Planning
Task Decomposition
Sub-Agent
Long-running Task
Context Management
Filesystem
```

==所以大家记住我们这门课程的技术递进：==

```text
LLM
 ↓
Tool Calling
 ↓
LangChain
 ↓
LangGraph
 ↓
DeepAgents
```

这不是五个毫无关系的东西。

而是：

**Agent 能力不断升级的过程。**

---

## 1-8 RAG 是什么？
---

## 【核心内容】

> [!important] 重点标记
> 这一节是本章核心，建议慢读。

接下来我们再看一个非常重要的东西：

## RAG
很多刚接触 AI 的同学会把 RAG 和 Agent 混在一起。

这是不对的。

RAG 解决的是一个非常具体的问题：

**大模型不知道你的私有数据怎么办？**

比如：

```text
公司规章制度
产品说明书
员工手册
售后政策
技术文档
PDF
Word
数据库
```

这些数据没有被模型训练进去。

怎么办？

我们可以：

```text
用户问题
 ↓
检索企业知识库
 ↓
找到相关内容
 ↓
交给 LLM
 ↓
生成回答
```

这就是：

## Retrieval Augmented Generation
也就是：

**检索增强生成。**

---

## 【实操】
```text
                 用户问题
                    ↓
                Embedding
                    ↓
              Vector Search
                    ↓
               Relevant Docs
                    ↓
                  Context
                    ↓
                   LLM
                    ↓
                  Answer
```

---

## 1-9 Tool Calling 是什么？
---

## 【内容】
但是还有一个问题。

大模型本身只能：

**思考和生成内容。**

它不能天然知道：

```text
你的订单
你的数据库
你的 CRM
你的 ERP
你的公司 API
```

==所以我们需要给 Agent 提供工具。==

比如：

```text
query_order()
query_product()
query_logistics()
refund_order()
```

然后：

```text
用户
 ↓
Agent
 ↓
判断需要查询订单
 ↓
query_order()
 ↓
返回订单数据
 ↓
Agent
 ↓
生成回答
```

这就是：

**Tool Calling。**

---

## 1-10 MCP 是什么？
---

## 【内容】
那大家可能又会问：

Tool Calling 已经可以调用工具了，为什么还需要 MCP？

这是后面我们会重点讲的。

现在先建立一个简单认知。

传统方式：

```text
Agent
 ↓
Tool
 ↓
业务系统
```

每一个 Agent 都自己维护一套 Tool。

如果企业里面有：

```text
CRM
ERP
OA
数据库
订单系统
知识库
```

工具会越来越多。

MCP 希望解决的是：

**把这些能力标准化，让 Agent 更容易连接外部工具和数据。**

==所以后面我们会自己开发：==

```text
MCP Server
```

然后让 Agent：

```text
Agent
 ↓
MCP
 ↓
CRM
ERP
Database
Knowledge Base
```

---

## 1-11 Multi-Agent 是什么？
---

## 【核心内容】

> [!important] 重点标记
> 这一节是本章核心，建议慢读。

最后还有一个概念：

## Multi-Agent
为什么需要多个 Agent？

假设现在有一个非常复杂的任务。

一个 Agent 什么都干：

```text
搜索
分析
写代码
查数据
写报告
```

它的 Prompt 会越来越复杂。

所以我们可以拆成：

```text
Supervisor Agent
       │
 ┌─────┼─────┐
 ↓     ↓     ↓
Research  Data  Report
Agent     Agent Agent
```

每一个 Agent 负责一个领域。

比如：

```text
Research Agent
= 搜索资料

Data Agent
= 分析数据

Customer Agent
= 处理客服

Report Agent
= 生成报告
```

==这就是 Multi-Agent。==

---

## 1-12 课程完整技术栈
现在把前面所有东西串起来。

---

## 【实操】
```text
┌─────────────────────────────────────────────┐
│                   前端应用                    │
└──────────────────────┬──────────────────────┘
                       ↓
┌─────────────────────────────────────────────┐
│                   FastAPI                   │
│        REST API / SSE / Auth / Middleware   │
└──────────────────────┬──────────────────────┘
                       ↓
┌─────────────────────────────────────────────┐
│                    Python                   │
└──────────────────────┬──────────────────────┘
                       ↓
              ┌────────┴────────┐
              ↓                 ↓
           LLM API             RAG
              ↓                 ↓
         Tool Calling       pgvector
              ↓                 │
          LangChain             │
              ↓                 │
          LangGraph             │
              ↓                 │
         DeepAgents             │
              └────────┬────────┘
                       ↓
                     MCP
                       ↓
                 Multi-Agent
                       ↓
                 企业业务系统
```

---

## 1-13 数据库和基础设施
这一部分也需要提前讲清楚。

---

## 【内容】
除了 AI 框架，我们还需要一些基础设施。

第一个：

## PostgreSQL
它负责：

```text
用户
会话
消息
Agent
知识库
文档
权限
```

等等这些结构化数据。

---

第二个：

## pgvector
它是 PostgreSQL 的向量扩展。

我们的 RAG：

```text
Document
 ↓
Embedding
 ↓
Vector
 ↓
pgvector
```

都会用到它。

---

第三个：

## Redis
Redis 主要用于：

```text
缓存
Session
临时状态
Agent 状态
限流
任务
```

---

第四个：

## Docker
最终我们不能只做到：

```text
我的电脑可以运行
```

而是要做到：

```text
Docker
 ↓
Production
```

==所以最后会把整个 AI Agent 系统进行容器化部署。==

---

## 1-14 打开 VS Code：建立课程项目
现在开始第一次真正的实操。

---

### 【操作】
打开终端。

创建项目：

```bash
mkdir ai-agent-course
cd ai-agent-course
```

---

### 【内容】
这里我先创建一个项目：

```text
ai-agent-course
```

后面整门课程，我们都会围绕这个项目不断迭代。

也就是说：

**不是每一章重新创建一个项目。**

而是：

```text
第一章
 ↓
创建项目

第二章
 ↓
加入 Python 基础代码

第三章
 ↓
加入 FastAPI

第四章
 ↓
加入 LLM

第五章
 ↓
加入 LangChain

...
```

最后它会逐渐成长成一个完整的：

**企业级 AI Agent 平台。**

---

## 1-15 查看项目目录
执行：

```text
pwd
```

然后：

```text
ls
```

Windows 可以：

```text
dir
```

---

## 【内容】
现在目录还是空的。

我们先建立最终项目的大致结构。

执行：

```text
mkdir app
mkdir tests
```

Mac / Linux：

```text
mkdir -p app/{api,services,models,schemas,core,agents,rag,mcp}
```

Windows PowerShell：

```text
mkdir app
mkdir tests
mkdir app/api
mkdir app/services
mkdir app/models
mkdir app/schemas
mkdir app/core
mkdir app/agents
mkdir app/rag
mkdir app/mcp
```

最终结构：

```text
ai-agent-course/
├── app/
│   ├── api/
│   ├── services/
│   ├── models/
│   ├── schemas/
│   ├── core/
│   ├── agents/
│   ├── rag/
│   └── mcp/
├── tests/
└── README.md
```

---

## 1-16 为什么要提前设计目录？
## 【内容】
可能有同学会问：

老师，我们现在不是还没写 FastAPI 吗？为什么现在就创建这些目录？

因为我们不是在写 Demo。

我们最终要做的是：

**企业级 AI Agent 应用。**

==所以我们提前建立一个基本的工程结构。==

后面：

```text
agents/
```

放 Agent。

```text
rag/
```

放 RAG。

```text
mcp/
```

放 MCP。

```text
services/
```

放业务服务。

```text
schemas/
```

放 Pydantic 数据模型。

这样后面项目越来越大的时候，不会所有代码全部堆在一个：

```text
main.py
```

里面。

---

## 1-17 第一次建立 README
创建：

```text
README.md
```

内容：

```text
# AI Agent 全栈开发实战

Python + FastAPI + LLM + LangChain + LangGraph + DeepAgents + RAG + MCP

## 技术栈

- Python
- FastAPI
- Pydantic
- PostgreSQL
- Redis
- pgvector
- LangChain
- LangGraph
- DeepAgents
- RAG
- MCP
- Multi-Agent
- Docker

## 项目目标

最终构建一个企业级 AI Agent 平台。
```

---

## 1-18 第一个 Python 程序
==这一章虽然不是正式讲 Python，但是建议做一个非常小的实操。==

创建：

```text
app/main.py
```

代码：

```python
def main():
    print("Hello AI Agent")


if __name__ == "__main__":
    main()
```

运行：

```text
python app/main.py
```

输出：

```text
Hello AI Agent
```

---

## 【内容】
这里大家注意一下。

虽然我们还没有开始系统学习 Python。

但是我希望大家先建立一个概念：

Python 的程序入口经常会看到：

```python
if __name__ == "__main__":
```

它的作用可以简单理解成：

**只有直接运行这个文件的时候，才执行下面的 main。**

后面我们会详细讲。

现在知道这个概念就可以了。

---

## 1-19 第一个 FastAPI Demo
如果你希望第一章录制效果更强，我强烈建议这里直接做一个**30 秒 FastAPI Demo**。

虽然 FastAPI 正式内容放第二阶段，但第一章让学员看到结果，会极大提升课程的吸引力。

---

### 安装 FastAPI
```bash
pip install fastapi uvicorn
```

创建：

```text
app/api.py
```

代码：

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    return {
        "message": "Hello AI Agent"
    }
```

启动：

```text
uvicorn app.api:app --reload
```

看到：

```http
Uvicorn running on http://127.0.0.1:8000
```

打开：

```http
http://127.0.0.1:8000
```

返回：

```json
{
  "message": "Hello AI Agent"
}
```

---

## 【内容】
大家注意。

现在我们虽然只写了十几行代码，但是已经出现了整个课程里面非常重要的一条链路：

```text
Python
 ↓
FastAPI
 ↓
HTTP API
```

后面我们会把它变成：

```text
Python
 ↓
FastAPI
 ↓
LLM
 ↓
RAG
 ↓
Agent
 ↓
Tool
 ↓
MCP
 ↓
Multi-Agent
```

所以你现在看到的这个：

```http
GET /
```

只是整个课程的起点。

---

## 1-20 FastAPI 自动生成 Swagger
打开：

```http
http://127.0.0.1:8000/docs
```

---

## 【内容】
大家看这里。

这是 FastAPI 非常方便的地方。

我们什么都没配置，它就自动给我们生成了：

OpenAPI / Swagger 文档。

后面我们开发：

```text
/chat
/knowledge
/agent
/mcp
```

这些接口的时候，都会自动出现在这里。

这也是为什么：

**FastAPI 非常适合拿来做 AI 应用后端。**

---

## 【最终内容】
大家现在看到的这些东西：

```text
AI Chat
RAG
Agent
Tool Calling
Multi-Agent
```

后面都会由我们自己一步一步开发出来。

我希望大家注意：

**这门课不是让你学会复制几个 LangChain 示例代码。**

我们会从：

```text
Python
```

开始。

然后：

```text
FastAPI
```

解决 AI 后端问题。

然后：

```text
原生 LLM API
```

理解大模型应用到底是怎么工作的。

再进入：

```text
LangChain
```

学习 AI 应用开发的基础抽象。

然后：

```text
LangGraph
```

开发复杂、有状态的 Agent Workflow。

再进入：

```text
DeepAgents
```

解决 Planning、Sub-Agent、长任务、复杂任务拆解。

然后加入：

```text
RAG
Tool
MCP
Multi-Agent
```

最后：

```text
Docker
Redis
PostgreSQL
pgvector
```

把整个系统部署起来。

---

## 1-22 第一章总结

> [!success] 复盘要点
> 复盘时重点看这一节。

### 【核心内容】
好，到这里第一章我们就结束了。

==这一章大家不需要记住 Python 的语法。==

因为 Python 语法，我们下一章开始会系统学习。

这一章大家只需要记住下面这张图。

---

## 【最终 PPT / 屏幕】
```markdown
                  AI Agent 全栈开发

                       Python
                         ↓
                      FastAPI
                         ↓
                    LLM 原生开发
                         ↓
                   Tool Calling
                         ↓
                    LangChain
                         ↓
                    LangGraph
                         ↓
                    DeepAgents
                         ↓
               ┌─────────┴─────────┐
               ↓                   ↓
              RAG                 MCP
               ↓                   ↓
               └─────────┬─────────┘
                         ↓
                    Multi-Agent
                         ↓
                  企业业务系统
                         ↓
            PostgreSQL / Redis / pgvector
                         ↓
                       Docker
                         ↓
                      生产环境
```

---

## 【最后一段内容】
所以，如果你现在是做过一个前端或者是java开发者，不要觉得：

“我是不是要重新学习一门 Python，然后从零开始。”

其实不是。

你已经有：

```text
JavaScript / TypeScript / java 
HTTP
API
前后端交互
工程化
Git
Node.js spring-boot 
```

这些开发经验。

我们只是把后端语言从：

```text
JavaScript / TypeScript  java 
```

扩展到：

```text
Python
```

然后进入 AI 应用开发。

==所以接下来我们正式开始：==

---

## 第一章需要准备的代码文件
```markdown
ai-agent-course/
├── app/
│   ├── main.py
│   └── api.py
├── tests/
└── README.md
```

#### `app/main.py`
```python
def main():
    print("Hello AI Agent")


if __name__ == "__main__":
    main()
```

#### `app/api.py`
```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    return {
        "message": "Hello AI Agent"
    }
```

#### `README.md`
```markdown
# AI Agent 全栈开发实战

Python + FastAPI + LLM + LangChain + LangGraph + DeepAgents + RAG + MCP

## 学习目标

从 Python 后端开发开始，逐步完成：

- LLM Chat
- Streaming
- RAG
- Tool Calling
- LangChain Agent
- LangGraph Agent
- DeepAgents
- MCP
- Multi-Agent
- 企业级 AI Agent

## 最终项目

Enterprise AI Agent Platform
```

---

---

> [!success] 一句话带走
> ==学 Python 不是为了语法，是为了能读懂并改造 AI 框架本身。==

> [!quote] 关于本文档
> 由原始讲义 `第 01 章：为什么 Python 是 AI Agent 开发的核心语言.md` 转换为 Obsidian 风格笔记；原文完整保留，未做任何删改。
> 整理日期：2026-11-22
