---
name: xlsx-authoring
description: |
  openpyxl + pandas 新建 Excel 檔案的規則與最佳實踐。
  新建 .xlsx 時首選此路線（比 MCP COM 更穩定）。
  適用：從頭建立報告、資料輸出至 xlsx、工程數據表、成本分析。
  **編輯已有 Excel 請用 excel-operations skill（MCP COM 增量編輯）**。
  需要：conda env ai-office（openpyxl 已安裝）。
---

# Excel 新建（openpyxl code-based）

## 環境

```bash
PYTHONUTF8=1 "C:\Users\lin46\.conda\envs\ai-office\python.exe" your_script.py
```

## 核心原則：公式優先，禁 hardcode 計算值

```python
# 錯誤：Python 算好再填入
ws['B10'] = df['Sales'].sum()

# 正確：讓 Excel 自己計算
ws['B10'] = '=SUM(B2:B9)'
ws['C5'] = '=C4*(1+$B$2)'   # 引用假設格，不寫死 1.05
```

## 標準建立流程

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

wb = Workbook()
ws = wb.active
ws.title = "Report"

# 1. 寫標題列
headers = ["Part No.", "測試條件", "樣品數", "失效數", "FIT Rate"]
for col, h in enumerate(headers, 1):
    ws.cell(row=1, column=col).value = h

# 2. 寫資料（含公式）
data = [["1N5819", "125°C/1000hr", 77, 0, "=D3/C3*1e9/1000"]]
for r, row in enumerate(data, 2):
    for c, val in enumerate(row, 1):
        ws.cell(row=r, column=c).value = val

# 3. 標題列樣式
for col in range(1, len(headers) + 1):
    cell = ws.cell(row=1, column=col)
    cell.font = Font(bold=True, color="FFFFFF", name="Microsoft JhengHei", size=10)
    cell.fill = PatternFill("solid", fgColor="1F4E79")
    cell.alignment = Alignment(horizontal="center", vertical="center")

# 4. 資料列交替色
for r in range(2, len(data) + 2):
    for c in range(1, len(headers) + 1):
        cell = ws.cell(row=r, column=c)
        cell.font = Font(name="Microsoft JhengHei", size=9)
        if r % 2 == 0:
            cell.fill = PatternFill("solid", fgColor="F2F2F2")

# 5. 凍結首行 + 自動欄寬
ws.freeze_panes = 'A2'
for col in ws.columns:
    max_len = max((len(str(cell.value or '')) for cell in col), default=10)
    ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 40)

wb.save("output.xlsx")
```

## 公式重算（有公式時必跑）

```bash
PYTHONUTF8=1 "C:\Users\lin46\.conda\envs\ai-office\python.exe" /d/ai-office/shared/tools/recalc.py output.xlsx
```

輸出 `{"status": "success", "total_errors": 0}` 或 `errors_found`（含錯誤位置）。

## 色彩語義標準

| 顏色 | fgColor | 語義 | 適用欄位 |
|------|---------|------|---------|
| 藍色字 | `0000FF` | 可修改的輸入值 | 溫度、時間、電壓 |
| 黑色字 | `000000` | 公式計算結果（預設） | 失效率、累計數 |
| 綠色字 | `008000` | 跨工作表連結 | 來自 BOM/master |
| 黃底 | `FFFF00` | 待確認的關鍵假設 | LTPD、CI level |

```python
ws['B3'].font = Font(color="0000FF")                       # 藍字 = 可修改
ws['B3'].fill = PatternFill("solid", fgColor="FFFF00")     # 黃底 = 假設
```

## 數字格式

| 類型 | Format |
|------|--------|
| 千分位 | `#,##0` |
| 千分位（負數括號）| `#,##0;(#,##0);-` |
| 百分比 | `0.0%` |
| 日期 | `yyyy-mm-dd` |

```python
ws['C5'].number_format = '#,##0;(#,##0);-'
ws['D5'].number_format = '0.0%'
```

## 假設格分離

```python
# 假設區（黃底 + 藍字）
ws['B2'] = 0.05
ws['B2'].fill = PatternFill("solid", fgColor="FFFF00")
ws['B2'].font = Font(color="0000FF")
ws['A2'] = 'Growth Rate'

# 公式引用假設格（不寫死參數值）
ws['C5'] = '=C4*(1+$B$2)'
```

## 多工作表報告

```python
# 摘要頁放第一，原始資料放後面
ws_summary = wb.active
ws_summary.title = "Summary"
ws_raw = wb.create_sheet("Raw Data")

# 跨表引用（摘要 → 原始資料）
ws_summary['B5'] = "='Raw Data'!C10"
```

## 品質驗證清單

- [ ] 測 2-3 個樣本格，確認公式值正確
- [ ] Excel row = DataFrame row + 1（1-based）
- [ ] 除法前確認分母非零（避免 #DIV/0!）
- [ ] 跨表引用格式 `='Sheet Name'!A1`
- [ ] recalc.py 輸出 `status: success`
- [ ] 凍結首行（`freeze_panes = 'A2'`）
- [ ] 自動欄寬套用
- [ ] 無殘留空白工作表
