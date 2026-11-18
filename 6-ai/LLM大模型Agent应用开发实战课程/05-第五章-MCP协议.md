---
title: 第5章 MCP 协议（Model Context Protocol）
tags: [AI, LLM, 课程笔记, 协议]
status: 骨架 / 正文待精读
source: 语雀《LLM大模型Agent应用开发实战课程 VVVIP（持续加餐中）》
yuque: https://www.yuque.com/sohucw/irt1ar/dvzlbqrgyq0rm1th
chapter: 5
created: 2026-11-18
---

# 📘 第5章：MCP 协议（Model Context Protocol）

> [!abstract] 原文开篇导语（已核对）
> MCP 是 Anthropic 在 2024 年底发布的开放协议，目标是把 AI 工具调用标准化。原文用一句话区分第四章与本章：**Function Call 是「你自己写工具、自己用」，MCP 是「按标准写工具，所有 AI 应用都能用」**。没有 MCP 之前，每个 AI 应用都要自己写一遍工具调用逻辑。

> [!tip] 一句话理解
> 把工具调用做成统一插头：按 MCP 写一次，Claude Desktop、LangChain、自家应用都能直接接。

## 🗺 本章结构（照录原文目录锚点）

- 5.1 MCP 解决什么问题
- MCP 的三种原语
- 两种传输方式
- 5.2 写一个 MCP Server
- 5.2.1 stdio 传输（本地工具）
- 5.2.2 HTTP + SSE 传输（远程服务）
- 5.3 写一个 MCP Client
- 5.3.1 连接 stdio Server
- 5.3.2 连接 SSE Server
- 5.4 把 MCP 工具接入 LangChain.js
- 5.5 在 Express 应用里管理多个 MCP Server
- 5.6 Vue3 展示 MCP 工具列表
- React 版本
- 5.7 配置到 Claude Desktop
- 5.8 MCP vs Function Call 的关系
- 5.9 本章小结

## 🧩 核心概念速记

| 概念 | 一句通俗解释 |
| --- | --- |
| MCP | 工具调用的统一协议，相当于 AI 世界的 USB 接口标准 |
| 三种原语 | Tools（能做事）/ Resources（能提供数据）/ Prompts（能提供模板） |
| stdio 传输 | 工具作为本地子进程运行，通过标准输入输出通信 |
| HTTP + SSE 传输 | 工具跑在远程服务上，用 SSE 把事件推给客户端 |
| MCP vs Function Call | 不冲突：MCP 定义工具怎么被描述和发现，Function Call 是模型决定要调哪个工具的能力 |

> [!info] 关于上表
> 表格是**助学注解**（依据章节标题写的通俗解释），不是原文逐字内容。原文正文全文尚未抓取，细节见下方待精读清单。


## 🔗 关联与定位

- **上一篇**：[[04-第四章-FunctionCall]]
- **下一篇**：[[06-第六章-RAG]]
- [[技术栈地图]] —— 对照 Java / Spring AI 主线
- 全库导航：[[00-课程总览]] · 实战与源码：[[13-实战与视频模块索引]]

## 📌 原文与源码

- 原文：[语雀 · 第5章](https://www.yuque.com/sohucw/irt1ar/dvzlbqrgyq0rm1th)
- 本章源码：[语雀](https://www.yuque.com/sohucw/irt1ar/lh8ntdf8tplt9gr1)

## ✅ 待精读清单

> [!todo] 正文全文待补
> - [ ] 补齐本章各小节的讲解、代码示例与图表
> - [ ] 把「核心概念速记」升级为带原文依据的完整笔记
> - [ ] 对照自己的技术栈补一列「Java / Spring AI 侧等价实现」
>
> 补全方式见 [[00-课程总览]] 的「如何补全全文」（导出整库 Markdown / 分批精读）。

---
回到 [[00-课程总览]]
