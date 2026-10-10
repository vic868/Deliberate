---
title: AI 工具总览
tags: [AI, 工具, 索引, MOC]
status: 进行中
created: 2026-10-10
---

# 🧰 AI 工具总览

> `1-AI 工具/` 的**入口页**。这里收录「选什么工具、要花多少钱、免费额度怎么用」。
> 与其他规划页的分工：[[技术栈地图]] 讲**技术栈**，[[01-学习路径总览]] 讲**路线**，本目录讲**买什么/用什么**。

---

## 本目录内容

| 笔记 | 回答什么问题 |
|---|---|
| **[[AI编程工具与订阅总览]]** | AI 编程工具（Cursor / Claude Code / Copilot / Windsurf / Antigravity / CodeBuddy / Qoder / Trae）**价格、额度、怎么选** |
| **[[AI对话助手与API价格]]** | 对话助手订阅、**API 按量计费的省钱方法**、免费额度清单、支付与网络问题 |

---

## 三句话结论

> [!important] 如果你只记三件事
> 1. **编程与对话共用同一个 $20 订阅**，不要为每个用途各买一份。
> 2. **求职期一律月付**——这个领域半年就可能调价或换产品线（Google 半年内调了两次）。
> 3. **API 只按量、只用于开发演示**；省钱全靠**模型分级 + prompt 缓存 + RAG 召回截断**。

---

## 已核实的价格速查（2026-10-10）

> [!warning] 价格变动快，下单前**必须**查官网
> 以下为撰写当日从官方页面核实的数据。**这个领域几个月就调一次**，请以官网为准。

### 编程工具

| 工具 | 免费 | 入门付费 | 数据来源 |
|---|---|---|---|
| **Cursor** | Hobby 免费 | **Pro $20/月** · Pro+ $60 · Ultra $200 | [官方](https://cursor.com/help/account-and-billing/pricing.md) |
| **GitHub Copilot** | Free（2000 补全/月）· **Student 免费 PRO** | **Pro $10/月** · Pro+ $39 · Max $100 | [官方](https://docs.github.com/en/copilot/get-started/plans.md) |
| **Claude Code** | ❌ | 随 Claude 订阅；**企业实测 $150–250/人/月** | [官方](https://code.claude.com/docs/en/costs.md) |
| **Windsurf** | Free 25 额度/月 · **2 周 Pro 试用** | Pro 500 额度（附加 $10/250） | [官方](https://docs.windsurf.com/zh/windsurf/accounts/usage) |
| **Devin** | Free | **Pro $20/月** · Max $200 | [官方](https://devin.ai/pricing) |
| **Google Antigravity** | **Individual 免费**（无限 Tab） | 随 Google AI：**$19.99 / $99.99 / $199.99** | [官方](https://antigravity.google/blog/changes-to-antigravity-plans) |
| **腾讯 CodeBuddy** | Free 100 积分 + 活跃 30/天 | **Pro $10/月**（年付 $8/月） | [官方](https://www.codebuddy.ai/docs/zh/ide/Account/pricing) |
| **Qoder CN**（原通义灵码） | 社区版免费 | 见官方公告 | [公告](https://cn.aliyun.com/notice/118264) |
| **Trae**（字节） | 有免费额度 | **按 Token 计费**（已改） | [报道](https://m.ithome.com/html/0923234.htm) |

### 三个"很多教程已过时"的坑

| 过时说法 | 现状 |
|---|---|
| "Gemini CLI 免费额度很大，推荐" | ⚠️ **2026-06-18 起 Gemini CLI 停止服务免费/个人 Google 账号**，由 **Antigravity CLI** 取代（[来源](https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/)） |
| "通义灵码免费" | 已更名 **Qoder CN**，计费模式有调整 |
| "Trae 按次数收费" | 已改为**按 Token 计费** |

---

## 给你的推荐配置

> [!tip] 脱产求职期（现金流优先）
> | 角色 | 选择 | 月成本 |
> |---|---|---|
> | 主力 | **Claude Code** 或 **Cursor Pro** | $20 |
> | 补位（国内直连） | **CodeBuddy Free** / **Qoder CN 免费版** | ¥0 |
> | 评估 | Cursor Hobby · Windsurf 试用 · CodeBuddy 7 天试用 | ¥0 |
> | **合计** | | **$0–20/月** |
>
> 有**学生身份**的话：**Copilot Student 直接免费拿完整 Pro**，这是最值的一项。
> 详细理由见 [[AI编程工具与订阅总览]] §1 与 §5 决策图。

---

## 关联

- [[README|AI 学习规划]] · [[技术栈地图]] · [[01-学习路径总览]] · [[每日进度]]
- 学习阶段用法：[[02-基础阶段]] · [[03-Java开发阶段]] · [[04-高级架构阶段]] · [[05-项目与求职阶段]]

> [!question] 待补充
> - [ ] 各家对话助手**当前档位与额度**（变动快，需逐家核实）
> - [ ] 国产模型编码/Agent 能力横向对比
> - [ ] 自建 RAG 的**实际月度账单**记录
