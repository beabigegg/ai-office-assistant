# F-PE0404-05 REV:05 整合知識

> **來源**：PANJIT F-PE0404-05 REV:05（廠內可靠性測試規範）
> **升級日期**：2026-03-02
> **升級來源**：ECR-R25, STD-L04/L05/L06, ECR-L43/L44/L45 (learning_notes.md)

---

## 1. 規範優先序（ECR-R25, D-091）

變更評估可靠性測試時，依以下優先序查閱：

| 優先 | 規範 | 用途 |
|------|------|------|
| **第一** | F-PE0404-05（廠內） | §3 變更矩陣 + §1 測試項目表 |
| **第二** | AEC-Q006 Rev B | Cu Wire 補充（三腳架構） |
| **第三** | AEC-Q101 Rev E | F-PE0404 未涵蓋項目的 fallback |

**理由**：廠內規範已根據 PANJIT 產品線特性做適配（省略不適用項目、強化關鍵項目），比直接參考國際標準更精準。

---

## 2. F-PE0404 測試佈局（ECR-L44）

### 24 欄 = RA Lab 17 + CT Lab 7

**RA Lab（信賴實驗室）17 項**：

| 序 | 代碼 | 測試名稱 | Q101 對應 |
|---|------|---------|-----------|
| 1 | B1 | HTRB (High Temperature Reverse Bias) | Group B |
| 2 | B2 | HTGB (High Temperature Gate Bias) | Group B |
| 3 | A4 | TCT (Temperature Cycling Test) | Group A |
| 4 | A4a | TCDT (TC Delamination Test) | Group A |
| 5 | A3 | UHAST (Unbiased HAST) | Group A |
| 6 | A2 | HAST (Highly Accelerated Stress Test) | Group A |
| 7 | A5 | IOL (Intermittent Operating Life) | Group A |
| 8 | E3/E4 | ESD (HBM + CDM) | Group E |
| 9 | C1 | DPA (Destructive Physical Analysis) | Group C |
| 10 | C2 | PD (Physical Dimensions) | Group C |
| 11 | C6 | TS (Terminal Strength) | Group C |
| 12 | C7 | RTS (Resistance to Solvents) | Group C |
| 13 | C8 | RSH (Resistance to Soldering Heat) | Group C |
| 14 | C10 | SD (Solderability) | Group C |
| 15 | C9 | TR (Thermal Resistance) | Group C |
| 16 | C11 | WG (Whisker Growth) | Group C |
| 17 | A1 | MSL (Moisture Sensitivity Level) | Group A |

**CT Lab（特性實驗室）7 項**：

| 序 | 代碼 | 測試名稱 | Q101 對應 |
|---|------|---------|-----------|
| 18 | E0 | EV (Electrical Verification) | Group E |
| 19 | E2 | PV (Parametric Verification) | Group E |
| 20 | C3 | WBP (Wire Bond Pull) | Group C |
| 21 | C4 | WBS (Wire Bond Shear) | Group C |
| 22 | C5 | DS (Die Shear) | Group C |
| 23 | E5 | UIS (Unclamped Inductive Switching) | Group E |
| 24 | D1 | DI (Destructive Inspection) | Group D |

### F-PE0404 省略的 Q101 項目

| Q101 代碼 | 名稱 | 省略原因 |
|-----------|------|---------|
| B1a | ACBV (Avalanche Capability) | Thyristor 專用，PANJIT 無此產品 |
| C12-C15 | Hermetic 系列測試 | PANJIT 無 Hermetic 封裝 |
| E6 | SC (Safe Operating Curve / Short Circuit) | Smart Power 專用，PANJIT 無此產品 |

---

## 3. F-PE0404 vs Q101 Table 3 差異（STD-L04）

### F-PE0404 更嚴格

- **MSL(A1) 系統性增列**：Assembly Site Transfer、New/Equivalent LF、Wire、Compound、D/A 全加 MSL
- **Parameter Analysis 額外欄位**：每個變更類型增加「參數分析」要求（超越 PASS/FAIL 的趨勢評估）
- **New Wafer 產品類型細分**：8 種（Diode/TVS/ESD/Schottky/MOSFET/Trench/IGBT/FRD）
- **Equivalent 變更仍要求部分測試**：如 Equivalent LF 需 A4(TC) + C5(DS) + C9(Solderability)
- **● 符號語意強化**：Q101 的 "should be considered" → F-PE0404 的「必須執行」

### F-PE0404 較寬鬆

- Assembly Site Transfer 缺 C5(DS)：Q101 有 ● 標記
- New Package C6(TS) 降級：Q101 為 ●，F-PE0404 降為 E（依客戶要求）

### ● 符號語意差異（STD-L06）

| 規範 | ● 定義 | 強制程度 |
|------|--------|---------|
| Q101 Table 3 Legend | "should be considered" (Appendix 3 A3.1: 討論基準，可協議刪減) | 建議 |
| F-PE0404 實際執行 | 必須執行 | **強制** |

→ 按 F-PE0404 評估的測試範圍 ≥ 按 Q101 ● 定義評估的範圍

---

## 4. §3.5 封裝製程變更 — 不區分產品功能（ECR-L43, D-094）

**關鍵規則**：F-PE0404 Section 3.5（Assembly Process Changes）的 15 種變更類型**不區分產品功能**。

- 所有料號（MOSFET/Zener/SKY/TVS/ESD...）適用同一測試矩陣
- Function-specific 測試（DI/HTGB/UIS/SSOP 等）**僅適用於 §3.1（新 Wafer Qualification）**
- §3.1 有 8 種產品類型分行（Diode/TVS/ESD/Schottky/MOSFET/Trench/IGBT/FRD）
- §3.5 無產品類型分行

**適用範圍判斷**：
- O-0001~O-0004 全為封裝製程變更 → §3.5 → 無 Function-specific 測試
- 新晶片認證 → §3.1 → 需查功能分行

---

## 5. ECR 變更類型映射（ECR-L45）

### O-0001~O-0004 → F-PE0404 §3.5 變更類型

| ECR | 描述 | F-PE0404 變更類型 | §3.5 行 |
|-----|------|------------------|---------|
| O-0001 | 金線轉鈀金銅線 (BSOB) | 線材/跳線變更 | 行12 |
| O-0002 | 金線轉銅線 | 線材/跳線變更 + Q006 override | 行12 |
| O-0003 | 背金轉背錫/背銀 | 貼晶 Die Attach | 行10 |
| O-0004 | 腳架材質/供應商變更 | 腳架材質/供應商變更 | 行14 |

### 各變更測試項目（F-PE0404 §3.5 原文）

**線材/跳線變更** (O-0001, O-0002)：
`B1(J), B2(J), A4, A4a, A2, A5, C1, C8, A1, E2, C3, C4`
- Q006 override: O-0002 (Cu Wire) → A4a/TCDT 不適用

**貼晶 Die Attach** (O-0003)：
`A4, A3, A2, A5, C8, C9, A1, E2, C5` + NOTES A,X

**腳架材質/供應商變更** (O-0004)：
`A4, A4a, A3, A2, A5, C2, C6, C8, C10, C9, C11(L), E0, C3(2), C5` + NOTES A,F,X

---

## 6. Full_PKG_CODE → Q101/Q006 Family 映射（STD-L05）

| PKG_CODE 段 | Q101 Assembly Family 屬性 | Q006 Technology Family |
|-------------|--------------------------|----------------------|
| Seg1 Package | 封裝類型（A4 TC 條件、C6 TS 適用性） | Case 3d（package 構造差異） |
| Seg2 LF | LF base material（A42/Cu/銅鍍銀） | Case 3a/3b（material 差異） |
| Seg3 D/A | D/A material/method（EP/EU/SS/SP） | — |
| Seg4 Wires | Wire bond material（AU/CU/AG/PC） | Case 3c（wire 差異） |
| Seg5 Compound | Mold compound | Case 3a（compound 差異） |
| Seg6 Vendor | Assembly site（廠區） | Case 1（site transfer） |

**PKG_CODE 未覆蓋的屬性**：
- LF plating（Ag/Ni/NiPdAu）→ 需從 BOM LEF Desc 或 BOP 推導
- Wire diameter（0.8/1.0/1.2 mil）→ 需從 BOP Pos4-5 推導
- Silicon Die 屬性（Q006 Cases 2a-2c）→ 需從 BOM 晶片資料推導
