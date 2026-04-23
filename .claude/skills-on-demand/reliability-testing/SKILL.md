---
name: reliability-testing
description: |
  汽車電子可靠性測試標準應用規則。適用於：
  判斷產品適用的 AEC-Q 標準、查詢材料/製程變更需要的測試項目、
  了解 Q006 銅線加長測試條件、MSL 濕敏等級處理規則、
  測試方法標準對照（JESD22/MIL-STD-750/MIL-STD-883）、
  離散元件動態測試參數體系（trr/Qg/Ciss/CJ/TLP/箝制電壓）、
  ESD/Surge 標準層級（IEC 61000/ISO 10605/ANSI ESD）。
  F-PE0404 廠內規範整合（規範優先序、24欄測試佈局、變更類型映射）。
  當任務涉及可靠性驗證、材料變更評估、測試計畫制定、
  AEC-Q 認證、銅線驗證、MSL 管理、動態參數、
  TLP、箝制電壓、系統級 ESD、IEC 61000、F-PE0404 時觸發。
triggers:
  - AEC-Q101, AEC-Q006, Q101, Q006, 可靠性, qualification, 認證
  - HAST, HTRB, HTSL, H3TRB, UHAST, TC, IOL, PTC, ACBV
  - 銅線, Cu wire, 金轉銅, Au→Cu, 線材變更
  - ESD, HBM, CDM, DPA, WBP, WBS, Die Shear
  - Table 3, 變更測試, 測試矩陣, 測試計畫
  - Q006 銅線驗證, Option 1, Option 2, Family
  - MSL, 濕敏等級, 動態參數, trr, Qg, Ciss, CJ
  - TLP, 箝制電壓, IEC 61000, ISO 10605, Surge
  - Grade, 溫度範圍, Tj max, Schottky
  - TCHT, TCDT, PdAuCu, BSOB, Terminal Strength
  - F-PE0404, 廠內規範, RA Lab, CT Lab, 信賴實驗室, 特性實驗室
  - 規範優先序, 變更類型映射, 封裝製程變更
---

# 汽車電子可靠性測試標準應用規則

> **來源**：AEC-Q101 Rev E + AEC-Q006 Rev B + PANJIT F-PE0404-05 REV:05
> **最後更新**：2026-03-02

---

## Lazy Loading 路由表

| 問題類型 | 讀取 |
|---------|------|
| Q101 完整測試項目（A1-E6 條件/樣品數/標準） | `references/q101-q006-test-details.md` §AEC-Q101 |
| Q006 銅線驗證（Table 3 序列/Option 1 vs 2/Release Criteria/Family） | `references/q101-q006-test-details.md` §AEC-Q006 |
| 失效定義（漂移/漏電/RDSon 判定門檻） | `references/q101-q006-test-details.md` §失效定義 |
| 樣品數與允收標準（77×3 lots 統計意義） | `references/q101-q006-test-details.md` §樣品數 |
| HBM/CDM ESD 分級、WBS 最低力、UIS/DPA、Short Circuit | `references/test-methods-detail.md` |
| DB/WB 檢驗規範（M2017/M2037/Q006 Cu 標準、Inline 建議） | `references/db-wb-inspection-standards.md` |
| 封裝/原物料變更（Table 3 Assembly 15 子分類、Family 定義） | `references/package-material-change-qualification.md` |
| 動態測試參數（按功能分類/TLP/箝制電壓/ESD標準體系/IEC 61000） | `references/dynamic-test-parameters-summary.md` |
| **F-PE0404 廠內規範**（優先序/24欄佈局/變更類型映射/§3.5 vs §3.1） | `references/f-pe0404-integration.md` |

---

## Q101 測試概覽

### Test Group A — 加速環境應力（PC→HAST/H3TRB→UHAST/AC→TC→IOL/PTC）

77×3 lots, 0 failures。關鍵條件：HAST 130°C/85%RH/96h, TC 1000 cycles -55°C~Tj max, IOL ΔTj≥100°C。
Cu wire 產品 A4a TCHT/TCDT 不執行 → follow Q006。

### Test Group B — 加速壽命（HTRB/ACBV/SSOP/HTGB）

77×3 lots, 1000h。Schottky HTRB 注意 thermal runaway → 調 Ta 避 runaway。

### Test Group C — 封裝組裝完整性（DPA→PD→WBP/WBS→DS→TS→RTS→RSH→TR→SD→WG）

WBP: Au/Al → M2037, Cu → Q006。WBS: Q101-003/B116。DS: M2017。TS: M2036 (PTH only)。

### Test Group D — 晶圓製造（DI, Power MOS/IGBT only）

### Test Group E — 電性驗證（EV→TEST→PV→ESDH/ESDC→UIS→SC）

---

## Q006 銅線驗證摘要

- **Option 1**: 1X stress + 詳細 analytical (AM/SEM/WBS/WBP/Cross-section)，若不通過續 2X
- **Option 2**: 直接 2X stress duration
- **三支測試腿**: TC / HAST(THB/H3TRB) / HTSL or HTGB or HTRB，各 3×77 pcs (第三腿 3×45)
- **第三腿選用**: Q006 允許 HTSL/HTGB/HTRB 擇一，依產品類型：Rectifier→HTRB, MOSFET/IGBT→HTGB, 通用→HTSL。三者皆可加速 Cu/Al IMC 成長
- **1X Release**: WBS 禁 Bond lift/Cratering, WBP 只允許 wire breaks, WBS/WBP=0gf → FAIL
- **Family**: Table 2 定義 Case 1-5，die/pkg/site 屬性不同時各需獨立驗證

---

## Grade 溫度範圍 (Q101)

| Grade | Ta Range | Tj max | TC Range | 應用環境 |
|-------|----------|--------|----------|---------|
| 0 | -40°C ~ +150°C | >150°C | -65°C ~ +150°C (or Tj max) | 引擎室 |
| 1 | -40°C ~ +125°C | 150°C | -55°C ~ Tj max (≤150°C) | 引擎室周邊 |
| 2 | -40°C ~ +105°C | 125°C | -55°C ~ +125°C | 車內一般 |
| 3 | -40°C ~ +85°C | 105°C | -55°C ~ +105°C | 車內低溫 |

---

## Table 3 變更測試矩陣（摘要，2026-02-13 像素驗證修正版）

| 變更 | A2 | A3 | A4 | A4a | A5 | B1 | B2 | C1 | C2 | C3 | C5 | C6 | C8 | C9 | C10 | E0 | E2 | E6 | NOTES |
|------|:--:|:--:|:--:|:---:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:---:|:--:|:--:|:--:|:------|
| **Wire Bonding** | ● | | ● | ● | ● | J | J | ● | | ● | | | ● | | | | ● | ● | |
| **LF Plating** | C | C | C | | | | | | D | 2,C | C | | | C | D | D | | | |
| **LF Material/Source** | **●** | **●** | **●** | **●** | **●** | | | | ● | 2 | ● | ● | ● | ● | ● | ● | | ● | **A,F,X** |
| **Die Attach** | ● | ● | ● | | ● | | | | | | ● | | ● | ● | | | ● | ● | A,X |
| **Encap Material** | ● | ● | ● | ● | ● | ● | ● | ● | ● | | | | ● | ● | ● | ● | ● | | A,F,G |

> **完整 15 子分類 + Note codes + 像素驗證方法** → `references/package-material-change-qualification.md`

---

## 快速查詢指南

### 「TS 是什麼測試？」

**Terminal Strength（端子強度）** — C6, MIL-STD-750-2 M2036, Through-hole leaded parts only

### 「TCDT 是什麼測試？」

**TC Delamination Test** — A4a alt, TC 後 100% SAT 掃描 + decap WBS。Cu Wire 不執行 → Q006

### 「H3TRB 和 HAST 差異？」

| 項目 | HAST (A2) | H3TRB (A2 alt) |
|------|-----------|----------------|
| 溫度/壓力 | **130°C 加壓** | **85°C 常壓** |
| 時間 | 96h | **1000h** |
| 偏壓 | 80% Vr (≤42V) | 80% VBR (≤100V) |
| 用途 | 加速封裝濕氣 | 晶片電性壽命 |

### 「Schottky 該用什麼測試？」

避免 HAST 130°C（Barrier 劣化）→ 建議 H3TRB 85°C + UHAST/AC（無偏壓）。HTRB 注意 thermal runaway。

---

## ECR/ECN 變更驗證關鍵規則（2026-02-25 升級）

> 來源：ECR-L06~L09, L11, L17, L26, L27 (learning_notes.md)
> 驗證：使用者確認 + PDF 原文驗證

### VR1: Q006 是 Q101 的補充，不是替代 (Q006-SUPPLEMENT)

銅線變更需**同時**滿足 AEC-Q006（銅線補充測試）+ AEC-Q101 Table 3（基礎變更框架）。
C1/C2 測試計畫標準標示為「Q101 Rev E + Q006 Rev B」。

### VR2: Q006 第三支腿 — HTSL / HTGB / HTRB 擇一 (Q006-LEG3)

Q006 Rev B 第三支測試腿允許三種方式，依產品類型選用：

| 測試 | 偏壓 | 適用產品 | 共同目的 |
|------|------|---------|---------|
| HTSL | **無偏壓** | 通用 | 加速 Cu/Al IMC 成長 + stitch bond 劣化 |
| HTGB | **閘極偏壓** | MOSFET/IGBT | 同上 + 閘極氧化層應力 |
| HTRB | **反向偏壓** | Rectifier/Diode | 同上 + 接面穩定性 |

三者**可互選**（Q006 原文："Perform per the test requirements in AEC-Q100/Q101"）。
PANJIT 以二極體/整流器為主 → 選用 HTRB 作為第三腿是正確的。

### VR3: PdAuCu 不享 Q101 Note 2 豁免 (PDAUCU-NO-NOTE2)

Q101 Note 2 只豁免「Cu wire bonded products」不需做 A4a (TCHT/TCDT)。
PdAuCu (Palladium-Gold-Copper alloy wire) 嚴格不算 bare Cu wire → O-0001 (BSOB) **必須做 TCT**。

### VR4: 線材變更需完整 ESD + DPA (WIRE-CHANGE-ESD-DPA)

Au→Cu 改變電阻率，影響 ESD 放電路徑：
- 完整 ESD HBM (E3) + CDM (E4) **qualification**（非僅 engineering evaluation）
- 完整 DPA (C1)（非僅 Q006 的 XS/SEM，後者只看 wire bond 區域）

### VR5: M2037 vs Q101 C3 拉力門檻差異 (WBP-THRESHOLD)

| 標準 | 1 mil Au wire 最小值 |
|------|---------------------|
| MIL-STD-750 M2037 Table 2037-I | **2.5 gf** |
| AEC-Q101 C3 Additional Requirements | **3 gf** |

Q101 要求**高於** M2037。Au wire ≤ 1 mil 時，拉力鉤須放在 **ball bond 上方**。

### VR6: C6 Terminal Strength 僅適用 PTH (C6-PTH-ONLY)

Q101 C6 (MIL-STD-750-2 M2036): "Through-hole leaded parts only"。
- **PTH 封裝**：DO-201, DO-41, TO-220, TO-247, TO-92
- **SMT 封裝**（C6 不適用）：DO-218AB, SOT-23, SOD-123, SMAF, TO-277 等
- DO-218AB 是**大型 SMT 封裝**（兩面散熱片），非 PTH

### VR7: 背面金屬變更 = Die Attach 變更 (BACKMETAL-IS-DA)

BackAu→Sn/Ag 變更正確分類為 Table 3 **Die Attach**（非 Die Overcoat）：
- **Die Overcoat** = 晶片**正面**保護塗層（passivation/polyimide）
- **Die Attach** = 晶片**背面**黏著/焊接介面（含 BackAu/Sn/Ag 金屬化層）

Die Attach 測試項目：A2●, A3●, A4●, A5●, C5●, C8●, C9●, E2●, E6●, Notes A(SAT), X(X-Ray), H

---

## F-PE0404 廠內規範整合（2026-03-02 升級）

> 來源：ECR-R25, STD-L04/L05/L06, ECR-L43/L44/L45 (learning_notes.md)
> 驗證：F-PE0404-05 原文 + 使用者確認 D-091/D-094/D-095

### VR8: 規範優先序 — F-PE0404 → Q006 → Q101 (SPEC-PRIORITY)

變更評估時：第一優先 F-PE0404（廠內），第二 Q006（Cu Wire 補充），第三 Q101（fallback）。
廠內規範已對 PANJIT 產品線做適配：省略 Thyristor/Hermetic/Smart Power 不適用項目，系統性增列 MSL。

### VR9: §3.5 封裝製程變更不區分產品功能 (NO-FUNC-SPECIFIC)

F-PE0404 Section 3.5（Assembly Process Changes）的 15 種變更類型對所有產品功能（MOSFET/Zener/SKY/TVS/ESD...）適用同一測試矩陣。
Function-specific 測試（DI/HTGB/UIS/SSOP 等）**僅適用於 §3.1（新 Wafer Qualification）**。

### VR10: F-PE0404 測試佈局 24 欄 = RA Lab 17 + CT Lab 7 (F-PE0404-LAYOUT)

RA Lab（信賴實驗室）：B1, B2, A4, A4a, A3, A2, A5, E3/E4, C1, C2, C6, C7, C8, C10, C9, C11, A1
CT Lab（特性實驗室）：E0(EV), E2(PV), C3(WBP), C4(WBS), C5(DS), E5(UIS), D1(DI)
F-PE0404 省略 Q101 的 B1a(ACBV)/C12-C15(Hermetic)/E6(SC)。

> **完整詳細** → `references/f-pe0404-integration.md`

---

## 來源文件

| 文件 | 版本 | 日期 |
|------|------|------|
| AEC-Q101 | Rev E | 2021-03-01 |
| AEC-Q006 | Rev B | 2025-06-30 |
| AEC-Q101-001A ~ 006 | Various | 1996-2019 |
| PANJIT F-PE0404-05 | REV:05 | 廠內規範 |

> **PDF 位置**：`projects/aec-q-standards/vault/originals/`

---

## 修訂記錄

| 日期 | 內容 |
|------|------|
| 2026-02-05 | 初始建立（Q101/Q006 完整內容） |
| 2026-02-05 | TS=Terminal Strength 更正、TCDT 定義新增 |
| 2026-02-12 | 新增 db-wb-inspection-standards.md、package-material-change-qualification.md |
| 2026-02-12 | **瘦身**：測試詳細表格移至 q101-q006-test-details.md，SKILL.md 改為路由表+摘要 |
| 2026-02-24 | 新增 dynamic-test-parameters-summary.md（動態參數體系/TLP/ESD標準層級），擴展觸發詞 |
| 2026-02-25 | **/promote 升級**：新增 VR1~VR7（ECR/ECN 變更驗證規則），來源 ECR-L06~L09/L11/L17/L26/L27 |
| 2026-03-02 | **/promote 升級**：新增 VR8~VR10（F-PE0404 整合）+ reference `f-pe0404-integration.md`，來源 ECR-R25/STD-L04~L06/ECR-L43~L45 |
