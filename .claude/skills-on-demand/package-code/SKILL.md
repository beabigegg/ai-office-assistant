---
name: package-code
description: |
  PANJIT Package Code (Full_PKG_CODE) 編碼準則。適用於：
  解碼 Full_PKG_CODE 六段結構（Package-LF-D/A-Wires-Compound-Vendor）、
  判別封裝系列編碼模式（SOT/SOD, DFN, SMA/TO/DO）、
  Vendor Code 新舊制對照（2023年 P->5/6/7）、
  PLP 封裝八段擴展結構、Wire Code 與 ECR 變更關聯。
  當任務涉及 Full_PKG_CODE、Package Code、封裝代碼、
  PKG_CODE、Vendor Code、LF Code、D/A Code、Wires Code、
  Compound Code、封裝編碼解碼時觸發。
triggers:
  - Full_PKG_CODE, Package Code, PKG_CODE, 封裝代碼, 封裝編碼
  - Vendor Code, 供應商代碼, MBU1, MBU2, MBU3, 岡山廠
  - LF Code, 腳架代碼, D/A Code, 焊接代碼
  - Wires Code, 線材代碼, Compound Code, 成型膠代碼
  - SOT, SOD, DFN, SMA, SMB, TO-, DO-, SMAF, SMBF
  - BOP推導, pj_package, 封裝映射
  - SOTU20, SOTD20, SODU20, SODU00, DO0218, TO0277
---

# PANJIT Package Code 編碼準則

> 來源: F-RD0215 rev20 (2025-10-28 PQM)
> 原始檔案: PANJIT Package code編碼準則_20230704(PQM) rev20.xlsx
> 前版: rev15 (2024-09-03)

## R1: Full_PKG_CODE 主結構 (FULL-PKG-CODE-STRUCTURE)
信心度: 高 | 來源: 官方文件 F-RD0215 rev20 | 驗證: 官方

Full_PKG_CODE 由 6 段組成，以 `-` 分隔：

```
XXXXXX - X  - XX - XX - XXXX - X
  |       |    |    |     |     |
  |       |    |    |     |     +-- Vendor Code (1 char) -- 封裝供應商
  |       |    |    |     +-------- Compound Code (4 chars) -- 成型膠
  |       |    |    +-------------- Wires Code (2 chars) -- 線材
  |       |    +------------------- D/A Code (2 chars) -- Die Attach 焊接方式
  |       +------------------------ LF Code (1 char) -- Lead Frame 腳架材質
  +-------------------------------- Package Code (6 chars) -- 封裝代碼
```

**範例解碼**: `SOTU20-C-EP-CU-1702-P`
- Package: SOTU20 = SOT-23/SOT-323, Die up, Gull Wing, LF 0.10-0.25mm
- LF: C = Cu 腳架
- D/A: EP = Epoxy 銀膠
- Wires: CU = Cu wires 銅線
- Compound: 1702 = CEL-1702HF9
- Vendor: P = PANJIT（2022年以前）

## R2: Package Code 三種模式 (PKG-CODE-MODES)
信心度: 高 | 來源: 官方文件 | 驗證: 官方

Package Code (6 chars) 依封裝系列分為三種編碼模式：

### 模式 A: SOT/SOD 系列

```
XXX  X  X  X
 |   |  |  +-- L/F厚度 (0=0.10-0.25, 1=0.26-0.3, 2=0.31-0.6)
 |   |  +----- 腳型 (0=Flat Lead, 1=Flat Lead+Heat Sink, 2=Gull Wing)
 |   +-------- Die位置 (U=Die up, D=Die down)
 +------------ 封裝 (SOT, SOD)
```

常用代碼：

| Code | 封裝 | 說明 |
|------|------|------|
| SOTU20 | SOT-23/SOT-323/SOT-23 5L/6L | Die up, Gull Wing |
| SOTD20 | SOT-363/353/SOT-23 6L-1 | Die down, Gull Wing |
| SOTU00 | SOT-523/543/553/563/SC-89 | Die up, Flat Lead |
| SODU20 | SOD-123 | Die up, Gull Wing |
| SODU00 | SOD-123FL/SOD-323/SOD-523/SOD-923 | Die up, Flat Lead |
| SODU10 | SOD-123HE/SOD-323HE | Die up, Flat Lead+Heat Sink |

### 模式 B: DFN 系列

兩種子格式：

**DFN + 厚度碼 (3 chars)**:
```
DFN  XXX  -- 本体厚度碼
```
| Code | 厚度 |
|------|------|
| DFN030 | <0.3mm |
| DFN050 | 0.3~0.5mm |
| DFN075 | 0.65~0.85mm |

**DF + 獨立碼 (4 chars)**:
| Code | 封裝 |
|------|------|
| DF3333 | DFN3333-8L |
| DF5060 | DFN5060-8L/DFN5060X-8L/DFN5060B-8L | qualification in progress |
| DF8080 | DFN8x8-4L | qualification in progress |
| PDFN88 | PDFN8x8-8L | **Rev.20 新增**, qualification in progress |
| DFN33S | DFN3333S-8L/DFN3333SW-8L(sawed+WF) | WX Sawn type, Rev.19 增 SW |
| DFN56S | DFN5060S-8L/DFN5060SW-8L(sawed+WF) | WX Sawn type, Rev.19 增 SW |

### 模式 C: SMA/SMB/SMC/SME 系列

```
XXX  X  X  X
 |   |  |  +-- 流水碼 Serial No (0, 1...)
 |   |  +----- 腳架型 LF structure (0=二片式, 1=三片式)
 |   +-------- 本体厚度 (0=正常, F=薄型)
 +------------ 封裝 (SMA, SMB, SMC, SME)
```

### 模式 D: TO/DO/其他 -- 獨立封裝碼

使用 6 字元獨立編碼，常用代碼見 `references/full_code_table.md`。

核心對照（最常用）：

| Code | 封裝 |
|------|------|
| TO0252 | TO-251AA/TO-252AA |
| TO0220 | TO-220AB/TO-220AC |
| TO0247 | TO-247AD-2LD/3LD |
| TO0263 | TO-263 |
| TO0277 | TO-277/TO-277B/TO-277C |
| TOLL00 | TOLL/TOLLK 9.8x11.7 (TO-Leadless) |
| sTOLL0 | sTOLL 7x8 (small TO-Leadless, Rev.20 新增) |
| ITO220 | ITO-220AB/ITO-220AC |
| DO0218 | DO-218AC/DO-218AB |
| SOT223 | SOT-223 |
| SOP008 | SOP-8 |
| M60000 | M6 (Rev.18 新增) |

## R3: LF Code 腳架材質 (LF-CODE)
信心度: 高 | 來源: 官方文件 + LEF 物理資訊交叉驗證 | 驗證: 官方 + D-092/D-093

| Code | 材質 | 備註 |
|------|------|------|
| C | Cu (Bare Cu) | 裸銅 — **需 Pad Coating 確認** |
| A | Alloy (A42) | 合金腳架 — 唯一不需 Pad Coating 驗證的 LF |
| P | Cu+Ni-Pd-Au | 鍍鎳鈀金 |
| B | Bare Cu | 裸銅（BOP 'N' 映射） |
| G | Cu plating Ag | 鍍銀銅 — **需 Pad Coating 確認** |
| U | A42 plating Cu | A42鍍銅 (Rev.20 新增) |
| D | AgNi plating Au | 銀鎳鍍金 (Rev.20 新增) |
| H | High Density (Cu) | 高密度腳架 — **需 Pad Coating 確認** |

**LF Code 判定規則（D-092, D-093 修正）**:

> **警告**: BOP 第2碼**不能**直接映射為 LF Code。BOP 'C'/'H'/'N' 都是銅系材質，
> 無法區分 C (裸銅) vs G (鍍銀)。必須交叉比對 LEF Pad Coating。

判定路徑: `part_number → BOM(LEF_no) → lef_physical_info(Pad Coating) → LF Code`

| Pad Coating | LF Code | 說明 |
|-------------|---------|------|
| 鍍銀 | **G** | Cu plating Ag |
| 裸銅 | **C** | Bare Cu |
| 整條鍍鎳 | **C** | Ni plating, base Cu |
| - (無/未知) | **C** | 保守預設 |

- **A (Alloy42)**: 唯一不需 Pad Coating 的 LF Code，BOP 'A' → LF 'A' 直接映射
- **C/H/N**: 全部需要 Pad Coating 查表。查不到時保留原值並 WARNING
- **資料來源**: `lef_physical_info` DB 表（134 筆，由 LEF物理資訊.xlsx 入庫）
- **統計**: BOP 2nd='C' 料號中 73% 為 G (鍍銀)，僅 27% 為 C (裸銅)

**與 process-bom-semantics R4 的關聯**:
- BOP 第2碼 A → LF Code A（直接映射，Alloy42 唯一確定值）
- BOP 第2碼 C → LF Code C 或 G（**需 Pad Coating 驗證**，不可直接映射）
- BOP 第2碼 H → LF Code C 或 G（**需 Pad Coating 驗證**，不可直接映射）
- BOP 第2碼 N → LF Code C（大部分為整條鍍鎳→C，仍應驗證）

## R4: D/A Code 焊接方式 (DA-CODE)
信心度: 高 | 來源: 官方文件 | 驗證: 官方

| Code | 製程 | 說明 |
|------|------|------|
| EP | Epoxy | 銀膠焊接 |
| EU | Eutectic | 共晶焊 |
| SS | Soft Solder | 軟焊 |
| SP | Solder paste | 焊膏 |
| SF | Solder flake | 焊片 |

**與 process-bom-semantics R4 的關聯**:
- D/A Code EP = BOP 第1碼 E (EPOXY)
- D/A Code EU = BOP 第1碼 U (EUTECTIC)

## R5: Wires Code 線材 (WIRES-CODE)
信心度: 高 | 來源: 官方文件 | 驗證: 官方

| Code | 線材 | 與 ECR 的關聯 |
|------|------|-------------|
| CU | Cu wires 銅線 | ECR 金轉銅目標線材 |
| AU | Au wires 金線 | ECR 被替換線材 |
| AG | Ag wires 銀線 | |
| PC | PdAuCu wire 鈀金銅線 | BSOB 變更用線材 |
| CR | Cu/Rib | |
| CA | Cu/Al | |
| AL | Al wires | |
| CJ | Clip (jump) | Clip bonding，非 wire bonding |
| LW | LeadWire | |
| AR | Au/Rib | |
| AA | Au/Al | |
| AC | Au/Clip | |

**ECR 變更關聯**:
- 金線轉銅線: AU -> CU (ECR-R1~R3)
- BSOB 轉鈀金銅: AU -> PC (ECR-R9)
- CJ (Clip) 封裝不涉及金轉銅（無 wire bonding）

**Wire Code 交叉驗證（D-092 修正）**:
- BOP 推導的 Wire Code 應以 BOM `wire_type` 交叉驗證
- BOM wire_type → Wire Code 映射: CLIP→CJ, CU WIRE→CU, GOLD WIRE→AU, AG WIRE→AG
- BOM 中無 PdAuCu wire_type（PC 碼目前僅存在於定義，實際 BOM 無此線材）

**與 process-bom-semantics R4 的關聯**:
- Wires Code CU = BOP 第3碼 C (COPPER)
- Wires Code AU = BOP 第3碼 A (GOLD)
- Wires Code AG = BOP 第3碼 G (SILVER)

## R6: Compound Code 成型膠 (COMPOUND-CODE)
信心度: 高 | 來源: 官方文件 + BOM 交叉驗證 | 驗證: 官方 + BOM

完整 42 組代碼（詳見 `references/full_code_table.md`）。
BOM 中實際使用的 7 組（覆蓋 95.5% 零件）：

| Code | 成型膠 | BOM 零件數 |
|------|--------|-----------|
| 500C | 500C/500C-S | 12,741 |
| G600 | G600(FL/FB) | 3,733 |
| G660 | G660/G660BP-A | 580 |
| 100H | ELER-8-100HFS | 161 |
| G590 | G590 | 144 |
| 9240 | CEL-9240HF | 67 |
| G630 | EME-G630AY-H | 32 |

**BOM 比對要點**:
- BOM 中成型膠存在 `sub_com_item_desc` 欄位，描述含「成型」關鍵字
- BOM 使用內部料號（如 COM000XXX），需從描述模糊比對產品名稱
- 罐頭名稱（如 SOT23_MD0001）為模板，正式料展開到 SUB COM 層
- ELER-8-130PJ9 (470件) 因 delamination 已停用，不在 33 碼表中
- 660P 與 G660 重疊（同映射 G660BP-A），660P 為舊碼

## R7: Vendor Code 供應商代碼 (VENDOR-CODE)
信心度: 高 | 來源: 官方文件 | 驗證: 官方 + ECR-R17 交叉驗證

### 2023 年制度變更

**舊制** (2022年以前):
- P = PANJIT（不分廠區）

**新制** (2023年起):
- **5** = PANJIT_MBU3
- **6** = PANJIT_MBU2
- **7** = PANJIT_MBU1 = **岡山廠** (與 ECR-R17 交叉驗證)

不追溯已建立的 Package Code（舊料號仍可能用 P）。

### 完整供應商列表

| Code | 供應商 | 類別 |
|------|--------|------|
| 5 | PANJIT_MBU3 | 自有 |
| 6 | PANJIT_MBU2 | 自有 |
| 7 | PANJIT_MBU1 (岡山廠) | 自有 |
| P | PANJIT (舊制) | 自有 |
| E | GEM 捷敏電子 | 外包 |
| F | FH 風華 | 外包 |
| T | TSHT 天水華天 | 外包 |
| U | Comchip 典琦 / 信展通 | 外包 (注意: U 碼重用，信展通 Rev.16, ERP 106534) |
| B | 力邁 | 外包 |
| L | ATEC | 外包 |
| K | PPL 寶浦萊 | 外包 |
| S | Carsem 嘉盛 | 外包 |
| 8 | 秀武 | 外包 |
| M | 美林 | 外包 |
| X | ATX 日月新半導體 | 外包 |
| V | 龍晶微(龍平微) | 外包 |
| A | 安美 | 外包 (Rev.18 升格，ERP 105978) |
| C | PANSTAR-合肥矽邁SMAT | PLP 專用 (Rev.18 升格) |
| J | 晶導微 | 外包 (Rev.17, ERP 104161) |
| H | PANSTAR-華宇HISEMI | 外包 (Rev.18) |
| D | PANSTAR-長電JCET | 外包 (Rev.18) |
| Y | YJ 揚杰 | 外包 (Rev.18, ERP 104315) |
| N | PANSTAR-南岩Nanotesch | 外包 (Rev.20) |

詳細供應商資訊（含 ERP 交易代碼）見 `references/vendor_codes.md`。

## R8: NEW vs OLD Package Code 對照 (CODE-MAPPING)
信心度: 高 | 來源: 官方文件 Sheet 6 | 驗證: 官方

| NEW Code | OLD Code | 封裝 |
|----------|----------|------|
| SOTU20 | SOT230 | SOT-23/SOT-323 |
| SOTD20 | SOT231 | SOT-363/353 |
| SOTU00 | SOT232 | SOT-523/543/553/563/SC-89 |
| SODU20 | SOD23W | SOD-123 |
| SODU00 | SOD23F | SOD-123FL |
| SODU10 | SOD231 | SOD-123HE/SOD-323HE |
| SMAF00 | -- | SMAF (新封裝) |
| SMBF00 | -- | SMBF (新封裝) |
| DFN030 | DFN030 | DFN0603 |
| DFN050 | DFN050 | DFN 2L/3L/DFN2510/DFN5515 |
| TO0277 | TO-277 | TO-277(B)/TO-277C |
| DO0218 | DO-218 | DO-218AC/DO-218AB |

## R9: 與 ECR/ECN 規則的交叉關聯 (ECR-CROSS-REF)
信心度: 高 | 來源: 交叉驗證

此 Skill 與 ECR/ECN 規則有以下交叉點：

1. **Vendor Code 7 = MBU1 = 岡山廠** -- 驗證 ECR-R17（變更僅限岡山廠）
2. **Wires Code AU->CU** -- 對應 ECR 金線轉銅線變更
3. **Wires Code AU->PC** -- 對應 ECR BSOB 轉鈀金銅線（ECR-R9）
4. **LF Code** -- 對應 process-bom-semantics R4 BOP 第2碼
5. **D/A Code** -- 對應 process-bom-semantics R4 BOP 第1碼
6. **CJ (Clip bonding)** -- 不涉及金轉銅（非 wire bonding 封裝）

ECR-R13（原 low confidence 的 Full_PKG_CODE 結構推測）現已由本 Skill 的 R1 完全取代。

## R10: BOP → PKG CODE 推導規則 (BOP-DERIVATION)
信心度: 高 | 來源: 使用者確認 (D-045) + 全量審計驗證 | 驗證: 2026-02-22

BOP（Bill of Process）編碼可推導 Full_PKG_CODE 的中間 4 段（LF, D/A, Wire, Compound）。

### BOP 結構（5 字元 + 可選後綴）

```
X  X  X  XX  [-DW]
|  |  |  |      |
|  |  |  |      +-- 可選: -DW = Dual Wire / 一貫機
|  |  |  +--------- Pos 4-5: Wire Bond 線徑 (08=0.8mil, 10=1.0mil, 12=1.2mil, 15=1.5mil)
|  |  +------------ Pos 3: Wire 類型 (A=Au, C=Cu, G=Ag) / Clip 特殊碼 (P/H/U/N)
|  +--------------- Pos 2: LF 材質 (C=Cu, A=A42, H=High Density)
+------------------ Pos 1: D/A 製程 (U=Eutectic, E=Epoxy, P=Solder Paste/Clip)
```

### Pos 1 → D/A Code 映射

| BOP Pos 1 | D/A Code | 說明 |
|-----------|----------|------|
| U | EU | Eutectic 共晶焊 |
| E | EP | Epoxy 銀膠 |
| P | SP | Solder Paste / Clip 製程 |

### Pos 3 細分（P 前綴 BOP 特有）

當 Pos 1 = P 時，Pos 3 有特殊含義：

| Pos 3 | Wire Code | 說明 |
|-------|-----------|------|
| C/A/G + 數字Pos4-5 | CU/AU/AG | 標準焊線（含線徑） |
| P | **CJ** | **Clip (jump)** — CLIP 的 SP 製程變體 |
| H | CJ | Clip (jump) |
| U | CJ | Clip (jump) |
| N | LW | LeadWire（DO-218 鍍鎳跳線） |

> **注意 (D-092, ECR-L39)**: BOP P-prefix 第3碼 'P' **不是** PdAuCu (PC)。
> BOM 全量比對 1,426 筆，100% 為 CLIP，0 筆 PdAuCu。
> BOM 中完全沒有 PdAuCu wire_type 記錄。

### pj_package → Package Code 映射（已審計確認 2026-02-22）

| pj_package | Package Code | 備註 |
|------------|-------------|------|
| SOT-23, SOT-323, SOT23-6L, SOT23-5L, SOT-23 6L-1 | SOTU20 | Die up |
| SOT-363, SOT-353 | SOTD20 | Die down |
| SOT-523, SOT-543, SOT-553, SOT-563 | SOTU00 | 小型 SOT |
| SOT-223 | SOT223 | 獨立碼 |
| SOT-89, SC-89 | SOT-89 | |
| SOD-123 | SODU20 | |
| SOD-123FL | SODU00 | Flat Lead |
| SOD-123HE, SOD-323HE | SODU10 | Heat Extension |
| SOD-323, SOD-523, SOD-923 | SODU00 | |
| SMAF, SMAF-C, SMAF-1 | SMAF00 | 含變體 |
| SMBF | SMBF00 | |
| TO-277, TO-277B | TO0277 | 含變體 |
| DO-218AB | DO0218 | |
| TDI | TDI000 | |

### 特殊 Compound Code

| Code | 膠料 | 狀態 |
|------|------|------|
| 130P | ELER-8-130PJ9 | **已停用**（delamination） |
| EL2K | ELL-2K-2 | **RoHS 特殊**，僅 3 料號，早期配方 |

### LF Code 特殊值與交叉驗證

| 值 | 處理 | 備註 |
|----|------|------|
| N | → B (Bare Cu) | DO-218 鍍鎳，底材為銅（D-042）— 仍應 Pad Coating 驗證 |

**交叉驗證原則（D-092/D-093 升級）**:
- 所有 BOP 推導的 LF/Wire Code **必須**以 BOM 實際資料交叉驗證
- LF Code: `part→BOM(LEF_no)→lef_physical_info(Pad Coating)→COATING_TO_LF`
- Wire Code: `part→BOM(wire_type)→BOM_WIRE_TO_CODE`
- 推導腳本: `derive_full_pkg_code.py` v3, `rebuild_lf_families.py` v2
- 查不到時**不猜測**，保留原值並 WARNING，等待使用者確認

## 詳細規則

- `references/full_code_table.md` -- 完整代碼對照表（所有 Package Code, Compound Code）
- `references/plp_structure.md` -- PLP 封裝八段擴展結構
- `references/process_matrix.md` -- 封裝 x 製程能力矩陣
- `references/vendor_codes.md` -- 供應商完整列表（含 ERP 交易代碼、更新歷史）
- `references/revision_history.md` -- F-RD0215 版本變更摘要 (Rev.02~20)

## 來源與信心度

| 規則 | 來源 | 信心度 | 驗證 |
|------|------|--------|------|
| R1 Full_PKG_CODE 主結構 | 官方文件 F-RD0215 rev20 | 高 | 官方 |
| R2 Package Code 三種模式 | 官方文件 Sheet 0+1 | 高 | 官方 |
| R3 LF Code | 官方文件 | 高 | 官方 + BOP交叉 |
| R4 D/A Code | 官方文件 | 高 | 官方 + BOP交叉 |
| R5 Wires Code | 官方文件 | 高 | 官方 + ECR交叉 |
| R6 Compound Code | 官方文件 | 高 | 官方 |
| R7 Vendor Code | 官方文件 | 高 | 官方 + ECR-R17交叉 |
| R8 NEW/OLD Code 對照 | 官方文件 Sheet 6 | 高 | 官方 |
| R9 ECR 交叉關聯 | 交叉驗證 | 高 | 多重來源 |
| R10 BOP→PKG CODE 推導 | 使用者確認 D-041~D-045 | 高 | 全量審計 + D-092修正 |

## 升級記錄

| 日期 | 內容 | 來源 |
|------|------|------|
| 2026-02-06 | 初始建立 -- 從官方文件 F-RD0215 rev15 吸收 | Explorer 偵察報告 + 原始檔案 |
| 2026-02-22 | 新增 R10 BOP→PKG CODE 推導規則 + pj_package 映射表 + 特殊碼 | 全量審計 + 使用者確認 D-041~D-045 |
| 2026-03-02 | **重大修正**: R3 LF Code 加入 Pad Coating 交叉驗證規則; R5 Wire Code 加入 BOM 交叉驗證; R10 BOP P→CJ 修正 (非 PC); 升級來源 ECR-L38/L39/L42, D-092/D-093 | 全量 BOM 比對 + 使用者確認 |
| 2026-03-04 | **rev15→rev20 同步**: +3 封裝碼(PDFN88/sTOLL0/M60000), +2 LF Code(U/D), +9 Compound, +7 Vendor, TO-263等升格合格, DFN厚度碼標準化, 安美/SMAT升格, MBU3 PKG Code List | 官方文件 F-RD0215 rev20 |
