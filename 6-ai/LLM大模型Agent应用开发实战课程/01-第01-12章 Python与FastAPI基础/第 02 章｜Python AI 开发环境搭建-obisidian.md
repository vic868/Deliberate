---
title: "第 02 章｜Python AI 开发环境搭建"
chapter: "02"
source: "第 02 章｜Python AI 开发环境搭建.md"
type: obsidian-note
created: 2026-11-22
status: 整理中
tags:
  - course/llm-agent
  - python
  - uv
  - 虚拟环境
---

# 第 02 章｜Python AI 开发环境搭建

> [!abstract] 本章重点
>
> - ==不要直接使用系统 Python== — 系统自带 Python 被系统工具依赖，往里装包容易把环境搞乱。
> - ==虚拟环境 = 每个项目一个独立房间== — 项目之间的依赖互不干扰。
> - ==venv 是自带方案，uv 是更快的现代方案== — 先理解 venv 在做什么，再用 uv 提效。
> - ==Python 3.1x 优先== — AI 框架对新版本支持最及时。
> - ==课程主项目从这一章开始== — 后面所有章节都在这个项目上继续加代码。

> [!note] 大白话
>
> - **虚拟环境**：给项目单独开一个装包的抽屉，不碰别人的东西。
> - **pyproject.toml**：项目的说明书，写清依赖和版本。

> [!info] 导航与来源
> - 原始讲义：[[第 02 章｜Python AI 开发环境搭建|打开原始讲义]]
> - [[第 01 章：为什么 Python 是 AI Agent 开发的核心语言|上一章｜第 01 章]]
> - [[第 03 章｜Python AI 开发快速入门|下一章｜第 03 章]]
> - 本章所有内容均保留，未删改原文。

## 本章导航

- [[#一、本章学习目标]]
- [[#二、本章最终项目结构]]
- [[#三、01 为什么环境搭建非常重要]]
- [[#四、02｜检查电脑当前有没有 Python]]
- [[#五、03｜Python 版本怎么选择]]
- [[#六、04｜为什么建议使用 Python 3.13]]
- [[#七、05｜安装 Python]]
- [[#八、06｜为什么我不建议直接使用系统 Python]]
- [[#虚拟环境]]
- [[#九、07｜什么是 Python 虚拟环境]]
- [[#十、08｜使用 Python 自带的 venv]]
- [[#十一、09｜激活虚拟环境]]
- [[#十二、10｜检查虚拟环境是否生效]]
- [[#十三、11｜退出虚拟环境]]

---

## 一、本章学习目标

> [!abstract] 本节定位
> 先看清这一节要解决什么问题。

这一章我们不讲复杂的 Python 语法。

这一章只有一个目标：

> **把开发 AI Agent 所需要的完整 Python 开发环境搭建起来，并且让第一个 Python + FastAPI 项目真正跑起来。**
>

学完这一章以后，你需要能够独立完成：

```latex
Python 安装
    ↓
Python 版本检查
    ↓
VS Code 配置
    ↓
Python 虚拟环境
    ↓
pip / uv 包管理
    ↓
安装 FastAPI
    ↓
安装 Uvicorn
    ↓
创建项目
    ↓
启动 FastAPI
    ↓
访问 API
    ↓
访问 Swagger
    ↓
创建 requirements.txt
    ↓
配置 .env
    ↓
Git 忽略配置
```

最终我们的开发环境变成：

```bash
  Mac / Windows
       ↓
    Python
       ↓
   uv / pip
       ↓
  Virtual Environment
       ↓
  VS Code
       ↓
  FastAPI
       ↓
  Uvicorn
       ↓
AI Agent Project
```

---

## 二、本章最终项目结构
这一章结束之后，我们会得到这样一个项目：

```text
ai-agent-course/
├── app/
│   ├── __init__.py
│   └── main.py
│
├── tests/
│
├── .env
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
└── uv.lock
```

如果使用 `requirements.txt` 管理依赖，也可以得到：

```text
ai-agent-course/
├── app/
│   ├── __init__.py
│   └── main.py
│
├── tests/
│
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

后面的课程，我们会不断往这个项目里面增加：

```text
FastAPI
LLM
RAG
LangChain
LangGraph
DeepAgents
MCP
Multi-Agent
PostgreSQL
Redis
pgvector
Docker
```

==所以从这一章开始，这个项目就是我们整个课程的主项目。==



## 三、01 为什么环境搭建非常重要
### 【重点内容】
大家好，欢迎来到第二章。

上一章我们已经讲清楚了：

为什么现在做 AI Agent，需要掌握 Python。

我们也把整门课程的技术路线梳理了一遍：

```text
Python
 ↓
FastAPI
 ↓
LLM
 ↓
Tool Calling
 ↓
LangChain
 ↓
LangGraph
 ↓
DeepAgents
 ↓
RAG
 ↓
MCP
 ↓
Multi-Agent
```

那么这一章，我们正式开始动手。

但是在正式写 Python 之前，我们必须先解决一个问题：

**把开发环境搭建起来。**

很多刚开始学 Python 的同学，真正浪费时间的地方并不是代码。

而是：

```bash
Python 版本不对
pip 装错环境
虚拟环境没有激活
VS Code 没选择正确解释器
依赖装到了系统 Python
Mac 和 Windows 命令不一样
```

最后代码明明没有问题，但是就是跑不起来。

==所以这一章我会带着大家，从零开始把整个环境配置好。==

而且我们不是只安装一个 Python。

我们会把：

```text
Python
虚拟环境
VS Code
包管理器
FastAPI
Uvicorn
环境变量
Git
```

全部配置好。

这样从下一章开始，我们就可以专心学习 Python 和 AI，而不是每天解决环境问题。

---

## 四、02｜检查电脑当前有没有 Python
### 【实操】
打开终端。

Mac：

```text
Command + Space
```

搜索：

```text
Terminal
```

Windows：

打开：

```text
PowerShell
```

或者：

```text
Windows Terminal
```

---

### 【内容】
首先我们不要急着安装。

先检查一下自己的电脑有没有 Python。

执行：

```text
python --version
```

如果没有，再执行：

```text
python3 --version
```

也可以：

```text
python3 -V
```

---

### 【预期结果】
例如：

```text
Python 3.13.x
```

或者：

```text
Python 3.13.x
```

---

## 五、03｜Python 版本怎么选择
### 【重点内容】
这里我要特别强调一个问题：

Python 并不是越新越好。

我们做 AI 开发的时候，真正重要的是：

**Python 版本、AI 框架、第三方依赖之间的兼容性。**

==所以学习阶段，我建议大家优先选择：==

```text
Python 3.11
Python 3.12
Python 3.13
```

如果你的环境已经是较新的稳定 Python 版本，也可以继续使用。

但是如果后面遇到某个 AI 框架或者第三方库暂时不兼容，我们优先考虑切换到课程统一版本。

---

## 六、04｜为什么建议使用 Python 3.13
### 【内容】
如果你现在是一台全新的电脑，准备专门搭建这套 AI 开发环境。

课程统一环境建议：

```text
Python 3.13
```

原因非常简单：

我们后面会使用大量：

```text
FastAPI
Pydantic
LangChain
LangGraph
DeepAgents
AI SDK
Vector Database
```

这些依赖非常多。

课程开发环境最重要的不是：

“一定使用最新版本。”

而是：

**大家尽可能保持环境一致。**

所以后面大家如果遇到：

```text
我的代码为什么和老师的不一样？
```

第一件事情就是检查：

```text
Python Version
```

---

## 七、05｜安装 Python
### Mac 用户
如果电脑没有 Python，可以使用官方安装方式。

安装完成之后执行：

```text
python3 --version
```

例如：

```text
Python 3.13.x
```

---

### Windows 用户
安装完成之后，在 PowerShell 执行：

```text
python --version
```

或者：

```text
py --version
```

---

## 八、06｜为什么我不建议直接使用系统 Python
### 【重点内容】
这里大家注意一个非常重要的问题。

==Python 和 Node.js 有一个非常明显的区别。==

如果你是前端开发者，你可能习惯：

```text
node
npm
pnpm
```

然后直接：

```text
npm install
```

但是 Python 项目千万不要养成：

```bash
pip install xxx
```

然后什么项目都往系统 Python 里面安装的习惯。

因为以后你会有：

```text
项目 A
Python 3.11
LangChain A 版本

项目 B
Python 3.12
LangChain B 版本

项目 C
Python 3.12
FastAPI
Pydantic
```

如果全部安装到系统环境里面，很快就会发生：

```text
依赖冲突
版本冲突
项目之间相互影响
```

所以我们需要：

## 虚拟环境
---

## 九、07｜什么是 Python 虚拟环境
### 【重点内容】
如果你是前端开发，可以把 Python 虚拟环境理解成：

```text
node_modules
```

当然，它们不是完全一样。

但是从工程使用习惯上，你可以先这么理解。

比如：

```text
项目 A
 ↓
独立 Python 环境
 ↓
FastAPI 0.x
```

项目 B：

```text
项目 B
 ↓
独立 Python 环境
 ↓
FastAPI 另一版本
```

两个项目互不影响。

所以：

```text
Python Project
       ↓
Virtual Environment
       ↓
Dependencies
```

这是 Python 开发非常重要的工程习惯。

---

## 十、08｜使用 Python 自带的 venv
### 【操作】
进入我们的项目：

```bash
cd ai-agent-course
```

创建虚拟环境：

Mac / Linux：

```bash
python3 -m venv .venv
```

Windows：

```bash
python -m venv .venv
```

执行完成之后：

```bash
ai-agent-course/
└── .venv/
```

---

## 十一、09｜激活虚拟环境
### Mac / Linux
执行：

```bash
source .venv/bin/activate
```

成功之后终端前面一般会出现：

```bash
(.venv)
```

例如：

```bash
(.venv) xxx@MacBook ai-agent-course %
```

---

### Windows PowerShell
执行：

```bash
.venv\Scripts\Activate.ps1
```

如果使用 CMD：

```bash
.venv\Scripts\activate.bat
```

成功之后：

```bash
(.venv)
```

---

## 十二、10｜检查虚拟环境是否生效
执行：

```text
python --version
```

然后：

```text
which python
```

Mac / Linux：

```text
which python
```

Windows：

```text
where python
```

---

### 【内容】
这里大家一定要注意。

如果看到的 Python 路径指向：

```bash
ai-agent-course/.venv/
```

说明当前项目已经使用自己的 Python 环境。

这就是我们想要的效果。

---

## 十三、11｜退出虚拟环境
### 【操作】
执行：

```text
deactivate
```

然后你会发现：

```bash
(.venv)
```

消失了。

重新进入：

```bash
source .venv/bin/activate
```

---

## 十四、12｜为什么课程还要介绍 uv
### 【重点内容】
到这里大家已经可以使用 Python 进行开发了。

但是我们再来看一个现在非常重要的工具：

## uv
如果你是前端开发，可以把 uv 理解成：

**Python 生态里面一个非常现代、高性能的项目和依赖管理工具。**

传统 Python 项目经常会看到：

```text
pip
venv
requirements.txt
```

而现在越来越多现代 Python 项目会使用：

```text
uv
pyproject.toml
uv.lock
```

这和 Node.js 的：

```text
package.json
package-lock.json
pnpm-lock.yaml
```

==在工程思路上有一定相似性。==

---

## 十五、13｜安装 uv
### Mac / Linux
可以使用官方安装方式安装。

安装完成后：

```bash
uv --version
```

例如：

```bash
uv 0.x.x
```

---

### Windows
安装完成后：

```bash
uv --version
```

如果能够看到版本号，就说明安装成功。

---

## 十六、14｜pip 和 uv 到底怎么选
### 【重点内容】
这里大家不要纠结：

“到底用 pip 还是 uv？”

这一章我把两个都讲清楚。

传统方式：

```text
python
 ↓
venv
 ↓
pip
 ↓
requirements.txt
```

现代项目方式：

```text
uv
 ↓
pyproject.toml
 ↓
uv.lock
```

如果你是在维护一个老项目：

```text
requirements.txt
```

那你需要会 pip。

如果是我们自己的新项目：

**课程后面优先使用 uv。**

这样大家以后接触现代 Python 项目，会更容易理解。

---

## 十七、15｜使用 uv 创建项目
如果已经安装 uv，可以直接执行：

```bash
uv init ai-agent-course
```

如果我们已经进入项目目录，也可以：

```bash
uv init
```

执行之后会生成类似：

```text
ai-agent-course/
├── .python-version
├── pyproject.toml
└── README.md
```

---

## 十八、16｜理解 pyproject.toml
打开：

```text
pyproject.toml
```

你会看到类似：

```toml
[project]
name = "ai-agent-course"
version = "0.1.0"
description = "AI Agent 全栈开发实战"
readme = "README.md"
requires-python = ">=3.12"
dependencies = []
```

---

## 【内容】
大家注意。

如果你是前端开发者，这个文件可以类比：

```text
package.json
```

它负责描述：

```text
项目名称
项目版本
Python 版本要求
项目依赖
```

后面我们安装：

```text
FastAPI
LangChain
LangGraph
```

这些依赖都会记录在这里。

---

## 十九、17｜创建 Python 虚拟环境
使用 uv：

```bash
uv venv
```

它会创建：

```bash
.venv/
```

然后激活：

Mac / Linux：

```bash
source .venv/bin/activate
```

Windows：

```bash
.venv\Scripts\Activate.ps1
```

---

## 二十、18｜安装 FastAPI
### 【操作】
执行：

```bash
uv add fastapi
```

然后安装 Uvicorn：

```bash
uv add "uvicorn[standard]"
```

---

## 【内容】
==这里我们已经开始接触 AI 后端开发的第一个核心框架：==

```text
FastAPI
```

FastAPI 后面会负责：

```text
HTTP API
接口
请求参数
响应
SSE
Middleware
认证
Swagger
```

而：

```text
Uvicorn
```

负责启动我们的 Python Web 服务。

可以简单理解成：

```text
FastAPI
=
Web Framework

Uvicorn
=
ASGI Server
```

---

## 二十一、19｜创建第一个 FastAPI 项目
创建：

```text
app/
```

创建：

```text
app/__init__.py
```

然后创建：

```text
app/main.py
```

代码：

```python
from fastapi import FastAPI

app = FastAPI(
    title="AI Agent Course",
    description="Python + FastAPI + LLM AI Agent 开发实战",
    version="0.1.0",
)


@app.get("/")
async def root():
    return {
        "message": "Hello AI Agent"
    }
```

---

## 二十二、20｜启动 FastAPI
执行：

```bash
uv run uvicorn app.main:app --reload
```

如果使用传统 pip / venv：

```text
uvicorn app.main:app --reload
```

看到：

```http
Uvicorn running on http://127.0.0.1:8000
```

说明服务启动成功。

---

## 二十三、21｜访问第一个 API
浏览器打开：

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

## 【重点内容】

> [!important] 重点标记
> 这一节是本章核心，建议慢读。

大家看一下。

我们现在已经完成了：

```text
Python
 ↓
FastAPI
 ↓
Uvicorn
 ↓
HTTP API
```

这其实就是后面整个 AI Agent 后端的基础。

现在我们只是：

```http
GET /
```

返回：

```json
{
    "message": "Hello AI Agent"
}
```

后面我们会逐渐变成：

```http
POST /chat
```

然后：

```text
用户问题
 ↓
FastAPI
 ↓
LLM
 ↓
AI 回答
```

再进一步：

```http
POST /agent
 ↓
Agent
 ↓
Tool
 ↓
RAG
 ↓
MCP
 ↓
最终回答
```

==所以现在这个 Hello World 虽然非常简单，但它是整个项目的起点。==

---

## 二十四、22｜FastAPI 自动生成 Swagger
打开：

```http
http://127.0.0.1:8000/docs
```

---

## 【内容】
这里大家一定要注意。

FastAPI 一个非常好用的能力就是：

**自动生成 API 文档。**

我们什么都没有额外配置。

只需要：

```python
@app.get("/")
```

FastAPI 就能够生成 OpenAPI 文档。

这对于企业级开发非常方便。

后面我们会看到：

```http
GET /health
POST /chat
POST /agent
POST /knowledge/upload
GET /knowledge/search
```

全部都会自动出现在这里。

---

## 二十五、23｜再创建一个接口
修改：

```text
app/main.py
```

代码：

```python
from fastapi import FastAPI

app = FastAPI(
    title="AI Agent Course",
    description="Python + FastAPI + LLM AI Agent 开发实战",
    version="0.1.0",
)


@app.get("/")
async def root():
    return {
        "message": "Hello AI Agent"
    }


@app.get("/health")
async def health():
    return {
        "status": "ok"
    }
```

---

## 二十六、24｜访问健康检查接口
打开：

```http
http://127.0.0.1:8000/health
```

返回：

```json
{
  "status": "ok"
}
```

---

## 【内容】
为什么企业项目经常需要：

```text
/health
```

这种接口？

因为后面我们部署到 Docker、Kubernetes 或云服务器之后，需要知道：

**服务现在是不是正常运行。**

所以我们可以通过：

```http
GET /health
```

快速判断：

```text
服务是否启动
服务是否可以访问
```

后面如果接入数据库，还可以进一步检查：

```text
Database
Redis
LLM
Vector Database
```

---

## 二十七、25｜创建项目配置文件
接下来我们把项目稍微工程化一点。

创建：

```text
.env
```

内容：

```text
APP_ENV=development
APP_NAME=AI Agent Course
```

创建：

```text
.env.example
```

内容：

```text
APP_ENV=development
APP_NAME=AI Agent Course
```

---

## 二十八、26｜为什么需要 .env
### 【内容】
后面我们的 AI Agent 项目会出现大量敏感配置。

例如：

```text
OPENAI_API_KEY=xxxx
DEEPSEEK_API_KEY=xxxx
QWEN_API_KEY=xxxx

DATABASE_URL=xxxx

REDIS_URL=xxxx
```

这些东西绝对不能直接写在代码里面。

错误：

```text
api_key = "sk-xxxxxxxx"
```

正确：

```text
.env
```

负责本地环境配置。

---

## 二十九、27｜配置 .gitignore
创建：

```text
.gitignore
```

内容：

```bash
# Python
__pycache__/
*.py[cod]
*.pyo

# Virtual Environment
.venv/

# Environment
.env

# IDE
.idea/
.vscode/

# OS
.DS_Store
Thumbs.db

# Test
.pytest_cache/

# Coverage
.coverage
htmlcov/

# Logs
*.log
```

---

## 【内容】
这里尤其要注意：

```text
.env
```

必须加入：

```text
.gitignore
```

因为后面：

```text
OPENAI_API_KEY
DEEPSEEK_API_KEY
```

这些都是敏感信息。

千万不要：

```text
git add .
git commit
git push
```

之后发现自己的 API Key 已经被提交到 GitHub。

---

## 三十、28｜创建 Git 仓库
执行：

```text
git init
```

然后：

```text
git status
```

---

## 三十一、29｜配置 README
README：

```text
# AI Agent 全栈开发实战

Python + FastAPI + LLM + LangChain + LangGraph + DeepAgents

## 当前阶段

第二章：Python AI 开发环境搭建

## 技术栈

- Python 3.12
- FastAPI
- Uvicorn
- uv

## 运行项目

```
uv sync
uv run uvicorn app.main:app --reload
```http

访问：

http://127.0.0.1:8000

Swagger：

http://127.0.0.1:8000/docs

```
---

## 三十二、30｜requirements.txt 方式

### 【内容】

前面我们使用的是：

```text
uv
pyproject.toml
```

但是大家以后工作的时候，还会大量遇到：

```text
requirements.txt
```

==所以我们也要知道它是什么。==

如果使用 pip，可以：

```bash
pip freeze > requirements.txt
```

然后得到：

```text
requirements.txt
```

例如：

```text
fastapi==...
uvicorn==...
```

以后别人拿到项目：

```bash
pip install -r requirements.txt
```

就可以安装项目依赖。

---

## 三十三、31｜requirements.txt 和 package.json 的对比
### 【实操】
JavaScript：

```javascript
package.json
package-lock.json
```

Python：

```python
requirements.txt
```

现代 Python：

```text
pyproject.toml
uv.lock
```

---

## 【内容】
如果你是前端开发者，可以简单建立这样的认知：

```text
package.json
≈
pyproject.toml
```

而：

```text
package-lock.json
pnpm-lock.yaml
≈
uv.lock
```

它们都是为了：

**保证项目依赖能够稳定复现。**

---

## 三十四、32｜VS Code 安装 Python 插件
### 【操作】
打开 VS Code。

进入：

```text
Extensions
```

搜索：

```text
Python
```

安装官方 Python 扩展。

---

## 三十五、33｜选择 Python Interpreter
### 【操作】
VS Code：

```text
Command + Shift + P
```

或者 Windows：

```text
Ctrl + Shift + P
```

输入：

```sql
Python: Select Interpreter
```

选择：

```bash
.venv
```

里面的 Python。

---

## 【内容】
这个步骤非常重要。

很多同学会遇到：

```text
终端可以运行
VS Code 报错
```

原因就是：

VS Code 使用的 Python 和终端不是同一个 Python。

所以大家看到：

```bash
.venv/bin/python
```

或者：

```bash
.venv\Scripts\python.exe
```

就说明 VS Code 已经使用项目自己的虚拟环境。

---

## 三十六、34｜在 VS Code 里面运行 Python
创建：

```text
app/test.py
```

代码：

```python
print("Hello Python")
```

运行：

```text
python app/test.py
```

输出：

```text
Hello Python
```

---

## 三十七、35｜Python 和 JavaScript 的第一次对比
### TypeScript
```json
function add(a: number, b: number): number {
  return a + b;
}

console.log(add(1, 2));
```

### Python
```python
def add(a: int, b: int) -> int:
    return a + b


print(add(1, 2))
```

输出：

```text
3
```

---

## 【内容】
大家看一下。

我们现在开始正式建立 Python 的语法认知。

TypeScript：

```typescript
function add()
```

Python：

```python
def add()
```

TypeScript：

```typescript
console.log()
```

Python：

```python
print()
```

但是：

**编程思想没有变化。**

==这就是为什么有开发经验的人学习 Python 会比较快。==

---

## 三十八、36｜Python 缩进问题第一次出现
创建：

```python
def hello():
    print("Hello")
```

注意：

```python
def hello():
    print("Hello")
```

而不是：

```python
def hello():
print("Hello")
```

---

## 【内容】
这里我要提前提醒大家一个 Python 非常重要的特点：

Python 使用缩进表达代码块。

JavaScript：

```javascript
if (true) {
  console.log("hello");
}
```

Python：

```python
if True:
    print("hello")
```

没有：

```text
{}
```

而是通过缩进表达代码结构。

所以以后大家看到：

```text
if
for
def
class
try
except
```

后面经常都会看到：

```text
:
```

然后下一行缩进。

这个概念后面我们会详细讲。

---

## 三十九、37｜创建第一个 AI 项目配置
现在把：

```text
app/main.py
```

升级一下：

```python
from fastapi import FastAPI

app = FastAPI(
    title="AI Agent 全栈开发实战",
    description="Python + FastAPI + LLM + Agent",
    version="0.1.0",
)


@app.get("/")
async def root():
    return {
        "message": "Hello AI Agent"
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "ai-agent-course",
    }
```

---

## 四十、38｜测试两个接口
启动：

```bash
uv run uvicorn app.main:app --reload
```

测试：

```http
GET /
```

结果：

```json
{
  "message": "Hello AI Agent"
}
```

测试：

```http
GET /health
```

结果：

```json
{
  "status": "ok",
  "service": "ai-agent-course"
}
```

---

## 四十一、39｜查看 Swagger
打开：

```http
http://127.0.0.1:8000/docs
```

可以看到：

```http
GET /
GET /health
```

点击：

```text
Try it out
```

然后：

```text
Execute
```

就可以直接测试接口。

---

## 四十二、40｜本章第一个完整项目结构
到这里：

```text
ai-agent-course/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   └── test.py
│
├── tests/
│
├── .env
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
└── uv.lock
```

---

## 四十三、41｜常见问题一：python 找不到
如果执行：

```text
python --version
```

出现：

```text
command not found
```

Mac 可以尝试：

```text
python3 --version
```

Windows 可以尝试：

```text
py --version
```

---

## 四十四、42｜常见问题二：pip 装了但是 Python 找不到
例如：

```bash
pip install fastapi
```

但是：

```text
python
```

运行的时候：

```text
ModuleNotFoundError
```

可以使用：

```bash
python -m pip install fastapi
```

或者：

```bash
python3 -m pip install fastapi
```

---

## 【内容】
为什么推荐：

```text
python -m pip
```

而不是直接：

```text
pip
```

因为：

```text
python
```

和：

```text
pip
```

可能不是同一个环境。

使用：

```text
python -m pip
```

可以明确告诉系统：

使用当前这个 Python 对应的 pip。

---

## 四十五、43｜常见问题三：PowerShell 无法激活虚拟环境
Windows 如果执行：

```bash
.venv\Scripts\Activate.ps1
```

出现执行策略问题。

可以检查：

```text
Get-ExecutionPolicy
```

如果你的公司电脑或者安全策略限制脚本执行，不要直接修改企业安全策略。

可以使用：

```text
cmd
```

然后：

```bash
.venv\Scripts\activate.bat
```

或者直接使用：

```bash
uv run
```

来执行项目命令。

---

## 四十六、44｜常见问题四：VS Code 使用了错误 Python
现象：

```text
终端可以运行
VS Code 报错
```

解决：

```text
Command + Shift + P
```

选择：

```sql
Python: Select Interpreter
```

选择：

```bash
.venv
```

---

## 四十七、45｜常见问题五：端口 8000 被占用
如果出现：

```text
Address already in use
```

说明：

```text
8000
```

端口已经被占用。

可以换端口：

```bash
uv run uvicorn app.main:app --reload --port 8001
```

然后访问：

```http
http://127.0.0.1:8001
```

Swagger：

```http
http://127.0.0.1:8001/docs
```

---

## 四十八、46｜常见问题六：忘记激活虚拟环境
如果：

```bash
(.venv)
```

没有出现。

不要慌。

直接：

Mac / Linux：

```bash
source .venv/bin/activate
```

Windows：

```bash
.venv\Scripts\Activate.ps1
```

或者使用：

```bash
uv run uvicorn app.main:app --reload
```

---

## 四十九、47｜为什么我们现在就开始接触工程化
### 【重点内容】
到这里可能有同学会觉得：

老师，我们不是刚开始学 Python 吗？

为什么已经讲：

```text
虚拟环境
uv
pyproject.toml
Git
.env
FastAPI
Swagger
```

其实原因很简单。

因为：

**我们不是在学 Python 语法。**

我们是在：

**学习如何使用 Python 开发 AI 应用。**

企业项目里面不会只有：

```text
hello.py
```

而是：

```text
Python
+
虚拟环境
+
依赖管理
+
FastAPI
+
数据库
+
Redis
+
LLM
+
Agent
+
Docker
```

==所以从第一天开始，我们就按照真实项目的方式开发。==

---

## 五十、48｜本章第一次完整回顾

> [!success] 复盘要点
> 复盘时重点看这一节。

现在我们回顾一下今天做了什么。

---

### 第一步：安装 Python
```text
Python 3.13
```

---

### 第二步：创建项目
```bash
mkdir ai-agent-course
cd ai-agent-course
```

---

### 第三步：创建虚拟环境
```bash
uv venv
```

---

### 第四步：激活虚拟环境
Mac：

```bash
source .venv/bin/activate
```

Windows：

```bash
.venv\Scripts\Activate.ps1
```

---

### 第五步：初始化项目
```bash
uv init
```

---

### 第六步：安装 FastAPI
```bash
uv add fastapi
```

---

### 第七步：安装 Uvicorn
```bash
uv add "uvicorn[standard]"
```

---

### 第八步：创建 FastAPI
```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    return {
        "message": "Hello AI Agent"
    }
```

---

### 第九步：启动
```bash
uv run uvicorn app.main:app --reload
```

---

### 第十步：访问
```http
http://127.0.0.1:8000
```

Swagger：

```http
http://127.0.0.1:8000/docs
```

---

## 五十一、49｜本章最终技术架构
现在我们已经有了：

```markdown
                  开发电脑
                     │
              ┌──────┴──────┐
              ↓             ↓
            VS Code       Terminal
              │             │
              └──────┬──────┘
                     ↓
                  Python
                     ↓
                 Virtual Env
                     ↓
                    uv
                     ↓
                 FastAPI
                     ↓
                 Uvicorn
                     ↓
                  HTTP API
```

下一章我们会继续往里面加入：

```text
LLM
```

最终变成：

```markdown
用户
 ↓
FastAPI
 ↓
Python
 ↓
LLM
 ↓
AI Response
```

---

## 五十二、50｜课后实操任务
这一章结束以后，不要直接进入下一章。

大家完成下面 5 个任务。

---

### 任务一：创建自己的项目
项目名称：

```text
ai-agent-course
```

---

### 任务二：创建虚拟环境
```bash
uv venv
```

---

### 任务三：安装 FastAPI
```bash
uv add fastapi
```

---

### 任务四：安装 Uvicorn
```bash
uv add "uvicorn[standard]"
```

---

### 任务五：完成两个接口
#### `/`
返回：

```json
{
  "message": "Hello AI Agent"
}
```

#### `/health`
返回：

```json
{
  "status": "ok"
}
```

---

## 五十三、51｜进阶任务
如果你已经完成上面的任务，可以继续完成：

```http
GET /info
```

返回：

```json
{
  "project": "AI Agent Course",
  "python": "3.12",
  "framework": "FastAPI",
  "stage": "environment"
}
```

然后访问：

```text
/docs
```

确保 Swagger 中出现：

```http
GET /
GET /health
GET /info
```

---



 

# 
---

> [!success] 一句话带走
> ==先把环境隔离干净，后面才不会踩依赖冲突的坑。==

> [!quote] 关于本文档
> 由原始讲义 `第 02 章｜Python AI 开发环境搭建.md` 转换为 Obsidian 风格笔记；原文完整保留，未做任何删改。
> 整理日期：2026-11-22
