# -*- coding: utf-8 -*-
"""輸出單頁 HTML 與 Markdown 報表。

模板用 __PLACEHOLDER__ 取代，避免與 CSS 的大括號衝突。
"""

from indicators import LAYERS, STATE_LABEL, threshold_text

CSS = """
:root{--ground:#EDF0F2;--panel:#FFF;--ink:#16202B;--muted:#6C7A87;--rule:#D5DCE2;
--rule-soft:#E7ECEF;--safe:#1B7F5A;--warn:#C07A14;--danger:#BE3A2E;--ghost:#7A4A5B;
--serif:"Noto Serif TC",Georgia,serif;--sans:"Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif;
--mono:"IBM Plex Mono",ui-monospace,Menlo,monospace}
*{box-sizing:border-box}html,body{margin:0;padding:0}
body{background:var(--ground);color:var(--ink);font-family:var(--sans);font-size:15px;
line-height:1.6;-webkit-font-smoothing:antialiased}
.wrap{max-width:1080px;margin:0 auto;padding:28px 18px 64px}
.masthead{border-bottom:2px solid var(--ink);padding-bottom:14px;margin-bottom:20px}
.eyebrow{font-family:var(--mono);font-size:11px;letter-spacing:.18em;text-transform:uppercase;
color:var(--muted);margin:0 0 6px}
.masthead h1{font-family:var(--serif);font-weight:700;font-size:clamp(26px,5vw,40px);
line-height:1.15;letter-spacing:-.01em;margin:0 0 8px}
.masthead p{margin:0;color:var(--muted);font-size:13.5px;max-width:62ch}
.stamp{font-family:var(--mono);font-size:12px;color:var(--muted);margin-top:8px}
.ladder{background:var(--panel);border:1px solid var(--rule);padding:18px 16px 14px;margin-bottom:24px}
.ladder-head{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;
border-bottom:1px solid var(--rule-soft);padding-bottom:12px;margin-bottom:14px}
.ladder-head h2{font-family:var(--serif);font-size:17px;margin:0;font-weight:600}
.ladder-head .sub{font-size:12.5px;color:var(--muted)}
.depth{margin-left:auto;font-family:var(--mono);font-size:12px;border:1px solid var(--rule);padding:4px 10px}
.depth.hot{border-color:var(--danger);color:var(--danger)}
.rung{display:grid;grid-template-columns:96px 1fr 62px;gap:12px;align-items:center;padding:7px 0}
.rung+.rung{border-top:1px dashed var(--rule-soft)}
.rung-name{font-size:13px;font-weight:500}
.rung-name small{display:block;font-family:var(--mono);font-size:10px;color:var(--muted);letter-spacing:.06em}
.ticks{display:flex;gap:4px;height:22px}
.tick{flex:1;background:var(--rule-soft);border-radius:1px;min-width:8px}
.tick.safe{background:var(--safe)}.tick.warn{background:var(--warn)}.tick.danger{background:var(--danger)}
.rung-score{font-family:var(--mono);font-size:13px;text-align:right;color:var(--muted)}
.rung-score.hot{color:var(--danger);font-weight:600}
section{margin-bottom:24px}
.sec-head{display:flex;align-items:baseline;gap:10px;margin:0 0 4px}
.sec-num{font-family:var(--mono);font-size:12px;color:var(--muted);letter-spacing:.1em}
.sec-head h2{font-family:var(--serif);font-size:19px;margin:0;font-weight:600}
.sec-head .lead{font-size:12px;color:var(--muted);margin-left:auto;font-family:var(--mono)}
.sec-desc{font-size:11.5px;color:var(--muted);margin:0 0 8px}
table{width:100%;border-collapse:collapse;background:var(--panel);border:1px solid var(--rule)}
thead th{font-family:var(--mono);font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;
color:var(--muted);font-weight:500;text-align:left;padding:9px 10px;border-bottom:1px solid var(--rule)}
thead th.num{text-align:right}
tbody td{padding:9px 10px;border-bottom:1px solid var(--rule-soft);vertical-align:middle}
tbody tr:last-child td{border-bottom:none}
.ind-name{font-size:13.5px;font-weight:500;line-height:1.35}
.ind-note{font-size:11.5px;color:var(--muted);line-height:1.4;margin-top:2px}
.ind-note.stale{color:var(--danger)}
.ref{font-family:var(--mono);font-size:13.5px;color:var(--ghost);text-align:right;white-space:nowrap}
.ref small{display:block;font-size:10px;opacity:.75;letter-spacing:.05em}
.thresh{font-family:var(--mono);font-size:11.5px;color:var(--muted);text-align:right;white-space:nowrap}
.now{font-family:var(--mono);font-size:15px;text-align:right;white-space:nowrap;font-weight:500}
.now small{display:block;font-size:10px;color:var(--muted);font-weight:400;letter-spacing:.04em}
td.st{width:78px;text-align:right}
.badge{display:inline-block;font-family:var(--mono);font-size:11px;letter-spacing:.08em;
padding:3px 8px;border:1px solid currentColor;white-space:nowrap}
.badge.safe{color:var(--safe)}.badge.warn{color:var(--warn)}
.badge.danger{color:#fff;background:var(--danger);border-color:var(--danger)}
.badge.none{color:#AEB8C0}
.hist{background:var(--panel);border:1px solid var(--rule);padding:14px 16px;margin-top:8px}
.hist h2{font-family:var(--serif);font-size:17px;margin:0 0 10px;font-weight:600}
.hist-row{display:grid;grid-template-columns:104px 1fr 46px;gap:10px;align-items:center;
padding:6px 0;border-top:1px solid var(--rule-soft)}
.hist-row:first-child{border-top:none}
.hist-date{font-family:var(--mono);font-size:12.5px}
.bar{height:8px;background:var(--rule-soft)}.bar span{display:block;height:100%;background:var(--ink)}
.hist-score{font-family:var(--mono);font-size:12.5px;text-align:right}
.errs{margin-top:18px;border:1px solid var(--rule);background:var(--panel);padding:12px 14px}
.errs h3{font-family:var(--serif);font-size:14px;margin:0 0 6px;font-weight:600}
.errs li{font-size:11.5px;color:var(--muted);font-family:var(--mono)}
.disclaimer{margin-top:20px;font-size:11.5px;color:var(--muted);line-height:1.6;
border-top:1px dashed var(--rule);padding-top:12px}
@media (max-width:720px){
 body{font-size:14px}
 thead{display:none}
 table,tbody,tr,td{display:block;width:100%}
 table{border:none;background:transparent}
 tbody tr{background:var(--panel);border:1px solid var(--rule);margin-bottom:8px;padding:10px 12px;
  display:grid;grid-template-columns:1fr auto;gap:6px 10px}
 tbody td{border:none;padding:0}
 td.name{grid-column:1/-1}
 .ref,.thresh,.now{text-align:left}
 .ref::before{content:"2007 ";font-family:var(--mono);font-size:10px;color:var(--muted)}
 .thresh::before{content:"閾值 ";font-size:10px}
 td.st{text-align:right;align-self:center}
 .rung{grid-template-columns:80px 1fr 48px}
}
"""

PAGE = """<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>金融海嘯預警對照表 __DATE__</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Noto+Sans+TC:wght@400;500;700&family=Noto+Serif+TC:wght@600;700&display=swap" rel="stylesheet">
<style>__CSS__</style></head><body><div class="wrap">
<header class="masthead">
<p class="eyebrow">Credit Stress Monitor · 2007 vs Today</p>
<h1>金融海嘯預警對照表</h1>
<p>2008 是信用與槓桿危機，股價最後才反應。這張表盯的是資金的價格，不是資產的價格——依訊號領先時間分四層，看壓力傳導到了哪一層。</p>
<p class="stamp">更新時間 __STAMP__　·　綜合壓力 __SCORE__　·　已取得 __FILLED__／__TOTAL__ 項</p>
</header>
<div class="ladder">
<div class="ladder-head"><h2>壓力傳導階梯</h2>
<span class="sub">危機由上往下燒：結構失衡 → 信用收縮 → 流動性斷裂 → 台灣外溢</span>
<span class="depth __DEPTHCLS__">__DEPTH__</span></div>
__LADDER__
</div>
__SECTIONS__
<div class="hist"><h2>近期綜合壓力</h2>__HISTORY__</div>
__ERRORS__
<p class="disclaimer">2007 對照欄為該指標在危機前後的概略代表值，用於量級比較而非精確重建。SOFR−3個月國庫券為 TED spread 的免費代理，非等價指標。本頁為個人研究與紀錄工具，所載內容僅供參考，不構成任何投資建議或買賣要約，投資人應自行判斷並承擔風險。</p>
</div></body></html>
"""


def fmt_delta(ind, delta):
    """把 60 日變化寫成 +0.12 這種形式，沒有設定或取不到就回空字串。"""
    cfg = ind.get("delta")
    if not cfg or delta is None:
        return ""
    return f"　{cfg['lookback']}日 {delta:+g}{ind['unit']}"


def fmt_value(ind, value):
    if value is None:
        return "—"
    if ind["unit"] == "口":
        return f"{int(value):,}口"
    return f"{value:g}{ind['unit']}"


def build_html(results, summary, history, errors, stamp):
    by_layer = {l["id"]: [] for l in LAYERS}
    for r in results:
        by_layer[r["ind"]["layer"]].append(r)

    # 階梯
    rungs = []
    for layer in LAYERS:
        rows = by_layer[layer["id"]]
        pct = summary["layers"][layer["id"]]
        ticks = "".join(
            f'<span class="tick {"" if r["state"] == "none" else r["state"]}"></span>'
            for r in rows)
        hot = "hot" if pct is not None and pct >= 50 else ""
        rungs.append(
            f'<div class="rung"><div class="rung-name">{layer["name"]}'
            f'<small>{layer["short"]}</small></div>'
            f'<div class="ticks">{ticks}</div>'
            f'<div class="rung-score {hot}">{"—" if pct is None else str(pct) + "%"}</div></div>')

    # 各層表格
    sections = []
    for layer in LAYERS:
        body = []
        for r in by_layer[layer["id"]]:
            ind = r["ind"]
            note_cls = "ind-note stale" if r.get("stale") else "ind-note"
            note = ind["note"] + (f"　⚠ 資料已 {r['age_days']} 天未更新" if r.get("stale") else "")
            as_of = r["as_of"] or "無資料"
            body.append(
                f'<tr><td class="name"><div class="ind-name">{ind["name"]}</div>'
                f'<div class="{note_cls}">{note}</div></td>'
                f'<td><div class="ref">{ind["ref"]}{ind["unit"]}<small>{ind["ref_when"]}</small></div></td>'
                f'<td class="thresh">{threshold_text(ind)}</td>'
                f'<td class="now">{fmt_value(ind, r["value"])}'
                f'<small>{as_of}{fmt_delta(ind, r.get("delta"))}</small></td>'
                f'<td class="st"><span class="badge {r["state"]}">{STATE_LABEL[r["state"]]}</span></td></tr>')
        sections.append(
            f'<section><div class="sec-head"><span class="sec-num">{layer["num"]}</span>'
            f'<h2>{layer["name"]}</h2><span class="lead">{layer["lead"]}</span></div>'
            f'<p class="sec-desc">{layer["desc"]}</p>'
            f'<table><thead><tr><th>指標</th><th class="num">2007 對照</th>'
            f'<th class="num">閾值</th><th class="num">最新讀數</th><th class="num">狀態</th>'
            f'</tr></thead><tbody>{"".join(body)}</tbody></table></section>')

    hist_rows = []
    for date_s, score in history:
        width = 0 if score is None else score
        hist_rows.append(
            f'<div class="hist-row"><span class="hist-date">{date_s}</span>'
            f'<span class="bar"><span style="width:{width}%"></span></span>'
            f'<span class="hist-score">{"—" if score is None else score}</span></div>')
    hist_html = "".join(hist_rows) or '<p class="ind-note">尚無歷史紀錄。</p>'

    err_html = ""
    if errors:
        items = "".join(f"<li>{name}：{msg}</li>" for name, msg in errors)
        err_html = f'<div class="errs"><h3>本次未取得的指標</h3><ul>{items}</ul></div>'

    depth = summary["depth"]
    return (PAGE
            .replace("__CSS__", CSS)
            .replace("__DATE__", stamp[:10])
            .replace("__STAMP__", stamp)
            .replace("__SCORE__", "—" if summary["score"] is None else f'{summary["score"]}%')
            .replace("__FILLED__", str(summary["filled"]))
            .replace("__TOTAL__", str(summary["total"]))
            .replace("__DEPTH__", f"傳導深度：{depth}" if depth else "傳導深度：尚未觸發")
            .replace("__DEPTHCLS__", "hot" if depth else "")
            .replace("__LADDER__", "".join(rungs))
            .replace("__SECTIONS__", "".join(sections))
            .replace("__HISTORY__", hist_html)
            .replace("__ERRORS__", err_html))


def build_markdown(results, summary, errors, stamp):
    by_layer = {l["id"]: [] for l in LAYERS}
    for r in results:
        by_layer[r["ind"]["layer"]].append(r)

    icon = {"safe": "🟢", "warn": "🟡", "danger": "🔴", "none": "⚪"}
    out = [f"# 金融海嘯預警對照表 {stamp[:10]}", "",
           f"**綜合壓力** {'—' if summary['score'] is None else str(summary['score']) + '%'}　"
           f"**傳導深度** {summary['depth'] or '尚未觸發'}　"
           f"**已取得** {summary['filled']}/{summary['total']} 項", "",
           "| 層級 | 壓力 |", "|---|---|"]
    for layer in LAYERS:
        pct = summary["layers"][layer["id"]]
        out.append(f"| {layer['name']}（{layer['lead']}） | "
                   f"{'—' if pct is None else str(pct) + '%'} |")
    out.append("")

    for layer in LAYERS:
        out += [f"## {layer['num']} {layer['name']}", "",
                "| 狀態 | 指標 | 最新 | 2007 對照 | 閾值 | 資料日 |",
                "|---|---|---|---|---|---|"]
        for r in by_layer[layer["id"]]:
            ind = r["ind"]
            out.append(f"| {icon[r['state']]} {STATE_LABEL[r['state']]} | {ind['name']} | "
                       f"{fmt_value(ind, r['value'])}{fmt_delta(ind, r.get('delta'))} | {ind['ref']}{ind['unit']}"
                       f"（{ind['ref_when']}） | {threshold_text(ind)} | {r['as_of'] or '—'} |")
        out.append("")

    if errors:
        out += ["## 未取得的指標", ""]
        out += [f"- {name}：{msg}" for name, msg in errors]
        out.append("")

    out += ["---", "",
            "2007 對照欄為概略代表值，用於量級比較。本報表僅供參考，"
            "不構成任何投資建議或買賣要約，投資人應自行判斷並承擔風險。"]
    return "\n".join(out)
