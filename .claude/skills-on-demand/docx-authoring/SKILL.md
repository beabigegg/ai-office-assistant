---
name: docx-authoring
scope: generic
tracking: tracked
description: |
  WHAT：用 docx-js（Node.js）從零新建 Word 文件，或 unpack/pack XML 精修既有文件。
  WHEN：需要 TOC、多欄、tracked changes、footnotes、精確格式控制的正式 Word 文件。
  NOT：簡單增量編輯（find_replace、改儲存格）請用 word-operations（MCP COM）。
triggers:
  - docx-js, docx npm, pptxgenjs 姊妹包, Node.js Word
  - Word 新建, 報告 Word, 正式函文, 測試報告 docx
  - TOC, 目錄, footnotes, 多欄, tracked changes, 頁首頁尾
  - unpack pack XML, document.xml 編輯, OOXML
---

# Word 新建 — docx-js code-based 路線

## 環境

```bash
# Git Bash 執行 docx-js 腳本
NODE_PATH="C:\Users\lin46\AppData\Roaming\npm\node_modules" node create_doc.js
```

## 基本文件建立

```javascript
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, HeadingLevel, AlignmentType, BorderStyle,
  WidthType, ShadingType, PageNumber, LevelFormat, PageBreak
} = require('docx');
const fs = require('fs');

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Microsoft JhengHei", size: 24 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Microsoft JhengHei" },
        paragraph: { spacing: { before: 240, after: 240 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Microsoft JhengHei" },
        paragraph: { spacing: { before: 180, after: 180 }, outlineLevel: 1 } },
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 },  // A4 (DXA: 1440 = 1 inch)
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
      }
    },
    headers: {
      default: new Header({ children: [
        new Paragraph({ children: [new TextRun("報告標題")] })
      ]})
    },
    footers: {
      default: new Footer({ children: [
        new Paragraph({ children: [
          new TextRun("Page "),
          new TextRun({ children: [PageNumber.CURRENT] })
        ]})
      ]})
    },
    children: [
      new Paragraph({
        heading: HeadingLevel.HEADING_1,
        children: [new TextRun("第一章")]
      }),
      new Paragraph({ children: [new TextRun("內容文字")] }),
      new Paragraph({ children: [new PageBreak()] }),  // 分頁
    ]
  }]
});

Packer.toBuffer(doc).then(buf => fs.writeFileSync("output.docx", buf));
```

## 關鍵規則

| 規則 | 正確做法 |
|------|---------|
| 頁面大小 | 必須明確設定：A4 = `11906×16838`，Letter = `12240×15840`（DXA） |
| 換行 | 用新的 `Paragraph`，絕不用 `\n` |
| 清單 bullet | 用 `LevelFormat.BULLET`，絕不插入 `•` Unicode 字元 |
| 分頁 | `new Paragraph({ children: [new PageBreak()] })` |
| 表格寬度 | `columnWidths` 加總必須等於 `table width`，每個 cell 也要設 `width` |
| 表格寬度單位 | 永遠用 `WidthType.DXA`，禁用 `WidthType.PERCENTAGE` |

## 表格

```javascript
const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };

// A4 內文寬（1" 四邊距）= 11906 - 2880 = 9026 DXA
new Table({
  width: { size: 9026, type: WidthType.DXA },
  columnWidths: [3000, 3000, 3026],  // 加總 = 9026
  rows: [
    new TableRow({
      tableHeader: true,
      children: [
        new TableCell({
          borders,
          width: { size: 3000, type: WidthType.DXA },
          shading: { fill: "1F4E79", type: ShadingType.CLEAR },
          margins: { top: 80, bottom: 80, left: 120, right: 120 },
          children: [new Paragraph({
            children: [new TextRun({ text: "欄位", bold: true, color: "FFFFFF" })]
          })]
        }),
        // ... 其餘標題欄
      ]
    }),
    // 資料列
    new TableRow({
      children: [
        new TableCell({
          borders,
          width: { size: 3000, type: WidthType.DXA },
          margins: { top: 80, bottom: 80, left: 120, right: 120 },
          children: [new Paragraph({ children: [new TextRun("值")] })]
        }),
        // ...
      ]
    }),
  ]
})
```

## 清單

```javascript
const doc = new Document({
  numbering: {
    config: [
      { reference: "bullets",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
          alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbers",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.",
          alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ]
  },
  sections: [{ children: [
    new Paragraph({ numbering: { reference: "bullets", level: 0 },
      children: [new TextRun("清單項目")] }),
    new Paragraph({ numbering: { reference: "numbers", level: 0 },
      children: [new TextRun("有序項目")] }),
  ]}]
});
```

## 圖片

```javascript
const { ImageRun } = require('docx');

new Paragraph({ children: [
  new ImageRun({
    type: "png",  // 必填：png / jpg / jpeg / gif / bmp
    data: fs.readFileSync("chart.png"),
    transformation: { width: 400, height: 300 },  // pixels
    altText: { title: "圖表", description: "說明", name: "圖1" }  // 三個都必填
  })
]})
```

## 編輯已有文件（unpack → edit XML → pack）

```bash
# 1. 解包（pretty-print XML）
python /d/ai-office/shared/tools/office/unpack.py document.docx unpacked/

# 2. 直接編輯 unpacked/word/document.xml（用 Edit tool）

# 3. 重包（含驗證）
python /d/ai-office/shared/tools/office/pack.py unpacked/ output.docx --original document.docx
```

## 驗證

```bash
python /d/ai-office/shared/tools/office/validate.py output.docx
```
