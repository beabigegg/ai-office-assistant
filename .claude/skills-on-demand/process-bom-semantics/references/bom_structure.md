# BOM 資料庫結構與查詢模式

> 升級自: shared/kb/dynamic/patterns/bom_database_schema.md
> 升級日期: 2026-02-05

## 概述

BOM 資料入庫後存放於 SQLite，位於 `{P}/workspace/db/bom.db`。
包含原始表（raw_bom）和標準化表（std_bom）。

---

## 資料表結構

### raw_bom（原始資料表）

保留原始 CSV 欄位，共 62 欄，主要欄位：

| 欄位 | 說明 |
|------|------|
| `_id` | 主鍵 |
| `_source_file` | 來源檔案 |
| `_source_row` | 來源行號 |
| `ass_item_no` | 成品料號 |
| `bom_name` | BOM 名稱（唯一識別碼）|
| `bop` | 製程配方代碼 |
| `operation_seq_num` | 製程站別 |
| `com_item_no` | 配方/罐頭料號（或獨立料號）|
| `sub_com_item_no` | 實際原物料料號（可能為空）|
| `sub_com_item_m_type` | 物料類型（晶片/腳架/線材/膠...）|
| `sub_com_item_desc` | 物料描述（重要！解析來源）|
| `com_qty` | 用量（>0 主料，=0 備用料）|

### std_bom（標準化資料表）

從 Desc 欄位解析出的結構化資料，共 40 欄：

| 欄位 | 說明 | 來源 |
|------|------|------|
| `_id` | 主鍵 | |
| `_raw_id` | 關聯 raw_bom._id | |
| `ass_item_no` | 成品料號 | 原始 |
| `bom_name` | BOM 名稱 | 原始 |
| `bop` | 製程配方代碼 | 原始 |
| `operation_seq_num` | 製程站別 | 原始 |
| `sub_com_m_type` | 物料類型 | 原始 |
| **晶片相關** | | |
| `wafer_function` | 晶片功能（ZEN/SWI/SKY...）| 解析自 Desc |
| `wafer_size` | 晶圓尺寸（5"/6"/8"）| 解析自 Desc |
| `die_size_raw` | Die 尺寸（mil）| 解析自 Desc |
| `thickness` | 厚度（um）| 解析自 Desc |
| `metal` | 金屬層（ALAU/AUAU/ALSN...）| 解析自 Desc |
| **腳架相關** | | |
| `lef_package` | 封裝類型 | 解析自 Desc |
| `lef_option` | 腳架選項 | 解析自 Desc |
| `lef_form` | 形式（REEL/STRIP）| 解析自 Desc |
| `lef_material` | 材質（Cu/A42）| 解析自 Desc |
| **線材相關** | | |
| `wire_type` | 線材類型（CU/GOLD/AG WIRE）| 解析自 Desc |
| `wire_mil` | 線徑（phi1.0mil 等）| 解析自 Desc |
| `wire_grade` | 等級（Normal/GLF...）| 解析自 Desc |
| `is_clip` | 是否為 CLIP | 解析自 Desc |
| **膠相關** | | |
| `glue_type` | 膠類型（銀膠/錫膏/成型膠）| 解析自 Desc |
| `glue_model` | 膠型號 | 解析自 Desc |

---

## 重要：物料類型與欄位對應

**不同物料類型的資料在不同的資料列，關鍵欄位互斥：**

| sub_com_m_type | 有值的欄位 | 空白的欄位 |
|----------------|-----------|-----------|
| 晶片 | `metal`, `die_size_raw`, `wafer_*`, `thickness` | `lef_*`, `wire_*`, `glue_*` |
| 腳架 | `lef_material`, `lef_package`, `lef_option` | `metal`, `die_*`, `wire_*` |
| 線材 | `wire_type`, `wire_mil`, `wire_grade` | `metal`, `lef_*`, `glue_*` |
| 膠 | `glue_type`, `glue_model` | `metal`, `lef_*`, `wire_*` |

---

## ⚠️ 重要：BOM 雙層結構與 2nd Source

### Com Item vs Sub Com Item 的關係

BOM 資料有**兩個層級**，查詢物料時必須**同時查詢兩層再 UNION**：

| 層級 | 欄位 | 內容 |
|------|------|------|
| **Com Item** | `com_item_no`, `com_item_desc`, `com_item_m_type` | 配方/罐頭 **或** 2nd Source 實際料號 |
| **SubCom Item** | `sub_com_item_no`, `sub_com_item_desc`, `sub_com_item_m_type` | 主要實際原物料 |

### ❌ 錯誤理解（會漏料！）

```sql
-- 只查 SubCom → 漏掉 Com 層的 2nd Source
SELECT sub_com_item_no FROM raw_bom WHERE ...
```

### ✅ 正確查詢方式

```sql
-- 必須 UNION 兩層
SELECT com_item_no as item_no, com_item_desc as desc, com_item_m_type as m_type, 'Com' as layer
FROM raw_bom WHERE ass_item_no = ? AND length(com_item_no) > 0

UNION

SELECT sub_com_item_no, sub_com_item_desc, sub_com_item_m_type, 'SubCom'
FROM raw_bom WHERE ass_item_no = ? AND length(sub_com_item_no) > 0
```

### 實例驗證（已驗證 3 個產品）

| 產品 | Com Item 層 | SubCom Item 層 | 說明 |
|------|------------|----------------|------|
| MMDT3946_S1_00001 | **LEF000175** (SOT-363/A42) | LEF000044 (SOT-363/A42) | 同規格不同料號，皆為有效腳架 |
| MMSZ4691-V_R1_00001 | **WIR000108** (CU WIRE/1.2mil) | WIR000037 (CU WIRE/1.2mil) | 同規格不同料號，皆為有效線材 |
| BAV99W_R1_000A5 | **LEF000173** + **WIR000107** | LEF000040 + WIR000029/041 | 腳架和線材都有 2nd Source |

⚠️ **重要性：極高** — 只查 SubCom 層會漏掉有效的 2nd Source 原物料！

### RD- 研發產品的特殊行為（2026-02-22 驗證）

RD- 開頭的研發產品在 Com 層有特殊結構：
- **LEF 在 Com 層 + com_qty > 0**：39 筆，全部為 RD- 產品（Op 15/23）
- **WIR 在 Com 層 + com_qty > 0**：29 筆，全部為 RD- 產品（Op 23）

這與正式產品的 Com 層行為不同（正式產品 Com 層的 LEF/WIR 通常 com_qty = 0）。
分析時排除 RD- 產品即可規避此差異。

### 兩種 2nd Source 情況

**情況 A：Com 有料、SubCom 為空（獨立料號）**
- `Com Item No` = 實際料號（如 `LEF000172`）
- `Sub Com Item No` = 空白
- 特徵：Com Qty 通常 = 0.0

**情況 B：Com 和 SubCom 都有料（✅ 更常見！）**
- `Com Item No` = 2nd Source 料號
- `Sub Com Item No` = 主要料號
- 兩者規格相同但料號不同
- **查詢時必須 UNION 兩層才能取得完整清單**

---

## 跨物料類型關聯查詢

**核心：透過 `bom_name` 關聯同一 BOM 中不同物料類型的資料**

### 範例 1：查詢「背金 + 銅腳架」的組合（含 2nd Source）

```sql
WITH
-- 背金晶片（metal 後兩碼為 AU）
chip_au AS (
    SELECT DISTINCT bom_name, metal, die_size_raw
    FROM std_bom
    WHERE metal IN ('ALAU', 'AUAU')
),
-- 銅腳架（含獨立料號）
lef_cu AS (
    SELECT DISTINCT bom_name, lef_package, lef_material
    FROM std_bom
    WHERE lef_material = 'Cu'

    UNION

    -- 獨立料號中的銅腳架
    SELECT DISTINCT r.bom_name, NULL as lef_package, 'Cu' as lef_material
    FROM raw_bom r
    WHERE r.com_item_no LIKE 'LEF%'
      AND (r.sub_com_item_no IS NULL OR r.sub_com_item_no = '')
      AND r.com_item_desc LIKE '%/Cu%'
)

SELECT c.*, l.lef_package, l.lef_material
FROM chip_au c
INNER JOIN lef_cu l ON c.bom_name = l.bom_name
```

### 範例 2：查詢特定產品的完整原物料清單（含 2nd Source）

```sql
-- ⚠️ 必須 UNION 兩層才能取得完整清單
SELECT
    operation_seq_num as station,
    com_item_m_type as m_type,
    com_item_no as item_no,
    com_item_desc as desc,
    'Com' as layer
FROM raw_bom
WHERE ass_item_no = '{產品料號}' AND length(com_item_no) > 0

UNION

SELECT
    operation_seq_num,
    sub_com_item_m_type,
    sub_com_item_no,
    sub_com_item_desc,
    'SubCom'
FROM raw_bom
WHERE ass_item_no = '{產品料號}' AND length(sub_com_item_no) > 0

ORDER BY station, layer, m_type
```

### 範例 3：統計封裝 x 腳架材質 x 線材搭配

```sql
WITH
chip AS (
    SELECT bom_name, metal, die_size_raw
    FROM std_bom WHERE sub_com_m_type = '晶片'
),
lef AS (
    SELECT bom_name, lef_material, lef_package
    FROM std_bom WHERE sub_com_m_type = '腳架'
),
wire AS (
    SELECT bom_name, wire_type, wire_mil
    FROM std_bom WHERE sub_com_m_type = '線材'
)

SELECT
    l.lef_package, l.lef_material, w.wire_type, w.wire_mil,
    COUNT(DISTINCT c.bom_name) as bom_cnt,
    MIN(c.die_size_raw) as min_die,
    MAX(c.die_size_raw) as max_die
FROM chip c
LEFT JOIN lef l ON c.bom_name = l.bom_name
LEFT JOIN wire w ON c.bom_name = w.bom_name
GROUP BY l.lef_package, l.lef_material, w.wire_type, w.wire_mil
```

---

## 常用過濾條件

```sql
-- 排除研發料
WHERE ass_item_no NOT LIKE 'RD-%'

-- 排除 WIP 結構
WHERE alt_bom_designator NOT IN ('WIP', 'WIPOEM')
  OR alt_bom_designator IS NULL

-- 只看主料
WHERE com_qty > 0

-- 包含備用料（建議）
WHERE com_qty >= 0
```

---

## 資料統計（參考）

- 資料筆數：409,567 筆（raw_bom & std_bom）
- 唯一 BOM 數：約 26,000 個
- 封裝類型：28 種
- 最近全量驗證：2026-02-22
