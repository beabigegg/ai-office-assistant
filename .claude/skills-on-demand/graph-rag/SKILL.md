---
name: graph-rag
description: |
  WHAT：查詢製程分析 Knowledge Graph（FMEA/CP/OI 實體關聯圖），走 graph_query.py。
  WHEN：問失效原因/預防/偵測、跨站比較、影響分析、路徑追溯、覆蓋 gap 分析。
  NOT：若要查 decisions/learning 語意走 kb.py search；若要查 SQL 結構走 SCHEMA 檔。
triggers:
  - GraphRAG, knowledge graph, 知識圖譜, graph_query
  - 失效模式, failure mode, 失效原因, failure cause
  - 預防措施, prevention, 偵測措施, detection, 影響分析
  - 1610, 1620, Eutectic, Epoxy, Die Bond
  - 頂針, 吸嘴, 腳架, 晶片, 膠材, X-RAY
  - 跨站比較, 物料影響, 管制覆蓋, gap 分析, 路徑查詢
  - trace, impact, compare, related, path, gaps, search
---

# Knowledge Graph 查詢 — GraphRAG 入口

## 概述

本 Skill 用於查詢製程分析的 Knowledge Graph（知識圖譜）。
KG 包含 1610（Eutectic 共晶）和 1620（Epoxy 銀膠）兩站的 FMEA/CP/OI 實體和關係。

## 何時觸發

當用戶的問題涉及以下情境時，**自動使用 graph_query.py 查詢**：

1. **因果追溯**：「某失效的原因是什麼？」「怎麼預防/偵測？」
2. **影響分析**：「頂針壞了會怎樣？」「某設備故障影響什麼？」
3. **跨站比較**：「1610 和 1620 的差異？」「Epoxy 獨有的失效？」
4. **物料/設備關聯**：「吸嘴相關的管制？」「X-RAY 檢什麼？」
5. **Gap 分析**：「哪些失效沒有 CP 管制？」
6. **路徑查詢**：「溫度異常和推力不合格有什麼關係？」

## 工具

```bash
python shared/tools/graph_query.py <command> [args]
```

### 可用指令

| 指令 | 用途 | 範例 |
|------|------|------|
| `trace <名稱>` | 多跳追溯（預設 2 跳） | `trace 吸嘴印 --station 1610 --depth 3` |
| `impact <名稱>` | 影響分析（找相關失效+管制） | `impact 頂針 --station 1610` |
| `compare <s1> <s2>` | 跨站比較 | `compare 1610 1620 --type failure_mode` |
| `related <名稱>` | 列出所有相關實體 | `related 顯微鏡 --station 1620` |
| `path <A> <B>` | 找兩實體間最短路徑 | `path 溫度 推力 --station 1610` |
| `gaps` | FMEA-CP 覆蓋 gap | `gaps --station 1620` |
| `search <關鍵字>` | 搜尋實體 | `search 膠 --type material --station 1620` |
| `stats` | KG 統計 | `stats` |

### 常用參數
- `--station` / `-s`：指定站別（1610 或 1620）
- `--type` / `-t`：指定實體類型（failure_mode, material, equipment 等）
- `--depth` / `-d`：trace 的跳數（預設 2）

## KG 結構

### Entity 類型
| Type | 說明 | 數量 |
|------|------|------|
| specification | 規格值 | 504 |
| action | 操作動作 | 493 |
| document_ref | 文件引用 | 478 |
| process_step | 製程步驟 | 263 |
| material | 物料 | 253 |
| equipment | 設備 | 225 |
| condition | 條件 | 189 |
| failure_cause | 失效原因 | 106 |
| failure_mode | 失效模式 | 73 |
| prevention | 預防措施 | 71 |
| detection | 偵測措施 | 24 |

### Relation 類型
| Type | 說明 | 數量 |
|------|------|------|
| uses | 使用 | 962 |
| applies_to | 適用於 | 888 |
| references | 引用 | 653 |
| specifies | 定義 | 493 |
| requires | 需要 | 266 |
| triggers | 觸發 | 176 |
| controls | 管制 | 167 |
| detects | 偵測 | 153 |
| prevents | 預防 | 143 |
| causes | 導致 | 129 |

### 站別
- **1610**：晶粒黏著共晶 Eutectic DB
- **1620**：晶粒黏著銀膠 Epoxy DB

## 使用模式

### 1. 用戶問因果問題 → 用 trace 或 impact
```
用戶：「頂針磨損會造成什麼問題？」
→ python graph_query.py impact 頂針磨損
→ python graph_query.py trace 頂針磨損 --depth 3
```

### 2. 用戶問比較問題 → 用 compare
```
用戶：「1620 比 1610 多哪些失效模式？」
→ python graph_query.py compare 1610 1620 --type failure_mode
```

### 3. 用戶問管制覆蓋 → 用 gaps
```
用戶：「1620 有哪些風險沒管到？」
→ python graph_query.py gaps --station 1620
```

### 4. 用戶問關聯 → 用 related 或 search
```
用戶：「X-RAY 在檢查什麼？」
→ python graph_query.py related X-RAY
```

## 注意事項

- 查詢結果可能較多，用 `| head -30` 限制輸出
- 若找不到結果，嘗試簡化關鍵字（如用「頂針」而非「頂針磨損」）
- 跨站查詢不指定 `--station` 會列出兩站的結果
- graph_query.py 的輸出是 UTF-8 文字，bash 終端可能亂碼 → 用 `2>&1 | cat` 或寫入檔案
