---
title: 第7章 Agent 智能体
tags: [AI, LLM, 课程笔记, Agent]
status: 骨架 / 正文待精读
source: 语雀《LLM大模型Agent应用开发实战课程 VVVIP（持续加餐中）》
yuque: https://www.yuque.com/sohucw/irt1ar/fm5yds7r3qiig8et
chapter: 7
created: 2026-11-18
---

# 📘 第7章：Agent 智能体

> [!abstract] 原文开篇导语（已核对）
> Agent 和普通的「调用模型回答问题」有本质区别：Agent 能自主规划步骤、调用工具、观察结果、调整策略，持续执行直到完成复杂任务。普通 LLM 调用是单次问答、一问一答就结束；Agent 是一个持续执行的循环，原文把它叫做 **ReAct**：思考 → 行动 → 观察 → 再思考。

> [!tip] 一句话理解
> 普通调用像问一句答一句，Agent 像派了个实习生：自己拆活、自己动手、看结果再改，直到把事办完。

## 🗺 本章结构（照录原文目录锚点）

- 7.1 Agent 是什么
- Agent vs Function Call
- 7.2 ReAct Agent 实现
- 7.2.1 工具定义
- 7.2.2 构建 ReAct Agent 图
- 7.2.3 执行过程示例
- 7.3 自我反思（Reflection）
- 7.4 多 Agent 协作（Supervisor 模式）
- 什么时候用多 Agent
- 7.5 流式推送执行步骤
- Vue3 前端接收步骤状态
- React 版本
- 7.6 Agent 评估
- 7.7 Agent 的几个工程陷阱
- 7.8 本章小结

## 🧩 核心概念速记

| 概念 | 一句通俗解释 |
| --- | --- |
| Agent | 能自己拆任务、调工具、看反馈再调整，直到完成目标的程序 |
| ReAct | 「想一步 → 做一步 → 看一眼 → 再想」的循环，是 Agent 的基本心跳 |
| Reflection | 让模型回头检查自己上一轮的答案，挑毛病再改一版 |
| Supervisor 模式 | 一个主管 Agent 负责派活和汇总，几个专职 Agent 各干一块 |
| Agent 评估 | 不只看最终答案对不对，还要看步骤是否合理、有没有绕远路或死循环 |

> [!info] 关于上表
> 表格是**助学注解**（依据章节标题写的通俗解释），不是原文逐字内容。原文正文全文尚未抓取，细节见下方待精读清单。


## 🔗 关联与定位

- **上一篇**：[[06-第六章-RAG]]
- **下一篇**：[[08-第八章-Workflow工作流]]
- [[技术栈地图]] 的 Agent / ReAct / MCP 一节
- 全库导航：[[00-课程总览]] · 实战与源码：[[13-实战与视频模块索引]]

## 📌 原文与源码

- 原文：[语雀 · 第7章](https://www.yuque.com/sohucw/irt1ar/fm5yds7r3qiig8et)
- 本章源码：[语雀](https://www.yuque.com/sohucw/irt1ar/fyeg65gg6upommhs)

## ✅ 待精读清单

> [!todo] 正文全文待补
> - [ ] 补齐本章各小节的讲解、代码示例与图表
> - [ ] 把「核心概念速记」升级为带原文依据的完整笔记
> - [ ] 对照自己的技术栈补一列「Java / Spring AI 侧等价实现」
>
> 补全方式见 [[00-课程总览]] 的「如何补全全文」（导出整库 Markdown / 分批精读）。

---
回到 [[00-课程总览]]
