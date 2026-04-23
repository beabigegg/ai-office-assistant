# 封裝供應商代碼完整列表

> 來源: F-RD0215 rev20, Sheet 0 + Sheet 3 "Package Supplier code"

## 2023 年制度變更

**Rev.08 (2022-12-27)** 實施重大變更：
- PANJIT 自有廠區不再統一使用 "P"
- 改為按 MBU (Manufacturing Business Unit) 分區編碼
- 已建立的 Package Code **不追溯**（舊料號仍可能是 P）

| 舊制 | 新制 | 說明 |
|------|------|------|
| P = PANJIT (統一) | 5 = MBU3 | PANJIT 第三製造單位 |
| | 6 = MBU2 | PANJIT 第二製造單位 |
| | 7 = MBU1 = **岡山廠** | PANJIT 第一製造單位 |

## 完整供應商列表

| Vendor Code | ERP 交易代碼 | 供應商名稱 | 分類 | 新增版本 | 備註 |
|-------------|-------------|-----------|------|---------|------|
| P | -- | PANJIT | 自有(舊制) | 初始 | 2022年以前適用 |
| 5 | 待 | PANJIT_MBU3 | 自有(新制) | Rev.08 | ERP 代碼待設定 |
| 6 | -- | PANJIT_MBU2 | 自有(新制) | Rev.08 | |
| 7 | 無 | PANJIT_MBU1 (岡山廠) | 自有(新制) | Rev.08 | 自有廠區無需交易代碼 |
| E | 104427 | GEM 捷敏電子 | 外包 | 初始 | |
| F | 103583 | FH 風華 | 外包 | 初始 | |
| T | 104685 | TSHT 天水華天 | 外包 | 初始 | |
| U | 103694 / 106534 | Comchip 典琦 / 信展通 | 外包 | 初始 / Rev.16 | 注意: U 碼有兩家供應商 |
| B | -- | 力邁 | 外包 | 初始 | |
| L | -- | ATEC | 外包 | 初始 | |
| K | -- | PPL 寶浦萊 | 外包 | 初始 | |
| S | -- | Carsem 嘉盛 | 外包 | 初始 | |
| 8 | -- | 秀武 | 外包 | 初始 | |
| M | -- | 美林 | 外包 | 初始 | |
| X | -- | ATX 日月新半導體 | 外包 | Rev.09 (2023-03-24) | |
| V | -- | 龍晶微(龍平微) | 外包 | Rev.11 (2023-11-09) | |
| A | 105978 | 安美 | 外包 | Rev.13 (2024-02-27) | Rev.20 已合格 |
| C | -- | PANSTAR-合肥矽邁SMAT | PLP 專用 | -- | Rev.20 已合格 |
| J | 104161 | 晶導微 | 外包 | Rev.17 (2024-12-12) | |
| H | -- | PANSTAR-華宇HISEMI | 外包 | Rev.18 (2025-02-06) | |
| D | -- | PANSTAR-長電JCET | 外包 | Rev.18 (2025-02-06) | |
| Y | 104315 | YJ 揚杰 (OSAT) | 外包 | Rev.18 (2025-02-07) | |
| N | -- | PANSTAR-南岩Nanotesch | 外包 | Rev.20 (2025-04-29) | |

## ECR/ECN 交叉驗證

### Vendor Code 7 = MBU1 = 岡山廠

與 ECR-R17 完全吻合：
- ECR 變更僅限**岡山廠**進行
- Vendor Code 7 的料號 = 岡山廠生產
- 非 Vendor Code 7 的自有料號（5, 6）= 其他廠區，不在本次變更範圍

### 供應商合格狀態 (Rev.20 更新)

**已合格** (Rev.20 移除 unqualified 標記):
- TO-263AB (GEM, code E) -- 已合格
- TO-263AB-L (ATX, code X) -- 已合格
- TO-247AD-2LM (安美, code A) -- 已合格
- 安美 (code A) -- 已合格，ERP 105978
- PANSTAR-合肥矽邁 SMAT (code C) -- 已合格

**驗證中** (qualification in progress):
- DFN5060XC-8L (Carsem, code S)
- DFN8x8-4L (DF8080)
- PDFN8x8-8L (PDFN88, Rev.20 新增)
- sTOLL 7x8 (sTOLL0, Rev.20 新增)

### MBU 與外包的關係

| 生產來源 | Vendor Code | ECR 適用性 |
|---------|-------------|-----------|
| 岡山廠 (MBU1) | 7 | 適用（主要對象） |
| MBU2 | 6 | 不適用（非岡山） |
| MBU3 | 5 | 不適用（ECR-R2 排除） |
| 外包供應商 | E/F/T/U/B/L/K/S/8/M/X/V/A/J/H/D/Y/N | 不適用（非自製） |
| 舊 PANJIT | P | 需判斷實際生產廠區 |

## Sheet 3 額外資訊

Sheet 3 "Package Supplier code" 提供的額外欄位：
- **D 欄 (Update reason)**: 供應商新增或變更原因
- **E 欄 (Update date)**: 更新日期

最新新增（2025-04-29）：
- N = PANSTAR-南岩Nanotesch

Rev.16~20 期間新增：
- U = 信展通 (Rev.16, 2024-10-07)
- J = 晶導微 (Rev.17, 2024-12-12)
- H = PANSTAR-華宇HISEMI (Rev.18, 2025-02-06)
- D = PANSTAR-長電JCET (Rev.18, 2025-02-06)
- Y = YJ 揚杰 (Rev.18, 2025-02-07)
- N = PANSTAR-南岩Nanotesch (Rev.20, 2025-04-29)
