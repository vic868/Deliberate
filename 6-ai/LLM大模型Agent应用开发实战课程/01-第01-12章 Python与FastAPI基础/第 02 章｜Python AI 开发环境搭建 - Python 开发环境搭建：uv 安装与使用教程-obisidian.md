---
title: "第 02 章补充｜uv 安装与使用教程"
chapter: "02"
source: "第 02 章｜Python AI 开发环境搭建 - Python 开发环境搭建：uv 安装与使用教程.md"
type: obsidian-note
created: 2026-11-22
status: 整理中
tags:
  - course/llm-agent
  - python
  - uv
  - 环境搭建
---

# 第 02 章补充｜uv 安装与使用教程

> [!abstract] 本章重点
>
> - ==uv 一条命令管 Python 版本和依赖== — 以前要 pip、pyenv、virtualenv 好几个工具，现在一个 uv 就够。
> - ==装完找不到命令，先查 PATH== — command not found 多半不是没装好，而是终端没找到可执行文件。
> - ==pyproject.toml 相当于 package.json== — 项目名、依赖、Python 版本都写在这一个文件里。
> - ==macOS 用官方脚本，Windows 用 WinGet== — 不同系统装法不同，按对应步骤走最省事。
>
> [!note] 大白话
>
> - **PATH**：系统找命令时翻的通讯录，没登记就喊不到人。
> - **uv**：用 Rust 写的超快 Python 包与环境管理器。
>
> [!info] 导航与来源
> - 原始讲义：[[第 02 章｜Python AI 开发环境搭建 - Python 开发环境搭建：uv 安装与使用教程|打开原始讲义]]
> - [[第 01 章：为什么 Python 是 AI Agent 开发的核心语言|上一章｜第 01 章]]
> - [[第 03 章｜Python AI 开发快速入门|下一章｜第 03 章]]
> - 本章所有内容均保留，未删改原文。

## 本章导航

- [[#2. 为什么推荐使用 uv？]]
- [[#3. Windows 安装 uv]]
- [[#4. Windows 验证 uv 是否安装成功]]
- [[#5. Windows 出现 uv 找不到命令]]
- [[#6. Windows 查看 uv 安装位置]]
- [[#7. Windows 配置 PATH 环境变量]]
- [[#8. Windows 使用 WinGet 安装 uv]]
- [[#9. macOS 安装 uv]]
- [[#10. macOS 验证安装]]
- [[#11. macOS 出现 command not found: uv]]
- [[#12. macOS 第一种解决办法：重启 Terminal]]
- [[#13. macOS 第二种解决办法：重新加载 Shell]]
- [[#14. 查看 uv 是否已经安装]]
- [[#15. macOS 手动配置 PATH]]

---
### 1. uv 是什么？
在正式学习 Python 之前，我们先把 Python 的开发环境搭建好。

这套课程推荐大家使用 **uv** 来管理 Python。

uv 是 Astral 团队开发的一款 Python 包管理和项目管理工具，可以把它理解成 Python 生态里的：

```latex
Node.js 生态：

nvm + npm + yarn/pnpm
       ↓
      uv
       ↑
Python 生态
```

以前使用 Python，经常需要同时接触：

```latex
Python
pip
pip3
venv
virtualenv
pyenv
poetry
requirements.txt
```

对于刚从前端或者 Java 转 Python 的同学来说，会比较混乱。

而现在使用 uv，很多事情一个工具就可以完成：

```latex
安装 Python
管理 Python 版本
创建虚拟环境
安装第三方依赖
管理项目依赖
运行 Python 程序
生成 lock 文件
同步项目环境
```

因此这套课程统一推荐：

```latex
uv + Python
```

---

## 2. 为什么推荐使用 uv？
比如传统 Python 项目安装 FastAPI：

```bash
pip install fastapi
```

使用 uv：

```bash
uv add fastapi
```

运行 Python：

```bash
python main.py
```

使用 uv：

```bash
uv run main.py
```

安装指定 Python：

```bash
uv python install 3.12
```

初始化项目：

```bash
uv init
```

安装项目全部依赖：

```bash
uv sync
```

所以后面做：

```latex
FastAPI
LangChain
LangGraph
RAG
Agent
MCP
AI Agent
```

都可以统一使用 uv 管理环境。

---

## 3. Windows 安装 uv
下面先讲 Windows 系统。

---

### 3.1 打开 PowerShell
在 Windows 搜索框输入：

```latex
PowerShell
```

打开：

```latex
Windows PowerShell
```

或者：

```latex
Terminal
```

都可以。

==建议直接使用 PowerShell。==

---

### 3.2 使用官方命令安装 uv
在 PowerShell 中执行：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

等待安装完成。

正常情况下会看到类似：

```latex
Downloading uv
Installing uv
uv installed successfully
```

---

## 4. Windows 验证 uv 是否安装成功
安装完成以后执行：

```bash
uv --version
```

例如：

```latex
uv 0.x.x
```

只要能够看到版本号，就说明安装成功。

---

## 5. Windows 出现 uv 找不到命令
有些同学安装完成以后执行：

```bash
uv --version
```

可能出现：

```latex
uv : 无法将“uv”项识别为 cmdlet、函数、脚本文件或可运行程序的名称
```

或者：

```latex
'uv' is not recognized as an internal or external command
```

本质上就是：

```latex
系统没有找到 uv
```

通常是 PATH 环境变量没有刷新。

---

### 5.1 第一种解决办法：重新打开终端
这是最常见的情况。

安装完 uv 后：

```latex
关闭 PowerShell
```

重新打开一个 PowerShell。

然后执行：

```bash
uv --version
```

很多时候就可以了。

---

## 6. Windows 查看 uv 安装位置
可以执行：

```powershell
where.exe uv
```

如果安装正常，会看到类似：

```latex
C:\Users\你的用户名\.local\bin\uv.exe
```

uv 默认情况下通常会安装到用户目录。

类似：

```latex
C:\Users\username\.local\bin
```

---

## 7. Windows 配置 PATH 环境变量
如果还是执行不了：

```bash
uv --version
```

可以手动检查环境变量。

搜索：

```latex
编辑系统环境变量
```

打开：

```latex
环境变量
```

找到用户变量中的：

```latex
Path
```

点击：

```latex
编辑
```

查看是否包含：

```latex
C:\Users\你的用户名\.local\bin
```

如果没有，就手动添加。

例如：

```latex
C:\Users\zhangsan\.local\bin
```

保存以后：

```latex
关闭 PowerShell
重新打开 PowerShell
```

再次执行：

```bash
uv --version
```

---

## 8. Windows 使用 WinGet 安装 uv
如果官方安装脚本因为网络等问题无法使用，也可以尝试 WinGet。

执行：

```powershell
winget install --id=astral-sh.uv -e
```

安装完成：

```bash
uv --version
```

---

## 9. macOS 安装 uv
下面来看 macOS。

==macOS 推荐直接使用官方安装脚本。==

打开：

```latex
Terminal
```

或者：

```latex
iTerm2
```

执行：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

等待安装完成。

---

## 10. macOS 验证安装
执行：

```bash
uv --version
```

如果出现类似：

```latex
uv 0.x.x
```

说明安装成功。

---

## 11. macOS 出现 command not found: uv
如果安装完成以后执行：

```bash
uv --version
```

出现：

```latex
zsh: command not found: uv
```

这是非常常见的问题。

==并不一定代表 uv 没有安装成功。==

通常是因为：

```latex
PATH 环境变量还没有生效
```

---

## 12. macOS 第一种解决办法：重启 Terminal
先执行最简单的方法：

```latex
关闭 Terminal
重新打开 Terminal
```

然后执行：

```bash
uv --version
```

---

## 13. macOS 第二种解决办法：重新加载 Shell
如果使用 zsh：

```bash
source ~/.zshrc
```

然后：

```bash
uv --version
```

---

## 14. 查看 uv 是否已经安装
执行：

```bash
ls ~/.local/bin
```

如果能够看到：

```latex
uv
uvx
```

说明 uv 已经安装成功，只是 PATH 没有配置。

---

## 15. macOS 手动配置 PATH
编辑：

```bash
~/.zshrc
```

可以执行：

```bash
nano ~/.zshrc
```

在文件最后增加：

```bash
export PATH="$HOME/.local/bin:$PATH"
```

保存。

然后执行：

```bash
source ~/.zshrc
```

再次验证：

```bash
uv --version
```

---

## 16. macOS 使用 Homebrew 安装 uv
如果电脑已经安装 Homebrew，也可以直接：

```bash
brew install uv
```

安装完成以后：

```bash
uv --version
```

---

## 17. 检查当前是否安装 Python
uv 安装完成以后，我们继续安装 Python。

先执行：

```bash
python --version
```

或者：

```bash
python3 --version
```

例如：

```latex
Python 3.12.x
```

如果电脑没有 Python，也没有关系。

uv 可以直接帮我们安装。

---

## 18. 使用 uv 安装 Python
例如安装 Python 3.12：

```bash
uv python install 3.12
```

然后查看：

```bash
uv python list
```

会看到当前电脑里面可用的 Python 版本。

---

## 19. 为什么推荐 Python 3.1x？
==目前学习 AI 应用开发，我通常建议课程统一：==

```latex
Python 3.12
```

不要让每个学员自己随便安装版本。

统一版本可以减少大量环境问题。

例如课程统一：

```latex
uv
Python 3.12
```

后面学习：

```latex
FastAPI
Pydantic
LangChain
LangGraph
RAG
MCP
Agent
```

环境都会比较统一。

---

## 20. 创建第一个 Python 项目
创建一个目录：

```bash
mkdir python-demo
```

进入目录：

```bash
cd python-demo
```

初始化项目：

```bash
uv init
```

完成以后目录可能类似：

```latex
python-demo
├── .python-version
├── README.md
├── main.py
└── pyproject.toml
```

其中最重要的是：

```latex
pyproject.toml
```

---

## 21. pyproject.toml 是什么？
如果你是前端开发，可以这样理解：

```latex
Node.js                  Python

package.json       →     pyproject.toml

package-lock.json  →     uv.lock

node_modules       →     .venv
```

这个对比非常重要。

前端同学一下就能理解。

---

## 22. Node.js 和 Python 项目对比
| Node.js | Python + uv |
| --- | --- |
| `package.json` | `pyproject.toml` |
| `package-lock.json` | `uv.lock` |
| `node_modules` | `.venv` |
| `npm install` | `uv sync` |
| `npm install axios` | `uv add httpx` |
| `npm uninstall axios` | `uv remove httpx` |
| `npm run dev` | `uv run xxx` |
| `nvm` | `uv python` |
| `npm` / `pnpm` | `uv` |


==所以对于前端同学来说，可以把：==

```latex
uv
```

简单理解为：

```latex
nvm + npm + pnpm + venv
```

这一类能力的组合。

---

## 23. 运行第一个 Python 程序
打开：

```latex
main.py
```

写：

```python
print("Hello Python")
```

运行：

```bash
uv run main.py
```

输出：

```latex
Hello Python
```

这样第一个 Python 程序就跑起来了。

---

## 24. 使用 uv 创建虚拟环境
执行：

```bash
uv venv
```

项目下面会出现：

```latex
.venv
```

类似：

```latex
python-demo
├── .venv
├── main.py
├── pyproject.toml
└── uv.lock
```

---

## 25. 什么是 Python 虚拟环境？
==这个概念初学者必须理解。==

假设电脑里面同时有两个项目：

```latex
项目 A
FastAPI 0.100

项目 B
FastAPI 0.120
```

如果所有依赖全部装在全局 Python 环境，很容易发生版本冲突。

所以 Python 项目一般会：

```latex
每一个项目
↓
拥有自己的 Python 环境
↓
拥有自己的第三方依赖
```

这个独立环境就是：

```latex
virtual environment
```

也就是：

```latex
虚拟环境
```

uv 默认通常使用：

```latex
.venv
```

---

## 26. Windows 激活虚拟环境
Windows PowerShell：

```powershell
.venv\Scripts\Activate.ps1
```

如果成功，终端前面通常会看到：

```latex
(.venv)
```

例如：

```latex
(.venv) PS C:\code\python-demo>
```

---

## 27. macOS 激活虚拟环境
执行：

```bash
source .venv/bin/activate
```

成功以后：

```latex
(.venv)
```

例如：

```latex
(.venv) zhangsan@MacBook python-demo %
```

---

## 28. 是否必须手动激活虚拟环境？
如果使用 uv：

很多情况下：

```latex
不需要手动 activate
```

直接：

```bash
uv run main.py
```

uv 会自动使用当前项目对应的环境。

因此课程里推荐：

```bash
uv run main.py
```

而不是让初学者天天研究：

```latex
activate
deactivate
PATH
Python interpreter
```

这样会简单很多。

---

## 29. 使用 uv 安装第三方依赖
比如安装 requests：

```bash
uv add requests
```

安装完成以后，可以在：

```latex
pyproject.toml
```

里面看到依赖。

例如：

```toml
[project]
dependencies = [
    "requests>=2.x.x"
]
```

同时还会生成：

```latex
uv.lock
```

---

## 30. 安装 FastAPI
例如：

```bash
uv add fastapi
```

再安装 uvicorn：

```bash
uv add uvicorn
```

也可以一次安装：

```bash
uv add fastapi uvicorn
```

---

## 31. 创建第一个 FastAPI 项目
main.py：

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def hello():
    return {
        "message": "Hello AI Agent"
    }
```

运行：

```bash
uv run uvicorn main:app --reload
```

启动以后访问：

```latex
http://127.0.0.1:8000
```

可以看到：

```json
{
  "message": "Hello AI Agent"
}
```

Swagger 文档地址：

```latex
http://127.0.0.1:8000/docs
```

---

## 32. 安装开发环境依赖
比如安装 pytest：

```bash
uv add --dev pytest
```

这种依赖只在开发阶段使用。

例如：

```latex
pytest
ruff
mypy
```

可以作为开发依赖。

---

## 33. 删除依赖
例如删除：

```latex
requests
```

执行：

```bash
uv remove requests
```

类似前端：

```bash
npm uninstall axios
```

---

## 34. 查看项目依赖
可以查看：

```latex
pyproject.toml
```

例如：

```toml
[project]
name = "python-demo"
version = "0.1.0"
description = "Python demo"
requires-python = ">=3.12"
dependencies = [
    "fastapi",
    "uvicorn",
]
```

---

## 35. uv sync 是什么？
假设你从 GitHub 下载了一个项目：

```bash
git clone xxx
```

进入：

```bash
cd project
```

不需要一个个安装依赖。

直接：

```bash
uv sync
```

uv 会读取：

```latex
pyproject.toml
uv.lock
```

自动创建环境并安装依赖。

可以类比前端：

```bash
npm install
```

或者：

```bash
pnpm install
```

---

## 36. 团队开发为什么需要 uv.lock？
比如：

```latex
张三
李四
王五
```

三个人一起开发。

如果每个人安装的第三方包版本不同，就可能出现：

```latex
张三电脑能运行

李四电脑报错

线上服务器又是另外一个版本
```

因此需要：

```latex
uv.lock
```

锁定完整依赖版本。

可以类比：

```latex
package-lock.json
pnpm-lock.yaml
yarn.lock
```

---

## 37. 常用 uv 命令
==建议学员先掌握下面这些就够了。==

| 命令 | 作用 |
| --- | --- |
| `uv --version` | 查看 uv 版本 |
| `uv self update` | 更新 uv |
| `uv python install 3.12` | 安装 Python 3.12 |
| `uv python list` | 查看 Python |
| `uv init` | 初始化项目 |
| `uv venv` | 创建虚拟环境 |
| `uv add xxx` | 安装依赖 |
| `uv add --dev xxx` | 安装开发依赖 |
| `uv remove xxx` | 删除依赖 |
| `uv sync` | 同步项目环境 |
| `uv run main.py` | 运行 Python |
| `uv run xxx` | 在项目环境运行命令 |


---

## 38. uv pip
uv 同样兼容很多 pip 的操作方式。

例如：

```bash
uv pip install requests
```

但是对于新的项目，更推荐：

```bash
uv add requests
```

区别可以简单理解：

```latex
uv pip install
```

更加类似传统：

```latex
pip install
```

而：

```latex
uv add
```

会直接管理当前项目的依赖配置。

课程项目统一推荐：

```bash
uv add
```

---

## 39. requirements.txt 项目怎么办？
很多老项目仍然使用：

```latex
requirements.txt
```

例如：

```latex
fastapi
uvicorn
requests
```

可以：

```bash
uv pip install -r requirements.txt
```

==所以以前的 Python 项目 uv 一样可以使用。==

---

## 40. Windows 常见问题
### 问题一
执行：

```bash
uv
```

出现：

```latex
'uv' is not recognized
```

优先：

```latex
关闭 PowerShell
重新打开
```

再：

```bash
uv --version
```

如果还不行，就检查：

```latex
PATH
```

---

### 问题二：PowerShell 禁止执行脚本
可能出现：

```latex
running scripts is disabled on this system
```

可以尝试：

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

然后重新执行相关命令。

注意：

==企业电脑如果有 IT 安全策略，不建议随意修改系统级安全配置。==

---

### 问题三：python 命令找不到
不用急着自己去下载各种 Python 安装包。

可以直接：

```bash
uv python install 3.12
```

然后：

```bash
uv python list
```

---

## 41. macOS 常见问题
### 问题一
出现：

```latex
zsh: command not found: uv
```

执行：

```bash
source ~/.zshrc
```

再：

```bash
uv --version
```

---

### 问题二
还是找不到。

执行：

```bash
ls ~/.local/bin
```

检查有没有：

```latex
uv
```

如果存在，就在：

```latex
~/.zshrc
```

加入：

```bash
export PATH="$HOME/.local/bin:$PATH"
```

然后：

```bash
source ~/.zshrc
```

---

## 42. Intel Mac 和 Apple Silicon 有区别吗？
使用官方 uv 安装脚本：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

一般不需要自己区分：

```latex
Intel
M1
M2
M3
M4
```

安装程序会根据当前平台处理。

---

## 43. 查看 Mac CPU 架构
如果想确认，可以执行：

```bash
uname -m
```

Apple Silicon 通常显示：

```latex
arm64
```

Intel Mac 通常显示：

```latex
x86_64
```

---

## 44. 更新 uv
可以执行：

```bash
uv self update
```

然后：

```bash
uv --version
```

查看版本。

如果是通过 Homebrew 安装：

```bash
brew upgrade uv
```

---

## 45. VS Code 配置 Python
==安装 VS Code 以后，建议安装：==

```latex
Python
```

扩展。

项目使用 uv 创建：

```latex
.venv
```

以后，在 VS Code 中选择 Python Interpreter。

通常选择：

Windows：

```latex
.venv\Scripts\python.exe
```

macOS：

```latex
.venv/bin/python
```

---

## 46. 如何确认 VS Code 使用的是正确 Python？
创建：

```python
import sys

print(sys.executable)
```

运行：

```bash
uv run main.py
```

例如可能输出：

macOS：

```latex
/Users/xxx/project/.venv/bin/python
```

Windows：

```latex
C:\project\.venv\Scripts\python.exe
```

看到：

```latex
.venv
```

基本就说明当前项目正在使用自己的虚拟环境。

---

## 47. 给前端开发者的理解方式
如果你之前是前端开发，完全可以这样理解：

```latex
Node.js                    Python

nvm                  →     uv python

npm / pnpm           →     uv

package.json          →     pyproject.toml

package-lock.json     →     uv.lock

node_modules          →     .venv

npm install           →     uv sync

npm install axios     →     uv add requests

npm run dev           →     uv run ...
```

因此：

> 不要把 Python 环境管理想得特别复杂。
>

如果你已经会 Node.js：

```latex
nvm
npm
pnpm
package.json
node_modules
```

那么 uv 的很多概念其实你已经会了。

只是名字不同。

---

## 48. 给 Java 开发者的理解方式
如果你以前是 Java 开发，也可以这样理解：

```latex
Java                        Python

JDK                   →    Python

Maven / Gradle        →    uv

pom.xml               →    pyproject.toml

Maven dependency      →    Python package

mvn install           →    uv sync

Maven repository      →    Python package index
```

但是 Python 比 Java 多一个非常重要的概念：

```latex
虚拟环境 .venv
```

每一个项目尽量拥有自己独立的 Python 环境。

---

## 49. 课程统一环境建议
==为了减少后面的问题，建议整套 AI Agent 课程统一使用：==

```latex
编辑器：

VS Code
Cursor
```

Python：

```latex
Python 3.12
```

Python 管理工具：

```latex
uv
```

Web 框架：

```latex
FastAPI
```

数据校验：

```latex
Pydantic
```

Agent：

```latex
LangChain
LangGraph
```

最终整个技术栈：

```latex
Python 3.12
        ↓
       uv
        ↓
    FastAPI
        ↓
   LangChain
        ↓
   LangGraph
        ↓
 RAG / MCP / Agent
```

---

## 50. 最终环境检查
Windows 和 macOS 安装完成以后，都执行下面几个命令。

### 检查 uv
```bash
uv --version
```

### 检查 Python
```bash
uv python list
```

### 创建项目
```bash
uv init python-demo
```

### 进入项目
```bash
cd python-demo
```

### 运行程序
```bash
uv run main.py
```

如果这些命令全部可以正常执行：

```latex
✅ uv 安装成功

✅ Python 环境正常

✅ 虚拟环境正常

✅ 项目依赖管理正常

✅ Python 开发环境搭建完成
```

接下来就可以正式开始：

```latex
Python 基础

↓

FastAPI

↓

大模型 API

↓

LangChain

↓

RAG

↓

MCP

↓

LangGraph

↓

AI Agent
```

的学习。

---

> [!success] 一句话带走
> ==环境问题里，九成都是 PATH 和版本没对上。==

> [!quote] 关于本文档
> 由原始讲义 `第 02 章｜Python AI 开发环境搭建 - Python 开发环境搭建：uv 安装与使用教程.md` 转换为 Obsidian 风格笔记；原文完整保留，未做任何删改。
> 整理日期：2026-11-22
