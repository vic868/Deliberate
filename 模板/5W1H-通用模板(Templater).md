<%*
// ============ 交互：插入时弹窗问你 ============
// 需要默认值不弹窗的话，把下面三行的 tp.system.suggester / prompt 换成常量即可
const title   = await tp.system.prompt("📌 标题（留空 = 用文件名）", "", false);
const type    = await tp.system.suggester(["需求","问题","决策","复盘","学习"], ["需求","问题","决策","复盘","学习"], false, "🏷️ 类型");
const prio    = await tp.system.suggester(["P0","P1","P2","P3"], ["P0","P1","P2","P3"], false, "⚡ 优先级");
const owner   = await tp.system.prompt("🧑 负责人（直接写名字，会自动变双链）", "", false);
const loc     = await tp.system.prompt("📍 涉及系统 / 环境（可留空）", "", false);

// ============ 日期工具 ============
const weekZh = ['日','一','二','三','四','五','六'][Number(tp.date.now('E')) % 7];
const today  = tp.date.now("YYYY-MM-DD");
const deadline = tp.date.now("YYYY-MM-DD", 7);
const noteTitle = title || tp.file.title;
const ownerLink = owner ? `"[[${owner}]]"` : '""';

// 改名：只在「新建笔记」场景改名；对模板文件本身执行时不改名
const isTemplateFile = tp.file.path(true).startsWith("模板/");
const targetFile = tp.file.title;
if (!isTemplateFile) {
  if (!title && /^Untitled/i.test(targetFile)) {
    await tp.file.rename(`${today} 5W1H`);
  } else if (title && title !== targetFile) {
    await tp.file.rename(title);
  }
}
-%>
---
title: "<% noteTitle %>"
aliases: []
tags: [5W1H, 待归类]
type: <% type %>
status: 进行中        # 草稿 / 进行中 / 待确认 / 已完成 / 已归档
priority: <% prio %>
created: <% today %>
updated: <% today %>
time: <% tp.date.now("HH:mm") %>
weekday: 星期<% weekZh %>
location: "<% loc %>"
owner: <% ownerLink %>
participants: []      # 别人：[[张三]], [[李四]]
stakeholders: []      # 决策者 / 使用者 / 受影响方
deadline: <% deadline %>   # 默认 7 天后，按需改
milestones: []        # [ {日期, 事项} ]
cost: 待评估          # 人力 / 预算 / 资源投入（How much）
notes: null           # 关联目标 [[ ]]
source: []
---

# <% noteTitle %>

> [!abstract] 一句话概述
> ______（30 字内说清"谁为了让谁做什么、在什么时候完成一件什么事"）

> [!tip] 使用说明
> 1. 先看 **基础信息**，再按 **Why → What → Who → When → Where → How → How much** 填写；
> 2. 不确定的项写 `待确认 + 找谁确认`，不要留空；
> 3. 填完看底部 **自检清单**，全部打勾才算合格。

---

## 🗂️ 基础信息

| 项目 | 内容 |
|---|---|
| 📌 标题 | <% noteTitle %> |
| 🏷️ 类型 | <% type %> |
| ⚡ 优先级 | <% prio %> |
| 🧑 负责人（Owner） | <% owner || "______" %> |
| 👥 参与人 | ______ |
| 🎯 关键决策人 | ______ |
| 📅 创建时间 | <% today %> <% tp.date.now("HH:mm") %>（星期<% weekZh %>） |
| ⏰ 截止时间 | <% deadline %> |
| 📍 涉及范围 | <% loc || "______" %> |
| 💰 预估投入 | 人天：______ ｜ 预算：______ |
| 🔗 关联 | 目标：______ ｜ 上游：______ ｜ 下游：______ |

---

## 🧭 5W1H 分析

### 1️⃣ Why · 为什么做
> 回答"不做会怎样"，把动机和代价说清楚。

- **动机 / 背景**：
- **不做的后果**：
- **核心痛点**：
- **优先级依据**：
- ✅ 判断标准：这栏能让不了解背景的人愿意为此投资源。

### 2️⃣ What · 做什么
- **目标（可衡量）**：
- **交付物清单**：
  - [ ] 
- **验收标准（DoD）**：
- **明确不做的（Out of Scope）**：
- **成功指标（KPI）**：

### 3️⃣ Who · 谁

| 角色 | 姓名 | 职责 / 责任边界 | RACI |
|---|---|---|---|
| 发起人 |  |  | A |
| 负责人 | <% owner || "" %> |  | R |
| 执行人 |  |  | R |
| 审核 / 决策 |  |  | C |
| 知情方 |  |  | I |

- **受影响的人 / 团队**：
- **外部依赖方**：

### 4️⃣ When · 何时

| 阶段 | 时间点 | 产出 | 状态 |
|---|---|---|---|
| 启动 | <% today %> |  | ✅ |
| 关键里程碑 |  |  | ⬜ |
| 联调 / 验收 |  |  | ⬜ |
| 上线 / 交付 | <% deadline %> |  | ⬜ |

- **硬约束（不可变的外部门槛）**：
- **缓冲时间**：

### 5️⃣ Where · 在哪
- **业务场景 / 流程节点**：
- **系统 / 服务 / 模块**：<% loc || "______" %>
- **环境**：开发 / 测试 / 预发 / 生产
- **地域 / 市场 / 渠道**：
- **文档 / 代码位置**：`______`

### 6️⃣ How · 怎么做
- **整体方案 / 思路**：
- **关键步骤**：
  1. 
- **依赖与前置条件**：
- **风险与应对**：

| 风险 | 可能性 | 影响 | 应对措施 | 责任人 |
|---|---|---|---|---|
|  | 高/中/低 | 高/中/低 |  |  |

### 7️⃣ How much · 多少
- **人力投入**：______ 人天（______ 人 × ______ 天）
- **资金 / 资源**：______
- **产出与收益**：______
- **ROI 判断**：值得 / 不值得 / 需再评估 —— 理由：______

---

## 🧩 结论与下一步

> [!success] 结论
> ______

| # | 行动项 | 负责人 | 截止时间 | 状态 |
|---|---|---|---|---|
| 1 |  |  |  | ⬜ |

---

## ✅ 自检清单

- [ ] Why 能说清"不做会怎样"
- [ ] What 有边界 + 有验收标准 + 有明确不做的部分
- [ ] Who 每项职责落实到具体一个人，没有"大家一起"
- [ ] When 有时间点，且与相关方确认过
- [ ] Where 说清了系统 / 环境 / 场景
- [ ] How 有步骤、有风险应对
- [ ] How much 有估算，且投入与收益能对上

---

## 🔗 关联笔记

- 方法论：[[02-结构化思维-5W1H与任务拆解]]
- 上游：
- 下游：
<% tp.file.cursor(1) %>
