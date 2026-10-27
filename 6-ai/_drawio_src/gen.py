import html

W, H = 1700, 1000

def esc(s):
    return html.escape(s, quote=True)

class Page:
    def __init__(self, name):
        self.name = name
        self.cells = []
        self.n = 0
    def _id(self, prefix="c"):
        self.n += 1
        return f"{prefix}{self.n}"
    def box(self, label, x, y, w, h, fill="#dae8fc", stroke="#6c8ebf",
            shape="rounded=1", fs=14, bold=1, dashed=0, font_color="#1f2937", valign="middle"):
        i = self._id()
        style = (f"{shape};whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};"
                 f"strokeWidth=2;fontSize={fs};fontStyle={bold};align=center;verticalAlign={valign};"
                 f"dashed={dashed};fontColor={font_color};arcSize=8;")
        self.cells.append(
            f'<mxCell id="{i}" value="{esc(label)}" style="{style}" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
        return i
    def diamond(self, label, x, y, w, h, fill="#fff2cc", stroke="#d6b656", fs=13):
        return self.box(label, x, y, w, h, fill=fill, stroke=stroke, shape="rhombus", fs=fs)
    def text(self, label, x, y, w, h, fs=16, bold=1, color="#111827", align="left"):
        i = self._id()
        style = (f"text;html=1;whiteSpace=wrap;strokeColor=none;fillColor=none;align={align};"
                 f"verticalAlign=middle;fontSize={fs};fontStyle={bold};fontColor={color};")
        self.cells.append(
            f'<mxCell id="{i}" value="{esc(label)}" style="{style}" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
        return i
    def edge(self, src, tgt, extra="", label="", dashed=0, color="#334155", width=2, arrow="block"):
        i = self._id("e")
        style = (f"edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;strokeWidth={width};strokeColor={color};"
                 f"endArrow={arrow};endFill=1;dashed={dashed};fontSize=12;fontColor=#475569;{extra}")
        self.cells.append(
            f'<mxCell id="{i}" value="{esc(label)}" style="{style}" edge="1" parent="1" source="{src}" target="{tgt}">'
            f'<mxGeometry relative="1" as="geometry"/></mxCell>')
        return i
    def xml(self):
        body = "\n        ".join(self.cells)
        return (f'  <diagram name="{esc(self.name)}" id="{esc(self.name)}">\n'
                f'    <mxGraphModel dx="1600" dy="1000" grid="1" gridSize="10" guides="1" tooltips="1" '
                f'connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{W}" pageHeight="{H}" '
                f'math="0" shadow="0">\n      <root>\n        <mxCell id="0"/>\n        <mxCell id="1" parent="0"/>\n'
                f'        {body}\n      </root>\n    </mxGraphModel>\n  </diagram>')

# ============ Page 1: 八站全景 ============
p1 = Page("01-八站全景")
p1.text("Agent 面试八站作战地图", 60, 24, 900, 46, fs=30)
p1.text("一条主线：从「它是什么」一路推到「30 秒讲清我的项目」", 62, 74, 1100, 30, fs=15, bold=0, color="#475569")

sta = [
    ("第 1 站  概念与边界", "Agent = 会调用工具的循环系统<br/>三判句定生死", "#dbeafe", "#2563eb"),
    ("第 2 站  架构五件套", "模型是大脑，Harness 是脊椎<br/>上线就崩多半是脊椎塌了", "#e0e7ff", "#4338ca"),
    ("第 3 站  核心循环", "Thought 到 Action 到 Observation<br/>上下文在循环里累积", "#dcfce7", "#16a34a"),
    ("第 4 站  工具与协议", "FC 是模型层能力，MCP 是生态层标准<br/>M×N 变 M+N", "#fef3c7", "#d97706"),
    ("第 5 站  推理范式", "ReAct 地基 / P&E 全局 / Reflexion 自审<br/>选型看能否预判步骤", "#fce7f3", "#db2777"),
    ("第 6 站  记忆与上下文", "三层记忆 + 四招压缩<br/>上下文越少越准", "#cffafe", "#0891b2"),
    ("第 7 站  多智能体与 RAG", "三种编排 · 15 倍成本<br/>能不用就不用", "#ede9fe", "#7c3aed"),
    ("第 8 站  生产化与实战", "四种死法 · 兜底四层 · 评测闭环<br/>简单 可衡量 可持续", "#fee2e2", "#dc2626"),
]
xs = [80, 500, 920, 1340]
ids = []
for idx, (t, sub, fill, stroke) in enumerate(sta):
    row, pos = idx // 4, idx % 4
    col = pos if row == 0 else 3 - pos
    y = 140 if row == 0 else 470
    ids.append(p1.box(f"<b>{t}</b><br/><br/>{sub}", xs[col], y, 300, 130, fill=fill, stroke=stroke))

for k in range(3):
    p1.edge(ids[k], ids[k+1])
p1.edge(ids[3], ids[4])
for k in range(4, 7):
    p1.edge(ids[k], ids[k+1])

offer = p1.box("<b>Offer</b><br/>原理能推导 · 组件能画图<br/>系统能落地 · 坏 case 能复盘",
               690, 730, 420, 110, fill="#bbf7d0", stroke="#15803d", fs=15)
p1.edge(ids[7], offer, color="#15803d")
p1.text("答题总纲：<b>简单、可衡量、可持续</b> —— 用能可靠解决问题的最简单架构，把效果变成数字，让系统可被持续迭代。",
        82, 872, 1500, 40, fs=16, bold=0)
p1.text("配套阅读：笔记《Agent 面试八站图文精编》 / 逐字稿原文", 82, 915, 900, 30, fs=12, bold=0, color="#64748b")

# ============ Page 2: 五件套 ============
p2 = Page("02-五件套-大脑与脊椎")
p2.text("第 2 站：架构五件套 —— 大脑与脊椎", 60, 24, 1100, 46, fs=28)

llm = p2.box("<b>LLM 模型</b><br/>推理 / 决策 / 生成", 190, 120, 300, 100, fill="#dbeafe", stroke="#2563eb", fs=15)
pln = p2.box("<b>Planning 规划</b><br/>任务拆解 / 路径选择 / 重规划", 550, 120, 340, 100, fill="#dbeafe", stroke="#2563eb", fs=15)
tol = p2.box("<b>Tools 工具</b><br/>与真实世界交互", 950, 120, 290, 100, fill="#fef3c7", stroke="#d97706", fs=15)
mem = p2.box("<b>Memory 记忆</b><br/>短期上下文 / 长期资产", 1290, 120, 290, 100, fill="#fef3c7", stroke="#d97706", fs=15)
p2.text("大脑层：决定「想什么」", 190, 228, 700, 26, fs=13, bold=0, color="#2563eb")
p2.text("能力层：决定「能和什么交互」", 950, 228, 700, 26, fs=13, bold=0, color="#b45309")

p2.text("脊椎：Harness 运行时 —— 最容易被漏掉，也是「demo 能跑、上线就崩」的主因", 60, 268, 1300, 32, fs=17, color="#b91c1c")
p2.box("", 60, 306, 1520, 214, fill="#fff5f5", stroke="#dc2626", fs=14)
inner = [("循环调度", "决定下一轮做什么"), ("上下文管理", "压缩 / 外置 / 隔离"),
         ("工具执行", "真正调用 · 参数校验"), ("错误恢复", "重试 / 熔断 / 降级")]
inids = []
for i, (t, s) in enumerate(inner):
    inids.append(p2.box(f"<b>{t}</b><br/>{s}", 100 + i * 375, 372, 330, 112, fill="#fee2e2", stroke="#dc2626"))

p2.edge(llm, pln, label="决策")
p2.edge(pln, inids[0], extra="exitX=0.5;exitY=1;entryX=0.5;entryY=0;", label="拆解")
p2.edge(inids[2], tol, extra="exitX=0.5;exitY=0;entryX=0.5;entryY=1;", label="执行")
p2.edge(inids[1], mem, extra="exitX=0.5;exitY=0;entryX=0.5;entryY=1;", label="读写")
p2.edge(inids[3], inids[0], extra="exitX=0.5;exitY=1;entryX=0.5;entryY=1;", label="再来一轮", dashed=1)
p2.edge(mem, inids[1], extra="exitX=1;exitY=0.5;entryX=1;entryY=0.5;", label="", dashed=1, arrow="none", color="#94a3b8")

p2.text("讲架构的话术：按「大脑 / 脊椎」的层级讲，比干巴巴报组件清单高一个段位。", 62, 560, 1200, 34, fs=16, bold=0, color="#334155")
p2.box("常见坑｜<b>只换更强模型，不修脊椎</b>：没有步数上限、没有循环检测、没有超时熔断、没有结构化错误回传。",
       62, 610, 1000, 70, fill="#fef2f2", stroke="#f87171", fs=14, bold=0)

# ============ Page 3: 核心循环 + FC 四拓扑 ============
p3 = Page("03-核心循环与工具拓扑")
p3.text("第 3 站：核心循环（Agent Loop）与 Function Calling 四拓扑", 60, 22, 1500, 42, fs=26)

th = p3.box("<b>Thought</b><br/>想下一步做什么", 120, 150, 250, 84, fill="#dbeafe", stroke="#2563eb")
ac = p3.box("<b>Action</b><br/>调哪个工具、传什么参", 120, 290, 250, 84, fill="#dcfce7", stroke="#16a34a")
ob = p3.box("<b>Observation</b><br/>工具真实返回", 120, 430, 250, 84, fill="#fef3c7", stroke="#d97706")
wall = p3.box("<b>上下文墙</b><br/><br/>每轮 Observation 都追加<br/>下一轮看到的是整面墙<br/>不只是最新一张",
              470, 150, 230, 364, fill="#fef9c3", stroke="#ca8a04", fs=13)
p3.edge(th, ac, extra="exitX=0.5;exitY=1;entryX=0.5;entryY=0;")
p3.edge(ac, ob, extra="exitX=0.5;exitY=1;entryX=0.5;entryY=0;")
p3.edge(ob, th, extra="exitX=0;exitY=0.5;entryX=0;entryY=0.5;", label="带着记忆再来一轮")
p3.edge(ob, wall, dashed=1, color="#ca8a04", arrow="none")
p3.edge(wall, th, dashed=1, color="#ca8a04", extra="exitX=0;exitY=0.5;entryX=1;entryY=0.5;", label="")

p3.text("循环上的三种变体", 780, 140, 500, 30, fs=17)
v1 = p3.box("<b>CoT 思维链</b><br/>只在脑子里想，容易想歪", 780, 190, 380, 80, fill="#f1f5f9", stroke="#64748b")
v2 = p3.box("<b>ToT 思维树</b><br/>展开多条路径，再挑最优", 780, 300, 380, 80, fill="#f1f5f9", stroke="#64748b")
v3 = p3.box("<b>ReAct</b><br/>整个循环主干，所有 Agent 的地基", 780, 410, 380, 80, fill="#bbf7d0", stroke="#15803d")
p3.text("变体都长在 Loop 这根主干上", 1200, 450, 420, 30, fs=13, bold=0, color="#475569")
p3.edge(v1, v3, dashed=1, arrow="none", color="#94a3b8")
p3.edge(v2, v3, dashed=1, arrow="none", color="#94a3b8")
p3.text("工程底线：模型只决定「调什么工具、传什么参数」，<b>真正执行的是你的代码</b>。", 780, 520, 760, 60, fs=15, bold=0, color="#b91c1c")

p3.text("Function Calling 四种调用拓扑", 60, 580, 700, 34, fs=20)

def mini(title, x0, y0, w=360, h=250):
    p3.text(f"<b>{title}</b>", x0, y0, w, 26, fs=14, color="#0f172a")
    p3.box("", x0, y0 + 30, w, h - 30, fill="#f8fafc", stroke="#cbd5e1", fs=12)

# 1) parallel
mini("① 并行：无依赖", 60, 630)
m1 = p3.box("模型", 190, 668, 100, 36, fill="#dbeafe", stroke="#2563eb", fs=12)
t1 = [p3.box(nm, 70 + i * 112, 740, 96, 34, fill="#dcfce7", stroke="#16a34a", fs=11)
      for i, nm in enumerate(["工具A", "工具B", "工具C"])]
s1 = p3.box("汇总", 190, 806, 100, 34, fill="#fef3c7", stroke="#d97706", fs=12)
for t in t1:
    p3.edge(m1, t, width=1.5)
    p3.edge(t, s1, width=1.5)

# 2) chain
mini("② 链式：有依赖", 460, 630)
c1 = p3.box("模型", 480, 668, 110, 34, fill="#dbeafe", stroke="#2563eb", fs=12)
c2 = p3.box("工具A", 480, 724, 110, 36, fill="#dcfce7", stroke="#16a34a", fs=12)
c3 = p3.box("工具B", 480, 780, 110, 36, fill="#dcfce7", stroke="#16a34a", fs=12)
c4 = p3.box("工具C", 480, 836, 110, 36, fill="#dcfce7", stroke="#16a34a", fs=12)
for a, b in [(c1, c2), (c2, c3), (c3, c4)]:
    p3.edge(a, b, width=1.5)
p3.text("顺序排队，结果传递", 616, 760, 190, 60, fs=11, bold=0, color="#475569")

# 3) conditional
mini("③ 条件：结果决定走向", 860, 630)
d1 = p3.box("模型", 950, 668, 120, 34, fill="#dbeafe", stroke="#2563eb", fs=12)
dd = p3.diamond("结果？", 960, 718, 110, 64, fs=11)
da = p3.box("工具A", 876, 806, 100, 34, fill="#dcfce7", stroke="#16a34a", fs=11)
db = p3.box("工具B", 1052, 806, 100, 34, fill="#dcfce7", stroke="#16a34a", fs=11)
p3.edge(d1, dd, width=1.5)
p3.edge(dd, da, label="分支1", width=1.5)
p3.edge(dd, db, label="分支2", width=1.5)

# 4) nested
mini("④ 嵌套：工具内部借工具", 1260, 630)
n1 = p3.box("模型", 1360, 668, 120, 34, fill="#dbeafe", stroke="#2563eb", fs=12)
n2 = p3.box("工具A", 1360, 724, 120, 38, fill="#dcfce7", stroke="#16a34a", fs=12)
n3 = p3.box("工具B", 1360, 782, 120, 38, fill="#fef3c7", stroke="#d97706", fs=12)
p3.edge(n1, n2, width=1.5)
p3.edge(n2, n3, width=1.5)

# ============ Page 4: 推理范式 + 选型 ============
p4 = Page("04-推理范式与选型")
p4.text("第 5 站：三种推理范式与选型决策", 60, 22, 1200, 42, fs=26)

def paradigm(x, title, color, fill, bullets):
    p4.box(f"<b>{title}</b>", x, 110, 400, 56, fill=color, stroke=fill, fs=17)
    p4.box(bullets, x, 176, 400, 200, fill="#ffffff", stroke=fill, fs=13, bold=0, valign="top")

paradigm(60, "ReAct", "#dbeafe", "#2563eb",
         "<b>边走边看</b>：走一步看一步<br/>· Thought / Action / Observation 交替<br/>· 适应未知环境，纠错快<br/>· 弱点：局部贪心，每步只看眼前最优<br/>· 三道保险：步数上限 / 循环检测 / 超时熔断")
paradigm(500, "Plan-and-Execute", "#dcfce7", "#16a34a",
         "<b>先画地图</b>：再出发<br/>· 强模型规划 + 轻模型执行，成本更低<br/>· 核心配套：动态重规划（回灌规划器）<br/>· ReWOO：一次排完所有调用，worker 并行<br/>· 前提：工具无依赖且都能确定成功")
paradigm(940, "Reflexion", "#fce7f3", "#db2777",
         "<b>自审 + 错题本</b>：挂在循环外的 Buff<br/>· 不是另一种循环，是循环外的一层<br/>· 每轮多 1~3 次调用，必须封顶<br/>· retry 是原样再来，reflection 是改了打法<br/>· 与多 Agent critic 的区别：自己审 vs 别人审")

p4.text("选型决策树（可以直接背）", 60, 410, 700, 34, fs=20)
q1 = p4.diamond("步骤能不能<br/>提前预判？", 120, 470, 220, 110, fs=13)
pe = p4.box("<b>Plan-and-Execute</b><br/>先规划后执行", 420, 440, 230, 80, fill="#dcfce7", stroke="#16a34a", fs=14)
re_ = p4.box("<b>ReAct</b><br/>边查边定", 420, 560, 230, 80, fill="#dbeafe", stroke="#2563eb", fs=14)
p4.edge(q1, pe, label="能")
p4.edge(q1, re_, label="不能")

q2 = p4.diamond("错了<br/>代价大不大？", 760, 470, 200, 110, fs=13)
p4.edge(pe, q2, extra="exitX=1;exitY=0.5;entryX=0.5;entryY=0;")
p4.edge(re_, q2, extra="exitX=1;exitY=0.5;entryX=0.5;entryY=1;")
add = p4.box("<b>叠加 Reflexion</b><br/>自审 + 错题本", 1020, 440, 240, 80, fill="#fce7f3", stroke="#db2777", fs=14)
keep = p4.box("就到这里", 1020, 570, 240, 70, fill="#f1f5f9", stroke="#64748b", fs=14)
p4.edge(q2, add, label="大")
p4.edge(q2, keep, label="不大")

simple = p4.box("任务很简单（比如查个股价）<br/><b>别上规划，纯浪费时间和 token</b>",
                1300, 470, 340, 100, fill="#fef3c7", stroke="#d97706", fs=13)
p4.box("<b>工业界真实做法</b><br/>先用 ReAct 跑通业务 → 看步数 / 延迟 / 出错率的数据 → 按需升级到 P&amp;E 或叠加 Reflexion。",
       60, 700, 900, 90, fill="#f0fdf4", stroke="#16a34a", fs=15, bold=0)
p4.box("<b>一句话切开 ReAct 与 CoT</b><br/>CoT 只在脑子里想；ReAct 每做一步就收回一条真实观察。<br/>区别在于<b>是否引入外部环境反馈</b>。",
       60, 820, 900, 90, fill="#eff6ff", stroke="#2563eb", fs=15, bold=0)
p4.text("代价必须主动说：无限反思 = 无限烧钱。", 1000, 830, 600, 40, fs=15, bold=0, color="#b91c1c")

# ============ Page 5: 生产化 ============
p5 = Page("05-生产化兜底与安全")
p5.text("第 8 站：生产化 —— 兜底四层与安全四护栏", 60, 22, 1200, 42, fs=26)

layers = [
    ("④ 消费层", "下游不认输出", "适配层 / 告警 / 转人工", "#fee2e2", "#dc2626", 110),
    ("③ 模型层", "幻觉、格式错、校验失败", "改 prompt / 回退备用模型", "#fef3c7", "#d97706", 240),
    ("② 推理层", "工具出错", "换工具 / 跳过 / 返回默认值", "#dcfce7", "#16a34a", 370),
    ("① 调用层", "网络超时", "重试 / 熔断 / 降级", "#dbeafe", "#2563eb", 500),
]
lids = []
for name, sym, fix, fill, stroke, y in layers:
    p5.box(f"<b>{name}</b>　{sym}", 80, y, 300, 90, fill=fill, stroke=stroke, fs=15)
    lids.append(p5.box(f"兜底：{fix}", 400, y, 420, 90, fill="#ffffff", stroke=stroke, fs=14, bold=0))
for k in range(3):
    p5.edge(lids[k + 1], ids and lids[k] or lids[k], extra="exitX=0.5;exitY=0;entryX=0.5;entryY=1;",
            label="向上传导" if k == 0 else "", dashed=1, color="#94a3b8")

p5.text("四道护栏（防提示词注入）", 900, 100, 700, 34, fs=20)
g1 = p5.box("<b>① 不可信数据隔离</b><br/>独立 Guard 检测层，与主模型不同上下文", 900, 150, 700, 80, fill="#fef2f2", stroke="#dc2626", fs=14)
g2 = p5.box("<b>② 最小权限</b><br/>按任务给权限；只读订单就别给改价", 900, 250, 700, 80, fill="#fff7ed", stroke="#ea580c", fs=14)
g3 = p5.box("<b>③ 沙箱执行</b><br/>高风险动作隔离运行", 900, 350, 700, 80, fill="#fefce8", stroke="#ca8a04", fs=14)
g4 = p5.box("<b>④ 高风险操作人工确认</b><br/>大额退款必须人点头", 900, 450, 700, 80, fill="#f0fdf4", stroke="#16a34a", fs=14)
p5.edge(g1, g2)
p5.edge(g2, g3)
p5.edge(g3, g4)
p5.text("12 字真经：<b>权限最小 · 输入消毒 · 输出审计</b>", 900, 550, 700, 40, fs=18, color="#b91c1c")
p5.text("提示词不负责安全，系统才负责安全。OWASP：83% 的 Agent 系统存在注入漏洞。",
       900, 600, 720, 60, fs=14, bold=0, color="#475569")

p5.text("上线翻车四种死法", 80, 630, 700, 34, fs=20)
deaths = [("死循环", "同一失败动作反复重试", "步数上限 + 循环检测"),
          ("幻觉参数", "工具入参全是编的", "入参强校验 schema，不认识直接拒"),
          ("越权", "该只读的能改价转账", "权限白名单 + 最小权限"),
          ("级联失败", "一个环节错全链路错", "交接处设错误边界")]
for i, (nm, sym, fix) in enumerate(deaths):
    p5.box(f"<b>{nm}</b>：{sym}", 80, 680 + i * 66, 400, 56, fill="#fef2f2", stroke="#f87171", fs=13)
    p5.box(fix, 500, 680 + i * 66, 360, 56, fill="#ffffff", stroke="#cbd5e1", fs=13, bold=0)

p5.text("评测三件套：真实日志数据集 → 分层指标（含错误分级）→ golden set 回归，改动即跑，掉阈值回滚。",
        900, 690, 720, 70, fs=14, bold=0, color="#334155")
p5.text("上线不是终点：bad case → 分析 → 定位 → 优化 → 回归验证。稳定是迭代出来的。",
        900, 780, 720, 70, fs=14, bold=0, color="#334155")

pages = [p1, p2, p3, p4, p5]
out = '<mxfile host="app.diagrams.net" type="device">\n' + "\n".join(p.xml() for p in pages) + "\n</mxfile>\n"
path = "/Users/vic/workspace-obsidian/Deliberate/6-ai/Agent 面试八站作战地图.drawio"
with open(path, "w", encoding="utf-8") as f:
    f.write(out)
print("written", path, len(out), "bytes,", len(pages), "pages")
