---
name: pdf
scope: generic
tracking: tracked
description: |
  WHAT：PDF 基本操作（讀文字/表格、合併分割旋轉、新建 PDF、浮水印加密、OCR）。
  WHEN：一般 .pdf 檔案處理，pypdf/pdfplumber/reportlab 可解決的任務。
  NOT：合併儲存格/跨頁複雜表格請用 table-reader；PLM/PA/OI/CP/FMEA 管線請用 plm-pdf-ingestion。
triggers:
  - PDF, .pdf, pdf 讀取, pdf 提取
  - pypdf, pdfplumber, reportlab, qpdf
  - PDF 合併, PDF 分割, PDF 旋轉, PDF 加密, PDF 浮水印
  - OCR, pytesseract, pdf2image, 掃描稿
  - 新建 PDF, PDF 報告, PDF 表單
---

# PDF 操作（Python code-based）

## 環境

```bash
PYTHONUTF8=1 "C:\Users\lin46\.conda\envs\ai-office\python.exe" your_script.py
```

輔助腳本位於 `/d/ai-office/pdf/scripts/`。

---

## 讀取與提取

### 文字提取（pdfplumber，保留版面）

```python
import pdfplumber

with pdfplumber.open("document.pdf") as pdf:
    for page in pdf.pages:
        print(page.extract_text())
```

### 表格提取（pdfplumber）

```python
import pdfplumber
import pandas as pd

with pdfplumber.open("document.pdf") as pdf:
    all_tables = []
    for page in pdf.pages:
        for table in page.extract_tables():
            if table:
                df = pd.DataFrame(table[1:], columns=table[0])
                all_tables.append(df)

if all_tables:
    pd.concat(all_tables, ignore_index=True).to_excel("extracted.xlsx", index=False)
```

> 合併儲存格、跨頁、多欄複雜表格 → 改用 `table-reader` agent（視覺提取）。

### 快速文字（命令列）

```bash
pdftotext -layout input.pdf output.txt
```

---

## 合併 / 分割 / 旋轉（pypdf）

```python
from pypdf import PdfReader, PdfWriter

# 合併
writer = PdfWriter()
for f in ["a.pdf", "b.pdf"]:
    for page in PdfReader(f).pages:
        writer.add_page(page)
with open("merged.pdf", "wb") as out:
    writer.write(out)

# 分割（每頁一檔）
reader = PdfReader("input.pdf")
for i, page in enumerate(reader.pages):
    w = PdfWriter()
    w.add_page(page)
    with open(f"page_{i+1}.pdf", "wb") as out:
        w.write(out)

# 旋轉
reader = PdfReader("input.pdf")
writer = PdfWriter()
page = reader.pages[0]
page.rotate(90)
writer.add_page(page)
with open("rotated.pdf", "wb") as out:
    writer.write(out)
```

```bash
# qpdf 命令列合併
qpdf --empty --pages file1.pdf file2.pdf -- merged.pdf
```

---

## 新建 PDF（reportlab）

```python
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

doc = SimpleDocTemplate("report.pdf", pagesize=A4)
styles = getSampleStyleSheet()
story = []

story.append(Paragraph("報告標題", styles['Title']))
story.append(Spacer(1, 12))
story.append(Paragraph("內容文字", styles['Normal']))

# 表格
data = [["欄位A", "欄位B", "欄位C"], ["值1", "值2", "值3"]]
t = Table(data)
t.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1F4E79')),
    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
    ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
    ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
]))
story.append(t)

doc.build(story)
```

### 重要：下標/上標

```python
# ❌ 禁用 Unicode 下標（₀₁₂）→ 渲染為黑色方塊
# ✅ 用 XML 標籤
Paragraph("H<sub>2</sub>O", styles['Normal'])
Paragraph("x<super>2</super>", styles['Normal'])
```

---

## 浮水印 / 加密

```python
from pypdf import PdfReader, PdfWriter

# 浮水印
watermark = PdfReader("watermark.pdf").pages[0]
reader = PdfReader("document.pdf")
writer = PdfWriter()
for page in reader.pages:
    page.merge_page(watermark)
    writer.add_page(page)
with open("watermarked.pdf", "wb") as out:
    writer.write(out)

# 加密
writer.encrypt("user_pass", "owner_pass")
```

---

## OCR 掃描稿

```python
# 需要：pip install pytesseract pdf2image  + Tesseract 安裝
import pytesseract
from pdf2image import convert_from_path

images = convert_from_path('scanned.pdf')
text = ""
for i, img in enumerate(images):
    text += f"--- Page {i+1} ---\n"
    text += pytesseract.image_to_string(img, lang='eng+chi_tra')
```

---

## 工具速查

| 任務 | 工具 |
|------|------|
| 提取文字/表格 | pdfplumber |
| 合併/分割/旋轉 | pypdf |
| 新建 PDF | reportlab |
| 命令列合併 | qpdf |
| 複雜表格（合併儲存格） | table-reader agent |
| OCR | pytesseract + pdf2image |
