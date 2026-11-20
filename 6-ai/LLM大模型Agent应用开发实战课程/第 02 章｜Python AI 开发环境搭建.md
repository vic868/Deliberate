---

# 一、本章学习目标
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

```plain
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

# 二、本章最终项目结构
这一章结束之后，我们会得到这样一个项目：

```plain
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

```plain
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

```plain
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

所以从这一章开始，这个项目就是我们整个课程的主项目。



# 三、01 为什么环境搭建非常重要
## 【重点内容】
大家好，欢迎来到第二章。

上一章我们已经讲清楚了：

为什么现在做 AI Agent，需要掌握 Python。

我们也把整门课程的技术路线梳理了一遍：

```plain
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

```plain
Python 版本不对
pip 装错环境
虚拟环境没有激活
VS Code 没选择正确解释器
依赖装到了系统 Python
Mac 和 Windows 命令不一样
```

最后代码明明没有问题，但是就是跑不起来。

所以这一章我会带着大家，从零开始把整个环境配置好。

而且我们不是只安装一个 Python。

我们会把：

```plain
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

# 四、02｜检查电脑当前有没有 Python
## 【实操】
打开终端。

Mac：

```plain
Command + Space
```

搜索：

```plain
Terminal
```

Windows：

打开：

```plain
PowerShell
```

或者：

```plain
Windows Terminal
```

---

## 【内容】
首先我们不要急着安装。

先检查一下自己的电脑有没有 Python。

执行：

```plain
python --version
```

如果没有，再执行：

```plain
python3 --version
```

也可以：

```plain
python3 -V
```

---

## 【预期结果】
例如：

```plain
Python 3.13.x
```

或者：

```plain
Python 3.13.x
```

---

# 五、03｜Python 版本怎么选择
## 【重点内容】
这里我要特别强调一个问题：

Python 并不是越新越好。

我们做 AI 开发的时候，真正重要的是：

**Python 版本、AI 框架、第三方依赖之间的兼容性。**

所以学习阶段，我建议大家优先选择：

```plain
Python 3.11
Python 3.12
Python 3.13
```

如果你的环境已经是较新的稳定 Python 版本，也可以继续使用。

但是如果后面遇到某个 AI 框架或者第三方库暂时不兼容，我们优先考虑切换到课程统一版本。

---

# 六、04｜为什么建议使用 Python 3.13
## 【内容】
如果你现在是一台全新的电脑，准备专门搭建这套 AI 开发环境。

课程统一环境建议：

```plain
Python 3.13
```

原因非常简单：

我们后面会使用大量：

```plain
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

```plain
我的代码为什么和老师的不一样？
```

第一件事情就是检查：

```plain
Python Version
```

---

# 七、05｜安装 Python
## Mac 用户
如果电脑没有 Python，可以使用官方安装方式。

安装完成之后执行：

```plain
python3 --version
```

例如：

```plain
Python 3.13.x
```

---

## Windows 用户
安装完成之后，在 PowerShell 执行：

```plain
python --version
```

或者：

```plain
py --version
```

---

# 八、06｜为什么我不建议直接使用系统 Python
## 【重点内容】
这里大家注意一个非常重要的问题。

Python 和 Node.js 有一个非常明显的区别。

如果你是前端开发者，你可能习惯：

```plain
node
npm
pnpm
```

然后直接：

```plain
npm install
```

但是 Python 项目千万不要养成：

```plain
pip install xxx
```

然后什么项目都往系统 Python 里面安装的习惯。

因为以后你会有：

```plain
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

```plain
依赖冲突
版本冲突
项目之间相互影响
```

所以我们需要：

# 虚拟环境
---

# 九、07｜什么是 Python 虚拟环境
## 【重点内容】
如果你是前端开发，可以把 Python 虚拟环境理解成：

```plain
node_modules
```

当然，它们不是完全一样。

但是从工程使用习惯上，你可以先这么理解。

比如：

```plain
项目 A
 ↓
独立 Python 环境
 ↓
FastAPI 0.x
```

项目 B：

```plain
项目 B
 ↓
独立 Python 环境
 ↓
FastAPI 另一版本
```

两个项目互不影响。

所以：

```plain
Python Project
       ↓
Virtual Environment
       ↓
Dependencies
```

这是 Python 开发非常重要的工程习惯。

---

# 十、08｜使用 Python 自带的 venv
## 【操作】
进入我们的项目：

```plain
cd ai-agent-course
```

创建虚拟环境：

Mac / Linux：

```plain
python3 -m venv .venv
```

Windows：

```plain
python -m venv .venv
```

执行完成之后：

```plain
ai-agent-course/
└── .venv/
```

---

# 十一、09｜激活虚拟环境
## Mac / Linux
执行：

```plain
source .venv/bin/activate
```

成功之后终端前面一般会出现：

```plain
(.venv)
```

例如：

```plain
(.venv) xxx@MacBook ai-agent-course %
```

---

## Windows PowerShell
执行：

```plain
.venv\Scripts\Activate.ps1
```

如果使用 CMD：

```plain
.venv\Scripts\activate.bat
```

成功之后：

```plain
(.venv)
```

---

# 十二、10｜检查虚拟环境是否生效
执行：

```plain
python --version
```

然后：

```plain
which python
```

Mac / Linux：

```plain
which python
```

Windows：

```plain
where python
```

---

## 【内容】
这里大家一定要注意。

如果看到的 Python 路径指向：

```plain
ai-agent-course/.venv/
```

说明当前项目已经使用自己的 Python 环境。

这就是我们想要的效果。

---

# 十三、11｜退出虚拟环境
## 【操作】
执行：

```plain
deactivate
```

然后你会发现：

```plain
(.venv)
```

消失了。

重新进入：

```plain
source .venv/bin/activate
```

---

# 十四、12｜为什么课程还要介绍 uv
## 【重点内容】
到这里大家已经可以使用 Python 进行开发了。

但是我们再来看一个现在非常重要的工具：

# uv
如果你是前端开发，可以把 uv 理解成：

**Python 生态里面一个非常现代、高性能的项目和依赖管理工具。**

传统 Python 项目经常会看到：

```plain
pip
venv
requirements.txt
```

而现在越来越多现代 Python 项目会使用：

```plain
uv
pyproject.toml
uv.lock
```

这和 Node.js 的：

```plain
package.json
package-lock.json
pnpm-lock.yaml
```

在工程思路上有一定相似性。

---

# 十五、13｜安装 uv
## Mac / Linux
可以使用官方安装方式安装。

安装完成后：

```plain
uv --version
```

例如：

```plain
uv 0.x.x
```

---

## Windows
安装完成后：

```plain
uv --version
```

如果能够看到版本号，就说明安装成功。

---

# 十六、14｜pip 和 uv 到底怎么选
## 【重点内容】
这里大家不要纠结：

“到底用 pip 还是 uv？”

这一章我把两个都讲清楚。

传统方式：

```plain
python
 ↓
venv
 ↓
pip
 ↓
requirements.txt
```

现代项目方式：

```plain
uv
 ↓
pyproject.toml
 ↓
uv.lock
```

如果你是在维护一个老项目：

```plain
requirements.txt
```

那你需要会 pip。

如果是我们自己的新项目：

**课程后面优先使用 uv。**

这样大家以后接触现代 Python 项目，会更容易理解。

---

# 十七、15｜使用 uv 创建项目
如果已经安装 uv，可以直接执行：

```plain
uv init ai-agent-course
```

如果我们已经进入项目目录，也可以：

```plain
uv init
```

执行之后会生成类似：

```plain
ai-agent-course/
├── .python-version
├── pyproject.toml
└── README.md
```

---

# 十八、16｜理解 pyproject.toml
打开：

```plain
pyproject.toml
```

你会看到类似：

```plain
[project]
name = "ai-agent-course"
version = "0.1.0"
description = "AI Agent 全栈开发实战"
readme = "README.md"
requires-python = ">=3.12"
dependencies = []
```

---

# 【内容】
大家注意。

如果你是前端开发者，这个文件可以类比：

```plain
package.json
```

它负责描述：

```plain
项目名称
项目版本
Python 版本要求
项目依赖
```

后面我们安装：

```plain
FastAPI
LangChain
LangGraph
```

这些依赖都会记录在这里。

---

# 十九、17｜创建 Python 虚拟环境
使用 uv：

```plain
uv venv
```

它会创建：

```plain
.venv/
```

然后激活：

Mac / Linux：

```plain
source .venv/bin/activate
```

Windows：

```plain
.venv\Scripts\Activate.ps1
```

---

# 二十、18｜安装 FastAPI
## 【操作】
执行：

```plain
uv add fastapi
```

然后安装 Uvicorn：

```plain
uv add "uvicorn[standard]"
```

---

# 【内容】
这里我们已经开始接触 AI 后端开发的第一个核心框架：

```plain
FastAPI
```

FastAPI 后面会负责：

```plain
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

```plain
Uvicorn
```

负责启动我们的 Python Web 服务。

可以简单理解成：

```plain
FastAPI
=
Web Framework

Uvicorn
=
ASGI Server
```

---

# 二十一、19｜创建第一个 FastAPI 项目
创建：

```plain
app/
```

创建：

```plain
app/__init__.py
```

然后创建：

```plain
app/main.py
```

代码：

```plain
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

# 二十二、20｜启动 FastAPI
执行：

```plain
uv run uvicorn app.main:app --reload
```

如果使用传统 pip / venv：

```plain
uvicorn app.main:app --reload
```

看到：

```plain
Uvicorn running on http://127.0.0.1:8000
```

说明服务启动成功。

---

# 二十三、21｜访问第一个 API
浏览器打开：

```plain
http://127.0.0.1:8000
```

返回：

```plain
{
  "message": "Hello AI Agent"
}
```

---

# 【重点内容】
大家看一下。

我们现在已经完成了：

```plain
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

```plain
GET /
```

返回：

```plain
{
    "message": "Hello AI Agent"
}
```

后面我们会逐渐变成：

```plain
POST /chat
```

然后：

```plain
用户问题
 ↓
FastAPI
 ↓
LLM
 ↓
AI 回答
```

再进一步：

```plain
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

所以现在这个 Hello World 虽然非常简单，但它是整个项目的起点。

---

# 二十四、22｜FastAPI 自动生成 Swagger
打开：

```plain
http://127.0.0.1:8000/docs
```

---

# 【内容】
这里大家一定要注意。

FastAPI 一个非常好用的能力就是：

**自动生成 API 文档。**

我们什么都没有额外配置。

只需要：

```plain
@app.get("/")
```

FastAPI 就能够生成 OpenAPI 文档。

这对于企业级开发非常方便。

后面我们会看到：

```plain
GET /health
POST /chat
POST /agent
POST /knowledge/upload
GET /knowledge/search
```

全部都会自动出现在这里。

---

# 二十五、23｜再创建一个接口
修改：

```plain
app/main.py
```

代码：

```plain
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

# 二十六、24｜访问健康检查接口
打开：

```plain
http://127.0.0.1:8000/health
```

返回：

```plain
{
  "status": "ok"
}
```

---

# 【内容】
为什么企业项目经常需要：

```plain
/health
```

这种接口？

因为后面我们部署到 Docker、Kubernetes 或云服务器之后，需要知道：

**服务现在是不是正常运行。**

所以我们可以通过：

```plain
GET /health
```

快速判断：

```plain
服务是否启动
服务是否可以访问
```

后面如果接入数据库，还可以进一步检查：

```plain
Database
Redis
LLM
Vector Database
```

---

# 二十七、25｜创建项目配置文件
接下来我们把项目稍微工程化一点。

创建：

```plain
.env
```

内容：

```plain
APP_ENV=development
APP_NAME=AI Agent Course
```

创建：

```plain
.env.example
```

内容：

```plain
APP_ENV=development
APP_NAME=AI Agent Course
```

---

# 二十八、26｜为什么需要 .env
## 【内容】
后面我们的 AI Agent 项目会出现大量敏感配置。

例如：

```plain
OPENAI_API_KEY=xxxx
DEEPSEEK_API_KEY=xxxx
QWEN_API_KEY=xxxx

DATABASE_URL=xxxx

REDIS_URL=xxxx
```

这些东西绝对不能直接写在代码里面。

错误：

```plain
api_key = "sk-xxxxxxxx"
```

正确：

```plain
.env
```

负责本地环境配置。

---

# 二十九、27｜配置 .gitignore
创建：

```plain
.gitignore
```

内容：

```plain
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

# 【内容】
这里尤其要注意：

```plain
.env
```

必须加入：

```plain
.gitignore
```

因为后面：

```plain
OPENAI_API_KEY
DEEPSEEK_API_KEY
```

这些都是敏感信息。

千万不要：

```plain
git add .
git commit
git push
```

之后发现自己的 API Key 已经被提交到 GitHub。

---

# 三十、28｜创建 Git 仓库
执行：

```plain
git init
```

然后：

```plain
git status
```

---

# 三十一、29｜配置 README
README：

```plain
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

```bash
uv sync
uv run uvicorn app.main:app --reload
```

访问：

http://127.0.0.1:8000

Swagger：

http://127.0.0.1:8000/docs

```plain
---

# 三十二、30｜requirements.txt 方式

## 【内容】

前面我们使用的是：

```text
uv
pyproject.toml
```

但是大家以后工作的时候，还会大量遇到：

```plain
requirements.txt
```

所以我们也要知道它是什么。

如果使用 pip，可以：

```plain
pip freeze > requirements.txt
```

然后得到：

```plain
requirements.txt
```

例如：

```plain
fastapi==...
uvicorn==...
```

以后别人拿到项目：

```plain
pip install -r requirements.txt
```

就可以安装项目依赖。

---

# 三十三、31｜requirements.txt 和 package.json 的对比
## 【实操】
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

```plain
pyproject.toml
uv.lock
```

---

# 【内容】
如果你是前端开发者，可以简单建立这样的认知：

```plain
package.json
≈
pyproject.toml
```

而：

```plain
package-lock.json
pnpm-lock.yaml
≈
uv.lock
```

它们都是为了：

**保证项目依赖能够稳定复现。**

---

# 三十四、32｜VS Code 安装 Python 插件
## 【操作】
打开 VS Code。

进入：

```plain
Extensions
```

搜索：

```plain
Python
```

安装官方 Python 扩展。

---

# 三十五、33｜选择 Python Interpreter
## 【操作】
VS Code：

```plain
Command + Shift + P
```

或者 Windows：

```plain
Ctrl + Shift + P
```

输入：

```plain
Python: Select Interpreter
```

选择：

```plain
.venv
```

里面的 Python。

---

# 【内容】
这个步骤非常重要。

很多同学会遇到：

```plain
终端可以运行
VS Code 报错
```

原因就是：

VS Code 使用的 Python 和终端不是同一个 Python。

所以大家看到：

```plain
.venv/bin/python
```

或者：

```plain
.venv\Scripts\python.exe
```

就说明 VS Code 已经使用项目自己的虚拟环境。

---

# 三十六、34｜在 VS Code 里面运行 Python
创建：

```plain
app/test.py
```

代码：

```plain
print("Hello Python")
```

运行：

```plain
python app/test.py
```

输出：

```plain
Hello Python
```

---

# 三十七、35｜Python 和 JavaScript 的第一次对比
## TypeScript
```plain
function add(a: number, b: number): number {
  return a + b;
}

console.log(add(1, 2));
```

## Python
```plain
def add(a: int, b: int) -> int:
    return a + b


print(add(1, 2))
```

输出：

```plain
3
```

---

# 【内容】
大家看一下。

我们现在开始正式建立 Python 的语法认知。

TypeScript：

```plain
function add()
```

Python：

```plain
def add()
```

TypeScript：

```plain
console.log()
```

Python：

```plain
print()
```

但是：

**编程思想没有变化。**

这就是为什么有开发经验的人学习 Python 会比较快。

---

# 三十八、36｜Python 缩进问题第一次出现
创建：

```plain
def hello():
    print("Hello")
```

注意：

```plain
def hello():
    print("Hello")
```

而不是：

```plain
def hello():
print("Hello")
```

---

# 【内容】
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

```plain
{}
```

而是通过缩进表达代码结构。

所以以后大家看到：

```plain
if
for
def
class
try
except
```

后面经常都会看到：

```plain
:
```

然后下一行缩进。

这个概念后面我们会详细讲。

---

# 三十九、37｜创建第一个 AI 项目配置
现在把：

```plain
app/main.py
```

升级一下：

```plain
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

# 四十、38｜测试两个接口
启动：

```plain
uv run uvicorn app.main:app --reload
```

测试：

```plain
GET /
```

结果：

```plain
{
  "message": "Hello AI Agent"
}
```

测试：

```plain
GET /health
```

结果：

```plain
{
  "status": "ok",
  "service": "ai-agent-course"
}
```

---

# 四十一、39｜查看 Swagger
打开：

```plain
http://127.0.0.1:8000/docs
```

可以看到：

```plain
GET /
GET /health
```

点击：

```plain
Try it out
```

然后：

```plain
Execute
```

就可以直接测试接口。

---

# 四十二、40｜本章第一个完整项目结构
到这里：

```plain
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

# 四十三、41｜常见问题一：python 找不到
如果执行：

```plain
python --version
```

出现：

```plain
command not found
```

Mac 可以尝试：

```plain
python3 --version
```

Windows 可以尝试：

```plain
py --version
```

---

# 四十四、42｜常见问题二：pip 装了但是 Python 找不到
例如：

```plain
pip install fastapi
```

但是：

```plain
python
```

运行的时候：

```plain
ModuleNotFoundError
```

可以使用：

```plain
python -m pip install fastapi
```

或者：

```plain
python3 -m pip install fastapi
```

---

# 【内容】
为什么推荐：

```plain
python -m pip
```

而不是直接：

```plain
pip
```

因为：

```plain
python
```

和：

```plain
pip
```

可能不是同一个环境。

使用：

```plain
python -m pip
```

可以明确告诉系统：

使用当前这个 Python 对应的 pip。

---

# 四十五、43｜常见问题三：PowerShell 无法激活虚拟环境
Windows 如果执行：

```plain
.venv\Scripts\Activate.ps1
```

出现执行策略问题。

可以检查：

```plain
Get-ExecutionPolicy
```

如果你的公司电脑或者安全策略限制脚本执行，不要直接修改企业安全策略。

可以使用：

```plain
cmd
```

然后：

```plain
.venv\Scripts\activate.bat
```

或者直接使用：

```plain
uv run
```

来执行项目命令。

---

# 四十六、44｜常见问题四：VS Code 使用了错误 Python
现象：

```plain
终端可以运行
VS Code 报错
```

解决：

```plain
Command + Shift + P
```

选择：

```plain
Python: Select Interpreter
```

选择：

```plain
.venv
```

---

# 四十七、45｜常见问题五：端口 8000 被占用
如果出现：

```plain
Address already in use
```

说明：

```plain
8000
```

端口已经被占用。

可以换端口：

```plain
uv run uvicorn app.main:app --reload --port 8001
```

然后访问：

```plain
http://127.0.0.1:8001
```

Swagger：

```plain
http://127.0.0.1:8001/docs
```

---

# 四十八、46｜常见问题六：忘记激活虚拟环境
如果：

```plain
(.venv)
```

没有出现。

不要慌。

直接：

Mac / Linux：

```plain
source .venv/bin/activate
```

Windows：

```plain
.venv\Scripts\Activate.ps1
```

或者使用：

```plain
uv run uvicorn app.main:app --reload
```

---

# 四十九、47｜为什么我们现在就开始接触工程化
## 【重点内容】
到这里可能有同学会觉得：

老师，我们不是刚开始学 Python 吗？

为什么已经讲：

```plain
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

```plain
hello.py
```

而是：

```plain
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

所以从第一天开始，我们就按照真实项目的方式开发。

---

# 五十、48｜本章第一次完整回顾
现在我们回顾一下今天做了什么。

---

## 第一步：安装 Python
```plain
Python 3.13
```

---

## 第二步：创建项目
```plain
mkdir ai-agent-course
cd ai-agent-course
```

---

## 第三步：创建虚拟环境
```plain
uv venv
```

---

## 第四步：激活虚拟环境
Mac：

```plain
source .venv/bin/activate
```

Windows：

```plain
.venv\Scripts\Activate.ps1
```

---

## 第五步：初始化项目
```plain
uv init
```

---

## 第六步：安装 FastAPI
```plain
uv add fastapi
```

---

## 第七步：安装 Uvicorn
```plain
uv add "uvicorn[standard]"
```

---

## 第八步：创建 FastAPI
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

## 第九步：启动
```plain
uv run uvicorn app.main:app --reload
```

---

## 第十步：访问
```plain
http://127.0.0.1:8000
```

Swagger：

```plain
http://127.0.0.1:8000/docs
```

---

# 五十一、49｜本章最终技术架构
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

```plain
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

# 五十二、50｜课后实操任务
这一章结束以后，不要直接进入下一章。

大家完成下面 5 个任务。

---

## 任务一：创建自己的项目
项目名称：

```plain
ai-agent-course
```

---

## 任务二：创建虚拟环境
```plain
uv venv
```

---

## 任务三：安装 FastAPI
```plain
uv add fastapi
```

---

## 任务四：安装 Uvicorn
```plain
uv add "uvicorn[standard]"
```

---

## 任务五：完成两个接口
### `/`
返回：

```plain
{
  "message": "Hello AI Agent"
}
```

### `/health`
返回：

```plain
{
  "status": "ok"
}
```

---

# 五十三、51｜进阶任务
如果你已经完成上面的任务，可以继续完成：

```plain
GET /info
```

返回：

```plain
{
  "project": "AI Agent Course",
  "python": "3.12",
  "framework": "FastAPI",
  "stage": "environment"
}
```

然后访问：

```plain
/docs
```

确保 Swagger 中出现：

```plain
GET /
GET /health
GET /info
```

---



 

# 