---
name: pptx-authoring
scope: generic
tracking: tracked
description: |
  WHAT：用 pptxgenjs（Node.js）從零建立原生可編輯 .pptx（自由設計，非公司模板）。
  WHEN：全新簡報設計、需在 PowerPoint 內直接編輯、不受公司模板限制、程式化生成。
  NOT：公司標準模板請用 pptx-template；精修已有 .pptx 請用 pptx-operations；快速 PDF 分發請用 marp-pptx。
triggers:
  - pptxgenjs, pptx-js, Node.js PPT
  - 新建 pptx, 從零建立簡報, 程式化簡報
  - 自由設計, 非公司模板, 可編輯簡報
  - unpack pack XML, slide.xml 編輯
---

# PPTX 新建 — pptxgenjs 自由設計路線

## 環境

```bash
NODE_PATH="C:\Users\lin46\AppData\Roaming\npm\node_modules" node create_pptx.js
```

腳本輔助工具：`/d/ai-office/shared/tools/pptx/`

---

## 基本結構

```javascript
const pptxgen = require("pptxgenjs");

let prs = new pptxgen();
prs.layout = 'LAYOUT_16x9';  // 10" × 5.625"
prs.title = '簡報標題';

let slide = prs.addSlide();
slide.addText("標題文字", {
  x: 0.5, y: 0.3, w: 9, h: 0.8,
  fontSize: 28, bold: true, color: "1F4E79"
});

prs.writeFile({ fileName: "output.pptx" });
```

**座標單位**：英吋（inches）。LAYOUT_16x9 = 寬 10"，高 5.625"。

---

## 關鍵陷阱（必讀）

| 陷阱 | 說明 |
|------|------|
| **顏色不能加 `#`** | `color: "1F4E79"` ✅，`color: "#1F4E79"` ❌ → 檔案損毀 |
| **不要重用 options 物件** | 每個元素給獨立的 `{}` → 共用物件會被 mutation 覆寫 |
| **ROUNDED_RECTANGLE + accent overlay** | 圓角矩形無法被直角 overlay 完全蓋住，改用 `RECTANGLE` |
| **shadow offset 不能為負** | 向上陰影用 `angle: 270` + 正數 offset |
| **Unicode bullets 禁用** | `{ bullet: true }` ✅，`"• 項目"` ❌ → 雙層 bullet |
| **charSpacing 非 letterSpacing** | `letterSpacing` 被靜默忽略 |
| **多行文字需 breakLine** | 最後一項不需要 |

---

## 常用元素

### 文字

```javascript
// 普通文字
slide.addText("內容", { x: 0.5, y: 1, w: 9, h: 1, fontSize: 18, color: "363636" });

// 富文字（粗體 + 斜體混排）
slide.addText([
  { text: "粗體 ", options: { bold: true } },
  { text: "正常文字" }
], { x: 0.5, y: 1, w: 9, h: 1, fontSize: 16 });

// 多行（breakLine）
slide.addText([
  { text: "第一行", options: { breakLine: true } },
  { text: "第二行", options: { breakLine: true } },
  { text: "第三行" }
], { x: 0.5, y: 1.5, w: 9, h: 2, fontSize: 16 });
```

### 子彈清單

```javascript
slide.addText([
  { text: "第一點", options: { bullet: true, breakLine: true } },
  { text: "第二點", options: { bullet: true, breakLine: true } },
  { text: "子項目", options: { bullet: true, indentLevel: 1, breakLine: true } },
  { text: "第三點", options: { bullet: true } }
], { x: 0.5, y: 1.5, w: 8, h: 3, fontSize: 16, color: "363636" });
```

### 形狀

```javascript
// 矩形（帶陰影）
slide.addShape(prs.shapes.RECTANGLE, {
  x: 0, y: 0, w: 10, h: 0.8,
  fill: { color: "1F4E79" },
  shadow: { type: "outer", color: "000000", blur: 6, offset: 2, angle: 135, opacity: 0.15 }
});

// 線條
slide.addShape(prs.shapes.LINE, {
  x: 0.5, y: 1.2, w: 9, h: 0,
  line: { color: "D6E4F0", width: 1.5 }
});
```

### 表格

```javascript
// ⚠️ 每個 cell 用獨立物件，不要重用
let rows = [
  [{ text: "欄位A", options: { bold: true, color: "FFFFFF", fill: "1F4E79" } },
   { text: "欄位B", options: { bold: true, color: "FFFFFF", fill: "1F4E79" } }],
  [{ text: "值1" }, { text: "值2" }],
];
slide.addTable(rows, {
  x: 0.5, y: 1.5, w: 9,
  fontSize: 12,
  border: { pt: 0.5, color: "CCCCCC" },
  align: "left"
});
```

### 圖片

```javascript
// 從檔案
slide.addImage({ path: "chart.png", x: 1, y: 1, w: 5, h: 3 });

// 從 base64（無 I/O，較快）
const imgData = "image/png;base64," + require("fs").readFileSync("img.png").toString("base64");
slide.addImage({ data: imgData, x: 1, y: 1, w: 5, h: 3 });

// 保持比例計算
const origW = 1920, origH = 1080, maxH = 3.0;
const w = maxH * (origW / origH);
slide.addImage({ path: "img.png", x: (10 - w) / 2, y: 1.2, w, h: maxH });
```

---

## 版面設計原則

- 每頁一個核心訊息，≤6 行 × ≤6 字/行
- 標題深藍（1F4E79），副標題淺藍（D6E4F0），正文深灰（363636）
- 重點橘色（F4B084），成功綠底（C6EFCE），警告黃底（FFEB9C），錯誤紅底（FFC7CE）
- 字型：英文 Calibri，中文 Microsoft JhengHei
- 標題 24-28pt，內容 14-18pt，註解 10-12pt

---

## 從模板建立（unpack/edit/pack 流程）

適合：有現成 .pptx 模板、要替換內容但保留版型。

```bash
# 1. 分析模板外觀
python /d/ai-office/shared/tools/pptx/thumbnail.py template.pptx
python -m markitdown template.pptx

# 2. 解包
python /d/ai-office/shared/tools/office/unpack.py template.pptx unpacked/

# 3. 複製 / 調整投影片
python /d/ai-office/shared/tools/pptx/add_slide.py unpacked/ slide2.xml

# 4. 編輯 unpacked/ppt/slides/slide{N}.xml

# 5. 清理 + 打包
python /d/ai-office/shared/tools/pptx/clean.py unpacked/
python /d/ai-office/shared/tools/office/pack.py unpacked/ output.pptx --original template.pptx
```

> **先完成所有結構調整（刪除/複製/重排投影片），再逐頁編輯內容。**
> 內容編輯階段（步驟 4）可以用 subagents 平行處理不同 slide XML。

---

## 流程選擇速查

| 需求 | 工具 |
|------|------|
| 全新設計，需可在 PowerPoint 編輯 | pptxgenjs（本 skill） |
| 公司標準模板（Panjit） | pptx-template skill |
| 快速產出 / PDF 分發 | marp-pptx skill |
| 修改已有 .pptx | pptx-operations skill（MCP）或 unpack/edit/pack |
