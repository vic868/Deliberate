---
title: "第 18 章补充｜base.py 工具类型说明"
chapter: "18"
source: "第 18 章｜Function Calling 与 Tool Calling -base.py说明.md"
type: obsidian-note
created: 2026-11-22
status: 整理中
tags:
  - course/llm-agent
  - llm
  - tool-calling
  - 类型注解
---

# 第 18 章补充｜base.py 工具类型说明

> [!abstract] 本章重点
>
> - ==ToolCallable 同时兼容同步和异步函数== — 返回值写 BaseModel 或 Awaitable[BaseModel]，两种实现都能注册。
> - ==Callable[..., X] 的 ... 表示参数不限== — 不同工具参数各不相同，用省略号放宽约束。
> - ==工具结果统一是 Pydantic 对象== — 后面序列化、校验、日志都好处理。

> [!note] 大白话
>
> - **Awaitable**：一个可以 await 的对象，异步函数返回的就是它。

> [!info] 导航与来源
> - 原始讲义：[[第 18 章｜Function Calling 与 Tool Calling -base.py说明|打开原始讲义]]
> - [[第 17 章｜Structured Output 结构化输出|上一章｜第 17 章]]
> - [[第 19 章｜项目一：AI Chat 聊天系统|下一章｜第 19 章]]
> - 本章所有内容均保留，未删改原文。

```python
import inspect
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, Field


# 定义一个工具函数的类型
#
# Callable[..., XXX]
# 表示：
#   这是一个可调用对象（通常就是函数）
#   ... 表示函数参数不做限制，可以接收任意参数
#
# 返回值支持两种情况：
# 1. BaseModel
#    普通同步函数直接返回 Pydantic 对象
#
# 2. Awaitable[BaseModel]
#    异步函数返回一个可 await 的对象，
#    await 之后最终得到 BaseModel
#
# 所以 ToolCallable 同时兼容：
#
# def query_order(...) -> BaseModel:
#     ...
#
# async def query_order(...) -> BaseModel:
#     ...
ToolCallable = Callable[..., Awaitable[BaseModel] | BaseModel]


class ToolDefinition(BaseModel):
    """
    ToolDefinition 用来描述一个完整的 Agent Tool。

    一个 Tool 通常包含：
    1. 工具名称
    2. 工具描述
    3. 入参 Schema
    4. 返回值 Schema
    5. 真正执行的 Python 函数
    6. 是否启用
    7. 是否需要人工确认
    """

    # Tool 的唯一名称
    #
    # 例如：
    # query_order
    # query_user
    # search_product
    #
    # Field(...) 中的 ... 表示该字段必填
    name: str = Field(
        ...,
        description="工具名称"
    )

    # Tool 的功能描述
    #
    # 大模型会根据 name 和 description
    # 判断当前用户的问题是否需要调用这个 Tool
    #
    # 例如：
    # "根据订单 ID 查询订单状态"
    description: str = Field(
        ...,
        description="工具描述"
    )

    # Tool 的参数模型
    #
    # 注意这里是：
    # type[BaseModel]
    #
    # 表示这里保存的是一个 Pydantic 模型“类”
    # 而不是模型实例。
    #
    # 例如：
    #
    # class QueryOrderArgs(BaseModel):
    #     order_id: str
    #
    # 这里传：
    #
    # args_schema=QueryOrderArgs
    #
    # 而不是：
    #
    # args_schema=QueryOrderArgs(order_id="10001")
    args_schema: type[BaseModel] = Field(
        ...,
        description="参数 Schema"
    )

    # Tool 的返回结果模型
    #
    # 用来描述这个 Tool 最终应该返回什么数据结构。
    #
    # 例如：
    #
    # class OrderResult(BaseModel):
    #     order_id: str
    #     status: str
    #
    # 创建 Tool 时：
    #
    # result_schema=OrderResult
    #
    # 注意：
    # 当前这段代码只是保存了 result_schema，
    # execute() 中还没有真正使用它校验返回值。
    result_schema: type[BaseModel] = Field(
        ...,
        description="结果 Schema"
    )

    # 真正执行的 Python 工具函数
    #
    # 例如：
    #
    # async def query_order(order_id: str) -> OrderResult:
    #     ...
    #
    # 这里最终：
    #
    # func=query_order
    #
    # ToolCallable 表示：
    # 同步函数、异步函数都可以
    func: ToolCallable = Field(
        ...,
        description="工具函数"
    )

    # 当前 Tool 是否启用
    #
    # 默认 True，表示启用
    #
    # 实际项目中可以用来实现：
    # - Tool 开关
    # - 灰度发布
    # - 权限控制
    # - 动态下线某个 Tool
    enabled: bool = Field(
        default=True,
        description="是否启用"
    )

    # 当前 Tool 是否需要人工确认
    #
    # 默认 False，表示直接执行
    #
    # 例如普通查询：
    # query_order
    # query_weather
    #
    # 一般可以直接执行。
    #
    # 但是一些危险操作，比如：
    # - 删除数据
    # - 退款
    # - 转账
    # - 发邮件
    # - 修改订单
    #
    # 可以设置：
    #
    # require_confirm=True
    #
    # 让 Agent 在执行之前先让用户确认
    require_confirm: bool = Field(
        default=False,
        description="是否需要人工确认"
    )

    class Config:
        # 允许 Pydantic Model 保存普通 Python 类型
        #
        # 因为 func 是一个 Callable，也就是 Python 函数。
        #
        # Pydantic 默认主要处理：
        # str、int、bool、list、dict、BaseModel 等数据类型。
        #
        # 设置 arbitrary_types_allowed=True 后，
        # 就允许保存函数等任意 Python 对象。
        arbitrary_types_allowed = True

    def to_openai_tool(self) -> dict:
        """
        将我们自己的 ToolDefinition
        转换成 OpenAI Function Calling 能识别的 Tool 格式。
        """

        # 将 Pydantic 参数模型转换成 JSON Schema
        #
        # 假设：
        #
        # class QueryOrderArgs(BaseModel):
        #     order_id: str
        #
        # 转换后大概得到：
        #
        # {
        #     "properties": {
        #         "order_id": {
        #             "type": "string"
        #         }
        #     },
        #     "required": ["order_id"],
        #     "type": "object"
        # }
        #
        # 为什么要转换？
        #
        # 因为大模型 API 不认识 Python 的 BaseModel，
        # 但是认识 JSON Schema。
        schema = self.args_schema.model_json_schema()

        # 如果 additionalProperties 不存在，
        # 就设置为 False
        #
        # 等价于：
        #
        # if "additionalProperties" not in schema:
        #     schema["additionalProperties"] = False
        #
        # 作用：
        # 不允许模型随便生成 Schema 中没有定义的额外字段。
        #
        # 假设参数只有：
        #
        # {
        #     "order_id": "10001"
        # }
        #
        # 那么这种参数：
        #
        # {
        #     "order_id": "10001",
        #     "abc": "xxx"
        # }
        #
        # 就属于额外字段。
        schema.setdefault(
            "additionalProperties",
            False
        )

        # 返回 OpenAI Function Calling 标准 Tool 格式
        return {
            # 表示这是一个函数类型的 Tool
            "type": "function",

            "function": {
                # Tool 名字
                #
                # 例如：
                # query_order
                "name": self.name,

                # Tool 描述
                #
                # 大模型会结合 description 判断：
                # 当前用户的问题是否应该调用这个 Tool
                "description": self.description,

                # Tool 参数 JSON Schema
                #
                # 告诉大模型：
                # 调用这个函数时，需要生成哪些参数
                "parameters": schema,
            },
        }

    async def execute(
        self,
        arguments: dict[str, Any]
    ) -> BaseModel:
        """
        统一执行 Tool。

        arguments 是大模型生成的 Tool 参数，例如：

        {
            "order_id": "10001"
        }

        这个方法同时兼容：
        - 同步 Tool
        - 异步 Tool
        """

        # 第一步：
        # 使用 args_schema 对大模型生成的参数进行校验
        #
        # 假设：
        #
        # class QueryOrderArgs(BaseModel):
        #     order_id: str
        #     limit: int = 10
        #
        # 大模型返回：
        #
        # {
        #     "order_id": "10001",
        #     "limit": 20
        # }
        #
        # model_validate 会：
        # 1. 检查字段是否存在
        # 2. 检查类型是否合法
        # 3. 做必要的类型转换
        # 4. 生成 QueryOrderArgs 对象
        #
        # 如果参数不合法，
        # Pydantic 会抛出 ValidationError
        validated_args = self.args_schema.model_validate(
            arguments
        )

        # 判断 self.func 本身是不是 async def 定义的异步函数
        #
        # 例如：
        #
        # async def query_order(order_id: str):
        #     ...
        #
        # inspect.iscoroutinefunction(query_order)
        #
        # 会返回 True
        if inspect.iscoroutinefunction(self.func):

            # validated_args 当前是一个 Pydantic 对象
            #
            # model_dump() 将它转换成普通 dict
            #
            # 例如：
            #
            # QueryOrderArgs(
            #     order_id="10001",
            #     limit=10
            # )
            #
            # 转换为：
            #
            # {
            #     "order_id": "10001",
            #     "limit": 10
            # }
            #
            # 然后 ** 解包成函数关键字参数：
            #
            # self.func(
            #     order_id="10001",
            #     limit=10
            # )
            #
            # 因为这是 async 函数，
            # 所以前面必须 await
            return await self.func(
                **validated_args.model_dump()
            )

        # 如果上面没有进入 if，
        # 说明 self.func 看起来是普通同步函数。
        #
        # 先正常调用一次。
        result = self.func(
            **validated_args.model_dump()
        )

        # 为什么这里还要判断一次 isawaitable？
        #
        # 因为：
        # 有些函数本身虽然不是 async def，
        # 但是它返回的结果仍然可能是一个 Awaitable。
        #
        # 例如：
        #
        # def query_order():
        #     return some_async_function()
        #
        # query_order 本身不是 async def，
        # 但是返回的是 coroutine。
        #
        # 所以还要检查返回值能不能 await。
        if inspect.isawaitable(result):

            # 如果返回值可以 await，
            # 就等待异步任务执行完成，
            # 返回最终结果。
            return await result

        # 如果既不是 async 函数，
        # 返回值也不是 Awaitable，
        # 那它就是普通同步函数的结果。
        #
        # 直接返回即可。
        return result
```

---

> [!success] 一句话带走
> ==这份说明解释了工具注册表为什么能同时吃同步和异步工具。==

> [!quote] 关于本文档
> 由原始讲义 `第 18 章｜Function Calling 与 Tool Calling -base.py说明.md` 转换为 Obsidian 风格笔记；原文完整保留，未做任何删改。
> 整理日期：2026-11-22
