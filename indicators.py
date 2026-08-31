# -*- coding: utf-8 -*-
"""指標定義：閾值、2007 對照值、資料來源。

dir = "low"  → 數值越低越危險（利差、房價年增、外資買賣超…）
dir = "high" → 數值越高越危險（信用利差、VIX、Sahm、台幣貶幅…）
"""

LAYERS = [
    {"id": "structure", "num": "01", "name": "結構失衡", "short": "STRUCTURE",
     "lead": "領先 12–18 個月", "desc": "槓桿與房市已經歪掉，但市場還沒開始付代價"},
    {"id": "credit", "num": "02", "name": "信用收縮", "short": "CREDIT",
     "lead": "領先 6–12 個月", "desc": "銀行開始縮手、風險溢酬回補，股市通常還在高檔"},
    {"id": "liquidity", "num": "03", "name": "流動性斷裂", "short": "LIQUIDITY",
     "lead": "領先 1–6 個月", "desc": "錢開始借不到。到這一層，時間就不是用年在算了"},
    {"id": "taiwan", "num": "04", "name": "台灣外溢", "short": "TAIWAN",
     "lead": "同步至落後 1–3 個月", "desc": "台股是外資與出口的槓桿放大器，跟在美國信用訊號之後"},
]

INDICATORS = [
    # ---------- 01 結構失衡 ----------
    {"id": "y10y3m", "layer": "structure", "name": "10年–3個月 殖利率利差",
     "note": "本循環倒掛已發生過，現在看的是陡峭化速度（無法區分多頭/空頭陡峭化，需搭配短端方向判讀）",
     "unit": "%", "dir": "low", "warn": 0.5, "danger": 0.0,
     "delta": {"lookback": 60, "dir": "high", "warn": 0.4, "danger": 0.7},
     "ref": "−0.36", "ref_when": "2007/01", "source": "fred:T10Y3M"},

    {"id": "y10y2y", "layer": "structure", "name": "10年–2年 殖利率利差",
     "note": "比 10Y–3M 早倒掛，但雜訊較多",
     "unit": "%", "dir": "low", "warn": 0.3, "danger": 0.0,
     "ref": "−0.19", "ref_when": "2006/11", "source": "fred:T10Y2Y"},

    {"id": "cshiller", "layer": "structure", "name": "Case-Shiller 20城 房價年增率",
     "note": "2006 年底就翻負，領先股市高點近一年",
     "unit": "%", "dir": "low", "warn": 3.0, "danger": 0.0,
     "ref": "−9.1", "ref_when": "2007/12", "source": "fred_yoy:SPCS20RSA"},

    {"id": "nahb", "layer": "structure", "name": "NAHB 住宅市場指數",
     "note": "建商信心，房市最靈敏的月更指標",
     "unit": "", "dir": "low", "warn": 50, "danger": 35,
     "ref": "20", "ref_when": "2007/09", "source": "manual", "stale_days": 45},

    # ---------- 02 信用收縮 ----------
    {"id": "sloos", "layer": "credit", "name": "SLOOS 商用放款淨緊縮比例",
     "note": "季更。翻正代表銀行開始關水龍頭",
     "unit": "%", "dir": "high", "warn": 0, "danger": 20,
     "ref": "32", "ref_when": "2007Q4", "source": "manual", "stale_days": 120},

    {"id": "hyoas", "layer": "credit", "name": "高收益債利差 HY OAS",
     "note": "絕對值低不代表安全，擴大速度才是訊號：60日擴大 100bp 直接判警戒",
     "unit": "%", "dir": "high", "warn": 3.5, "danger": 4.5,
     "delta": {"lookback": 60, "dir": "high", "warn": 1.0, "danger": 1.5},
     "ref": "5.7", "ref_when": "2007/12", "source": "fred:BAMLH0A0HYM2"},

    {"id": "igoas", "layer": "credit", "name": "投資級債利差 IG OAS",
     "note": "IG 也擴代表壓力不只在垃圾債",
     "unit": "%", "dir": "high", "warn": 1.0, "danger": 1.3,
     "ref": "1.8", "ref_when": "2007/12", "source": "fred:BAMLC0A0CM"},

    {"id": "xlfdd", "layer": "credit", "name": "XLF 距 52 週高點",
     "note": "金融股先跌，2007 年初就領先大盤走弱",
     "unit": "%", "dir": "low", "warn": -10, "danger": -20,
     "ref": "−25", "ref_when": "2007/11", "source": "yf_drawdown:XLF"},

    # ---------- 03 流動性斷裂 ----------
    {"id": "sofrproxy", "layer": "liquidity", "name": "SOFR − 3個月國庫券（資金壓力代理）",
     "note": "免費代理；當年對應指標為 TED spread，非等價但方向一致",
     "unit": "bp", "dir": "high", "warn": 15, "danger": 30,
     "ref": "240", "ref_when": "2007/08 (TED)", "source": "fred_spread:SOFR-DTB3"},

    {"id": "xccy", "layer": "liquidity", "name": "3個月 歐元/美元 交叉貨幣基差",
     "note": "無免費來源，需手動；轉深負值＝美元荒",
     "unit": "bp", "dir": "low", "warn": -25, "danger": -50,
     "ref": "−90", "ref_when": "2007/12", "source": "manual", "stale_days": 30,
     "optional": True},

    {"id": "sahm", "layer": "liquidity", "name": "Sahm Rule 值",
     "note": "失業率3月均值減前12月低點，≥0.5 視為衰退已開始",
     "unit": "pp", "dir": "high", "warn": 0.3, "danger": 0.5,
     "ref": "0.53", "ref_when": "2008/01", "source": "fred_sahm:UNRATE"},

    {"id": "vix", "layer": "liquidity", "name": "VIX",
     "note": "確認用不是預警用——VIX 通常最後才動",
     "unit": "", "dir": "high", "warn": 20, "danger": 30,
     "ref": "30.8", "ref_when": "2007/08", "source": "fred:VIXCLS"},

    {"id": "hygspy", "layer": "liquidity", "name": "HYG 減 SPY 近20日報酬",
     "note": "信用先破底、股市還創高＝背離，信用通常對",
     "unit": "%", "dir": "low", "warn": -1.5, "danger": -3.0,
     "ref": "−6", "ref_when": "2007/11", "source": "yf_relative:HYG-SPY"},

    # ---------- 04 台灣外溢 ----------
    {"id": "exports", "layer": "taiwan", "name": "外銷訂單年增率",
     "note": "連續3個月負成長是實質確認（經濟部統計處）",
     "unit": "%", "dir": "low", "warn": 0, "danger": -5,
     "ref": "−28.6", "ref_when": "2008/11", "source": "manual", "stale_days": 60},

    {"id": "bizsig", "layer": "taiwan", "name": "景氣對策信號分數",
     "note": "16分以下為藍燈（國發會）",
     "unit": "分", "dir": "low", "warn": 22, "danger": 16,
     "ref": "9", "ref_when": "2008/12", "source": "manual", "stale_days": 45},

    {"id": "fininet", "layer": "taiwan", "name": "外資近5日累計買賣超",
     "note": "連續大額賣超搭配匯出才算訊號",
     "unit": "億", "dir": "low", "warn": -200, "danger": -500,
     "ref": "−900", "ref_when": "2008/09", "source": "finmind:foreign_net5"},

    {"id": "txfoi", "layer": "taiwan", "name": "台指期外資淨未平倉",
     "note": "淨空單快速擴大＝外資避險加碼",
     "unit": "口", "dir": "low", "warn": -5000, "danger": -15000,
     "ref": "−20000", "ref_when": "2008/10", "source": "finmind:txf_foreign_oi"},

    {"id": "margin", "layer": "taiwan", "name": "融資餘額近20日變化",
     "note": "急速去化＝散戶被斷頭",
     "unit": "%", "dir": "low", "warn": -5, "danger": -10,
     "ref": "−25", "ref_when": "2008/10", "source": "finmind:margin_chg20"},

    {"id": "twd", "layer": "taiwan", "name": "台幣近20日貶值幅度",
     "note": "正值為貶值；急貶常伴隨外資匯出",
     "unit": "%", "dir": "high", "warn": 1.5, "danger": 3.0,
     "ref": "5.2", "ref_when": "2008/10", "source": "yf_change:TWD=X"},
]

STATE_LABEL = {"safe": "安全", "warn": "警戒", "danger": "危險", "none": "未取得"}
STATE_POINTS = {"safe": 0, "warn": 1, "danger": 2}
STATE_ORDER = {"none": -1, "safe": 0, "warn": 1, "danger": 2}


def worse(state_a, state_b):
    """取兩個狀態中較嚴重者；none 不會蓋掉已判定的狀態。"""
    return state_a if STATE_ORDER[state_a] >= STATE_ORDER[state_b] else state_b


def delta_state(ind, delta):
    """依變化幅度判定狀態。沒有設定 delta 或取不到值時回傳 none。"""
    cfg = ind.get("delta")
    if not cfg or delta is None:
        return "none"
    d = float(delta)
    if cfg["dir"] == "low":
        if d <= cfg["danger"]:
            return "danger"
        return "warn" if d <= cfg["warn"] else "safe"
    if d >= cfg["danger"]:
        return "danger"
    return "warn" if d >= cfg["warn"] else "safe"


def state_of(ind, value):
    """依閾值判定狀態。"""
    if value is None:
        return "none"
    v = float(value)
    if ind["dir"] == "low":
        if v <= ind["danger"]:
            return "danger"
        return "warn" if v <= ind["warn"] else "safe"
    if v >= ind["danger"]:
        return "danger"
    return "warn" if v >= ind["warn"] else "safe"


def threshold_text(ind):
    u = ind["unit"]
    if ind["dir"] == "low":
        return f"警 ≤{ind['warn']}{u} · 危 ≤{ind['danger']}{u}"
    return f"警 ≥{ind['warn']}{u} · 危 ≥{ind['danger']}{u}"
