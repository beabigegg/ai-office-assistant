---
name: mes-report
description: |
  WHAT：MES（SSRS）報表透過 mes_report.py 走 NTLM 認證下載、入庫、分析。
  WHEN：需要 PJMES/PJCMR 系列報表、Lot History、良率日報、Q-Time、CST 損耗、設備叫修紀錄。
triggers:
  - MES, mes report, PJMES, PJCMR, SSRS
  - mes_report.py, NTLM, Playwright, VPN
  - Lot History, Equipment Jobs, Material History, Q-Time, OEE, Traceability
  - PJMES002, PJMES007, PJMES022, PJMES023, PJMES068, PJCMR068
  - 報表下載, 良率日報, CST 損耗, 站間管制時間
---

# MES 報表下載 — SSRS URL Access 路線

MES (Manufacturing Execution System) 報表透過 SSRS URL Access API 下載。
**必須連 VPN**（NTLM 模式，2026-03-30 確認：外部 DNS 記錄已由 IT 移除，Playwright 模式也需 VPN）。

## 工具

### T1: mes_report.py — CLI 下載工具

**位置**：`shared/tools/mes_report.py`
**設定檔**：`projects/mes-report/workspace/mes_reports.yaml`

```bash
# 列出可用報表
python shared/tools/mes_report.py list

# 下載報表（需 VPN，NTLM 為預設推薦模式）
python shared/tools/mes_report.py download PJMES002 --start 2026/03/01 --end 2026/03/19

# 下載並合併為單一 Excel
python shared/tools/mes_report.py download PJMES002 --start 2026/03/01 --end 2026/03/19 --merge

# 覆寫參數
python shared/tools/mes_report.py download PJMES007 --start 2026/03/01 --end 2026/03/15 --param P_RESOURCENAME=GXXX-0001

# 查看報表參數
python shared/tools/mes_report.py params PJMES002

# 測試連線
python shared/tools/mes_report.py test
python shared/tools/mes_report.py --auth playwright test
```

**環境變數**（必須在 .env 設定）：
- `MES_USER` — SSRS 帳號（員工編號）
- `MES_PASSWORD` — SSRS 密碼

## 規則

### R1: 認證模式
| 模式 | 機制 | VPN | 依賴 |
|------|------|-----|------|
| `--auth ntlm`（預設，推薦） | requests + NTLM 直連 | **需要** | requests-ntlm |
| `--auth playwright` | Chromium + NTLM 直連 | **需要** | playwright |

> **2026-03-30 確認**：`mesrss.panjit.com.tw` 外部 DNS 記錄已由 IT 移除。
> 兩種模式均需 VPN，一律使用 NTLM 模式（預設）即可。

### R2: 日期分段與 timeout
所有報表統一 1 天 1 段（避免 SSRS Excel 渲染 timeout），default_timeout=1800s（30 分鐘）。

**已驗證報表的實測耗時**：

| 報表 | 耗時/天 | 大小/天 | timeout |
|------|---------|---------|---------|
| PJMES002 (Lot History) | ~245s | ~7.8MB | 600 |
| PJMES007 (Equipment Jobs) | ~19min | ~147KB | 1800 |
| PJMES022 (良率日報) | ~578s | ~828KB | 1800 |
| PJMES023 (Material History) | ~20min | ~614KB | 1800 |
| PJMES068 (Q-Time) | ~209s | ~1.6MB | 1800 |
| PJCMR068 (CST損耗) | ~293s/月 | ~8.7MB/月 | 1800 |

### R3: 參數格式
**日期格式**：`YYYYMMDD HH24MISS`（大部分）或 `YYYYMMDD`（022/051/CMR068）
**Nullable 參數**：自動以 `ParamName:isnull=true` 傳遞
**多值參數**：`select_all: true` → 自動 SOAP 取有效值 → 重複 key 傳遞

### R4: Pre-auth 與 Split Timeout
1. **Pre-auth**：下載前先發輕量 GET 建立 NTLM session
2. **Split timeout**：`timeout=(30, read_timeout)` 分離 connect/read

### R5: 停用報表（2026-03-30 全部實際探索）

| 報表 | 停用原因 | 實際可用性 |
|------|---------|-----------|
| PJMES009 (Reject History) | SQL 查詢極慢（>5min），任何篩選條件均 timeout | **不可用**（SSRS 效能問題） |
| PJMES012 (Job Txn History) | 全廠查詢 timeout | **限定**：需 `--param P_Resource=設備ID`（~18s/設備） |
| PJMES051 (OEE) | 需按 WorkCenter 查詢 | **可用**：P_DATE_M=2 + 指定 WC（~150s/WC/月），13 個 WC |
| PJMES084 (Traceability) | URL 超長 + P_HIDELOTIDS bug | **可用**：單 Lot 查詢，需 SOAP 取 WorkCenter hex IDs |

**PJMES051 WorkCenter 有效值（13個）**：PKG_SAW, TMTT, 切割, 切彎腳, 去膠, 成型, 水吹砂, 焊接_DB, 焊接_DW, 焊接_WB, 電鍍, 移印, 品檢

**PJMES084 關鍵**：P_HIDELOTIDS 必須為 `%`（YAML 原設 `"0"` 是 bug，已修正）；P_WorkCenter 需 SOAP 動態取 33 個 hex ID

### R6: 新增報表流程
1. 在 SSRS 找到報表路徑（`ReportServer?/folder&rs:Command=ListChildren`）
2. 用 SOAP API 取得參數定義（`LoadReport`）
3. 在 `mes_reports.yaml` 新增設定
4. 測試 HTML 渲染（快速驗證參數正確性）
5. 測試 Excel 匯出，逐步調整 timeout

## 報表清單

| ID | 名稱 | 狀態 | 用途 |
|----|------|------|------|
| PJMES002 | Lot History | ✅ | Lot 異動歷程 |
| PJMES007 | Equipment Jobs | ✅ | 設備叫修紀錄 |
| PJMES009 | Lot History for Reject | ❌ disabled | 報廢 Lot 歷程 |
| PJMES012 | Job Txn History | ❌ disabled | 設備維修歷史 |
| PJMES022 | TMTT 良率日報 | ✅ | 生產良率日報表 |
| PJMES023 | Material History | ✅ | Lot 物料使用歷程 |
| PJMES051 | E10 OEE | ❌ disabled | 設備稼動率總表 |
| PJMES068 | Q-Time 紀錄 | ✅ | 站間管制時間紀錄 |
| PJCMR068 | CST 損耗明細 | ✅ | 損耗明細與彙總 |
| PJMES084 | Traceability | ❌ disabled | 全程追溯報告 |

## 欄位結構（實測 2026-03-30）

詳細欄位文件：`projects/mes-report/workspace/memos/report_column_schema.md`

### 關鍵結構差異

| 報表 | 欄位行 | 資料起始行 | Sheets 數 |
|------|--------|-----------|-----------|
| PJMES002 | Row 2 | Row 3 | 1 |
| PJMES022 | Row 2 | Row 3 | 2（Daily Yield + SW BIN） |
| PJMES023 | Row 2 | Row 3 | 2（Detail + Total） |
| PJMES007 | Row 3（Row 2 空） | **Row 4** | 1 |
| PJMES068 | Row 3（Row 2 空） | **Row 4** | 9（總覽 + 8 製程） |
| PJCMR068 損耗明細 | Row 2 | Row 3 | 4 |
| PJCMR068 損耗彙總 | Row 1~2 雙層 | Row 3 | 4 |
| PJCMR068 排除明細 | **Row 1** | **Row 2** | 1 |
| PJCMR068 Overall | **Row 1** | **Row 2** | 1 |

### 主要欄位速查

**PJMES002**：Lot, Txn Name, From/To Spec, From/To Work Center, From/To Qty, Equipment, Comments, Txn Date Time, 人員, Shift

**PJMES022 Daily Yield**：Lot, 工單號碼, Owner, Product, TYPE, Package, BOP, Family, Function, 良品數(K), 不良品數(K), TMTT良率, 電性良率, BIN NG 數（227~483）, 各製程設備+Track in/out time

**PJMES023 Detail**：Lot, 原物料, SPEC, 摘要, 原物料批號, 需求數量, Consume Factor, 耗用數量, 扣料時間, 班別, 人員, 機台, PACKAGE

**PJMES068**：Process Timer Name, Lot, Lot狀態, Package, BOP, Qty, Time to Max(剩餘小時), 目前Spec, 開始時間, 標準時間, 實際經過時間, 判定結果

**PJCMR068 損耗明細**：工單號碼, 組裝料號, LINE, FUNCTION, PACKAGE, FAMILY, TYPE, 站別, 移轉數量, 報廢數量, 製成率
