# MIL-STD-750 Method 2037 — Bond Strength (Destructive Bond Pull Test)

> **來源**：MIL-STD-750-2B w/Change 3 (750F 體系), Method 2037.1
> **舊版**：MIL-STD-750D (1995) — 數值標準無變化，但 **Test Condition 字母重新編排**
> **檔案位置**：`projects/aec-q-standards/vault/originals/MIL-STD-750F/MIL-STD-750-2B(3).pdf` pages 61-67
> **最後更新**：2026-03-27（750D→750F 比對）
>
> **⚠ 重要：Condition 字母映射變更**
> - 750D Condition A (Double bond pull) = **750F Condition D**
> - 750D Condition B (Single bond pull) = **750F Condition C**
> - 750F 新增：Condition A (Bond peel), F (Flip chip), G/H (Beam lead)

---

## 1. 目的 (Purpose)

測量打線接合強度，判定是否符合規定的接合強度要求。
適用於離散半導體元件（Discrete Devices）封裝內部的：
- Wire-to-die bond（線對晶粒接合）
- Clip-to-die bond（金屬片對晶粒接合）
- Wire-to-package lead bond（線對引腳接合）
- Wire-to-substrate bond（線對基板接合）

接合方式包括：焊接（soldering）、熱壓接合（thermocompression）、超音波接合（ultrasonic）等。

---

## 2. 設備要求 (Apparatus)

| 應力範圍 | 精度要求 |
|---------|---------|
| ≤ 10 gf | ± **0.25 gf** |
| 10 ~ 50 gf | ± **0.5 gf** |
| > 50 gf | ± **5%** of indicated value |

---

## 3. 測試條件 (Test Conditions)

### 3.1 Condition A — Wire Pull, Double Bond（標準雙鍵拉力）

**最常用的標準方法**

- 鉤子插入導線下方，在兩個接合點之間的中點施加拉力
- 拉力方向：**垂直於** die/substrate 平面，偏差 ≤ 5°
- 兩個接合點（ball bond + stitch bond）**同時受力**
- 拉到破壞或達到規定的最小值

### 3.2 Condition B — Wire Pull, Single Bond（單鍵拉力）

- **不建議用於線徑 < 0.005 inch (0.125 mm) 的線材**
- 用於需要個別測試 die bond 和 post bond 時
- 切斷線材，分別抓取自由端拉測
- Ball/nailhead bond：拉力方向垂直於 die 表面 (±5°)
- Wedge bond（線從側面出）：拉力角度 ≥ 45° 對 die 表面
- 產品判定基於 **等量測試** die bond 和 post bond

### 3.3 Condition C — Clip Pull（金屬片拉力）

- 用於 clip-bonded 離散元件
- 鉤子插入 clip 下方，靠近 die 附著點
- 拉力方向垂直於 die/substrate (±5°)

---

## 4. Table 2037-I — 最小接合強度 (Minimum Bond Strength)

### Condition A: Wire Pull, Double Bond

| 線材 | 線徑 (inch) | 線徑 (mil) | 線徑 (μm) | Preseal (gf) | Post seal (gf) |
|------|-----------|-----------|----------|-------------|----------------|
| **Au** | 0.0007 | 0.7 | 17.8 | **1.5** | **1.2** |
| Al | 0.0010 | 1.0 | 25.4 | **2.5** | **1.5** |
| **Au** | 0.0010 | 1.0 | 25.4 | **3.0** | **2.5** |
| Al | 0.0013 | 1.3 | 33.0 | **3.0** | **2.0** |
| **Au** | 0.0013 | 1.3 | 33.0 | **4.0** | **3.0** |
| Al | 0.0015 | 1.5 | 38.1 | **4.0** | **2.5** |
| **Au** | 0.0015 | 1.5 | 38.1 | **5.0** | **4.0** |
| Al | 0.002 | 2.0 | 50.8 | **5.5** | **3.8** |
| **Au** | 0.002 | 2.0 | 50.8 | **8.0** | **5.5** |
| Al | 0.003 | 3.0 | 76.2 | **12.0** | **8.0** |
| **Au** | 0.003 | 3.0 | 76.2 | **15.0** | **12.0** |
| Al | 0.005 | 5.0 | 127.0 | **30.0** | **21.0** |
| Al | 0.010 | 10.0 | 254.0 | **120.0** | **80.0** |
| Al | 0.015 | 15.0 | 381.0 | **220.0** | **160.0** |
| Al | 0.020 | 20.0 | 508.0 | **300.0** | **240.0** |
| **Clip** | - | - | - | **300.0** | **300.0** |

### 重要註解

1. **Condition B (Single Bond)**：最小強度 = Condition A 的 **75%**
2. **未列出的線徑**：使用 Figure 2037-1 和 2037-2 曲線查詢
3. **Ribbon wire**：使用等效截面積換算為等效圓線徑
4. **Post seal 測試**：在完成所有加工和篩選後執行

### 關鍵觀察

- **Au wire 強度 > Al wire**（同線徑），因 Au 的延展性和接合特性較佳
- Post seal 強度要求 < Preseal（因應力鬆弛和 IMC 成長）
- 1 mil Au wire Post seal 最小值 = **2.5 gf**（AEC-Q101 C3 要求 TC 後 ≥ 3 gf for Au wire > 1 mil）

---

## 5. 失效類別 (Failure Categories)

### 5.1 Wire Bond 失效類別

| 類別 | 描述 | 英文 | 常見原因 |
|------|------|------|---------|
| **a** | 線在頸縮處斷裂 | Wire break at neckdown | 正常失效，bonding 製程壓扁處 |
| **b** | 線在非頸縮處斷裂 | Wire break at point other than neckdown | 最佳結果，表示 bond 比線強 |
| **c** | Die 端 bond 界面失效 | Failure at wire/metallization interface at die | Die metallization 或 bond 品質問題 |
| **d** | Post 端 bond 界面失效 | Failure at wire/plating interface at package post | Lead plating 或 stitch bond 問題 |
| **e** | Die 金屬層剝離 | Lifted metallization from die | Metallization 附著力不足 |
| **f** | Post 金屬層/鍍層剝離 | Lifted metallization from substrate/post | 鍍層品質問題 |
| **g** | Die 破裂 | Fracture of die | Bond 力過大或 die 有裂紋 |
| **h** | 基板破裂 | Fracture of substrate | 基板強度不足 |

### 5.2 Clip Bond 失效類別

| 類別 | 描述 |
|------|------|
| **a** | Clip/die metallization 界面失效 |
| **b** | Die metallization 剝離 |
| **c** | Clip 從 package post 分離 |
| **d** | Die 破裂 |

---

## 6. 生產抽樣失敗處置 (Production Sampling Failure)

當樣品中不良數超過允收數時：

1. 產出不良品的設備 **停機**，直到新樣品通過
2. 自上次合格抽樣以來在該設備上接合的所有元件，需：
   - **全部拒收**，或
   - 進行 **100% 非破壞拉力測試**，力量 = 最小規定值的 **1/2**
3. 替代公式：非破壞拉力 = (X̄ - 3σ) / 2，其中 σ ≤ 0.2X̄
4. **99.999% 純鋁退火線**：除數改為 **3**（即拉力 = 最小值的 1/3）
5. **Die fracture 失效除外**：不可用非破壞篩選替代（可能 die 已受損）

---

## 7. 與 MIL-STD-883 Method 2011 的關係

| 項目 | MIL-STD-750 M2037 | MIL-STD-883 M2011 |
|------|-------------------|-------------------|
| **適用對象** | 離散半導體 (Discrete) | IC / 微電路 (Microcircuits) |
| **Test Conditions** | A (Double), B (Single), C (Clip) | A-K（更多條件） |
| **力量精度** | ±0.25/±0.5/±5% | ±0.3 gf 或 ±5% |
| **力量標準** | Table 2037-I | Table I (M2011) |
| **AEC-Q101 引用** | C3 (Au/Al wire) | C3 (備選) |

### MIL-STD-883 M2011 Table I 參考值（常用線徑）

| 線材 | 線徑 (mil) | Condition D Min (gf) |
|------|-----------|---------------------|
| Au | 1.0 | 2.4 |
| Au | 1.2 | 4.0 |
| Au | 1.5 | 6.0 |
| Al | 1.0 | 3.0 |
| Al | 1.2 | 4.0 |
| Al | 1.5 | 5.0 |

> **注意**：M2011 Condition D = M2037 Condition A（標準雙鍵拉力）

---

## 8. 與 AEC-Q101 的關聯

| Q101 項目 | 代號 | 引用 | 說明 |
|-----------|------|------|------|
| C3 | WBP | MIL-STD-750-2 M2037 (Au/Al) | Condition C or D |
| C3 | WBP | AEC-Q006 (Cu wire) | Cu wire 專用 |

### AEC-Q101 C3 特殊要求

- Au wire > 1 mil：**TC 後最小拉力 = 3 gf**
- Au wire ≤ 1 mil：依 M2037 Table 2037-I 作為 guideline
- Au wire ≤ 1 mil：拉力鉤必須置於 **ball bond 上方**，非線中央
- Cu wire：依 **AEC-Q006** 執行（含 Ball + Stitch pull）

---

## 來源文件

| 文件 | 頁碼 | 內容 |
|------|------|------|
| MILSTD750.pdf Page 127 | Method 2037 第 1 頁 | 目的、設備、測試條件 A/B/C、失效標準 |
| MILSTD750.pdf Page 128 | Method 2037 第 2 頁 | 失效類別（Wire/Clip）、生產抽樣失敗處置 |
| MILSTD750.pdf Page 129 | Method 2037 第 3 頁 | **Table 2037-I 最小接合強度**（完整表格） |
| MILSTD750.pdf Page 130 | Method 2037 第 4 頁 | Figure 2037-1 Bond pull limits 曲線圖 |
| MILSTD750.pdf Page 131 | Method 2037 第 5/6 頁 | Figure 2037-2 Bond pull limits 續 |
