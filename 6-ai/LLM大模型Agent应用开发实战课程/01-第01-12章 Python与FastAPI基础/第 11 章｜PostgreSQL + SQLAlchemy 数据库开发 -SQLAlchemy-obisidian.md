---
title: "第 11 章补充｜SQLAlchemy 与 ORM 概念"
chapter: "11"
source: "第 11 章｜PostgreSQL + SQLAlchemy 数据库开发 -SQLAlchemy.md"
type: obsidian-note
created: 2026-11-21
status: 整理中
tags:
  - course/llm-agent
  - sqlalchemy
  - orm
---

# 第 11 章补充｜SQLAlchemy 与 ORM 概念

> [!abstract] 本章重点
>
> - ==ORM 让代码用对象操作表== — 不用手写 SQL 也能增删改查。
> - ==NestJS 常用 TypeORM / Prisma== — Python 这边对应的就是 SQLAlchemy。
>
> [!note] 大白话
>
> - **ORM**：把数据库表翻译成编程语言里的类。
>
> [!info] 导航与来源
> - 原始讲义：[[第 11 章｜PostgreSQL + SQLAlchemy 数据库开发 -SQLAlchemy|打开原始讲义]]
> - [[第 10 章｜Middleware、异常处理与日志|上一章｜第 10 章]]
> - [[第 12 章｜Redis 在 AI 应用中的使用|下一章｜第 12 章]]
> - 本章所有内容均保留，未删改原文。

---
SQLAlchemy
**SQLAlchemy 是 Python 生态中最著名、功能最强大的对象关系映射（ORM）框架。** 它允许开发者使用 Python 代码来操作数据库（如 MySQL、PostgreSQL、SQLite），而无需编写原生的 SQL 语句。

在其他主流后端框架中，都有与之对应且同样举足轻重的 **ORM 框架**：

******核心框架对比**

| **特性 / 框架** | **Python (SQLAlchemy)** | **Spring Boot (Java)** | **NestJS (Node.js/TypeScript)** |
| --- | --- | --- | --- |
| **官方/社区标准** | **SQLAlchemy** | **Spring Data JPA** (基于 Hibernate) | **TypeORM** / **Prisma** |
| **设计模式** | Data Mapper (数据映射器) | Data Mapper (数据映射器) | TypeORM 支持两者；Prisma 采用独特模式 |
| **核心优势** | 灵活性极高，支持复杂查询 | 与 Spring 生态完美融合，开箱即用 | TypeScript 类型安全支持极佳 |


---

**1. Spring Boot 中的对应者：Hibernate / Spring Data JPA**

在 Spring Boot 中，你通常不会直接使用一个单独的“库”，而是使用 Spring 官方封装的生态：

+ **Hibernate**：这是 Java 世界中真正的 SQLAlchemy 对应者。它是一个功能完整的 ORM 框架，负责将 Java 类映射到数据库表。
+ **Spring Data JPA**：Spring 对 Hibernate 等 JPA（Java Persistence API）规范实现进行的二次封装。它让你只需要定义一个接口（Repository），就能自动实现增删改查，极大地简化了开发。

**2. NestJS 中的对应者：TypeORM / Prisma**

==NestJS 官方支持并推荐两个主要的 ORM 框架：==

+ **TypeORM**：在设计理念上与 SQLAlchemy 和 Hibernate 最为相似。它完全基于装饰器（Decorators），支持 **Data Mapper** 模式，非常适合面向对象编程（OOP）的风格。
+ **Prisma**：目前 Node.js 生态中极其火爆的新一代 ORM。它不使用传统的类和装饰器，而是通过一个独立的 `schema.prisma` 文件来定义数据模型，并自动生成类型安全的客户端，开发体验极佳。

---

> [!success] 一句话带走
> ==ORM 是同一套思路，换个语言换个库而已。==

> [!quote] 关于本文档
> 由原始讲义 `第 11 章｜PostgreSQL + SQLAlchemy 数据库开发 -SQLAlchemy.md` 转换为 Obsidian 风格笔记；原文完整保留，未做任何删改。
> 整理日期：2026-11-21
