---
name: pptx-brand-master
scope: internal
tracking: local-only
description: |
  WHAT：將 PANJIT 公司母片／品牌規範套用到可編輯 PPTX；固定封面、header、logo、頁尾、頁碼與內容安全區，但內容頁本身保持自由排版。
  WHEN：需符合公司格式、客戶要求可在 PowerPoint 內編輯，而且內容頁沒有固定模板、只要求品牌一致時。
  NOT：自由設計請用 pptx-authoring；PDF 分發或快速產出請用 marp-pptx；精修已有 pptx 請用 pptx-operations。
triggers:
  - pptx_panjit, PANJIT 簡報, panjit pptx, 公司母片, 公司格式
  - corporate master, branded pptx, brand overlay, 母片套用
  - semicon 色盤, 1F4E79, 企業標準版面, logo, 頁尾, 頁碼
  - add_title_slide, add_content_slide, CONTENT_LEFT, CONTENT_WIDTH
  - COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER
---

# PPTX 品牌母片 Overlay — pptx_panjit PANJIT 品牌路線

## T1：定位

這個 skill 不是「固定內容模板」。它的真實角色是：

- 套用公司母片與品牌元素
- 固定封面、頁尾、頁碼、logo、標題區與內容安全區
- 讓內容頁維持自由排版
- 作為 `pptx-authoring` 的 internal overlay，而不是獨立取代它

如果需求是「先自由生成內容，再符合公司格式」，正確做法是：

1. 用 `pptx-authoring` 的思路規劃內容頁
2. 以公司母片的 header / footer / safe area 為邊界排版
3. 用本 skill 套用品牌規範與固定元素

## T2：何時用這個 skill

| 情境 | 用本 skill | 用其他 skill |
|------|-----------|-------------|
| 公司正式簡報，需符合 corporate look | ✓ | |
| 客戶/上層要求可在 PowerPoint 內編輯 | ✓ | |
| 內容頁沒有固定模板，只有母片規範 | ✓ | |
| 從零自由設計、無公司格式約束 | | `pptx-authoring` |
| 快速 Markdown 轉簡報 / PDF 分發 | | `marp-pptx` |
| 已有 .pptx 要增量修改 | | `pptx-operations` |

**決策規則**：當「公司格式」其實只等於母片規範，而不是固定內容模板時，用本 skill。

## T3：母片規則摘要

以目前 PANJIT 範例簡報觀察，公司格式主要固定的是：

- 首頁與結尾頁的 title layout
- 內容頁的固定上方藍線 / logo / footer / 頁碼
- 內容頁標題區與內容區安全邊界
- 品牌色、字型與頁尾資訊

不固定的是：

- 中間內容頁的欄位切分
- 圖表、表格、圖片、callout 的具體配置
- 單頁是否雙欄、單欄、圖左文右、表格主導等版型

因此不要把內容頁硬編成少數幾種 API 樣板。內容頁應視為自由畫布，但必須待在 safe area 內。

## T4：API 速查

工具位置：`shared/tools/pptx_panjit.py`
正式 baseline spec：`.claude/skills-on-demand/pptx-brand-master/brand_spec.panjit.json`
預設 dump spec：`.claude/skills-on-demand/pptx-brand-master/brand_spec.default.json`
範例萃取 spec：`.claude/skills-on-demand/pptx-brand-master/brand_spec.ecr_ecn.sample.json`

```python
from pptx_panjit import (
    PanjitBrandMasterPresentation,
    add_table, add_image, add_bullets, add_two_column, add_text_box,
    load_brand_spec,
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
| `PanjitBrandMasterPresentation(template_path=None, brand_spec=None, brand_spec_path=None)` | 建立以公司母片規範為基底的新簡報 |
| `.add_title_slide(title, subtitle, department, owner, date, version)` | 封面頁 |
| `.add_section_divider(section_title)` | 章節頁，可用但不是必須 |
| `.add_master_content_slide(title, section_label="") -> slide` | 建立符合母片 header/footer 的內容頁骨架 |
| `.get_content_safe_area() -> dict` | 取得 title/content/footer/logo 的安全區座標 |
| `.save(output_path)` | 存檔 |

### CLI

| 指令 | 用途 |
|------|------|
| `python shared/tools/pptx_panjit.py dump-spec <out.json>` | 匯出預設 brand spec |
| `python shared/tools/pptx_panjit.py demo-with-spec <spec.json> <out.pptx>` | 用指定 spec 產生示範 PPT |
| `python shared/tools/pptx_panjit.py extract-spec <sample.pptx> <out.json> [--logo-output ...]` | 從真實範例簡報萃取 brand spec 與 logo |

### 元素函式（作用在 slide 上）

| 函式 | 用途 |
|------|------|
| `add_table(...)` | 在 safe area 內放表格 |
| `add_image(...)` | 在 safe area 內放圖片 |
| `add_bullets(...)` | 在 safe area 內放條列文字 |
| `add_two_column(...)` | 內容頁自由欄位配置的輔助函式，不是公司固定版型 |
| `add_text_box(...)` | 通用文字框 / callout，可配合品牌色使用 |

### 格式化輔助

| 函式 | 用途 |
|------|------|
| `set_cell_style(cell, bg_color, font_color, font_size, bold, align)` | 單一 cell 樣式 |
| `apply_table_style(table, header_color, alt_row_color, ...)` | 整表套樣式（自動跳過合併儲存格） |

## T5：標準工作流程

```python
from pathlib import Path
import sys
sys.path.insert(0, "shared/tools")
from pptx_panjit import (
    PanjitBrandMasterPresentation, add_table, add_bullets, add_image, add_two_column,
    add_text_box, load_brand_spec, COLOR_WARNING, COLOR_ACCENT, COLOR_PRIMARY,
)

# 1. 建立以公司母片規範為底的簡報
brand = load_brand_spec(".claude/skills-on-demand/pptx-brand-master/brand_spec.panjit.json")
prs = PanjitBrandMasterPresentation(brand_spec=brand)

# 2. 封面
prs.add_title_slide(
    title="月度品質報告",
    subtitle="2026 Q1 可靠性驗證結果",
    department="QA Engineering",
    owner="林志明",
    date="2026-04-21",
    version="V1.0",
)

# 3. 內容頁：標題固定，內容自由排版
slide = prs.add_master_content_slide("AEC-Q101 結果", section_label="供應商變更")
add_table(slide, [
    ["項目", "規格", "結果"],
    ["HTRL", "1000h@150°C", "PASS"],
    ["HTGB", "1000h@20V", "PASS"],
])

# 4. 第二頁：仍沿用母片，但版面可改成雙欄
slide2 = prs.add_master_content_slide("風險與行動")

def left_fn(s, left, top, width, h):
    add_bullets(s, ["風險 1", "風險 2"], left=left, top=top, width=width, title="關鍵發現")

def right_fn(s, left, top, width, h):
    add_text_box(s, "追加複測 77pcs", left=left, top=top, width=width,
                 bg_color=COLOR_WARNING, border_left_color=COLOR_ACCENT)

add_two_column(slide2, left_fn, right_fn, ratio="1:1")

# 5. 存檔
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

## T6：安全區與座標快速參考（panjit 常數名稱）

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

`add_xxx` 函式的 top/left/width 參數未指定時，自動套用 `CONTENT_*` 預設。

**實務規則**：

- 把 `CONTENT_*` 視為內容安全區，不要侵入 header、footer、logo 區
- 內容頁版面可以自由切欄，但不要破壞固定品牌元素
- 不要假設所有內容頁都用同一種表格/雙欄配置

## T7：色彩對照

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

## T8：常見陷阱

| 問題 | 原因 | 解法 |
|------|------|------|
| 把公司格式理解成固定內容模板 | 實際上只有母片與品牌元素固定 | 內容頁應自由排版，只受 safe area 約束 |
| Validator 報 PPTX-004 Major overlap | 用了全頁背景矩形 | 改用 `slide.background.fill`（`_set_slide_background` 已內建） |
| Validator 報 PPTX-005 字太小 | footer/caption < 10pt | 本工具預設 footer 10pt、caption 10pt，不要手動調低 |
| 表格欄寬相加超過 CONTENT_WIDTH | col_widths 給太寬 | 確保 `sum(col_widths) ≤ CONTENT_WIDTH = 12.5` |
| 合併儲存格資料寫入失敗 | 寫到 spanned cell | `apply_table_style` 和 `add_table` 會自動 `if cell.is_spanned: continue` |
| 中文字型 fallback 成英文 | 沒設 East Asian font | `_set_run_font` 會自動設 `eastAsia=Microsoft JhengHei` |

## T9：與其他 PPT skill 的分工

| 需求 | 用哪個 skill |
|------|-------------|
| 自由建立可編輯 PPTX，無公司格式限制 | `pptx-authoring` |
| 套公司母片與品牌規範，內容仍自由排版 | 本 skill |
| Markdown 大量內容快速轉簡報 / PDF | `marp-pptx` |
| 修改已有 PPTX、補原生圖表或複雜表格 | `pptx-operations` |

## T10：驗證（必做）

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
