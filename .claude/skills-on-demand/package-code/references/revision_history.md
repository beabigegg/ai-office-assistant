# F-RD0215 版本變更摘要

> 文件編號: F-RD0215「車規產品 Wafer 與 Package 系列代碼原則」
> 來源: Sheet 4 "更新履歷" (Rev.02 ~ Rev.15)
> 現行版本: Rev.20 (2025-10-28)

## 重要版本變更

### Rev.03 (2020-09-09) -- Package Code 重新定義
- **里程碑**: 從舊版編碼（Sheet 5 "原-總編碼"）切換為新版編碼（Sheet 0 "new編碼"）
- 此版本後的 Package Code 才是目前使用的格式

### Rev.08 (2022-12-27) -- Vendor Code 改制
- **重大變更**: PANJIT 自有廠區 Vendor Code 從統一 "P" 改為分區碼
  - 5 = MBU3, 6 = MBU2, 7 = MBU1 (岡山廠)
- 新增 "Package Supplier code" Sheet（Sheet 3）
- 已建立的 Package Code 不追溯

### Rev.09 (2023-03-24)
- 新增 Wires Code: AC (Au/Clip)
- 新增 Compound: CEL-1772HF9
- 新增 Vendor: X = ATX 日月新半導體

### Rev.10 (2023-04-13)
- G660BP-A 合併入 G660 Compound Code
- TO-277C 加入 TO0277 封裝組
- SMAF/SMBF 封裝確認

### Rev.11 (2023-11-09)
- 新增 LF Code: B (Bare Cu), G (Cu plating Ag)
- 新增 Vendor: V = 龍晶微(龍平微)
- 新增封裝: ITO-220AB-F (FTO220), TO-247-3L

### Rev.12 (2024-01-11)
- TO-263AB (unqualified, GEM) 加入
- DFN5060XC-8L (unqualified, Carsem) 加入

### Rev.13 (2024-02-27)
- TO-247AD-2LM (unqualified, 安美) 加入
- 新增 Compound: K200 = KHG200F (安美)
- 新增 Vendor: A = 安美 (未合格承認供應商)

### Rev.14 (2024-02-29 ~ 2024-04-12)
- 新增封裝: TOP247 (TO-247PLUS-3L)
- 新增封裝: TO1252 (TO-252AA-2LD)
- 新增封裝: FTO220 (ITO-220AB-F)
- **刪除**: SF (solder flux) 從 Wires Code 移除
  - 注意: SF 在 D/A Code 中仍存在 (Solder flake)

### Rev.15 (2024-09-03)
- 新增 Package Code: DFN33S (DFN3333S-8L, WX Sawn type)
- 新增 Package Code: DFN56S (DFN5060S-8L, WX Sawn type)
- WX = 無錫廠 Sawn type（鋸切分離）封裝

### Rev.16 (2024-10-07)
- 新增 Compound: 400S (EMG400SV-4, 信展通 SOD-123 用)
- 新增 Vendor: U = 信展通 (code 106534)
- 信展通 SOD-123 compound 400S + vendor U

### Rev.17 (2024-11~12)
- 新增 Compound: 100V (ELER-8-100HFV)
- 新增 Package: SC-89 加入 SOTU00 封裝組
- 新增 Vendor: J = 晶導微 (code 104161, 2024-12-12)

### Rev.18 (2025-02-06~07)
- 新增 PANSTAR 體系供應商: H=華宇HISEMI, D=長電JCET
- 新增 Vendor: Y = YJ 揚杰 (code 104315 OSAT)
- 新增 Package Code: M60000 (M6)
- 安美 (code A) 升格為合格供應商，ERP 105978
- PANSTAR-合肥矽邁 SMAT (code C) 升格為合格

### Rev.19 (2025-04-11)
- 新增 DFN5060SW-8L (sawed type + WF) 加入 DFN56S
- 新增 DFN3333SW-8L (sawed type + WF) 加入 DFN33S

### Rev.20 (2025-04-29 ~ 2025-10-28) -- 現行版本
- 新增 Vendor: N = PANSTAR-南岩Nanotesch
- 新增 Compound: 9220 (CEL-9220HF)
- 新增 Compound: E600 (EMG-600-2JC)
- 新增 LF Code: U = A42 plating Cu
- 新增 LF Code: D = AgNi plating Au
- 新增 Package Code: sTOLL0 (sTOLL 7x8, small TO-Leadless)
- 新增 Package Code: PDFN88 (PDFN8x8-8L)
- DFN 厚度碼標準化: 0→030, 1→050, 2→075
- DFN5515 更新為 DFN5515C-14L/18L
- DFN2020BW-6L 加入 DFN075 (qualification in progress)
- TO-263 系列、TO-247AD-2LM(安美) 移除 unqualified 標記
- DF5060, DF8080 從 unqualified → qualification in progress
- TOLL00 加入 TOLLK, 尺寸 9.8x11.7
- Vendor Code 格式標準化（冒號後加空格）
- Wires Code 修正: Cu/Rid → Cu/Rib
- 新增 MBU3 Package Code List (工作表1, 8 筆)

## 版本趨勢觀察

1. **供應商擴張**: 持續新增外包供應商（ATX, 龍晶微, 安美），反映產能分散策略
2. **Unqualified 封裝增加**: Rev.12~13 新增多個 unqualified 封裝，表示積極驗證新組合
3. **技術演進**:
   - LF 材質多樣化（Rev.11 新增 B/G）
   - 新封裝形式（TOLL, TO-247PLUS, Sawn type DFN）
   - Clip bonding 相關（AC = Au/Clip）
4. **品質管控**: 安美 (code A) 和 SMAT (code C) 標記為「未合格承認供應商」

## 版本完整清單

| Rev | 日期 | 主要變更 |
|-----|------|---------|
| 02 | (早期) | 基礎版本 |
| 03 | 2020-09-09 | Package Code 重新定義（new 編碼） |
| 04~07 | 2020~2022 | 逐步完善 |
| 08 | 2022-12-27 | Vendor Code 改制 P->5/6/7 |
| 09 | 2023-03-24 | AC/CEL-1772HF9/ATX |
| 10 | 2023-04-13 | G660 合併/TO-277C/SMAF/SMBF |
| 11 | 2023-11-09 | LF B/G/龍晶微/ITO-220AB-F |
| 12 | 2024-01-11 | TO-263AB(GEM)/DFN5060XC(Carsem) |
| 13 | 2024-02-27 | TO-247AD-2LM(安美)/K200/安美 vendor |
| 14 | 2024-02-29~04-12 | TOP247/TO1252/FTO220/刪除SF |
| 15 | 2024-09-03 | DFN33S/DFN56S (WX Sawn type) |
| 16 | 2024-10-07 | 信展通/400S/Vendor U |
| 17 | 2024-11~12 | 100V/SC-89/晶導微 |
| 18 | 2025-02-06 | PANSTAR(H/D)/揚杰(Y)/M60000/安美升格 |
| 19 | 2025-04-11 | DFN SW type(sawed+WF) |
| 20 | 2025-04-29~10-28 | 南岩(N)/9220/E600/LF U,D/sTOLL0/PDFN88/TO-263合格 |
