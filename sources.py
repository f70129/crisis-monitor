# -*- coding: utf-8 -*-
"""資料抓取：FRED（免 API key 的 CSV 端點）、yfinance、FinMind。

每個抓取函式都回傳 (value, as_of, error)；失敗時 value=None 並帶錯誤訊息，
讓主程式能把單一指標標成「未取得」而不是整支腳本掛掉。
"""

import csv
import io
import os
import re
from datetime import datetime, timedelta

import requests

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
FINMIND_URL = "https://api.finmindtrade.com/api/v4/data"
FINMIND_TOKEN = os.environ.get("FINMIND_TOKEN", "")
TIMEOUT = 30


# ---------------------------------------------------------------- FRED
def fred_series(series_id):
    """回傳 [(date_str, float)]，日期升冪，已剔除缺值。"""
    url = FRED_CSV.format(sid=series_id)
    resp = requests.get(url, timeout=TIMEOUT)
    resp.raise_for_status()
    rows = []
    reader = csv.reader(io.StringIO(resp.text))
    next(reader, None)  # 表頭
    for row in reader:
        if len(row) < 2:
            continue
        date_s, val_s = row[0].strip(), row[1].strip()
        if val_s in ("", "."):
            continue
        try:
            rows.append((date_s, float(val_s)))
        except ValueError:
            continue
    return rows


def fred_latest(series_id):
    rows = fred_series(series_id)
    if not rows:
        return None, None, "FRED 無資料"
    return rows[-1][1], rows[-1][0], None


def fred_yoy(series_id):
    """月頻指數轉年增率 (%)。"""
    rows = fred_series(series_id)
    if len(rows) < 13:
        return None, None, "FRED 資料不足 13 期"
    now, year_ago = rows[-1][1], rows[-13][1]
    if year_ago == 0:
        return None, None, "前期值為 0"
    return round((now / year_ago - 1) * 100, 2), rows[-1][0], None


def fred_spread(sid_a, sid_b):
    """兩個序列相減，取共同的最新日期，回傳 bp。"""
    a = dict(fred_series(sid_a))
    b = dict(fred_series(sid_b))
    common = sorted(set(a) & set(b))
    if not common:
        return None, None, f"{sid_a}/{sid_b} 無共同日期"
    d = common[-1]
    return round((a[d] - b[d]) * 100, 1), d, None


def fred_sahm(series_id="UNRATE"):
    """Sahm Rule：失業率3月移動均，減前12個月的3月移動均最低值。"""
    rows = fred_series(series_id)
    if len(rows) < 16:
        return None, None, "UNRATE 資料不足"
    vals = [v for _, v in rows]
    ma3 = [sum(vals[i - 2:i + 1]) / 3 for i in range(2, len(vals))]
    current = ma3[-1]
    prior_low = min(ma3[-13:-1])
    return round(current - prior_low, 2), rows[-1][0], None


# ---------------------------------------------------------------- yfinance
def _yf_close(ticker, period="2y"):
    import yfinance as yf
    df = yf.Ticker(ticker).history(period=period, auto_adjust=True)
    if df is None or df.empty or "Close" not in df:
        raise ValueError(f"{ticker} 無報價資料")
    s = df["Close"].dropna()
    if s.empty:
        raise ValueError(f"{ticker} 收盤價全為缺值")
    return s


def yf_drawdown(ticker, window=252):
    """距 52 週高點的百分比（負值）。"""
    s = _yf_close(ticker)
    recent = s.tail(window)
    peak = float(recent.max())
    if peak == 0:
        return None, None, "高點為 0"
    val = round((float(s.iloc[-1]) / peak - 1) * 100, 2)
    return val, str(s.index[-1].date()), None


def yf_change(ticker, lookback=20):
    """近 N 個交易日的變化率 (%)。"""
    s = _yf_close(ticker)
    if len(s) < lookback + 1:
        return None, None, f"{ticker} 資料不足 {lookback + 1} 筆"
    base = float(s.iloc[-(lookback + 1)])
    if base == 0:
        return None, None, "基期為 0"
    val = round((float(s.iloc[-1]) / base - 1) * 100, 2)
    return val, str(s.index[-1].date()), None


def yf_relative(ticker_a, ticker_b, lookback=20):
    """A 與 B 的近 N 日報酬差 (%)。"""
    a_val, a_date, a_err = yf_change(ticker_a, lookback)
    b_val, _, b_err = yf_change(ticker_b, lookback)
    if a_err or b_err:
        return None, None, a_err or b_err
    return round(a_val - b_val, 2), a_date, None


# ---------------------------------------------------------------- FinMind
def fetch_finmind(dataset, data_id="", days=60):
    if not FINMIND_TOKEN:
        raise ValueError("缺少 FINMIND_TOKEN")
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    # token 走 Authorization 標頭，不放在 URL，避免例外訊息帶出憑證
    params = {"dataset": dataset, "start_date": start, "end_date": end}
    if data_id:
        params["data_id"] = data_id
    headers = {"Authorization": f"Bearer {FINMIND_TOKEN}"}
    resp = requests.get(FINMIND_URL, params=params, headers=headers, timeout=TIMEOUT)
    resp.raise_for_status()
    result = resp.json()
    if result.get("status") != 200:
        raise ValueError(f"FinMind 錯誤：{result.get('msg')}")
    return result.get("data", [])


def _net_of(row):
    """買賣超金額。優先用 difference，缺欄位時退回 buy − sell。"""
    diff = row.get("difference")
    if diff not in (None, ""):
        return float(diff)
    return float(row.get("buy", 0) or 0) - float(row.get("sell", 0) or 0)


def _describe(data):
    """把實際欄位與字串值摘要出來，讓錯誤訊息足以定位問題。"""
    keys = sorted(data[0]) if data else []
    strings = {}
    for row in data[:200]:
        for k, v in row.items():
            if isinstance(v, str) and k != "date":
                strings.setdefault(k, set()).add(v)
    sample = {k: sorted(v)[:4] for k, v in strings.items()}
    return f"欄位={keys}　字串值={sample}"


def foreign_net5():
    """外資近 5 個交易日累計買賣超（億元）。

    只取 Foreign_Investor（外資及陸資），不含 Foreign_Dealer_Self，
    與看盤軟體的「外資買賣超」定義一致。
    """
    data = fetch_finmind("TaiwanStockTotalInstitutionalInvestors", days=30)
    if not data:
        return None, None, "三大法人無資料"
    by_date = {}
    for row in data:
        if row.get("name") == "Foreign_Investor":
            by_date[row["date"]] = by_date.get(row["date"], 0) + _net_of(row)
    if not by_date:
        return None, None, f"找不到 Foreign_Investor（{_describe(data)}）"
    dates = sorted(by_date)[-5:]
    if all(by_date[d] == 0 for d in dates):
        return None, None, f"買賣超金額全為 0，欄位不符（{_describe(data)}）"
    return round(sum(by_date[d] for d in dates) / 1e8, 1), dates[-1], None


def txf_foreign_oi():
    """台指期(TX)外資淨未平倉口數。

    法人欄位是 institutional_investors（複數）；若欄位名稱再變動，
    退回掃描所有字串欄位找含「外資」的值。
    """
    data = fetch_finmind("TaiwanFuturesInstitutionalInvestors", data_id="TX", days=30)
    if not data:
        return None, None, "台指期法人無資料"
    rows = [r for r in data if "外資" in str(r.get("institutional_investors", ""))]
    if not rows:
        rows = [r for r in data
                if any(isinstance(v, str) and "外資" in v for v in r.values())]
    if not rows:
        return None, None, f"找不到外資未平倉（{_describe(data)}）"
    latest = max(r["date"] for r in rows)
    net = 0
    for r in rows:
        if r["date"] == latest:
            net += int(r.get("long_open_interest_balance_volume", 0) or 0)
            net -= int(r.get("short_open_interest_balance_volume", 0) or 0)
    if net == 0:
        return None, None, f"外資未平倉口數為 0，欄位不符（{_describe(rows)}）"
    return net, latest, None


# 融資餘額的 name 值，依偏好順序。MarginPurchase 是張數、
# MarginPurchaseMoney 是金額，兩者同向變動、變化率一致。
# 絕不可用 ShortSale——那是融券，與融資經常反向。
MARGIN_NAMES = ("MarginPurchase", "MarginPurchaseMoney")


def margin_chg20():
    """融資餘額近 20 個交易日變化率 (%)。"""
    data = fetch_finmind("TaiwanStockTotalMarginPurchaseShortSale", days=60)
    if not data:
        return None, None, "融資融券無資料"

    available = {str(r.get("name", "")) for r in data}
    picked = next((n for n in MARGIN_NAMES if n in available), None)
    if picked is None:
        return None, None, f"找不到融資餘額項目（{_describe(data)}）"

    by_date = {}
    for row in data:
        if row.get("name") != picked:
            continue
        val = float(row.get("TodayBalance", 0) or 0)
        if val > 0:
            by_date[row["date"]] = val

    series = sorted(by_date.items())
    if len(series) < 21:
        return None, None, f"{picked} 資料不足 21 筆（實得 {len(series)} 筆）"

    base, latest = series[-21][1], series[-1][1]
    val = round((latest / base - 1) * 100, 2)
    if abs(val) > 40:
        return None, None, (f"融資餘額變化 {val}% 超出合理範圍"
                            f"（{picked}：基期 {base:g} → 最新 {latest:g}）")
    return val, series[-1][0], None


def fred_delta(series_id, lookback):
    """最新值減去 lookback 期前的值。"""
    rows = fred_series(series_id)
    if len(rows) < lookback + 1:
        return None, None, f"{series_id} 資料不足 {lookback + 1} 筆"
    return round(rows[-1][1] - rows[-1 - lookback][1], 3), rows[-1][0], None


def safe_error(exc):
    """把例外轉成可以公開的訊息。

    report.md 與 history.json 會 commit 進公開 repo，而 GitHub 的自動遮蔽只作用在
    Actions log、不作用在檔案內容。所以這裡把憑證與整段 URL 都拿掉再往外傳。
    """
    msg = f"{type(exc).__name__}: {exc}"
    for secret in (FINMIND_TOKEN,
                   os.environ.get("TELEGRAM_BOT_TOKEN", ""),
                   os.environ.get("TELEGRAM_CHAT_ID", "")):
        if secret and len(secret) >= 6:
            msg = msg.replace(secret, "***")
    msg = re.sub(r"https?://\S+", "<url>", msg)
    msg = re.sub(r"(?i)(token|authorization|bearer|api[_-]?key)[=:\s]+\S+",
                 r"\1=***", msg)
    return msg[:200]


# ---------------------------------------------------------------- 分派
def fetch_delta(source, lookback):
    """取變化幅度。目前只有 FRED 單一序列支援，其餘回傳 none。"""
    try:
        kind, _, arg = source.partition(":")
        if kind == "fred":
            return fred_delta(arg, lookback)
        return None, None, f"{source} 不支援變化率"
    except Exception as exc:  # noqa: BLE001
        return None, None, safe_error(exc)


def fetch(source):
    """依 source 字串取值，統一回傳 (value, as_of, error)。"""
    try:
        kind, _, arg = source.partition(":")
        if kind == "fred":
            return fred_latest(arg)
        if kind == "fred_yoy":
            return fred_yoy(arg)
        if kind == "fred_spread":
            a, b = arg.split("-", 1)
            return fred_spread(a, b)
        if kind == "fred_sahm":
            return fred_sahm(arg)
        if kind == "yf_drawdown":
            return yf_drawdown(arg)
        if kind == "yf_change":
            return yf_change(arg)
        if kind == "yf_relative":
            a, b = arg.split("-", 1)
            return yf_relative(a, b)
        if kind == "finmind":
            return {"foreign_net5": foreign_net5,
                    "txf_foreign_oi": txf_foreign_oi,
                    "margin_chg20": margin_chg20}[arg]()
        return None, None, f"未知來源 {source}"
    except Exception as exc:  # noqa: BLE001 — 單一指標失敗不應中斷整份報告
        return None, None, safe_error(exc)
