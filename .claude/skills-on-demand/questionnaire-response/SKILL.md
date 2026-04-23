---
name: questionnaire-response
description: |
  WHAT：Leader 主導的客戶封裝製程問卷自動回覆流程（解析→分類→檢索→生成→Excel→回饋入庫）。
  WHEN：收到客戶 CSR/CQR/PQR/CTPP/Cu Wire Risk Assessment 問卷、稽核表、Self-Assessment。
  NOT：單題簡單問答請 Leader 直接處理，不必跑全流程。
triggers:
  - 客戶問卷, 問卷回覆, questionnaire, CSR review, CQR, PQR
  - customer audit, 稽核回覆, self-assessment, scoring levels
  - 回覆客戶, 草稿回覆, 策略建議
  - qa_pairs, qar_embed, qar_search
  - FULL_COMPLY, PARTIAL_COMPLY, ALT_JUSTIFY, ADVOCATE_CURRENT, DECLARE_GAP
  - Cu wire risk, bonding technology, CTPP, Qual Matrix
---

# 客戶問卷回覆 — Leader 主導流程

> Leader 主導的工作流程。收到客戶封裝製程問卷時按此步驟操作。

## 流程總覽

```
Step 1: 解析問卷 → Step 2: 分類每題 → Step 3: 檢索知識
→ Step 4: 生成回覆 → Step 5: 產出 Excel → Step 6: 回饋入庫
```

---

## Step 1: 解析問卷

1. 用 openpyxl 讀取 Excel（`read_only=True`）
2. 辨識問卷格式（10 種，見下方辨識規則）
3. 定位問題欄/回覆欄/狀態欄
4. 提取結構化列表：`[{row, section, question, existing_response, owner}, ...]`

### 格式辨識規則

| 特徵 | 問卷類型 |
|------|---------|
| Sheet = "Review result" + "Type of change" | CSR Review |
| Column 含 "CQR" 或 Sheet 含 "Development/Qualification/Production" | CQR |
| Column 含 "Self-Assessment" + "Auditor" | PQR Audit |
| Sheet 含 "特規需求" | Customer Quality Requirement |
| 大量 Cu wire / bonding 關鍵字 + K/R/S priority | Cu Wire Risk Assessment |
| Sheet 含 "PB-A" ~ "PB-F" | Bonding Technology |
| Column 含 "站別" + "具體執行方式" | CTPP |
| Sheet 含 "Scoring Levels" | Self-Assessment |
| 日文+英文雙欄 | Japanese Audit |
| 按產品型號橫向展開 | Qual Matrix |

---

## Step 2: 分類每題（Leader 直接判斷）

### 站別判斷
- 關鍵字匹配（切割/DB/WB/Mold/Plating/T&F/Marking/Test，中英日韓）
- Section 提示（如 CQR 的 "M-AOI_PM" = Assembly post-WB）
- 上下文推斷

### 主題判斷
- process_control / material / equipment / spc / aoi_inspection
- delamination / contamination / 4m_change / reliability / documentation

### 題型判斷
- yes_no / parameter / evidence / procedure / capability / gap_analysis

---

## Step 3: 檢索相關知識

### A. 委派 query-runner（並行）
```
對每題：
1. qar_search.py 找 past responses (top-5)
2. 按 station 查 fmea_items
3. 按 station 查 cp_items
4. 按 station 查 oi_paragraphs
→ 結果寫入 {project}/workspace/_query_result.txt（runtime 自動建立）
```

### B. Leader 直接做
- KG 查詢：`python shared/tools/graph_query.py search <key_terms>`
- 讀特定 OI/CP 原文（需精確引用時）
- Skills 知識（bom-rules, reliability-testing 等）

---

## Step 4: 生成回覆

### 13 種回覆策略

| # | 代碼 | 名稱 | 適用情境 |
|---|------|------|---------|
| 1 | FULL_COMPLY | 直接合規 | 有 OI/SOP 對應 |
| 2 | PARTIAL_COMPLY | 部分合規 | 符合意圖但未達標 |
| 3 | ALT_JUSTIFY | 替代方案 | 不同方法等效效果 |
| 4 | ADVOCATE_CURRENT | 維護現行 | 現行方式已足夠 |
| 5 | FEASIBILITY_EVAL | 評估中 | 承諾評估不承諾執行 |
| 6 | PROVIDE_DATA | 提供資料 | 附件數據 |
| 7 | DECLARE_GAP | 宣告差距 | 如實揭露 |
| 8 | DEFER_BACKEND | 延遲回覆 | 轉對應團隊 |
| 9 | NA_SCOPE | 不適用 | 產品特性排除 |
| 10 | CONDITIONAL | 有條件 | 附帶成本/條件 |
| 11 | COST_PASSTHROUGH | 成本轉嫁 | 同意但反映售價 |
| 12 | BENCHMARK_OTHER | 對標他客 | 引用先例 |
| 13 | REDIRECT_DEPT | 轉嫁部門 | 指定 Sales/QS/NPI |

### 策略遞進層級
```
FULL_COMPLY → ALT_JUSTIFY → ADVOCATE_CURRENT →
FEASIBILITY_EVAL → CONDITIONAL → DECLARE_GAP
```

### 模式選擇
- **≤20 題**：Leader 逐題處理
- **>20 題**：委派 response-drafter agent（gpt-oss:120b 批量生成）

### 信心評分
- **H (High)**: 有高相似過去回覆 + FMEA/CP/OI 佐證
- **M (Medium)**: 有部分參考但需人工確認
- **L (Low)**: 知識不足，建議指派專人

---

## Step 5: 產出 Excel

委派 report-builder：
- Sheet 1: Draft Responses（色碼：綠=H / 黃=M / 紅=L）
- Sheet 2: Statistics（按站別/策略/信心統計）
- 欄位：問題 | 站別 | 草稿回覆 | 策略 | 信心 | 引用文件 | 過去參考
- 路徑：`vault/outputs/QAR_{customer}_{date}.xlsx`

---

## Step 6: 回饋入庫

用戶審查後：
- **Approved**: 存入 qa_pairs + 產生 embedding
- **Modified**: 修改版存入 qa_pairs + embedding
- **Rejected**: 記錄原因

```python
# Leader 入庫操作
python workspace/scripts/qar_embed.py "question text"
# → 取得 embedding blob → INSERT INTO qa_pairs
```

---

## 資料工具

| 工具 | 路徑 | 用途 |
|------|------|------|
| qar_embed.py | workspace/scripts/ | 文字 → Ollama embedding |
| qar_search.py | workspace/scripts/ | query → cosine search qa_pairs |

## DB 表

| 表 | 用途 |
|----|------|
| qa_pairs | 過去回覆儲存（含 embedding） |
| doc_references | 高頻引用文件索引 |

---

## 高頻引用文件 TOP 15

| 文件編號 | 站點 | 用途 |
|---------|------|------|
| SOD-OI01 | Die Bond | DB 製程管控 |
| SOD-OI02 | Wire Bond | WB 製程管控 |
| SOD-OI03 | Molding | 模封製程管控 |
| SOD-OI05 | Trim & Form | 切彎腳 |
| SOD-OI06 | Test & Taping | 測試+編帶 |
| SOD-OI07 | Marking | 印字 |
| W-PE0220 | 全站 | Control Plan (車規) |
| P-QC2002 | 全站 | SPC 規範 |
| DICE1420-OI01 | 切割 | 晶片切割 OI |
| P-EE1201 | 全站 | 設備保養 PM |
| W-QA0901 | 測試 | SYL/SBL 規範 |
| P-QC1301 | 全站 | 異常品處理 |
| W-PE0401 | 全站 | 製程變更 TCCS |
| P-RM0901 | 全站 | 設備維護管理 |
| F-PE0945 | DB/WB | 吸嘴/銲針更換記錄 |

---

## 客戶回覆風格參考

| 客戶 | 風格 |
|------|------|
| Mando/Klemove | 文件引用型 — 全部 OI 編號 |
| Continental | Gap 標示型 — C/NA/Gap 明確 |
| Alien | MES 綁定型 — workflow 追蹤 |
| 冠捷(華為) | 深度對質型 — 多輪討論 |
| 小米 | 三廠平行型 — 跨廠差異 |
| CATL | 全項行動計畫型 — 無一空白 |
| LG | Level 分析型 — gap 分級 |
| BOSCH/VW | 合規聲明型 — 簡潔程序號 |
