# -*- coding: utf-8 -*-
"""每日執行：抓資料 → 評分 → 產出 HTML/Markdown → 推 Telegram。

用法：
    python monitor.py            # 正常執行
    python monitor.py --dry-run  # 不寫檔、不推播，只印結果
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta

import requests

import sources
from indicators import (INDICATORS, LAYERS, STATE_LABEL, STATE_POINTS,
                        state_of, threshold_text)
from render import build_html, build_markdown, fmt_value

ROOT = os.path.dirname(os.path.abspath(__file__))
MANUAL_PATH = os.path.join(ROOT, "manual.json")
HISTORY_PATH = os.path.join(ROOT, "data", "history.json")
LATEST_PATH = os.path.join(ROOT, "data", "latest.json")
HTML_PATH = os.path.join(ROOT, "docs", "index.html")
MD_PATH = os.path.join(ROOT, "report.md")

TPE = timezone(timedelta(hours=8))
HISTORY_KEEP = 120


# ------------------------------------------------------------------ 讀取
def load_manual():
    if not os.path.exists(MANUAL_PATH):
        return {}
    with open(MANUAL_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def load_history():
    if not os.path.exists(HISTORY_PATH):
        return {}
    with open(HISTORY_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def age_in_days(as_of, today):
    try:
        return (today - datetime.strptime(as_of, "%Y-%m-%d").date()).days
    except (ValueError, TypeError):
        return None


# ------------------------------------------------------------------ 收集
def collect(manual, today):
    results, errors = [], []
    for ind in INDICATORS:
        if ind["source"] == "manual":
            entry = manual.get(ind["id"]) or {}
            value = entry.get("value")
            as_of = entry.get("as_of")
            err = None if value is not None else "manual.json 尚未填入"
        else:
            value, as_of, err = sources.fetch(ind["source"])

        age = age_in_days(as_of, today) if as_of else None
        stale = (ind["source"] == "manual" and age is not None
                 and age > ind.get("stale_days", 60))

        if err and not ind.get("optional"):
            errors.append((ind["name"], err))

        results.append({"ind": ind, "value": value, "as_of": as_of,
                        "state": state_of(ind, value), "error": err,
                        "age_days": age, "stale": stale})
    return results, errors


def summarize(results):
    layers, pts_all, max_all = {}, 0, 0
    for layer in LAYERS:
        rows = [r for r in results if r["ind"]["layer"] == layer["id"]]
        filled = [r for r in rows if r["state"] != "none"]
        if not filled:
            layers[layer["id"]] = None
            continue
        pts = sum(STATE_POINTS[r["state"]] for r in filled)
        layers[layer["id"]] = round(pts / (len(filled) * 2) * 100)
        pts_all += pts
        max_all += len(filled) * 2

    hot = [l for l in LAYERS if layers[l["id"]] is not None and layers[l["id"]] >= 50]
    filled_n = sum(1 for r in results if r["state"] != "none")
    return {"layers": layers,
            "score": round(pts_all / max_all * 100) if max_all else None,
            "depth": hot[-1]["name"] if hot else None,
            "filled": filled_n, "total": len(results)}


def diff_states(results, prev_states):
    """回傳今日狀態較前一次惡化的指標。"""
    order = {"none": -1, "safe": 0, "warn": 1, "danger": 2}
    changed = []
    for r in results:
        before = prev_states.get(r["ind"]["id"])
        if before is None or r["state"] == "none":
            continue
        if order[r["state"]] > order.get(before, -1):
            changed.append((r["ind"]["name"], before, r["state"]))
    return changed


# ------------------------------------------------------------------ 推播
def pages_url():
    """在 Actions 環境中由 GITHUB_REPOSITORY 推出 Pages 網址；本機執行回傳 None。
    也可用 PAGES_URL 環境變數直接覆寫（自訂網域時用）。"""
    override = os.environ.get("PAGES_URL", "").strip()
    if override:
        return override
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" not in repo:
        return None
    owner, name = repo.split("/", 1)
    root = f"https://{owner.lower()}.github.io"
    return root + "/" if name.lower() == f"{owner.lower()}.github.io" else f"{root}/{name}/"


def telegram(text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        print("[telegram] 未設定 token/chat_id，略過推播")
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(url, timeout=30, data={
        "chat_id": chat_id, "text": text,
        "parse_mode": "HTML", "disable_web_page_preview": "true"})
    ok = resp.ok and resp.json().get("ok")
    print(f"[telegram] {'已送出' if ok else '送出失敗：' + resp.text[:200]}")
    return ok


def build_telegram(results, summary, changed, stale, errors, stamp, link=None):
    icon = {"safe": "🟢", "warn": "🟡", "danger": "🔴", "none": "⚪"}
    lines = [f"<b>金融海嘯預警對照表 {stamp[:10]}</b>",
             f"綜合壓力 <b>{'—' if summary['score'] is None else str(summary['score']) + '%'}</b>"
             f"　傳導深度 <b>{summary['depth'] or '尚未觸發'}</b>", ""]
    for layer in LAYERS:
        pct = summary["layers"][layer["id"]]
        lines.append(f"{layer['name']}　{'—' if pct is None else str(pct) + '%'}")

    hot = [r for r in results if r["state"] == "danger"]
    if hot:
        lines += ["", "<b>危險區</b>"]
        lines += [f"{icon['danger']} {r['ind']['name']}　{fmt_value(r['ind'], r['value'])}"
                  for r in hot]

    if changed:
        lines += ["", "<b>今日惡化</b>"]
        lines += [f"• {name}　{STATE_LABEL[a]} → {STATE_LABEL[b]}" for name, a, b in changed]

    if stale:
        lines += ["", "<b>手動資料過期</b>"]
        lines += [f"• {r['ind']['name']}　已 {r['age_days']} 天未更新" for r in stale]

    if errors:
        lines += ["", f"未取得 {len(errors)} 項：" + "、".join(n for n, _ in errors[:5])]

    if link:
        lines += ["", f'<a href="{link}">開啟完整對照表</a>']

    lines += ["", "本訊息僅供參考，不構成投資建議。"]
    return "\n".join(lines)


# ------------------------------------------------------------------ 主流程
def main():
    dry = "--dry-run" in sys.argv
    now = datetime.now(TPE)
    stamp = now.strftime("%Y-%m-%d %H:%M") + " (台北)"
    today = now.date()
    date_key = now.strftime("%Y-%m-%d")

    manual = load_manual()
    results, errors = collect(manual, today)
    summary = summarize(results)

    history = load_history()
    prev_keys = sorted(k for k in history if k != date_key)
    prev_states = history[prev_keys[-1]]["states"] if prev_keys else {}
    changed = diff_states(results, prev_states)
    stale = [r for r in results if r.get("stale")]

    history[date_key] = {
        "score": summary["score"],
        "layers": summary["layers"],
        "states": {r["ind"]["id"]: r["state"] for r in results},
        "values": {r["ind"]["id"]: r["value"] for r in results},
    }
    for key in sorted(history)[:-HISTORY_KEEP]:
        del history[key]

    recent = [(k, history[k]["score"]) for k in sorted(history, reverse=True)[:14]]
    html = build_html(results, summary, recent, errors, stamp)
    md = build_markdown(results, summary, errors, stamp)
    msg = build_telegram(results, summary, changed, stale, errors, stamp, pages_url())

    print(md)
    if dry:
        print("\n--- Telegram 預覽 ---\n" + msg)
        return

    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(HTML_PATH), exist_ok=True)
    with open(HISTORY_PATH, "w", encoding="utf-8") as fh:
        json.dump(history, fh, ensure_ascii=False, indent=1, sort_keys=True)
    with open(LATEST_PATH, "w", encoding="utf-8") as fh:
        json.dump(history[date_key], fh, ensure_ascii=False, indent=1, sort_keys=True)
    with open(HTML_PATH, "w", encoding="utf-8") as fh:
        fh.write(html)
    with open(MD_PATH, "w", encoding="utf-8") as fh:
        fh.write(md)

    telegram(msg)


if __name__ == "__main__":
    main()
