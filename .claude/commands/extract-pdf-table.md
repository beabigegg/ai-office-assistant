---
name: extract-pdf-table
description: |
  提取 PDF 複雜表格。適用於合併儲存格、跨頁、多欄並列、表外標籤等
  一般 pdfplumber / PyMuPDF 難以穩定解析的表格。
---

產出複雜 PDF 表格提取結果：

1. 確認輸入 PDF 或頁面 PNG 路徑
2. 若輸入是 PDF，先用 `read-pdf` / `pdf_to_markdown.py` 嘗試統一抽取流程
3. 只有在複雜表格仍失真時，才把目標頁導出為 PNG
4. 使用 `table-reader` agent 處理複雜表格提取
5. 產出同目錄 `_extracted.md` 或使用者指定輸出路徑
6. 回報提取範圍、表格數量、任何版面不確定點

步驟：
- 一般 PDF 文字或規則表格先走 `read-pdf`
- 若存在合併儲存格、跨頁、並列表格或表外上下文標籤，使用 `table-reader` agent
- 必要時補充文件類型上下文，例如 parameter sheet / OI / questionnaire
- 回報輸出檔路徑與尚待人工確認的欄位
