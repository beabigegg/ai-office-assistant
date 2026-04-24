---
name: pptx-operations
scope: generic
tracking: tracked
description: |
  WHAT：透過 mcp__pptx__* 工具（COM 自動化）精修已有 .pptx，處理原生圖表、複雜表格、版面調整。
  WHEN：修改現有簡報、add_chart 原生可編輯圖表、20+ 欄 add_table、delete_shape 清理 placeholder。
  NOT：從零新建簡報請用 pptx-authoring 或 pptx-template；Markdown 大量內容請用 marp-pptx。
triggers:
  - mcp__pptx, MCP PPTX, PPTX COM
  - add_chart, add_table, add_rich_textbox, modify_shape
  - delete_shape, duplicate_slide, merge_table_cells
  - set_gradient_fill, set_slide_background
  - 精修簡報, 編輯已有 pptx, 原生圖表
---

# PPTX 精修 — MCP COM 增量編輯路線

## 工具總覽（25 個）

| 區塊 | 工具 | 數量 |
|------|------|------|
| A. 生命週期 | create_presentation, save_presentation, export_to_pdf, close_presentation, list_slide_layouts | 5 |
| B. 投影片 | add_slide, duplicate_slide, set_slide_background | 3 |
| C. 文字 | add_textbox, add_rich_textbox, add_bullet_list, set_placeholder_text | 4 |
| D. 表格 | add_table, format_table_cell, merge_table_cells | 3 |
| E. 圖形 | add_shape, add_image, delete_shape, modify_shape | 4 |
| F. 圖表 | add_chart | 1 |
| G. 進階 | add_connector, set_gradient_fill, get_slide_info, get_presentation_info, add_presenter_notes | 5 |

---

## R1：新增投影片後必須刪除預設 placeholder（信心度：very high）

使用 `add_slide(layout_index=6)` 新增空白投影片時，PowerPoint 仍會自動插入一個
`Type=14, Name='Title 1'` 的 placeholder（顯示「按一下以新增標題」）。

**必須操作**：新增投影片後，立即用 `delete_shape` 刪除該 placeholder。

```
標準流程：
1. add_slide(layout_index=6)
2. get_slide_info(slide_index=N)  ← 確認 shape [1] 是 Type=14 Title
3. delete_shape(slide_index=N, shape_index=1)
```

**批次刪除建議**：如果一次新增多張投影片，可以全部新增後再逐頁刪除。
刪除順序不影響其他投影片的 shape index（各頁獨立編號）。

**注意**：Slide 1（標題頁）通常使用 layout_index=1，其 Title 和 Subtitle
placeholder 是有用的，不需刪除。

---

## R2：add_chart COM API 限制與正確操作模式（信心度：very high）

PowerPoint COM 圖表有多個已知限制，必須使用特定模式：

### 2a. 必須用 AddChart，不能用 AddChart2
`AddChart2` 在 COM 自動化中會拋出 E_FAIL (-2147467259)。
Server 已內建使用 `Shapes.AddChart(chart_type, left, top, width, height)`。

### 2b. SetSourceData 不可用
`chart.SetSourceData()` 在 PowerPoint 內嵌圖表中會失敗。
正確做法是直接覆寫工作表儲存格。

### 2c. 圖表資料寫入的正確流程
```
1. AddChart 建立圖表（帶預設範例資料）
2. chart.ChartData.Activate() + sleep(1.5)
3. 取得 wb = cd.Workbook, ws = wb.Worksheets(1)
4. ws.UsedRange.Clear() 清除全部預設資料
5. A1 設為空格 " "（與預設結構一致）
6. A2 起寫入 categories
7. B1 起寫入 series header，B2 起寫入數值
8. wb.Close(True)  ← SaveChanges=True 觸發圖表刷新
9. 用 SeriesCollection().Delete() 刪除多餘 series
10. **chart.SeriesCollection(n).XValues = categories** ← 強制設定分類標籤
    （wb.Close 後圖表可能快取舊的分類名如「第一季~第四季」，
     即使儲存格已更新，必須透過 XValues 強制覆蓋）
11. 設定 HasTitle / HasLegend 等屬性
```

### 2d. 預設圖表的工作表結構（繁中 Office）
```
     |  A      |  B      |  C      |  D      |
  1  | " "     | 數列 1  | 數列 2  | 數列 3  |
  2  | 類別 1  | 4.3     | 2.4     | 2.0     |
  3  | 類別 2  | 2.5     | 4.4     | 2.0     |
  4  | 類別 3  | 3.5     | 1.8     | 3.0     |
  5  | 類別 4  | 4.5     | 2.8     | 5.0     |
```
預設 3 series x 4 categories。超出部分需覆寫為 None 並刪除多餘 Series。

### 2e. 支援的圖表類型
| chart_type | XlChartType 常數 |
|---|---|
| column | 51 |
| column_stacked | 52 |
| bar | 57 |
| pie | 5 |
| line | 4 |
| doughnut | -4120 |
| area | 1 |

---

## R3：add_rich_textbox 的 runs 結構（信心度：very high）

每個 run 為一個 dict，支援的 key：

| Key | 型別 | 預設值 | 說明 |
|-----|------|--------|------|
| text | str | 必填 | 文字內容 |
| size | int | 14 | 字體大小 |
| color | str | "000000" | 顏色 hex |
| bold | bool | false | 粗體 |
| italic | bool | false | 斜體 |
| name | str | "Microsoft JhengHei" | 字型 |
| newline | bool | false | 在此 run 前插入換行 |

**COM 原理**：先組合全部文字寫入 TextRange，再用 `Characters(pos, length)`
逐 run 設定格式（COM 是 1-based index）。newline 插入 `\r` 字元。

---

## R4：建立簡報的標準流程範本（信心度：high）

```
1. create_presentation(title, subtitle)
2. 設定 Slide 1 樣式：
   - set_gradient_fill(slide_index=1, target="slide", ...)
   - modify_shape 調整標題/副標題字色
   - add_presenter_notes（可選）
3. 批次 add_slide(layout_index=6) 新增所有空白頁
4. 批次 delete_shape 刪除每頁的預設 Title placeholder
5. 逐頁建立內容：
   - set_slide_background 設定背景色
   - add_textbox 頁面標題
   - 內容元素（chart / table / rich_textbox / shape / bullet_list）
6. save_presentation(path)
7. get_presentation_info 確認最終狀態
```

---

## R5：常用版面座標參考（13.333" x 7.5" 標準寬螢幕）

| 元素 | left | top | width | height | 說明 |
|------|------|-----|-------|--------|------|
| 頁標題 | 0.5 | 0.15 | 12.0 | 0.5 | 26pt 粗體 |
| 左半內容 | 0.5 | 0.9 | 6.0 | — | 左欄 |
| 右半內容 | 6.9 | 0.9 | 6.0 | — | 右欄 |
| 全寬內容 | 0.4 | 0.9 | 12.5 | — | 滿版 |
| 下半區塊 | 0.5 | 4.0 | 12.3 | 3.2 | 下半頁 |

---

## R6：shape_type 擴充清單（信心度：very high）

| shape_type | 說明 | 常數 |
|---|---|---|
| rectangle | 矩形 | 1 |
| rounded_rect | 圓角矩形 | 5 |
| oval | 橢圓 | 9 |
| triangle | 三角形 | 7 |
| diamond | 菱形 | 4 |
| hexagon | 六邊形 | 10 |
| chevron | V 形箭頭 | 52 |
| pentagon | 五邊形 | 51 |
| star | 五角星 | 92 |
| arrow_right | 右箭頭 | 33 |
| arrow_down | 下箭頭 | 36 |
| left_arrow | 左箭頭 | 34 |
| up_arrow | 上箭頭 | 35 |

---

## R7：表格操作注意事項（信心度：high）

### 7a. merge_table_cells 需要正確的 table_shape_index
先用 `get_slide_info` 查詢表格的 shape index（Type=19 的元素）。

### 7b. alt_row_color 從第 2 筆資料列開始交替
偶數列（index 1, 3, 5...）上色。header 不受影響。

### 7c. format_table_cell 的 row/col 從 1 開始
row=1 是 header 列，row=2 起是資料列。

---

## Q：品質規範與常見錯誤（Quality Rules）

### Q1：產出前必做清單
1. 每頁空白投影片已刪除預設 Title placeholder（R1）
2. Slide 1 標題頁有漸層背景或主色背景，與內容頁區分
3. 每頁只傳達一個核心訊息，遵循 6×6 原則（≤6 行 × ≤6 字/行）
4. 圖表已設定 HasTitle + HasLegend，分類標籤已用 XValues 強制設定（R2c）
5. 所有文字使用 Microsoft JhengHei，英文可用 Calibri
6. get_presentation_info 確認最終頁數和內容完整
7. **save 後執行 `office_validator.py` 驗證**，將 PASS/WARNING/FAIL 結果文字回報使用者，修正所有 ERROR 後才能 close（CLI 環境無截圖，視覺確認由使用者自行開檔）

### Q2：常見錯誤規避
| 錯誤 | 正確做法 |
|------|---------|
| 忘記刪除預設 placeholder | add_slide 後立刻 delete_shape（R1） |
| 文字塞滿整頁 | 用圖表/表格取代大段文字，留白提升可讀性 |
| 每頁用不同配色 | 統一色盤（1F4E79 主色 + D6E4F0 輔色 + F4B084 強調） |
| 圖表用 AddChart2 | 只能用 AddChart（R2a） |
| 忘記 wb.Close(True) | 圖表資料寫完必須 Close(True) 觸發刷新（R2c） |
| 元素超出投影片邊界 | 參考 R5 座標，left+width ≤ 13.0", top+height ≤ 7.2" |
| 字級過多 | 最多 3 級：標題 24-28pt → 內容 16-18pt → 註解 12pt |
| 重複相同版面 | 交替使用不同佈局（雙欄、卡片、數據 callout） |
| 純文字投影片 | 每頁需有視覺元素（圖表/表格/形狀/圖示） |
| 標題下方加裝飾線 | AI 生成的特徵——用留白或背景色取代 |
| 低對比元素 | 文字和圖示都必須與背景有足夠對比 |

### Q3：投影片結構建議
- **第 1 頁**：標題 + 副標題 + 日期（layout_index=1，保留 placeholder）
- **第 2 頁**：目錄/大綱（bullet_list）
- **中間頁**：每頁一主題（圖表/表格/要點）
- **最後一頁**：摘要/結論/下一步

### Q4：佈局變化建議（避免單調）
- **雙欄**：左文字 + 右圖表（或反向）
- **圖示+文字行**：圖示在色圓中 + 粗體標題 + 說明
- **2×2 / 2×3 網格**：一側圖片 + 另側內容卡片
- **大數字 Callout**：關鍵數據 60-72pt + 下方小標籤
- **比較欄位**：前/後、優/缺、方案 A/B 並排
- **時間線/流程**：編號步驟 + 箭頭連結

### Q5：間距規範
- 0.5" 最小邊距
- 0.3-0.5" 元素間距（選一個標準，全簡報一致）
- 不要填滿每一寸空間——留白是設計的一部分

---

## R8：set_gradient_fill 用法（信心度：very high）

| 參數 | 說明 |
|------|------|
| target="slide" | 投影片背景漸層（會自動設定 FollowMasterBackground=False） |
| target="shape" | shape 填充漸層（需提供 shape_index） |
| gradient_style | horizontal / vertical / diagonal_up / diagonal_down / from_center |
| variant | 1-4，同一方向的不同變體 |
| color1, color2 | 兩端顏色 hex |

**COM 原理**：`fill.TwoColorGradient(style, variant)` + `ForeColor` / `BackColor`。
