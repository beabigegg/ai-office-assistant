# 封裝 x 製程能力矩陣

> 來源: F-RD0215 rev20, Sheet 6 "組合 嘉韋"
> 定義每種封裝支援哪些製程步驟（V = 支援）

## 製程步驟列表

| 階段 | 製程 | 細分 |
|------|------|------|
| Die bond | Eutectic | 共晶焊 |
| | Epoxy | 銀膠焊 |
| | Solder | 軟焊 |
| Clip bonding | Jump | Clip jump |
| | Lead frame | Clip on LF |
| Wire bond | Cu | 銅線打線 |
| | Au | 金線打線 |
| Molding | -- | 成型 |
| De-gate | -- | 去澆口 |
| Wet De-flash | -- | 濕式去毛邊 |
| Plating (strip) | -- | 條鍍 |
| Laser Marking | -- | 雷射標記 |
| Device Trim Form | Punchi | 沖切 |
| | Saw UV de-tape | 鋸切+UV脫膜 |
| Plating (barrel) | -- | 桶鍍 |
| TMTT | Laser Marking | TMTT 段雷射 |
| | Reel Packing | TMTT 段捲帶包裝 |

## 封裝製程能力總覽

| NEW Code | 封裝 | Die Bond | Clip Bond | Wire Bond | 後段特殊 |
|----------|------|----------|-----------|-----------|---------|
| SOTU20 | SOT-23/SOT-323 | EU+EP | -- | CU+AU | 標準 |
| SOTD20 | SOT-363/353 | EU+EP | -- | CU+AU | 標準 |
| SOTU00 | SOT-523/543/553/563 | EU+EP | -- | AU (主流) + CU (擴展中) | 2023文件標 AU only，但 BOM 已有少量 CU (SOT-523:4筆, SOT-563:1筆)。ECR 正在擴展銅線能力 |
| SODU20 | SOD-123 | EU | -- | CU+AU | 標準 |
| SODU00 | SOD-123FL | Solder | Jump+LF | -- | Clip，無 wire |
| SODU10 | SOD-123HE/SOD-323HE | EU+Solder | -- | CU+AU | Heat Sink |
| SMAF00 | SMAF | Solder | Jump+LF | -- | Clip，TMTT 後段 |
| SMBF00 | SMBF | Solder | Jump+LF | -- | Clip，TMTT 後段 |
| DFN030 | DFN0603 | EP | -- | **AU only** | Saw 分離 |
| DFN050 | DFN 2L/3L/DFN2510/DFN5515 | EP | -- | **AU only** | Saw 分離 |
| DFN075 | DFN2020B-6L | EP | -- | AU+CU | Saw 分離 |
| DF3333 | DFN3333-8L | EP | -- | CU+AU | Saw 分離 |
| DF5060 | DFN5060-8L | EP+SS | -- | CU+AU | Saw 分離 |
| TDI000 | MICRO DIP (TDI) | Solder | -- | CU | |
| TO0277 | TO-277/TO-277C | Solder | Jump+LF | -- | Clip，TMTT 後段 |
| TO0252 | TO-252AA | EU+SS | -- | CU+AU | |
| TO0220 | TO-220AB/AC | EU+SS | -- | CU+AU | |
| TO0263 | TO-263 | EU+SS | -- | CU+AU | |
| TO0247 | TO-247 | SS | -- | CU+AU | |
| DO0218 | DO-218AC/AB | Solder | Jump+LF | -- | Clip，Barrel plating |
| SOT223 | SOT-223 | EU+EP | -- | CU+AU | |
| SOP008 | SOP-8 | EP | -- | CU+AU | |

## 關鍵發現

### 1. 金線為主的小型封裝（銅線擴展中）

以下封裝歷史上以金線為主，2023 文件標示 AU only，但 BOM 中已有少量銅線 BOP：
- SOTU00 (SOT-523/543/553/563) -- 小型封裝，BOM 中 SOT-523 有 4 筆 CU，SOT-563 有 1 筆 CU
- DFN030 (DFN0603) -- 超小 DFN，待驗證
- DFN050 (DFN 2L/3L) -- 小 DFN，待驗證

**注意**: ECR 金轉銅變更包含將銅線能力擴展到這些封裝（cost down + 能力擴展）。

### 2. Clip bonding 封裝（不涉及金轉銅）

以下封裝使用 Clip bonding（非 wire bonding），不在金轉銅範圍：
- SODU00 (SOD-123FL) -- Solder + Clip
- SMAF00 (SMAF) -- Solder + Clip
- SMBF00 (SMBF) -- Solder + Clip
- TO0277 (TO-277) -- Solder + Clip
- DO0218 (DO-218) -- Solder + Clip

### 3. TMTT 後段封裝

使用 TMTT 後段處理（Laser Marking + Reel Packing 在 TMTT 站完成）：
- SMAF00, SMBF00, TO0277

### 4. NEW vs OLD Code 隱藏欄對照

Sheet 6 的隱藏 B 欄包含舊版 Package Code，可用於 NEW-OLD 對照：
| NEW | OLD |
|-----|-----|
| SOTU20 | SOT230 |
| SOTD20 | SOT231 |
| SOTU00 | SOT232 |
| SODU20 | SOD23W |
| SODU00 | SOD23F |
| SODU10 | SOD231 |

### 5. 隱藏欄中的物理參數

Sheet 6 的隱藏欄 D/E/F/G 包含：
- D: (未知)
- E: Lead type
- F: Lead frame Thickness
- G: Body Size

這些參數未在可見區展示，但可能在深入分析時有用。
