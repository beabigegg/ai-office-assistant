---
name: process-bom-semantics
description: |
  半導體製程BOM語意規則與查詢模式。適用於：
  解析製程站別(Operation Seq Num)、判斷主料備用料(Com Qty)、
  解讀Bop製程編碼(焊接/腳架/線材/線徑)、WAF晶片料號生命週期、
  Desc欄位解析、跨物料類型關聯查詢、BOM雙層結構查詢。
  製程搭配規則：Die Size與封裝對應、腳架材質限制、金屬層與封裝搭配。
  Die Size精度規則：0.1mil精度，不可容差合併。
  當任務涉及製程BOM、站別、Com Qty、Bop編碼、WAF料號、
  Desc解析、bom_name關聯、晶片/腳架/線材搭配分析、
  Die Size範圍、背金/背銀、腳架Cu/A42選用、
  die diagonal、WAF回補、物料屬性判斷時觸發。
triggers:
  - 製程BOM, 站別, Operation Seq, Op 10, Op 15, Op 23, Op 28
  - Com Qty, 主料, 備用料, com_qty
  - Bop, BOP, 製程編碼, UAA, UAC, ECC, EAA, -DW, 一貫機, CLIP
  - WAF, 晶片料號, WAF0, WAF9, _CP, 晶片生命週期
  - Desc解析, bom_name, 跨物料關聯
  - Die Size, 封裝對應, 腳架材質, Cu腳架, A42, ALLOY42
  - 背金, 背銀, AGAG, AUAU, ALAU, ALSN, 金屬層
  - Die Attach, Eutectic, Epoxy, 共晶焊, 銀膠, Sn, Ag
  - 雙層結構, Com Item, SubCom, 2nd Source, 雙層查詢
  - die diagonal, die size 精度, 容差合併, WAF 回補, 跨BOP
  - BPO, Bond Pad Opening, 焊墊開口, mil單位, um換算
---

# 製程 BOM 語意規則

> 詳細範例、統計數據、SQL 範例見 `references/rule-details.md`

## Lazy Loading 路由表

| 問題類型 | 讀取 |
|---------|------|
| 詳細範例、統計、SQL 範例、修正歷史 | `references/rule-details.md` |
| Desc 欄位完整解析規則 | `references/desc_parsing.md` |
| BOM 資料庫結構與查詢模式 | `references/bom_structure.md` |
| 料號前綴與物料類型對照 | `references/material_coding.md` |

## 核心規則摘要

### R1: 製程站別語意 (OPERATION-SEQ-NUM)
信心度: 高 | 驗證: 4次

| 站別 | 名稱 | 站別 | 名稱 |
|------|------|------|------|
| 10 | 晶片站 | 28 | 成型站 |
| 15 | 焊接站 | 40/70/80 | WIP站 |
| 23 | 打線/焊接站 | 60/63/85 | 電鍍站 |
| 25 | 保護膠站(DO-218) | 90 | 包裝站 |

**Op 15 / Op 23 物料因製程類型而異**：

| 製程類型 | Op 15 物料 | Op 23 物料 |
|---------|-----------|-----------|
| U/E 標準 | 膠+腳架 | **線材** |
| U/E -DW 一貫機 | （空） | 膠+腳架+線材 |
| P/CLIP | 膠+腳架 | **膠+腳架+跳線** |
| PNPNC1 (DO-218) | 膠+腳架+跳線 | - |

### R2: 有效料/備用料判斷 (COM-QTY-RULE)
信心度: 高 | 驗證: 3次

- `Com Qty > 0` = **有效使用料**（但不代表唯一主料，同站可有多筆 >0）
- `Com Qty = 0` = **備用料/備選**（可靠標記）
- Sub Com Remarks 是變更歷史記錄，**不是**主/備判斷依據

### R3: 替代結構標識 (ALT-BOM-DESIGNATOR)
信心度: 高 | 驗證: 3次

| 值 | 含義 |
|----|------|
| 空值 | 主結構（8,487 BOMs） |
| 製程變體描述 | 替代製程結構（Alt Designator 編碼了製程變體類型，與 bop 對應） |
| WIP/WIPOEM | 半成品入廠，可不考慮（15 BOMs） |

**注意**: 替代結構 != 替代料。替代結構是整個製程配方變體。詳細對照表見 `references/rule-details.md` R3。

### R4: Bop 製程編碼規則 (BOP-CODING)
信心度: 高 | 驗證: 2次（0 反例）

#### U/E 製程格式: `[焊接][腳架][線材][線徑][-DW]`

| 位置 | 碼 | 含義 |
|------|---|------|
| 第1碼 | U=共晶焊, E=銀膠 |
| 第2碼 | C=銅腳架, A=A42腳架, H=HD腳架(Cu) |
| 第3碼 | C=銅線, A=金線, G=銀線 |
| 後續 | 08~24 線徑(mil), -DW=一貫機 |

**P 製程**：`P[腳架][線材][線徑]` / CLIP: `P[腳架類型][封裝結構]` / `PNPNC1`=DO-218 專用

### R5: WAF 晶片料號生命週期 (WAF-LIFECYCLE)
信心度: 高 | 驗證: 4次

- WAF0 → WAF9 是同一晶片的**生命週期狀態**（非替代關係）
- WAF9 = 已入庫，數量單位改為 K 數
- `_CP` = 已完成 Chip Probing；**Sub 層永遠無 _CP**，Com 層才有
- 實際命名規則比「WAF0=點測前, WAF9=點測後」更複雜，以 BOM Com→Sub 對應關係為準

**跨 BOP WAF 回補**（D-114）：同料號跨 BOP 合併所有 unique WAF 填入缺失 BOP（65 料號/174 BOP）。

### R6: Desc 解析優先原則 (DESC-PRIORITY)
信心度: 極高 | 驗證: 3次

- 獨立欄位空白率 90~95%，**Desc 欄位空白率 0~3%** → 優先從 Desc 解析
- BOM Desc 是物料屬性的 **Source of Truth**（優先序：BOM desc > BOP fallback）
- Pattern B（11.7%）資訊只在 Com Item Desc → fallback 到 Com 層，`_parser_used` 標記來源
- 詳細格式與 Die Size 解析見 `references/rule-details.md` R6

### R7: 跨物料關聯查詢 (BOM-NAME-JOIN)
信心度: 高 | 驗證: 3次

透過 `bom_name` 關聯同一 BOM 中不同物料類型。INNER JOIN 時注意 CLIP 製程 BOM 無線材（572 BOMs）。

### R8: BOM 雙層結構與 2nd Source (DUAL-LAYER-QUERY)
信心度: 高 | 驗證: 4次

**極重要**：BOM 原物料分布在 Com Item 層和 SubCom Item 層兩個層級。

**硬規則**：任何涉及 std_bom 的 WAF/WIR/LEF/COM 查詢，**必須同時查 sub_com_item_no 和 com_item_no 兩層**（UNION）。
- Pattern B（`_parser_used LIKE 'com_%'`）物料資訊只在 Com 層
- **實際事故**：只查 sub_com 層遺漏 1,699 個成品的 Die Size/Thickness
- 2nd Source 規則適用範圍：量產品（非 RD-）的 LEF/WIR 類型
- SQL 範例見 `references/rule-details.md` R8

### R9: 封裝與 Die Size 範圍 (PACKAGE-DIE-SIZE)
信心度: 高 | 驗證: 3次

| 分類 | Max Die Size | 代表封裝 |
|------|-------------|---------|
| 超大型 (>=150) | 170 mil | DO-218 |
| 大型 (100~150) | 120 mil | TO-277/C |
| 中型 (50~100) | 76 mil | SMBF, SMAF |
| 小型 (<50) | 43 mil | SOT-23, SOD-123 |

### R10: 腳架材質與封裝限制 (LEADFRAME-MATERIAL)
信心度: 高 | 驗證: 4次（0 反例）

- A42 (ALLOY42)：僅小型封裝（SOT-23, SOD-123 等）
- Cu (銅)：全範圍
- **硬規則**：Die Size > 50 mil / CLIP 製程 / DO-218 → 必須 Cu 腳架

### R11: 金屬層代碼語意 (METAL-CODING)
信心度: 高 | 驗證: 4次

Metal 四字元：前兩字=正面金屬，後兩字=背面金屬

| 代碼 | 正/背 | 分類 | Die Size 範圍 |
|------|-------|------|--------------|
| AUAU | Au/Au | 背金 | 46~120 mil |
| ALAU | Al/Au | 背金 | 9~33.5 mil（僅小型封裝） |
| AGAG | Ag/Ag | **背銀** | 26~170 mil |
| ALSN | Al/Sn | 無背金 | 一般 |

- 查「背金」→ ALAU + AUAU，**不含 AGAG**
- AGAG/AUAU 只搭配 Cu 腳架
- wafer_function 與金屬層**無絕對對應**（詳見 `references/rule-details.md` R11）

### R12: 背面金屬與 Die Attach (BACKMETAL-DA)
信心度: 高 | 驗證: 2次

| 背面金屬 | Die Attach | PKG CODE D/A |
|---------|-----------|-------------|
| Sn (錫) | Eutectic (共晶焊) | EU |
| Ag (銀) | Epoxy (銀膠) | EP |

**硬規則**：Ag 無法做 Eutectic；Sn 無法做 Epoxy。需同時供應兩種 DA → 拆成兩種晶片。

### R13: Compound 取決於 LF 材質 (COMPOUND-LF-DEPENDENCY)
信心度: 高 | 驗證: 1次（978 組 0 例外）

| LF 材質 | 常用 Compound |
|---------|--------------|
| A42 | 500C (ELER-8-500C) |
| Cu | G600 (EME-G600FL) |

DA 製程不影響 Compound 選擇，LF 材質才是決定因素。

### R14: Die Size 不可容差合併 (DIE-SIZE-EXACT-PRECISION)
信心度: 極高 | 驗證: 2次

**硬規則**：Die size 精確到 **0.1 mil**，絕對不可做容差合併或取整。
- 10.0 和 10.2 mil 就是不同的 die
- 單位：系統統一用 **mil**（1 mil = 25.4 um），入庫時換算

### R15: BPO 焊墊開口定義 (BOND-PAD-OPENING)
信心度: 高 | 驗證: 1次

| 縮寫 | 全名 | 含義 |
|------|------|------|
| **BOP** | Bill of Process | 製程文件 |
| **BPO** | Bond Pad Opening | 焊墊開口尺寸 |

TVS/ESD 產品只有一個 Bond Pad：BPO(G)=空，BPO(S)=打線區域（um）。

## 過濾規則快速參考

```sql
WHERE ass_item_no NOT LIKE 'RD-%'                        -- 排除研發料
  AND (alt_bom_designator NOT IN ('WIP','WIPOEM') OR alt_bom_designator IS NULL)  -- 排除 WIP
  AND com_qty >= 0                                        -- 包含備用料
```

## 來源與信心度

| 規則 | 信心度 | 驗證 | 規則 | 信心度 | 驗證 |
|------|--------|------|------|--------|------|
| R1 站別 | 高 | 4 | R9 封裝/Die | 高 | 3 |
| R2 有效料 | 高 | 3 | R10 腳架材質 | 高 | 4 |
| R3 替代結構 | 高 | 3 | R11 金屬層 | 高(已修正) | 4 |
| R4 Bop編碼 | 高 | 3 | R12 DA搭配 | 高 | 2 |
| R5 WAF生命 | 高 | 4 | R13 Compound | 高 | 1 |
| R6 Desc解析 | 極高 | 3 | R14 Die精度 | 極高 | 2 |
| R7 跨物料JOIN | 高 | 3 | R15 BPO | 高 | 1 |

## 升級記錄

見 `.skill.yaml` 的 `upgrade_history` 欄位。最近更新：2026-03-20（R14 mil 換算 + R15 BPO）。
