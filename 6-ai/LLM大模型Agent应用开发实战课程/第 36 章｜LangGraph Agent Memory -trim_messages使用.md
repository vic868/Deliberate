```python
trimmed_messages = trim_messages(
    state["messages"],
    strategy="last",
    token_counter=count_tokens_approximately,
    max_tokens=128,
    start_on="human",
    end_on=("ai", "human"),
)
```

**从 **`**state["messages"]**`** 里面，从后往前保留最近的消息，控制消息总量大约不超过 128 tokens，同时保证消息从 Human 开始，并且以 AI 或 Human 消息结束。**



---

## 1. `state["messages"]`
这是 LangGraph State 里的聊天历史。

比如：

```plain
state["messages"]
```

可能是：

```plain
Human: 你好
AI: 你好，有什么可以帮你？
Human: 帮我查订单
AI: 好的，请提供订单号
Human: 10001
AI: 正在查询
```

也就是：

```plain
[
    HumanMessage(...),
    AIMessage(...),
    HumanMessage(...),
    AIMessage(...),
    HumanMessage(...),
    AIMessage(...),
]
```

---

# 2. `strategy="last"`
这个非常重要。

```plain
strategy="last"
```

意思是：

**优先保留最后面的消息，也就是最近的聊天记录。**

例如原来有：

```plain
① Human：你好
② AI：你好
③ Human：帮我查订单
④ AI：好的
⑤ Human：订单号10001
⑥ AI：查询中
```

如果长度超过限制：

```plain
max_tokens=128
```

它会优先保留：

```plain
③ Human：帮我查订单
④ AI：好的
⑤ Human：订单号10001
⑥ AI：查询中
```

而不是从第一条开始保留。

所以：

```plain
strategy="last"
```

可以记成：

**我要最近的上下文，不要太久以前的聊天记录。**

---

# 3. `token_counter=count_tokens_approximately`
这个参数是：

**告诉 **`**trim_messages**`** 怎么估算消息占用了多少 Token。**

这里使用：

```plain
count_tokens_approximately
```

它是 LangChain 提供的一个**近似 Token 计算函数**。

为什么需要它？

因为你设置了：

```plain
max_tokens=128
```

程序需要知道：

```plain
当前消息用了多少 Token？
```

然后决定：

```plain
哪些消息留下？
哪些消息裁掉？
```

这里并不是调用大模型真正计算 Token，而是进行**近似估算**。

所以可以理解为：

```plain
token_counter=count_tokens_approximately
```

就是：

**按照这个规则估算聊天记录的 Token 数量。**

---

# 4. `max_tokens=128`
这个就比较直观：

```plain
max_tokens=128
```

表示：

**裁剪后的消息尽量控制在 128 tokens 以内。**

比如：

```plain
消息 A → 30 tokens
消息 B → 25 tokens
消息 C → 40 tokens
消息 D → 35 tokens
```

总共：

```plain
30 + 25 + 40 + 35 = 130
```

超过：

```plain
128
```

那么就需要继续裁剪。

所以：

```plain
max_tokens=128
```

相当于给聊天历史设置了一个**上下文预算**。

---

# 5. `start_on="human"`
这个参数特别容易忽略。

```plain
start_on="human"
```

意思是：

**裁剪完成之后，消息列表应该从 Human 消息开始。**

例如原始消息：

```plain
AI：你好
Human：帮我查订单
AI：好的
Human：10001
```

如果直接裁剪，可能得到：

```plain
AI：好的
Human：10001
```

但这时候第一条是 AI。

通过：

```plain
start_on="human"
```

就会尽量调整为：

```plain
Human：10001
```

也就是说：

```plain
start_on="human"
```

要求：

**消息序列的开头最好是用户消息。**

---

# 6. `end_on=("ai", "human")`
这个表示：

```plain
end_on=("ai", "human")
```

允许消息序列：

**以 AI 或 Human 消息结束。**

也就是说最后一条可以是：

```plain
AI
```

也可以是：

```plain
Human
```

例如：

```plain
Human
AI
Human
AI
```

合法。

```plain
Human
AI
Human
```

也合法。

---

# 7. 为什么需要 `start_on` 和 `end_on`？
因为聊天消息是有结构的。

正常对话：

```plain
Human
AI
Human
AI
Human
AI
```

如果你随便从中间截：

```plain
AI
Human
AI
```

虽然技术上可能是消息列表，但对于模型来说，上下文结构可能不够自然。

所以：

```plain
start_on="human"
```

要求：

```plain
Human → ...
```

而：

```plain
end_on=("ai", "human")
```

允许：

```plain
... → AI
```

或者：

```plain
... → Human
```

从而让裁剪后的消息结构更加合理。

---

# 8. 解释
你的代码：

```python
trimmed_messages = trim_messages(
    state["messages"],
    strategy="last",
    token_counter=count_tokens_approximately,
    max_tokens=128,
    start_on="human",
    end_on=("ai", "human"),
)
```

**从当前 LangGraph 的聊天历史 **`**state["messages"]**`** 中，优先保留最近的消息，使用近似 Token 计算方式，把上下文控制在约 128 tokens，并且保证裁剪后的消息尽量从 Human 消息开始，最后一条可以是 AI 或 Human 消息。**

最终结果放到：

```plain
trimmed_messages
```

里面。

---

## 9. 放到 Agent 里面就更好理解了
例如你的 Agent 已经聊了 50 轮：

```plain
Human → AI
Human → AI
Human → AI
...
Human → AI
```

如果把全部 50 轮都丢给大模型：

```plain
50轮历史
   ↓
LLM
```

会有几个问题：

+  Token 消耗越来越大 
+  请求成本越来越高 
+  上下文越来越长 
+  模型注意力被大量历史信息占用 
+  接近上下文窗口限制 

所以可以：

```plain
50轮历史
   ↓
trim_messages()
   ↓
最近几轮
   ↓
LLM
```

这就是一个非常典型的：

**短期记忆 / 对话上下文裁剪策略。**

---

### 你可以记住这 6 个参数
```plain
state["messages"]
        ↓
我要裁剪谁？

strategy="last"
        ↓
保留最近的

token_counter=count_tokens_approximately
        ↓
怎么估算 Token？

max_tokens=128
        ↓
最多保留多少？

start_on="human"
        ↓
从谁开始？

end_on=("ai", "human")
        ↓
允许谁结束？
```

所以这段代码本质上就是：

**“从 LangGraph 的历史消息里，按照 Token 限制，截取最近的一段对话上下文给 Agent 使用。”**
