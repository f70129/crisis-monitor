# -*- coding: utf-8 -*-
"""資料抓取：FRED（免 API key 的 CSV 端點）、yfinance、FinMind。

每個抓取函式都回傳 (value, as_of, error)；失敗時 value=None 並帶錯誤訊息，
讓主程式能把單一指標標成「未取得」而不是整支腳本掛掉。
"""

import csv
import io
import os
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
    params = {"dataset": dataset, "token": FINMIND_TOKEN,
              "start_date": start, "end_date": end}
    if data_id:
        params["data_id"] = data_id
    resp = requests.get(FINMIND_URL, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    result = resp.json()
    if result.get("status") != 200:
        raise ValueError(f"FinMind 錯誤：{result.get('msg')}")
    return result.get("data", [])


def foreign_net5():
    """外資近 5 個交易日累計買賣超（億元）。"""
    data = fetch_finmind("TaiwanStockTotalInstitutionalInvestors", days=30)
    if not data:
        return None, None, "三大法人無資料"
    by_date = {}
    for row in data:
        if str(row.get("name", "")).startswith("Foreign"):
            by_date.setdefault(row["date"], 0)
            by_date[row["date"]] += float(row.get("difference", 0) or 0)
    if not by_date:
        return None, None, "找不到外資欄位"
    dates = sorted(by_date)[-5:]
    total = sum(by_date[d] for d in dates) / 1e8
    return round(total, 1), dates[-1], None


def txf_foreign_oi():
    """台指期(TX)外資淨未平倉口數。"""
    data = fetch_finmind("TaiwanFuturesInstitutionalInvestors", data_id="TX", days=30)
    if not data:
        return None, None, "台指期法人無資料"
    rows = [r for r in data if r.get("institutional_investor") == "外資"]
    if not rows:
        return None, None, "找不到外資未平倉"
    latest = max(r["date"] for r in rows)
    net = 0
    for r in rows:
        if r["date"] == latest:
            net += int(r.get("long_open_interest_balance_volume", 0) or 0)
            net -= int(r.get("short_open_interest_balance_volume", 0) or 0)
    return net, latest, None


def margin_chg20():
    """融資餘額近 20 個交易日變化率 (%)。"""
    data = fetch_finmind("TaiwanStockTotalMarginPurchaseShortSale", days=60)
    if not data:
        return None, None, "融資融券無資料"
    series = sorted(((r["date"], float(r.get("TodayBalance", 0) or 0)) for r in data),
                    key=lambda x: x[0])
    series = [(d, v) for d, v in series if v > 0]
    if len(series) < 21:
        return None, None, "融資餘額資料不足 21 筆"
    base = series[-21][1]
    val = round((series[-1][1] / base - 1) * 100, 2)
    return val, series[-1][0], None


def fred_delta(series_id, lookback):
    """最新值減去 lookback 期前的值。"""
    rows = fred_series(series_id)
    if len(rows) < lookback + 1:
        return None, None, f"{series_id} 資料不足 {lookback + 1} 筆"
    return round(rows[-1][1] - rows[-1 - lookback][1], 3), rows[-1][0], None


# ---------------------------------------------------------------- 分派
def fetch_delta(source, lookback):
    """取變化幅度。目前只有 FRED 單一序列支援，其餘回傳 none。"""
    try:
        kind, _, arg = source.partition(":")
        if kind == "fred":
            return fred_delta(arg, lookback)
        return None, None, f"{source} 不支援變化率"
    except Exception as exc:  # noqa: BLE001
        return None, None, f"{type(exc).__name__}: {exc}"


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
        return None, None, f"{type(exc).__name__}: {exc}"
