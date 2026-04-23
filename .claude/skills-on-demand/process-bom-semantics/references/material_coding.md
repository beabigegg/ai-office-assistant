# 料號前綴與物料類型對照

> 升級自: shared/kb/dynamic/column_semantics.md (料號命名規則章節)
> 升級日期: 2026-02-05

## 料號前綴對照表

| 前綴 | 類型 | 說明 | 信心度 |
|------|------|------|--------|
| WAF | 晶片 | Wafer | 高 |
| COM | 耗材 | 膠類等消耗品 | 高 |
| LEF | 腳架 | Lead Frame | 高 |
| WIR | 線材 | Wire | 高 |
| PAC | 包裝材料 | Packing Material | 高 |
| RAW | 原物料 | Raw Material | 高 |

## WAF 晶片料號生命週期

```
WAF0xxxxx (點測前)
    |
    | CP (Chip Probing) 點測
    v
WAF9xxxxx_CP (點測後)
```

### 規則說明

| 狀態 | 料號格式 | 說明 |
|------|---------|------|
| 點測前 | WAF0xxxxx | 原始晶片 |
| 點測後 | WAF9xxxxx_CP | 數量單位改為 K 數 |

**重要**: WAF0 -> WAF9 **不是替代關係**，是同一晶片的不同生命週期狀態。

---

## Com Item No 配方前綴（罐頭）

配方/罐頭是一組原物料的組合碼，前綴對應站別：

| 前綴 | 站別 | 說明 |
|------|------|------|
| DBT, DBD, DBSMAFC | 15 | Die Bonding 配方 |
| WBD, WBSMAFC, DWBDO | 23 | Wire Bonding 配方 |
| T23D, D123D, T363D | 23 | 打線配方 |
| SOT, SOD, SMAF, DFN | 60, 90 | 電鍍/包裝配方 |
| WFT | - | 特殊配方 |

### 配方格式範例

```
DBT23_U1_COP5_00 = SOT-23 焊接配方
SOT23_PA0037 = SOT-23 包裝配方
D123D12-15C12WX1 = SOD-123 打線配方
```

---

## 獨立料號識別

當 `Com Item No` 為以下格式且 `Sub Com Item No` 為空時，表示是獨立料號（2nd Source 導入）：

| Com Item No 格式 | 物料類型 |
|-----------------|---------|
| WAF* | 晶片 |
| LEF* | 腳架 |
| WIR* | 線材 |
| COM* | 耗材/膠 |
| PAC* | 包裝材料 |

### 識別特徵

```sql
-- 識別獨立料號
SELECT *
FROM raw_bom
WHERE (sub_com_item_no IS NULL OR sub_com_item_no = '')
  AND (com_item_no LIKE 'WAF%'
    OR com_item_no LIKE 'LEF%'
    OR com_item_no LIKE 'WIR%'
    OR com_item_no LIKE 'COM%'
    OR com_item_no LIKE 'PAC%')
```

---

## 過濾規則

### RD- 開頭料號

- 含義: 研發用料
- 處理: **分析時應排除**

```sql
WHERE ass_item_no NOT LIKE 'RD-%'
```
