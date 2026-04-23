# MIL-STD-750 — Die Attach Void 相關規範彙整

> **來源**：MIL-STD-750-2B w/Change 3 (750F 體系), Method 2076.6
> **舊版**：MIL-STD-750D (1995) — **M2076 void 判定標準已大幅收緊**
> **檔案位置**：`projects/aec-q-standards/vault/originals/MIL-STD-750F/MIL-STD-750-2B(3).pdf` pages 249-263
> **最後更新**：2026-03-27（750D→750F 比對，M2076 為變化最大的 Method）

---

## 總覽

MIL-STD-750 中與 die attach void 相關的規範分布在四個 Method 中，依檢測方式分類：

| Method | 名稱 | 檢測方式 | 破壞性 | 適用場景 |
|--------|------|---------|--------|---------|
| **2076** | Radiography (X-ray) | X 光影像判讀 | 非破壞 | **最常用**，產線 inline 檢查 |
| **2074** | Internal Visual Inspection | 開封目視檢查 | 破壞 | DPA / 失效分析 |
| **3101** | Thermal Impedance Testing | 暫態熱阻偵測 | 非破壞 | 產線 screening / 來料檢驗 |
| **2017-B** | Die Shear (Condition B) | 機械衝擊破碎後目視 | 破壞 | 大型 die 驗證（≥ 161 mm²） |

---

## 1. Method 2076 — Radiography（X 光檢查）

> **PDF 頁碼**：pages 220-226
> **性質**：**非破壞性檢測**，有明確的面積百分比判定標準

### 1.1 目的

非破壞性偵測密封封裝內部缺陷，特別是：
- 封蓋造成的缺陷
- 異物（foreign objects）
- 不當內連線
- **Die attach 材料中的 void**
- 玻璃封裝中的 void

### 1.2 設備要求

| 項目 | 規格 |
|------|------|
| X-ray 設備 | 電壓範圍足以穿透元件，最高不超過 **150 kV** |
| 影像解析度 | 可辨識 **.001 inch (0.025 mm)** 主要尺寸的物件 |
| 底片 | Eastman type R 或等效 |
| 觀片器 | 可辨識 **.001 inch (0.025 mm)** 解析度 |
| 影像品質標準 | ASTM type B 或等效穿透計 |
| 底片密度 | H&D 密度 1.0 ~ 2.5（感興趣區域） |
| 觀片放大 | **6X ~ 20X** |

### 1.3 拍攝方向

| 封裝類型 | 標準拍攝方向 | 備註 |
|---------|------------|------|
| 扁平封裝 / 單端圓柱 | Y 方向 | 需要時加拍 X、Z 方向 |
| 螺柱安裝 / 軸向引線圓柱 | X 方向 | 需要時加拍 Z 方向及 45° |
| JANS 等級 | X + Y 兩個方向 | 強制雙向 |

### 1.4 Die Attach Void 判定標準

#### Thermal Integrity（§3.8.2.2，750F 大幅收緊）

| 元件類型 | 750D 標準 | **750F 標準** | 判定 |
|---------|----------|-------------|------|
| **Power / case mounted devices** | >50% | **>15%** | **REJECT** |
| **All other devices** | >50% | **>30%** | **REJECT** |

> **750F 新增**：JANS inspection lot 中若 ≥5% 元件 fail die attach criteria → lot review + corrective action。
> 若 die attach image 顯示 unusual anomalies 或 significant voiding directly under active area → lot review。

#### Unacceptable Construction（§3.8.2.3.1）

| 條件 | 判定 |
|------|------|
| **Single void** 貫穿 die 長度或寬度，且面積 > **10%** of total intended contact area | **REJECT** |
| 半導體元件 bonded area < **75%** of base area | **REJECT** |

### 1.5 其他相關 reject 條件

- 異物（extraneous material）
- 焊料噴濺（solder/weld splash）
- 引線或 whisker 形狀/位置不當
- 引線間距不足（< .002 inch）
- Weld void 減少引線連接面積 > **25%** of total weld area

### 1.6 注意事項

> **重要**：某些封裝類型的材料屏蔽效應可能使 X 光無法從某些角度辨識特定缺陷。
> 應根據具體元件設計評估此限制。

---

## 2. Method 2074 — Internal Visual Inspection（離散二極體內部目檢）

> **PDF 頁碼**：pages 198-218
> **性質**：**破壞性檢測**（需開封），依結構類型分多組判定標準

### 2.1 目的

檢查離散半導體二極體及其他雙端子元件的材料、設計、構造及工藝。

### 2.2 設備

| 項目 | 規格 |
|------|------|
| 顯微鏡 | 單目/雙目/立體，放大倍率 **20X ~ 30X** |
| 照明 | 充足照明 |
| 視覺標準 | 必要的量規、圖面、照片 |

### 2.3 Solder Void 判定標準

依元件構造分為多個子類別，核心判定原則一致：

#### 2.3.1 透明體軸向引線直通型（3.1.3）

| 接合類型 | Reject 條件 | 備註 |
|---------|------------|------|
| **Die-to-post** solder (3.1.3.1a) | 焊料流動 < **50%** of minimum available contact area perimeter | Figure 2074-19 |
| **Lead-to-die** solder (3.1.3.2) | > **50%** of available contact area perimeter void of solder | Figure 2074-21 |
| **Die-to-die** solder (3.1.3.3) | > **50%** of available contact area perimeter void of solder | Figure 2074-24 |

#### 2.3.2 金屬體焊接接觸型（3.1.2）

| 接合類型 | Reject 條件 |
|---------|------------|
| Solder 接合 (3.1.2.1a) | 焊料未平滑成形，或未融合至相鄰元件之間 **50%** 周長 |

#### 2.3.3 玻璃封裝壓力接觸型（3.1.5）

| 接合類型 | Reject 條件 |
|---------|------------|
| Solder voids (3.1.5.3) | 焊料流動 < **50%** of minimum available contact area perimeter |
| Die-to-post contact area (3.1.5.4) | 焊料未融合至 **50%** 可用 bonding area |

#### 2.3.4 Power 元件（3.2.3.4）

| 接合類型 | Reject 條件 |
|---------|------------|
| Die-to-pedestal / Die-to-clip (3.2.3.4.1a) | 焊料流動 < **50%** of minimum available contact area perimeter |
| Clip-to-post / Feed-through-to-heat-sink (3.2.3.4.2a) | 焊料 wetting 不連續 |

### 2.4 其他 Die Attach 相關 Reject 條件

| 缺陷 | Reject 條件 |
|------|------------|
| Solder overflow | 焊料接觸 die 對面表面 |
| Die alignment | Die 表面偏離安裝中心線 > **15°** |
| Die chipout | Chipout 延伸超過 die 寬度 **25%** 或距 junction < **2 mil** |
| Die cracks | 裂紋使 die 有效面積降至原面積 < **75%** |
| Die tilt | 元件傾斜 > **10°** |

---

## 3. Method 3101 — Thermal Impedance Testing of Diodes（暫態熱阻測試）

> **PDF 頁碼**：pages 287-299
> **性質**：**非破壞性偵測**，透過熱響應間接偵測 void

### 3.1 原理

Die attach 中的 void 會阻礙晶片到基板的熱傳導。利用暫態熱響應（thermal transient）可以比穩態熱阻更靈敏地偵測 void：

- 晶片熱時間常數 << 封裝熱時間常數（差距數個數量級）
- 選擇適當加熱脈衝寬度 tH（**1 ~ 400 ms**），使只有晶片和 chip-to-substrate 界面被加熱
- Void 處熱傳導差 → ΔVF 偏高 → 可識別不良品

### 3.2 適用對象

- Rectifier diodes
- Transient voltage suppressors
- Power zener diodes
- 部分 zener / signal / switching diodes

### 3.3 用途

| 用途 | 說明 |
|------|------|
| Production monitoring | 產線即時篩選 |
| Incoming inspection | 來料 die attach 品質評估 |
| Pre-burn-in screening | 老化前篩選不良 die attach |

### 3.4 測試架構

```
                     Position 1: 量測 VF（IM）
Electronic Switch ─┤
                     Position 2: 加熱（IH）

流程：VFi 量測 → IH 加熱 tH 時間 → 切回量測 VFf → 計算 ΔVF
```

### 3.5 關鍵參數

| 參數 | 說明 | 典型值 |
|------|------|--------|
| IH | 加熱電流 | ≈ 元件額定工作電流，通常 ≥ 50× IM |
| IM | 量測電流（TSP） | ~10 mA（約 IH 的 2%） |
| tH | 加熱脈衝寬度 | 10-50 ms (≤15W) / 50-100 ms (≤200W) / ≥250 ms (穩態) |
| tMD | 量測延遲時間 | ≤ 100 μs |
| tSW | 取樣窗口時間 | 越小越好，可用示波器趨近零 |
| ΔVF | 正向電壓變化 | 目標範圍 5-80 mV（對應 ΔTJ ≈ +10°C ~ +20°C） |
| K | 校準因子 | = ΔTJ / ΔVF，單位 °C/mV，約 ~2 °C/mV |

### 3.6 合格判定方法（五種，由簡到繁）

| 方法 | 判定基準 | 複雜度 | 說明 |
|------|---------|--------|------|
| **ΔVF limit** | 單一 ΔVF 上限值 | 最簡單 | 適合篩選，但不同供應商需不同限值 |
| **ΔTJ limit** | 最大容許接面溫升 | 中等 | ΔTJ = K × ΔVF，需校準 K factor |
| **CU limit** | Comparison Unit = ΔVF / VH | 中等 | 補償不同元件間的功率差異 |
| **K×CU limit** | 綜合 K factor 和功率差異 | 較高 | 更精確 |
| **ZθJX limit** | 暫態熱阻抗 = ΔTJ / PH | 完整 | 絕對值規格，克服所有變異 |

### 3.7 限值設定方法

| 方法 | 說明 |
|------|------|
| 與其他方法交叉驗證 | 與 die shear (M2017)、X-ray (M2076) 結果關聯 |
| 最大 TJ 變異 | ΔVF 約 0.5°C/mV，可反推容許溫度分佈 |
| **統計法（最常用）** | 取 20-25 顆樣品，限值 = **平均值 + 3σ** |

### 3.8 建立測試的標準步驟摘要

| 階段 | Steps | 工作內容 |
|------|-------|---------|
| A - Initial Setup | 1-4 | 近似儀器設定，找出 10-15 顆樣品間的差異 |
| B - Heating Curve | 5-6 | 用最高/最低讀值的元件產生加熱曲線 |
| C - Curve Interpretation | 7-9 | 從加熱曲線找到適當的 tH（die attach 區域的拐點） |
| D - Final Setup | 10 | 提高加熱功率以改善量測靈敏度 |
| E - Pass/Fail | 11-12 | 設定合格/不合格門檻 |

### 3.9 加熱曲線解讀

```
ΔVF
  ↑
  │         ╱── 不良品（void 大，熱阻高）
  │        ╱
  │       ╱ ─── 兩曲線在此開始分離
  │      ╱      → 熱已穿過晶片進入 die attach 區
  │     ╱╱
  │    ╱╱
  │   ╱╱ ─── chip 熱常數內，兩曲線重合
  │  ╱╱       （相同晶片特性一致）
  │ ╱╱
  │╱╱──── 良品（void 小/無，熱阻低）
  └──────────────────→ tH (ms)
     chip    die attach   package
     region  region       region
```

> **關鍵**：選擇 tH 使其落在 chip→die attach 的過渡拐點處，
> 可最大化對 void 的偵測靈敏度。

---

## 4. Method 2017 Condition B — Mechanical Impact（機械衝擊法）

> **PDF 頁碼**：page 113
> **性質**：**破壞性檢測**，大型 die 專用
> **完整 Method 2017 規格**：見 `method-2017-die-shear.md`

### 4.1 適用條件

- Die 面積 **≥ 0.25 in²**（約 **161 mm²**）
- 一側或兩側有**冶金鍵合**（metallurgical bond）的 die

### 4.2 程序

1. Die 組件放在砧座上
2. 用球頭錘（ball peen hammer）敲碎矽晶片
3. 矽**不會附著**在有 void 的區域（void 處矽脫落）
4. 目視檢查 void 的大小與密度
5. 與建立的視覺標準比較

### 4.3 Void 失效判定

| 條件 | 判定 |
|------|------|
| 任何 **single void** 面積 > **3%** of total die area | **REJECT** |
| 所有 **void 面積總和** > **6%** of total die area | **REJECT** |

### 4.4 安全注意

- 需佩戴護目鏡及防護衣物
- 敲碎矽片會產生飛濺碎屑

---

## 5. 各方法比較與選用建議

### 5.1 判定標準比較

| Method | Void 面積門檻 | 量測方式 |
|--------|-------------|---------|
| **2076 X-ray** | Single > **10%**, Total > **50%**, Bonded < **75%** | 影像面積比 |
| **2074 Visual** | Solder coverage < **50%** perimeter | 周長比 |
| **2017-B Impact** | Single > **3%**, Total > **6%** | 敲碎後面積比 |
| **3101 Thermal** | 統計法 **mean + 3σ** | ΔVF 或 ZθJX |

### 5.2 適用場景選用

| 場景 | 建議方法 | 原因 |
|------|---------|------|
| **產線 inline 檢查** | M2076 (X-ray) 或 SAT | 非破壞，可 100% 檢 |
| **產線 screening** | M3101 (Thermal) | 非破壞，快速，靈敏度高 |
| **DPA / 失效分析** | M2074 (Visual) | 開封後直接觀察 |
| **大型 power die 驗證** | M2017-B (Impact) | 適合冶金鍵合的大 die |
| **AEC-Q101 C5 認證** | M2017-A (Shear) | 標準要求的破壞性測試 |
| **製程能力評估** | M3101 + M2076 | 組合使用，互相驗證 |

### 5.3 Method 間的交叉驗證

Method 3101 明確提到（Step 11a）：

> 暫態熱阻結果應與 **die shear (M2017)** 和 **X-ray (M2076)** 結果進行關聯驗證。
> 雖然後兩者「從熱的觀點實際價值有限」，但它們是軍標中的標準化方法。

---

## 6. 與 AEC-Q101 的關聯

| Q101 項目 | Method | 說明 |
|-----------|--------|------|
| C1 - DPA | M2074 + M2076 | DPA 中包含內部目檢和 X 光檢查 |
| C5 - Die Shear | M2017 | 主要是 Condition A（剪切），Condition B 用於大型 die |
| 製程監控 | M3101 | 非 Q101 強制，但業界常用於 die attach 品質監控 |

---

## 6. Method 2076.7 — 提案修訂（EP Study 5961-2025-111, 2025/11/06）

> **來源**：`eps750tm2076_25-111.pdf`（Engineering Practice Study Final Report）
> **狀態**：EP Study 完成，建議納入下一次 MIL-STD-750-2 修訂，**尚未正式生效**
> **主要變更**：GaN flip-chip 支持 + Void 判定大幅加嚴 + Lid seal 圖示更新

### 6.1 Void 判定標準變更（Section 3.8.2.2 Thermal Integrity）

| 元件類別 | 舊版 2076（750D） | 新版 2076.7（提案） | 變化 |
|---------|-----------------|-------------------|------|
| **Power / case-mounted** | Total > 50% → Reject | Total > **15%** → Reject | **大幅加嚴（50%→15%）** |
| **Power GaN flip-chip** | 無此類別 | **每個 solder point 個別 < 15%** | **新增類別** |
| **All other devices** | Total > 50% → Reject | Total > **30%** → Reject | **加嚴（50%→30%）** |
| Single void 貫穿 die | > 10% → Reject | > 10% → Reject（GaN 除外） | 不變 |
| Bonded area（軸向引線） | < 75% → Reject | < 75% → Reject | 不變 |

### 6.2 新增 Section 3.8.4 — Power GaN Flip-chip Discrete Devices

GaN flip-chip 使用 solder bump 接合（非 wire bond），需專用檢查方式：

| 檢查項目 | 視角 | 判定 | 對應圖示 |
|---------|------|------|---------|
| a. Cold/insufficient reflow | Side view | 焊點回流不足、die 不平 | Figure 2076-8 |
| b. Over reflow | Top + Side view | 焊料溢出正常尺寸 | Figure 2076-9 |
| c. Solder shorting | Top view | 焊點間短路 | Figure 2076-10 |
| d. Voiding | Top view | **每個焊點個別**檢查 void | Figure 2076-11 |

> **注意**：GaN flip-chip 的 solder joint 是**封裝內部**的 1st level interconnect（die → package substrate），
> 不是板級 SMT solder paste（2nd level, package → PCB）。TM2076 不涉及 solder paste 製程參數。

### 6.3 Lid Seal Void 圖示更新（Section 3.8.2.3.2 + Figure 2076-2）

- 新版 Figure 2076-2 改為來自 MIL-STD-883-2 Method 2012 的圖示（Government Working Group 建議）
- 判定邏輯不變：seal width 被 void 減少超過 75% → Reject
- 新增 Note：Reject if A/W, (B+C)/W, or D/W < 25% of W

### 6.4 其他更新

- 設備規格：底片改為 **Agfa D2 or equivalent**（舊版 Eastman type R）
- 觀片放大：改為 **10X ~ 40X**（舊版 6X ~ 20X），疑問時可加到 100X
- Real-time radiography：補充數位影像存儲格式要求（CD-ROM/DVD）
- JANS devices：強制至少兩個方向拍攝

### 6.5 對 PANJIT 離散元件封裝的影響

| 封裝 | 元件類別（新版） | Void 上限 | 備註 |
|------|---------------|----------|------|
| DO-218 | Power / case-mounted | **15%** | 大功率 SMD |
| PDFN | Power / case-mounted | **15%** | Power DFN |
| SOD-123FL | 視用途：Power=15%, Signal=30% | **15% 或 30%** | 需依產品功率判定 |
| TDI | 需確認功率等級 | **待定** | PANJIT 內部封裝 |
| SOD-323HE | All other devices | **30%** | 小信號 |
| MICRODIP | All other devices | **30%** | 小型封裝 |

---

## 來源文件

| 文件 | 頁碼 | 內容 |
|------|------|------|
| MILSTD750.pdf Page 113 | Method 2017 Condition B | 機械衝擊 void 判定 |
| MILSTD750.pdf Pages 198-218 | Method 2074 | 離散二極體內部目視檢查 |
| MILSTD750.pdf Pages 220-226 | Method 2076 | X 光 radiography（舊版） |
| MILSTD750.pdf Pages 287-299 | Method 3101 | 二極體暫態熱阻測試 |
| eps750tm2076_25-111.pdf | EP Study 5961-2025-111 | **TM2076.7 提案修訂**（2025/11/06） |
