# Upwork 新单扫描器

每天自动扫 Upwork 公开职位搜索，挑出**技术栈匹配 + 够新**的单子，落成一份 markdown。

## 为什么不用 curl

Upwork 对非浏览器请求直接回 Cloudflare 403，所以脚本用**真实 Chrome + CDP** 打开搜索页再取 DOM。首次运行会自己在 `/tmp/bu-upwork-scan` 建一个临时 Chrome 配置，跑完自动关掉。

## 用法

```bash
cd upwork-jobscan
python3 scan.py              # 默认扫最近 96 小时
python3 scan.py --hours 24   # 只看最近一天
python3 scan.py --all        # 不按时间过滤（调试用）
```

一次完整扫描约 2 分钟（10 个关键词 × 12 秒）。

产物：

```
runs/2026-10-26.md   # 当天的报告
.seen.json           # 见过哪些 job，避免重复推送
```

## 筛选逻辑

1. 10 个关键词，全部用 `sort=recency`（按发布时间倒序）
2. 丢掉标题/正文里出现 React、Flutter、Laravel、WordPress 等**不在武器库**的字样
3. 要求标题里有技术词，或正文命中 ≥2 个技术词（防止 "服装设计师" 这种噪音）
4. 打分：技术命中数 ×2 + 固定价 +1 + Entry/Intermediate +2 + **新鲜度加成（2h 内 +6 / 6h 内 +4 / 12h 内 +3 / 24h 内 +1）**
5. 按分数倒序，时间越新越靠前

## 改配置

- 想加/减关键词：改 `KEYWORDS`
- 调整"匹配"和"排除"的词：改 `GOOD` / `BAD`
- 新鲜度权重：改 `score()` 里那几档

## 已知限制

- **匿名访问看不到 "Payment verified" 徽章**，也过滤不了提案数（这两个过滤项要登录）。所以报告里的单子，投之前必须自己进 job 页确认右下角 About the client。
- 部分搜索结果其实是 **private listing**（点进去是 apply 页），这种投不了，直接跳过。
- 临时 Chrome 用的是干净配置，**没有你的 Upwork 登录态**——这是故意的，避免脚本动到你的账号。

## 每天怎么用

早上跑一次，看报告里 **评分 ≥ 6** 的，按 [../Upwork-接单判断清单.md](../Upwork-接单判断清单.md) 过一遍五条否决项，每天最多投 2 个。

> 2026-10-26 建立
