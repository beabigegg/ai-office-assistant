# Desc 欄位完整解析規則

> 升級自: shared/kb/dynamic/column_semantics.md (Desc 解析規則章節)
> 升級日期: 2026-02-05

## 重要原則

**獨立欄位空白率 90~95%，Desc 欄位空白率僅 0~3%**
**結論：優先從 Desc 欄位解析資料，不依賴獨立欄位**

---

## Sub Com Item Desc 解析（依物料類型）

### 晶片格式
```
{Wafer Function}/{Wafer Size}/{Wafer Type}/{Die Size}/{Die Size2}/{Thickness}/{Metal}/
```

| 位置 | 欄位 | 範例 |
|------|------|------|
| 1 | Wafer Function | SWI, ZEN, MOS, SKY, TVS, TRA |
| 2 | Wafer Size | 5", 6", 8" |
| 3 | Wafer Type | 5DS02MH-K |
| 4 | Die Size | 10, 35 |
| 5 | Die Size2 | *10mil, *35mil |
| 6 | Thickness | 230um |
| 7 | Metal | ALAU, AGAG, ALSN |

範例：`SWI/5"/5DS02MH-K/10/*10mil/230um/ALAU/`

### 腳架格式
```
腳架/{Package}/{Option}/{Form}/{Material}/
```

| 位置 | 欄位 | 範例 |
|------|------|------|
| 2 | Package | SOT-23, SOD-123FL |
| 3 | Option | OPTION 1, BASE, HD |
| 4 | Form | REEL（捲狀）, STRIP（片狀）|
| 5 | Material | Cu, A42 |

範例：`腳架/SOT-23/OPTION 4/REEL/Cu`

### 線材格式（標準）
```
{Wire Type}/phi{Mil}/{Grade}/{Length}/
```

| 位置 | 欄位 | 範例 |
|------|------|------|
| 1 | Wire Type | GOLD WIRE, CU WIRE, AG WIRE |
| 2 | Wire Mil | phi1.0mil |
| 3 | Grade | Normal, GLF, AgLite |
| 4 | Length | 1000M |

範例：`GOLD WIRE/phi1.0mil/GLF/1000M/`

### 線材格式（跳線/CLIP）
```
跳線/{Package}/{Option}/{Grade}/
```

範例：`跳線/SMAF/C(C)/HD A/`

### 膠格式
```
{Glue Type}/{Model}/{Size}/{Weight}/
```

| Glue Type | 用途 |
|-----------|------|
| 銀膠 | EPOXY 製程 |
| 錫膏 | SOLDER 製程 |
| 成型膠 | Molding |

範例：`銀膠/84-1LMISR4/5cc/18g//`

---

## Com Item Desc 解析（依站別）

### 站別 15（焊接 DB）
```
焊接(DB)/{Package}/{Process}/{Material}/{Option}/.../for Chip size {Range}/{Loss}
```

範例：`焊接(DB)/SOT-23/Eutectic/Cu/OP5////0%`

### 站別 23（打線 WB）
```
焊接/{Package}/...//{Wire Type}/{WireSpec}/for Chip size {Range}/{Loss}
```

範例：`焊接/SOT-23////Cu WIRE/10WX1/for Chip size8~19mil/0.0%`

### 站別 28（成型）
```
成型/{Package}/{EMC Type}/.../
```

範例：`成型/SOT-23/Green EMC//////0.0%`

### 站別 60/63（電鍍）
```
電鍍/{Package}/.../(PJ)/{Loss}
```

範例：`電鍍/SOT-23//////(PJ)/0.0%`

### 站別 90（包裝）
```
包裝/{Package}/{Packing Type}/.../
```

範例：`包裝/SOT-23/R7//////0.00%`

---

## 欄位值對照表

### Wafer Function 對應 Pj Function

| Wafer Function | Pj Function |
|----------------|-------------|
| ZEN | ZENER |
| SWI | SWITCHING |
| SKY | SKY |
| TVS | TVS |
| MOS | MOSFET |
| TRA | TRANSISTOR |
| TEA | TVS/ESD |
| GPP | GENERAL |
| FRG | FAST |
| ERG | SUPER |
| UFG | ULTRA |

### Metal（金屬層）

| 代碼 | Top 金屬 | Back 金屬 | BOM 筆數 |
|------|---------|----------|---------|
| ALSN | AL (鋁) | SN (錫) | 17,484 |
| ALAU | AL (鋁) | AU (金) | 12,762 |
| AGAG | AG (銀) | AG (銀) | 4,135 |
| AUAU | AU (金) | AU (金) | 1,925 |
| ALAG | AL (鋁) | AG (銀) | 917 |

### Lef Material（腳架材質）

| 代碼 | 說明 | BOM 筆數 |
|------|------|---------|
| A42 | ALLOY42 合金 | 13,843 |
| Cu | 銅 | 12,420 |

---

## 解析器工具

位置: `shared/tools/parsers/desc_parser.py`

功能: 自動解析 Sub Com Item Desc / Com Item Desc 並提取結構化欄位
