---
name: pptx-template
description: |
  PANJIT 樣式 PPT 生成工具。適用於：
  用 pptx_panjit.py 建立符合公司視覺標準的可編輯 PPTX 報告、
  標題/表格/圖片/雙欄/callout 的標準版面、
  semicon 色盤 (#1F4E79 深藍主色) 應用在 PowerPoint 元素。
  當任務涉及可編輯 PPT、公司報告模板、PANJIT 簡報時觸發。
triggers:
  - pptx-template
  - 可編輯ppt
  - 可編輯PPT
  - 公司報告
  - pptx_panjit
  - PANJIT簡報
  - panjit pptx
  - 原生 pptx
---

# pptx_panjit — PANJIT 樣式可編輯 PPT

## T1：何時用 pptx_panjit vs Marp

| 情境 | 用 pptx_panjit | 用 Marp |
|------|---------------|---------|
| 客戶/上層要求可在 PowerPoint 內編輯 | ✓ | |
| 公司標準報告（需要符合企業版面） | ✓ | |
| 事後需手動微調細節（改字/換圖/加頁） | ✓ | |
| 快速分發（PDF 導出即可） | | ✓ |
| 純展示、不再修改 | | ✓ |
| 大量 Markdown 內容要轉 PPT | | ✓ |

**決策規則**：要「可編輯 .pptx」就用 pptx_panjit；不需編輯只導出 PDF 就用 Marp。

## T2：API 速查

工具位置：`shared/tools/pptx_panjit.py`

```python
from pptx_panjit import (
    PanjitPresentation,
    add_table, add_image, add_bullets, add_two_column, add_text_box,
    set_cell_style, apply_table_style,
    # 顏色常數
    COLOR_PRIMARY, COLOR_SECONDARY, COLOR_ACCENT,
    COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
    COLOR_TEXT, COLOR_MUTED, COLOR_WHITE, COLOR_ALT_ROW,
    # 版面常數
    CONTENT_TOP, CONTENT_LEFT, CONTENT_WIDTH, CONTENT_HEIGHT,
)
```

### 主類別

| 方法 | 一行說明 |
|------|---------|
| `PanjitPresentation(template_path=None)` | 建立新簡報（可選模板） |
| `.add_title_slide(title, subtitle, department, owner, date, version)` | 封面頁（深藍背景） |
| `.add_section_divider(section_title)` | 章節分隔頁（淺藍背景） |
| `.add_content_slide(title, section_label="") -> slide` | 內容頁，回傳 slide 供後續加元素 |
| `.save(output_path)` | 存檔 |

### 元素函式（作用在 slide 上）

| 函式 | 用途 |
|------|------|
| `add_table(slide, data, col_widths=None, top=None, left=None, width=None, header_color="1F4E79", alt_row=True, font_size=10, caption=None)` | 表格（第一行自動為 header） |
| `add_image(slide, image_path, left=None, top=None, width=None, height=None, caption=None)` | 嵌入圖片（預設置中） |
| `add_bullets(slide, items, top=None, left=None, width=None, font_size=14, title=None)` | 項目列表（items 支援 `(text, indent)`） |
| `add_two_column(slide, left_fn, right_fn, ratio="1:1", top=None, gap=0.25)` | 雙欄佈局 |
| `add_text_box(slide, text, left, top, width, height=None, font_size=12, bold=False, color="1F2937", bg_color=None, border_left_color=None)` | 通用文字框（可加 callout 色條） |

### 格式化輔助

| 函式 | 用途 |
|------|------|
| `set_cell_style(cell, bg_color, font_color, font_size, bold, align)` | 單一 cell 樣式 |
| `apply_table_style(table, header_color, alt_row_color, ...)` | 整表套樣式（自動跳過合併儲存格） |

## T3：標準工作流程

```python
from pathlib import Path
import sys
sys.path.insert(0, "shared/tools")
from pptx_panjit import (
    PanjitPresentation, add_table, add_bullets, add_image, add_two_column,
    add_text_box, COLOR_WARNING, COLOR_ACCENT, COLOR_PRIMARY,
)

# 1. 建立簡報
prs = PanjitPresentation()

# 2. 封面
prs.add_title_slide(
    title="月度品質報告",
    subtitle="2026 Q1 可靠性驗證結果",
    department="QA Engineering",
    owner="林志明",
    date="2026-04-21",
    version="V1.0",
)

# 3. 章節分隔
prs.add_section_divider("第一章　可靠性測試")

# 4. 內容頁 + 表格
slide = prs.add_content_slide("AEC-Q101 結果", section_label="第一章")
add_table(slide, [
    ["項目", "規格", "結果"],
    ["HTRL", "1000h@150°C", "PASS"],
    ["HTGB", "1000h@20V", "PASS"],
])

# 5. 雙欄
slide2 = prs.add_content_slide("風險與行動")

def left_fn(s, left, top, width, h):
    add_bullets(s, ["風險 1", "風險 2"], left=left, top=top, width=width, title="關鍵發現")

def right_fn(s, left, top, width, h):
    add_text_box(s, "追加複測 77pcs", left=left, top=top, width=width,
                 bg_color=COLOR_WARNING, border_left_color=COLOR_ACCENT)

add_two_column(slide2, left_fn, right_fn, ratio="1:1")

# 6. 存檔
prs.save("output.pptx")
```

**完整執行**：
```bash
PYTHONUTF8=1 "C:\Users\lin46\.conda\envs\ai-office\python.exe" \
  shared/tools/pptx_panjit.py demo /tmp/panjit_demo.pptx

PYTHONUTF8=1 "C:\Users\lin46\.conda\envs\ai-office\python.exe" \
  shared/tools/office_validator.py /tmp/panjit_demo.pptx
```

Validator 必須回報 PASS 或只有 WARNING（無 ERROR）。

## T4：座標快速參考（panjit 常數名稱）

```
投影片尺寸：SLIDE_WIDTH × SLIDE_HEIGHT = 13.33" × 7.50"

標題列：
  TITLE_LEFT, TITLE_TOP, TITLE_WIDTH, TITLE_HEIGHT = 0.59", 0.12", 10.12", 0.80"

節標籤（標題下方）：
  SECTION_LABEL_LEFT, SECTION_LABEL_TOP = 0.59", 0.94"
  SECTION_LABEL_WIDTH, SECTION_LABEL_HEIGHT = 10.12", 0.30"

內容區：
  CONTENT_LEFT = 0.42"
  CONTENT_TOP = 1.35"
  CONTENT_WIDTH = 12.50"
  CONTENT_HEIGHT ≈ 5.65"（至頁尾前）
  CONTENT_BOTTOM = 7.00"

頁尾（版權）：
  FOOTER_LEFT, FOOTER_TOP = 0.22", 7.19"
  FOOTER_WIDTH, FOOTER_HEIGHT = 4.82", 0.28"

頁碼（右下）：
  PAGE_NUM_LEFT, PAGE_NUM_TOP = 12.50", 7.19"
  PAGE_NUM_WIDTH, PAGE_NUM_HEIGHT = 0.60", 0.28"
```

`add_xxx` 函式的 top/left/width 參數未指定時，自動套用 CONTENT_* 預設。

## T5：色彩對照

| 常數 | Hex | 用途 |
|------|-----|------|
| `COLOR_PRIMARY` | `1F4E79` | 主色：標題、表頭、封面背景 |
| `COLOR_SECONDARY` | `D6E4F0` | 輔色：章節分隔背景、次要區塊 |
| `COLOR_ACCENT` | `F4B084` | 強調：重點色條、callout 左邊 |
| `COLOR_SUCCESS` | `C6EFCE` | 綠底：通過/OK 標示 |
| `COLOR_WARNING` | `FFEB9C` | 黃底：警告/待確認 |
| `COLOR_DANGER` | `FFC7CE` | 紅底：失敗/NG |
| `COLOR_ALT_ROW` | `F2F2F2` | 表格交替行淺灰 |
| `COLOR_TEXT` | `1F2937` | 主文字深灰 |
| `COLOR_MUTED` | `6B7280` | 次要文字中灰（頁尾、caption） |
| `COLOR_WHITE` | `FFFFFF` | 白字 |

**使用規則**：
- 一份報告內相同語意用相同顏色（所有 FAIL 都用 DANGER）
- 禁止引入色盤外的顏色
- 顏色輸入永遠用 6 位 hex string（無 `#`），內部自動轉 RGBColor

## T6：常見陷阱

| 問題 | 原因 | 解法 |
|------|------|------|
| Validator 報 PPTX-004 Major overlap | 用了全頁背景矩形 | 改用 `slide.background.fill`（`_set_slide_background` 已內建） |
| Validator 報 PPTX-005 字太小 | footer/caption < 10pt | 本工具預設 footer 10pt、caption 10pt，不要手動調低 |
| 表格欄寬相加超過 CONTENT_WIDTH | col_widths 給太寬 | 確保 `sum(col_widths) ≤ CONTENT_WIDTH = 12.5` |
| 合併儲存格資料寫入失敗 | 寫到 spanned cell | `apply_table_style` 和 `add_table` 會自動 `if cell.is_spanned: continue` |
| 中文字型 fallback 成英文 | 沒設 East Asian font | `_set_run_font` 會自動設 `eastAsia=Microsoft JhengHei` |

## T7：驗證（必做）

產出後跑 `office_validator.py`：

```bash
PYTHONUTF8=1 "C:\Users\lin46\.conda\envs\ai-office\python.exe" \
  shared/tools/office_validator.py <output.pptx>
```

| 結果 | 處理 |
|------|------|
| PASS | 可交付 |
| WARNING | 檢視問題清單，能修的立即修正 |
| FAIL | 必須修所有 ERROR（通常是元素超出邊界或重疊 > 50%） |

結果必須以文字回報給使用者（PASS/WARNING/FAIL + 問題清單摘要）。
