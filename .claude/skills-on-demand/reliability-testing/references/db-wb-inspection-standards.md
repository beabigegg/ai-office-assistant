# Die Bonding (DB) & Wire Bonding (WB) 檢驗規範完整彙整

> **來源**：AEC-Q101 Rev E, AEC-Q006 Rev B, AEC-Q101-003A, MIL-STD-750D, MIL-STD-883
> **最後更新**：2026-02-12

---

## 一、Die Bonding (DB) 檢驗規範

### 1.1 適用標準總覽

| 檢驗方法 | 標準 | Method | 破壞性 | 用途 |
|---------|------|--------|--------|------|
| Die Shear | MIL-STD-750 | **M2017** | 破壞 | AEC-Q101 C5 認證 |
| Die Shear (IC) | MIL-STD-883 | **M2019** | 破壞 | IC 元件認證 |
| X-ray Void | MIL-STD-750 | **M2076** | 非破壞 | 產線 inline 檢查 |
| Thermal Impedance | MIL-STD-750 | **M3101** | 非破壞 | Die attach screening |
| Internal Visual | MIL-STD-750 | **M2074** | 破壞 | DPA / 失效分析 |
| Mechanical Impact | MIL-STD-750 | **M2017-B** | 破壞 | 大型 die (≥161mm²) |
| SAT (Acoustic) | J-STD-035 / Internal | - | 非破壞 | 分層檢測 |

### 1.2 Die Shear Test — MIL-STD-750 M2017（離散元件）

**詳細規格**：見 `../mil-std-750/references/method-2017-die-shear.md`

#### 最小剪切力速查

| Die Area (mm²) | 1.0X Min (Kg) | 2.0X Pass (Kg) |
|----------------|---------------|-----------------|
| 0.323 | 0.15 | 0.30 |
| 0.645 | 0.35 | 0.70 |
| 1.290 | 0.70 | 1.40 |
| 1.935 | 1.05 | 2.10 |
| 3.226 | 1.75 | 3.50 |
| **≥ 4.129** | **2.50 (固定)** | **5.00** |

#### 合格/失效判定（四級）

| 條件 | 力量 | 附著面積 | 判定 |
|------|------|---------|------|
| A | < 1.0X | 不論 | **FAIL** |
| B | < 1.25X | < 50% | **FAIL** |
| C | < 1.5X | < 25% | **FAIL** |
| D | < 2.0X | < 10% | **FAIL** |
| - | ≥ 2.0X 未剪斷 | - | **PASS** |

#### 分離類別與診斷

| 類別 | 描述 | 診斷方向 |
|------|------|---------|
| a | Die 剪斷，基板有殘矽 | 正常良好，最佳結果 |
| b | Die 從 D/A 材料脫離 | D/A 材料或溫度 profile 問題 |
| c | Die + D/A 一起從封裝脫離 | LF 表面處理 / plating 問題 |

### 1.3 Die Shear Test — MIL-STD-883 M2019（IC 元件）

#### 最小剪切力（三區段）

| Die Area | 計算方式 | 1.0X 最小力 |
|---------|---------|------------|
| < 5×10⁻⁴ in² (< 0.323 mm²) | 0.04 kg / 10⁻⁴ in² | 按面積線性計算 |
| 5~64 × 10⁻⁴ in² (0.323~4.129 mm²) | Figure 2019-4 曲線 | 約 0.04 kg/10⁻⁴ in² |
| > 64×10⁻⁴ in² (> 4.129 mm²) | **固定值** | **2.5 Kg** |

#### 失效判定（與 M2017 一致）

| 條件 | 力量 | 附著面積 | 判定 |
|------|------|---------|------|
| 1 | < 1.0X (Figure 2019-4) | 不論 | **FAIL** |
| 2 | < 1.25X | < 50% adhesion | **FAIL** |
| 3 | < 2.0X | < 10% adhesion | **FAIL** |

> **M2017 vs M2019 差異**：M2017 有四級（多 Condition C: <1.5X + <25%），M2019 只有三級。
> 數值門檻和曲線形狀基本一致。

### 1.4 X-ray Void 檢查 — MIL-STD-750 M2076

**詳細規格**：見 `../mil-std-750/references/die-attach-void-specs.md`

#### Void 判定標準

| 條件 | 判定 |
|------|------|
| **Single void** > **10%** of total contact area | **REJECT** |
| **Total void** > **50%** of total contact area | **REJECT** |
| Bonded area < **75%** of base area | **REJECT** |

### 1.5 SAT (Scanning Acoustic Tomography) 分層檢測

#### AEC-Q101 中的 SAT 要求

- **A4a alt (TCDT)**：TC 後 **100% SAT 掃描**，5 highest delaminated parts → decap + WBS
- **Q006 Table 3**：AM (Acoustic Microscopy) 在 T0、PC 後、1X 應力後執行
- **Change Matrix**：DA/MC/LF 變更均建議 SAT (●/○)

#### SAT 合格標準（Q006 7.2.1.1）

- TC 後：**No delamination at 1st/2nd bond and die corners**
- 判定位置：ball bond 下方、stitch bond 下方、die 四角

### 1.6 Thermal Impedance — MIL-STD-750 M3101

**詳細規格**：見 `../mil-std-750/references/die-attach-void-specs.md`

#### 關鍵參數

| 參數 | 說明 | 典型值 |
|------|------|--------|
| IH (加熱電流) | ≈ 元件額定工作電流 | ≥ 50× IM |
| tH (加熱脈衝) | 需落在 chip→D/A 過渡拐點 | 10-100 ms |
| 合格門檻 | 統計法 | **mean + 3σ** |

---

## 二、Wire Bonding (WB) 檢驗規範

### 2.1 適用標準總覽

| 檢驗方法 | 標準 | 用途 |
|---------|------|------|
| Wire Bond Pull | MIL-STD-750 **M2037** | AEC-Q101 C3 (Au/Al wire) |
| Wire Bond Pull | MIL-STD-883 **M2011** | IC 元件 / 備選 |
| Wire Bond Shear | AEC-Q101-003 / **JESD22-B116** | AEC-Q101 C4 |
| Ball Shear | **JESD22-B116B** | Cu wire ball bond |
| Ball + Stitch Pull | **AEC-Q006** Table 3 | Cu wire 驗證 |
| Non-destructive Pull | MIL-STD-883 **M2023** | 100% 產線篩選 |

### 2.2 Wire Bond Pull — MIL-STD-750 M2037

**詳細規格**：見 `../mil-std-750/references/method-2037-bond-strength.md`

#### 最小拉力速查（Condition A, Double Bond）

| 線材 | 線徑 (mil) | Preseal (gf) | Post seal (gf) |
|------|-----------|-------------|----------------|
| Au | 0.7 | 1.5 | 1.2 |
| Al | 1.0 | 2.5 | 1.5 |
| **Au** | **1.0** | **3.0** | **2.5** |
| Al | 1.3 | 3.0 | 2.0 |
| **Au** | **1.3** | **4.0** | **3.0** |
| Al | 1.5 | 4.0 | 2.5 |
| **Au** | **1.5** | **5.0** | **4.0** |
| Al | 2.0 | 5.5 | 3.8 |
| **Au** | **2.0** | **8.0** | **5.5** |

> **AEC-Q101 C3 要求**：Au wire > 1 mil，TC 後最小 **3 gf**

#### 失效類別

| 類別 | 描述 | 品質意義 |
|------|------|---------|
| a | Neckdown 處斷裂 | 正常，但頸縮過度需注意 |
| b | 非 neckdown 處斷裂 | **最佳**，表示 bond 比線強 |
| c | Die 端 bond 界面失效 | **異常** — 檢查 bond pad / bonding 參數 |
| d | Post 端 bond 界面失效 | **異常** — 檢查 LF plating / stitch 參數 |
| e | Die metallization 剝離 | **嚴重** — metallization 附著問題 |
| f | Post metallization 剝離 | **嚴重** — plating 品質問題 |
| g | Die 破裂 | **嚴重** — bond 力過大或 die 缺陷 |

### 2.3 Wire Bond Shear — AEC-Q101-003A

**詳細規格**：見 `test-methods-detail.md`

#### 適用範圍

- **Gold Ball Bonds**：金球對鋁墊（Ball Shear）
- **Aluminum Wedge/Stitch Bonds**：鋁線楔形接合（Wedge Shear）
- **Cu Ball Bonds**：銅球接合 → 改用 **JESD22-B116B**
- **Gold Wedge Bonds**：**不需做 WBS**

#### Gold Ball Bond 最低剪切力（AEC-Q101-003A Table 1）

| Ball Diameter (mil) | Min Sample Avg (gf) | Min Individual (gf) |
|--------------------|--------------------|--------------------|
| 2.0 | 12.6 | 5.7 |
| 2.5 | 20.6 | 12.4 |
| 3.0 | 30.8 | 21.1 |
| 3.5 | 43.4 | 31.7 |
| 4.0 | 58.3 | 44.3 |
| 4.5 | 75.6 | 59.0 |
| 5.0 | 95.1 | 75.5 |

> **公式近似**：Min Avg (gf) ≈ K × (Ball Dia)²，K ≈ 3.8 for Au

#### 剪切類型定義

| Type | 名稱 | 描述 | 接受 |
|------|------|------|------|
| 1 | **Bond Lift** | 整球脫離，幾乎無 IMC | ✓ |
| 2 | **Bond Shear** | 正常剪切，有 IMC 殘留 | ✓（最佳） |
| 3 | **Cratering** | Si/oxide 下層損傷 | ✓（如非製程造成） |
| 4 | **Die Surface Contact** | 剪切刀碰到 die 面 | ✗ 無效 |
| 5 | **Shearing Skip** | 只剪頂部 | ✗ 無效 |
| 6 | **Bonding Surface Lift** | 墊層脫離基材 | ✓ |

### 2.4 Wire Bond Shear — JESD22-B116B（Cu Wire 專用）

#### 適用範圍

- **Gold ball bonds** 和 **Copper ball bonds** 的剪切強度測試
- 可在封膠前（pre-encapsulation）或封膠後（post-encapsulation）執行
- **AEC-Q101 C4**：Cu wire 需使用 JESD22-B116 的 shear criteria

#### Cu Wire vs Au Wire 差異

| 特性 | Au Wire | Cu Wire |
|------|---------|---------|
| 硬度 | 較低（軟） | 較高（硬 2-4 倍） |
| Ball 形狀 | 圓整 | 可能略扁/不規則 |
| FAB 氣氛 | 空氣或 N₂ | **必須** Forming Gas (95%N₂/5%H₂) |
| Shear Force | 基準值 | **通常 > Au**（同 ball size） |
| IMC 成長 | Cu₃Al₂ / CuAl | 較慢但更穩定 |
| 腐蝕風險 | 低 | **較高**（Cu 易氧化） |

#### Cu Ball Bond 最低剪切力

JESD22-B116B 為 Cu ball bond 新增了最低剪切力標準：
- 剪切力計算基於 **bonded ball diameter**
- Cu ball 的最低剪切力通常 **≥ Au ball**（因 Cu 硬度較高）
- 具體數值需依 JESD22-B116B Table 查詢

### 2.5 AEC-Q006 Wire Bond 驗證（Cu Wire 專用）

#### Q006 Table 3 WB 相關測試序列

| # | 步驟 | TC | HAST/THB | HTSL | Option 1 | Option 2 |
|---|------|-----|----------|------|----------|----------|
| 2 | AM @ T0 | ● | ● | - | ● | ● |
| 4 | AM after PC | ●(11pcs) | - | - | ● | ● |
| 8 | AM post-1X | ●(11pcs) | - | - | ● | - |
| 9 | SEM inspection (stitch) | ●(1pc) | - | - | ● | - |
| 10a | **Ball + Stitch pull** | ●(3pcs) | ●(3pcs) | - | ● | - |
| 10b | **Ball shear** | ●(3pcs) | ●(3pcs) | ●(3pcs) | ● | - |
| 11 | Cross-section | ●(1pc) | ●(1pc) | ●(1pc) | ● | - |

#### Q006 1X Stress 後 Release Criteria

**TC 後 (7.2.1.1)**：

| 項目 | 合格標準 |
|------|---------|
| AM | No delamination at 1st/2nd bond and die corners |
| SEM | **No heel cracks** |
| WBS Codes | **禁止** Bond lift 或 Cratering |
| WBS Force | > T0 spec limit |
| WBP Codes | **只允許** Wire breaks (任何位置) |
| WBP Force | > T0 spec limit |
| Cross-section | No cracks in BEoL stack (bond over active) |

**HAST/THB/H3TRB 後 (7.2.1.2)**：

| 項目 | 合格標準 |
|------|---------|
| WBS Codes | **禁止** Bond lift 或 Cratering |
| WBP Codes | **只允許** Wire breaks |
| Cross-section | **Assess any sign of corrosion**（腐蝕評估） |

**HTSL 後 (7.2.1.3)**：

| 項目 | 合格標準 |
|------|---------|
| WBS Codes | **禁止** Bond lift 或 Cratering |
| WBS Force | > T0 spec limit **AND** > 50% of T0 measured minimum |
| Stitch pull | Force > T0 spec，**assess corrosion** |

> **WBS/WBP = 0 gf 是 FAIL**，禁止繼續 2X stress

---

## 三、DB/WB 檢驗在變更驗證中的角色

### 3.1 AEC-Q101 Table 3 中的 DB/WB 測試觸發

| 變更類型 | C3 WBP | C4 WBS | C5 DS | C9 TR | SAT |
|---------|--------|--------|-------|-------|-----|
| **Die Attach 材料** | - | - | **●** | **●** | ● |
| **Die Attach 製程** | - | - | **●** | ● | ● |
| **Wire Bonding** (Au/Al) | **●** | **●** | - | - | - |
| **Wire Bonding** (→Cu) | **J** | **J** | - | - | - |
| **Leadframe Plating** | ●(2,C) | - | ●(C) | - | - |
| **Leadframe Material** | ●(2) | - | - | - | - |
| **Mold Compound** | - | - | - | - | ● |
| **New Package** | **●** | **●** | **●** | **●** | ● |
| **Assembly Site Transfer** | **●** | **●** | **●** | **●** | ● |

> J = Change to Cu Wire → refer to **AEC-Q006**
> C = Leadframe Plating change only
> 2 = Verify post package

### 3.2 DB/WB 檢驗流程建議

```
製程變更通知 → Table 3 確認測試項目
                  ↓
        ┌─── DB 相關變更 ──┐
        │  (DA材料/製程)    │
        │                  │
        ▼                  ▼
   Die Shear (C5)    X-ray/SAT
   M2017 or M2019    M2076 void check
   Pre/Post 比較      分層確認
        │                  │
        └──── 報告 ────────┘

        ┌─── WB 相關變更 ──┐
        │  (線材/製程)      │
        │                  │
        ▼                  ▼
   Au/Al: WBP (C3)   Cu: Q006 全流程
   M2037 Cond. A      1X or 2X stress
   + WBS (C4)         AM + SEM + WBS/WBP
   Q101-003A          + Cross-section
        │                  │
        └──── 報告 ────────┘
```

---

## 四、產線 Inline 檢驗建議

### 4.1 Die Bonding Inline 檢驗

| 檢驗項目 | 方法 | 頻率建議 | 合格基準 |
|---------|------|---------|---------|
| Die Shear | M2017 Cond. A | 每批/每 lot | ≥ 2.0X 或分離類別 a |
| X-ray Void | M2076 | 100% (power die) / 抽樣 (small signal) | Single < 10%, Total < 50% |
| SAT | J-STD-035 | 每批或 SPC 抽樣 | No delamination at bond/die corners |
| Thermal Impedance | M3101 | 100% screen 或 SPC | mean + 3σ |
| Visual | M2074 (DPA) | 每月 DPA 或失效時 | Solder coverage ≥ 50% |

### 4.2 Wire Bonding Inline 檢驗

| 檢驗項目 | 方法 | 頻率建議 | 合格基準 |
|---------|------|---------|---------|
| Wire Bond Pull | M2037 Cond. A | 每批首件 + SPC | ≥ Table 2037-I Post seal |
| Ball Shear | Q101-003A / B116 | 每批首件 + SPC | ≥ Table 1 Min Individual |
| Non-destructive Pull | M2023 (MIL-STD-883) | 100% screen (可選) | 50% of destructive min |
| Visual (Pre-cap) | M2072/M2078 | 100% 或抽樣 | Ball size, loop height, wire sweep |

### 4.3 Pre-cap Visual 檢查項目

| 項目 | 合格標準 | 不合格 |
|------|---------|--------|
| Ball 位置 | Ball 中心在 pad 範圍內 | Ball 偏移超出 pad |
| Ball 大小 | 2.0-5.0 × wire dia (typical) | 過大(短路風險)/過小(強度不足) |
| Loop 高度 | 依規格，均勻一致 | 過高(sweep風險)/過低(接觸風險) |
| Wire Sweep | < 封裝允許範圍 | 線材碰觸相鄰線或 die edge |
| Stitch 位置 | 在 LF finger 規定區域 | 偏離 LF finger |
| 尾絲 (Tail) | 乾淨斷裂 | 過長尾絲(短路風險) |

---

## 來源文件索引

| 文件 | 內容 |
|------|------|
| MIL-STD-750D M2017 | Die Shear (離散) — pp.109-113 |
| MIL-STD-750D M2037 | Bond Strength (Wire Pull) — pp.127-131 |
| MIL-STD-750D M2076 | Radiography (X-ray) — pp.220-226 |
| MIL-STD-750D M2074 | Internal Visual — pp.198-218 |
| MIL-STD-750D M3101 | Thermal Impedance — pp.287-299 |
| MIL-STD-883 M2019 | Die Shear (IC) |
| MIL-STD-883 M2011 | Bond Strength (IC Wire Pull) |
| AEC-Q101-003A | Wire Bond Shear (Au ball/Al wedge) |
| JESD22-B116B | Wire Bond Shear (Au/Cu ball) |
| AEC-Q006 Rev B | Cu Wire Interconnect Qualification |
| AEC-Q101 Rev E Table 3 | Process Change Test Matrix |
