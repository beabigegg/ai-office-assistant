# 封裝變更與原物料變更 — 資格重新認證指南

> **來源**：AEC-Q101 Rev E (2021-03-01) Table 3 + Appendix 1 + Sections 2.2-3.2
> **檔案位置**：`projects/aec-q-standards/vault/originals/AEC_Q101_Rev_E_Base_Document.pdf`
> **最後更新**：2026-02-13（根據官方 PDF 像素級驗證修正 — 見驗證方法附錄）

---

## 一、變更管理總則 (Section 3.2)

### 1.1 何時需要重新認證

當供應商對產品和/或製程做出**影響（或可能影響）**以下的變更時：
- **Form**（外形）
- **Fit**（配合）
- **Function**（功能）
- **Quality**（品質）
- **Reliability**（可靠性）

### 1.2 重新認證流程

```
供應商識別變更 → Table 3 確定測試項目 → 與客戶討論測試計畫
    → 簽署 Qualification Test Plan → 執行測試 → 提交報告 → 客戶核准
```

### 1.3 Table 3 的定位

- Table 3 是**測試超集 (superset)**，作為供應商與客戶討論的基線
- 標記的測試項目表示「**should be considered**」（應被考慮）
- 供應商可提出不執行某項測試的技術理由，**但必須文件化**
- 客戶有權要求額外測試

### 1.4 抽樣要求

| 項目 | 要求 |
|------|------|
| 最小 Lot 數 | **3 lots** |
| 每 Lot 最小樣品數 | **77 pcs** |
| 允收標準 | **0 failures** |
| 總樣品數 | 231 pcs（90% CL → ≤ 1400 ppm） |
| 生產要求 | 必須使用量產工具和製程 |

---

## 二、Assembly 變更類型與對應測試矩陣 (Table 3 ASSEMBLY Section)

### 2.1 完整測試對照表

> **符號說明**：● = 建議執行，字母 = 有條件執行（見註解）
> **驗證方法**：2026-02-13 從原始 PDF 渲染 300 DPI 影像，逐格像素掃描驗證（見附錄）
> **閾值**：暗像素比率 > 0.07 = 有內容（真實●比率約0.15-0.20, 文字標記約0.07-0.10）

| 變更類型 | A2 HAST | A3 UHAST/AC | A4 TC | A4a TCHT | A5 IOL | B1 HTRB | B2 HTGB | C1 DPA | C2 PD | C3 WBP | C4 WBS | C5 DS | C6 TS | C7 RTS | C8 RSH | C9 TR | C10 SD | C11 WG | C12 CA | C13 VIB | C14 MS | C15 HER | D1 DI | E0 EV | E2 PV | E3/E4 ESD | E5 UIS | E6 SCC | NOTES |
|----------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Die Overcoat** | ● | ● | ● | | ● | ● | ● | ● | | ● | | | | | | | | | | | | H | | | | | | | |
| **LF Plating / Lead Finish** | C | C | C | | | | | | D | 2,C | | C | | D | | C | D | L | | | | H | | D | | | | | |
| **LF Material / Source** | ● | ● | ● | ● | ● | | | | ● | 2 | | ● | ● | | ● | ● | ● | L | | | | H | | ● | | | | ● | A,F,X |
| **Package / LF Dimension** | ● | | ● | | ● | | | | ● | | | ● | | | | ● | | L | | | | H | | | | | | ● | |
| **Wire Bonding** | ● | | ● | ● | ● | J | J | ● | | ● | ● | | | | ● | | | | | | | | | | ● | | | ● | |
| **Die Scribe / Separation** [*] | | | | | | | | | | | | ● | | | | | | | | | | | | | | | | | |
| **Die Preparation / Clean** [*] | | | | | | | | | | | | | | | | | | | | | | | | | | | | | X |
| **Die Attach** | ● | ● | ● | | ● | | | | | | | ● | | | ● | ● | | | | | | H | | | ● | | | ● | A,X |
| **Encapsulation Material** | ● | ● | ● | ● | ● | ● | ● | ● | ● | | | | | B | ● | ● | ● | | | | | H | ● | ● | ● | | | | A,F,G |
| **Encapsulation Process** [*] | | | | | | | | | | | | | | B | | | | L | | | | H | | | | | | | A,G |
| **Hermetic Sealing** [*] | H | H | H | | | | | H | | | | | H | | H | | | | H | H | H | H | | H | | | | | |
| **New Package** | ● | ● | ● | ● | ● | ● | ● | ● | ● | | | ● | ● | B | ● | ● | ● | L | H | H | H | H | ● | ● | ● | ● | | ● | |
| **Test Process / Sequence** [*] | | | | | | | | | | | | | | | | | | | | | | | | | | | | | |
| **Package Marking** [*] | | | | | | | | | | | | | | B | | | | | | | | | | | | | | | |
| **Assembly Site Transfer** | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | | ● | L | | | H | H | | ● | ● | | | | A,G,I,S,X |

> **[*]** = 此行僅有文字標記（無●），由 PDF 文字提取取得，未經像素掃描額外驗證。
> 無 [*] 標記的行已通過像素級驗證。

### 2.2 註解代碼對照

| 代碼 | 含義 |
|------|------|
| **A** | Acoustic Microscopy (SAT/AM) — 壓力測試前後分層掃描 |
| **B** | If not laser etched（非雷射打標時才需要） |
| **C** | Leadframe **Plating** change only（僅鍍層變更時） |
| **D** | Lead **Finish** change only（僅引腳表面處理變更時） |
| **E** | If Applicable（適用時） |
| **F** | Finite Element Analysis（有限元素分析） |
| **G** | 需提供封膠固化/shrinkage 相關數據 |
| **H** | **Hermetic part only**（僅氣密封裝適用） |
| **I** | Infant Mortality Rate（早期失效率） |
| **J** | **Change to Cu Wire → refer to AEC-Q006** |
| **L** | **Pb-free devices only**（僅無鉛元件適用） |
| **M** | Power MOS/IGBT parts only |
| **P** | CV Plot (MOS only) |
| **R** | Reliability data review |
| **S** | Steady State Mortality Rate |
| **X** | **X-Ray** 檢查 |
| **0** | Required for Schottky Barrier changes |
| **1** | If bond pads are affected |
| **2** | Verify post **package**（封裝後驗證） |

---

## 三、各變更類型詳解

### 3.1 Die Attach 變更（黏晶材料/製程）

**典型場景**：銀膠更換、燒結銀導入、導電膠→焊錫、D/A 溫度 profile 調整

#### 必須測試項目（依 Table 3 像素驗證結果）

| 測試 | 代號 | 標準 | 目的 |
|------|------|------|------|
| **HAST / H3TRB** | A2 | JESD22-A110/AEC-Q101-005 | 濕氣+偏壓下腐蝕耐受性 |
| **UHAST / Autoclave** | A3 | JESD22-A102/A118 | 無偏壓濕氣耐受性 |
| **Temperature Cycling** | A4 | JESD22-A104 | 熱機械應力下 D/A 完整性 |
| **IOL / PTC** | A5/alt | M1037 / JESD22-A105 | 功率循環下 D/A 疲勞 |
| **Die Shear** | C5 | MIL-STD-750 **M2017** | **核心測試** — D/A 黏著強度 |
| **Resist to Solder Heat** | C8 | JESD22-B106 | 焊接耐熱性 |
| **Thermal Resistance** | C9 | JESD24-3/4/6 | D/A 品質 → 熱傳導能力 |
| **Parametric Verification** | E2 | User spec | 電性驗證 |
| **Short Circuit Char.** | E6 | AEC-Q101-006 | 短路特性 |

#### 建議附加項目 (Notes A,X)

| 測試 | 說明 |
|------|------|
| **Acoustic Microscopy** (Note A) | SAT 分層檢測 — 壓力前後比較 |
| **X-Ray** (Note X) | 檢查 void — MIL-STD-750 M2076 |
| **H** | 氣密封裝時加做 C15 氣密測試 |

#### 關鍵判定標準

- Die Shear：依 M2017 Figure 2017-4（Die ≥ 4.129mm² → 最小 2.5 Kg）
- Thermal Resistance：Pre/Post 變更比較，不得惡化
- X-ray Void：Single < 10%, Total < 50%, Bonded ≥ 75%

---

### 3.2 Leadframe Plating / Lead Finish 變更

**典型場景**：鍍層更換（NiPdAu→純Sn）、鍍層厚度調整、無鉛轉換

#### 測試項目（依變更範圍分兩級）

**Plating change (Code C) — 鍍層變更**：

| 測試 | 代號 | 說明 |
|------|------|------|
| HAST / H3TRB | A2/alt | 濕氣 + 鍍層腐蝕耐受性 |
| UHAST / AC | A3/alt | 無偏壓濕氣 |
| Temperature Cycling | A4 | 鍍層 CTE 匹配 |
| Wire Bond Pull (post pkg) | C3 (Note 2,C) | 鍍層對 bond 強度影響 |
| Die Shear | C5 (Note C) | 鍍層對 D/A 影響 |
| Thermal Resistance | C9 (Note C) | 鍍層對散熱影響 |
| Solderability | C10 (Note D) | **關鍵** — 鍍層可焊性 |
| Whisker Growth | C11 (Note L) | **Pb-free 必做** — Sn whisker |

**Lead Finish change (Code D) — 引腳表面處理變更**：

| 測試 | 代號 | 說明 |
|------|------|------|
| Physical Dimensions | C2 (Note D) | 尺寸驗證 |
| Resist to Solvents | C7 (Note D) | 表面處理耐溶劑性 |
| Solderability | C10 (Note D) | **關鍵** — 可焊性 |
| External Visual | E0 (Note D) | 外觀檢查 |

---

### 3.3 Leadframe Material / Source 變更

**典型場景**：Cu→A42、C194→KFC、供應商更換（2nd Source）

> **重要修正 (2026-02-13)**：此行在 Table 3 中標記了完整的 Group A 壓力測試，
> 不僅僅是封裝/電性驗證。NOTES 欄為 A,F,X。

#### 必須測試項目（依 Table 3 像素驗證結果）

**Group A 壓力測試（全部 5 項）：**

| 測試 | 代號 | 標準 | 目的 |
|------|------|------|------|
| **HAST / H3TRB** | A2 | JESD22-A110/AEC-Q101-005 | 濕氣+偏壓下 LF 腐蝕 |
| **UHAST / Autoclave** | A3 | JESD22-A102/A118 | 無偏壓濕氣 |
| **Temperature Cycling** | A4 | JESD22-A104 | **關鍵** — LF/die CTE mismatch |
| **TCHT / TCDT** | A4a | JESD22-A104 variant | 高溫TC / 差溫TC |
| **IOL / PTC** | A5 | M1037 / JESD22-A105 | 功率循環疲勞 |

**Group C 封裝完整性測試：**

| 測試 | 代號 | 標準 | 目的 |
|------|------|------|------|
| **Physical Dimensions** | C2 | MIL-STD-750 M2066 | LF 尺寸驗證 |
| **Wire Bond Pull** (post pkg) | C3 (Note 2) | MIL-STD-750 M2037 | LF 對 bond pad 影響 |
| **Die Shear** | C5 | MIL-STD-750 M2017 | LF 材料對 D/A 影響 |
| **Terminal Strength** | C6 | MIL-STD-750 M2036 | **關鍵** — LF 機械強度 |
| **Resist to Solder Heat** | C8 | JESD22-B106 | 焊接耐熱性 |
| **Thermal Resistance** | C9 | JESD24-3/4/6 | LF 散熱能力 |
| **Solderability** | C10 | J-STD-002 | LF 可焊性 |
| **Whisker Growth** | C11 (Note L) | AEC-Q005 | Pb-free 元件晶鬚 |

**其他：**

| 測試 | 代號 | 標準 | 目的 |
|------|------|------|------|
| **External Visual** | E0 | MIL-STD-750 M2071/2072 | 外觀檢查 |
| **Short Circuit Char.** | E6 | AEC-Q101-006 | 短路特性 |

> **注意**：C1(DPA) 和 E2(PV) 在 Table 3 中**未標記**（像素比率 = 0.000）。
> 這與直覺不同，但已通過多次像素掃描確認。
> 實務上建議仍納入 DPA 和 PV 作為補充項目。

#### 附加要求 (Notes A,F,X)

| 附加 | 說明 |
|------|------|
| **A** | Acoustic Microscopy (SAT) — 壓力測試前後分層比較 |
| **F** | Finite Element Analysis — 評估 CTE mismatch |
| **X** | X-Ray 檢查 |

#### 與 LF Plating 的差異

| 維度 | LF Material/Source | LF Plating |
|------|-------------------|------------|
| Group A 壓力 | **● (全部 5 項，含 A4a)** | C (僅 A2-A4，條件式) |
| C5 Die Shear | ● | C (條件式) |
| C6 Terminal Str | **●** | - |
| C10 Solderability | ● | D (條件式) |
| E0 External Visual | ● | D (條件式) |
| E6 Short Circuit | **●** | - |
| NOTES | **A,F,X** | - |

---

### 3.4 Wire Bonding 變更

**典型場景**：線徑變更、打線參數調整、設備更換

#### Au/Al Wire 變更 — 必須測試項目（依像素驗證）

| 測試 | 代號 | 標準 | 說明 |
|------|------|------|------|
| HAST / H3TRB | A2 | JESD22-A110 | IMC/腐蝕 |
| Temperature Cycling | A4 | JESD22-A104 | IMC 成長與 bond 退化 |
| TCHT / TCDT | A4a | JESD22-A104 variant | 高溫TC |
| IOL / PTC | A5 | M1037 | 功率循環 |
| DPA | C1 | AEC-Q101-004 | 破壞性分析 |
| **Wire Bond Pull** | C3 | MIL-STD-750 **M2037** | **核心測試** |
| **Wire Bond Shear** | C4 | AEC-Q101-003A | **核心測試** |
| Resist to Solder Heat | C8 | JESD22-B106 | 耐焊熱 |
| Parametric Verification | E2 | User spec | 電性驗證 |
| Short Circuit Char. | E6 | AEC-Q101-006 | 短路特性 |

#### Cu Wire 變更 (Note J) — 轉移至 AEC-Q006

| 情境 | 要求 |
|------|------|
| Au → Cu 首次導入 | **完整 Q006 Table 3 流程** |
| Cu wire 供應商變更 | Q006 Table 3 |
| Cu wire 規格變更 | Q006 Table 3 |
| 已驗證 Cu wire 擴展 (Case 5) | 1 lot TC up to item #10 |

> **重要**：Cu wire 變更**不執行** A4a/A4a alt (TCHT/TCDT)，改依 Q006 流程

---

### 3.5 Encapsulation Material 變更（封膠材料）

**典型場景**：Mold compound 供應商更換、配方調整、低 CTE EMC 導入

#### 必須測試項目（依像素驗證）

| 測試 | 代號 | 說明 |
|------|------|------|
| HAST / H3TRB | A2 | 濕氣耐受性 |
| UHAST / Autoclave | A3 | 無偏壓濕氣 |
| Temperature Cycling | A4 | EMC CTE vs LF/die 匹配 |
| TCHT / TCDT | A4a | 高溫TC |
| IOL / PTC | A5 | 功率循環 |
| HTRB | B1 | 高溫逆偏 |
| HTGB | B2 | 高溫閘偏 |
| DPA | C1 | 破壞性分析 |
| Physical Dimensions | C2 | 封膠後尺寸 |
| Resist to Solvents | C7 (Note B) | 非雷射打標時 |
| Resist to Solder Heat | C8 | 耐焊熱 |
| Thermal Resistance | C9 | EMC 熱傳導影響 |
| Solderability | C10 | 可焊性 |
| Dielectric Integrity | D1 | 介電強度 |
| External Visual | E0 | 外觀 |
| Parametric Verification | E2 | 電性驗證 |

#### 建議附加項目 (Notes A,F,G)

| 測試 | 說明 |
|------|------|
| **A** | SAT — 封膠/LF/die 分層 |
| **F** | FEA — CTE mismatch 模擬 |
| **G** | 封膠固化/shrinkage 數據 |

---

### 3.6 Encapsulation Process 變更（封膠製程）

**典型場景**：壓模參數調整、後固化溫度/時間調整

#### 必須測試項目 [*未經像素掃描驗證]

| 測試 | 代號 | 說明 |
|------|------|------|
| Resist to Solvents | C7 (Note B) | 非雷射打標時 |
| Whisker Growth | C11 (Note L) | Pb-free 元件 |

---

### 3.7 New Package（新封裝導入）

**最全面的測試要求** — 幾乎涵蓋所有 Table 2 測試

#### 必須測試項目（依像素驗證）

| 群組 | 測試項目 |
|------|---------|
| **Group A** | HAST(A2), UHAST/AC(A3), TC(A4), TCHT(A4a), IOL/PTC(A5) |
| **Group B** | HTRB(B1), HTGB(B2) |
| **Group C** | DPA(C1), PD(C2), DS(C5), TS(C6), RTS(C7-B), RSH(C8), TR(C9), SD(C10), WG(C11-L) |
| **Group D** | DI(D1) |
| **Group E** | EV(E0), PV(E2), ESD(E3/E4), SCC(E6) |

> **氣密封裝額外**：C12 CA(H), C13 VIB(H), C14 MS(H), C15 HER(H)

---

### 3.8 Assembly Site Transfer（封裝廠轉移）

**第二全面的測試要求** — 確保新廠製程一致性

#### 必須測試項目（依像素驗證）

| 群組 | 測試項目 |
|------|---------|
| **Group A** | HAST(A2), UHAST/AC(A3), TC(A4), TCHT(A4a), IOL/PTC(A5) |
| **Group B** | HTRB(B1), HTGB(B2) |
| **Group C** | DPA(C1), PD(C2), WBP(C3), WBS(C4), DS(C5), TS(C6), RTS(C7), RSH(C8), SD(C10), WG(C11-L) |
| **Group E** | EV(E0), PV(E2) |

#### 附加要求 (Notes)

| 附加 | 說明 |
|------|------|
| **A** | Acoustic Microscopy (SAT) |
| **G** | 封膠相關數據 |
| **I** | Infant Mortality Rate 比較 |
| **S** | Steady State Mortality Rate 比較 |
| **X** | X-Ray 檢查 |

---

## 四、Qualification Family 定義 (Appendix 1)

### 4.1 基本原則

- 同一 Family 的產品必須共享**相同的主要製程和材料要素**
- 經由 Family 中一個成員成功完成認證，同 Family 其他成員可**藉由關聯 (by association)** 獲得資格
- 例外：**元件專屬測試 (Section 4.2)** 必須在特定元件上執行（ESD、PV）

### 4.2 Assembly Process Family 定義屬性 (A1.2)

#### A1.2.1 Package Type

- 封裝類型（如 TO-220, SOT-23, DO-41, SOIC 等）
- **Paddle (flag) size** 範圍需涵蓋待認證的 die size / aspect ratio

#### A1.2.2 Assembly Process — 定義 Family 的關鍵屬性

| # | 屬性 | 影響 |
|---|------|------|
| 1 | **Leadframe base material** | CTE、強度、導電/導熱 |
| 2 | **Leadframe plating** (internal and external) | 可焊性、bond 品質、耐蝕性 |
| 3 | **Die attach material / method** | 黏著強度、散熱、電性 |
| 4 | **Wire bond material, wire diameter, and process** | 接合強度、電流承載 |
| 5 | **Plastic mold compound or other encapsulation material** | 濕氣保護、CTE 匹配 |

> **任一屬性變更** → 需要 Family 重新認證（依 Table 3 對應測試）

### 4.3 Worst-Case Test Vehicle 策略 (Section 2.3)

當變更涉及多個屬性（如場地+材料+製程）時：
- 可選擇 **worst-case test vehicles** 涵蓋所有排列組合
- 最大 die size、最多打線數、最薄封裝 → 最敏感配置
- 通過 worst case = 覆蓋所有較不嚴苛的配置

---

## 五、變更類型快速決策矩陣

### 5.1 按影響範圍排列（由大到小）

| 排名 | 變更類型 | 測試範圍 | 估計週期 |
|------|---------|---------|---------|
| 1 | **New Package** | A2-A5, B1-B2, C1-C2/C5-C11, D1, E0-E4, E6 | 12-16 週 |
| 2 | **Assembly Site Transfer** | A2-A5, B1-B2, C1-C8/C10-C11, E0/E2 | 12-16 週 |
| 3 | **Encapsulation Material** | A2-A5, B1-B2, C1-C2/C7-C10, D1, E0/E2 | 10-14 週 |
| 4 | **LF Material/Source** | **A2-A5(含A4a), C2-C3/C5-C6/C8-C10, E0/E6** | **10-14 週** |
| 5 | **Die Attach** | A2-A4, A5, C5/C8-C9, E2/E6 | 10-14 週 |
| 6 | **Die Overcoat** | A2-A5, B1-B2, C1/C3 | 8-12 週 |
| 7 | **Leadframe Plating** | A2-A4(C), C3/C5/C9/C10/C11 | 8-12 週 |
| 8 | **Wire Bonding (→Cu)** | **Q006 完整流程** | 12-20 週 |
| 9 | **Wire Bonding (Au/Al)** | A2/A4-A5, C1/C3-C4/C8, E2/E6 | 8-12 週 |
| 10 | **Package/LF Dimension** | A2/A4-A5, C2/C5/C9, E6 | 8-10 週 |
| 11 | **Encapsulation Process** | C7/C11 | 4-6 週 |
| 12 | **Lead Finish only** | C2/C7/C10, E0 | 2-4 週 |

### 5.2 按原物料類型分類

| 原物料 | 對應變更類型 | 核心測試 | 關鍵注意 |
|--------|------------|---------|---------|
| **銀膠/焊錫 (D/A)** | Die Attach | A2-A4, C5(DS), C9(TR), E2 | SAT, X-ray void |
| **金線 (Au wire)** | Wire Bonding | A2/A4/A4a/A5, C1/C3/C4 | M2037 Table 2037-I |
| **鋁線 (Al wire)** | Wire Bonding | A2/A4/A4a/A5, C1/C3/C4 | M2037 Table 2037-I |
| **銅線 (Cu wire)** | Wire Bonding (J) | **AEC-Q006 全套** | 不走 Table 3 |
| **腳架 (LF base)** | LF Material | **A2-A5(含A4a), C2/C3/C5/C6/C8-C10, E0/E6** | **壓力測試全套! SAT+FEA+X-ray** |
| **腳架鍍層 (LF plating)** | LF Plating | A2-A4(C), C3/C5/C9/C10 | 可焊性是關鍵 |
| **封膠 (EMC)** | Encap. Material | A2-A5, B1-B2, C1/C2/C7-C10, D1, E0/E2 | SAT, CTE |
| **引腳表面 (Lead Finish)** | Lead Finish | C2/C7/C10, E0 | 可焊性、外觀 |

---

## 六、與其他標準的交叉引用

### 6.1 Q006 觸發條件（Cu Wire 專用）

Table 3 中 **Note J** 出現在 Wire Bonding 行的 B1 和 B2 欄位：
- B1 HTRB → **AEC-Q006**
- B2 HTGB → **AEC-Q006**

Q006 完整流程見：`../reliability-testing/SKILL.md` (Q006 Section)

### 6.2 Q005 觸發條件（Whisker Growth）

Table 3 中 **Note L** 出現在 C11 欄位：
- Pb-free 元件的 LF Plating、LF Material、Package Dimension、Encap Process、New Package、Assembly Site Transfer 均需 Whisker Growth Evaluation
- 依 **AEC-Q005** 執行

### 6.3 MIL-STD 方法引用

| Q101 Test | Method | 詳細參考 |
|-----------|--------|---------|
| C3 WBP | MIL-STD-750 M2037 | `../mil-std-750/references/method-2037-bond-strength.md` |
| C4 WBS | AEC-Q101-003A | `test-methods-detail.md` |
| C5 DS | MIL-STD-750 M2017 | `../mil-std-750/references/method-2017-die-shear.md` |
| C6 TS | MIL-STD-750 M2036 | Terminal Strength |
| C9 TR | JESD24-3/4/6 | Thermal Resistance |
| C10 SD | J-STD-002 | Solderability |

---

## 七、實務建議

### 7.1 變更計畫準備

1. **識別變更範圍**：確定 Table 3 中哪些行受影響
2. **疊加測試項目**：多個行的測試項目取聯集
3. **應用 Family 概念**：選擇 worst-case test vehicle
4. **與客戶溝通**：提交 Qualification Test Plan

### 7.2 常見組合變更

| 情境 | 涉及的 Table 3 行 | 測試策略 |
|------|-------------------|---------|
| LF 供應商更換（同材質同鍍層） | LF Material/Source | **A2-A5, C2/C3/C5/C6/C8-C10/C11(L), E0/E6** + Notes A,F,X |
| LF 供應商更換（不同鍍層） | LF Material + LF Plating | 聯集（壓力測試升級為無條件●） |
| D/A 材料更換 + 封膠更換 | Die Attach + Encap Material | 聯集：A2-A5, B1/B2, C1/C2/C5/C7-C10, D1, E0/E2/E6 |
| 封裝廠轉移（全製程） | Assembly Site Transfer | 幾乎全套（最大範圍） |
| Au → Cu wire | Wire Bonding (J) | **Q006 全套**（不走 Table 3） |

### 7.3 測試報告要點

| 項目 | 要求 |
|------|------|
| Pre/Post 比較 | 所有電性和物理參數 |
| 失效分析 | 所有失效品 root cause |
| 統計數據 | Mean, σ, Cpk（如適用） |
| 通過準則 | 0 failures / 231 pcs (77×3) |
| Family 適用說明 | 技術理由文件化 |
| 客戶簽核 | Qualification Test Plan Agreement |

---

## 附錄：Table 3 像素級驗證方法 (2026-02-13)

### 驗證流程

1. **渲染**：使用 PyMuPDF 將 PDF Page 22 渲染為 300 DPI 影像 (2550x3300 px)
2. **網格偵測**：掃描垂直/水平暗像素線 → 識別 33 個欄位邊界 + 47 個行邊界
3. **文字定位**：用 `page.search_for()` 定位每行標籤的像素座標
4. **欄位校準**：以 LF Plating 行的已知文字標記 (C/D/2,C/L/H) 交叉驗證欄位對齊
5. **像素掃描**：對每個儲存格中心 70% 區域掃描暗像素（brightness < 100）

### 判定標準

| 比率範圍 | 判定 | 說明 |
|----------|------|------|
| > 0.10 | ● 確認 | 與已知 DOT 行的比率一致 (0.15-0.21) |
| 0.07-0.10 | 文字標記 | 對應 C/D/L/H/B/J 等字母 |
| 0.03-0.07 | 需個案判斷 | 可能是小字或邊界效應 |
| < 0.03 (特別是 0.0465 均勻值) | 網格線殘影 | 忽略 |
| 0.0000 | 確認空白 | 無任何內容 |

### 原始錯誤原因

先前版本使用 PyMuPDF `find_tables()` + `get_text()` 提取表格，但：
- Table 3 的 ● 符號是**向量圖形**（填充圓），非文字字元
- 文字提取只能捕獲字母/數字標記，系統性遺漏所有 ● 標記
- `find_tables()` 的儲存格座標因表格旋轉佈局而嚴重偏移

---

## 來源文件

| 文件 | 頁碼 | 內容 |
|------|------|------|
| AEC-Q101 Rev E p.4 (Table 1) | Page 8 | Part Qualification/Re-qualification Lot Requirements |
| AEC-Q101 Rev E p.7 (Sec 3.2) | Page 11 | Re-qualification of a Changed Part |
| AEC-Q101 Rev E p.18 (Table 3) | **Page 22** | **Process Change Guidelines — 完整測試矩陣** |
| AEC-Q101 Rev E p.19-20 (App 1) | Pages 23-24 | **Qualification Family Definition** |
| AEC-Q101 Rev E p.8 (Sec 4) | Page 12 | Qualification Tests 總則 |
