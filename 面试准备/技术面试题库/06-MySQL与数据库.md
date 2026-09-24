---
title: 06-MySQL与数据库
tags: [面试, Java, 技术题库, MySQL, 数据库]
status: 进行中
---

# 🗄️ 06 · MySQL 与数据库

> 返回 [[00-总览与使用说明]]

---

## 一、索引 `#高频`

| 问题 | 得分骨架 |
|---|---|
| 为什么用 B+ 树 | 矮胖（3-4 层存千万级）、非叶子只存键（扇出大）、**叶子节点成链表支持范围查询**；B 树数据分散在各层，范围查询要回旋 |
| 聚簇索引 vs 二级索引 | InnoDB 主键即聚簇索引（叶子存整行）；二级索引叶子存主键值 → **需要回表** |
| 覆盖索引 | 查询列全在索引中，无需回表（`explain` 的 Extra 显示 `Using index`） |
| **最左前缀** | 联合索引 `(a,b,c)` 从最左连续匹配；范围查询后的列失效 |
| 索引下推 ICP | MySQL 5.6+，在存储引擎层就过滤（减少回表），Extra 显示 `Using index condition` |
| 索引失效场景 | 函数/运算、隐式类型转换、`like '%x'`、`or`（一侧无索引）、`!=`/`not in`（可能）、最左前缀断裂、优化器认为全表更快 |
| 回表 | 二级索引查到主键再回聚簇索引取数据 |
| 索引选择 | 区分度高、经常 where/order by/join 的列；**别建太多**（写放大） |
| 唯一索引 vs 普通索引 | 唯一索引能保证约束；插入时不能 change buffer 优化（性能略差） |

---

## 二、事务与锁 `#高频`

| 问题 | 得分骨架 |
|---|---|
| ACID | 原子性（undo）、一致性、隔离性（锁+MVCC）、持久性（redo） |
| 隔离级别与问题 | 读未提交（脏读）/ 读已提交（不可重复读）/ **可重复读（MySQL 默认，MVCC 解决；间隙锁解决大部分幻读）** / 串行化 |
| **MVCC** | 隐藏列 `trx_id` + `roll_pointer` + undo log 版本链；ReadView（m_ids、min_trx_id、max_trx_id）判断可见性；**RC 每次查询新建 ReadView，RR 只在第一次查询建立** |
| 当前读 vs 快照读 | `select` 普通查询是快照读；`select ... for update`/`lock in share mode`/增删改是当前读 |
| 锁类型 | 表锁 / 行锁（Record Lock）/ **间隙锁 Gap Lock** / **Next-Key Lock（记录+间隙）** |
| 间隙锁作用 | 在 RR 下防止其他事务在间隙插入 → 解决幻读；**只在 RR 生效，RC 无间隙锁** |
| 死锁 | 两个事务互相等锁；MySQL 会自动检测并回滚代价小的一方；避免：按固定顺序访问、缩小事务、加索引减少锁范围 |
| 乐观锁 vs 悲观锁 | 版本号/CAS vs `for update`；读多写少用乐观锁 |

---

## 三、日志与复制

| 日志 | 作用 |
|---|---|
| **redo log** | 物理日志、InnoDB 特有、**循环写**；保证崩溃恢复（持久性）；WAL 机制 |
| **undo log** | 逻辑日志；回滚 + MVCC 版本链 |
| **binlog** | Server 层、逻辑日志、**追加写**；主从复制 + 数据恢复；STATEMENT/ROW/MIXED |
| 两阶段提交 | redo prepare → 写 binlog → redo commit；**保证两份日志一致** |

**主从复制**：master 写 binlog → dump 线程发送 → slave IO 线程写 relay log → SQL 线程重放
- **主从延迟原因**：从库单线程重放（可开并行复制）、大事务、从库压力大
- **延迟解决**：半同步复制、并行复制、读写分离时"写后读主"、缓存

---

## 四、优化实战 `#高频`

**explain 关键列**：`type`（system>const>eq_ref>ref>range>index>ALL）、`key`、`rows`、`filtered`、`Extra`（Using index / Using filesort / Using temporary）

**慢 SQL 优化步骤**：
1. 开慢查询日志定位 SQL
2. `explain` 看执行计划
3. 加/改索引（注意最左前缀、覆盖索引）
4. 改写 SQL（避免子查询、大 offset）
5. 分页优化、冷热分离、归档

**深分页优化**：
```sql
-- 慢：扫描 100 万行
select * from t order by id limit 1000000, 10;
-- 快：用上次最大 id 做游标
select * from t where id > 1000000 order by id limit 10;
-- 或延迟关联
select * from t join (select id from t order by id limit 1000000,10) x using(id);
```

**其他**：`count(*)` vs `count(1)` vs `count(列)`、大事务拆分、批量插入、连接池（HikariCP）、读写分离

---

## 五、分库分表

- 垂直拆分（按业务/字段）vs 水平拆分（按行）
- 分片键选择：**尽量让查询能落到单分片**（如按 user_id / tenant_id）
- 问题：跨分片查询、分布式事务、全局 ID、扩容迁移
- 中间件：ShardingSphere、MyCat
- **先考虑**：读写分离 → 索引优化 → 归档 → 分区表 → 最后才分库分表

---

## 📥 待补充

- 

## 🔗 关联

- [[00-总览与使用说明]] · [[07-Redis与缓存]] · [[09-分布式与微服务]]

#面试 #MySQL #数据库 #待补
