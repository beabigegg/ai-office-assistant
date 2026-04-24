---
name: marp-pptx
scope: generic
tracking: tracked
description: |
  WHAT：用 Marp Markdown 生成 PPTX/PDF，走 marp_build.py + semicon.css 主題。
  WHEN：標題/目錄/摘要頁、KPI callout、雙欄、Markdown 大量內容轉簡報、PDF 分發。
  NOT：客戶可編輯的原生圖表、20+ 欄表格、公司模板請用 pptx-template 或 pptx-operations。
triggers:
  - Marp, marp-pptx, marp_build, marp markdown
  - Markdown 簡報, 簡報 md, md to pptx
  - semicon 主題, cards, callout, cols, CSS class
  - PDF 分發, 快速簡報, matplotlib 圖表嵌入
---

# Marp 簡報生成 — Markdown to PPTX 路線

## 工作流程

```
1. 撰寫 Marp Markdown（.md）
2. marp_build.py → .pptx
3. office_validator.py 結構驗證 → 回報結果
4. （選用）MCP PPTX 精修原生圖表 / 20+ 欄表格
```

## M1：Marp vs MCP PPTX 分工決策

| 情境 | 用 Marp | 用 MCP PPTX |
|------|---------|-------------|
| 標題/目錄/摘要頁 | ✓ | |
| 文字+簡單表格（≤10 欄） | ✓ | |
| KPI callout、雙欄佈局 | ✓（semicon.css class） | |
| matplotlib/PNG 圖表嵌入 | ✓（`![](chart.png)`） | |
| 客戶可在 PPT 內調整的原生圖表 | | ✓ add_chart |
| 20+ 欄寬表（FMEA/可靠性矩陣） | | ✓ add_table |
| 客戶指定版型（Logo 座標/特殊頁碼） | | ✓ 全 MCP |

**預設：用 Marp。只有上表右欄情境才切換 MCP PPTX。**

## M2：Marp Markdown 基本結構

```markdown
---
marp: true
theme: semicon
paginate: true
size: 16:9
---

<!-- _class: title -->
# 標題
## 副標題 | 2026-04-21

---

# 第一頁標題

內容...

---
```

**frontmatter 必填**：`marp: true`、`theme: semicon`、`paginate: true`、`size: 16:9`

## M3：semicon.css 可用 CSS class

| Class | 用途 | 範例 |
|-------|------|------|
| `<!-- _class: title -->` | 深藍漸層標題頁 | 第一頁 |
| `<!-- _class: section -->` | 章節分隔頁（淺藍底） | 每章開頭 |
| `.cards` | 3 欄卡片網格 | KPI 並排 |
| `.cards.col2` | 2 欄 | |
| `.cards.col4` | 4 欄 | |
| `.card` | 單一卡片（藍左框） | |
| `.card.success/.warning/.danger` | 綠/黃/紅卡片 | 狀態標示 |
| `.stat-large` | 大數字（52px 深藍） | 關鍵數字 |
| `.stat-label` | 大數字下方小標籤 | |
| `.callout` | 注意區塊（藍左框） | 備註說明 |
| `.callout.warn/.info` | 橘/藍色注意區塊 | |
| `.cols` | 雙欄佈局（各 50%） | 左文右圖 |
| `.cols.ratio31` | 3:1 欄寬 | |
| `.cols.ratio13` | 1:3 欄寬 | |

**CSS class 用法（Marp 裡用 HTML div）**：
```html
<div class="cards">
  <div class="card">
    <div class="stat-large">85%</div>
    <div class="stat-label">免測率</div>
  </div>
  <div class="card success">通過</div>
  <div class="card warning">待確認</div>
</div>
```

## M4：圖表嵌入（matplotlib PNG）

```python
# 先用 matplotlib 生成 PNG，存到和 .md 同目錄
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(10, 5), dpi=120)
ax.plot(...)
plt.savefig("chart.png", bbox_inches="tight")
plt.close()
```

在 MD 裡嵌入：
```markdown
![w:900](chart.png)
```

寬度控制：`![w:900](file.png)`、`![w:600 h:350](file.png)`

## M5：執行產出

```bash
# 產出 PPTX（預設用 semicon.css 主題）
PYTHONUTF8=1 "C:\Users\lin46\.conda\envs\ai-office\python.exe" \
  shared/tools/marp_build.py input.md output.pptx

# 產出 PDF
PYTHONUTF8=1 "C:\Users\lin46\.conda\envs\ai-office\python.exe" \
  shared/tools/marp_build.py input.md output.pdf

# 自訂主題
PYTHONUTF8=1 "C:\Users\lin46\.conda\envs\ai-office\python.exe" \
  shared/tools/marp_build.py input.md output.pptx custom.css
```

執行成功輸出：`OK: output.pptx (xxx KB)`

## M6：產出後驗證

```bash
PYTHONUTF8=1 "C:\Users\lin46\.conda\envs\ai-office\python.exe" \
  shared/tools/office_validator.py output.pptx
```

結果必須文字回報使用者（PASS/WARNING/FAIL + 問題摘要）。

## M7：表格欄位限制

- ≤ 10 欄 → Markdown 表格（`| 欄1 | 欄2 | ...`）
- > 10 欄 → 改用 MCP PPTX `add_table`（`mcp__pptx__add_table`）

## M8：中英文字型

`semicon.css` 已設定 `"Microsoft JhengHei", "Calibri"`，Marp 的 Chromium 能直接取用 Windows 內建字型，**無需額外處理**。

## M9：常見問題

| 問題 | 原因 | 解法 |
|------|------|------|
| 圖片不顯示 | 路徑問題 | 必須加 `--allow-local-files`（marp_build.py 已內建） |
| 字型 fallback 成英文 | CSS 未指定 | semicon.css 已處理，確認 theme 有載入 |
| 投影片數不符 | MD 分頁 `---` 有誤 | 確認每頁都用 `---` 分隔（frontmatter 後第一個 `---` 是第一頁結束） |
| 表格超出邊界 | 欄數過多或內容太長 | 縮短文字 / 切換 MCP 表格 |
