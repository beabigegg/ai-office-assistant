# AEC-Q101 附加測試方法詳細說明

> **來源**：AEC-Q101-001A, Q101-003A, Q101-004, Q101-005A, Q101-006 官方 PDF

---

## Q101-001A：HBM ESD Test（Human Body Model 靜電放電）

### 測試電路

```
100pF 電容 + 1500Ω 電阻 → 模擬人體放電
```

### 波形規格（Table 1）

| 電壓 (V) | Ipeak Short (A) | Rise Time (ns) | Decay Time (ns) |
|---------|----------------|----------------|-----------------|
| 1000 | 0.60 - 0.74 | 2.0 - 10 | 130 - 170 |
| 2000 | 1.20 - 1.46 | 2.0 - 10 | 130 - 170 |
| 4000 | 2.40 - 2.94 | 2.0 - 10 | 130 - 170 |
| 8000 | 4.80 - 5.86 | 2.0 - 10 | 130 - 170 |

### 失效判定（Key Parameters）

| 元件類型 | 參數 | 最大允許漂移 |
|---------|------|-------------|
| Bipolar | ICES, ICBO, IEBO | 10× 初始值 |
| FET | IDSS, IGSS | 10× 初始值 |
| IGBT | ICES, IGES | 10× 初始值 |
| **Diode** | **IR** | **10× 初始值** |

### HBM ESD 分級（Table 3）

| 分級 | 耐壓範圍 |
|------|---------|
| H0 | ≤ 250V |
| H1A | > 250V ~ ≤ 500V |
| H1B | > 500V ~ ≤ 1000V |
| H1C | > 1000V ~ ≤ 2000V |
| **H2** | **> 2000V ~ ≤ 4000V** |
| H3A | > 4000V ~ ≤ 8000V |
| H3B | > 8000V |

> **AEC-Q101 要求最低 H2 (> 2000V)**

---

## Q101-003A：Wire Bond Shear Test（打線剪切測試）

### 適用範圍

- **Gold Ball Bonds**：金球對鋁墊
- **Aluminum Wedge/Stitch Bonds**：鋁線楔形鍵合
- **注意**：金線楔形鍵合不需做 WBS

### 剪切類型定義（Figure 3）

| Type | 名稱 | 描述 | 接受狀態 |
|------|------|------|---------|
| **Type 1** | Bond Lift | 整個球脫離，幾乎無 IMC 殘留 | ✓ 可接受 |
| **Type 2** | Bond Shear | 正常剪切，有 IMC 或金屬殘留 | ✓ 可接受 |
| **Type 3** | Cratering | 晶片下層材料（Si/oxide）損傷 | ✓ 可接受（如非製程造成）|
| **Type 4** | Die Surface Contact | 剪切刀碰到晶片表面 | ✗ 無效數據 |
| **Type 5** | Shearing Skip | 只剪掉頂部，未完全剪切 | ✗ 無效數據 |
| **Type 6** | Bonding Surface Lift | 墊層脫離基材 | ✓ 可接受 |

### Gold Ball Bond 最低剪切力（Table 1）

| Ball Diameter (mil) | Min Sample Avg (g) | Min Individual (g) |
|--------------------|--------------------|--------------------|
| 2.0 | 12.6 | 5.7 |
| 2.5 | 20.6 | 12.4 |
| 3.0 | 30.8 | 21.1 |
| 3.5 | 43.4 | 31.7 |
| 4.0 | 58.3 | 44.3 |
| 4.5 | 75.6 | 59.0 |
| 5.0 | 95.1 | 75.5 |

### Wedge/Stitch Bond 失效標準

- 最小剪切力 **≥ 製造商 wire tensile strength**
- 鍵合面積覆蓋率 **≥ 50%**

---

## Q101-004：Miscellaneous Test Methods

### Section 2：UIS (Unclamped Inductive Switching)

**適用**：Power MOSFET、內部鉗位 IGBT

**目的**：測試元件在電感負載中關閉時的能量耐受能力

**測試電路**：
```
VDD = 供應電壓
L = 電感器（不飽和）
DUT = 待測元件
```

**程序**：
1. 開啟 gate，電流在電感中建立
2. 關閉 gate，監測 drain 電壓和電流
3. 逐步增加電流（1A 增量）直到失效
4. 記錄失效時的 IAV 和 VDS

**失效模式**：
- 電壓崩潰（在能量耗盡前）
- 電流持續流動（Latch-up）

### Section 3：DI (Dielectric Integrity)

**適用**：Power MOSFET、其他 MOS 閘極元件

**目的**：測定閘極氧化層的介電強度

**程序**：
1. 逐步增加閘極電壓（1V 增量）
2. 監測閘極漏電流
3. 當漏電流增加 10 倍時，記錄前一步電壓

### Section 4：DPA (Destructive Physical Analysis)

**目的**：檢查經環境測試後的內部完整性

**檢查項目**（50X 放大）：
- ✗ 不符合設計/建構/驗證文件
- ✗ 腐蝕、污染、分層、金屬化空洞
- ✗ 晶片裂痕或缺陷
- ✗ 打線、晶片、端子鍵合缺陷
- ✗ 樹枝狀生長或電遷移

---

## Q101-005A：CDM ESD Test（Charged Device Model 靜電放電）

### 參考標準

**ANSI/ESDA/JEDEC JS-002**（2019 年版本採用）

### 測試要求

- 樣品數：**10 pcs/stress level**
- 放電次數：**3 次正極 + 3 次負極**
- 所有 pin（包括 power 和 ground）都要測

### 失效判定（Table 1）

| 元件類型 | 參數 | 最大允許漂移 |
|---------|------|-------------|
| Bipolar | ICES, ICBO, IEBO | 10× 初始值 |
| FET | IDSS, IGSS | 10× 初始值 |
| IGBT | ICES, IGES | 10× 初始值 |
| **Diode** | **IR** | **10× 初始值** |

### CDM ESD 分級（Table 2）

| 分級 | 耐壓範圍 |
|------|---------|
| C0a | < TC 125V |
| C0b | TC 125V ~ < TC 250V |
| C1 | TC 250V ~ < TC 500V |
| **C2a** | **TC 500V ~ < TC 750V** |
| C2b | TC 750V ~ < TC 1000V |
| C3 | TC 1000V |

> **注意**：TC > 1000V 時，電暈效應可能限制實際放電電壓

### 小封裝考量

- 極小封裝（< 幾平方毫米）難以固定
- 電容極小，脈衝極快（標準 1GHz 無法量測）
- 極小封裝 CDM 失效極罕見
- 可與客戶協議不測試，但須記錄

---

## Q101-006：Short Circuit Reliability（短路可靠性）

### 適用範圍

**Smart Power Devices for 12V Systems**（14V 測試）

### 保護類型定義

| 類型 | 說明 |
|------|------|
| **Latching Protection** | 偵測過載後永久關斷，需系統重置 |
| **Auto-Restart Protection** | 偵測過載後關斷，冷卻後自動重啟（Toggling）|
| **Over-Temperature Protection** | 達到最高接面溫度時關斷 |

### 測試電路

**High Side Device**：
```
14V → 10mΩ + 5µH → Smart Power Device → Rshort + Lshort → GND
```

**Short Circuit 類型（Table 1）**：

| 類型 | Rshort | Lshort | 說明 |
|------|--------|--------|------|
| **TSC** (Terminal Short) | 20mΩ | < 1µH | 模組端短路（Ishort ≤ 20A 可不測）|
| **LSC** (Load Short) | 100mΩ (20-100A) / 50mΩ (>100A) | 5µH | 負載端短路（約 5m 線材）|

### 測試條件選擇

| 保護類型 | Cold Short Pulse | Cold Long Pulse | Hot Repetitive |
|---------|------------------|-----------------|----------------|
| Latching + Status FB | ● | - | - |
| Latching (no FB) | ● | - | - |
| Auto-Restart | ● | ● | ● |

**Cold Repetitive**：
- Short Pulse：Status FB 後 10ms 關閉
- Long Pulse：Status FB 後 300ms 關閉
- 溫度：-40°C（over-temp protected）或評估最壞情況

**Hot Repetitive**：
- 持續 toggling 直到失效
- 溫度：25°C + 強制風冷

### 失效判定

- 無法關閉（電性短路）
- 無法開啟（開路）
- 參數漂移超出規格

### 短路循環能力等級（Table 2）

| Grade | Cycles | Lots/Samples | Fails |
|-------|--------|--------------|-------|
| A | > 1,000,000 | 3/10 | 0 |
| B | > 300,000 - 1M | 3/10 | 0 |
| C | > 100,000 - 300K | 3/10 | 0 |
| D | > 30,000 - 100K | 3/10 | 0 |
| E | > 10,000 - 30K | 3/10 | 0 |
| F | > 3,000 - 10K | 3/10 | 0 |
| G | > 1,000 - 3K | 3/10 | 0 |
| H | 300 - 1,000 | 3/10 | 0 |
| O | < 300 | 3/10 | 0 |

---

## 來源文件索引

| 文件 | 版本 | 日期 | 內容 |
|------|------|------|------|
| AEC-Q101-001A | Rev A | 2005-07-18 | HBM ESD Test |
| AEC-Q101-003A | Rev A | 2005-07-18 | Wire Bond Shear Test |
| AEC-Q101-004 | - | 1996-05-15 | UIS, DI, DPA |
| AEC-Q101-005A | Rev A | 2019-01-29 | CDM ESD Test |
| AEC-Q101-006 | - | 2006-09-14 | Short Circuit Reliability |
