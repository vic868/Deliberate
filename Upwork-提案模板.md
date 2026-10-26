# Upwork 提案模板（3 套）

> 用法：选对应场景 → 替换 `[方括号]` 里的内容 → 删掉不适用的一行 → 发送。
> 每封控制在 150 词以内。客户平均只读 8 秒，第一句决定他读不读第二句。

---

## 模板 A：后端开发 / Bug 修复 / API 集成

**适用**：Spring Boot 功能开发、接口对接、线上问题排查、小功能交付

```
Hi — [一句话复述他的问题，用他的词]。

I've spent 14 years on the JVM, most recently building high-concurrency services
in Spring Boot and Spring Cloud — [举一个最接近的案例，一句，带数字]。

How I'd approach it:
1. Reproduce it first, and confirm the failing path before touching code
2. [具体技术点：如 fix the N+1 / add retry with backoff / isolate the transaction]
3. Ship with a test that would have caught it, plus a short note on what changed

[可选：一句边界，如 "If the root cause turns out to be in X, I'll flag it before going further."]

I work async by default — written updates, no status meetings. UTC+8, but I overlap
your morning. Happy to start today.

— Yong, PMP, OCP
```

**替换要点**
- 第一行的 `[他的问题]`：直接用 JD 里的原话改写，别用你自己的术语
- 案例要带数字：`20+ cities`、`100M+ transactions/year`、`P99 1.2s → 180ms`

---

## 模板 B：架构评审 / 技术咨询 / 短期诊断

**适用**：architecture review、技术选型、代码审计、交付流程诊断、migration 评估

```
Hi — before quoting the whole thing, I'd want to see the code.

[一句判断：这类项目的成本通常不在 X，而在 Y]。On stacks like yours
([列他 JD 里的 2-3 个技术]) that usually means [具体的坑]。

I'd suggest a paid 2-day audit ($[金额]) that gives you:
- a dependency and risk inventory — what breaks, what has no modern equivalent
- a phased plan with a fixed price per phase
- [一个可验证的产出，如 "the core module building on JDK 21"]

If you'd rather skip it, I can start on milestone 1 at $[金额] and we re-scope from
real data instead of guesses.

14 years on the JVM, PMP-certified, and I write the documentation so the next
person doesn't have to reverse-engineer your system.

— Yong
```

**为什么这样写**：把"要钱"包装成"降低你的风险"。50+ 个竞争者里，只有你会说"先别急着给我大合同"。

---

## 模板 C：数据库 / 性能调优

**适用**：MySQL / Oracle 慢查询、索引设计、连接池、Kafka 消费延迟、Flink 任务调优

```
Hi — [复述症状：slow query / consumer lag / connection pool exhaustion]。

I've tuned Oracle and MySQL in production for 14 years — [案例：如 "cut a 40-minute
IFRS9 batch report to under 3 minutes on a 200M-row table"].

What I'd do in the first pass:
1. Pull the execution plan (EXPLAIN / EXPLAIN ANALYZE) and the actual row counts —
   not the estimates
2. [具体手段：rewrite the correlated subquery / add a covering index / fix the type
   cast that kills the index]
3. Measure before and after, and hand you both numbers plus the exact change

[Kafka 场景替换为：check consumer group lag by partition, then the producer's
batching and the consumer's processing time per record.]

I don't guess at indexes. I show you the plan before and after.

UTC+8, async, can start today.

— Yong
```

**替换要点**：把 `EXPLAIN ANALYZE`、`covering index` 这类词留在信里——**这是筛选器**，懂行的客户会立刻知道你是内行。

---

## 三个通用规则

1. **第一句不写"我是谁"**，写"你的问题是什么"。90% 的提案都在第一句自报家门。
2. **不写"我很有经验"**，写一个具体数字或一个具体技术动作。
3. **结尾给一个低成本下一步**（"can start today" / "happy to do a 15-min call"），不要写"期待您的回复"。

## 发送前 30 秒检查

- [ ] 客户名字或项目名出现过一次（证明不是群发）
- [ ] 至少一个具体技术名词（证明你懂）
- [ ] 没有"Dear Sir/Madam"、"I am the best fit"、"Please find attached"
- [ ] 总长度 < 200 词
- [ ] 报价 ≤ 客户预算上限

---

*2026-10-26 ｜ 配套《Upwork-接单判断清单.md》使用*
