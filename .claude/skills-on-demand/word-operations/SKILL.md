---
name: word-operations
description: |
  MCP Word Server 操作規則與最佳實踐。適用於：
  透過 mcp__docx__* 工具建立和編輯 Word 文件時的正確操作流程、
  COM Range.Find 跨 run 搜尋取代、段落索引規則、表格操作、書籤功能。
  當任務涉及 Word、docx、文件、報告、mcp__docx 時觸發。
---

# MCP Word Server 操作規則

## 工具總覽（30 個）

| 區塊 | 工具 | 數量 |
|------|------|------|
| A. 生命週期 | create_document, open_document, save_document, close_document, get_document_info | 5 |
| B. 內容寫入 | append_paragraph, insert_paragraph, append_heading, append_page_break, write_at_bookmark | 5 |
| C. 讀取搜尋 | read_paragraphs, find_text, find_replace, get_bookmarks | 4 |
| D. 表格 | add_table, read_table, write_table_cell, format_table_cell, merge_table_cells | 5 |
| E. 格式化 | format_paragraph, add_style, apply_style | 3 |
| F. 圖片形狀 | insert_image, insert_shape, add_text_box | 3 |
| G. 節與頁面 | page_setup, add_section, add_header_footer | 3 |
| H. 工具 | export_to_pdf, get_statistics | 2 |

---

## R1：文件生命週期管理（信心度：very high）

**必須遵循的流程**：
1. `create_document` 或 `open_document` 開啟文件
2. 執行所有內容操作
3. `save_document` 儲存
4. `close_document` 關閉並釋放 COM

**注意**：`close_document` 會同時退出 Word 應用程式。未呼叫會導致 Word 程序殘留。

---

## R2：find_replace 的 COM 優勢（信心度：very high）

**核心設計選擇**：使用 COM（非 python-docx）的主要原因。

python-docx 的問題：Word 內部將文字分散在多個 `<w:r>` XML 元素中（稱為 "runs"）。
例如 "Hello World" 可能被拆為 `<w:r>Hello</w:r><w:r> </w:r><w:r>World</w:r>`。
python-docx 的搜尋只能在單個 run 內匹配，導致跨 run 的文字搜尋不到。

**COM 的 Range.Find.Execute** 完美解決此問題——它在文件的邏輯文字層面搜尋，
不受 XML 結構影響。

```
使用方式：
find_replace(find="舊文字", replace="新文字", replace_all=true)
```

---

## R3：段落索引規則（信心度：very high）

- 所有段落操作使用 **1-based index**（COM convention）
- `doc.Paragraphs(1)` 是第一個段落
- `append_paragraph` 在文件末尾追加，回傳新段落的 index
- `insert_paragraph(after_paragraph_index=5, ...)` 在第 5 段後插入

**查詢段落**：用 `read_paragraphs(start=1, count=50)` 讀取段落內容和樣式資訊。

---

## R4：表格操作注意事項（信心度：very high）

### 4a. 表格 index 從 1 開始
`doc.Tables(1)` 是文件中的第一個表格。

### 4b. 儲存格文字有尾端控制字元
Word 表格儲存格的文字末尾有 `\r\x07`（段落標記 + cell end mark）。
`read_table` 已自動剝除這些字元。

### 4c. 合併儲存格
`merge_table_cells(table_index, start_row, start_col, end_row, end_col)`
合併後的儲存格座標會重新編號，後續操作需注意。

---

## R5：書籤功能（信心度：high）

書籤是 Word 模板化報告的關鍵功能。

**工作流程**：
1. 用模板建立文件：`create_document(path, template="template.docx")`
2. 查詢書籤：`get_bookmarks()`
3. 在書籤位置寫入：`write_at_bookmark(bookmark_name="title", text="報告標題")`

**模板 + 書籤 = 增量編輯的最佳實踐**。

---

## R6：建立 Word 報告的標準流程範本（信心度：high）

### 從零建立
```
1. create_document(path)
2. page_setup(orientation="portrait", paper_size="A4")
3. append_heading(text="報告標題", level=1)
4. append_paragraph(text="摘要內容...", font_size=12)
5. append_heading(text="第一章", level=2)
6. append_paragraph(text="章節內容...")
7. add_table(rows=5, cols=3, headers=["欄位1","欄位2","欄位3"], data=[...])
8. append_page_break()
9. append_heading(text="第二章", level=2)
10. insert_image(image_path="chart.png", width=5.0)
11. add_header_footer(header_text="報告標題", page_number=true)
12. save_document()
13. export_to_pdf(output_path="report.pdf")  # 可選
14. close_document()
```

### 增量編輯（修改已有文件）
```
1. open_document(path)
2. find_replace(find="舊日期", replace="新日期")
3. write_table_cell(table_index=1, row=3, col=2, text="更新值")
4. save_document()
5. close_document()
```

---

## R7：匯出 PDF（信心度：high）

`export_to_pdf` 使用 Word 內建的 PDF 轉換功能。

**注意**：匯出 PDF 後文件仍保持開啟狀態（不會改變當前文件格式）。
需要分別 `save_document` 儲存 .docx 和 `export_to_pdf` 產出 PDF。

---

## Q：品質規範與常見錯誤（Quality Rules）

### Q1：產出前必做清單
1. `page_setup` 設定紙張大小和方向（預設 A4 直式）
2. `add_header_footer` 加入頁首（報告標題）和頁碼
3. Heading 層級正確（H1 章 → H2 節 → H3 小節），可生成目錄
4. 表格 header 列有深色背景 + 白字，資料列有交替色
5. 圖片有適當寬度（不超出頁面邊界，A4 內文寬 ≤ 6.5"）
6. 長報告在章節間加 page_break
7. **save 後執行 `office_validator.py` 驗證**，修正所有 ERROR 後才能 close

### Q2：常見錯誤規避
| 錯誤 | 正確做法 |
|------|---------|
| 全文用 append_paragraph 不分層 | 用 append_heading 建立結構，內容再用 paragraph |
| 表格無標題列格式 | format_table_cell row=1 設深色背景白字 |
| find_replace 用 python-docx | 必須用 COM find_replace，才能跨 run 搜尋（R2） |
| 忘記 close_document | save + close 缺一不可，否則 Word 殘留 |
| 段落間距不一致 | 用 format_paragraph 統一 space_before/space_after |
| 字型混亂 | 中文 Microsoft JhengHei + 英文 Calibri，全文統一 |

### Q3：報告結構建議
- **封面**：標題 + 日期 + 作者（Heading 1 + 正文）
- **目錄**：（Word 內建目錄需手動更新，可略）
- **正文**：H2 分章 → H3 分節 → 段落 + 表格 + 圖片
- **附錄**：原始資料表、參考資料

---

## R8：heading 樣式（信心度：high）

`append_heading(text, level)` 使用 Word 內建標題樣式：

| level | 樣式 | 用途 |
|-------|------|------|
| 1 | Heading 1 | 章節標題 |
| 2 | Heading 2 | 子章節 |
| 3 | Heading 3 | 小節 |
| 4-9 | Heading 4-9 | 更細的層級 |

標題會自動出現在文件的「導覽窗格」和目錄中。
