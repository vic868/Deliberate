# 一、本章定位
这一章不是传统 Python 基础课。

我们不会按照“变量、判断、循环、函数”这种纯语法教程去讲，而是站在一个开发者的角度，快速掌握后面开发 AI 应用真正会用到的 Python 语法。

这一章的核心目标是：

**用最短时间掌握 AI 开发必备 Python 语法，为后面的 FastAPI、LLM、LangChain、LangGraph、DeepAgents、RAG、MCP 打基础。**

本章会大量使用：

```plain
JavaScript / TypeScript/ Java
        ↓
Python
```

的方式做对比。

因为很多学员本身已经会前端、Node.js  Java 或 TypeScript，所以他们不是从零学习编程，而是把已有编程经验迁移到 Python。

---

# 二、本章学习目标
学完这一章以后，学员应该掌握：

```plain
1. Python 变量和数据类型
2. Python 字符串和 f-string
3. Python List 列表
4. Python Dict 字典
5. Python 条件判断
6. Python 循环
7. Python 函数
8. Type Hint 类型注解
9. Python Class 类
10. Pydantic 数据模型
11. 异常处理
12. 模块导入
13. async / await 异步编程
14. async generator 异步生成器
15. Python 语法在 AI 开发中的真实用途
```

这一章结束后，学员可以理解后面这些代码为什么这样写：

```python
from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
```

也能理解：

```python
async def chat(request: ChatRequest):
    response = await llm_service.chat(request.message)
    return response
```

更重要的是，他们会知道：

```markdown
函数
= 后面封装 Tool

Class
= 后面封装 Service / Agent

Type Hint
= 后面结合 FastAPI / Pydantic 做参数校验

async / await
= 后面调用大模型 API、数据库、Redis

Generator
= 后面实现流式输出
```

---

# 三、本章最终项目结构
本章继续使用上一章的项目：

```plain
ai-agent-course/
├── app/
│   ├── __init__.py
│   ├── main.py
│   └── basics/
│       ├── 01_variables.py
│       ├── 02_collections.py
│       ├── 03_functions.py
│       ├── 04_type_hints.py
│       ├── 05_classes.py
│       ├── 06_pydantic.py
│       ├── 07_errors.py
│       ├── 08_modules.py
│       ├── 09_async.py
│       └── 10_ai_demo.py
│
├── tests/
├── .env
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
└── uv.lock
```

本章所有练习代码都放到：

```plain
app/basics/
```

里面。

---

# 四、01｜本章开场
## 【内容】
大家好，欢迎来到第 03 章。

上一章我们已经把 Python AI 开发环境搭建好了。

我们完成了：

```plain
Python
 ↓
虚拟环境
 ↓
uv
 ↓
FastAPI
 ↓
Uvicorn
 ↓
Swagger
```

并且我们已经跑通了第一个 FastAPI 接口。

从这一章开始，我们正式进入 Python 语法。

但是大家注意，我不会按照传统 Python 教程给大家讲很多和 AI 开发没什么关系的细节。

因为我们的目标不是成为 Python 语法专家。

我们的目标是：

**用 Python 开发 AI 应用和 AI Agent。**

所以这一章我们只讲后面真正会用到的 Python 核心语法。

比如：

```plain
变量
List
Dict
函数
Type Hint
Class
Pydantic
异常处理
模块
async / await
```

这些内容后面都会直接用在：

```plain
FastAPI 接口
LLM 请求
Prompt 模板
Tool Calling
RAG 检索
Agent 封装
流式输出
```

里面。

如果你是前端开发者，你可以放心。

Python 和 JavaScript / TypeScript 有很多概念是相通的。

你不是从零开始学编程。

你是在把已有的开发经验迁移到 Python。

---

# 五、02｜创建本章代码目录
## 【屏幕操作】
打开上一章项目：

```bash
cd ai-agent-course
```

创建目录：

```bash
mkdir -p app/basics
```

Windows PowerShell：

```powershell
mkdir app\basics
```

创建初始化文件：

```bash
touch app/basics/__init__.py
```

Windows PowerShell：

```powershell
New-Item app\basics\__init__.py
```

---

## 【内容】
这里我们创建一个：

```plain
app/basics
```

目录。

这一章所有 Python 基础练习，都放到这个目录里。

这样后面项目变大之后，我们不会把所有文件都堆到根目录。

---

# 六、03｜Python 变量和基本数据类型
## 【创建文件】
新建文件：

```plain
app/basics/01_variables.py
```

---

## 【第一步：变量定义】
写入代码：

```python
# Python 没有 var / let / const
# 直接赋值就可以

name = "大伟"
age = 30
score = 99.5
is_teacher = True
nothing = None

print(name)
print(age)
print(score)
print(is_teacher)
print(nothing)
```

运行：

```bash
python app/basics/01_variables.py
```

输出：

```plain
大伟
30
99.5
True
None
```

---

## 【内容】
大家先看最基础的变量。

在 JavaScript 里面，我们会写：

```javascript
const name = "大伟";
let age = 30;
```

但是 Python 里面没有：

```plain
var
let
const
```

直接写：

```python
name = "大伟"
age = 30
```

就可以了。

另外几个点大家要注意。

Python 的布尔值是：

```python
True
False
```

首字母大写。

不是 JavaScript 里面的：

```javascript
true
false
```

Python 的空值是：

```python
None
```

不是：

```javascript
null
undefined
```

所以这三个是 Python 零基础学员最容易写错的地方：

```plain
True
False
None
```

必须首字母大写。

---

# 七、04｜Python 命名风格
继续修改：

```plain
app/basics/01_variables.py
```

追加代码：

```python
# Python 推荐使用 snake_case 下划线命名

user_name = "张三"
max_retry_count = 3
is_login = False

print(user_name)
print(max_retry_count)
print(is_login)
```

运行：

```bash
python app/basics/01_variables.py
```

---

## 【内容】
Python 的变量命名风格和 JavaScript / TypeScript / Java 不太一样。

JavaScript 常见的是：

```javascript
const userName = "张三";
const maxRetryCount = 3;
const isLogin = false;
```

也就是：

```plain
camelCase
```

但是 Python 推荐：

```python
user_name = "张三"
max_retry_count = 3
is_login = False
```

也就是：

```plain
snake_case
```

当然，你在 Python 里面写：

```python
userName = "张三"
```

不会报错。

但是不推荐。

因为后面你看 FastAPI、LangChain、LangGraph、Pydantic 的源码，基本都是 Python 社区风格：

```plain
snake_case
```

所以从第一天开始就要养成这个习惯。

---

# 八、05｜字符串和 f-string
继续在：

```plain
app/basics/01_variables.py
```

追加：

```python
name = "大伟"
age = 30

# 不推荐这种拼接方式
msg1 = "你好，我是" + name

# 推荐 f-string
msg2 = f"你好，我是{name}，今年{age}岁"

print(msg1)
print(msg2)
```

运行：

```bash
python app/basics/01_variables.py
```

输出：

```plain
你好，我是大伟
你好，我是大伟，今年30岁
```

---

## 【内容】
在 TypeScript 里面，我们经常用模板字符串：

```typescript
const msg = `你好，我是${name}，今年${age}岁`;
```

Python 里面推荐使用：

```python
f"你好，我是{name}，今年{age}岁"
```

这个叫：

```plain
f-string
```

后面我们写 Prompt 的时候会大量用到。

比如：

```python
prompt = f"""
你是一个专业的电商客服。
用户问题是：{question}
订单信息是：{order_info}
"""
```

所以 f-string 是 AI 开发里非常常用的字符串格式化方式。

---

# 九、06｜常见错误：字符串不能直接拼接数字
继续写：

```python
age = 30

# 故意写错
print("年龄：" + age)
```

运行：

```bash
python app/basics/01_variables.py
```

会报错：

```plain
TypeError: can only concatenate str (not "int") to str
```

---

## 【内容】
这里我们故意写一个错误。

在 JavaScript 里面：

```javascript
console.log("年龄：" + 30);
```

可以正常输出：

```plain
年龄：30
```

因为 JavaScript 会自动做类型转换。

但是 Python 不会这样。

Python 会告诉你：

```plain
你不能把 str 和 int 直接用 + 拼在一起
```

所以正确写法有两种。

第一种：

```python
print("年龄：" + str(age))
```

第二种，更推荐：

```python
print(f"年龄：{age}")
```

所以以后大家字符串拼接，优先使用 f-string。

---

# 十、07｜List 列表
## 【创建文件】
新建：

```plain
app/basics/02_collections.py
```

写入：

```python
# List 对应 JavaScript 里面的 Array

fruits = ["苹果", "香蕉", "橙子"]

print(fruits)
print(fruits[0])
print(fruits[1])
print(fruits[-1])
```

运行：

```bash
python app/basics/02_collections.py
```

输出：

```plain
['苹果', '香蕉', '橙子']
苹果
香蕉
橙子
```

---

## 【内容】
Python 里面的 List，可以先简单理解成 JavaScript 的 Array。

比如 JavaScript：

```javascript
const fruits = ["苹果", "香蕉", "橙子"];
console.log(fruits[0]);
```

Python：

```python
fruits = ["苹果", "香蕉", "橙子"]
print(fruits[0])
```

索引都是从 0 开始。

不过 Python 有一个非常方便的写法：

```python
fruits[-1]
```

表示取最后一个元素。

这在 JavaScript 里面通常要写：

```javascript
fruits[fruits.length - 1]
```

---

# 十一、08｜List 常用操作
继续追加：

```python
fruits = ["苹果", "香蕉", "橙子"]

# 添加元素，对应 JS 的 push
fruits.append("葡萄")

# 修改元素
fruits[0] = "西瓜"

# 删除元素
fruits.remove("香蕉")

print(fruits)

# 获取长度，对应 JS 的 fruits.length
print(len(fruits))
```

运行：

```bash
python app/basics/02_collections.py
```

输出：

```plain
['西瓜', '橙子', '葡萄']
3
```

---

## 【内容】
这里记住几个常用操作就可以了。

JavaScript：

```javascript
fruits.push("葡萄");
fruits.length;
```

Python：

```python
fruits.append("葡萄")
len(fruits)
```

大家注意：

Python 获取长度不是：

```python
fruits.length
```

而是：

```python
len(fruits)
```

后面我们处理：

```plain
messages
documents
tools
chunks
```

都会大量用到 List。

比如：

```python
messages = [
    {"role": "system", "content": "你是一个 AI 助手"},
    {"role": "user", "content": "你好"}
]
```

---

# 十二、09｜List 遍历
继续写：

```python
fruits = ["苹果", "香蕉", "橙子"]

for fruit in fruits:
    print(fruit)
```

运行：

```bash
python app/basics/02_collections.py
```

输出：

```plain
苹果
香蕉
橙子
```

---

## 【内容】
Python 的 for 循环，和 JavaScript 的 for...of 很像。

JavaScript：

```javascript
for (const fruit of fruits) {
  console.log(fruit);
}
```

Python：

```python
for fruit in fruits:
    print(fruit)
```

大家注意两个点。

第一，Python 后面有一个冒号：

```python
:
```

第二，下一行必须缩进。

Python 没有花括号：

```javascript
{}
```

它是靠缩进表示代码块。

---

# 十三、10｜List 推导式
继续写：

```python
numbers = [1, 2, 3, 4, 5]

# 普通写法
result = []

for num in numbers:
    result.append(num * 2)

print(result)

# 列表推导式
doubled = [num * 2 for num in numbers]

print(doubled)
```

运行：

```bash
python app/basics/02_collections.py
```

输出：

```plain
[2, 4, 6, 8, 10]
[2, 4, 6, 8, 10]
```

---

## 【内容】
列表推导式是 Python 很常见的写法。

如果你是前端开发，可以把它理解成类似：

```javascript
numbers.map(num => num * 2)
```

Python：

```python
[num * 2 for num in numbers]
```

后面我们处理文档切片的时候，可能会写：

```python
texts = [doc.content for doc in documents]
```

处理工具名称的时候，可能会写：

```python
tool_names = [tool.name for tool in tools]
```

所以这个写法非常常见。

---

# 十四、11｜带条件的 List 推导式
继续写：

```python
numbers = [1, 2, 3, 4, 5]

big_numbers = [num for num in numbers if num > 2]

print(big_numbers)
```

输出：

```plain
[3, 4, 5]
```

---

## 【内容】
这就类似 JavaScript 的：

```javascript
numbers.filter(num => num > 2)
```

如果既要过滤，又要转换：

```python
result = [num * 2 for num in numbers if num > 2]
```

类似 JavaScript：

```javascript
numbers
  .filter(num => num > 2)
  .map(num => num * 2)
```

---

# 十五、12｜Dict 字典
继续在：

```plain
app/basics/02_collections.py
```

追加：

```python
# Dict 对应 JavaScript 里面的 Object

user = {
    "name": "大伟",
    "age": 30,
    "city": "北京"
}

print(user)
print(user["name"])
print(user["age"])
```

运行：

```bash
python app/basics/02_collections.py
```

输出：

```plain
{'name': '大伟', 'age': 30, 'city': '北京'}
大伟
30
```

---

## 【内容】
Python 的 Dict，可以先理解成 JavaScript 的 Object。

JavaScript：

```javascript
const user = {
  name: "大伟",
  age: 30
};

console.log(user.name);
```

Python：

```python
user = {
    "name": "大伟",
    "age": 30
}

print(user["name"])
```

注意，Python 访问字典字段常见方式是：

```python
user["name"]
```

不是：

```python
user.name
```

---

# 十六、13｜Dict 的 get 方法
继续写：

```python
user = {
    "name": "大伟",
    "age": 30
}

print(user.get("name"))
print(user.get("email"))
print(user.get("email", "未填写"))
```

输出：

```plain
大伟
None
未填写
```

---

## 【内容】
字典有一个非常常用的方法：

```python
get()
```

它的好处是：

如果 key 不存在，不会直接报错。

比如：

```python
user.get("email")
```

如果没有 email，返回：

```python
None
```

还可以设置默认值：

```python
user.get("email", "未填写")
```

这个有点像 JavaScript 里面：

```javascript
user.email ?? "未填写"
```

后面我们处理大模型返回 JSON、工具参数、请求参数的时候会经常用到。

---

# 十七、14｜Dict 遍历
继续写：

```python
user = {
    "name": "大伟",
    "age": 30,
    "city": "北京"
}

for key, value in user.items():
    print(f"{key}: {value}")
```

输出：

```plain
name: 大伟
age: 30
city: 北京
```

---

## 【内容】
Python 遍历字典时，常用：

```python
user.items()
```

它会同时拿到：

```plain
key
value
```

后面我们可能会遍历：

```plain
metadata
config
tool_arguments
model_params
```

比如：

```python
for key, value in model_config.items():
    print(f"{key}: {value}")
```

---

# 十八、15｜条件判断 if / elif / else
## 【创建文件】
新建：

```plain
app/basics/03_control_flow.py
```

写入：

```python
score = 85

if score >= 90:
    print("优秀")
elif score >= 60:
    print("及格")
else:
    print("不及格")
```

运行：

```bash
python app/basics/03_control_flow.py
```

输出：

```plain
及格
```

---

## 【内容】
Python 的条件判断和 JavaScript 思想一样。

JavaScript：

```javascript
if (score >= 90) {
  console.log("优秀");
} else if (score >= 60) {
  console.log("及格");
} else {
  console.log("不及格");
}
```

Python：

```python
if score >= 90:
    print("优秀")
elif score >= 60:
    print("及格")
else:
    print("不及格")
```

大家注意：

JavaScript 是：

```javascript
else if
```

Python 是：

```python
elif
```

这是新手非常容易写错的点。

---

# 十九、16｜逻辑运算符
继续写：

```python
age = 25
is_vip = True

if age >= 18 and is_vip:
    print("成年 VIP 用户")

if age < 18 or is_vip:
    print("满足其中一个条件")

if not is_vip:
    print("不是 VIP")
else:
    print("是 VIP")
```

---

## 【内容】
Python 的逻辑运算符不是：

```javascript
&&
||
!
```

而是：

```python
and
or
not
```

对比一下：

```plain
JavaScript       Python

&&               and
||               or
!                not
```

比如后面我们判断用户权限：

```python
if user.is_admin and user.is_active:
    print("允许访问")
```

判断 Agent 是否需要调用工具：

```python
if intent == "order" or intent == "logistics":
    print("需要调用业务工具")
```

---

# 二十、17｜for 循环和 range
继续写：

```python
for i in range(5):
    print(i)
```

输出：

```plain
0
1
2
3
4
```

---

## 【内容】
Python 的：

```python
range(5)
```

会生成：

```plain
0 到 4
```

不包含 5。

这和 JavaScript：

```javascript
for (let i = 0; i < 5; i++) {}
```

效果类似。

如果想从 1 开始：

```python
for i in range(1, 6):
    print(i)
```

输出：

```plain
1
2
3
4
5
```

---

# 二十一、18｜enumerate 获取索引
继续写：

```python
fruits = ["苹果", "香蕉", "橙子"]

for index, fruit in enumerate(fruits):
    print(f"{index}: {fruit}")
```

输出：

```plain
0: 苹果
1: 香蕉
2: 橙子
```

---

## 【内容】
如果你遍历 List 的时候既想拿到值，又想拿到索引，可以使用：

```python
enumerate()
```

类似 JavaScript：

```javascript
fruits.forEach((fruit, index) => {
  console.log(index, fruit);
});
```

Python：

```python
for index, fruit in enumerate(fruits):
    print(index, fruit)
```

后面我们处理多条消息、多段文档、多次工具调用时，会用到这个写法。

---

# 二十二、19｜函数定义
## 【创建文件】
新建：

```plain
app/basics/04_functions.py
```

写入：

```python
def greet(name):
    return f"你好，{name}"


result = greet("大伟")
print(result)
```

运行：

```bash
python app/basics/04_functions.py
```

输出：

```plain
你好，大伟
```

---

## 【内容】
Python 定义函数使用：

```python
def
```

JavaScript：

```javascript
function greet(name) {
  return `你好，${name}`;
}
```

Python：

```python
def greet(name):
    return f"你好，{name}"
```

大家注意两个点：

第一，函数声明后面有：

```python
:
```

第二，函数体需要缩进。

这也是 Python 和 JavaScript 最大的语法差异之一。

---

# 二十三、20｜默认参数
继续写：

```python
def greet(name, age=18):
    return f"你好，{name}，今年 {age} 岁"


print(greet("大伟"))
print(greet("大伟", 30))
print(greet("大伟", age=30))
```

输出：

```plain
你好，大伟，今年 18 岁
你好，大伟，今年 30 岁
你好，大伟，今年 30 岁
```

---

## 【内容】
Python 函数也支持默认参数。

TypeScript：

```typescript
function greet(name: string, age: number = 18) {}
```

Python：

```python
def greet(name, age=18):
    pass
```

另外 Python 支持关键字参数：

```python
greet("大伟", age=30)
```

也就是说，你可以明确告诉 Python：

```plain
age 这个参数传 30
```

后面调用 LLM 的时候，我们可能会写：

```python
chat(
    message="你好",
    temperature=0.7,
    max_tokens=1024
)
```

这样代码可读性非常好。

---

# 二十四、21｜Type Hint 类型注解
## 【创建文件】
新建：

```plain
app/basics/05_type_hints.py
```

写入：

```python
def add(a: int, b: int) -> int:
    return a + b


result = add(1, 2)
print(result)
```

运行：

```bash
python app/basics/05_type_hints.py
```

输出：

```plain
3
```

---

## 【内容】
接下来这个知识点非常重要：

# Type Hint
也就是类型注解。

如果你学过 TypeScript，就非常好理解。

TypeScript：

```typescript
function add(a: number, b: number): number {
  return a + b;
}
```

Python：

```python
def add(a: int, b: int) -> int:
    return a + b
```

这里：

```python
a: int
b: int
```

表示参数类型。

这里：

```python
-> int
```

表示返回值类型。

---

# 二十五、22｜Type Hint 不等于运行时强校验
继续写：

```python
def add(a: int, b: int) -> int:
    return a + b


print(add("1", "2"))
```

运行：

```bash
python app/basics/05_type_hints.py
```

输出：

```plain
12
```

---

## 【内容】
大家看，这里有一个非常重要的点。

我们明明写了：

```python
a: int
b: int
```

但是传入：

```python
"1"
"2"
```

程序并没有报错。

而是输出了：

```plain
12
```

因为字符串相加就是字符串拼接。

所以大家一定要记住：

**Python 的 Type Hint 默认只是类型提示，不是强制校验。**

它主要给：

```plain
编辑器
IDE
类型检查工具
框架
```

使用。

但是后面我们结合：

```plain
Pydantic
FastAPI
```

就会实现运行时校验。

这也是为什么 Pydantic 在 FastAPI 和 AI 开发里面非常重要。

---

# 二十六、23｜常用类型注解
继续写：

```python
from typing import Any


name: str = "大伟"
age: int = 30
score: float = 99.5
is_active: bool = True
tags: list[str] = ["AI", "FastAPI", "Agent"]
user: dict[str, Any] = {
    "name": "大伟",
    "age": 30
}

print(name)
print(tags)
print(user)
```

运行：

```bash
python app/basics/05_type_hints.py
```

---

## 【内容】
常见类型大家先记住这些：

```plain
TypeScript          Python

string              str
number              int / float
boolean             bool
string[]            list[str]
Record<string, any> dict[str, Any]
any                 Any
```

后面我们会大量写：

```python
messages: list[dict[str, str]]
```

表示：

```plain
messages 是一个列表
列表里面每一项是字典
字典的 key 是字符串
value 也是字符串
```

例如：

```python
messages = [
    {"role": "system", "content": "你是一个 AI 助手"},
    {"role": "user", "content": "你好"}
]
```

---

# 二十七、24｜可选类型 None
继续写：

```python
def get_user_name(user_id: int) -> str | None:
    if user_id == 1:
        return "大伟"

    return None


print(get_user_name(1))
print(get_user_name(2))
```

输出：

```plain
大伟
None
```

---

## 【内容】
这里：

```python
str | None
```

表示返回值可能是：

```plain
字符串
或者
None
```

类似 TypeScript：

```typescript
string | null
```

在老版本 Python 里面，也常见这种写法：

```python
from typing import Optional

def get_user_name(user_id: int) -> Optional[str]:
    pass
```

这两种写法大家都要认识。

后面 FastAPI、LangChain 源码里面都可能看到。

---

# 二十八、25｜Class 类
## 【创建文件】
新建：

```plain
app/basics/06_classes.py
```

写入：

```python
class User:
    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age

    def greet(self) -> str:
        return f"我是 {self.name}，今年 {self.age} 岁"


user = User("大伟", 30)

print(user.name)
print(user.age)
print(user.greet())
```

运行：

```bash
python app/basics/06_classes.py
```

输出：

```plain
大伟
30
我是 大伟，今年 30 岁
```

---

## 【内容】
Python 里面也有 Class。

TypeScript：

```typescript
class User {
  constructor(name: string, age: number) {
    this.name = name;
    this.age = age;
  }

  greet() {
    return `我是 ${this.name}`;
  }
}
```

Python：

```python
class User:
    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age
```

这里：

```python
__init__
```

就类似 TypeScript 里面的：

```typescript
constructor
```

而：

```python
self
```

就类似：

```typescript
this
```

这是前端开发者学习 Python Class 最需要适应的地方。

---

# 二十九、26｜self 是什么
继续看：

```python
class User:
    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age

    def greet(self) -> str:
        return f"我是 {self.name}"
```

---

## 【内容】
这里单独讲一下 self。

Python 里面实例方法的第一个参数，通常都写：

```python
self
```

它表示当前对象自己。

在 TypeScript 里面，你会写：

```typescript
this.name
```

Python 里面写：

```python
self.name
```

但是调用的时候不需要你传 self。

比如：

```python
user.greet()
```

你不需要写：

```python
user.greet(user)
```

Python 会自动把当前对象传进去。

所以大家先记住一句话：

**Python 类里面的方法，第一个参数固定写 self。**

---

# 三十、27｜继承
继续写：

```python
class User:
    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age

    def greet(self) -> str:
        return f"我是 {self.name}"


class Teacher(User):
    def __init__(self, name: str, age: int, subject: str):
        super().__init__(name, age)
        self.subject = subject

    def introduce(self) -> str:
        return f"我是 {self.name}，我教 {self.subject}"


teacher = Teacher("大伟", 30, "AI Agent 开发")

print(teacher.greet())
print(teacher.introduce())
```

输出：

```plain
我是 大伟
我是 大伟，我教 AI Agent 开发
```

---

## 【内容】
Python 也支持继承。

这里：

```python
class Teacher(User):
```

表示：

```plain
Teacher 继承 User
```

这里：

```python
super().__init__(name, age)
```

类似 TypeScript 里面：

```typescript
super(name, age)
```

后面我们封装 Service、Provider、Agent 的时候会用到面向对象思想。

比如：

```plain
BaseLLMProvider
    ↓
OpenAIProvider
DeepSeekProvider
QwenProvider
```

这就是继承的真实使用场景。

---

# 三十一、28｜Pydantic 快速入门
## 【创建文件】
新建：

```plain
app/basics/07_pydantic.py
```

先安装：

```bash
uv add pydantic
```

如果已经安装过，可以跳过。

写入：

```python
from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


request = ChatRequest(message="你好")

print(request.message)
print(request.session_id)
print(request.model_dump())
```

运行：

```bash
python app/basics/07_pydantic.py
```

输出：

```plain
你好
None
{'message': '你好', 'session_id': None}
```

---

## 【内容】
Pydantic 是后面非常重要的一个库。

你可以把它理解成：

**Python 里面用来定义数据结构和做运行时校验的工具。**

如果你是前端开发，可以先简单类比 TypeScript interface。

TypeScript：

```typescript
interface ChatRequest {
  message: string;
  sessionId?: string;
}
```

Python + Pydantic：

```python
class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
```

但是注意：

TypeScript 的 interface 运行后就没有了。

Pydantic 不一样。

它真的会在运行时做数据校验。

这也是为什么 FastAPI 会大量使用 Pydantic。

---

# 三十二、29｜Pydantic 类型校验
继续写：

```python
from pydantic import BaseModel, ValidationError


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


try:
    request = ChatRequest(message=123)
except ValidationError as e:
    print(e)
```

运行：

```bash
python app/basics/07_pydantic.py
```

会看到类似错误：

```plain
1 validation error for ChatRequest
message
  Input should be a valid string
```

---

## 【内容】
大家看，这次真的报错了。

这说明：

```python
message: str
```

在 Pydantic 里面不是简单提示。

它会进行运行时校验。

这对于 AI 开发非常重要。

比如前端调用我们的接口：

```json
{
  "message": 123
}
```

但是后端要求：

```python
message: str
```

那么 FastAPI 就会自动返回参数错误，不需要我们手写一堆 if 判断。

所以大家记住：

```plain
Type Hint
= 类型提示

Pydantic
= 运行时类型校验

FastAPI
= 基于 Pydantic 做请求参数校验
```

---

# 三十三、30｜Pydantic 嵌套模型
继续写：

```python
from pydantic import BaseModel


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    model: str = "deepseek-chat"


request = ChatRequest(
    messages=[
        Message(role="system", content="你是一个 AI 助手"),
        Message(role="user", content="你好")
    ]
)

print(request.model_dump())
```

运行：

```bash
python app/basics/07_pydantic.py
```

输出：

```plain
{
  'messages': [
    {'role': 'system', 'content': '你是一个 AI 助手'},
    {'role': 'user', 'content': '你好'}
  ],
  'model': 'deepseek-chat'
}
```

---

## 【内容】
后面我们调用大模型时，经常会传 messages。

比如：

```python
messages = [
    {"role": "system", "content": "你是一个 AI 助手"},
    {"role": "user", "content": "你好"}
]
```

为了让结构更清晰，我们可以用 Pydantic 定义模型：

```python
class Message(BaseModel):
    role: str
    content: str
```

然后：

```python
class ChatRequest(BaseModel):
    messages: list[Message]
```

这就是后面 FastAPI 接口请求体的基础。

---

# 三十四、31｜异常处理 try / except
## 【创建文件】
新建：

```plain
app/basics/08_errors.py
```

写入：

```python
def divide(a: int, b: int) -> float:
    return a / b


try:
    result = divide(10, 0)
    print(result)
except ZeroDivisionError as e:
    print(f"除数不能为 0：{e}")
except Exception as e:
    print(f"其他错误：{e}")
finally:
    print("不管有没有报错，finally 都会执行")
```

运行：

```bash
python app/basics/08_errors.py
```

输出：

```plain
除数不能为 0：division by zero
不管有没有报错，finally 都会执行
```

---

## 【内容】
Python 的异常处理和 JavaScript 很像。

JavaScript：

```javascript
try {
  // ...
} catch (error) {
  console.error(error);
} finally {
  // ...
}
```

Python：

```python
try:
    pass
except Exception as e:
    pass
finally:
    pass
```

区别是 Python 可以针对不同异常类型分别处理。

比如：

```python
except ZeroDivisionError as e:
```

这表示只捕获除数为 0 的错误。

后面调用大模型 API 的时候，我们会经常处理：

```plain
网络错误
超时错误
API Key 错误
模型返回格式错误
工具调用失败
```

所以异常处理是 AI 后端必须掌握的基础能力。

---

# 三十五、32｜自定义异常
继续写：

```python
class ModelNotFoundError(Exception):
    pass


def get_model(model_name: str) -> str:
    supported_models = ["deepseek-chat", "qwen-plus", "gpt-4o-mini"]

    if model_name not in supported_models:
        raise ModelNotFoundError(f"不支持的模型：{model_name}")

    return model_name


try:
    model = get_model("unknown-model")
    print(model)
except ModelNotFoundError as e:
    print(f"模型错误：{e}")
```

运行：

```bash
python app/basics/08_errors.py
```

输出：

```plain
模型错误：不支持的模型：unknown-model
```

---

## 【内容】
这里我们自定义了一个异常：

```python
class ModelNotFoundError(Exception):
    pass
```

后面我们做 LLM Provider 的时候，可能会遇到：

```plain
模型不存在
模型不可用
API Key 不存在
Token 超限
工具不存在
知识库不存在
```

这些都可以通过自定义异常来表达。

不要所有错误都返回：

```plain
Exception
```

而是尽量让错误更清晰。

---

# 三十六、33｜模块导入 import
## 【创建文件】
新建：

```plain
app/basics/09_modules.py
```

写入：

```python
import os
from pathlib import Path
from typing import Any

print(os.getcwd())

current_file = Path(__file__)
print(current_file)
print(current_file.parent)
```

运行：

```bash
python app/basics/09_modules.py
```

---

## 【内容】
Python 导入模块使用：

```python
import os
```

或者：

```python
from pathlib import Path
```

这和 TypeScript 的 import 很像。

TypeScript：

```typescript
import { readFile } from "fs";
```

Python：

```python
from pathlib import Path
```

后面我们会看到大量类似写法：

```python
from fastapi import FastAPI
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph
```

所以 import 是 Python 项目组织代码的基础。

---

# 三十七、34｜项目内模块导入
创建文件：

```plain
app/basics/utils.py
```

写入：

```python
def format_user_name(name: str) -> str:
    return f"用户：{name}"
```

修改：

```plain
app/basics/09_modules.py
```

写入：

```python
from app.basics.utils import format_user_name

result = format_user_name("大伟")

print(result)
```

运行：

```bash
python app/basics/09_modules.py
```

如果直接运行有路径问题，可以使用：

```bash
python -m app.basics.09_modules
```

---

## 【内容】
这里我们做了一次项目内导入：

```python
from app.basics.utils import format_user_name
```

这类似 TypeScript 里面：

```typescript
import { formatUserName } from "./utils";
```

Python 项目里面推荐通过包路径导入。

如果遇到导入路径问题，可以使用：

```bash
python -m app.basics.09_modules
```

这种方式从项目根目录按模块运行。

后面我们写 FastAPI 项目时，经常会有：

```python
from app.services.chat_service import ChatService
from app.schemas.chat import ChatRequest
from app.core.config import settings
```

所以项目内模块导入一定要熟悉。

---

# 三十八、35｜async / await 异步编程
## 【创建文件】
新建：

```plain
app/basics/10_async.py
```

写入：

```python
import asyncio


async def fetch_data():
    print("开始获取数据")
    await asyncio.sleep(1)
    print("数据获取完成")
    return "这是数据"


result = asyncio.run(fetch_data())

print(result)
```

运行：

```bash
python app/basics/10_async.py
```

输出：

```plain
开始获取数据
数据获取完成
这是数据
```

---

## 【内容】
接下来这个知识点非常重要。

Python 也支持：

```python
async
await
```

这和 JavaScript / TypeScript 的 async/await 思想是一样的。

TypeScript：

```typescript
async function fetchData() {
  const data = await request();
  return data;
}
```

Python：

```python
async def fetch_data():
    data = await request()
    return data
```

后面我们调用：

```plain
大模型 API
数据库
Redis
向量数据库
外部工具
```

大量都是 IO 操作。

所以 async / await 在 AI 后端里面非常重要。

---

# 三十九、36｜并发执行 asyncio.gather
继续写：

```python
import asyncio


async def query_user():
    await asyncio.sleep(1)
    return "用户信息"


async def query_order():
    await asyncio.sleep(1)
    return "订单信息"


async def query_llm():
    await asyncio.sleep(1)
    return "AI 回答"


async def main():
    user, order, answer = await asyncio.gather(
        query_user(),
        query_order(),
        query_llm()
    )

    print(user)
    print(order)
    print(answer)


asyncio.run(main())
```

运行：

```bash
python app/basics/10_async.py
```

---

## 【内容】
大家看这个例子。

如果我们顺序执行：

```plain
查询用户 1 秒
查询订单 1 秒
调用 LLM 1 秒
```

总共大约要 3 秒。

但是使用：

```python
asyncio.gather()
```

可以并发执行。

也就是说：

```plain
查询用户
查询订单
调用 LLM
```

同时开始。

最后整体大约 1 秒完成。

这在 AI 应用里面非常有用。

比如 Agent 回答一个问题时，可能需要同时：

```plain
查询用户信息
查询订单信息
查询知识库
调用搜索工具
```

如果每一步都串行，响应会非常慢。

所以后面我们优化 Agent 性能时，会经常用到并发思想。

---

# 四十、37｜async for 和流式输出
继续写：

```python
import asyncio


async def generate_tokens():
    tokens = ["你", "好", "，", "我", "是", "AI", "。"]

    for token in tokens:
        await asyncio.sleep(0.2)
        yield token


async def main():
    async for token in generate_tokens():
        print(token, end="", flush=True)

    print()


asyncio.run(main())
```

运行：

```bash
python app/basics/10_async.py
```

屏幕会一个字一个字输出：

```plain
你好，我是AI。
```

---

## 【内容】
这个例子非常重要。

因为它和后面的：

```plain
LLM 流式输出
```

直接相关。

大模型流式输出的时候，不是一次性把完整答案返回给你。

而是：

```plain
token
token
token
token
```

一点点返回。

所以我们在 Python 里面可以使用：

```python
async for
```

来处理这种异步数据流。

后面 FastAPI 里面我们会用：

```python
StreamingResponse
```

实现：

```plain
LLM
 ↓
Token Stream
 ↓
FastAPI
 ↓
SSE
 ↓
前端逐字显示
```

所以这个：

```python
async def generate_tokens()
```

虽然现在是模拟的，但它就是后面 AI Chat 流式输出的底层思想。

---

# 四十一、38｜async with 异步上下文管理
继续写：

```python
import asyncio


class AsyncDatabase:
    async def __aenter__(self):
        print("打开数据库连接")
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        print("关闭数据库连接")

    async def query(self, sql: str) -> str:
        await asyncio.sleep(0.5)
        return f"查询结果：{sql}"


async def main():
    async with AsyncDatabase() as db:
        result = await db.query("SELECT * FROM users")
        print(result)


asyncio.run(main())
```

运行：

```bash
python app/basics/10_async.py
```

输出：

```plain
打开数据库连接
查询结果：SELECT * FROM users
关闭数据库连接
```

---

## 【内容】
后面我们用异步数据库、异步 HTTP 客户端的时候，经常会看到：

```python
async with
```

比如：

```python
async with httpx.AsyncClient() as client:
    response = await client.get(url)
```

它的作用是：

**自动管理资源的打开和关闭。**

比如：

```plain
数据库连接
HTTP 客户端
文件资源
网络连接
```

这些资源不能只打开不关闭。

所以 Python 里面会用：

```python
async with
```

来保证资源使用完成后自动释放。

---

# 四十二、39｜综合实战：模拟一个 AI Chat 请求
## 【创建文件】
新建：

```plain
app/basics/11_ai_demo.py
```

写入：

```python
import asyncio
from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    model: str = "deepseek-chat"
    temperature: float = 0.7


class ChatResponse(BaseModel):
    answer: str
    model: str


async def call_llm(message: str, model: str, temperature: float) -> str:
    print("正在调用大模型...")
    print(f"模型：{model}")
    print(f"温度：{temperature}")
    print(f"用户问题：{message}")

    await asyncio.sleep(1)

    return f"AI 回答：你刚才问的是：{message}"


async def chat(request: ChatRequest) -> ChatResponse:
    answer = await call_llm(
        message=request.message,
        model=request.model,
        temperature=request.temperature
    )

    return ChatResponse(
        answer=answer,
        model=request.model
    )


async def main():
    request = ChatRequest(
        message="什么是 AI Agent？",
        model="deepseek-chat",
        temperature=0.7
    )

    response = await chat(request)

    print(response.model_dump())


asyncio.run(main())
```

运行：

```bash
python app/basics/11_ai_demo.py
```

输出类似：

```plain
正在调用大模型...
模型：deepseek-chat
温度：0.7
用户问题：什么是 AI Agent？
{'answer': 'AI 回答：你刚才问的是：什么是 AI Agent？', 'model': 'deepseek-chat'}
```

---

## 【内容】
现在我们把前面学到的内容串起来。

这段代码虽然没有真正调用大模型，但是它已经非常接近后面真实项目的结构了。

我们用了：

```plain
Pydantic
 ↓
定义请求体 ChatRequest

Pydantic
 ↓
定义响应体 ChatResponse

async / await
 ↓
模拟异步调用大模型

函数
 ↓
封装 call_llm 和 chat

Type Hint
 ↓
让代码结构更清晰
```

大家看：

```python
class ChatRequest(BaseModel):
    message: str
    model: str = "deepseek-chat"
    temperature: float = 0.7
```

这个后面会直接变成 FastAPI 的请求体。

也就是说，后面我们写：

```python
@app.post("/chat")
async def chat(request: ChatRequest):
    pass
```

FastAPI 会自动帮我们解析请求参数。

所以这一章不是单纯学语法。

我们学的每个语法，后面都会变成 AI 项目的一部分。

---

# 四十三、40｜综合实战：模拟流式 AI 输出
继续创建：

```plain
app/basics/12_stream_demo.py
```

写入：

```python
import asyncio


async def stream_llm_answer(message: str):
    answer = f"这是针对「{message}」的模拟 AI 流式回答。"

    for char in answer:
        await asyncio.sleep(0.05)
        yield char


async def main():
    async for chunk in stream_llm_answer("什么是 RAG？"):
        print(chunk, end="", flush=True)

    print()


asyncio.run(main())
```

运行：

```bash
python app/basics/12_stream_demo.py
```

你会看到文字逐字输出：

```plain
这是针对「什么是 RAG？」的模拟 AI 流式回答。
```

---

## 【内容】
这个例子就是我们后面做 AI Chat 流式输出的雏形。

现在它只是：

```plain
终端逐字打印
```

后面我们会变成：

```plain
LLM
 ↓
FastAPI StreamingResponse
 ↓
SSE
 ↓
浏览器 EventSource
 ↓
页面逐字显示
```

所以这里大家先记住：

```python
yield
```

表示一点点产出数据。

```python
async for
```

表示一点点消费异步数据。

这两个概念结合起来，就是后面流式大模型输出的基础。

---

# 四十四、41｜本章核心知识和 AI 开发场景对应表
| Python 知识点 | AI 开发中的用途 |
| --- | --- |
| 变量 | 保存用户输入、模型配置、API Key |
| f-string | 拼接 Prompt 模板 |
| List | 存储 messages、documents、tools |
| Dict | 存储 JSON、metadata、tool 参数 |
| if / elif / else | 判断意图、判断工具调用分支 |
| for | 遍历文档、遍历消息、遍历工具 |
| 函数 | 封装 Tool、封装 Service |
| Type Hint | 定义请求和响应类型 |
| Class | 封装 Provider、Service、Agent |
| Pydantic | 请求体验证、结构化输出 |
| try / except | 处理模型调用失败、工具失败 |
| import | 组织项目模块 |
| async / await | 调用 LLM、数据库、Redis |
| asyncio.gather | 并发执行多个工具 |
| async generator | 实现 LLM 流式输出 |


---

# 四十五、42｜常见错误一：忘记缩进
错误代码：

```python
def hello():
print("hello")
```

报错：

```plain
IndentationError: expected an indented block
```

正确写法：

```python
def hello():
    print("hello")
```

---

## 【内容】
Python 使用缩进表示代码块。

只要看到：

```python
if
for
def
class
try
except
```

后面有：

```python
:
```

下一行就要缩进。

这是 Python 最核心的语法规则之一。

---

# 四十六、43｜常见错误二：True / False / None 写错
错误：

```python
is_active = true
value = null
```

正确：

```python
is_active = True
value = None
```

---

## 【内容】
Python 里面：

```plain
True
False
None
```

首字母必须大写。

写成：

```plain
true
false
null
```

Python 会认为它们是变量名，然后报：

```plain
NameError
```

---

# 四十七、44｜常见错误三：字符串和数字拼接
错误：

```python
age = 30
print("年龄：" + age)
```

正确：

```python
age = 30
print("年龄：" + str(age))
print(f"年龄：{age}")
```

推荐：

```python
print(f"年龄：{age}")
```

---

# 四十八、45｜常见错误四：await 写在普通函数里
错误：

```python
async def request_llm():
    return "AI 回答"


def main():
    result = await request_llm()
    print(result)
```

报错：

```plain
SyntaxError: 'await' outside async function
```

正确：

```python
import asyncio


async def request_llm():
    return "AI 回答"


async def main():
    result = await request_llm()
    print(result)


asyncio.run(main())
```

---

## 【内容】
大家记住一句话：

**await 只能写在 async def 函数里面。**

后面我们写 FastAPI 时，路由函数经常会写：

```python
@app.post("/chat")
async def chat():
    result = await llm_service.chat()
```

因为路由函数本身是：

```python
async def
```

所以里面可以 await。

---

# 四十九、46｜常见错误五：模块导入失败
错误：

```plain
ModuleNotFoundError
```

常见原因：

```plain
1. 文件名写错
2. 路径写错
3. 没有从项目根目录运行
4. 虚拟环境没激活
5. 包没安装
```

解决方式：

```bash
python -m app.basics.09_modules
```

或者确认：

```bash
pwd
```

当前是否在项目根目录。

---

# 五十、47｜本章最终复习
这一章我们快速掌握了 AI 开发需要的 Python 基础。

重点不是背语法，而是建立对应关系：

```plain
JavaScript / TypeScript
        ↓
Python
        ↓
AI 开发场景
```

---

## Python vs TypeScript 核心对照表
| 场景 | TypeScript | Python |
| --- | --- | --- |
| 变量 | `const name = "大伟"` | `name = "大伟"` |
| 字符串模板 | ``你好${name}`` | `f"你好{name}"` |
| 布尔值 | `true / false` | `True / False` |
| 空值 | `null / undefined` | `None` |
| 数组 | `string[]` | `list[str]` |
| 对象 | `Record<string, any>` | `dict[str, Any]` |
| 函数 | `function fn()` | `def fn():` |
| 返回类型 | `: string` | `-> str` |
| 类构造器 | `constructor` | `__init__` |
| this | `this` | `self` |
| 异常 | `try/catch` | `try/except` |
| 异步函数 | `async function` | `async def` |
| 等待异步 | `await` | `await` |
| 遍历数组 | `for...of` | `for...in` |
| 长度 | `.length` | `len()` |
| 添加数组项 | `.push()` | `.append()` |


---

# 五十一、48｜本章课后任务
## 任务一：完成所有基础文件
确认你已经完成：

```plain
app/basics/
├── 01_variables.py
├── 02_collections.py
├── 03_control_flow.py
├── 04_functions.py
├── 05_type_hints.py
├── 06_classes.py
├── 07_pydantic.py
├── 08_errors.py
├── 09_modules.py
├── 10_async.py
├── 11_ai_demo.py
└── 12_stream_demo.py
```

---

## 任务二：自己写一个 User 模型
要求：

```plain
1. 使用 Pydantic
2. 字段包括：id、name、email、is_active
3. email 可以为空
4. 打印 model_dump()
```

参考：

```python
from pydantic import BaseModel


class User(BaseModel):
    id: int
    name: str
    email: str | None = None
    is_active: bool = True


user = User(
    id=1,
    name="大伟"
)

print(user.model_dump())
```

---

## 任务三：模拟一个订单查询 Tool
要求：

```plain
1. 定义函数 query_order
2. 接收 order_id
3. 返回订单信息 dict
4. 使用 Type Hint
```

参考：

```python
def query_order(order_id: str) -> dict[str, str]:
    return {
        "order_id": order_id,
        "status": "已发货",
        "logistics": "顺丰快递"
    }


result = query_order("10001")
print(result)
```

---

## 任务四：把订单 Tool 改成异步
参考：

```python
import asyncio


async def query_order(order_id: str) -> dict[str, str]:
    await asyncio.sleep(1)

    return {
        "order_id": order_id,
        "status": "已发货",
        "logistics": "顺丰快递"
    }


async def main():
    result = await query_order("10001")
    print(result)


asyncio.run(main())
```

---

## 任务五：模拟 Agent 调用 Tool
参考：

```python
import asyncio
from pydantic import BaseModel


class AgentRequest(BaseModel):
    question: str
    order_id: str | None = None


async def query_order(order_id: str) -> dict[str, str]:
    await asyncio.sleep(1)

    return {
        "order_id": order_id,
        "status": "已发货",
        "logistics": "顺丰快递"
    }


async def agent_run(request: AgentRequest) -> str:
    if "订单" in request.question and request.order_id:
        order = await query_order(request.order_id)
        return f"您的订单 {order['order_id']} 当前状态是：{order['status']}，物流：{order['logistics']}"

    return "我暂时无法处理这个问题。"


async def main():
    request = AgentRequest(
        question="帮我查一下订单",
        order_id="10001"
    )

    result = await agent_run(request)
    print(result)


asyncio.run(main())
```

输出：

```plain
您的订单 10001 当前状态是：已发货，物流：顺丰快递
```

---

# 五十二、49｜本章总结内容
## 【最终内容】
好了，到这里，第 03 章我们就讲完了。

这一章内容非常多，但是大家不要慌。

你不需要一下子把所有 Python 语法全部背下来。

你只需要先建立一个非常重要的认知：

**Python 语法不是孤立存在的，它们后面都会直接用在 AI 应用开发里。**

比如：

```plain
变量
= 保存模型参数、用户问题、配置项

List
= 保存 messages、documents、tools

Dict
= 保存 JSON、metadata、tool 参数

函数
= 封装 Tool、封装业务逻辑

Class
= 封装 Service、Provider、Agent

Type Hint
= 定义清晰的数据结构

Pydantic
= 做请求校验和结构化输出

try / except
= 处理模型调用失败

async / await
= 调用 LLM、数据库、Redis、向量库

async generator
= 实现流式输出
```

所以我们这一章不是在学传统 Python。

我们是在学：

**AI 开发真正需要的 Python。**

下一章，我们会继续往前走，进入：

# 第 04 章｜Python 类型系统与 Pydantic 深入
为什么要单独讲 Pydantic？

因为后面我们开发 FastAPI 接口、大模型结构化输出、Agent 状态管理，都会大量依赖 Pydantic。

尤其是：

```plain
请求参数校验
响应结构定义
LLM Structured Output
Tool 参数 Schema
Agent State
```

都会和 Pydantic 强相关。

所以下一章我们会把：

```plain
Type Hint
Pydantic
BaseModel
Field
Validator
嵌套模型
默认值
Optional
Literal
Enum
JSON Schema
```

这些内容系统讲清楚。

学完下一章以后，你再看 FastAPI 和 LangChain 的代码，会明显轻松很多。
