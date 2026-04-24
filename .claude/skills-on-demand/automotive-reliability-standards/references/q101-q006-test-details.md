# AEC-Q101 / Q006 完整測試項目與條件

> **來源**：AEC-Q101 Rev E (2021-03-01) + AEC-Q006 Rev B (2025-06-30) 官方 PDF
> **最後更新**：2026-02-12

---

## AEC-Q101 Rev E 完整測試項目清單

### Test Group A — 加速環境應力測試 (Accelerated Environment Stress Tests)

| # | ABV | 測試名稱 | 參考標準 | 樣品數 | 條件摘要 |
|---|-----|---------|---------|--------|---------|
| A1 | **PC** | Preconditioning | J-STD-020 + JESD22-A113 | 隨後續測試 | SMD 前處理，3x reflow，TEST before/after PC |
| A2 | **HAST** | Highly Accelerated Stress Test | JESD22-A110 | 77×3 | 130°C/85%RH/**96h** 或 110°C/85%RH/264h，80% Vr (≤42V)，有偏壓 |
| A2 alt | **H3TRB** | High Humidity High Temp Reverse Bias | JESD22-A101 | 77×3 | **85°C/85%RH/1000h**，80% VBR (≤100V)，有偏壓 |
| A3 | **UHAST** | Unbiased HAST | JESD22-A118 or A101 | 77×3 | 130°C/85%RH/**96h** 或 110°C/85%RH/264h，無偏壓 |
| A3 alt | **AC** | Autoclave | JESD22-A102 | 77×3 | **121°C/100%RH/15psig/96h**，無偏壓 |
| A4 | **TC** | Temperature Cycling | JESD22-A104 App.6 | 77×3 | **1000 cycles**，-55°C ~ Tj max (≤150°C)，或 400c @ Tj+25°C |
| A4a | **TCHT** | TC Hot Test | JESD22-A104 App.6 | 77×3 | TC 後 125°C 電測 + decap + WBP (wire ≤5mil) |
| A4a alt | **TCDT** | **TC Delamination Test** | JESD22-A104 + J-STD-035 | 77×3 | **TC 後 100% SAT 掃描，5 highest delam parts decap + WBS** |
| A5 | **IOL** | Intermittent Operational Life | MIL-STD-750 M1037 | 77×3 | ΔTj ≥ 100°C，依 Table 2A 計算 cycles |
| A5 alt | **PTC** | Power Temperature Cycling | JESD22-A105 | 77×3 | 若 IOL 無法達 ΔTj 100°C，改用 PTC |

> **Note 2**: A4a/A4a alt (TCHT/TCDT) **不適用** Cu wire bonded products → follow AEC-Q006
> **Note 3**: Cu wire parts → follow **AEC-Q006**

### Test Group B — 加速壽命模擬測試 (Accelerated Lifetime Simulation Tests)

| # | ABV | 測試名稱 | 參考標準 | 樣品數 | 條件摘要 |
|---|-----|---------|---------|--------|---------|
| B1 | **HTRB** | High Temperature Reverse Bias | MIL-STD-750 M1038/1039 | 77×3 | Tj max, Vr=100% Vr max, **1000h** |
| B1a | **ACBV** | AC Blocking Voltage | MIL-STD-750 M1040 | 77×3 | Thyristors only, AC VBR max, **1000h** |
| B1b | **SSOP** | Steady State Operational | MIL-STD-750 M1038 cond.B | 77×3 | Zeners only, Iz max, **1000h** |
| B2 | **HTGB** | High Temperature Gate Bias | JESD22-A108 | 77×3 | Tj max, Vgs=100%, **1000h** 或 500h @ Tj+25°C |

> **HTRB Note X (Schottky)**：thermal runaway 可能發生。需調整 Ta 以達成最大 Tj 而不進入 runaway。

### Test Group C — 封裝組裝完整性測試 (Package Assembly Integrity Tests)

| # | ABV | 測試名稱 | 參考標準 | 樣品數 | 條件摘要 |
|---|-----|---------|---------|--------|---------|
| C1 | **DPA** | Destructive Physical Analysis | AEC Q101-004 Sec.4 | 2×1 | Random sample from H3TRB/HAST + TC 完成品 |
| C2 | **PD** | Physical Dimensions | JESD22-B100 | 30×1 | Verify to user packaging spec |
| C3 | **WBP** | Wire Bond Pull | **MIL-STD-750-2 M2037** (Au/Al) / **AEC Q006** (Cu) | 10 bonds from ≥5 pcs | Cond. C or D，Au wire ≥1mil: min 3g after TC |
| C4 | **WBS** | Wire Bond Shear | **AEC Q101-003** / **JESD22-B116** (Cu) | 同上 | 詳見 AEC Q101-003 |
| C5 | **DS** | Die Shear | **MIL-STD-750-2 M2017** | 5×1 | Pre/Post process change comparison |
| C6 | **TS** | **Terminal Strength** | **MIL-STD-750-2 M2036** | 30×1 | **Through-hole leaded parts only** |
| C7 | **RTS** | Resistance to Solvents | JESD22-B107 | 30×1 | Verify marking permanency (耐溶劑/印字耐久) |
| C8 | **RSH** | Resistance to Solder Heat | JESD22-A111 (SMD) / B106 (PTH) | 30×1 | TEST before/after |
| C9 | **TR** | Thermal Resistance | JESD24-3/4/6 | 10×1 | Measure TR to spec |
| C10 | **SD** | Solderability | **J-STD-002** | 10×1 | 50x magnification |
| C11 | **WG** | Whisker Growth Evaluation | AEC-Q005 | - | Family basis |
| C12-C15 | **CA/VVF/MS/HER** | Mechanical Tests | Various | 30×1 | **Hermetic packages only** |

### Test Group D — 晶圓製造可靠性測試

| # | ABV | 測試名稱 | 參考標準 | 樣品數 |
|---|-----|---------|---------|--------|
| D1 | **DI** | Dielectric Integrity | AEC Q101-004 Sec.3 | 5×1 (Power MOS/IGBT only) |

### Test Group E — 電性驗證測試

| # | ABV | 測試名稱 | 參考標準 | 樣品數 |
|---|-----|---------|---------|--------|
| E0 | **EV** | External Visual | JESD22-B101 | All |
| E1 | **TEST** | Pre/Post Stress Electrical | User spec | All |
| E2 | **PV** | Parametric Verification | User spec | 25×3 |
| E3 | **ESDH** | ESD HBM Characterization | AEC Q101-001 | 30×1 |
| E4 | **ESDC** | ESD CDM Characterization | AEC Q101-005 | 30×1 |
| E5 | **UIS** | Unclamped Inductive Switching | AEC Q101-004 Sec.2 | 5×1 |
| E6 | **SC** | Short Circuit Characterization | AEC Q101-006 | 10×3 |

---

## 失效定義 (Section 2.4)

| 條件 | 失效標準 |
|------|---------|
| 電性參數 | 不符合 user spec 或 supplier spec |
| 參數漂移 | > ±20% of initial reading |
| 漏電 (moisture tests) | > 10× initial value |
| 漏電 (other tests) | > 5× initial value |
| MOSFET (IGSS/IDSS) | 0h <10nA → allowed 100nA (moisture) / 50nA (others) |
| RDSon (IOL/PTC/TC) | ≤2.5mΩ parts: allowed shift = 0.5mΩ |
| BV shift | >20% 但 final > 80% of datasheet max → not a failure |

---

## 樣品數與允收標準

| 測試類型 | 樣品數 | Lots | 允收標準 |
|---------|--------|------|---------|
| Group A/B 環境/壽命 | 77 pcs | 3 lots | **0 failures** |
| C3/C4 WBS/WBP | 10 bonds from ≥5 pcs | - | Per spec |
| C5 DS | 5 pcs | 1 lot | 0 failures |
| C6 TS | 30 pcs | 1 lot | 0 failures |
| E2 PV | 25 pcs | 3 lots | - |
| E3/E4 ESD | 30 pcs | 1 lot | - |

77 pcs × 3 lots = 231 pcs，零失敗 → 90% CL 下真實不良率 ≤ ~1400 ppm

---

## AEC-Q006 Rev B 銅線驗證規範

### 適用範圍

- Au → Cu Wire（含 coated Cu 和 CuA 合金）
- 新產品使用 Cu Wire
- Cu Wire 供應商/規格變更

### Q006 兩個驗證選項

| Option | 描述 | 測試序列 |
|--------|------|---------|
| **Option 1** | 1X stress + 詳細 analytical tests | Items 1-11 |
| **Option 2** | 2X stress duration | Items 1-7, 12, 13 |

### Q006 Table 3 測試序列

| # | 步驟 | TC | HAST/THB/H3TRB | HTSL/HTGB/HTRB | Opt 1 | Opt 2 |
|---|------|-----|----------------|------|-------|-------|
| 1 | Initial sampling | as req | as req | as req | ● | ● |
| 2 | AM @ T0 | as req | as req | --- | ● | ● |
| 3 | PC to MSLx | 3×77 | 3×77 | --- | ● | ● |
| 4 | AM after PC | 3×11 | --- | --- | ● | ● |
| 5 | ATE Test | 3×77 | 3×77 | 3×45 | ● | ● |
| 6 | **Stress 1X** | 3×77 | 3×77 | 3×45 | ● | ● |
| 7 | ATE Test | 3×77 | 3×77 | 3×45 | ● | ● |
| 8 | AM post-1X | 3×11 | --- | --- | ● | - |
| 9 | SEM (stitch) | 3×1 | --- | --- | ● | - |
| 10a | Ball+Stitch pull | 3×3 | 3×3 | --- | ● | - |
| 10b | Ball shear | 3×3 | 3×3 | 3×3 | ● | - |
| 11 | Cross-section | 3×1 | 3×1 | 3×1 | ● | - |
| 12 | **Stress 2X** | 3×77 | 3×77 | 3×45 | ○ | ● |
| 13 | ATE Test | 3×77 | 3×77 | 3×45 | ○ | ● |

### Q006 1X Release Criteria (Section 7.2.1)

**TC 後**：AM no delam, SEM no heel cracks, WBS 禁 Bond lift/Cratering, WBP 只允許 wire breaks, Cross-section no BEoL cracks

**HAST/THB 後**：WBS 禁 Bond lift/Cratering, WBP 只允許 wire breaks, Cross-section assess corrosion

**HTSL/HTGB/HTRB 後**：WBS 禁 Bond lift/Cratering, WBS force > T0 AND > 50% T0 min, Stitch pull assess corrosion
> **注意**：Q006 Rev B 第三支腿允許 HTSL、HTGB 或 HTRB，依產品類型選用（Rectifier→HTRB, MOSFET/IGBT→HTGB, 通用→HTSL）。三者皆可加速 Cu/Al 界面 IMC 成長。

> **WBS/WBP = 0 gf → FAIL**，禁止繼續 2X stress

### Q006 Technology Family Criteria (Table 2)

| Case | Die 屬性 | Package 屬性 | Assembly Site | 要求 |
|------|---------|-------------|---------------|------|
| 1 | different | different | different | Q006 Table 3, 3 lots |
| 2a | different bond pad material | same | same | Q006 Table 3, 3 lots |
| 2b | die diagonal >115% | same | same | TC only, 3 lots |
| 2c | different dielectric under pad | same | same | TC only, 3 lots |
| 3a | same | different mold compound | same | Q006 Table 3, 3 lots |
| 3b | same | different bond wire | same | Q006 Table 3, 3 lots |
| 3c | same | different LF surface | same | Q006 Table 3, 3 lots |
| 3d | same | different package type | same | Q006 Table 3, 3 lots |
| 4a | same | same | **different site** | Q006 Table 3, 3 lots |
| 5 | die diagonal <115% | same | same | 1 lot TC up to item #10 |

### Q006 Grade 0 特殊要求

- self-heating >10°C → HTSL 必須 175°C
