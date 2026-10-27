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
            shape="rounded=1", fs=14, bold=1, align="center", dashed=0, font_color="#1f2937"):
        i = self._id()
        style = (f"{shape};whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};"
                 f"strokeWidth=2;fontSize={fs};fontStyle={bold};align={align};verticalAlign=middle;"
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
    def edge(self, src, tgt, style_extra="", label="", dashed=0, color="#334155", width=2, arrow="block"):
        i = self._id("e")
        style = (f"edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;strokeWidth={width};strokeColor={color};"
                 f"endArrow={arrow};endFill=1;dashed={dashed};fontSize=12;{style_extra}")
        self.cells.append(
            f'<mxCell id="{i}" value="{esc(label)}" style="{style}" edge="1" parent="1" source="{src}" target="{tgt}">'
            f'<mxGeometry relative="1" as="geometry"/></mxCell>')
        return i
    def xml(self):
        body = "\n        ".join(self.cells)
        return (f'<diagram name="{esc(self.name)}" id="{esc(self.name)}">\n'
                f'  <mxGraphModel dx="1600" dy="1000" grid="1" gridSize="10" guides="1" tooltips="1" '
                f'connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{W}" pageHeight="{H}" '
                f'math="0" shadow="0">\n    <root>\n      <mxCell id="0"/>\n      <mxCell id="1" parent="0"/>\n'
                f'      {body}\n    </root>\n  </mxGraphModel>\n</diagram>')

# ---------------- Page 1: 八站全景 ----------------
p1 = Page("01-八站全景")
p1.text("Agent 面试八站作战地图", 60, 24, 900, 46, fs=30, bold=1)
p1.text("一条主线：从「它是什么」一路推到「30 秒讲清我的项目」", 62, 72, 1000, 30, fs=15, bold=0, color="#475569")

sta = [
    ("第 1 站  概念与边界", "Agent = 会调用工具的循环系统<br/>三判句定生死", "#dbeafe", "#2563eb"),
    ("第 2 站  架构五件套", "模型是大脑，Harness 是脊椎<br/>上线就崩多半是脊椎塌了", "#e0e7ff", "#4338ca"),
    ("第 3 站  核心循环", "Thought → Action → Observation<br/>上下文在循环里累积", "#dcfce7", "#16a34a"),
    ("第 4 站  工具与协议", "FC 是模型层能力，MCP 是生态层标准<br/>M×N 变 M+N", "#fef3c7", "#d97706"),
    ("第 5 站  推理范式", "ReAct 地基 / P&E 全局 / Reflexion 自审<br/>选型看能否预判步骤", "#fce7f3", "#db2777"),
    ("第 6 站  记忆与上下文", "三层记忆 + 四招压缩<br/>上下文越少越准", "#cffafe", "#0891b2"),
    ("第 7 站  多智能体与 RAG", "三种编排 · 15 倍成本<br/>能不用就不用", "#ede9fe", "#7c3aed"),
    ("第 8 站  生产化与实战", "四种死法 · 兜底四层 · 评测闭环<br/>简单 可衡量 可持续", "#fee2e2", "#dc2626"),
]
xs = [80, 500, 920, 1340]
ids = []
for idx, (t, sub, fill, stroke) in enumerate(sta):
    row = idx // 4
    col = idx % 4 if row == 0 else 3 - (idx % 4)
    x = xs[col]
    y = 140 if row == 0 else 470
    i = p1.box(f"<b>{t}</b><br/><br/>{sub}", x, y, 300, 130, fill=fill, stroke=stroke, fs=14)
    ids.append(i)

for k in range(3):
    p1.edge(ids[k], ids[k+1], color="#475569")
p1.edge(ids[3], ids[4], color="#475569")
for k in range(4, 7):
    p1.edge(ids[k], ids[k+1], color="#475569")

offer = p1.box("<b>Offer</b><br/>原理能推导 · 组件能画图<br/>系统能落地 · 坏 case 能复盘",
               690, 730, 420, 110, fill="#bbf7d0", stroke="#15803d", fs=15)
p1.edge(ids[7], offer, color="#15803d")

p1.text("答题总纲：<b>简单、可衡量、可持续</b> —— 用能可靠解决问题的最简单架构，把效果变成数字，让系统可被持续迭代。",
        82, 880, 1500, 40, fs=16, bold=0, color="#0f172a")
p1.text("配套 mermaid 版见笔记《Agent 面试八站图文精编》", 82, 920, 900, 30, fs=12, bold=0, color="#64748b")

# ---------------- Page 2: 五件套 ----------------
p2 = Page("02-五件套大脑与脊椎")
p2.text("第 2 站：架构五件套 —— 大脑与脊椎", 60, 24, 1100, 46, fs=28)

p2.box("<b>🧠 LLM 模型</b><br/>推理 / 决策 / 生成", 200, 120, 300, 100, fill="#dbeafe", stroke="#2563eb", fs=15)
p2.box("<b>🗺️ Planning 规划</b><br/>任务拆解 / 路径选择 / 重规划", 560, 120, 330, 100, fill="#dbeafe", stroke="#2563eb", fs=15)
p2.box("<b>🧰 Tools 工具</b><br/>与真实世界交互", 950, 120, 290, 100, fill="#fef3c7", stroke="#d97706", fs=15)
p2.box("<b>💾 Memory 记忆</b><br/>短期上下文 / 长期资产", 1290, 120, 290, 100, fill="#fef3c7", stroke="#d97706", fs=15)

p2.text("🦴 脊椎：Harness 运行时（最容易被漏掉，也是上线就崩的主因）", 60, 270, 1200, 34, fs=17, bold=1, color="#b91c1c")
harness = p2.box("", 60, 310, 1520, 210, fill="#fff5f5", stroke="#dc2626", fs=14)
inner = [
    ("循环调度", "决定下一轮做什么"),
    ("上下文管理", "压缩 / 外置 / 隔离"),
    ("工具执行", "真正调用、校验参数"),
    ("错误恢复", "重试 / 熔断 / 降级"),
]
inner_ids = []
for i, (t, s) in enumerate(inner):
    inner_ids.append(p2.box(f"<b>{t}</b><br/>{s}", 100 + i * 375, 380, 330, 110, fill="#fee2e2", stroke="#dc2626", fs=14))

p2.edge(ids and p2.cells[1] or "", "")  # placeholder removed below
