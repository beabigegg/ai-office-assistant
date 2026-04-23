# 離散半導體元件 — 動態測試參數完整總表

> **來源**：AEC-Q101 Rev E + PANJIT 官網產品頁 + ANSI/ESD + IEC 61000 + ISO 10605
> **建立日期**：2026-02-24
> **適用範圍**：PANJIT 產品線涵蓋的所有離散元件功能

---

## 1. 各功能動態參數總表

### 1.1 二極體 / 整流器類

| 功能 | 動態參數 | Symbol | 意義 | 典型測試條件 | 條件決定因素 | 概覽頁列出 |
|------|---------|--------|------|-------------|-------------|-----------|
| **General Purpose Rectifier** | (無動態參數) | — | — | — | — | — |
| **Fast Recovery Rectifier** | 反向恢復時間 | TRR | 從導通切換到截止的恢復時間 | IF=額定, IR=1A, IRR=0.25A, TJ=25°C | IF 依額定電流 | TRR (150-500ns) |
| **Ultra Fast Recovery Rectifier** | 反向恢復時間 | TRR | 同上 | 同上 | 同上 | TRR (50-100ns) |
| **Super Fast Recovery Rectifier** | 反向恢復時間 | TRR | 同上 | 同上 | 同上 | TRR (25-50ns) |
| **Hyper Fast Recovery Rectifier** | 反向恢復時間 | TRR | 同上 | 同上 | 同上 | TRR (15-35ns) |
| **FRED** | 反向恢復時間 | TRR | 同上 | 同上 | 同上 | TRR |
| **FRED** | 反向恢復電荷 | Qrr | 恢復期間的總電荷 | 同 TRR 條件 | 同上 | 部分列出 |
| **Small Signal Switching Diode** | 反向恢復時間 | trr | 同上 | IF, IR 指定 | IF 依額定 | trr (3-5ns) |
| **Small Signal Switching Diode** | 接面電容 | CJ | 反向偏壓下的接面電容 | VR=0V or 指定, f=1MHz | VR 依額定 | CJ Max (pF) |
| **Schottky (Power/Super)** | (無動態參數) | — | 多數載子元件，本質無 trr | — | — | — |
| **Schottky Bridge** | (無動態參數) | — | 同上 | — | — | — |
| **Bridge Rectifier** | 反向恢復時間 | TRR | 同 Fast Recovery | 同 Fast Recovery | 同上 | TRR (ns) |

### 1.2 SiC 元件

| 功能 | 動態參數 | Symbol | 意義 | 典型測試條件 | 條件決定因素 | 概覽頁列出 |
|------|---------|--------|------|-------------|-------------|-----------|
| **SiC Diode** | 電容性電荷 | QC | 取代 trr 的指標（零反向恢復） | VR=400V (or rated) | VR 依額定 | 否 (Datasheet) |
| **SiC Diode** | 總電容 | C | 多點量測 | VR=1V/200V/400V, f=100kHz | VR 依額定, f 固定 | 否 (Datasheet) |

### 1.3 MOSFET / IGBT

| 功能 | 動態參數 | Symbol | 意義 | 典型測試條件 | 條件決定因素 | 概覽頁列出 |
|------|---------|--------|------|-------------|-------------|-----------|
| **MOSFET (全電壓)** | 輸入電容 | Ciss | Cgs + Cgd | VDS=額定/2, VGS=0, f=1MHz | VDS 依額定, f 固定 | Ciss Typ (pF) |
| **MOSFET** | 輸出電容 | Coss | Cds + Cgd | 同上 | 同上 | 否 (Datasheet) |
| **MOSFET** | 反向傳輸電容 | Crss | Cgd (Miller 電容) | 同上 | 同上 | 否 (Datasheet) |
| **MOSFET** | 總閘極電荷 | Qg | 導通所需總電荷 | VDS=額定/2, ID=額定, VGS=10V | VDS+ID 依額定 | Qg Typ (nC) |
| **MOSFET** | 閘-源電荷 | Qgs | 到達 Miller 平台的電荷 | 同 Qg | 同上 | 否 (Datasheet) |
| **MOSFET** | 閘-汲電荷 | Qgd | Miller 平台期間的電荷 | 同 Qg | 同上 | 否 (Datasheet) |
| **MOSFET** | 導通延遲 | td(on) | 閘極訊號到汲極開始回應 | VDD, ID, RG 指定 | 依操作點 | 否 (Datasheet) |
| **MOSFET** | 上升時間 | tr | 汲極電流 10%→90% | 同上 | 同上 | 否 (Datasheet) |
| **MOSFET** | 關斷延遲 | td(off) | 閘極訊號到汲極開始回應 | 同上 | 同上 | 否 (Datasheet) |
| **MOSFET** | 下降時間 | tf | 汲極電流 90%→10% | 同上 | 同上 | 否 (Datasheet) |
| **Super Junction MOSFET** | (同上全部) | + Eoss, Qoss | 輸出電容儲能/電荷 | VDS 指定 | VDS 依額定 | Ciss + Qg |
| **IGBT** | 總閘極電荷 | Qg | 同 MOSFET | VCE, IC, VGE 指定 | 依額定 | 有限 |
| **IGBT** | 導通/關斷延遲 | td(on)/td(off) | 同 MOSFET | VCC, IC, RG 指定 | 依額定 | 否 (Datasheet) |
| **IGBT** | 上升/下降時間 | tr / tf | 同 MOSFET | 同上 | 同上 | 否 (Datasheet) |
| **IGBT** | 導通/關斷損耗 | Eon / Eoff | 切換能量損耗 | VCC, IC, TJ 指定 | 依額定 | 否 (Datasheet) |

### 1.4 BJT (雙極接面電晶體)

| 功能 | 動態參數 | Symbol | 意義 | 典型測試條件 | 條件決定因素 | 概覽頁列出 |
|------|---------|--------|------|-------------|-------------|-----------|
| **General Transistor** | 延遲時間 | td | 基極訊號到集極開始回應 | VCC, IC, IB1, IB2 指定 | 依額定 | 否 |
| **General Transistor** | 上升時間 | tr | 集極電流 10%→90% | 同上 | 同上 | 否 |
| **General Transistor** | 儲存時間 | ts | 關斷時少數載子清除時間 | 同上 | 同上 | 否 |
| **General Transistor** | 下降時間 | tf | 集極電流 90%→10% | 同上 | 同上 | 否 |
| **General Transistor** | 轉換頻率 | fT | 電流增益降至 1 的頻率 | VCE, IC 指定 | 依額定 | 否 |

### 1.5 保護元件類（Zener / TVS / ESD）

| 功能 | 動態參數 | Symbol | 意義 | 典型測試條件 | 條件決定因素 | 概覽頁列出 |
|------|---------|--------|------|-------------|-------------|-----------|
| **Zener** | 動態阻抗 | ZZT | 在 IZT 下的 AC 小信號阻抗 | IZ(ac)=0.1×IZ(dc), f=60Hz | IZT 依 VZ 額定 | ZZT @IZT Max (Ω) |
| **Zener** | 膝點阻抗 | ZZK | 在 IZK(低電流)下的阻抗 | f=60Hz | IZK 依 VZ 額定 | ZZK @IZK Max (Ω) |
| **TVS (Standard)** | 接面電容 | CJ | 反向偏壓下的接面電容 | VR=0V or VRWM, f=1MHz | VR 依 VRWM | 否 (Datasheet) |
| **TVS** | 箝制電壓 | VC | IPP 下的峰值箝制電壓 | 10/1000μs 波形, IPP=額定 | IPP 依額定功率 | VC @IPP Max (V) |
| **TVS** | 動態電阻 | Rd | 箝制區斜率 | Rd=(VC-VBR_min)/IPP | 由 VC 和 VBR 推算 | 否 (可計算) |
| **Load Dump TVS** | 箝制電壓 | VC | 高功率箝制 | 10/1000μs, IPP up to 6600W | 依車規額定 | VC @IPP |
| **Load Dump TVS** | 接面電容 | CJ | 同 TVS | 同 TVS | 同 TVS | 否 (Datasheet) |
| **ESD Protection** | 接面電容 | CJ | 信號完整性關鍵指標 | VR=0V, f=1MHz | f 固定 | CJ Max/Typ (pF) |
| **ESD Protection** | TLP 箝制電壓 | V_clamp(TLP) | 100ns TLP 脈衝下的箝制 | TLP 100ns pulse, @指定電流 | 依 IEC 61000-4-2 等級 | 部分列出 |
| **ESD Protection** | 插入損耗 | IL | 信號衰減 | f=指定頻率 (GHz) | 依介面速率 | 部分列出 |

---

## 2. 測試條件體系 — 固定 vs 依靜態額定決定

### 2.1 條件結構

| 固定部分（業界統一） | 依靜態額定值決定的部分 |
|--------------------|--------------------|
| 測試方法標準（MIL-STD-750, JEDEC, ANSI/ESD） | 施加電壓（VDS, VR, VDD, VRWM）→ 依元件額定值 |
| 量測頻率（Ciss/Coss/CJ: 1MHz; ZZT: 60Hz; SiC C: 100kHz） | 施加電流（IF, ID, IZ, IPP）→ 依元件額定值 |
| 溫度（TJ = 25°C 為標準點） | RG（閘極電阻）→ 依應用設計 |
| 脈衝波形定義（trr: IRR 截止點; TLP: 100ns 方波） | VGS 測試點（10V or 4.5V）→ 依閘極額定 |
| TLP 量測窗口（30ns 處取值） | 電荷量測的 VDS/VCE（通常為額定的一半） |

### 2.2 各參數的條件決定邏輯

```
trr:   IF=f(額定IF), IR=固定, IRR=固定比例, TJ=25°C
Ciss:  VDS=f(額定VDS), VGS=0V, f=1MHz
Qg:    VDS=f(額定VDS), ID=f(額定ID), VGS=10V or 4.5V
ZZT:   IZT=f(額定VZ), f=60Hz
CJ:    VR=f(額定VRWM), f=1MHz
VC:    IPP=f(額定PPP), waveform=10/1000μs
TLP:   pulse=100ns, current=stepwise (→ I-V curve)
```

---

## 3. ESD / 突波保護標準體系

### 3.1 標準架構總覽

```
ESD / 突波 測試標準
│
├── 元件級 (Component Level) ← AEC-Q101 管轄
│   ├── HBM — ANSI/ESDA/JEDEC JS-001 → AEC-Q101 E3 (Q101-001A)
│   │   └── 100pF / 1500Ω, Pass/Fail 分級
│   ├── CDM — ANSI/ESDA/JEDEC JS-002 → AEC-Q101 E4 (Q101-005A)
│   │   └── 元件自身電容 / 低阻, <1ns 脈衝
│   └── TLP — ANSI/ESD STM5.5.1-2022 → AEC-Q101 不涵蓋
│       ├── 100ns 方波, 產出 I-V 曲線（非 Pass/Fail）
│       └── VF-TLP: ANSI/ESD SP5.5.2 (1-10ns, 模擬 CDM 時域)
│
└── 系統級 (System Level) ← AEC-Q101 不管轄, OEM/Tier1 負責
    ├── IEC 61000-4-2 — ESD 抗擾
    │   └── 150pF / 330Ω, 接觸/空氣放電
    ├── IEC 61000-4-4 — EFT 電快速暫態
    │   └── 5/50ns 脈衝群
    ├── IEC 61000-4-5 — Surge 浪涌
    │   └── 1.2/50μs (開路) + 8/20μs (短路) 組合波
    └── ISO 10605 — 車用系統級 ESD
        └── 150pF/330Ω + 330pF/330Ω, 比 IEC 更嚴格
```

### 3.2 元件級 ESD 模型比較

| 項目 | HBM | CDM | TLP |
|------|-----|-----|-----|
| **模擬場景** | 人體接觸放電 | 帶電元件接地放電 | 特性量測工具 |
| **等效電路** | 100pF / 1500Ω | 器件自身電容 / 低阻 | 充電同軸傳輸線 |
| **脈衝特徵** | ~150ns 衰減 | <1ns 上升, ~1ns 寬 | 100ns 方波 |
| **輸出** | Pass/Fail 分級 | Pass/Fail 分級 | I-V 曲線 |
| **AEC-Q101** | E3 (Q101-001A) | E4 (Q101-005A) | 不在 Q101 |
| **標準** | JS-001 | JS-002 | STM5.5.1 |

### 3.3 IEC 61000-4-2 ESD 等級

| Level | 接觸放電 | 空氣放電 | 峰值電流 (接觸) |
|-------|---------|---------|----------------|
| 1 | ±2 kV | ±2 kV | 7.5 A |
| 2 | ±4 kV | ±4 kV | 15 A |
| 3 | ±6 kV | ±8 kV | 22.5 A |
| **4** | **±8 kV** | **±15 kV** | **30 A** |

- 脈衝波形：上升 0.7-1.0 ns
- **Level 4 = 車規標準要求**
- 8kV 接觸 ESD ≈ 16A TLP 電流（用於箝制電壓估算）

### 3.4 IEC 61000-4-5 Surge 等級

| Level | 開路電壓 | 短路電流 (推算) |
|-------|---------|---------------|
| 1 | ±0.5 kV | 依阻抗 |
| 2 | ±1 kV | 依阻抗 |
| 3 | ±2 kV | 依阻抗 |
| 4 | ±4 kV | 依阻抗 |

- 組合波：開路 1.2/50μs（電壓），短路 8/20μs（電流）
- TVS 的 VC@IPP 額定基於此類波形

### 3.5 箝制電壓的兩種量測標準

| 項目 | TLP 箝制電壓 | 8/20μs 箝制電壓 |
|------|-------------|----------------|
| **對應標準** | IEC 61000-4-2 (ESD) | IEC 61000-4-5 (Surge) |
| **脈衝特徵** | 上升 10ns, 寬度 100ns | 上升 8μs, 半值 20μs |
| **時間尺度** | 奈秒級 (10⁻⁹s) | 微秒級 (10⁻⁶s) |
| **代表事件** | 靜電放電 | 雷擊/電力暫態 |
| **主要用於** | ESD 保護元件 Datasheet | TVS 保護元件 Datasheet |
| **量測方式** | TLP I-V 曲線讀取 | 直接脈衝量測 VC@IPP |

### 3.6 ISO 10605 車用 ESD（補充）

| 項目 | IEC 61000-4-2 | ISO 10605 |
|------|---------------|-----------|
| 適用範圍 | 通用電子系統 | 車用電子系統 |
| 接觸放電最高 | ±8 kV (Level 4) | ±15 kV |
| 空氣放電最高 | ±15 kV (Level 4) | ±25 kV |
| 放電網路 | 150pF / 330Ω | 150pF/330Ω + 330pF/330Ω |
| 車規要求 | Level 4 為基準 | 視安裝位置和環境 |

---

## 4. PANJIT 產品線 — 動態參數涵蓋度矩陣

| 功能 | trr | CJ | Qg | Ciss | Coss/Crss | 切換時間 | ZZT | VC@IPP | TLP Clamp | Rd |
|------|:---:|:--:|:--:|:----:|:---------:|:--------:|:---:|:------:|:---------:|:--:|
| General Rectifier | — | — | — | — | — | — | — | — | — | — |
| Fast Recovery | O* | — | — | — | — | — | — | — | — | — |
| Ultra Fast Recovery | O* | — | — | — | — | — | — | — | — | — |
| Super Fast Recovery | O* | — | — | — | — | — | — | — | — | — |
| Hyper Fast Recovery | O* | — | — | — | — | — | — | — | — | — |
| FRED | O* | — | — | — | — | — | — | — | — | — |
| Small Signal Switch | O* | O* | — | — | — | — | — | — | — | — |
| Schottky | — | — | — | — | — | — | — | — | — | — |
| SiC Diode | — | D(QC,C) | — | — | — | — | — | — | — | — |
| Zener | — | — | — | — | — | — | O* | — | — | — |
| TVS (Standard) | — | D | — | — | — | — | — | O* | — | D |
| Load Dump TVS | — | D | — | — | — | — | — | O* | — | D |
| ESD Protection | — | O* | — | — | — | — | — | — | D | — |
| MOSFET | — | — | O* | O* | D | D | — | — | — | — |
| Super Junction MOS | — | — | O* | O* | D | D | — | — | — | — |
| IGBT | — | — | D | — | — | D | — | — | — | — |
| BJT | — | — | — | — | — | D | — | — | — | — |
| Bridge Rectifier | O* | — | — | — | — | — | — | — | — | — |
| Schottky Bridge | — | — | — | — | — | — | — | — | — | — |

> **O*** = 概覽頁列出（選型關鍵參數）
> **D** = 僅 Datasheet 內提供（詳細規格）
> **—** = 不適用或不列出

---

## 5. 與 AEC-Q101 的關係

### 5.1 AEC-Q101 涵蓋的動態/功能性測試

| 測試 | 編號 | 適用元件 | 性質 | 是否為動態參數量測 |
|------|------|---------|------|------------------|
| Pre/Post-Stress Electrical | E1 | 全部 | Appendix 5 靜態 DC 參數最低要求 | **否** |
| Parametric Verification | E2 | 全部 (Part-specific) | 依 user spec 全參數驗證 | **可能**（由 user spec 決定） |
| ESD HBM | E3 | 全部 | 元件級 ESD Pass/Fail | **否**（Pass/Fail，非參數量測） |
| ESD CDM | E4 | 全部 | 元件級 ESD Pass/Fail | **否**（Pass/Fail，非參數量測） |
| UIS | E5 | Power MOS + IGBT | 雪崩耐受應力測試 | **否**（應力測試，非參數量測） |
| Short Circuit | E6 | Smart Power | 短路耐受應力測試 | **否**（應力測試，非參數量測） |

### 5.2 AEC-Q101 不涵蓋但實務上必要的動態特性

| 類別 | 參數 | 歸屬 |
|------|------|------|
| 切換特性 | trr, Qrr, Qg, td/tr/tf, Eon/Eoff | 元件 Datasheet（廠商定義） |
| 寄生電容 | Ciss, Coss, Crss, CJ, QC | 元件 Datasheet（廠商定義） |
| 動態阻抗 | ZZT, ZZK, Rd | 元件 Datasheet（廠商定義） |
| 箝制特性 | VC@IPP, TLP Clamping | 元件 Datasheet + IEC 61000 系統規格 |
| TLP 特性 | I-V 曲線 | ANSI/ESD STM5.5.1（設計工具） |
| 系統級 ESD | IEC 61000-4-2 通過等級 | OEM/Tier1 系統規格 |
| 系統級 Surge | IEC 61000-4-5 通過等級 | OEM/Tier1 系統規格 |
| 車用系統 ESD | ISO 10605 通過等級 | OEM/Tier1 系統規格 |

### 5.3 設計哲學總結

```
AEC-Q101 的邊界：
┌─────────────────────────────────────────────────────┐
│  元件可靠性驗證                                       │
│  ├── 靜態參數（E1 最低要求 — Appendix 5）              │
│  ├── 全參數驗證（E2 指向 user spec）                   │
│  ├── 元件級 ESD（E3 HBM + E4 CDM — Pass/Fail）        │
│  └── 功能專屬應力（E5 UIS + E6 SC）                    │
└─────────────────────────────────────────────────────┘
                          ↕
            AEC-Q101 不介入的領域
┌─────────────────────────────────────────────────────┐
│  動態參數定義（Datasheet 規格）                         │
│  ├── 由元件廠商根據業界慣例定義                          │
│  ├── 測試方法依循 MIL-STD-750 / JEDEC / ANSI/ESD       │
│  └── 測試條件 = 方法固定 + 施加值依靜態額定決定            │
│                                                       │
│  系統級防護驗證                                         │
│  ├── IEC 61000-4-2 (ESD) / 4-4 (EFT) / 4-5 (Surge)  │
│  ├── ISO 10605 (車用 ESD)                              │
│  └── 由 OEM/Tier1 在系統設計時負責                      │
└─────────────────────────────────────────────────────┘
```

---

## 修訂記錄

| 日期 | 內容 |
|------|------|
| 2026-02-24 | 初始建立：5 大章節，涵蓋 19 種功能、10+ 種動態參數、ESD/Surge 標準體系 |
