---
title: LinkedIn Profile · 英文文案底稿
tags: [面试, 简历, LinkedIn, 英文, 待填]
status: 草稿
---

# LinkedIn Profile 英文底稿（待事实字段）

> 依据：[[01-酒店送物机器人-项目描述]]、[[02-回收站点积分平台-项目描述]]、[[03-SpringAIAlibaba-RAG-Demo-答辩准备]]
> 口径：只写真实做过的；AI 部分写"个人实践的 RAG Demo + 结合现有微服务架构的设计能力"，不写"落地"

`[方括号]` = 待你补的事实，其余可直接用。

---

## 1. Headline（≤220 字符）

> Java Backend Engineer | Spring Cloud · Netty/MQTT · High-concurrency IoT Platforms | RAG & LLM Application Engineering (Spring AI)

备选（更偏 AI 方向）：

> Backend Engineer (Java) | IoT Device Connectivity & High-concurrency Transaction Systems | Building LLM/RAG capabilities with Spring AI

---

## 2. About（约 1500 字符内）

I build backend systems for IoT and transaction-heavy platforms — the kind where a lost message means a robot never arrives, or a race condition means points get minted out of thin air.

Over the past `[N]` years I have led backend design and core-module development on two production systems: a hotel/building delivery-robot platform and a community recycling + loyalty-points platform. Both are real-time, device-connected, and unforgiving about consistency.

What I focus on:

• **Long-lived device connections at scale** — Netty + MQTT gateways with heartbeat keep-alive, reconnect storms handled by exponential backoff with jitter, stateless gateway nodes so any node can take a device after a restart.

• **State machines and idempotency over hope** — delivery tasks and reward events flow through explicit state machines with idempotency keys; duplicate device reports are de-duplicated before they ever affect a balance.

• **Money-grade consistency on points** — three-way point accounts (available / frozen / lifetime), atomic deduction via Redis + Lua, unique-key idempotency, and a T+1 reconciliation job between device ledgers and platform ledgers as the final line of defense.

• **Concurrency under peak load** — Redis pre-validation, async order placement through MQ, and idempotent consumers; core APIs kept within tight P99 budgets.

On the AI side, I have gone past the "read the docs" stage: I built a working enterprise-knowledge-base **RAG demo on Spring AI Alibaba** (chunking, embedding, vector store, retrieval + rerank, citation-grounded answers) and I spend real time on the engineering questions that matter in production — document-level permission isolation in retrieval, hallucination control via mandatory citations, and cost/latency trade-offs between small and large models. I am looking for roles where this meets the backend systems I already know how to run.

Tech I reach for: Java, Spring Boot / Spring Cloud, Netty, MQTT, MySQL, Redis, Kafka/RocketMQ, Kubernetes, plus Spring AI / LangChain for LLM applications.

---

## 3. Experience（按真实公司拆段）

### `[公司名]` — `[职位，如 Senior Backend Engineer / Backend Lead]`
`[城市]` · `[YYYY.MM] – [YYYY.MM 或 Present]`

Hotel / building delivery-robot platform — backend owner for core modules.

- Designed and built the robot connectivity gateway on **Netty + MQTT**, supporting `[N]` concurrent devices with heartbeat keep-alive, exponential-backoff reconnection and offline task recovery.
- Implemented **multi-robot dispatch** with a task state machine: Redis atomic claims (Lua / SETNX) prevent two robots from taking the same task; nearest-plus-load balancing for assignment; failed robots release tasks for reassignment.
- Integrated hotel **PMS and elevator-control** third parties (signed open API with timestamp anti-replay, idempotency keys, async callbacks with retry, T+1 reconciliation), enabling automatic elevator rides and status write-back.
- Pushed live robot/task state to clients over **WebSocket**, with report-rate throttling and change-only updates to keep the push fan-out bounded.
- Absorbed check-in peaks with **Redis pre-validation + MQ async order placement**, keeping core APIs at P99 `[X] ms` and delivery success rate at `[X]%`.

### `[公司名]` — `[职位]`
`[城市]` · `[YYYY.MM] – [YYYY.MM 或 Present]`

Community recycling + loyalty-points platform — backend owner for accounts, points, device ingestion and settlement.

- Designed the **points account system** (available / frozen / lifetime ledgers) with **Redis + Lua atomic deduction** and unique-key idempotency, achieving zero over-issuance under concurrent redemptions.
- Ingested smart recycling bins and weighing devices over **MQTT**, with device-level de-duplication (device ID + timestamp + sequence), abnormal-weight rejection and ordered replay of offline back-fill.
- Built **T+1 reconciliation** between device ledgers and platform ledgers, classifying discrepancies into auto-correction vs. manual ticket flows, keeping the variance rate under `[X]%`.
- Implemented **anti-abuse rules** (per-user/device/IP rate limits, anomalous weight detection, blacklist) with configurable thresholds — blocking `[N]` abnormal submissions per month.
- Delivered point expiry via **delayed messages + scheduled fallback**, and a **Redis ZSet** leaderboard serving million-scale rankings in milliseconds.
- Enforced multi-tenant data isolation by injecting site/tenant conditions through a MyBatis interceptor, so site admins only ever see their own data.

### Personal project — RAG Knowledge Base on Spring AI Alibaba
`[YYYY.MM] – [YYYY.MM]`

- Built an end-to-end enterprise knowledge-base RAG demo: document ingestion, chunking with `[chunk size / overlap]`, embedding, vector store, retrieval with `[top-K]`, and citation-grounded generation.
- Designed document-level permission filtering at retrieval time (metadata-scoped queries) so answers never cross tenant boundaries.
- Evaluated retrieval quality with a labeled `[N]`-question set, reaching `[X]%` hit rate; added hybrid retrieval (vector + keyword) with rerank for domain-specific terms.
- Analyzed production gaps: prompt-injection surfaces, cost per query, streaming latency and fallback paths when retrieval confidence is low.

---

## 4. Skills（LinkedIn 技能区块，按顺序加）

Java · Spring Boot · Spring Cloud · Netty · MQTT · MySQL · Redis · Apache Kafka · RocketMQ · Kubernetes · Docker · Distributed Systems · High Concurrency · Idempotency · System Design · Microservices · Spring AI · RAG (Retrieval-Augmented Generation) · LLM Application Development · Vector Databases

---

## 5. Education

`[学校]` — `[专业]`, `[学位]` · `[YYYY] – [YYYY]`

---

## 6. 待你确认的 4 个口径

1. `[N]` 年经验怎么算（写入 About 第一段）
2. 两段经历的时间线是否重叠 / 是否都在职
3. 数字要不要填真值（LinkedIn 上被追问的概率低于简历，但仍建议不编）
4. 目标岗位偏「Java 后端」还是「AI 应用工程」——决定 Headline 用第 1 还是第 2 版
