# MIL-STD-750 完整測試方法清單（Part 1-5）

> 本文件涵蓋 MIL-STD-750 全部五個 Part 的測試方法編號。
> SKILL.md 僅保留結構摘要與路由表，詳細清單在此。

---

## Part 1: 環境測試 (1000 Series)

| Method | 名稱 | 說明 |
|--------|------|------|
| 1001 | Barometric Pressure (Reduced) | 低氣壓測試 |
| 1011 | Immersion | 浸水測試 |
| 1015 | Steady-State Primary Photocurrent Irradiation | 電子束輻射 |
| 1016 | Insulation Resistance | 絕緣電阻 |
| 1017 | Neutron Irradiation | 中子輻射 |
| 1018 | Internal Gas Analysis | 內部氣體分析 |
| 1019 | Steady-State Total Dose Irradiation | 累積輻射劑量 |
| 1020 | ESD Sensitivity Classification | 靜電放電敏感度分級 |
| 1021 | Moisture Resistance | 耐濕性 |
| 1022 | Resistance to Solvents | 耐溶劑性 |
| 1026 | Steady-State Operation Life | 穩態工作壽命 |
| 1027 | Steady-State Operation Life (Sample Plan) | 穩態壽命抽樣計劃 |
| 1031 | High-Temperature Life (Non-operating) | 高溫儲存壽命 |
| 1032 | High-Temperature Life (Sample Plan) | 高溫壽命抽樣計劃 |
| 1033 | Reverse Voltage Leakage Stability | 反向漏電穩定性 |
| 1036 | Intermittent Operation Life | 間歇工作壽命 |
| 1037 | Intermittent Operation Life (Sample Plan) | 間歇壽命抽樣 (Q101 A5) |
| 1038 | Burn-In (Diodes, Rectifiers, Zeners) | 二極體老化篩選 (Q101 B1) |
| 1039 | Burn-In (Transistors) | 電晶體老化篩選 |
| 1040 | Burn-In (Thyristors) | 閘流體老化篩選 (Q101 B1a) |
| 1041 | Salt Atmosphere (Corrosion) | 鹽霧腐蝕 |
| 1042 | Burn-In/Life Test (Power MOSFETs/IGBT) | MOSFET/IGBT 老化壽命 |
| 1046 | Salt Spray (Corrosion) | 鹽水噴霧腐蝕 |
| 1048 | Blocking Life | 阻斷壽命 |
| 1049 | Blocking Life (Sample Plan) | 阻斷壽命抽樣 |
| 1051 | Temperature Cycling (Air to Air) | 溫度循環 (Q101 A4 引用 JESD22) |
| 1054 | Potted Environment Stress Test | 灌膠環境應力 |
| 1055 | Monitored Mission Temperature Cycle | 監控任務溫循 |
| 1056 | Thermal Shock (Liquid to Liquid) | 液態熱衝擊 |
| 1057 | Resistance to Glass Cracking | 玻璃抗裂性 |
| 1061 | Temperature Measurement (Case/Stud) | 外殼/螺柱溫度量測 |
| 1066 | Dew Point | 露點 |
| 1071 | Hermetic Seal | 氣密性測試 |
| 1080 | Single Event Burnout/Gate Rupture | 單粒子事件測試 |
| 1081 | Dielectric Withstanding Voltage | 介電耐壓 |

---

## Part 2: 機械特性測試 (2000 Series)

| Method | 名稱 | 說明 |
|--------|------|------|
| 2005 | Axial Lead Tensile Test | 軸向引線拉伸 |
| 2006 | Constant Acceleration | 恆加速度 |
| 2016 | Shock | 機械衝擊 |
| **2017** | **Die Attach Integrity (Die Shear)** | **晶粒剪切強度** (Q101 C5) → [詳細規格](method-2017-die-shear.md) |
| 2026 | Solderability | 可焊性 |
| 2031 | Resistance to Soldering Heat | 耐焊接熱 |
| **2036** | **Terminal Strength** | **端子強度** (Q101 C6) |
| **2037** | **Bond Strength (Wire Bond Pull)** | **銲線拉力** (Q101 C3) → [詳細規格](method-2037-bond-strength.md) |
| 2038 | Surface Mount End Cap Bond Integrity | SMD 端帽接合完整性 |
| 2046 | Vibration Fatigue | 振動疲勞 |
| 2051 | Vibration Noise | 振動噪音 |
| 2052 | PIND (Particle Impact Noise Detection) | 粒子衝擊噪音偵測 |
| 2056 | Vibration, Variable Frequency | 可變頻率振動 |
| 2057 | Vibration, Variable Frequency (Monitored) | 監控式可變頻率振動 |
| 2066 | Physical Dimensions | 物理尺寸 |
| 2068 | External Visual (Glass-Encased Diodes) | 外觀檢查-玻璃封裝 |
| 2069 | Pre-Cap Visual (Power MOSFETs) | 封蓋前檢查-MOSFET |
| 2070 | Pre-Cap Visual (Microwave Transistors) | 封蓋前檢查-微波電晶體 |
| 2071 | External Visual & Mechanical Exam | 外觀及機械檢查 |
| 2072 | Internal Visual Transistor (Pre-Cap) | 電晶體內部目檢 |
| 2073 | Visual Inspection (Unencapsulated Diode Die) | 裸晶二極體目檢 |
| 2074 | Internal Visual (Discrete Diodes) | 二極體內部目檢 |
| 2075 | Decap Internal Visual Design Verification | 開封內部設計驗證 |
| **2076** | **Radiography** | **X 光檢查** → [Cougar EVO 符合性](x-ray-cougar-evo-compliance.md) |
| 2077 | SEM Inspection of Metallization | 金屬化 SEM 檢查 |
| 2078 | Internal Visual (Wire Bonded Diodes) | 銲線二極體內部目檢 |
| 2081 | Forward Instability Shock Test (FIST) | 正向不穩定衝擊 |
| 2082 | Backward Instability Vibration (BIST) | 反向不穩定振動 |
| 2101 | DPA Procedures for Diodes | 二極體破壞性物理分析 |
| 2102 | DPA for Wire Bonded Devices | 銲線元件 DPA |
| 2103 | Design Verification (Surface Mount) | SMD 設計驗證 |

---

## Part 3: 電晶體電氣測試 (3000 Series)

### 3000 — 雙極電晶體基本特性 (Bipolar Transistor Characteristics)

| Method | 名稱 | 說明 |
|--------|------|------|
| 3001 | Breakdown Voltage, Collector to Base | 集極-基極崩潰電壓 |
| 3011 | Breakdown Voltage, Collector to Emitter | 集極-射極崩潰電壓 |
| 3026 | Breakdown Voltage, Emitter to Base | 射極-基極崩潰電壓 |
| 3036 | Collector to Base Cutoff Current | 集極-基極截止電流 |
| 3041 | Collector to Emitter Cutoff Current | 集極-射極截止電流 |
| 3051 | Safe Operating Area (Continuous DC) | 安全工作區-直流 |
| 3053 | Safe Operating Area (Switching) | 安全工作區-開關 |
| 3061 | Emitter to Base Cutoff Current | 射極-基極截止電流 |
| 3066 | Base to Emitter Voltage (Sat/Non-Sat) | 基極-射極電壓 |
| 3071 | Saturation Voltage and Resistance | 飽和電壓與電阻 |
| 3076 | Forward-Current Transfer Ratio | 正向電流轉移比 (hFE) |

### 3100 — 電路性能與熱阻 (Circuit Performance & Thermal Resistance)

| Method | 名稱 | 說明 |
|--------|------|------|
| 3100 | Junction Temperature at Burn-In/Life Test | 老化/壽命測試時接面溫度量測 |
| 3101 | Thermal Impedance & Response (Diodes) | 二極體熱阻抗與熱響應 |
| 3131 | Thermal Impedance (Transistors, Delta VBE) | 電晶體熱阻抗 (ΔVBE 法) |
| 3161 | Thermal Impedance (Power MOSFETs, Delta VSD) | MOSFET 熱阻抗 (ΔVSD 法) |
| 3181 | Thermal Resistance (Thyristors) | 閘流體熱阻 |

### 3200 — 低頻測試 (Low Frequency Tests)

| Method | 名稱 | 說明 |
|--------|------|------|
| 3201 | Small-Signal Short-Circuit Input Impedance | 小訊號短路輸入阻抗 |
| 3206 | Small-Signal SC Forward-Current Transfer Ratio | 小訊號短路正向電流轉移比 |
| 3211 | Small-Signal OC Reverse-Voltage Transfer Ratio | 小訊號開路反向電壓轉移比 |
| 3216 | Small-Signal Open-Circuit Output Admittance | 小訊號開路輸出導納 |
| 3236 | Open Circuit Output Capacitance | 開路輸出電容 |
| 3240 | Input Capacitance (Output OC or SC) | 輸入電容 |
| 3246 | Noise Figure | 噪聲指數 |
| 3251 | Pulse Response | 脈衝響應 |

### 3300 — 高頻測試 (High Frequency Tests)

| Method | 名稱 | 說明 |
|--------|------|------|
| 3301 | SS SC Forward-Current Transfer-Ratio Cutoff Freq | fT 截止頻率 |
| 3306 | SS SC Forward-Current Transfer Ratio (HF) | 高頻正向電流轉移比 |

### 3400 — MOS 場效電晶體測試 (MOSFET Tests)

| Method | 名稱 | 說明 |
|--------|------|------|
| 3401 | Breakdown Voltage, Gate to Source | 閘極-源極崩潰電壓 (V(BR)GSS) |
| 3403 | Gate to Source Voltage or Current | 閘極-源極電壓/電流 |
| 3405 | Drain to Source On-State Voltage | 汲極-源極導通電壓 |
| 3407 | Breakdown Voltage, Drain to Source | 汲極-源極崩潰電壓 (V(BR)DSS) |
| 3411 | Gate Reverse Current | 閘極反向電流 (IGSS) |
| 3413 | Drain Current | 汲極電流 (IDSS) |
| 3421 | Static Drain-Source On-State Resistance | 靜態導通電阻 (RDS(on)) |
| 3423 | Small-Signal Drain-Source On-State Resistance | 小訊號導通電阻 |
| 3470 | Single Pulse Unclamped Inductive Switching | 單脈衝無箝位感性開關 (UIS) |
| 3471 | Gate Charge | 閘極電荷 (Qg) |
| 3472 | Switching Time Test | 開關時間測試 |
| 3473 | Reverse Recovery Time (trr ≤ 100ns) | 反向恢復時間 (Body Diode) |
| 3474 | Safe Operating Area (Power MOSFET/IGBT) | MOSFET/IGBT 安全工作區 |
| 3475 | Forward Transconductance (Pulsed DC) | 正向跨導 (gfs) |
| 3476 | dv/dt During Reverse Recovery | 反向恢復期間 dv/dt |

---

## Part 4: 二極體電氣測試 (4000 Series)

### 4000 — 二極體基本電氣特性

| Method | 名稱 | 說明 |
|--------|------|------|
| 4000 | Condition for Measurement of Diode Static Params | 二極體靜態參數量測條件 |
| 4001 | Capacitance | 電容 |
| 4011 | Forward Voltage | 正向電壓 (VF) |
| 4016 | Reverse Current Leakage | 反向漏電流 (IR) |
| 4021 | Breakdown Voltage (Diodes) | 崩潰電壓 (VBR) |
| 4022 | Breakdown Voltage (Voltage Regulators/Zeners) | 穩壓管崩潰電壓 (VZ) |
| 4023 | Scope Display | 示波器波形顯示 |
| 4026 | Forward Recovery Voltage & Time | 正向恢復電壓與時間 |
| 4031 | Reverse Recovery Characteristics | 反向恢復特性 (trr) |
| 4036 | Q for Voltage Variable Capacitance Diodes | 變容二極體 Q 值 |
| 4041 | Rectification Efficiency | 整流效率 |
| 4046 | Reverse Current, Average | 平均反向電流 |
| 4051 | Small-Signal Reverse Breakdown Impedance | 小訊號反向崩潰阻抗 |
| 4056 | Small-Signal Forward Impedance | 小訊號正向阻抗 |
| 4061 | Stored Charge | 儲存電荷 |
| 4065 | Peak Reverse Power Test | 峰值反向功率 |
| 4066 | Surge Current & Impulse Clamp Voltage | 浪湧電流與脈衝箝位電壓 |
| 4071 | Temperature Coefficient of Breakdown Voltage | 崩潰電壓溫度係數 |
| 4076 | Saturation Current | 飽和電流 |
| 4081 | Thermal Resistance (Forward Voltage, Switching) | 熱阻（正向電壓/開關法） |

### 4200 — 閘流體測試 (Thyristor / SCR Tests)

| Method | 名稱 | 說明 |
|--------|------|------|
| 4201 | Holding Current | 維持電流 (IH) |
| 4206 | Forward Blocking Current | 正向阻斷電流 |
| 4211 | Reverse Blocking Current | 反向阻斷電流 |
| 4219 | Reverse Gate Current | 反向閘極電流 |
| 4221 | Gate-Trigger Voltage | 閘極觸發電壓 |
| 4223 | Gate-Controlled Turn-On Time | 閘控導通時間 |
| 4224 | Circuit-Commutated Turn-Off Time | 電路換相關斷時間 |
| 4226 | Forward "On" Voltage | 正向導通電壓 |
| 4231 | Exponential Rate of Voltage Rise | 指數電壓上升率 (dv/dt) |

---

## Part 5: 高可靠性太空應用 (5000 Series)

| Method | 名稱 | 說明 |
|--------|------|------|
| 5001-5010 | Hi-Rel Space Application Tests | 高可靠性太空應用測試方法 |

> Part 5 的測試方法數量有限（5001-5010），主要針對太空等級元件的額外篩選和驗證要求。
> 具體內容需參閱 MIL-STD-750-5 官方文件 (2018-08-10)。

---

## 來源參考

- VPT Components DLA 認可清單
- Keystone Compliance 完整方法列表
- SMT Corp 官方引用版本
- EverySpec 標準文件庫
- NASA SSRI-KB 標準檔案庫
