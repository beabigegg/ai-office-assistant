---
name: mil-std-750
description: |
  MIL-STD-750 半導體離散元件測試方法標準完整知識庫。適用於：
  查詢離散元件（二極體/電晶體/MOSFET/閘流體）的環境、機械、電氣測試方法、
  判斷 AEC-Q101 引用的對應 MIL-STD-750 方法編號、
  區分 MIL-STD-750（離散）與 MIL-STD-883（IC）的適用範圍。
  當任務涉及 MIL-STD-750、離散元件測試方法、Die Shear、Bond Strength、
  Temperature Cycling、HTRB、Burn-in、環境測試、電氣特性測試時觸發。
triggers:
  - MIL-STD-750, MIL-STD-883, 離散元件測試, 測試方法
  - Die Shear, M2017, Bond Strength, M2037, Bond Pull
  - Die Attach Void, M2076, X-ray, 空洞率
  - Terminal Strength, M2036, Temperature Cycling, M1051
  - HTRB, M1038, M1039, Burn-in, 穩態壽命
  - MOSFET測試, 二極體測試, 電晶體測試, 閘流體測試
  - PIND, M2052, Hermetic Seal, M1071
---

# MIL-STD-750 — 半導體離散元件測試方法標準

> **標準全名**：Department of Defense Test Method Standard: Test Methods for Semiconductor Devices
> **最新版本**：MIL-STD-750F (2012-01-03) with Change 2 (2016-11-30)
> **最後更新**：2026-02-12

---

## Lazy Loading 路由表

| 問題類型 | 讀取 |
|---------|------|
| Part 1-5 完整方法編號清單 | `references/complete-test-methods.md` |
| Die Shear (M2017) 詳細規格、Figure 2017-4 數值、失效判定 | `references/method-2017-die-shear.md` |
| Bond Strength (M2037) 詳細規格、Table 2037-I、失效類別 | `references/method-2037-bond-strength.md` |
| Die Attach Void (M2076/M2074/M3101/M2017-B) + **M2076.7 提案** | `references/die-attach-void-specs.md` |
| Cougar EVO X-ray vs M2076 符合性分析 | `references/x-ray-cougar-evo-compliance.md` |

---

## 標準結構

| Part | 編號範圍 | 主題 | 最新版本 |
|------|---------|------|---------|
| **750-F** | - | 基礎文件（範圍、定義、通用要求） | 2016-11-30 |
| **750-1** | 1000-1999 | 環境測試 (34 methods) | 2023-04-18 |
| **750-2** | 2000-2999 | 機械特性測試 (31 methods) | 2023-06-23 |
| **750-3** | 3000-3999 | 電晶體電氣測試 | 2019-12-09 |
| **750-4** | 4000-4999 | 二極體電氣測試 | 2023-05-16 |
| **750-5** | 5000-5999 | 高可靠太空應用 | 2018-08-10 |

---

## 與 MIL-STD-883 的區分

| 項目 | MIL-STD-750 | MIL-STD-883 |
|------|-------------|-------------|
| **適用對象** | 離散半導體 (Discrete) | IC / 微電路 (Microcircuits) |
| **Die Shear** | Method **2017** | Method **2019** |
| **Bond Pull** | Method **2037** | Method **2011** |
| **溫度循環** | Method **1051** | Method **1010** |
| **穩態壽命** | Method **1026** | Method **1005** |
| **密封測試** | Method **1071** | Method **1014** |

---

## AEC-Q101 引用的 MIL-STD-750 方法對照

| Q101 項目 | 代號 | 測試名稱 | MIL-STD-750 Method |
|-----------|------|---------|-------------------|
| A5 | IOL | Intermittent Operational Life | **M1037** |
| B1 | HTRB | High Temperature Reverse Bias | **M1038** / **M1039** |
| B1a | ACBV | AC Blocking Voltage | **M1040** |
| B1b | SSOP | Steady State Operational | **M1038 Cond.B** |
| C3 | WBP | Wire Bond Pull | **M2037** |
| C5 | DS | Die Shear | **M2017** |
| C6 | TS | Terminal Strength | **M2036** |

---

## 關鍵方法速查

| 用途 | Method | 備註 |
|------|--------|------|
| Die Shear | **2017** | Die Area ≥4.129mm² → min 2.5Kg。詳見 `references/method-2017-die-shear.md` |
| Bond Pull | **2037** | Au 1.0mil: Preseal 3.0gf, Post seal 2.5gf。Q101 C3 要求 TC 後 min 3gf |
| Die Attach Void (X-ray) | **2076** | 舊版: Single >10%, Total >50%. **提案 2076.7: Power >15%, Others >30%, GaN 逐點 <15%** |
| Die Attach Void (Thermal) | **3101** | 統計法 mean + 3σ |
| Terminal Strength | **2036** | Through-hole leaded parts only |
| MOSFET Burn-in | **1042** | Power MOSFET/IGBT 專用 |
| Diode Burn-in | **1038** | 含 Rectifier/Zener |
| Transistor Burn-in | **1039** | BJT |
| Thyristor Burn-in | **1040** | SCR |
| Hermetic Seal | **1071** | 氣密性測試 |
| Temperature Cycling | **1051** | Q101 A4 引用 JESD22-A104 |
| PIND | **2052** | 粒子衝擊噪音偵測 |

---

## 來源

| 來源 | 說明 |
|------|------|
| [DLA Land & Maritime](https://landandmaritimeapps.dla.mil/Programs/MilSpec/listdocs.aspx?BasicDoc=MIL-STD-750) | 官方最新版本 |
| [NASA SSRI-KB](https://s3vi.ndc.nasa.gov/ssri-kb/static/resources/MIL-STD-750F_CHG-2.pdf) | MIL-STD-750F CHG-2 PDF |

---

## 修訂記錄

| 日期 | 內容 |
|------|------|
| 2026-02-09 | 初始建立，含 Part 1-5 完整方法清單 |
| 2026-02-09 | M2017 Die Shear 詳細規格、Die Attach Void 規範彙整 |
| 2026-02-09 | Cougar EVO X-ray vs M2076 符合性分析 |
| 2026-02-12 | M2037 Bond Strength 完整規格 |
| 2026-02-12 | **瘦身**：Part 1/2 方法清單移至 complete-test-methods.md，詳細規格保留在各 reference |
| 2026-02-13 | **M2076.7 提案修訂**：EP Study 5961-2025-111 (GaN flip-chip + void 加嚴) 納入 die-attach-void-specs.md |
