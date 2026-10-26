#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Upwork 新单扫描器（匿名版）

用真实 Chrome + CDP 抓 Upwork 公开搜索页（curl 会被 Cloudflare 403）。
按 sort=recency 拉取，只保留最近 N 小时内发布、且技术栈匹配的单子，
落一份 markdown 报告，并把见过的 job 记到 .seen.json 里避免重复推送。

用法：
    python3 scan.py            # 默认 36 小时内
    python3 scan.py --hours 12
    python3 scan.py --all      # 不按时间过滤，全量列出（调试用）
"""

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.parse
import urllib.request

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DEBUG_PORT = 9222
BASE = os.path.dirname(os.path.abspath(__file__))
SEEN = os.path.join(BASE, ".seen.json")
RUNS = os.path.join(BASE, "runs")
PROFILE = "/tmp/bu-upwork-scan"

KEYWORDS = os.environ.get("UPWORK_KEYWORDS", "").split(",") if os.environ.get("UPWORK_KEYWORDS") else [
    "kafka",
    "kafka streams",
    "flink",
    "spring boot",
    "spring batch",
    "java microservices",
    "elasticsearch",
    "payment gateway",
    "rocketmq",
    "hadoop hive",
    "java migration",
    "event driven",
]

# 命中任一 → 认为和你的技术栈相关
GOOD = [
    "java", "spring", "kafka", "flink", "backend", "back-end", "microservice",
    "elasticsearch", "payment", "fintech", "data engineer", "big data",
    "hadoop", "spark", "rocketmq", "rabbitmq", "postgres", "mysql",
]
# 命中任一 → 直接丢掉（不在你的武器库里）
BAD = [
    "react", "angular", "vue", "flutter", "laravel", "wordpress", "php",
    "shopify", "woocommerce", "swift", "kotlin", "ios developer",
    "android developer", "salesforce", "unity", "figma", "wix",
]


def log(msg):
    print(msg, flush=True)


def http_json(path):
    with urllib.request.urlopen(f"http://[::1]:{DEBUG_PORT}{path}", timeout=5) as r:
        return json.load(r)


def daemon_up():
    try:
        http_json("/json/version")
        return True
    except Exception:
        return False


def ensure_chrome():
    if daemon_up():
        return None
    log("· 启动临时 Chrome …")
    shutil.rmtree(PROFILE, ignore_errors=True)
    p = subprocess.Popen(
        [CHROME, f"--remote-debugging-port={DEBUG_PORT}", f"--user-data-dir={PROFILE}",
         "--no-first-run", "--no-default-browser-check", "--no-sandbox",
         "--disable-gpu", "--window-size=1440,900", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    for _ in range(30):
        time.sleep(1)
        if daemon_up():
            return p
    raise RuntimeError("Chrome 没起来（远程调试端口没响应）")


def close_chrome(p):
    if not p:
        return
    try:
        p.send_signal(signal.SIGTERM)
        p.wait(timeout=8)
    except Exception:
        try:
            p.kill()
        except Exception:
            pass


def connect():
    import websocket
    tabs = [t for t in http_json("/json/list") if t.get("type") == "page"]
    ws = websocket.create_connection(tabs[0]["webSocketDebuggerUrl"], timeout=90,
                                     suppress_origin=True)
    return ws


class CDP:
    def __init__(self, ws):
        self.ws = ws
        self.i = 0

    def cmd(self, method, params=None):
        self.i += 1
        self.ws.send(json.dumps({"id": self.i, "method": method, "params": params or {}}))
        while True:
            m = json.loads(self.ws.recv())
            if m.get("id") == self.i:
                return m

    def js(self, expr):
        r = self.cmd("Runtime.evaluate",
                     {"expression": expr, "returnByValue": True, "awaitPromise": True})
        return r.get("result", {}).get("result", {}).get("value")

    def goto(self, url, wait=12):
        self.cmd("Page.enable")
        self.cmd("Page.navigate", {"url": url})
        time.sleep(wait)


TILE_JS = r"""[...document.querySelectorAll('a[href*="/jobs/"]')].map(a => {
  let el = a;
  for (let k = 0; k < 7 && el; k++) { el = el.parentElement; if (el && el.innerText && el.innerText.length > 250) break; }
  return JSON.stringify({href: a.href.split('?')[0], text: el ? el.innerText : ''});
}).join('\u0001')"""


def parse_tile(href, text):
    lines = [x.strip() for x in text.split("\n") if x.strip()]
    if len(lines) < 2:
        return None
    posted = lines[0]
    if not posted.lower().startswith("posted"):
        return None
    title = re.sub(r"<[^>]+>", "", lines[1])
    rest = " | ".join(lines[2:7])
    budget = ""
    m = re.search(r"(Hourly: \$[\d.,]+ - \$[\d.,]+|Hourly|Fixed price)", rest)
    if m:
        budget = m.group(1)
    est = ""
    m = re.search(r"Est\. (?:budget|time):? \|? ?([^|]{0,60})", rest)
    if m:
        est = m.group(1).strip()
    level = ""
    m = re.search(r"\b(Entry Level|Intermediate|Expert)\b", rest)
    if m:
        level = m.group(1)
    desc = " ".join(lines[2:])[:600]
    return {
        "href": href, "posted": posted, "title": title, "budget": budget,
        "est": est, "level": level, "desc": desc,
    }


def hours_ago(posted):
    p = posted.lower()
    m = re.search(r"posted\s+(\d+)\s+minute", p)
    if m:
        return int(m.group(1)) / 60.0
    m = re.search(r"posted\s+(\d+)\s+hour", p)
    if m:
        return float(m.group(1))
    if "yesterday" in p:
        return 24.0
    m = re.search(r"posted\s+(\d+)\s+day", p)
    if m:
        return float(m.group(1)) * 24
    if "week" in p:
        return 24 * 7.0
    return 9999.0


def score(job):
    title = job["title"].lower()
    blob = (job["title"] + " " + job["desc"]).lower()
    if any(b in blob for b in BAD):
        return -1
    title_hits = sum(1 for g in GOOD if g in title)
    hits = sum(1 for g in GOOD if g in blob)
    # 标题里没有技术词、且正文命中不足 2 个 → 噪音，丢掉
    if title_hits == 0 and hits < 2:
        return -1
    s = hits * 2
    if "fixed price" in blob:
        s += 1
    if job["level"] in ("Entry Level", "Intermediate"):
        s += 2
    h = hours_ago(job["posted"])
    if h <= 2:
        s += 6
    elif h <= 6:
        s += 4
    elif h <= 12:
        s += 3
    elif h <= 24:
        s += 1
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=96)
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    os.makedirs(RUNS, exist_ok=True)
    seen = set()
    if os.path.exists(SEEN):
        try:
            seen = set(json.load(open(SEEN)))
        except Exception:
            seen = set()

    proc = ensure_chrome()
    try:
        job = CDP(connect())
        found = {}
        for kw in KEYWORDS:
            url = ("https://www.upwork.com/nx/search/jobs/?q="
                   + urllib.parse.quote(kw) + "&sort=recency")
            log(f"· 搜索: {kw}")
            job.goto(url, wait=12)
            raw = job.js(TILE_JS) or ""
            for chunk in raw.split("\u0001"):
                if not chunk.strip():
                    continue
                try:
                    d = json.loads(chunk)
                except Exception:
                    continue
                if "~0" not in d["href"]:
                    continue
                jid = re.search(r"~0\d+", d["href"]).group(0)
                d["href"] = re.sub(r"-span-class-highlight-[^-]+-span", "", d["href"])
                d["href"] = d["href"].replace("-amp-", "-")
                t = parse_tile(d["href"], d["text"])
                if not t:
                    continue
                t["query"] = kw
                found[jid] = t            # 按 job id 去重（同一单的 URL 会带高亮标记）
        log(f"  共抓到 {len(found)} 条")
    finally:
        close_chrome(proc)

    fresh = []
    for j in found.values():
        if not args.all and hours_ago(j["posted"]) > args.hours:
            continue
        s = score(j)
        if s < 0:
            continue
        j["score"] = s
        fresh.append(j)
    fresh.sort(key=lambda x: (-x["score"], hours_ago(x["posted"])))

    new = [j for j in fresh if j["href"] not in seen]
    seen.update(j["href"] for j in fresh)
    json.dump(sorted(seen), open(SEEN, "w"))

    today = time.strftime("%Y-%m-%d")
    path = os.path.join(RUNS, f"{today}.md")
    with open(path, "w") as f:
        f.write(f"# Upwork 新单 {today} {time.strftime('%H:%M')}\n\n")
        f.write(f"关键词 {len(KEYWORDS)} 个 · 抓到 {len(found)} 条 · "
                f"匹配 {len(fresh)} 条 · 其中新单 {len(new)} 条\n\n")
        for j in (new or fresh):
            f.write(f"## [{j['score']}分] {j['title']}\n\n")
            f.write(f"- 发布：{j['posted']}　级别：{j['level']}　类型：{j['budget']} {j['est']}\n")
            f.write(f"- 链接：{j['href']}\n")
            f.write(f"- 摘要：{j['desc'][:300]}\n\n")

    log(f"\n匹配 {len(fresh)} 条，其中新单 {len(new)} 条 → {path}")
    for j in (new or fresh)[:10]:
        log(f"  [{j['score']:>2}] {j['posted']:<22} {j['title'][:60]}")
        log(f"       {j['budget']} {j['est']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
