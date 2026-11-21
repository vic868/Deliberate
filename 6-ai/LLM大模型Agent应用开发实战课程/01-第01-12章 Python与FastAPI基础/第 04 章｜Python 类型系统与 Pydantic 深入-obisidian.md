---
title: "第 04 章｜Python 类型系统与 Pydantic 深入"
chapter: "04"
source: "第 04 章｜Python 类型系统与 Pydantic 深入.md"
type: obsidian-note
created: 2026-11-22
status: 整理中
tags:
  - course/llm-agent
  - python
  - pydantic
  - 类型系统
---

# 第 04 章｜Python 类型系统与 Pydantic 深入

> [!abstract] 本章重点
>
> - ==Type Hint 默认不做运行时校验== — 它更像注释：IDE 和类型检查器看得懂，Python 运行时不拦。
> - ==Optional 不等于「可不传」== — Optional[str] 是说「可以是 str 或 None」，但参数仍然必填。
> - ==Pydantic BaseModel 才是真正的运行时校验== — 数据不合规直接抛明确错误，特别适合接 API 请求。
> - ==Field 管约束，model_dump 管序列化== — 长度、范围用 Field；转字典/JSON 用 model_dump / model_dump_json。
> - ==Literal / Enum / TypedDict 收紧取值范围== — 把「随便什么字符串」变成「只能是这几个值」。
>
> [!note] 大白话
>
> - **运行时校验**：程序真跑起来时检查数据合不合规，不只是写代码时提醒一下。
> - **泛型响应**：外面套一层统一结构，里面装什么类型由参数决定。
>
> [!info] 导航与来源
> - 原始讲义：[[第 04 章｜Python 类型系统与 Pydantic 深入|打开原始讲义]]
> - [[第 03 章｜Python AI 开发快速入门|上一章｜第 03 章]]
> - [[第 05 章｜Python 异步编程 async ｜ await|下一章｜第 05 章]]
> - 本章所有内容均保留，未删改原文。

## 本章导航

- [[#一、本章定位]]
- [[#二、本章学习目标]]
- [[#三、本章最终项目结构]]
- [[#四、01｜本章开场]]
- [[#类型系统与 Pydantic]]
- [[#五、02｜创建本章代码目录]]
- [[#六、03｜Type Hint 是什么]]
- [[#七、04｜Type Hint 默认不是运行时强校验]]
- [[#八、05｜常用基础类型]]
- [[#九、06｜Optional 和 None]]
- [[#十、07｜Optional 不是“可不传”的意思]]
- [[#十一、08｜Union 多类型]]
- [[#十二、09｜Literal 限定固定值]]
- [[#十三、10｜Enum 枚举]]

---
---

## 一、本章定位

> [!abstract] 本节定位
> 先看清这一节要解决什么问题。

上一章我们快速学习了 AI 开发常用的 Python 基础语法：

```text
变量
List
Dict
函数
Type Hint
Class
Pydantic
异常处理
模块导入
async / await
```

这一章我们单独把两个东西拿出来深入讲：

```text
Type Hint
Pydantic
```

为什么？

因为后面我们开发 AI 后端项目，基本每天都会写类似这样的代码：

```python
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="用户问题")
    model: str = Field(default="deepseek-chat", description="模型名称")
    temperature: float = Field(default=0.7, ge=0, le=2, description="模型温度")
    stream: bool = Field(default=True, description="是否流式输出")
```

这段代码不是普通的 Python 类。

它后面会直接变成：

```text
FastAPI 请求参数
OpenAPI 文档
Swagger 接口文档
LLM Structured Output
Tool 参数 Schema
Agent State
RAG Document Schema
```

所以这一章非常重要。

简单说：

**Type Hint 是 Python AI 后端的数据结构表达方式。**

**Pydantic 是 Python AI 后端的数据校验和数据建模核心。**

---

## 二、本章学习目标

> [!abstract] 本节定位
> 先看清这一节要解决什么问题。

学完这一章以后，学员需要掌握：

```text
1. Type Hint 到底是什么
2. Type Hint 和 TypeScript 类型系统有什么区别
3. str / int / float / bool / list / dict / Any 怎么写
4. Optional / Union / Literal / Enum 怎么用
5. TypedDict 适合什么场景
6. Pydantic BaseModel 怎么定义数据模型
7. Field 怎么设置默认值、描述、校验规则
8. ValidationError 怎么看懂
9. model_dump / model_dump_json 怎么用
10. 嵌套模型怎么写
11. List 模型怎么校验
12. field_validator 怎么写字段校验
13. model_validator 怎么写模型级校验
14. ConfigDict 怎么控制模型行为
15. alias 字段别名怎么处理前端 camelCase
16. default_factory 为什么重要
17. Pydantic 如何服务 FastAPI、LLM、Agent、Tool Calling
```

---

## 三、本章最终项目结构
本章继续使用上一章项目：

```text
ai-agent-course/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── basics/
│   └── schemas/
│       ├── __init__.py
│       ├── 01_type_hints.py
│       ├── 02_optional_union.py
│       ├── 03_literal_enum.py
│       ├── 04_typed_dict.py
│       ├── 05_base_model.py
│       ├── 06_field.py
│       ├── 07_nested_model.py
│       ├── 08_validator.py
│       ├── 09_model_config.py
│       ├── 10_serialization.py
│       ├── 11_chat_schema.py
│       ├── 12_tool_schema.py
│       └── 13_agent_state.py
│
├── tests/
├── .env
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
└── uv.lock
```

本章我们统一把数据模型相关代码放到：

```text
app/schemas/
```

后面的课程里：

```text
schemas/
```

会专门存放：

```text
请求体模型
响应体模型
LLM 输出模型
Tool 参数模型
RAG 文档模型
Agent 状态模型
```

---

## 四、01｜本章开场
### 【重点内容】
大家好，欢迎来到第 04 章。

这一章我们要讲 Python AI 后端开发里面非常重要的一块：

## 类型系统与 Pydantic
如果你之前是前端开发，学过 TypeScript，那么你对类型系统应该不陌生。

比如 TypeScript 里我们会写：

```typescript
interface ChatRequest {
  message: string;
  model?: string;
  temperature?: number;
}
```

这个 interface 可以帮我们约束数据结构。

但是大家注意，TypeScript 的类型主要发生在开发阶段和编译阶段。

代码真正运行到浏览器或者 Node.js 之后，类型大部分就不存在了。

但是 Python 里面结合 Pydantic，就不一样。

我们可以写：

```python
class ChatRequest(BaseModel):
    message: str
    model: str = "deepseek-chat"
    temperature: float = 0.7
```

这不只是给编辑器看的类型提示。

Pydantic 会在运行时真正校验数据。

比如前端传过来：

```json
{
  "message": 123
}
```

==如果我们要求 message 必须是字符串，Pydantic 就会给出明确的校验错误。==

这也是为什么 FastAPI、大模型结构化输出、Agent Tool 参数校验，都大量依赖 Pydantic。

所以这一章非常关键。

你可以把它理解成：

**正式进入 FastAPI 和 AI Agent 开发之前，必须先掌握的数据建模基础。**

---

## 五、02｜创建本章代码目录
### 【实操】
进入项目根目录：

```bash
cd ai-agent-course
```

创建目录：

```bash
mkdir -p app/schemas
```

Windows PowerShell：

```powershell
mkdir app\schemas
```

创建初始化文件：

```bash
touch app/schemas/__init__.py
```

Windows PowerShell：

```powershell
New-Item app\schemas\__init__.py
```

---

### 【重点内容】
这一章我们新建一个目录：

```text
app/schemas
```

这个目录后面非常重要。

在企业级 FastAPI 项目里面，我们通常会把：

```text
请求参数
响应参数
数据结构
Pydantic 模型
```

统一放到 schemas 目录。

比如后面我们会有：

```text
chat.py
agent.py
rag.py
tool.py
user.py
```

现在我们先从简单文件开始练习。

---

## 六、03｜Type Hint 是什么
### 【创建文件】
新建文件：

```text
app/schemas/01_type_hints.py
```

写入代码：

```python
def add(a: int, b: int) -> int:
    return a + b


result = add(1, 2)

print(result)
```

运行：

```bash
python app/schemas/01_type_hints.py
```

输出：

```text
3
```

---

### 【重点内容】
这里我们写了一个函数：

```python
def add(a: int, b: int) -> int:
```

这里的：

```python
a: int
b: int
```

表示参数类型。

这里的：

```python
-> int
```

表示返回值类型。

如果用 TypeScript 对比，它类似：

```typescript
function add(a: number, b: number): number {
  return a + b;
}
```

==所以 Type Hint 的第一层作用就是：==

**让代码的数据结构更清晰。**

没有类型注解时：

```python
def add(a, b):
    return a + b
```

你不知道 a 和 b 应该传什么。

有类型注解以后：

```python
def add(a: int, b: int) -> int:
    return a + b
```

调用者一看就知道：

```text
a 是整数
b 是整数
返回值也是整数
```

---

## 七、04｜Type Hint 默认不是运行时强校验
继续修改：

```text
app/schemas/01_type_hints.py
```

代码：

```python
def add(a: int, b: int) -> int:
    return a + b


print(add("1", "2"))
```

运行：

```bash
python app/schemas/01_type_hints.py
```

输出：

```text
12
```

---

### 【重点内容】
大家看这里，非常关键。

我们明明写了：

```python
a: int
b: int
```

但是传进去：

```python
"1"
"2"
```

程序没有报错，而是输出：

```text
12
```

因为字符串相加就是字符串拼接。

所以大家一定要记住：

**Python 的 Type Hint 默认只是类型提示，不是运行时强校验。**

它主要给：

```text
IDE
编辑器
类型检查工具
框架
开发者自己
```

看。

真正要做到运行时校验，就需要：

```text
Pydantic
```

==这就是这一章后面要重点讲的内容。==

---

## 八、05｜常用基础类型
继续写：

```python
from typing import Any


name: str = "大伟"
age: int = 30
score: float = 99.5
is_active: bool = True
extra: Any = {"level": "senior"}

tags: list[str] = ["Python", "FastAPI", "Agent"]

user: dict[str, Any] = {
    "name": "大伟",
    "age": 30,
    "city": "北京"
}

print(name)
print(age)
print(score)
print(is_active)
print(tags)
print(user)
print(extra)
```

运行：

```bash
python app/schemas/01_type_hints.py
```

---

### 【重点内容】
这里我们把常用类型集中看一下。

| TypeScript | Python |
| --- | --- |
| `string` | `str` |
| `number` | `int / float` |
| `boolean` | `bool` |
| `any` | `Any` |
| `string[]` | `list[str]` |
| `Record<string, any>` | `dict[str, Any]` |


这里特别说一下：

```python
Any
```

它表示任意类型。

但是在企业项目里面不要滥用 Any。

因为如果全部写 Any，就等于没有类型。

后面我们写 AI 项目的时候，有些数据确实很灵活，比如：

```text
metadata
tool_arguments
llm_raw_response
```

这些可以临时用：

```python
dict[str, Any]
```

==但是核心数据结构，比如：==

```text
ChatRequest
ChatResponse
ToolCall
AgentState
```

一定要尽量定义清楚。

---

## 九、06｜Optional 和 None
### 【创建文件】
新建：

```text
app/schemas/02_optional_union.py
```

写入：

```python
def get_user_name(user_id: int) -> str | None:
    if user_id == 1:
        return "大伟"

    return None


print(get_user_name(1))
print(get_user_name(2))
```

运行：

```bash
python app/schemas/02_optional_union.py
```

输出：

```text
大伟
None
```

---

### 【重点内容】
这里：

```python
str | None
```

表示：

```text
返回值可能是字符串
也可能是 None
```

这在 TypeScript 里面类似：

```typescript
string | null
```

在 Python 老写法里面，也经常会看到：

```python
from typing import Optional


def get_user_name(user_id: int) -> Optional[str]:
    pass
```

这两种写法大家都要认识：

```python
str | None
```

以及：

```python
Optional[str]
```

现在新项目里面，我们优先使用：

```python
str | None
```

因为更简洁。

---

## 十、07｜Optional 不是“可不传”的意思
继续写：

```python
from pydantic import BaseModel


class UserA(BaseModel):
    name: str
    email: str | None


class UserB(BaseModel):
    name: str
    email: str | None = None


print(UserB(name="大伟"))
```

运行：

```bash
python app/schemas/02_optional_union.py
```

---

### 【重点内容】
这里有一个非常容易误解的点。

很多同学看到：

```python
email: str | None
```

就以为 email 可以不传。

不是。

它的意思是：

```text
email 的值可以是 str
也可以是 None
```

但是字段是否必填，要看有没有默认值。

比如：

```python
email: str | None
```

表示：

```text
字段必传
但是可以传 None
```

而：

```python
email: str | None = None
```

表示：

```text
字段可以不传
不传时默认是 None
```

这个在 FastAPI 请求体里面非常重要。

后面你定义接口参数时，如果写错，会导致前端明明不想传这个字段，但是接口一直报 422 参数错误。

---

## 十一、08｜Union 多类型
继续写：

```python
def parse_id(value: int | str) -> str:
    return str(value)


print(parse_id(10001))
print(parse_id("10001"))
```

运行：

```bash
python app/schemas/02_optional_union.py
```

输出：

```text
10001
10001
```

---

### 【重点内容】
这里：

```python
int | str
```

表示 value 可以是：

```text
int
或者
str
```

这在 TypeScript 里面就是：

```typescript
number | string
```

老写法也可以写成：

```python
from typing import Union

value: Union[int, str]
```

新项目里，优先使用：

```python
int | str
```

更简洁。

---

## 十二、09｜Literal 限定固定值
### 【创建文件】
新建：

```text
app/schemas/03_literal_enum.py
```

写入：

```python
from typing import Literal


ModelName = Literal["deepseek-chat", "qwen-plus", "gpt-4o-mini"]


def chat(message: str, model: ModelName) -> str:
    return f"使用 {model} 回答：{message}"


print(chat("什么是 AI Agent？", "deepseek-chat"))
```

运行：

```bash
python app/schemas/03_literal_enum.py
```

输出：

```text
使用 deepseek-chat 回答：什么是 AI Agent？
```

---

### 【重点内容】
Literal 的作用是限定一个值只能是某几个固定值。

比如：

```python
Literal["deepseek-chat", "qwen-plus", "gpt-4o-mini"]
```

就表示 model 只能是这三个字符串之一。

这在 AI 应用里非常常见。

比如模型名称：

```text
deepseek-chat
qwen-plus
gpt-4o-mini
```

消息角色：

```text
system
user
assistant
tool
```

Agent 类型：

```text
chat
rag
tool
multi_agent
```

都适合用 Literal。

---

## 十三、10｜Enum 枚举
继续写：

```python
from enum import Enum


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


def create_message(role: MessageRole, content: str) -> dict[str, str]:
    return {
        "role": role.value,
        "content": content
    }


print(create_message(MessageRole.USER, "你好"))
```

运行：

```bash
python app/schemas/03_literal_enum.py
```

输出：

```text
{'role': 'user', 'content': '你好'}
```

---

### 【重点内容】
Literal 适合简单固定值。

如果固定值比较多，或者希望可维护性更好，可以使用 Enum。

比如：

```python
class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
```

这里我们继承：

```python
str, Enum
```

是为了让它既是枚举，又可以像字符串一样参与序列化。

后面我们定义大模型消息时，会经常用到：

```python
MessageRole.USER
MessageRole.ASSISTANT
MessageRole.SYSTEM
```

这样比直接写字符串更安全。

---

## 十四、11｜TypedDict：给字典加类型
### 【创建文件】
新建：

```text
app/schemas/04_typed_dict.py
```

写入：

```python
from typing import TypedDict


class MessageDict(TypedDict):
    role: str
    content: str


message: MessageDict = {
    "role": "user",
    "content": "你好"
}

print(message)
```

运行：

```bash
python app/schemas/04_typed_dict.py
```

输出：

```text
{'role': 'user', 'content': '你好'}
```

---

### 【重点内容】
TypedDict 可以给字典定义结构。

普通字典：

```python
message = {
    "role": "user",
    "content": "你好"
}
```

你不知道里面到底有哪些字段。

加上 TypedDict：

```python
class MessageDict(TypedDict):
    role: str
    content: str
```

以后编辑器就能知道：

```text
role 是字符串
content 是字符串
```

但是注意：

TypedDict 主要还是类型提示。

它不像 Pydantic 那样做运行时校验。

所以如果是：

```text
内部临时数据
简单字典结构
不需要运行时校验
```

可以用 TypedDict。

如果是：

```text
接口请求体
接口响应体
大模型输出
Tool 参数
Agent State
```

==建议优先使用 Pydantic BaseModel。==

---

## 十五、12｜Pydantic BaseModel 入门
### 【创建文件】
新建：

```text
app/schemas/05_base_model.py
```

确认安装 Pydantic：

```bash
uv add pydantic
```

写入：

```python
from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    model: str = "deepseek-chat"
    temperature: float = 0.7
    stream: bool = True


request = ChatRequest(
    message="什么是 AI Agent？"
)

print(request)
print(request.message)
print(request.model)
print(request.temperature)
print(request.stream)
```

运行：

```bash
python app/schemas/05_base_model.py
```

输出类似：

```text
message='什么是 AI Agent？' model='deepseek-chat' temperature=0.7 stream=True
什么是 AI Agent？
deepseek-chat
0.7
True
```

---

### 【重点内容】
现在正式进入 Pydantic。

我们定义了一个：

```python
class ChatRequest(BaseModel):
```

这里继承了：

```python
BaseModel
```

这就表示它是一个 Pydantic 模型。

里面这些字段：

```python
message: str
model: str = "deepseek-chat"
temperature: float = 0.7
stream: bool = True
```

就表示这个模型的数据结构。

如果你是前端开发，可以把它类比成 TypeScript interface：

```typescript
interface ChatRequest {
  message: string;
  model?: string;
  temperature?: number;
  stream?: boolean;
}
```

但是区别是：

**Pydantic 不只是类型声明，它还会在运行时创建对象、校验数据、转换数据、序列化数据。**

---

## 十六、13｜Pydantic 运行时校验
继续写：

```python
from pydantic import BaseModel, ValidationError


class ChatRequest(BaseModel):
    message: str
    model: str = "deepseek-chat"
    temperature: float = 0.7
    stream: bool = True


try:
    request = ChatRequest(
        message=123,
        temperature="abc"
    )
except ValidationError as e:
    print(e)
```

运行：

```bash
python app/schemas/05_base_model.py
```

输出类似：

```text
2 validation errors for ChatRequest
message
  Input should be a valid string
temperature
  Input should be a valid number
```

---

### 【重点内容】
大家看，这里就和普通 Type Hint 不一样了。

我们传：

```python
message=123
temperature="abc"
```

Pydantic 会真正校验。

如果类型不符合，它会抛出：

```python
ValidationError
```

==这就是 FastAPI 能自动校验请求参数的原因。==

后面我们写接口：

```python
@app.post("/chat")
async def chat(request: ChatRequest):
    pass
```

如果前端传错参数，FastAPI 会自动返回 422，不需要我们手写：

```python
if not isinstance(message, str):
    return error
```

这就是 Pydantic 的价值。

---

## 十七、14｜model_dump 转成字典
继续写：

```python
from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    model: str = "deepseek-chat"
    temperature: float = 0.7
    stream: bool = True


request = ChatRequest(
    message="什么是 RAG？"
)

data = request.model_dump()

print(data)
print(type(data))
```

运行：

```bash
python app/schemas/05_base_model.py
```

输出：

```text
{'message': '什么是 RAG？', 'model': 'deepseek-chat', 'temperature': 0.7, 'stream': True}
<class 'dict'>
```

---

### 【重点内容】
Pydantic 模型经常需要转换成字典。

这时候使用：

```python
model_dump()
```

比如我们后面调用大模型 API 时，可能需要把对象转成 dict。

```python
payload = request.model_dump()
```

再交给 HTTP 客户端。

在 Pydantic v1 里面，老项目可能会看到：

```python
dict()
```

但是在 Pydantic v2 里面，我们优先使用：

```python
model_dump()
```

==所以后面课程统一使用 Pydantic v2 写法。==

---

## 十八、15｜model_dump_json 转成 JSON 字符串
继续写：

```python
from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    model: str = "deepseek-chat"
    temperature: float = 0.7
    stream: bool = True


request = ChatRequest(
    message="什么是 LangGraph？"
)

json_str = request.model_dump_json()

print(json_str)
print(type(json_str))
```

运行：

```bash
python app/schemas/05_base_model.py
```

输出：

```json
{"message":"什么是 LangGraph？","model":"deepseek-chat","temperature":0.7,"stream":true}
<class 'str'>
```

---

### 【重点内容】
如果要转成 JSON 字符串，可以使用：

```python
model_dump_json()
```

注意区别：

```text
model_dump()
= Python dict

model_dump_json()
= JSON string
```

后面我们处理：

```text
日志
模型输入输出
接口响应
调试信息
```

都会用到这两个方法。

---

## 十九、16｜Field 基础用法
### 【创建文件】
新建：

```text
app/schemas/06_field.py
```

写入：

```python
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., description="用户输入的问题")
    model: str = Field(default="deepseek-chat", description="模型名称")
    temperature: float = Field(default=0.7, description="模型温度")
    stream: bool = Field(default=True, description="是否流式输出")


request = ChatRequest(message="什么是 AI Agent？")

print(request.model_dump())
```

运行：

```bash
python app/schemas/06_field.py
```

输出：

```text
{'message': '什么是 AI Agent？', 'model': 'deepseek-chat', 'temperature': 0.7, 'stream': True}
```

---

### 【重点内容】
Field 可以给字段增加更多信息。

比如：

```python
message: str = Field(..., description="用户输入的问题")
```

这里的：

```python
...
```

表示这个字段必填。

```python
description
```

表示字段描述。

后面 FastAPI 会把这些描述自动放到 Swagger 文档里面。

也就是说，你写的 Pydantic 模型，不只是校验数据，还会生成接口文档。

---

## 二十、17｜Field 校验字符串长度
继续写：

```python
from pydantic import BaseModel, Field, ValidationError


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="用户输入的问题"
    )


try:
    request = ChatRequest(message="")
except ValidationError as e:
    print(e)
```

运行：

```bash
python app/schemas/06_field.py
```

输出类似：

```text
1 validation error for ChatRequest
message
  String should have at least 1 character
```

---

### 【重点内容】
这里我们给 message 增加了长度限制：

```python
min_length=1
max_length=2000
```

这在 AI Chat 接口里面非常有用。

因为用户不能提交空问题。

同时也不能提交特别长的问题，否则可能导致：

```text
Token 超限
接口响应慢
模型成本变高
```

所以后面我们会经常写：

```python
message: str = Field(..., min_length=1, max_length=2000)
```

---

## 二十一、18｜Field 校验数字范围
继续写：

```python
from pydantic import BaseModel, Field, ValidationError


class ChatRequest(BaseModel):
    message: str
    temperature: float = Field(
        default=0.7,
        ge=0,
        le=2,
        description="模型温度，范围 0 到 2"
    )


try:
    request = ChatRequest(
        message="你好",
        temperature=3
    )
except ValidationError as e:
    print(e)
```

运行：

```bash
python app/schemas/06_field.py
```

输出类似：

```text
1 validation error for ChatRequest
temperature
  Input should be less than or equal to 2
```

---

### 【重点内容】
这里：

```python
ge=0
le=2
```

表示：

```text
greater than or equal，大于等于 0
less than or equal，小于等于 2
```

AI 模型里面经常有这种参数：

```text
temperature
top_p
max_tokens
```

这些参数都有合理范围。

我们不要等到调用模型之后才发现参数不对。

而是在请求进入系统的时候，就用 Pydantic 先校验掉。

---

## 二十二、19｜default_factory 解决可变默认值问题
继续写：

```python
from pydantic import BaseModel, Field


class ChatSession(BaseModel):
    session_id: str
    messages: list[str] = Field(default_factory=list)


session1 = ChatSession(session_id="s1")
session2 = ChatSession(session_id="s2")

session1.messages.append("你好")

print(session1.model_dump())
print(session2.model_dump())
```

运行：

```bash
python app/schemas/06_field.py
```

输出：

```text
{'session_id': 's1', 'messages': ['你好']}
{'session_id': 's2', 'messages': []}
```

---

### 【重点内容】
这里有一个非常重要的工程习惯。

如果字段默认值是列表、字典这种可变对象，不要直接写：

```python
messages: list[str] = []
```

推荐写：

```python
messages: list[str] = Field(default_factory=list)
```

为什么？

因为列表是可变对象。

如果多个实例共享同一个默认列表，就会出现非常隐蔽的问题。

==所以在 Pydantic 里，只要默认值是：==

```text
list
dict
set
```

这类可变对象，优先使用：

```python
default_factory
```

后面我们定义：

```text
messages
tools
documents
steps
```

这些字段都会用到。

---

## 二十三、20｜嵌套模型：Message 和 ChatRequest
### 【创建文件】
新建：

```text
app/schemas/07_nested_model.py
```

写入：

```python
from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str = Field(..., description="消息角色")
    content: str = Field(..., min_length=1, description="消息内容")


class ChatRequest(BaseModel):
    messages: list[Message] = Field(..., description="对话消息列表")
    model: str = Field(default="deepseek-chat", description="模型名称")


request = ChatRequest(
    messages=[
        Message(role="system", content="你是一个专业的 AI 助手"),
        Message(role="user", content="什么是 RAG？")
    ]
)

print(request.model_dump())
```

运行：

```bash
python app/schemas/07_nested_model.py
```

输出类似：

```json
{
  'messages': [
    {'role': 'system', 'content': '你是一个专业的 AI 助手'},
    {'role': 'user', 'content': '什么是 RAG？'}
  ],
  'model': 'deepseek-chat'
}
```

---

### 【重点内容】
AI Chat 里面最常见的数据结构就是：

```text
messages
```

它通常是一个列表。

列表里每一项都是一条消息。

所以我们可以先定义：

```python
class Message(BaseModel):
```

然后在 ChatRequest 里面写：

```python
messages: list[Message]
```

这就是嵌套模型。

后面我们会大量使用类似结构。

比如：

```text
ChatRequest
    ↓
Message[]

ToolCall
    ↓
ToolArgument

RAGResponse
    ↓
SourceDocument[]

AgentState
    ↓
Step[]
```

==一个企业级 AI 应用，数据模型一定会越来越复杂。==

所以嵌套模型必须熟悉。

---

## 二十四、21｜嵌套模型也会自动校验
继续写：

```python
from pydantic import BaseModel, Field, ValidationError


class Message(BaseModel):
    role: str = Field(..., description="消息角色")
    content: str = Field(..., min_length=1, description="消息内容")


class ChatRequest(BaseModel):
    messages: list[Message]


try:
    request = ChatRequest(
        messages=[
            {"role": "user", "content": ""}
        ]
    )
except ValidationError as e:
    print(e)
```

运行：

```bash
python app/schemas/07_nested_model.py
```

输出类似：

```text
1 validation error for ChatRequest
messages.0.content
  String should have at least 1 character
```

---

### 【重点内容】
这里大家看错误信息：

```text
messages.0.content
```

意思是：

```text
messages 列表里面第 0 个元素的 content 字段有问题
```

==这就是 Pydantic 很好用的地方。==

即使是嵌套结构，它也可以给出非常明确的错误位置。

后面如果我们的 Agent State 里面有很多嵌套字段，Pydantic 仍然可以帮我们定位问题。

---

## 二十五、22｜Field alias：处理前端 camelCase
### 【创建文件】
新建：

```text
app/schemas/09_model_config.py
```

写入：

```python
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(alias="sessionId")
    message: str


request = ChatRequest(
    sessionId="s_10001",
    message="你好"
)

print(request.session_id)
print(request.model_dump())
print(request.model_dump(by_alias=True))
```

运行：

```bash
python app/schemas/09_model_config.py
```

输出：

```text
s_10001
{'session_id': 's_10001', 'message': '你好'}
{'sessionId': 's_10001', 'message': '你好'}
```

---

### 【重点内容】
这里是前后端联调非常常见的问题。

前端习惯写：

```typescript
sessionId
```

这是 camelCase。

Python 后端习惯写：

```python
session_id
```

这是 snake_case。

那怎么办？

Pydantic 提供了 alias。

```python
session_id: str = Field(alias="sessionId")
```

这样前端传：

```json
{
  "sessionId": "s_10001"
}
```

Python 里面可以用：

```python
request.session_id
```

如果响应给前端时想继续保持 camelCase，可以：

```python
model_dump(by_alias=True)
```

---

## 二十六、23｜ConfigDict：允许用字段名和别名同时赋值
继续写：

```python
from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    session_id: str = Field(alias="sessionId")
    message: str


request1 = ChatRequest(
    sessionId="s_10001",
    message="你好"
)

request2 = ChatRequest(
    session_id="s_10002",
    message="你好"
)

print(request1.model_dump())
print(request2.model_dump())
```

运行：

```bash
python app/schemas/09_model_config.py
```

输出：

```text
{'session_id': 's_10001', 'message': '你好'}
{'session_id': 's_10002', 'message': '你好'}
```

---

### 【重点内容】
默认情况下，使用 alias 后，你可能只能用别名传值。

但是有时候我们希望：

```text
sessionId
```

和：

```text
session_id
```

都能传。

这时候可以写：

```python
model_config = ConfigDict(populate_by_name=True)
```

这在企业项目里很实用。

因为前端可能使用 camelCase，后端内部使用 snake_case。

我们既要保持前端接口友好，也要保持 Python 代码规范。

---

## 二十七、24｜extra='forbid'：禁止多余字段
继续写：

```python
from pydantic import BaseModel, ConfigDict, ValidationError


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str
    model: str = "deepseek-chat"


try:
    request = ChatRequest(
        message="你好",
        model="deepseek-chat",
        unknown_field="xxx"
    )
except ValidationError as e:
    print(e)
```

运行：

```bash
python app/schemas/09_model_config.py
```

输出类似：

```text
1 validation error for ChatRequest
unknown_field
  Extra inputs are not permitted
```

---

### 【重点内容】
默认情况下，多余字段有时候会被忽略。

但是在一些严谨场景，我们希望前端传了什么，后端就明确校验什么。

如果前端传了未知字段，就直接报错。

可以使用：

```python
ConfigDict(extra="forbid")
```

这在 AI Tool Calling 里面也很有用。

==比如工具参数必须严格符合 schema。==

如果模型多生成了一个字段，我们希望直接发现，而不是悄悄忽略。

---

## 二十八、25｜field_validator：字段级校验
### 【创建文件】
新建：

```text
app/schemas/08_validator.py
```

写入：

```python
from pydantic import BaseModel, Field, ValidationError, field_validator


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        if "广告" in value:
            raise ValueError("message 不能包含广告内容")

        return value


try:
    request = ChatRequest(message="这是一条广告")
except ValidationError as e:
    print(e)
```

运行：

```bash
python app/schemas/08_validator.py
```

输出类似：

```text
1 validation error for ChatRequest
message
  Value error, message 不能包含广告内容
```

---

### 【重点内容】
Field 可以处理很多基础校验，比如：

```text
字符串长度
数字范围
是否必填
```

但是有时候我们需要自定义校验逻辑。

比如：

```text
message 不能包含敏感词
temperature 必须符合业务规则
model 必须在当前租户可用模型列表中
tool_name 不能是禁用工具
```

这时候可以使用：

```python
@field_validator
```

这里我们对 message 做了一个简单判断：

```python
if "广告" in value:
    raise ValueError("message 不能包含广告内容")
```

如果校验不通过，就抛出错误。

---

## 二十九、26｜field_validator：规范化输入
继续写：

```python
from pydantic import BaseModel, field_validator


class UserCreateRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


request = UserCreateRequest(email="  DAWEI@EXAMPLE.COM  ")

print(request.email)
```

运行：

```bash
python app/schemas/08_validator.py
```

输出：

```text
dawei@example.com
```

---

### 【重点内容】
validator 不只是用来报错，还可以用来清洗数据。

比如用户输入 email：

```text
DAWEI@EXAMPLE.COM
```

我们可以自动变成：

```text
dawei@example.com
```

后面我们处理用户输入、Prompt 参数、Tool 参数的时候，也可以做类似清洗。

比如：

```text
去掉前后空格
统一转小写
规范模型名称
清洗用户输入
```

---

## 三十、27｜model_validator：模型级校验
继续写：

```python
from pydantic import BaseModel, Field, ValidationError, model_validator


class ChatRequest(BaseModel):
    message: str
    stream: bool = True
    callback_url: str | None = None

    @model_validator(mode="after")
    def validate_callback_url(self):
        if self.stream is False and self.callback_url is None:
            raise ValueError("非流式任务必须提供 callback_url")

        return self


try:
    request = ChatRequest(
        message="生成一份报告",
        stream=False
    )
except ValidationError as e:
    print(e)
```

运行：

```bash
python app/schemas/08_validator.py
```

输出类似：

```text
1 validation error for ChatRequest
  Value error, 非流式任务必须提供 callback_url
```

---

### 【重点内容】
字段校验适合检查单个字段。

但是有些规则涉及多个字段。

比如：

```text
如果 stream=False
那么 callback_url 必须存在
```

这种逻辑就适合使用：

```python
@model_validator
```

它可以拿到整个模型对象。

后面我们开发 AI 任务时，可能会有类似规则：

```text
如果 mode=rag，knowledge_base_id 必填
如果 mode=agent，agent_id 必填
如果 tool_enabled=True，tools 不能为空
如果 stream=False，callback_url 必填
```

这些都是模型级校验的典型场景。

---

## 三十一、28｜序列化：exclude_none
### 【创建文件】
新建：

```text
app/schemas/10_serialization.py
```

写入：

```python
from pydantic import BaseModel


class ChatResponse(BaseModel):
    answer: str
    session_id: str | None = None
    trace_id: str | None = None


response = ChatResponse(answer="你好，我是 AI 助手")

print(response.model_dump())
print(response.model_dump(exclude_none=True))
```

运行：

```bash
python app/schemas/10_serialization.py
```

输出：

```text
{'answer': '你好，我是 AI 助手', 'session_id': None, 'trace_id': None}
{'answer': '你好，我是 AI 助手'}
```

---

### 【重点内容】
有时候我们不想把 None 字段返回给前端。

默认：

```python
model_dump()
```

会包含：

```python
None
```

但是：

```python
model_dump(exclude_none=True)
```

会把 None 字段去掉。

这个在接口响应里面非常常用。

比如：

```json
{
  "answer": "你好"
}
```

比：

```json
{
  "answer": "你好",
  "trace_id": null,
  "session_id": null
}
```

更干净。

---

## 三十二、29｜序列化：include 和 exclude
继续写：

```python
from pydantic import BaseModel


class User(BaseModel):
    id: int
    name: str
    email: str
    password: str


user = User(
    id=1,
    name="大伟",
    email="dawei@example.com",
    password="123456"
)

print(user.model_dump(exclude={"password"}))
print(user.model_dump(include={"id", "name"}))
```

运行：

```bash
python app/schemas/10_serialization.py
```

输出：

```text
{'id': 1, 'name': '大伟', 'email': 'dawei@example.com'}
{'id': 1, 'name': '大伟'}
```

---

### 【重点内容】
这个很重要。

后端返回用户信息时，千万不能把：

```text
password
```

这种敏感字段返回给前端。

可以使用：

```python
exclude={"password"}
```

只返回指定字段，可以用：

```python
include={"id", "name"}
```

后面我们处理：

```text
用户信息
API Key
Tool 调用日志
模型原始响应
```

都要注意敏感字段过滤。

---

## 三十三、30｜实战一：定义 AI Chat 请求模型
### 【创建文件】
新建：

```text
app/schemas/11_chat_schema.py
```

写入：

```python
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, field_validator


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ChatMessage(BaseModel):
    role: MessageRole = Field(..., description="消息角色")
    content: str = Field(..., min_length=1, description="消息内容")


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    messages: list[ChatMessage] = Field(..., min_length=1, description="对话消息")
    model: str = Field(default="deepseek-chat", description="模型名称")
    temperature: float = Field(default=0.7, ge=0, le=2, description="温度")
    stream: bool = Field(default=True, description="是否流式输出")
    session_id: str | None = Field(default=None, description="会话 ID")

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str) -> str:
        supported_models = ["deepseek-chat", "qwen-plus", "gpt-4o-mini"]

        if value not in supported_models:
            raise ValueError(f"不支持的模型：{value}")

        return value


class ChatResponse(BaseModel):
    answer: str = Field(..., description="AI 回答")
    model: str = Field(..., description="模型名称")
    session_id: str | None = Field(default=None, description="会话 ID")


request = ChatRequest(
    messages=[
        ChatMessage(role=MessageRole.SYSTEM, content="你是一个专业的 AI 助手"),
        ChatMessage(role=MessageRole.USER, content="什么是 AI Agent？")
    ],
    model="deepseek-chat",
    temperature=0.7
)

response = ChatResponse(
    answer="AI Agent 是能够感知任务、规划步骤并调用工具完成目标的智能体。",
    model=request.model,
    session_id=request.session_id
)

print(request.model_dump())
print(response.model_dump(exclude_none=True))
```

运行：

```bash
python app/schemas/11_chat_schema.py
```

---

### 【重点内容】
现在我们进入真实 AI Chat 请求模型。

这个模型后面会直接用于 FastAPI 接口。

我们先定义消息角色：

```python
class MessageRole(str, Enum):
```

然后定义一条消息：

```python
class ChatMessage(BaseModel):
```

再定义请求体：

```python
class ChatRequest(BaseModel):
```

最后定义响应体：

```python
class ChatResponse(BaseModel):
```

大家注意这里已经非常接近真实项目了。

后面 FastAPI 里面只需要写：

```python
@app.post("/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    pass
```

那么：

```text
请求参数校验
Swagger 文档
响应结构
类型提示
```

都会自动具备。

==这就是 Pydantic 在 FastAPI 项目里面的价值。==

---

## 三十四、31｜实战二：定义 Tool Calling 参数模型
### 【创建文件】
新建：

```text
app/schemas/12_tool_schema.py
```

写入：

```python
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field, field_validator


class ToolName(str, Enum):
    QUERY_ORDER = "query_order"
    QUERY_PRODUCT = "query_product"
    QUERY_LOGISTICS = "query_logistics"


class ToolCall(BaseModel):
    tool_name: ToolName = Field(..., description="工具名称")
    arguments: dict[str, Any] = Field(default_factory=dict, description="工具参数")


class OrderQueryArguments(BaseModel):
    order_id: str = Field(..., min_length=1, description="订单 ID")

    @field_validator("order_id")
    @classmethod
    def validate_order_id(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("order_id 必须是数字字符串")

        return value


tool_call = ToolCall(
    tool_name=ToolName.QUERY_ORDER,
    arguments={
        "order_id": "10001"
    }
)

order_args = OrderQueryArguments(**tool_call.arguments)

print(tool_call.model_dump())
print(order_args.model_dump())
```

运行：

```bash
python app/schemas/12_tool_schema.py
```

输出类似：

```text
{'tool_name': <ToolName.QUERY_ORDER: 'query_order'>, 'arguments': {'order_id': '10001'}}
{'order_id': '10001'}
```

---

### 【重点内容】
现在我们看 Tool Calling。

大模型如果判断需要调用工具，可能会返回：

```json
{
  "tool_name": "query_order",
  "arguments": {
    "order_id": "10001"
  }
}
```

这个时候我们不能直接相信模型返回的参数。

因为模型可能会生成错误字段：

```json
{
  "order_id": ""
}
```

或者：

```json
{
  "order_id": "abc"
}
```

==所以我们用 Pydantic 定义：==

```python
class OrderQueryArguments(BaseModel):
```

对工具参数进行二次校验。

这就是 AI Agent 项目里面非常重要的安全意识：

**模型生成的内容不能直接执行，必须经过 Schema 校验。**

尤其是 Agent 能调用真实业务系统时，更要严格校验 Tool 参数。

---

## 三十五、32｜实战三：定义 Agent State
### 【创建文件】
新建：

```text
app/schemas/13_agent_state.py
```

写入：

```python
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class AgentStepType(str, Enum):
    THINK = "think"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    FINAL = "final"


class AgentStep(BaseModel):
    step_type: AgentStepType = Field(..., description="步骤类型")
    content: str = Field(..., description="步骤内容")
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展信息")


class AgentState(BaseModel):
    user_id: str = Field(..., description="用户 ID")
    session_id: str = Field(..., description="会话 ID")
    question: str = Field(..., min_length=1, description="用户问题")
    steps: list[AgentStep] = Field(default_factory=list, description="Agent 执行步骤")
    final_answer: str | None = Field(default=None, description="最终答案")


state = AgentState(
    user_id="u_10001",
    session_id="s_10001",
    question="帮我查询订单 10001 的物流状态"
)

state.steps.append(
    AgentStep(
        step_type=AgentStepType.THINK,
        content="用户想查询订单物流，需要调用 query_logistics 工具"
    )
)

state.steps.append(
    AgentStep(
        step_type=AgentStepType.TOOL_CALL,
        content="调用 query_logistics",
        metadata={
            "order_id": "10001"
        }
    )
)

state.final_answer = "订单 10001 当前正在运输中，预计明天送达。"

print(state.model_dump())
```

运行：

```bash
python app/schemas/13_agent_state.py
```

---

### 【重点内容】
现在这个例子非常重要。

后面我们进入 LangGraph 时，会大量遇到一个概念：

```text
State
```

也就是 Agent 执行过程中的状态。

比如一个 Agent 回答问题，不是一步完成的。

它可能经历：

```text
思考
调用工具
拿到工具结果
再次思考
生成最终答案
```

所以我们可以用：

```python
AgentState
```

来记录整个过程。

==这就是 Pydantic 和 Agent 的结合。==

大家现在先记住：

**Pydantic 不只是给 FastAPI 用，它同样可以用来定义 Agent State。**

后面 LangGraph 的 State、Tool 参数、RAG 文档结构，都可以用 Pydantic 或 TypedDict 表达。

---

## 三十六、33｜Pydantic 在 AI 项目里的四大用途
### 【展示】
```text
Pydantic 在 AI 项目中的用途

1. FastAPI 请求体 / 响应体
2. LLM Structured Output
3. Tool Calling 参数校验
4. Agent State 数据建模
```

---

### 【重点内容】
到这里我们可以总结一下。

Pydantic 在 AI 项目里面至少有四大用途。

第一个：

## FastAPI 请求体 / 响应体
比如：

```python
class ChatRequest(BaseModel):
    message: str
```

第二个：

## LLM Structured Output
比如让模型输出：

```python
class ProductAnalysis(BaseModel):
    name: str
    category: str
    summary: str
```

第三个：

## Tool Calling 参数校验
比如：

```python
class QueryOrderArgs(BaseModel):
    order_id: str
```

第四个：

## Agent State
比如：

```python
class AgentState(BaseModel):
    question: str
    steps: list[AgentStep]
```

==所以大家一定不要把 Pydantic 只理解成：==

“FastAPI 里面定义请求体的东西。”

它其实是整个 Python AI 后端的数据建模基础。

---

## 三十七、34｜Type Hint vs TypedDict vs Pydantic
### 【展示】
| 方案 | 是否运行时校验 | 适合场景 |
| --- | --- | --- |
| Type Hint | 否 | 函数参数、变量提示、提升可读性 |
| TypedDict | 否 | 简单字典结构、内部临时数据 |
| Pydantic BaseModel | 是 | API 请求、响应、LLM 输出、Tool 参数、Agent State |


---

### 【重点内容】
这里我们做一个对比。

Type Hint：

```python
def chat(message: str) -> str:
    pass
```

它主要是提高代码可读性。

TypedDict：

```python
class MessageDict(TypedDict):
    role: str
    content: str
```

它适合给字典增加类型说明。

Pydantic：

```python
class Message(BaseModel):
    role: str
    content: str
```

它不仅有类型，还有运行时校验、序列化、JSON Schema、默认值处理。

所以我们后面项目里面的原则是：

```text
函数参数
= Type Hint

简单内部 dict
= TypedDict

请求 / 响应 / LLM 输出 / Tool 参数
= Pydantic
```

---

## 三十八、35｜常见错误一：Optional 理解错

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误理解：

```python
email: str | None
```

以为可以不传。

实际含义：

```text
字段必传，但值可以是 None
```

如果字段可以不传，应该写：

```python
email: str | None = None
```

---

## 三十九、36｜常见错误二：把 Type Hint 当成强校验
错误认知：

```python
def add(a: int, b: int):
    return a + b
```

以为传字符串会报错。

实际：

```python
add("1", "2")
```

可能正常输出：

```text
12
```

正确认知：

```text
Type Hint
= 类型提示

Pydantic
= 运行时校验
```

---

## 四十、37｜常见错误三：可变默认值直接写 []

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

不推荐：

```python
class ChatSession(BaseModel):
    messages: list[str] = []
```

推荐：

```python
class ChatSession(BaseModel):
    messages: list[str] = Field(default_factory=list)
```

原因：

```text
list / dict / set 是可变对象
推荐使用 default_factory 创建独立默认值
```

---

## 四十一、38｜常见错误四：前后端命名风格不一致
前端：

```json
{
  "sessionId": "s_10001"
}
```

后端：

```python
session_id: str
```

解决：

```python
session_id: str = Field(alias="sessionId")
```

需要字段名和别名都支持：

```python
model_config = ConfigDict(populate_by_name=True)
```

---

## 四十二、39｜常见错误五：把模型输出直接拿去执行

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误：

```python
tool_args = llm_response["arguments"]
query_order(**tool_args)
```

风险：

```text
模型可能生成错误参数
模型可能生成多余字段
模型可能漏字段
模型可能生成危险参数
```

正确：

```python
args = OrderQueryArguments(**llm_response["arguments"])
query_order(order_id=args.order_id)
```

核心原则：

**LLM 输出不能直接执行，必须经过 Schema 校验。**

---

## 四十三、40｜本章完整复习
这一章我们掌握了：

```text
Type Hint
Optional
Union
Literal
Enum
TypedDict
BaseModel
Field
ValidationError
field_validator
model_validator
ConfigDict
alias
model_dump
model_dump_json
嵌套模型
Agent State
Tool 参数模型
```

这些内容后面都会用到。

---

## 四十四、41｜本章知识点和 AI 开发场景对应表
| 知识点 | AI 开发场景 |
| --- | --- |
| `str / int / float / bool` | 定义基础请求字段 |
| `list[str]` | messages、documents、tools |
| `dict[str, Any]` | metadata、tool arguments |
| `str | None` | 可选字段，如 session_id |
| `Literal` | 限定模型名称、消息角色 |
| `Enum` | 管理固定业务状态 |
| `TypedDict` | 简单内部状态 |
| `BaseModel` | 请求体、响应体、Agent State |
| `Field` | 参数描述、默认值、校验规则 |
| `field_validator` | 单字段业务校验 |
| `model_validator` | 多字段联合校验 |
| `ConfigDict` | 控制模型行为 |
| `alias` | 前端 camelCase 和后端 snake_case 适配 |
| `model_dump` | 转字典 |
| `model_dump_json` | 转 JSON 字符串 |
| `default_factory` | messages、steps、tools 默认空列表 |
| `ValidationError` | 捕获参数错误 |


---

## 四十五、42｜课后任务一：定义 UserCreateRequest
要求：

```text
1. 使用 BaseModel
2. 字段包括 name、email、age
3. name 最小长度 2
4. age 范围 0 到 120
5. email 可以不传
6. 打印 model_dump()
```

参考答案：

```python
from pydantic import BaseModel, Field


class UserCreateRequest(BaseModel):
    name: str = Field(..., min_length=2)
    email: str | None = None
    age: int = Field(..., ge=0, le=120)


user = UserCreateRequest(
    name="大伟",
    age=30
)

print(user.model_dump())
```

---

## 四十六、43｜课后任务二：定义 ChatRequest
要求：

```text
1. 定义 MessageRole 枚举
2. 定义 ChatMessage
3. 定义 ChatRequest
4. messages 至少一条
5. temperature 范围 0 到 2
6. stream 默认 True
```

参考答案：

```python
from enum import Enum
from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    role: MessageRole
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1)
    model: str = "deepseek-chat"
    temperature: float = Field(default=0.7, ge=0, le=2)
    stream: bool = True
```

---

## 四十七、44｜课后任务三：定义 QueryOrderArgs
要求：

```text
1. order_id 必填
2. order_id 必须是数字字符串
3. 如果不是数字字符串，抛出错误
```

参考答案：

```python
from pydantic import BaseModel, Field, field_validator


class QueryOrderArgs(BaseModel):
    order_id: str = Field(..., min_length=1)

    @field_validator("order_id")
    @classmethod
    def validate_order_id(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("order_id 必须是数字字符串")

        return value


args = QueryOrderArgs(order_id="10001")
print(args.model_dump())
```

---

## 四十八、45｜课后任务四：定义 RAG Document
要求：

```text
1. 定义 RAGDocument
2. 字段包括 id、content、metadata、score
3. content 最小长度 1
4. metadata 默认空 dict
5. score 范围 0 到 1
```

参考答案：

```python
from typing import Any
from pydantic import BaseModel, Field


class RAGDocument(BaseModel):
    id: str
    content: str = Field(..., min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    score: float = Field(..., ge=0, le=1)


doc = RAGDocument(
    id="doc_1",
    content="RAG 是检索增强生成。",
    score=0.89
)

print(doc.model_dump())
```

---

## 四十九、46｜课后任务五：定义 AgentState
要求：

```text
1. 定义 AgentStepType 枚举
2. 定义 AgentStep
3. 定义 AgentState
4. steps 默认空列表
5. final_answer 可以为空
```

参考答案：

```python
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class AgentStepType(str, Enum):
    THINK = "think"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    FINAL = "final"


class AgentStep(BaseModel):
    step_type: AgentStepType
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentState(BaseModel):
    question: str = Field(..., min_length=1)
    steps: list[AgentStep] = Field(default_factory=list)
    final_answer: str | None = None


state = AgentState(question="帮我查询订单状态")
print(state.model_dump())
```

---

## 五十、47｜本章总结

> [!success] 复盘要点
> 复盘时重点看这一节。

### 【重点内容】
好了，到这里，第 04 章我们就讲完了。

这一章内容非常重要。

因为从这一章开始，我们已经不只是写 Python 基础语法了。

我们开始真正进入：

**Python AI 后端的数据建模。**

==大家一定要记住几个核心结论。==

第一：

```text
Type Hint 主要是类型提示
默认不做运行时强校验
```

第二：

```text
Pydantic BaseModel 会做运行时校验
可以直接用于 FastAPI 请求体和响应体
```

第三：

```text
Field 可以定义默认值、描述、校验规则
```

第四：

```text
field_validator 和 model_validator 可以写业务校验
```

第五：

```text
model_dump 和 model_dump_json 用于序列化
```

第六：

```text
Pydantic 不只是 FastAPI 的请求模型
它还可以服务 LLM Structured Output、Tool Calling、Agent State、RAG Document
```

所以后面我们写：

```python
class ChatRequest(BaseModel):
    pass
```

不是为了写一个普通类。

而是在定义：

```text
接口协议
数据结构
校验规则
文档描述
模型输入输出约束
```

==这就是企业级 AI 应用和普通 Demo 最大的区别。==

普通 Demo 可能直接写：

```python
message = request["message"]
```

但是企业项目里面，我们要写：

```python
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
```

这样项目才稳定、可维护、可扩展。

---

> [!success] 一句话带走
> ==Type Hint 写给人和工具看，Pydantic 才是给入口数据把关的那道门。==

> [!quote] 关于本文档
> 由原始讲义 `第 04 章｜Python 类型系统与 Pydantic 深入.md` 转换为 Obsidian 风格笔记；原文完整保留，未做任何删改。
> 整理日期：2026-11-22
