# Package Code 完整代碼對照表

> 來源: F-RD0215 rev20, Sheet 0 "new編碼(含無錫,外包) v1"

## Package Code -- SOT/SOD 系列（模式 A）

### 位置碼定義

| 位置 | 碼 | 含義 |
|------|---|------|
| 封裝 (3 char) | SOT | Small Outline Transistor |
| | SOD | Small Outline Diode |
| Die 位置 (1 char) | U | Die up |
| | D | Die down |
| 腳型 (1 char) | 0 | Flat Lead |
| | 1 | Flat Lead + Heat Sink |
| | 2 | Gull Wing |
| L/F 厚度 (1 char) | 0 | 0.10~0.25mm |
| | 1 | 0.26~0.3mm |
| | 2 | 0.31~0.6mm |

### 完整對照

| Code | 封裝 | Die位置 | 腳型 | L/F厚度 |
|------|------|---------|------|---------|
| SOTU20 | SOT-23/SOT-323/SOT-23 5L/6L | Up | Gull Wing | 0.10-0.25 |
| SOTD20 | SOT-363/353/SOT-23 6L-1 | Down | Gull Wing | 0.10-0.25 |
| SOTU00 | SOT-523/543/553/563/SC-89 | Up | Flat Lead | 0.10-0.25 |
| SODU20 | SOD-123 | Up | Gull Wing | 0.10-0.25 |
| SODU00 | SOD-123FL/SOD-323/SOD-523/SOD-923 | Up | Flat Lead | 0.10-0.25 |
| SODU10 | SOD-123HE/SOD-323HE | Up | FL+Heat Sink | 0.10-0.25 |

## Package Code -- DFN 系列（模式 B）

### DFN + 厚度碼

| Code | 本体厚度 | 封裝 |
|------|---------|------|
| DFN030 | <0.3mm | DFN0603 等 |
| DFN050 | 0.3~0.5mm | DFN 2L/3L/DFN2510/DFN5515C-14L/18L 等 |
| DFN075 | 0.65~0.85mm | DFN2020B-6L/DFN2020BW-6L(qualification) 等 |

### DF + 獨立碼

| Code | 封裝 | 備註 |
|------|------|------|
| DF3333 | DFN3333-8L | |
| DF5060 | DFN5060-8L/DFN5060X-8L/DFN5060B-8L/DFN5060XC-8L | qualification in progress |
| DF8080 | DFN8x8-4L | qualification in progress |
| DFN33S | DFN3333S-8L/DFN3333SW-8L(sawed+WF) | WX Sawn type (Rev.15, Rev.19 增SW) |
| DFN56S | DFN5060S-8L/DFN5060SW-8L(sawed+WF) | WX Sawn type (Rev.15, Rev.19 增SW) |
| PDFN88 | PDFN8x8-8L | **Rev.20 新增**, qualification in progress |

## Package Code -- SMA/SMB/SMC/SME 系列（模式 C）

### 位置碼定義

| 位置 | 碼 | 含義 |
|------|---|------|
| 封裝 (3 char) | SMA, SMB, SMC, SME | 各尺寸系列 |
| 本体厚度 (1 char) | 0 | 正常 (Normal) |
| | F | 薄型 (Thinner) |
| 腳架型 (1 char) | 0 | 二片式 (Two-piece) |
| | 1 | 三片式 (Three-piece) |
| 流水碼 (1 char) | 0, 1... | 序號 |

### 常用代碼

| Code | 封裝 | 厚度 | 腳架型 |
|------|------|------|--------|
| SMAF00 | SMAF / SMAF-C / SMAF-1 | 薄型 | 二片式 |
| SMBF00 | SMBF | 薄型 | 二片式 |
| SMA000 | SMA | 正常 | 二片式 |
| SMB000 | SMB | 正常 | 二片式 |
| SMC000 | SMC | 正常 | 二片式 |

## Package Code -- TO/DO/其他（模式 D：獨立封裝碼）

| Code | 封裝 | 備註 |
|------|------|------|
| TO0252 | TO-251AA/TO-252AA | |
| TO1252 | TO-252AA-2LD | |
| TO0220 | TO-220AB/TO-220AC | |
| TOL220 | TO-220AB-L | |
| TO03P0 | TO-3P | |
| TO0247 | TO-247AD-2LD/TO-247AD-3LD/TO-247-3L/TO-247AD-2LM(安美) | Rev.20: 安美已合格 |
| TOP247 | TO-247PLUS-3L | Rev.14 新增 |
| TO0263 | TO-263/TO-263-7L/TO-263AB/TO-263AB-L | Rev.20: 全部已合格 |
| TO0277 | TO-277/TO-277B/TO-277C | |
| ITO220 | ITO-220AB/ITO-220AC | |
| FTO220 | ITO-220AB-F | Rev.14 新增 |
| DO0218 | DO-218AC/DO-218AB | |
| SOP008 | SOP-8 | |
| SOT223 | SOT-223 | |
| SOT-89 | SOT-89 | |
| DO0410 | DO-41 | |
| DO0150 | DO-15 | |
| DO0201 | DO-201AD/DO-201AE | |
| P00600 | P-600 | |
| MDI000 | MDI | |
| SDI000 | SDIP | |
| TDI000 | TDI | |
| TOLL00 | TOLL/TOLLK 9.8x11.7 (TO-Leadless) | Rev.20 更新 |
| sTOLL0 | sTOLL 7x8 (small TO-Leadless) | **Rev.20 新增**, qualification in progress |
| M40000 | M4 系列 | |
| M60000 | M6 系列 | **Rev.18 新增** |
| M80000 | M8 系列 | |
| DXK000 | DXK 系列 | |
| KBJ000 | KBJ-2 | |
| GBU000 | GBU-2 | |
| GBJ000 | GBJ-2 | |
| GBL000 | GBL | |
| GBJS00 | GBJS | |

## Compound Code 完整對照 (42 codes)

> 來源: F-RD0215 rev20, Sheet 0 Q-R 欄
> BOM 驗證: 2026-02-06, 7/42 codes 在 BOM 中有對應物料

| Code | 成型膠 | BOM 驗證 | 備註 |
|------|--------|---------|------|
| 1700 | EK-1700G | - | |
| 1702 | CEL-1702HF9 | - | |
| 1772 | CEL-1772HF9 | - | Rev.09 新增 |
| 3600 | EK-3600GH(GT/GTM) | - | |
| 5000 | CK5000 | - | |
| 8200 | SG-8200 | - | |
| 9240 | CEL-9240HF/10GEM(M1)/10-8L | 67 件 | |
| 100H | ELER-8-100HFS | 161 件 | 含 100HFV 變體 |
| 110G | EME-E110G | - | |
| 131Y | NH-131YS | - | |
| 300L | GE300LCF | - | |
| 500C | 500C / 500C-S | **12,741 件** | 最大宗，含 500C-4/500C-84 變體 |
| 660P | G660BP-A | - | 與 G660 重疊，可能為舊碼 |
| E110 | EME110G | - | |
| E115 | EME-115H | - | |
| E125 | EME125 | - | |
| E500 | E500 | - | |
| E590 | E590HT | - | |
| G100 | KL-G100S | - | |
| G260 | GR260 | - | |
| G300 | GR300 | - | |
| G310 | WH-G310 | - | |
| G430 | TH-G430 | - | |
| G510 | GR510 | - | |
| G530 | GR530 | - | |
| G590 | G590 | 144 件 | EME-G590 Type A |
| G600 | G600(FL/FB) | **3,733 件** | 主要為 G600FL |
| G630 | EME-G630AY-H | 32 件 | |
| G660 | G660/G660BP-A | 580 件 | Rev.10 合併 |
| G700 | G700 | - | |
| G720 | EME-G720C | - | |
| G770 | EME-G770 | - | |
| K200 | KHG200F | - | KHG200F(安美) Rev.13 新增 |
| 400S | EMG400SV-4 | - | Rev.16 新增 (信展通 SOD-123) |
| G350 | WH-G350 | - | Rev.16 新增 (創達-力邁) |
| K400 | KHG400 | - | Rev.16 新增 (首科化微-力邁) |
| 100V | ELER-8-100HFV/100HFV-A | - | Rev.17 新增 |
| 5600 | EK-5600GHR | - | Rev.17 新增 |
| 9220 | CEL-9220HF | - | Rev.20 新增 |
| E600 | EMG-600-2JC | - | Rev.20 新增 |
| K500 | KHG500 | - | Rev.20 新增 (MBU3) |

### BOM 未覆蓋物料 (不在 33 碼表中)

| BOM 物料 | 零件數 | 說明 |
|---------|--------|------|
| ELER-8-130PJ9 | 470 | 因 delamination 問題已停用 |
| G631MB | 6 | 非標準膠種 |
| ELL-2K-2 | 3 | 含鹵，非標準 |
| EME-A631HT | 1 | 非標準膠種 |

### 備註
- **660P vs G660**: 兩者都映射到 G660BP-A，660P 可能為舊版/替代碼
- **SOT23_MD0001**: BOM 中的「罐頭名稱」（模板），正式料會展開到 SUB COM 層看實際膠種
- **26 個未在 BOM 中出現的 code**: 可能為備用膠種、其他工廠使用、或未量產封裝

## LF Code 完整對照

| Code | 材質 | 全名 | 新增時間 |
|------|------|------|---------|
| C | Cu | 銅 | 初始 (2023前標準值) |
| A | Alloy | 合金 (A42) | 初始 |
| P | Cu+Ni-Pd-Au | 鍍鎳鈀金銅 | 初始 |
| B | Bare Cu | 裸銅 | Rev.11 (2023-11-09) |
| G | Cu plating Ag | 鍍銀銅 | Rev.11 (2023-11-09) |
| U | A42 plating Cu | A42鍍銅 | Rev.20 (2025-10-28) |
| D | AgNi plating Au | 銀鎳鍍金 | Rev.20 (2025-10-28) |

## D/A Code 完整對照

| Code | 製程 | 全名 |
|------|------|------|
| EP | Epoxy | 銀膠焊接 |
| EU | Eutectic | 共晶焊 |
| SS | Soft Solder | 軟焊 |
| SP | Solder paste | 焊膏 |
| SF | Solder flake | 焊片 |

## Wires Code 完整對照

| Code | 線材 | 全名 |
|------|------|------|
| CU | Cu wires | 銅線 |
| AU | Au wires | 金線 |
| AG | Ag wires | 銀線 |
| PC | PdAuCu wire | 鈀金銅線 |
| CR | Cu/Rib | 銅線/帶狀 |
| CA | Cu/Al | 銅/鋁複合線 |
| AL | Al wires | 鋁線 |
| CJ | Clip (jump) | Clip bonding |
| LW | LeadWire | 引線 |
| AR | Au/Rib | 金線/帶狀 |
| AA | Au/Al | 金/鋁複合線 |
| AC | Au/Clip | 金線+Clip (Rev.09 新增) |

### 舊版差異

| 舊版 (Sheet 5) | 新版 (Sheet 0) | 說明 |
|----------------|----------------|------|
| CLJ | CJ | Clip bonding 代碼簡化 |
