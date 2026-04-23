---
name: plm-pdf-ingestion
description: |
  WHAT：Aras Innovator PLM 文件擷取 + PA/OI/CP/FMEA PDF 解析策略（Docling GPU vs PyMuPDF）。
  WHEN：PLM OAuth ROPC、SOAP 查詢、Vault PDF 下載、大型 PDF 分批切割、字元級交織解析。
  NOT：簡單 PDF 讀寫請用 pdf skill；非 PLM 視覺表格請用 table-reader。
triggers:
  - PLM, Aras Innovator, OAuth ROPC, plm_fetch, Vault endpoint
  - PA 文件, OI 文件, CP 文件, FMEA 文件, 製程分析
  - Docling, GPU 轉換, bad_alloc, 分批切割, CHUNK_SIZE
  - PyMuPDF, fitz, find_tables, hybrid_pdf_parser
  - ingest_pa, ingest_doc, reingest_doc
  - AIAG-VDA, 字元級交織, CJK interleaved
---

# PLM PDF 文件擷取與解析策略

> 適用範圍：process-analysis 專案的 PA/OI/CP/FMEA 文件入庫管線
> 資料來源：PA-L05 / PA-L003 / PA-L004 / ECR-L67 / ECR-L63 / D-149 / D-150 / D-152

## 1. Aras Innovator PLM 認證與查詢（R1）

### 1.1 OAuth ROPC Token 取得

`POST {base_url}/OAuthServer/connect/token`

必要欄位（缺一會失敗）：
- `grant_type=password`
- `username`
- `password`（**必須 MD5 雜湊**，否則回 `incompatible_hash_use_md5`）
- `client_id=InnovatorClient`
- `scope=openid Innovator offline_access`
- `database=資料庫名稱`（缺少回 `invalid_grant`）

### 1.2 SOAP 文件查詢

`POST {base_url}/Server/InnovatorServer.aspx`

Headers:
- `SOAPACTION: "ApplyItem"`
- `queryType: Released`（僅取已發行版本）
- `sync: true`
- `timezone_name: Taipei Standard Time`
- `Authorization: Bearer {token}`

### 1.3 PDF Vault 下載

`GET {base_url}/vault/vaultserver.aspx?dbName={db}&fileId={id}&fileName={name}&vaultId={vault_id}`

加 `Authorization: Bearer {token}`，直接回 PDF stream。

### 1.4 實作位置

`shared/tools/plm_fetch.py`（統一入口）
- `plm_fetch.py --update` = 批次更新所有文件
- 自動觸發 `_auto_convert_oi_to_md()`（D-159）

## 2. PDF 解析工具選擇策略（R2）

| 文件類型 | 結構特徵 | 建議工具 | 理由 |
|---------|---------|---------|------|
| PA（製程分析） | 合併儲存格、併排表、跨頁、表外標籤 | **Docling GPU**（分批） | 複雜結構需視覺 Transformer |
| OI（作業指示） | 文字段落為主 + 少量表格 | **Docling GPU** 或 PyMuPDF `get_text` | 段落優先 |
| CP（控制計畫） | AIAG 標準 13 欄固定表 | **PyMuPDF `find_tables`** | 結構固定，程式化高效 |
| FMEA | AIAG-VDA 標準 32 欄固定表 | **PyMuPDF `find_tables`** | 結構固定，效率高 |
| 複雜非標表格（問卷/稽核） | 合併/視覺線條 | **table-reader Agent** | 視覺辨識 |

### 2.1 Hybrid 策略（PA/OI 專用）

`shared/tools/hybrid_pdf_parser.py::HybridPDFParser`：

1. `PyMuPDF find_tables()` 每頁偵測，`min_words_vertical=2, min_words_horizontal=2` 過濾無效表格
2. 連續表格頁合為群組，**最大 10 頁**防 `bad_alloc`
3. 表格群組 → 子 PDF → Docling GPU 轉 Markdown
4. 純文字頁 → PyMuPDF `get_text()`
5. 最後合併所有片段為完整 Markdown

驗證：hybrid vs 純 Docling MD 被同一 ingest parser 解析，category row count 差異 0%（WB-PA002 1303 筆、WB-PA003 1933 筆）。

## 3. Docling GPU 大型 PDF 分批策略（R3）

### 3.1 為何需要分批

Docling 轉換大型 PDF 時（>10 頁），C++ 預處理層（PDF 渲染）會因 **CPU RAM 不足**觸發 `std::bad_alloc`，導致 CUDA context 損毀（`unknown error`）。

**根本原因**：PDF 渲染在 **CPU RAM**，不是 VRAM。VRAM 大不代表安全。

### 3.2 分批實作

```python
# 每批最多 10 頁
CHUNK_SIZE = 10

# 用 PyMuPDF (fitz) 切割
import fitz
src = fitz.open(pdf_path)
for i in range(0, src.page_count, CHUNK_SIZE):
    chunk = fitz.open()
    chunk.insert_pdf(src, from_page=i, to_page=min(i+CHUNK_SIZE-1, src.page_count-1))
    chunk.save(chunk_pdf)
    # 獨立執行 Docling，Markdown 累積合併
```

### 3.3 實作位置

- `shared/tools/ingest_pa_docling.py::_docling_convert_chunked()`
- `shared/tools/run_docling_gpu.py`

驗證：WB-PA002(34頁)、WB-PA003(32頁) 皆成功。

## 4. FMEA 字元級交織格式（R4）

部分站別（1730/1740）FMEA PDF 中英文不是分行排列，而是**字元級交織**：

```
原始：M人en=Men/人
正常：Men / 人
```

### 4.1 偵測方法

PyMuPDF `find_tables` 提取後：
- 正常分行（1420-1920 多數站）→ `split_zh_en()` 按行分
- 字元級交織（1730/1740）→ `split_interleaved()` 按 CJK Unicode 範圍分離

### 4.2 CJK 偵測

```python
def is_cjk(c):
    return '\u4e00' <= c <= '\u9fff' or '\u3000' <= c <= '\u303f'
```

## 5. reingest_doc.py 統一分派器（R5）

`shared/tools/reingest_doc.py` 為 37 站的統一分派器：

- 依 `station` 和 `doc_type` 路由到對應的 parser
- 處理 cp950 encoding 問題（Python 腳本開頭 `PYTHONUTF8=1`）
- 統一 output_path 命名規則

## 6. 反例與注意事項

### 6.1 不要用 Docling 解析 CP/FMEA
結構固定的標準表格用 PyMuPDF `find_tables` 更快更可靠，Docling 反而會把欄位合併錯亂。

### 6.2 不要單支腳本寫認證邏輯
所有 PLM 抓取走 `plm_fetch.py`，不要重複實作 OAuth token。

### 6.3 不要假設 PyMuPDF 能抓 ● 符號
ECR-L20：PDF 中的 ● 符號常為**向量圖形**（filled circle path），PyMuPDF `get_text()` 和 `find_tables()` 都無法擷取。需用像素級影像分析驗證（見 reliability-testing R5 相關說明）。

### 6.4 PyMuPDF `find_tables()` 座標不可信
對旋轉表格的 cell 座標嚴重偏移（y 座標在同一行的不同格之間跳躍），不可作為像素掃描的定位基準。

## 應用場景

- 新站別 PA/OI/CP/FMEA 文件入庫
- PDF 解析腳本選擇工具
- 大型 PDF 轉換失敗除錯
- PLM 文件拉取自動化

## 關聯

- 關聯決策：D-149（PLM OAuth）、D-150（PA入庫 Pipeline）、D-152（Hybrid PDF Parser）、D-159（OI 自動轉 MD）
- 關聯 learning：PA-L003、PA-L004、PA-L05、ECR-L63、ECR-L67
- 關聯工具：`plm_fetch.py`、`hybrid_pdf_parser.py`、`ingest_pa_docling.py`、`reingest_doc.py`
- 關聯 Agent：table-reader（視覺辨識複雜表格）
- 關聯 Skill：graph-rag（PA 入庫後的查詢入口）、mil-std-750（● 符號解讀）
