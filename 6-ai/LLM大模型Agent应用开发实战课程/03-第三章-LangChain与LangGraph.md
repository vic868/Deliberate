---
title: 第3章 LangChain & LangGraph
tags: [AI, LLM, 课程笔记, 框架]
status: 骨架 / 正文待精读
source: 语雀《LLM大模型Agent应用开发实战课程 VVVIP（持续加餐中）》
yuque: https://www.yuque.com/sohucw/irt1ar/ocqtyiygyhq4iz4q
chapter: 3
created: 2026-11-18
---

# 📘 第3章：LangChain & LangGraph

> [!abstract] 原文开篇导语（已核对）
> 从手写 API 调用升级到工程化 AI 应用框架。原文一句话分工：**LangChain 解决「怎么调用模型」，LangGraph 解决「怎么编排 AI 流程」**。第一章直接用 fetch 调 API 没问题，但项目一复杂就会遇到重复造轮子的痛点。

> [!tip] 一句话理解
> LangChain 把「拼提示词、调模型、解析结果」标准化；LangGraph 再把多步流程画成一张可循环的图。

## 🗺 本章结构（照录原文目录锚点）

- 第三章：LangChain + LangGraph
- 3.1 为什么需要这两个框架
- 3.2 LangChain.js 核心用法
- 3.2.1 模型初始化
- 3.2.2 四种调用方式
- 3.2.3 多轮对话
- 3.3 ChatPromptTemplate 提示词模板
- 3.3.1 基础用法
- 3.3.2 模板复用
- 3.3.3 partial 预填变量
- 3.4 LCEL 链式调用
- 3.4.1 最简单的链
- 3.4.2 顺序链：多步处理
- 3.4.3 并行链：同时执行多个任务
- 3.4.4 链的健壮性配置
- 3.5 会话记忆管理
- 3.5.1 RunnableWithMessageHistory
- 3.5.2 滑动窗口：防止上下文超长
- 3.6 LangGraph 核心概念
- 3.6.1 StateGraph 基础
- 3.6.2 多节点顺序图
- 3.6.3 条件路由：动态决定流程
- 3.6.4 带循环的图：生成 → 检查 → 修正
- 3.7 完整项目：Vue3 + LangGraph 聊天应用
- 后端架构
- 关键代码：带记忆的对话图
- 关键代码：流式 SSE 接口
- 关键代码：Vue3 流式接收
- 3.8 选型参考
- 3.9 本章小结

## 🧩 核心概念速记

| 概念 | 一句通俗解释 |
| --- | --- |
| LCEL | 用管道把「提示词 → 模型 → 解析」串成一条链，每一步都可替换 |
| ChatPromptTemplate | 把提示词做成带变量的模板，不用每次手动拼字符串 |
| RunnableWithMessageHistory | 自动带上前几轮对话，不用自己维护历史数组 |
| 滑动窗口 | 只保留最近 N 条消息，防止历史越积越长把上下文撑爆 |
| StateGraph | 把流程画成「节点 + 边」的图，状态在节点之间流转，还能绕回来形成循环 |

> [!info] 关于上表
> 表格是**助学注解**（依据章节标题写的通俗解释），不是原文逐字内容。原文正文全文尚未抓取，细节见下方待精读清单。


## 🔗 关联与定位

- **上一篇**：[[02-第二章-提示词工程]]
- **下一篇**：[[04-第四章-FunctionCall]]
- [[技术栈地图]] —— 对照 Java / Spring AI 侧的等价能力
- 配套实操：[[13-实战与视频模块索引]] 的 LangGraph 五讲
- 全库导航：[[00-课程总览]] · 实战与源码：[[13-实战与视频模块索引]]

## 📌 原文与源码

- 原文：[语雀 · 第3章](https://www.yuque.com/sohucw/irt1ar/ocqtyiygyhq4iz4q)
- 本章源码：[语雀](https://www.yuque.com/sohucw/irt1ar/quqz4bgdlfgh2zgd)

## ✅ 待精读清单

> [!todo] 正文全文待补
> - [ ] 补齐本章各小节的讲解、代码示例与图表
> - [ ] 把「核心概念速记」升级为带原文依据的完整笔记
> - [ ] 对照自己的技术栈补一列「Java / Spring AI 侧等价实现」
>
> 补全方式见 [[00-课程总览]] 的「如何补全全文」（导出整库 Markdown / 分批精读）。

---
回到 [[00-课程总览]]
