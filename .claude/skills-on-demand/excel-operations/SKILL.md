---
name: excel-operations
scope: generic
tracking: tracked
description: |
  WHAT：透過 mcp__xlsx__* 工具（COM 自動化）對既有 Excel 做增量編輯。
  WHEN：開啟/修改現有 xlsx、改儲存格、套樣式、寫圖表、conditional format。
  NOT：從零建立新 xlsx 請用 xlsx-authoring（openpyxl code-based，更穩定）。
triggers:
  - Excel, xlsx, 試算表, 工作表, Sheet
  - mcp__xlsx, COM, write_range, read_range, format_range
  - apply_style_preset, add_borders, conditional_format
  - 增量編輯, 儲存格, 日期格式, 凍結窗格
---

# Excel 操作 — MCP COM 增量編輯路線

## 工具總覽（35 個）

| 區塊 | 工具 | 數量 |
|------|------|------|
| A. 生命週期 | create_workbook, open_workbook, save_workbook, close_workbook, get_workbook_info | 5 |
| B. 工作表 | add_sheet, rename_sheet, delete_sheet, get_sheet_info | 4 |
| C. 儲存格 | read_range, write_range, write_cell, clear_range, find_replace | 5 |
| D. 格式化 | format_range, set_column_width, set_row_height, merge_cells, add_borders | 5 |
| E. 表格篩選 | create_table, auto_filter, sort_range | 3 |
| F. 圖表 | add_chart, modify_chart, delete_chart | 3 |
| G. 工具 | insert_image, freeze_panes, page_setup | 3 |
| H. 進階 | auto_fit_columns, auto_fit_rows, read_cell_format, copy_worksheet, hide_rows_columns, add_conditional_format, apply_style_preset | 7 |

---

## R1：活頁簿生命週期管理（信心度：very high）

**必須遵循的流程**：
1. `create_workbook` 或 `open_workbook` 開啟活頁簿
2. 執行所有讀寫和格式化操作
3. `save_workbook` 儲存
4. `close_workbook` 關閉並釋放 COM

**注意**：`close_workbook` 會同時退出 Excel 應用程式。未呼叫會導致 Excel 程序殘留。

```
標準流程：
1. create_workbook(path="D:\\output\\report.xlsx")  或  open_workbook(path=...)
2. 寫入資料、格式化、建立圖表...
3. save_workbook()
4. close_workbook()
```

---

## R2：read_range 大範圍讀取限制（信心度：very high）

`read_range` 回傳 JSON 二維陣列，**最多 500 行**。超過時回傳前 500 行並附截斷提示。

**處理大量資料的策略**：
- 分批讀取：`read_range(sheet, "A1:Z500")`、`read_range(sheet, "A501:Z1000")`
- 只讀需要的欄位範圍
- 如果只是需要總行數，用 `get_sheet_info` 查詢 UsedRange

---

## R3：write_range 批次寫入模式（信心度：very high）

`write_range` 使用 COM 的 `Range.Resize(rows, cols).Value = data` 批次寫入。

**data 格式**：二維陣列（list of lists）
```json
[
  ["Name", "Score", "Grade"],
  ["Alice", 95, "A"],
  ["Bob", 87, "B"]
]
```

**注意**：
- 第一行可以是標題行
- 數值會保持為數字類型
- 空值用 `null` 或 `""`

---

## R4：日期值處理（信心度：very high）

COM 回傳的日期值為 `pywintypes.datetime` 類型。`read_range` 自動轉換為 ISO 格式字串（如 `"2026-02-26T00:00:00"`）。

寫入日期時，可以直接寫入字串格式的日期，再用 `format_range` 設定 `number_format`：
- `"yyyy-mm-dd"` → 2026-02-26
- `"yyyy/mm/dd"` → 2026/02/26
- `"mm/dd/yyyy"` → 02/26/2026

---

## R5：format_range 通用格式化（信心度：high）

只需提供要修改的參數，未提供的參數不會改變原有格式。

| 參數 | 說明 | 範例 |
|------|------|------|
| font_name | 字型名稱 | "Microsoft JhengHei" |
| font_size | 字體大小 | 12.0 |
| font_bold | 粗體 | true |
| font_color | 字體顏色 (hex) | "1F4E79" |
| bg_color | 背景色 (hex) | "E8EEF4" |
| h_align | 水平對齊 | "left" / "center" / "right" |
| v_align | 垂直對齊 | "top" / "center" / "bottom" |
| number_format | 數字格式 | "#,##0.00" / "0%" / "yyyy-mm-dd" |
| wrap_text | 自動換行 | true |

**顏色格式**：6 位 hex 碼（不含 #），COM 內部使用 BGR 順序。

---

## R6：add_borders 框線樣式（信心度：high）

| style | 說明 |
|-------|------|
| "thin" | 細線（預設） |
| "medium" | 中線 |
| "thick" | 粗線 |
| "hair" | 極細線 |

框線會套用到範圍的所有邊緣（上下左右 + 內部格線）。

---

## R7：建立 Excel 報告的標準流程範本（信心度：high）

```
1. create_workbook(path)
2. 寫入標題列：
   write_range(sheet="Sheet1", start_cell="A1", data=[headers])
3. 寫入資料：
   write_range(sheet="Sheet1", start_cell="A2", data=data_rows)
4. 格式化標題列：
   format_range(sheet="Sheet1", range="A1:Z1", font_bold=true, bg_color="1F4E79", font_color="FFFFFF")
5. 設定欄寬：
   set_column_width(sheet="Sheet1", columns="A:Z", width=15)
6. 加框線：
   add_borders(sheet="Sheet1", range="A1:Z100", style="thin")
7. 凍結首行：
   freeze_panes(sheet="Sheet1", cell="A2")
8. save_workbook()
9. close_workbook()
```

**增量編輯模式**（修改已有檔案）：
```
1. open_workbook(path)
2. 只修改需要的儲存格/範圍
3. save_workbook()
4. close_workbook()
```

---

## R8：auto_fit_columns / auto_fit_rows 自動調整（信心度：high）

自動根據內容調整欄寬或列高。columns/rows 為空時調整整個 UsedRange。

```
# 調整所有已用欄寬
auto_fit_columns(sheet="Sheet1")

# 只調整 A~F 欄
auto_fit_columns(sheet="Sheet1", columns="A:F")

# wrap_text 儲存格需要先 auto_fit_rows 才能正確顯示
auto_fit_rows(sheet="Sheet1")
```

**注意**：`auto_fit_columns` 不支援合併儲存格內的自動調整（COM 限制）。

---

## R9：apply_style_preset 預設樣式套用（信心度：very high）

一次呼叫套用完整樣式組合（bg_color + font + alignment + border），取代逐一呼叫 `format_range` + `add_borders`。

**可用預設**：

| preset | 背景色 | 字型 | 用途 |
|--------|--------|------|------|
| header | 1F4E79 (深藍) | 10pt 白色粗體 | 標題列 |
| subheader | D6E4F0 (淺藍) | 10pt 粗體 | 子標題列 |
| data | 無 | 9pt | 資料列 |
| data_alt | F2F2F2 (灰) | 9pt | 交替行 |
| confirm | C6EFCE (綠) | 9pt | 確認/通過 |
| warning | FFEB9C (黃) | 9pt | 警告/待確認 |
| error | FFC7CE (紅) | 9pt | 錯誤/失敗 |
| accent | F4B084 (橘) | 9pt | 強調/特殊標記 |

```
# 取代原本的 format_range + add_borders 兩次呼叫
apply_style_preset(sheet="Sheet1", range="A1:H1", preset="header")
apply_style_preset(sheet="Sheet1", range="A2:H100", preset="data")
```

樣式定義來自 `shared/tools/excel_styles.py`，所有報告共用。

---

## R10：read_cell_format 回查驗證（信心度：high）

增量編輯時回查現有格式，避免破壞原有樣式。回傳 JSON 包含：

```json
{
  "font_name": "Calibri",
  "font_size": 10.0,
  "font_bold": true,
  "font_color": "FFFFFF",
  "bg_color": "1F4E79",
  "h_align": "center",
  "v_align": "center",
  "wrap_text": true,
  "number_format": "General"
}
```

**使用場景**：
- 編輯前先讀取格式 → 修改後比對確認
- 確認報告是否已套用正確樣式

---

## Q：品質規範與常見錯誤（Quality Rules）

### Q1：產出前必做清單
1. `apply_style_preset("header")` 套用標題列 → 禁止手動逐欄 format_range 拼湊
2. `auto_fit_columns()` 調整欄寬 → 合併儲存格區域需手動 set_column_width
3. `freeze_panes(cell="A2")` 凍結首行 → 多標題列時凍結在資料起始行
4. 數值欄位設定 `number_format`（千分位 `#,##0`、百分比 `0.0%`、日期 `yyyy-mm-dd`）
5. 無空白工作表殘留（刪除未使用的 Sheet）

### Q2：常見錯誤規避
| 錯誤 | 正確做法 |
|------|---------|
| header 用淺色底深色字 | 深藍底（1F4E79）白字，用 apply_style_preset("header") |
| 數值欄靠左對齊 | 數值一律 h_align="right"，文字 h_align="left" |
| 忘記 close_workbook | 每個流程最後必須 save + close，否則 Excel 殘留 |
| 大量資料逐格 write_cell | 用 write_range 批次寫入，效率差 10-100 倍 |
| 格式化後才寫資料 | 先寫資料再格式化，避免格式被覆蓋 |
| 混用多種顏色 | 只用標準色盤（見 report-builder.md DP2） |

## R12：Ingestion 前的 Excel 正規化（信心度：high）

當 Excel 被拿來做資料入庫前處理時：

- 先檢查 `ws.merged_cells.ranges`
- 比對、JOIN、prefix/status 過濾前要先 unmerge + forward-fill
- 不可直接用合併儲存格的左上角值去代表整列資料

這是通用 ingestion 技巧，不屬任何公司內規。

### Q3：多工作表報告規範
- Sheet 命名有意義（"Summary", "Raw Data"），不留 "Sheet1"
- 摘要表放第一頁，原始資料放後面
- 跨表引用時在摘要表加說明

---

## R11：add_conditional_format 條件格式（信心度：high）

| rule_type | 說明 | operator | formula |
|-----------|------|----------|---------|
| cell_value | 依數值條件 | greater_than/less_than/between/equal | 比較值 |
| text_contains | 包含指定文字 | — | 搜尋文字 |
| duplicate | 標記重複值 | — | — |
| top_n | 前 N 名 | — | N 值 |

```
# 標記 > 100 的儲存格為紅底
add_conditional_format(sheet="Sheet1", range="C2:C100",
    rule_type="cell_value", operator="greater_than", formula="100",
    bg_color="FFC7CE")

# 標記包含 "FAIL" 的儲存格
add_conditional_format(sheet="Sheet1", range="D2:D100",
    rule_type="text_contains", formula="FAIL",
    bg_color="FFC7CE", font_color="C00000")

# 標記重複值
add_conditional_format(sheet="Sheet1", range="A2:A100",
    rule_type="duplicate", bg_color="FFEB9C")
```
