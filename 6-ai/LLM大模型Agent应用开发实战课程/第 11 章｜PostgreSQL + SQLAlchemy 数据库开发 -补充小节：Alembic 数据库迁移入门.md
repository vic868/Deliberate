---

# 一、本小节定位
在第 11 章里，我们已经完成了：

```plain
PostgreSQL 安装
SQLAlchemy 异步连接
AsyncSession
User / Conversation / Message 模型
create_tables.py 创建数据库表
ConversationRepository 数据库改造
Chat 消息入库
历史消息查询
```

上一章我们创建表用的是：

```python
Base.metadata.create_all
```

这个方式适合：

```plain
学习阶段
本地 Demo
快速验证模型
```

但是企业项目不能长期依赖它。

为什么？

因为真实项目里，表结构会不断变化。

比如：

```plain
messages 表要新增 token 字段
conversations 表要新增 summary 字段
users 表要新增 email 字段
documents 表要新增 file_type 字段
agent_runs 表要新增 status 字段
tool_calls 表要新增 cost_ms 字段
```

如果每次改表结构都靠：

```plain
删表
重新 create_all
重新导入数据
```

那生产环境肯定不能接受。

所以我们需要一个工具来管理数据库结构变化。

这个工具就是：

# Alembic
Alembic 的作用可以简单理解成：

**给数据库表结构做 Git 版本管理。**

---

# 二、本小节学习目标
学完这个补充小节以后，学员需要掌握：

```plain
1. 为什么不能长期使用 create_all
2. Alembic 是什么
3. Alembic 解决什么问题
4. migration 迁移脚本是什么
5. revision / upgrade / downgrade 分别是什么意思
6. 如何安装 Alembic
7. 如何初始化 Alembic
8. 如何配置异步 SQLAlchemy 项目
9. 如何让 Alembic 读取 settings.database_url
10. 如何让 Alembic 识别 SQLAlchemy ORM 模型
11. 如何生成第一版迁移脚本
12. 如何执行 alembic upgrade head
13. 如何查看 alembic_version 表
14. 如何新增字段并生成迁移
15. 如何回滚迁移
16. Alembic 在团队协作中怎么使用
17. 常见坑怎么排查
```

---

# 三、本小节最终项目结构
本小节结束后，项目会增加：

```plain
ai-agent-course/
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   ├── README
│   └── versions/
│       ├── xxxxx_init_tables.py
│       └── xxxxx_add_message_token_fields.py
│
├── alembic.ini
│
├── app/
│   ├── db/
│   │   ├── base.py
│   │   ├── session.py
│   │   └── init_db.py
│   │
│   ├── models/
│   │   ├── user.py
│   │   ├── conversation.py
│   │   └── message.py
│   │
│   └── ...
│
└── scripts/
    ├── create_tables.py
    └── test_db.py
```

新增重点文件：

```plain
alembic.ini
alembic/env.py
alembic/versions/*.py
```

---

# 四、01｜本小节开场
## 【重点内容】
大家好，这里我们补充一个第 11 章的小节：

# Alembic 数据库迁移入门
为什么这个小节要放在第 11 章后面？

因为第 11 章我们已经接入了 PostgreSQL 和 SQLAlchemy。

我们也已经定义了三张表：

```plain
users
conversations
messages
```

并且用：

```python
Base.metadata.create_all
```

创建了表。

但是 `create_all` 只适合学习和本地 Demo。

真实企业项目不能只靠它。

举个例子。

现在 messages 表只有：

```plain
id
conversation_id
role
content
model
created_at
```

后面我们想加：

```plain
prompt_tokens
completion_tokens
total_tokens
```

如果是本地 Demo，你可以删表重建。

但是生产环境里，messages 表可能已经有几百万条聊天记录。

你不可能把表删了。

所以我们需要一种方式：

```plain
保留旧数据
只修改表结构
记录每一次结构变更
支持升级
支持回滚
支持团队协作
```

这就是 Alembic 要解决的问题。

---

# 五、02｜create_all 的问题
## 【实操说明】
第 11 章里我们写过：

```python
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

这个代码可以根据 ORM 模型创建表。

但是它有几个限制。

---

## 【问题一：不会管理版本】
比如第一次表结构：

```plain
messages
├── id
├── conversation_id
├── role
├── content
└── created_at
```

第二次你想加字段：

```plain
total_tokens
```

`create_all` 不会帮你记录：

```plain
什么时候加的
谁加的
对应哪个代码版本
能不能回滚
```

---

## 【问题二：不会自动安全修改已有表】
`create_all` 的重点是：

```plain
没有表就创建
```

但它不是专门用来做复杂表结构变更的。

比如：

```plain
改字段类型
删除字段
重命名字段
增加索引
修改约束
```

这些都需要迁移脚本来明确描述。

---

## 【问题三：不适合团队协作】
假设两个同事同时改表：

```plain
A 同事给 users 表加 email
B 同事给 messages 表加 total_tokens
```

如果没有迁移文件，大家很难知道数据库应该按什么顺序变化。

---

## 【重点内容】
所以大家要记住：

```plain
create_all
适合学习、Demo、快速验证

Alembic
适合企业项目、团队协作、生产环境
```

后面我们就要从：

```plain
create_all
```

升级到：

```plain
Alembic migration
```

---

# 六、03｜Alembic 是什么
## 【重点内容】
Alembic 可以理解成数据库表结构的版本管理工具。

它会帮我们生成一系列迁移文件。

比如：

```plain
001_init_tables.py
002_add_message_token_fields.py
003_add_user_email.py
004_add_agent_run_table.py
```

每个迁移文件里通常有两个函数：

```python
def upgrade():
    pass


def downgrade():
    pass
```

其中：

```plain
upgrade
= 升级数据库结构

downgrade
= 回滚数据库结构
```

比如新增字段：

```python
def upgrade():
    op.add_column("messages", sa.Column("total_tokens", sa.Integer()))
```

回滚字段：

```python
def downgrade():
    op.drop_column("messages", "total_tokens")
```

这样数据库结构变化就有记录了。

---

# 七、04｜Alembic 核心命令
## 【屏幕展示】
| 命令 | 作用 |
| --- | --- |
| `alembic init alembic` | 初始化 Alembic 目录 |
| `alembic init -t async alembic` | 初始化异步模板 |
| `alembic revision -m "xxx"` | 创建空迁移文件 |
| `alembic revision --autogenerate -m "xxx"` | 自动对比 ORM 和数据库生成迁移 |
| `alembic upgrade head` | 升级到最新版本 |
| `alembic downgrade -1` | 回滚上一个版本 |
| `alembic history` | 查看迁移历史 |
| `alembic current` | 查看当前数据库版本 |
| `alembic heads` | 查看最新迁移头 |
| `alembic stamp head` | 标记当前数据库为最新版本，不执行迁移 |


Alembic 官方教程中也明确展示了 `alembic init` 初始化环境、迁移文件里的 `upgrade()` / `downgrade()` 结构，以及通过 `upgrade` 执行迁移的流程。([alembic.sqlalchemy.org](https://alembic.sqlalchemy.org/en/latest/tutorial.html?utm_source=chatgpt.com))

---

# 八、05｜安装 Alembic
## 【屏幕操作】
进入项目根目录：

```bash
cd ai-agent-course
```

安装：

```bash
uv add alembic
```

如果使用 pip：

```bash
pip install alembic
```

检查：

```bash
uv run alembic --version
```

或者：

```bash
alembic --version
```

---

## 【重点内容】
这里我们安装 Alembic。

如果你用的是 uv，推荐：

```bash
uv add alembic
```

后面执行命令时也推荐：

```bash
uv run alembic ...
```

这样可以保证使用的是当前虚拟环境里的 Alembic。

不要出现一个常见问题：

```plain
项目虚拟环境装了依赖
但是命令行调用的是全局 alembic
```

所以课程里统一用：

```bash
uv run alembic
```

---

# 九、06｜初始化 Alembic
因为我们第 11 章使用的是：

```plain
SQLAlchemy AsyncSession
asyncpg
postgresql+asyncpg
```

所以这里优先使用 Alembic 的 async 模板。

执行：

```bash
uv run alembic init -t async alembic
```

如果你的 Alembic 版本不支持 `-t async`，可以先用普通初始化：

```bash
uv run alembic init alembic
```

然后手动改 `env.py`。

执行成功后，会生成：

```plain
alembic/
├── env.py
├── README
├── script.py.mako
└── versions/

alembic.ini
```

---

## 【重点内容】
这里我们用：

```bash
alembic init -t async alembic
```

意思是：

```plain
初始化 Alembic
使用 async 模板
目录名叫 alembic
```

初始化之后，项目根目录会多一个：

```plain
alembic.ini
```

还会多一个：

```plain
alembic/
```

目录。

其中最重要的是：

```plain
alembic/env.py
```

它是 Alembic 执行迁移时的环境配置文件。

---

# 十、07｜先看 alembic.ini
打开：

```plain
alembic.ini
```

你会看到类似：

```plain
[alembic]
script_location = alembic

sqlalchemy.url = driver://user:pass@localhost/dbname
```

这里有一个配置：

```plain
sqlalchemy.url
```

它原本用来写数据库连接地址。

但是我们项目里已经有：

```plain
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ai_agent_course
```

所以我们不建议在 `alembic.ini` 里重复写死数据库地址。

可以先改成占位：

```plain
sqlalchemy.url =
```

然后在 `env.py` 里从：

```python
settings.database_url
```

读取。

---

## 【重点内容】
为什么不要把数据库地址写死在 `alembic.ini`？

因为不同环境数据库地址不一样。

比如：

```plain
本地开发数据库
测试环境数据库
生产环境数据库
```

如果写死在 `alembic.ini`，很容易误操作。

所以我们统一从：

```plain
.env
```

读取：

```plain
DATABASE_URL
```

这样和 FastAPI 项目配置保持一致。

---

# 十一、08｜配置 alembic/env.py
打开：

```plain
alembic/env.py
```

如果你用的是 async 模板，可以直接替换成下面这个版本。

```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.db.base import Base

# 关键：导入所有模型，让 Base.metadata 能收集到表结构
from app import models  # noqa: F401


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = settings.database_url

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named"
        },
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

Alembic 官方 Cookbook 说明，Alembic 本身没有直接的 async API，但可以结合 SQLAlchemy async engine 运行迁移和 autogenerate；async 模板会通过 async engine 与 `run_sync` 适配迁移执行。([alembic.sqlalchemy.org](https://alembic.sqlalchemy.org/en/latest/cookbook.html?utm_source=chatgpt.com))

---

## 【重点内容】
这个 `env.py` 是整个 Alembic 配置的核心。

重点看几个地方。

第一：

```python
from app.core.config import settings
```

我们从项目配置里读取数据库地址。

第二：

```python
from app.db.base import Base
```

引入 SQLAlchemy Base。

第三：

```python
from app import models
```

这句很重要。

它的作用是导入所有 ORM 模型。

否则 Alembic 不知道有哪些表。

第四：

```python
target_metadata = Base.metadata
```

这句告诉 Alembic：

请拿 SQLAlchemy ORM 模型的 metadata，和当前数据库结构做对比。

第五：

```python
compare_type=True
```

它表示字段类型变化也尽量参与对比。

比如字段从：

```plain
String(100)
```

改成：

```plain
String(200)
```

Alembic 可以尝试识别。

---

# 十二、09｜确认 app/models/**init**.py 正确导入模型
打开：

```plain
app/models/__init__.py
```

确认是：

```python
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User


__all__ = [
    "Conversation",
    "Message",
    "User",
]
```

---

## 【重点内容】
这一步非常重要。

很多同学 Alembic 自动生成迁移文件为空，原因就是模型没有被导入。

Alembic 通过：

```python
Base.metadata
```

收集表结构。

但是如果模型类没有被 import，metadata 里面就没有这些表。

所以我们在：

```python
app/models/__init__.py
```

里统一导入模型。

再在：

```python
alembic/env.py
```

里写：

```python
from app import models
```

这样 Alembic 就能识别表。

---

# 十三、10｜处理 create_all 已经创建过表的问题
## 【重要说明】
如果你在第 11 章已经运行过：

```bash
python scripts/create_tables.py
```

那么数据库里已经有表了：

```plain
users
conversations
messages
```

这时候你直接执行：

```bash
uv run alembic revision --autogenerate -m "init tables"
```

可能会生成一个空迁移文件。

原因是：

```plain
数据库里已经有表
ORM 模型里也有表
Alembic 一对比，发现没有差异
```

所以初学阶段有两种处理方式。

---

## 方案一：本地开发直接清库重来
如果这是本地 Demo 数据，可以清空数据库重新来。

### Docker 方式
```bash
docker compose down -v
docker compose up -d
```

注意：

```plain
这个命令会删除 postgres_data 数据卷
本地数据库数据会全部清空
```

---

### 手动 PostgreSQL 方式
进入 psql：

```bash
psql -U postgres
```

执行：

```sql
DROP DATABASE ai_agent_course;
CREATE DATABASE ai_agent_course;
```

退出：

```sql
\q
```

---

## 方案二：已有表不重建，使用 stamp 标记
如果你已经有一套表，而且不想删，可以先生成一版迁移文件，然后执行：

```bash
uv run alembic stamp head
```

这表示：

```plain
不要真正执行建表
只是告诉 Alembic：当前数据库已经处于最新版本
```

但是课程入门阶段，建议用方案一。

因为更直观。

---

## 【重点内容】
这里一定要讲清楚。

很多同学会问：

为什么我执行 autogenerate，生成的 migration 是空的？

原因通常是：

```plain
你已经用 create_all 把表建好了
```

Alembic 一对比，发现数据库和 ORM 一样，就没有可生成的变化。

所以课程演示时，我建议：

```plain
本地开发清库
让 Alembic 从零创建表
```

这样最容易理解。

但是生产环境千万不要随便 drop database。

---

# 十四、11｜生成第一版迁移文件
确保数据库是空的，或者已经清库。

执行：

```bash
uv run alembic revision --autogenerate -m "init tables"
```

执行成功后，会在：

```plain
alembic/versions/
```

生成类似文件：

```plain
20260824_103000_init_tables.py
```

或者：

```plain
8f3a2c1b9d4e_init_tables.py
```

文件名会根据 Alembic 生成规则变化。

---

## 【重点内容】
这条命令很重要：

```bash
alembic revision --autogenerate -m "init tables"
```

拆开看：

```plain
revision
= 创建一个迁移版本

--autogenerate
= 自动对比 ORM 模型和数据库结构

-m "init tables"
= 迁移说明
```

执行后，Alembic 会对比：

```plain
当前数据库结构
和
SQLAlchemy ORM 模型
```

然后生成迁移脚本。

---

# 十五、12｜查看第一版迁移文件
打开：

```plain
alembic/versions/xxxx_init_tables.py
```

你会看到类似：

```python
"""init tables

Revision ID: 8f3a2c1b9d4e
Revises:
Create Date: 2026-08-24 10:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8f3a2c1b9d4e"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("conversation_id", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_messages_conversation_id"),
        "messages",
        ["conversation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_messages_conversation_id"),
        table_name="messages",
    )
    op.drop_table("messages")
    op.drop_table("users")
    op.drop_table("conversations")
```

---

## 【重点内容】
大家一定要打开迁移文件看一眼。

不要盲目执行。

`upgrade()` 里是升级逻辑。

这里会创建：

```plain
users
conversations
messages
```

`downgrade()` 里是回滚逻辑。

这里会删除：

```plain
messages
users
conversations
```

注意删除顺序。

因为 messages 依赖 conversations，所以回滚时要先删除 messages。

---

# 十六、13｜执行迁移 upgrade head
执行：

```bash
uv run alembic upgrade head
```

成功后，数据库里应该出现：

```plain
users
conversations
messages
alembic_version
```

---

## 【重点内容】
现在我们执行迁移：

```bash
alembic upgrade head
```

意思是：

把数据库升级到最新迁移版本。

执行成功后，除了业务表，还会多一张表：

```plain
alembic_version
```

这张表是 Alembic 自己维护的。

它用来记录：

```plain
当前数据库处于哪个迁移版本
```

---

# 十七、14｜查看 alembic_version 表
在 DBeaver 或 psql 里执行：

```sql
SELECT * FROM alembic_version;
```

会看到类似：

```plain
version_num
8f3a2c1b9d4e
```

---

## 【重点内容】
这张表非常重要。

Alembic 每次执行迁移，都会更新：

```plain
alembic_version
```

比如现在是第一版：

```plain
init tables
```

后面新增字段后，版本号会变成新的 revision。

所以 Alembic 是通过这张表知道：

```plain
数据库现在升级到哪一步了
```

---

# 十八、15｜查看当前版本和历史
查看当前版本：

```bash
uv run alembic current
```

查看历史：

```bash
uv run alembic history
```

查看最新头：

```bash
uv run alembic heads
```

---

## 【重点内容】
这几个命令很常用。

```bash
alembic current
```

看当前数据库版本。

```bash
alembic history
```

看所有迁移历史。

```bash
alembic heads
```

看当前代码里的最新迁移版本。

以后团队协作时，如果出现迁移冲突，这几个命令会经常用。

---

# 十九、16｜新增字段：给 messages 表增加 token 字段
现在我们模拟一个真实需求：

AI Chat 消息需要记录 token 用量。

修改：

```plain
app/models/message.py
```

增加三个字段：

```python
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
```

在 Message 类里增加：

```python
prompt_tokens: Mapped[int] = mapped_column(
    Integer,
    nullable=False,
    default=0,
)
completion_tokens: Mapped[int] = mapped_column(
    Integer,
    nullable=False,
    default=0,
)
total_tokens: Mapped[int] = mapped_column(
    Integer,
    nullable=False,
    default=0,
)
```

完整模型变成：

```python
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("conversations.id"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    prompt_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    completion_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    total_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False,
    )

    conversation = relationship(
        "Conversation",
        back_populates="messages",
    )
```

---

## 【重点内容】
现在我们给 messages 表增加三个字段：

```plain
prompt_tokens
completion_tokens
total_tokens
```

这在 AI 项目里非常常见。

因为我们后面要统计：

```plain
每次调用用了多少 token
用户消耗了多少 token
模型成本是多少
```

以前如果不用 Alembic，我们可能要删表重建。

现在我们用迁移来解决。

---

# 二十、17｜生成新增字段迁移
执行：

```bash
uv run alembic revision --autogenerate -m "add message token fields"
```

会生成新文件：

```plain
alembic/versions/yyyy_add_message_token_fields.py
```

打开检查，应该看到类似：

```python
def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
    )
    op.add_column(
        "messages",
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
    )
    op.add_column(
        "messages",
        sa.Column("total_tokens", sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("messages", "total_tokens")
    op.drop_column("messages", "completion_tokens")
    op.drop_column("messages", "prompt_tokens")
```

---

## 【重要调整】
如果你的 messages 表已经有数据，新增 `nullable=False` 字段可能会失败。

因为旧数据没有这些字段的值。

更稳的迁移写法是给 `server_default`：

```python
def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column(
            "prompt_tokens",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "messages",
        sa.Column(
            "completion_tokens",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "messages",
        sa.Column(
            "total_tokens",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
```

也可以分两步：

```plain
先 nullable=True
填充旧数据
再改 nullable=False
```

课程入门阶段，先使用 `server_default="0"` 更容易理解。

---

## 【重点内容】
这里一定要提醒大家。

自动生成的迁移文件不是一定能直接上生产。

你必须打开检查。

尤其是这种：

```plain
给已有表新增 nullable=False 字段
```

如果表里已经有旧数据，数据库不知道旧数据这个字段应该填什么，就可能失败。

所以要加默认值，或者分步骤迁移。

这就是为什么迁移文件一定要人工 review。

---

# 二十一、18｜执行新增字段迁移
执行：

```bash
uv run alembic upgrade head
```

然后在 DBeaver 执行：

```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'messages';
```

应该能看到：

```plain
prompt_tokens
completion_tokens
total_tokens
```

---

## 【重点内容】
现在执行：

```bash
alembic upgrade head
```

数据库结构就升级了。

我们不需要删表。

旧数据还在。

新字段也加上了。

这就是 Alembic 的价值。

---

# 二十二、19｜回滚迁移 downgrade
如果想回滚上一个迁移：

```bash
uv run alembic downgrade -1
```

这会执行上一个迁移文件里的：

```python
downgrade()
```

也就是删除刚才加的 token 字段。

再升级回来：

```bash
uv run alembic upgrade head
```

---

## 【重点内容】
`downgrade` 表示回滚。

```bash
alembic downgrade -1
```

意思是回滚一个版本。

这在本地开发时很常用。

比如你生成了一个迁移，发现写错了，可以回滚。

但是生产环境回滚要谨慎。

尤其是：

```plain
删除字段
删除表
清理数据
```

这些操作可能导致数据丢失。

---

# 二十三、20｜手写迁移：新增索引示例
有时候 autogenerate 不能完全满足需求，我们可以手写迁移。

创建空迁移：

```bash
uv run alembic revision -m "add message role index"
```

打开生成的文件，写：

```python
from alembic import op


def upgrade() -> None:
    op.create_index(
        "ix_messages_role",
        "messages",
        ["role"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_messages_role",
        table_name="messages",
    )
```

执行：

```bash
uv run alembic upgrade head
```

---

## 【重点内容】
Alembic 不一定都靠自动生成。

有些复杂操作需要手写。

比如：

```plain
复杂索引
数据迁移
批量更新
重命名字段
拆表
合表
```

这时候可以先创建空迁移：

```bash
alembic revision -m "xxx"
```

然后自己写：

```python
op.create_index
op.add_column
op.drop_column
op.execute
```

这就是更接近企业项目的用法。

---

# 二十四、21｜更新 Repository 保存 token 字段
因为 messages 表已经新增 token 字段，我们可以更新：

```plain
app/repositories/conversation_repository.py
```

修改 `add_message`：

```python
async def add_message(
    self,
    db: AsyncSession,
    conversation_id: str,
    role: str,
    content: str,
    model: str | None = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
) -> Message:
    message = Message(
        id=f"m_{uuid.uuid4().hex[:8]}",
        conversation_id=conversation_id,
        role=role,
        content=content,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )

    db.add(message)
    await db.commit()
    await db.refresh(message)

    return message
```

---

## 【重点内容】
迁移完成后，代码也要同步更新。

因为数据库已经有新字段了。

Repository 新增参数：

```plain
prompt_tokens
completion_tokens
total_tokens
```

这样后面保存消息时，就可以把 token 用量写入数据库。

这就是正常开发流程：

```plain
改 ORM 模型
 ↓
生成迁移
 ↓
执行迁移
 ↓
更新业务代码
 ↓
测试接口
```

---

# 二十五、22｜更新 ChatService 保存 token
打开：

```plain
app/services/chat_service.py
```

找到保存 AI 回复的地方：

```python
await conversation_repository.add_message(
    db=db,
    conversation_id=request.session_id,
    role=MessageRole.ASSISTANT.value,
    content=answer,
    model=model,
)
```

改成：

```python
await conversation_repository.add_message(
    db=db,
    conversation_id=request.session_id,
    role=MessageRole.ASSISTANT.value,
    content=answer,
    model=model,
    prompt_tokens=usage.prompt_tokens,
    completion_tokens=usage.completion_tokens,
    total_tokens=usage.total_tokens,
)
```

用户消息可以保持默认 0，或者记录 prompt_tokens：

```python
await conversation_repository.add_message(
    db=db,
    conversation_id=request.session_id,
    role=MessageRole.USER.value,
    content=latest_user_message,
    model=request.model,
    prompt_tokens=usage.prompt_tokens,
)
```

---

## 【重点内容】
现在 AI 回复消息会保存 token 用量。

真实项目里，这些数据非常重要。

后面可以做：

```plain
用户 token 消耗统计
模型成本统计
组织级用量统计
接口调用账单
Agent 执行成本分析
```

所以 token 字段是 AI 项目数据库设计里非常常见的字段。

---

# 二十六、23｜团队协作中的 Alembic 流程
## 【屏幕展示】
```plain
开发同学 A：
1. 修改 ORM 模型
2. 生成 migration
3. 本地 upgrade 测试
4. 提交代码 + migration 文件

开发同学 B：
1. 拉最新代码
2. uv run alembic upgrade head
3. 本地数据库升级
4. 继续开发
```

---

## 【重点内容】
Alembic 在团队里怎么用？

非常简单。

谁改了数据库表结构，谁就要提交迁移文件。

不能只提交 ORM 模型。

比如你改了：

```plain
app/models/message.py
```

新增字段：

```plain
total_tokens
```

那你必须同时提交：

```plain
alembic/versions/xxxx_add_message_token_fields.py
```

否则别人拉代码后，数据库不会自动变化。

团队协作时，大家统一执行：

```bash
uv run alembic upgrade head
```

把本地数据库升级到最新结构。

---

# 二十七、24｜生产环境中的 Alembic 注意事项
## 【重点内容】
生产环境执行迁移要非常谨慎。

建议遵守几个原则。

第一：

```plain
先备份数据库
```

第二：

```plain
先在测试环境执行
```

第三：

```plain
不要随便 drop table
```

第四：

```plain
不要轻易删除字段
```

第五：

```plain
大表加字段要考虑锁表和耗时
```

第六：

```plain
迁移文件要人工 review
```

第七：

```plain
代码发布和数据库迁移要有顺序
```

比如：

```plain
先加兼容字段
再发代码
再清理旧字段
```

这类内容后面部署章节还会再讲。

这一小节先掌握入门流程。

---

# 二十八、25｜常见错误一：autogenerate 生成空文件
## 错误现象
```python
def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
```

## 常见原因
```plain
1. 数据库已经用 create_all 建过表
2. env.py 没有配置 target_metadata
3. app/models 没有导入模型
4. DATABASE_URL 指向了错误数据库
```

## 解决方式
检查：

```python
target_metadata = Base.metadata
```

检查：

```python
from app import models
```

确认连接的是：

```plain
ai_agent_course
```

---

# 二十九、26｜常见错误二：Can't locate revision
## 错误
```plain
Can't locate revision identified by 'xxxx'
```

## 原因
通常是：

```plain
数据库 alembic_version 记录了某个 revision
但是本地 alembic/versions 里没有这个文件
```

可能是：

```plain
迁移文件没提交
误删了 migration 文件
切换分支导致版本不一致
```

## 解决思路
```plain
1. 检查 Git 分支
2. 拉取最新代码
3. 确认 alembic/versions 文件完整
4. 不要随便手改 alembic_version
```

---

# 三十、27｜常见错误三：Target database is not up to date
## 错误
```plain
Target database is not up to date.
```

## 原因
当前数据库还没升级到最新版本，你又想生成新的迁移。

## 解决
先执行：

```bash
uv run alembic upgrade head
```

再生成：

```bash
uv run alembic revision --autogenerate -m "xxx"
```

---

# 三十一、28｜常见错误四：新增非空字段失败
## 错误原因
已有表里有旧数据。

你新增了：

```python
nullable=False
```

但没有默认值。

## 解决方式
方式一：加默认值：

```python
sa.Column(
    "total_tokens",
    sa.Integer(),
    nullable=False,
    server_default="0",
)
```

方式二：分三步：

```plain
1. 先新增 nullable=True 字段
2. 用 SQL 填充旧数据
3. 再改成 nullable=False
```

---

# 三十二、29｜常见错误五：连接数据库失败
## 错误
```plain
ConnectionRefusedError
```

检查：

```bash
docker ps
```

启动：

```bash
docker compose up -d
```

测试连接：

```bash
python scripts/test_db.py
```

---

# 三十三、30｜常见错误六：async 模板配置错误
## 错误现象
```plain
greenlet_spawn has not been called
```

或者迁移执行时报 async 相关错误。

## 排查
确认使用：

```python
async_engine_from_config
```

确认在线迁移里有：

```python
await connection.run_sync(do_run_migrations)
```

确认 DATABASE_URL 是：

```plain
postgresql+asyncpg://...
```

而不是：

```plain
postgresql://...
```

---

# 三十四、31｜本小节知识点和 AI 项目场景对应表
| Alembic 知识点 | AI 项目场景 |
| --- | --- |
| migration | 管理 AI 项目表结构变化 |
| revision | 每一次表结构变化的版本 |
| upgrade | 发布新表、新字段、新索引 |
| downgrade | 回滚错误表结构 |
| autogenerate | 根据 ORM 模型自动生成迁移 |
| alembic_version | 记录当前数据库版本 |
| init tables | 初始化 users / conversations / messages |
| add column | 给 messages 增加 token 字段 |
| create index | 给消息、会话、Agent Run 增加查询索引 |
| server_default | 给已有数据的新字段设置默认值 |
| stamp head | 标记已有数据库版本 |
| migration review | 避免自动生成脚本误伤数据 |
| 团队协作 | 提交 ORM 模型时同时提交 migration |
| 生产发布 | 数据库迁移和代码发布配合 |


---

# 三十五、32｜本小节完整复习
这一小节我们完成了：

```plain
1. 理解 create_all 的限制
2. 理解 Alembic 的作用
3. 理解 revision / upgrade / downgrade
4. 安装 Alembic
5. 初始化 async Alembic 环境
6. 配置 alembic.ini
7. 配置 alembic/env.py
8. 从 settings.database_url 读取数据库地址
9. 配置 target_metadata = Base.metadata
10. 导入 app.models 让 Alembic 识别 ORM 模型
11. 处理 create_all 已建表导致 autogenerate 为空的问题
12. 生成第一版 init tables 迁移
13. 执行 alembic upgrade head
14. 查看 alembic_version 表
15. 新增 messages token 字段
16. 自动生成 add message token fields 迁移
17. 处理 nullable=False 字段默认值问题
18. 执行升级和回滚
19. 手写索引迁移
20. 更新 Repository 保存 token 字段
21. 理解团队协作中的 Alembic 流程
22. 总结生产环境迁移注意事项
```

---

# 三十六、33｜课后任务一：给 users 表新增 email 字段
## 要求
```plain
1. 修改 app/models/user.py
2. 新增 email 字段
3. 字段类型 String(200)
4. nullable=True
5. 生成 migration
6. 执行 upgrade head
7. 用 DBeaver 查看字段是否存在
```

参考模型字段：

```python
email: Mapped[str | None] = mapped_column(
    String(200),
    nullable=True,
)
```

生成迁移：

```bash
uv run alembic revision --autogenerate -m "add user email"
```

执行迁移：

```bash
uv run alembic upgrade head
```

---

# 三十七、34｜课后任务二：给 conversations 表新增 summary 字段
## 要求
```plain
1. 修改 Conversation 模型
2. 新增 summary 字段
3. 类型 Text
4. nullable=True
5. 生成迁移
6. 执行迁移
```

参考：

```python
from sqlalchemy import DateTime, String, Text
```

字段：

```python
summary: Mapped[str | None] = mapped_column(
    Text,
    nullable=True,
)
```

---

# 三十八、35｜课后任务三：手写索引迁移
## 要求
给 messages 表增加组合索引：

```plain
conversation_id
created_at
```

创建空迁移：

```bash
uv run alembic revision -m "add message conversation created index"
```

迁移内容：

```python
def upgrade() -> None:
    op.create_index(
        "ix_messages_conversation_id_created_at",
        "messages",
        ["conversation_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_messages_conversation_id_created_at",
        table_name="messages",
    )
```

---

# 三十九、36｜课后任务四：练习回滚
## 要求
```plain
1. 执行 alembic history
2. 执行 alembic current
3. 执行 alembic downgrade -1
4. 用 DBeaver 查看字段或索引是否回滚
5. 再执行 alembic upgrade head
6. 确认恢复到最新版本
```

---

# 四十、37｜课后任务五：画出 Alembic 工作流程
画出完整链路：

```plain
修改 ORM Model
 ↓
alembic revision --autogenerate
 ↓
生成 migration 文件
 ↓
人工 review migration
 ↓
alembic upgrade head
 ↓
数据库结构变化
 ↓
alembic_version 更新
 ↓
提交 Model + Migration 到 Git
```

---


