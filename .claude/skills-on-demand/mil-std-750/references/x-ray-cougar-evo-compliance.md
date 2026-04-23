# Cougar EVO X-ray 系統 vs. MIL-STD-750 Method 2076 符合性分析

> **設備**：YXLON Cougar EVO（Comet Yxlon GmbH）
> **對照規範**：MIL-STD-750D Method 2076.3 — Radiography
> **用途**：Die Attach Void 檢測
> **最後更新**：2026-02-09
> **資料來源**：Cougar EVO 官方 Brochure (page 7 spec table) + MIL-STD-750D pp.220-226

---

## 1. Cougar EVO 完整規格

### 1.1 X-ray 源

| 項目 | FXT-160.50 Microfocus | FXT-160.51 Multifocus |
|------|----------------------|----------------------|
| 靶類型 | Transmission | Transmission |
| 靶材 | Tungsten | Tungsten |
| 電壓範圍 | 20 – 160 kV | 20 – 160 kV |
| 電流範圍 | 0.001 – 1.0 mA | 0.001 – 1.0 mA |
| 管功率 | max. 64 W | max. 64 W |
| 靶功率 | max. 15 W | max. 15 W |
| Detail detectability | 0.75 μm | < 0.3 μm |
| X-ray intensity control | TXI | TXI |

### 1.2 影像鏈（Image Chain）

| 項目 | 規格 |
|------|------|
| Geometric magnification | ~2,000x |
| Total magnification | ~256,000x |
| Spatial resolution (Microfocus) | 1.5 μm |
| Spatial resolution (Multifocus) | 0.6 μm |

### 1.3 偵測器（Detector）

| 項目 | Y.Panel 1308 | Y.Panel 1313 | ORYX 1616 |
|------|-------------|-------------|-----------|
| Pixel matrix | 1004 × 620 | 1004 × 1004 | 1276 × 1276 |
| Pixel pitch | 127 μm | 127 μm | 127 μm |
| Pixel area | 128 × 79 mm | 128 × 128 mm | 162 × 162 mm |
| A/D 解析度 | 16 bit | 16 bit | 16 bit |

### 1.4 操作性能

| 項目 | 規格 |
|------|------|
| Time to first image | ~10 s |
| Reconfiguration time | < 60 s |
| CT Quick Scan (2000 projections) 取像 | ~3.15 min |
| CT Quick Scan 重建 | ~1.55 min |
| micro3Dslice Semicon (120 projections) 取像 | ~1.45 min |
| micro3Dslice Semicon 重建 | ~0.30 min |

### 1.5 機構

| 項目 | 規格 |
|------|------|
| 最大樣品尺寸 | 440 × 550 mm (17" × 21") |
| 最大 radiographic area | 310 × 310 mm (12" × 12") |
| 最大樣品重量（標準） | 5 kg |
| 最大樣品重量（旋轉/傾斜） | 2 kg |
| 斜角觀察 | ±70° (140°) |
| 操控軸 | X, Y, Z(D)；可選水平/垂直旋轉與傾斜 |

### 1.6 軟體功能（Void 檢測相關）

| 功能 | 說明 |
|------|------|
| **MAVC** (Multi Area Void Calculation) | 多區域 void 自動面積計算，4 個參數即可設定 |
| **eHDR-Inspect** | 動態增強濾波，16-bit 灰階突顯微小對比差異 |
| **VoidInspect** | 自動 void 計算工作流程 |
| **micro3Dslice** | 層析成像（Laminography），非破壞性分層觀察 |
| **FF CT** | 完整 CT 3D 重建 |
| **FGUI** | 自動缺陷偵測介面（Bumps, Void） |
| **ProInsight** | 可開發與整合自訂演算法 |

### 1.7 系統

| 項目 | 規格 |
|------|------|
| 系統尺寸 (W×D×H) | 1,000 × 1,050 × 2,200 mm |
| 系統重量 | 1,450 kg |
| 電源 | 230 V ±10% AC, 50/60 Hz, 1 Phase |
| 保險絲 | 16 A |
| 最大功耗 | 2.5 kVA |
| 最大表面劑量率 | < 1 μSv/h（距機櫃表面 100 mm） |
| 監視器 | 27" Ultrasharp |

---

## 2. 逐項符合性比對

### 2.1 量測能力

| M2076 要求 | 規範值 | Cougar EVO | 倍率 | 判定 |
|-----------|-------|-----------|------|------|
| 影像解析度 | ≤ .001 inch (**25.4 μm**) | **0.6 μm** (Multifocus) / **1.5 μm** (Microfocus) | **17~42x** 優於規範 | **遠超** |
| 觀片放大倍率 | 6X ~ 20X | geometric ~2,000X, total ~256,000X | **100~12,800x** 優於規範 | **遠超** |
| X-ray 電壓 | ≤ 150 kV | 20 – 160 kV（**設定 ≤ 150 kV 即可**） | — | **可符合** |
| 底片密度 H&D 1.0~2.5 | 等效對比範圍 | 16-bit (65,536 灰階) | 底片約 8-bit 等效 | **遠超** |

### 2.2 非底片技術等效性（Section 3.3.1）

M2076 Section 3.3.1 允許非底片技術，需滿足三個條件：

| 條件 | M2076 要求 | Cougar EVO 對應 | 判定 |
|------|-----------|----------------|------|
| (a) 永久記錄 | 不需要永久記錄，**或**能以等效方式保存 | 數位影像可永久儲存（TIFF/BMP/專有格式），可無損複製備份 | **符合** |
| (b) 等同品質 | 設備能產出與底片技術等同品質的結果 | 解析度 0.6~1.5 μm 遠超底片，16-bit 動態範圍遠超底片 | **遠超** |
| (c) 其他要求 | 除底片條款外所有要求均須遵守 | 見下方 2.3 | **需操作配合** |

### 2.3 操作要求符合性

| M2076 操作要求 | Cougar EVO 對應方式 |
|---------------|-------------------|
| **拍攝方向**（3.1.1）：Y/X/Z 多方向 | ±70° 斜角觀察 + 多軸操控，可覆蓋所有指定方向 |
| **IQI 品質標準**（3.2）：ASTM type B 穿透計 | 需自備穿透計，初次驗證 + 定期驗證（建議每班/每批次） |
| **影像標記**（3.3）：製造商/型號/批號/日期/視角 | 軟體可自動記錄所有 metadata，並嵌入影像 |
| **判讀環境**（3.7）：低光源、無眩光 | 27" Ultrasharp 監視器，建議在遮光環境操作 |
| **人員視力**（3.6）：20/30 遠距、Jaeger No.2 近距 | 與設備無關，需維持人員視力檢查記錄（每年一次） |

---

## 3. Die Attach Void 判定標準

Cougar EVO 的 MAVC 軟體可自動計算以下 M2076 判定標準：

| 條件 | M2076 判定門檻 | MAVC 設定方式 |
|------|-------------|-------------|
| Single void 貫穿 die 長/寬 | > **10%** total intended contact area → REJECT | 設定 single void alarm threshold = 10% |
| Total void | > **50%** total contact area → REJECT | 設定 total void alarm threshold = 50% |
| Bonded area | < **75%** base area → REJECT | 等效於 total void > 25%，或直接設 bonded area threshold = 75% |

---

## 4. SOP 建議設定參數

### 4.1 操作參數

| 參數 | 建議設定 | 依據 |
|------|---------|------|
| **kV** | **≤ 150 kV**（依封裝材質調整，從低 kV 開始） | M2076 要求不超過 150 kV |
| **放大倍率** | die attach 區域 **10X ~ 100X** | 涵蓋 M2076 的 6-20X，更精確觀察 |
| **偵測器** | 建議使用 **ORYX 1616**（最大 FOV） | 減少拼接次數，提高效率 |
| **影像增強** | 啟用 **eHDR-Inspect** | 提高 void 與焊料的對比度 |

### 4.2 Void 量測參數（MAVC）

| 參數 | 建議設定 | 說明 |
|------|---------|------|
| ROI (Region of Interest) | 框選 die attach pad 區域 | 定義 total contact area |
| Void threshold | 依灰階校準 | void 通常比焊料亮（密度低） |
| Single void alarm | **10%** | 對應 M2076 判定 |
| Total void alarm | **50%** | 對應 M2076 判定 |

### 4.3 品質保證

| 項目 | 頻率 | 方法 |
|------|------|------|
| IQI 驗證 | 每班開始前 或 每批次開始前 | ASTM type B 穿透計拍攝，確認可辨識規定最小特徵 |
| GR&R | 初次導入 + 每年一次 | 標準試片（已知 void%），3 人 × 3 次量測，計算 %GR&R |
| 人員視力 | 每年一次 | 遠距 ≥ 20/30，近距可讀 Jaeger No.2（16 inch） |
| 影像備份 | 每次檢查 | 自動儲存至伺服器，保存期限依客戶/規格書要求 |

---

## 5. 說服論述框架

### 5.1 核心數據

```
                    M2076 要求        Cougar EVO         倍率
解析度              ≤ 25.4 μm        0.6 ~ 1.5 μm      17 ~ 42 倍優於規範
放大倍率            6 ~ 20X          ~2,000X (geo)      100 倍以上
灰階動態範圍        H&D 1.0~2.5      16-bit (65,536)    遠超底片能力
Void 判定           人眼判讀底片       MAVC 自動計算       更客觀、可重複
```

### 5.2 論述要點

1. **法規依據充分**：M2076 Section 3.3.1 明確允許非底片技術，條件是等同品質——Cougar EVO 在所有指標上遠超底片

2. **解析度超出規範 17~42 倍**：M2076 寫於 1995 年，當時最好的底片解析度約 25 μm；Cougar EVO 的 0.6 μm 是技術世代差距

3. **數位影像更客觀**：
   - 底片判讀依賴人眼，受光源、疲勞、經驗影響
   - MAVC 軟體自動計算 void 面積百分比，結果可重複、可追溯

4. **永久記錄完整**：數位影像可無損保存，附帶完整 metadata（時間、操作者、參數），優於底片的物理保存

5. **不需要過於嚴格**：
   - M2076 的 25.4 μm 解析度門檻是**最低要求**，不是目標
   - Cougar EVO 超出這個門檻太多，操作上只需要確保 **kV ≤ 150** 和 **IQI 驗證有記錄** 即可
   - Void 判定門檻（10%/50%/75%）是固定的，不因設備能力而改變

### 5.3 建議 SOP 聲明文字

> 本檢驗使用 YXLON Cougar EVO 數位 X-ray 檢測系統，依據 MIL-STD-750D
> Method 2076 Section 3.3.1 之非底片技術條款執行。
>
> 設備解析度 0.6 ~ 1.5 μm，超出規範要求（25.4 μm）17 倍以上；
> 16-bit 灰階動態範圍超出底片等效能力；
> MAVC 軟體提供自動化、可重複的 void 面積量測。
>
> 判定標準依 Method 2076 Section 3.9.2.1：
> - Single void 貫穿 die 長/寬且 > 10% contact area → REJECT
> - Total void > 50% contact area → REJECT
> - Bonded area < 75% base area → REJECT

---

## 6. 與其他 Void 檢測方法的搭配

| 場景 | 使用方法 | 備註 |
|------|---------|------|
| 產線 inline 檢查 | **Cougar EVO (M2076)** | 非破壞，可 100% 全檢 |
| Void 偵測靈敏度驗證 | Cougar EVO + **M3101 Thermal** | 熱測與 X-ray 交叉驗證 |
| DPA 開封後確認 | **M2074 Internal Visual** | X-ray 發現可疑品後開封確認 |
| AEC-Q101 C5 認證 | **M2017 Die Shear** | 破壞性測試，X-ray 為輔助參考 |

---

## 來源

| 來源 | 說明 |
|------|------|
| [Comet Yxlon 官方產品頁](https://yxlon.comet.tech/en/products/cougar-evo) | Cougar EVO 規格與功能介紹 |
| [Cougar EVO Brochure PDF](http://tstvn.com/wp-content/uploads/2021/07/Cougar-EVO_Brochure_eng-LR.pdf) | 官方 brochure page 7 完整規格表 |
| [efsmt.com 規格頁](https://efsmt.com/product/Yxlon-Cougar-EVO-X-ray-Inspection-Machine.html) | 規格確認 |
| [Cougar EVO SEMI Brochure](https://isodynamique.com/wp-content/uploads/2023/09/Cougar_EVO_SEMI_Product-Brochure.pdf) | 半導體版本 brochure |
| MILSTD750.pdf Pages 220-226 | Method 2076.3 Radiography 完整規範 |
