# 製程 BOM 語意規則 — 詳細範例與統計

> 從 SKILL.md 分離的詳細內容。規則摘要見 SKILL.md，本檔含範例、統計數據、SQL 範例、修正歷史。

---

## R1 詳細：Op 15 / Op 23 物料因製程類型而異

**統計事實（Op 23）**：膠 35,746 > 線材 21,328 > 腳架 12,707。
Op 23 **不是**純線材站，P/CLIP 製程的錫膏和腳架佔比更高。

**資料異常**：30 個 BOM（全為 008A1 控制碼）所有物料壓平到 Op 10 單一站別，為資料特例。

---

## R2 詳細：多筆 com_qty > 0 範例

- AB 晶產品：2~4 筆晶片 com_qty > 0（例：BC846APN 有 WAF912087 + WAF912104）
- 2nd Source 並行：同 BOM 有 LEF000164 + LEF000019 兩筆腳架 com_qty > 0
- 26,164 個 BOM+Op+Type 組合有多筆 com_qty > 0（不含包裝材料）

**Sub Com Remarks 用途**: 變更歷史記錄（如「替代COM000138」表示此料取代了舊料）。**不是**用來判斷主料/備用料。

---

## R3 詳細：Alt Bom Designator 編碼對照表

| Alt Designator | 對應 Bop | 含義 |
|---------------|---------|------|
| `AU WIRE` | UAA10 等 | 金線（非 DW） |
| `AU WIRE_DW` | UAA10-DW 等 | 金線+一貫機 |
| `CU WIRE` | UAC10 等 | 銅線 |
| `CU WIRE_DW` | UAC10-DW 等 | 銅線+一貫機 |
| `AG WIRE_DW` | UAG10-DW 等 | 銀線+一貫機 |
| `EPOXY` | EAA10 等 | 銀膠製程 |
| `EPOXY_CUWR` | EAC10 等 | 銀膠+銅線 |
| `HD_A CLIP` | PHPAX 等 | HD 腳架 CLIP A |
| `A~G CLIP_DW` | PCPAX-DW 等 | CLIP+一貫機 |
| `CULFCU_DW` | 含 CU LF | 銅腳架+銅線+DW |
| `OP1LF` | - | 腳架 Option 1 變體 |

**統計**：79.6% 替代結構改變了 bop（不同製程路線），20.4% 同 bop（可能僅腳架選項不同）。
單一產品最多 **16 個製程變體**。

---

## R5 詳細：WAF BOM 中的實際模式與統計

```
Com 層（配方）        Sub 層（實體料）       說明
WAF000099_CP    →    WAF900099            WAF0→WAF9 轉換（常見）
WAF912256_CP    →    WAF912256            WAF9→WAF9 無轉換
WAF002552_CP    →    WAF002552            WAF0→WAF0 無轉換
```

**統計事實**：
- **Sub 層永遠沒有 _CP 後綴**（WAF0: 406個/5,795筆, WAF9: 1,660個/28,576筆, 全部無 _CP）
- **Com 層才有 _CP**（WAF0_CP: 813個, WAF9_CP: 1,063個, 也有無_CP的 WAF0/WAF9）
- WAF0_CP 不一定指向 WAF9 sub（部分指向 WAF0 sub）
- WAF91xxxx 系列存在（不僅 WAF90xxxx）

---

## R6 詳細：Com-level Fallback 與 Die Size 解析格式

**Com-level Fallback**（2026-02-26 驗證）：
- BOM Pattern B（11.7%）的物料資訊只在 Com Item Desc，Sub Com 層為空或其他物料
- 入庫時必須先嘗試 Sub 層解析，失敗則 fallback 到 Com Item Desc
- 影響：wafer 5,246 筆、wire 5,697 筆、leadframe 1,779 筆（共 12,863 筆 / 4,367 產品）
- `_parser_used` 以 `com_` 前綴標記來源（com_wafer, com_wire, com_leadframe）

**BOM Desc 是物料屬性的 Source of Truth**（2026-03-06 ECR-L57 驗證）：
- BOP 位置碼（Pos2=LF 材質, Pos3=Wire 類型）適合粗分組，但不夠精確（如 BOP 2nd=C 可能對應鍍銀或裸銅）
- 物料屬性判斷優先序：**BOM desc 解析 > BOP fallback**
- WIR desc 格式：`XX WIRE/phiXmil/...`（AU/AG/CU）或 `跳線/封裝/...`（CJ = CLIP 跳線）
- LEF desc 格式：`腳架/封裝/.../材質`（末尾 /Cu 或 /A42）
- desc 與 BOP 一致率 100%（全量 BOM 比對驗證，D-111）

**Die Size 解析格式**（2026-03-05 ECR-L55 驗證，22,203 筆全量）：
- material_desc 中 die size 有 3 種格式：
  - `/W/*Lmil/`（主流 22,180 筆）— 標準格式
  - `/W/Lmil/`（無星號 18 筆）— 少數遺漏星號
  - `/W/L/thk/`（無 mil 後綴 5 筆，含 typo 如 `40.*9mil`）
- **Die Diagonal 計算**：die_diagonal_mil = sqrt(W^2 + L^2)，**不可用** die_size_mil * sqrt(2)（假設正方形會出錯）

---

## R7 詳細：JOIN 完整性統計

- 18,875 total BOMs, 15,950 with chip (84.5%)
- **596 BOMs 有晶片但無線材**：572 為 **PCUAB/PCUAC（CLIP 製程）** — CLIP 不需要傳統線材，用腳架跳線替代
- **31 BOMs 有晶片無腳架**：幾乎全是 RD-/PE- 特殊品
- **2,925 BOMs 無晶片資料**：多為替代結構 BOM（chip 由主結構指定）或無 Sub Com 晶片解析
- **使用 INNER JOIN 時留意**：CLIP 製程 BOM 會被 chip-wire JOIN 排除

---

## R8 詳細：雙層查詢範例與 2nd Source 實例

**實例驗證**（3 個產品確認）：
- MMDT3946: LEF000175 在 Com 層，LEF000044 在 SubCom 層（同為 SOT-363/A42 腳架）
- MMSZ4691-V: WIR000108 在 Com 層，WIR000037 在 SubCom 層（同為 CU WIRE/1.2mil）
- BAV99W: LEF000173 + WIR000107 在 Com 層，LEF000040 + WIR000029/041 在 SubCom 層

**正確查詢方式（必須 UNION 兩層）**:

```sql
-- 查詢某產品的所有腳架（含 2nd Source）
SELECT com_item_no as item_no, com_item_desc as item_desc, '1st_layer' as layer
FROM raw_bom
WHERE bom_name = '{bom}' AND com_item_no LIKE 'LEF%'
UNION
SELECT sub_com_item_no, sub_com_item_desc, '2nd_layer'
FROM raw_bom
WHERE bom_name = '{bom}' AND sub_com_item_m_type = '腳架'
```

**識別 2nd Source 特徵（量產品）**:
- `Com Item No` 為實際料號格式（LEF, WIR 等前綴）
- `Sub Com Item No` 為空白
- `Com Qty` 通常 = 0.0

**例外（2026-02-22 驗證）**：
- **RD- 研發產品**：LEF/WIR 可在 Com 層以 com_qty > 0 standalone 出現（39 LEF + 29 WIR 筆）
- **WAF 在 Com 層** com_qty > 0 (20,476 筆) 是**正常配方結構**（WAF_CP → WAF sub），非 2nd Source
- 2nd Source 規則適用範圍：**量產品（非 RD-）的 LEF/WIR 類型**

---

## R11 詳細：金屬層封裝搭配修正歷史

**2026-02-22 修正 — 封裝搭配規則（原規則嚴重錯誤）**：
- ~~AGAG = DO-218 專用~~ → **錯誤**。AGAG 實際分布：SOD-123FL(753), SOD-123HE(188), SMAF(155), SMBF(67), TO-277(7), DO-218(1)
- ~~AUAU = TO-277 功率封裝~~ → **不完整**。AUAU 分布：SOD-123FL(420), SMAF(227), SMBF(86), SOD-123HE(26), TO-277(21)

**wafer_function 與金屬層的關係（2026-02-22 修正）**：
wafer_function 與金屬層之間**無絕對對應關係**。同一 function 可用多種金屬層：
- ZEN 同時出現在 AGAG(437)、ALAU(2,723)、ALSN(6,814)
- SKY 同時出現在 AGAG(304)、ALAU(580)、ALSN(1,210)
- TVS 同時出現在 AGAG(348)、AUAU(348)

以下為統計分布（僅供參考，**不是規則**）：

| 金屬層 | 常見搭配 | Die Size |
|-------|---------|----------|
| AGAG | ZEN, TVS, SKY, ERG | 26-170 mil |
| AUAU | TVS, GPP, FRG, ERG, UFG | 46-120 mil |
| ALAU | ZEN, SWI, TRA, SKY, MOS | 9-33.5 mil |
| ALSN | ZEN, SKY, MOS, TEA, SWI | 8-35 mil |

金屬層選擇的真實決定因素可能涉及產品設計規格（非單一欄位可判定）。
