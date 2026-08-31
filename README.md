# crisis-monitor 金融海嘯預警對照表

每日自動抓取 19 項信用／流動性／房市／台股指標，與 2007 年危機前後的數值對照，
產出單頁 HTML 與 Markdown 報表，並推播 Telegram。

核心邏輯不是看單一數字，而是看**壓力傳導到哪一層**：
結構失衡（領先 12–18 個月）→ 信用收縮（6–12 個月）→ 流動性斷裂（1–6 個月）→ 台灣外溢。
2007 年這四層是依序點燃的，股價是最後才反應的。

## 產出

| 檔案 | 內容 |
|------|------|
| `docs/index.html` | 單頁對照表（可直接開，或開 GitHub Pages） |
| `report.md` | Markdown 報表，GitHub 上直接可讀 |
| `data/history.json` | 每日分數與各指標狀態，累積追蹤用 |
| `data/latest.json` | 最新一筆快照 |

## 資料來源

| 來源 | 指標 | 需要金鑰 |
|------|------|----------|
| FRED CSV 端點 | 殖利率利差 ×2、HY/IG OAS、Case-Shiller、Sahm Rule、VIX、SOFR−DTB3 | 不需要 |
| yfinance | XLF 距 52 週高點、HYG−SPY 相對報酬、台幣變化 | 不需要 |
| FinMind | 外資 5 日買賣超、台指期外資淨 OI、融資餘額 20 日變化 | `FINMIND_TOKEN` |
| `manual.json` | NAHB、SLOOS、外銷訂單、景氣對策信號、交叉貨幣基差 | 手動維護 |

## 手動指標怎麼維護

只有 5 項需要手動，且都是月更或季更。有新數據時編輯 `manual.json`：

```json
"exports": { "value": -1.2, "as_of": "2026-05-20" }
```

`as_of` 超過該指標的容忍天數（NAHB 45 天、SLOOS 120 天、外銷訂單 60 天、景氣信號 45 天）時，
報表會標紅並在 Telegram 提醒你補資料。沒填的項目不計分，不會影響其他指標。

## 設定

1. 建立 repo，把這些檔案推上去。
2. Settings → Secrets and variables → Actions，新增：
   - `FINMIND_TOKEN`（必要，台灣端三項靠它）
   - `TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID`（要推播才需要）
3. Settings → Actions → General → Workflow permissions 選「Read and write」，
   否則自動提交會失敗。
4. Actions 分頁手動跑一次「每日預警對照表」確認。

排程為 UTC 13:30（台北 21:30，週一至週五），台股盤後資料已出、美國前一日資料也已更新。
`workflow_dispatch` 保留，隨時可手動觸發。

## 開啟 GitHub Pages

`docs/index.html` 每天都會自動 commit，所以不用改任何程式，只要開設定：

Settings → Pages → Source 選「Deploy from a branch」→ Branch 選 `main`、資料夾選 `/docs` → Save。

網址會是 `https://<你的帳號>.github.io/crisis-monitor/`，手機加到書籤即可。
第一次設定後約 1–2 分鐘才會生效。Telegram 推播會自動附上這個連結
（由 Actions 的 `GITHUB_REPOSITORY` 推導；若用自訂網域，設環境變數 `PAGES_URL` 覆寫）。

repo 設為公開即可免費使用 Pages。這份報表不含任何金鑰——`FINMIND_TOKEN` 與 Telegram
的認證都放在 Actions Secrets，不會出現在產出的檔案裡。

## 本機執行

```bash
pip install -r requirements.txt
export FINMIND_TOKEN=你的token
python monitor.py --dry-run   # 只印結果，不寫檔不推播
python monitor.py             # 正式產出
```

## 調整閾值

全部集中在 `indicators.py` 的 `INDICATORS`。`dir` 為 `low` 代表數值越低越危險，
`high` 反之。改 `warn` / `danger` 即可，不用動其他檔案。

### 變化率觸發

信用利差的問題是：絕對值低不代表安全，**擴大速度才是訊號**。2007 年 HY OAS 從
2.4% 走到 5.7% 花了半年，若只用絕對門檻，前段的訊號會整段丟掉。

因此部分指標另外設 `delta`，用水準與變化率各判一次，取較嚴重者：

```python
"delta": {"lookback": 60, "dir": "high", "warn": 1.0, "danger": 1.5}
```

目前設定的兩項：

| 指標 | 水準門檻 | 60 日變化門檻 |
|------|----------|---------------|
| HY OAS | 警 3.5% / 危 4.5% | 擴大 ≥1.0pp 警戒、≥1.5pp 危險 |
| 10Y–3M | 警 ≤0.5% / 危 ≤0% | 陡峭化 ≥0.4pp 警戒、≥0.7pp 危險 |

10Y–3M 的倒掛條件在本循環已經發生過（2022–2024），單看水準這項不會再示警，
所以主訊號改成陡峭化速度。**注意這個判定無法區分多頭陡峭化（短端下行，衰退訊號）
與空頭陡峭化（長端上行，供給或通膨因素）**，需搭配 3 個月殖利率方向自行判讀。

變化率目前只支援 FRED 單一序列（`sources.fetch_delta`）；其他來源會靜默略過，
該指標就只依水準判定。

## 已知限制

- **SOFR − 3個月國庫券是 TED spread 的代理，不是等價指標。** 方向一致但幅度不可直接比較，
  2007 對照值僅供量級參考。
- 交叉貨幣基差無免費來源，預設留空不計分。
- 2007 對照欄為危機前後的概略代表值，用途是比量級，不是精確重建。
- FRED 序列代碼若被官方改名（例如 `SPCS20RSA`），該指標會標成「未取得」，
  其餘指標照常運作，改 `indicators.py` 的 `source` 即可。

---

本專案為個人研究與紀錄工具，所載內容僅供參考，不構成任何投資建議或買賣要約，
投資人應自行判斷並承擔風險。
