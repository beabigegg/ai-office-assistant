---
name: bom-rules
description: |
  BOM（物料清單）結構規則與替代材料識別。適用於：
  解析組裝品料號編碼、識別替代材料、判斷 BOM 結構特徵。
  當任務涉及 BOM、物料、替代料、Ass Item No、組裝品料號時觸發。
triggers:
  - BOM, 物料清單, 物料, Bill of Materials
  - 替代料, 替代材料, alt_bom_designator, sub_com_remarks
  - Ass Item No, 組裝品料號, 料號編碼, 控制碼
  - 排除規則, RD-, PE-, EOL, GD料號, MBU3
  - 扁平結構, 備用料, 2nd Source
---

# BOM 業務規則

## 核心規則摘要

### R1：BOM 結構為扁平製程型（BOM-FLAT-PROCESS）信心度：very high
PANJIT BOM 不是傳統多層樹狀結構（無 FG→SA→RM 層級）。
結構為：`ass_item_no（產品）→ operation_seq_num（製程站）→ com/sub_com items（物料）`。
無 level/parent 欄位，無 FG-/SA-/RM- 前綴。
全量驗證：409,567 筆資料中無任何多層結構證據。

> 注意：references/hierarchy.md 中的多層樹狀規則為通用製造業知識，不適用於 PANJIT BOM。

### R2：替代材料透過 alt_bom_designator 管理（BOM-ALT-DESIGNATOR）信心度：high
PANJIT BOM 不使用「層級上提」處理替代材料。替代/變體透過兩種機制管理：
1. **alt_bom_designator**：245,664 筆 (60%)，79 種值（如 AU WIRE_DW, CU WIRE, EPOXY）。
   這是**製程變體**（不同材料選擇的 BOM 版本），直接對應 bop 編碼。
2. **sub_com_remarks 替代標記**：42,810 筆 (10.5%)，格式為「替代COMXXXXXX」。
   這是**物料替代**（同一製程內的替代用料）。

> 注意：references/substitute.md 中的 5 種 Excel 出現方式為通用知識。
> 實際 PANJIT BOM 以 alt_bom_designator + sub_com_remarks 為主。

### R3：供應商壓平（BOM-VENDOR-FLATTEN）信心度：低 → 不適用
全量驗證結果：每站最多 24 筆物料（多 Die 產品的 Op 23 打線站），屬正常範圍。
無供應商壓平的證據。此規則保留為通用知識參考，但 PANJIT BOM 不適用。

### R4：替代材料識別模式（SUBSTITUTE-PATTERNS）信心度：high
PANJIT BOM 中替代材料的實際識別方式：

| 方式 | 欄位 | 數量 | 說明 |
|------|------|------|------|
| 製程變體 | alt_bom_designator | 245,664 (60%) | 不同製程/材料的 BOM 版本 |
| 物料替代 | sub_com_remarks | 42,810 (10.5%) | 「替代COMXXXXXX」格式 |
| 備用料 | com_qty = 0 | 見 process-bom-semantics R2 | com_qty=0 的物料為備用料 |

原則：不自動決定替代關係，標記後請使用者確認。

### R5：組裝品料號編碼（ASS-ITEM-NO-CODING）信心度：very high
Ass Item No 格式為 `{產品型號}_{包裝}{版本}_{5碼內部控制碼}`。
全量驗證：8,486/8,488 (100%) 符合格式。

5碼控制碼：
- 第1碼 = 有害物質：`0`(無鹵 99.94%), `1`(含鹵 0.06%), `V`(無鉛玻璃，本資料集無實例)
- 第2碼 = 等級：`0`(Standard 99.14%), `Z`(AU+ 0.86%)
- 第3碼 = 組裝廠：`0`(廠內 87.4%), `7`(MBU1 12.2%), `8`(ATEC外包 0.4%), `1`(LE 0.01%)
  - **ECR/ECN 評估僅納入 `0` 和 `7`**（皆為岡山廠自製，`7` 從 `0` 拆分）；其餘排除
- 第4-5碼 = 特殊需求：`01`(Standard), `A1`(AU/AU+ Standard), `A2~A9`(特規續編), `Bx~Yx`(CSR客戶特規：C1=Continental, P1=Aptiv, V1=Valeo), `02/AX/Z1~Z7`(保留碼)

產品前綴：`RD-`(研發 8%), `PE-`(特殊產品/驗證批 2.5%), 無前綴(正常 89.5%)
包裝版本：`R1`(75.7%), `R2`(22.6%), `S1`(1.4%), `S2`(0.2%)

### R6：ECR/ECN 通用排除規則（UNIVERSAL-EXCLUSION）信心度：very high
**以下料號不應納入 ECR/ECN 變更範疇。** 排除在查詢層處理，**BOM 入庫不排除**（D-155）。

**A. 前綴排除（全資料層級）：**

| 層級 | 前綴 | 說明 |
|------|------|------|
| 成品 (Ass Item) | `RD-` / `RD_` | 研發中成品料號（破折號或底線皆為研發前綴） |
| 成品 (Ass Item) | `PE-` | 特殊產品/驗證批 |
| 晶圓 (Wafer) | `WAFRD` | 研發中晶圓 |
| 腳架 (Lead Frame) | `LEFRD` | 研發中腳架 |
| 跳線/線材 (Wire) | `WIRRDD` | 研發中跳線/線材 |
| 膠材 (Compound) | `COMRD` | 研發中膠材 |

**B. 狀態排除（跨領域通用，適用所有變更案）：**

| 狀態 | 說明 |
|------|------|
| EOL | 已停產 |
| PM EOL | 計畫停產 |
| GD料號 | 淘汰料 |
| MBU3料號 | 非岡山廠管轄 |
| MBU2/LE/ATEC外包 | 控制碼第3碼非 0/7 |
| 十年無出貨紀錄 | 實質停產 |
| 外包外購 | 非自廠變更範圍 |
| 不良品 | 品質問題已另案處理 |

過濾實作：排除在 ECR/ECN **查詢層** 以 WHERE 條件處理，BOM 入庫保留全量資料（D-155 supersedes D-054）。
來源：使用者確認 2026-02-23 (D-054, D-055)。另見 ecr_ecn_rules.md ECR-R24。

### R7：bom_material_detail 雙層結構（BOM-DUAL-LAYER）信心度：very high ⚠️ 高頻犯錯點（已犯 4 次）

`bom_material_detail` 表同時包含兩種來源，缺一不可：

| 層別 | 資料來源 | _parser_used | 說明 |
|------|----------|--------------|------|
| **Type A**（sub_com 層） | `sub_com_item_no LIKE 'WAF/WIR/LEF/COM%'` | wafer/wire/leadframe/glue | 主流：sub_com_item_no 存放原物料 |
| **Type B**（com_item_no 層） | `_parser_used IN ('com_wafer','com_wire','com_leadframe','com_glue')` | com_* | 少量：com_item_no 直接是原物料（無 sub_com） |

**數量（2026-04-14 重建後）：**

| 物料類型 | Type A | Type B | 去重後 |
|----------|--------|--------|--------|
| WAF | 38,529 | 5,823 | 24,057 |
| WIR | 23,204 | 5,802 | 16,036 |
| LEF | 30,677 | 1,836 | 18,882 |
| COM | 75,979 | 76 | 49,090 |
| **合計** | | | **108,065** |

**重要**：只查 Type A 會遺漏約 ~4,500 個成品料號的 WIR/LEF 資訊。

### R8：晶粒對角線計算（DIE-DIAGONAL-CALC）信心度：very high

**正確公式**：從 WAF desc 解析 W×L 兩維度，`die_diagonal_mil = sqrt(W² + L²)`

WAF desc 格式：`{功能}/{晶圓尺寸}/{型號}/{W}/*{L}mil/{厚度}um/{背面金屬}/`
範例：`MOS/8"/SKWQ042/43.3/*31.1mil/178um/ALAG/` → W=43.3, L=31.1 → 對角=53.31 mil

**錯誤做法**（已廢棄）：`die_size_raw × sqrt(2)` 假設正方形晶粒，對長方形最多誤差 9 mil。

- `die_size_mil`：desc 中的 W（較大維度，或 die_size_raw 作 fallback）
- `die_diagonal_mil`：sqrt(W² + L²)；若僅有一維（正方形）則等同 W × sqrt(2)
- 長方形晶粒（184 種）：大多為 MOS MOSFET，誤差 2-9 mil，影響 QV 代表料選取

Fallback 順序（當 desc 無 W×L pattern 時）：
1. `die_size_raw`（std_bom 欄位）作正方形 fallback
2. 若 die_size_raw 也無 → 跨 BOP 借同料號其他 BOP 的 die info

工具：`projects/BOM資料結構分析/workspace/scripts/build_bom_material_detail.py`（`parse_die_diagonal()` 函式）

## 詳細規則

完整規則和案例說明見：
- `references/hierarchy.md` — BOM 階層結構通用知識（不適用於 PANJIT 扁平 BOM）
- `references/substitute.md` — 替代材料識別的 5 種通用方式
- `references/ass_item_no_coding.md` — 組裝品料號 5 碼控制碼解析（官方文件 + 全量驗證）

## 來源與信心度

| 規則 | 來源 | 信心度 | 驗證次數 | 備註 |
|------|------|--------|---------|------|
| R1 扁平結構 | 全量反例驗證 | very high | 1 | 409,567 筆無任何多層證據 |
| R2 Alt Designator | 全量反例驗證 | high | 1 | 60% 資料使用 alt_bom_designator |
| R3 供應商壓平 | 全量反例驗證 | -- | 1 | 不適用，無證據 |
| R4 替代材料識別 | 全量驗證 | high | 1 | remarks 替代 + alt designator |
| R5 料號編碼 | 官方文件 + 全量驗證 | very high | 2 | 100% 格式符合，Digit3 新增 8=ATEC |
| R6 通用排除 | 使用者確認 (D-054, D-055) | very high | 2 | 前綴(RD-/PE-/WAFRD/LEFRD/WIRRDD/COMRD) + 狀態(EOL/GD/MBU3等) |
| R7 雙層結構 | 全量驗證 + 使用者確認 | very high | 1 | Type A sub_com + Type B com_item_no 缺一不可 |
| R8 晶粒對角線 | 全量驗證 + 使用者確認 | very high | 1 | sqrt(W²+L²)，禁止用 W×sqrt(2) |

## 升級記錄

| 日期 | 內容 | 來源 |
|------|------|------|
| 2026-02-05 | R5: 組裝品料號編碼規則 | shared/kb/dynamic/column_semantics.md (Ass Item No) |
| 2026-02-22 | R1~R4: 全量反例驗證，R1~R3 標記不適用/改寫，R4 改寫為實際模式 | bom.db 全量驗證 |
| 2026-02-22 | R5: 全量驗證通過，新增 Digit3=8(ATEC)、產品前綴(RD-/PE-)、包裝版本分布 | 使用者確認 + bom.db |
| 2026-02-23 | R6: 通用排除規則 v1（前綴 RD-/PE- + 原物料 + 狀態排除 EOL/GD/MBU3 等） | 使用者確認 D-054, D-055 |
| 2026-04-14 | R7: 雙層結構（Type A sub_com + Type B com_wafer/wire/lef/glue），108,065 筆 | 全量驗證，WIR/LEF Type B 補入 |
| 2026-04-14 | R8: 晶粒對角線改用 sqrt(W²+L²)，廢棄 W×sqrt(2) 正方形假設 | 使用者確認，184 長方形晶粒最大誤差 9 mil |
