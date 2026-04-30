---
name: read-pdf
description: |
  通用 PDF 讀取/提取入口。任何專案需要讀取 PDF 內容時，先走
  `shared/tools/pdf_to_markdown.py` 的統一流程：PyMuPDF 全文提取，
  偵測到表格頁時預設啟用 Docling 表格增強，必要時再升級到 `table-reader`。
---

產出可供後續分析、入庫、摘要或比對使用的 Markdown：

1. 確認輸入 PDF 路徑與輸出 `.md` 路徑
2. 先視需要執行 `analyze` 了解頁數、低文字頁比例、表格群組
3. 執行 `shared/tools/pdf_to_markdown.py convert`
4. 回報輸出檔路徑、使用頁範圍、是否觸發 Docling 表格增強
5. 若仍有複雜表格遺漏或結構錯亂，再升級到 `extract-pdf-table` / `table-reader`

標準流程：

```bash
bash shared/tools/conda-python.sh shared/tools/pdf_to_markdown.py analyze <input.pdf>
bash shared/tools/conda-python.sh shared/tools/pdf_to_markdown.py convert <input.pdf> -o <output.md>
```

補充規則：
- `pdf_to_markdown.py` 已預設啟用 Docling 表格增強，不必額外加 `--docling-tables`
- 若只需部分頁面，使用 `--pages 10-25`
- 若 Docling 不適合或環境缺套件，可明確加 `--no-docling-tables`
- 合併儲存格、跨頁、併排表、表外標籤若仍提取失真，改用 `extract-pdf-table`
- PLM 的 PA/OI/CP/FMEA 批次入庫，改走 `plm-pdf-ingestion`，不要手工重建專案特化流程
