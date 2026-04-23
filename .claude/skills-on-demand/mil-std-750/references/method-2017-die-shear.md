# MIL-STD-750 Method 2017 — Die Attach Integrity (Die Shear Test)

> **來源**：MIL-STD-750-2B w/Change 3 (750F 體系), Method 2017.3
> **舊版**：MIL-STD-750D Method 2017.2 (1995) — 數值標準完全一致，僅版本號升級
> **檔案位置**：`projects/aec-q-standards/vault/originals/MIL-STD-750F/MIL-STD-750-2B(3).pdf` pages 23-28
> **圖片位置**：`projects/aec-q-standards/workspace/memos/figure_2017_4.png`
> **最後更新**：2026-03-27（750D→750F 比對確認，數值無變化）

---

## 1. 目的 (Purpose)

測試半導體晶粒（die）與封裝基座（package header）或基板（substrate）之間的
黏著完整性（die attach integrity）。

---

## 2. 測試設備 (Apparatus)

| 項目 | 規格 |
|------|------|
| 力量量測精度 | ±5% of full scale 或 ±50 gf，取較小值 |
| 力量施加方式 | 圓形測力計（circular dynamometer）或線性運動力量施加儀 |
| 接觸工具 | 需施加**均勻分佈**的力到 die 邊緣（見 Figure 2017-1） |
| 垂直度 | 工具面須**垂直**於 die 安裝平面（見 Figure 2017-3） |
| 旋轉能力 | 可旋轉以確保工具與 die 邊緣**端對端接觸**（見 Figure 2017-2） |
| 顯微鏡 | 雙目，最低 **10X** 放大，充足照明 |
| 小晶粒選項 | die 面積 < 25.5 × 10⁻⁴ in² (1.645 mm²)：可用手持工具替代校準儀器 |

---

## 3. Test Condition A — Die Shear（主要方法）

### 3.1 程序

- 施力**平行於** header/substrate 平面
- 施力方向**垂直於** die 邊緣
- 矩形 die：力施加於**較長邊的垂直方向**
- 施力從零**漸增**到指定值
- 工具接觸最接近 90° 的 die 邊緣（見 Figure 2017-3）
- 施力直到 die 剪斷或達到 **2× 最小剪切力**（取先發生者）
- **破壞性測試**

### 3.2 失效判定 (Failure Criteria) — 四級判定

| 條件 | 力量 | 附著面積 | 判定 |
|------|------|---------|------|
| A | < **1.0X** (Figure 2017-4 最小值) | 不論 | **FAIL** |
| B | < **1.25X** 最小值 | 附著 < **50%** die attach area | **FAIL** |
| C | < **1.5X** 最小值 | 附著 < **25%** die attach area | **FAIL** |
| D | < **2.0X** 最小值 | 附著 < **10%** die attach area | **FAIL** |

### 3.3 合格判定 (Acceptance Criteria)

| 條件 | 判定 |
|------|------|
| 施力 ≥ **2.0X** 最小值仍未剪斷 | **PASS** |
| 剪斷後殘留 ≥ **50%** 半導體材料在 die attach area（僅限 die < 1.645 mm²） | **PASS** |

> **NOTE**：離散區域的殘留半導體材料也算入附著面積

### 3.4 分離類別 (Separation Categories)

| 類別 | 描述 |
|------|------|
| a | Die 剪斷，基板上**有殘留矽** |
| b | Die 從 die attach 材料**脫離** |
| c | Die + die attach 材料一起從封裝**脫離** |

---

## 4. Figure 2017-4 — Die Shear 最小剪切力對照表

### 座標軸

- **X 軸**：Die Area（單位：×10⁻⁴ in²）
- **Y 軸**：Force（單位：Kg）
- **四條曲線**：1.0X（最小值）、1.25X、1.5X、2.0X

### 重要規則

> **Die Area > 64 × 10⁻⁴ in² (4.129 mm²) 時，最小剪切力固定為 2.5 Kg (1.0X)**

### 從圖表讀取的 1.0X 最小剪切力數值（近似值）

| Die Area (×10⁻⁴ in²) | Die Area (mm²) | 1.0X Min Force (Kg) | 1.25X (Kg) | 1.5X (Kg) | 2.0X (Kg) |
|----------------------|----------------|---------------------|------------|-----------|-----------|
| 1.5 | 0.097 | ~0.06 | ~0.08 | ~0.09 | ~0.12 |
| 5 | 0.323 | ~0.15 | ~0.19 | ~0.23 | ~0.30 |
| 10 | 0.645 | ~0.35 | ~0.44 | ~0.53 | ~0.70 |
| 15 | 0.968 | ~0.55 | ~0.69 | ~0.83 | ~1.10 |
| 20 | 1.290 | ~0.70 | ~0.88 | ~1.05 | ~1.40 |
| 25 | 1.613 | ~0.85 | ~1.06 | ~1.28 | ~1.70 |
| 30 | 1.935 | ~1.05 | ~1.31 | ~1.58 | ~2.10 |
| 40 | 2.581 | ~1.40 | ~1.75 | ~2.10 | ~2.80 |
| 50 | 3.226 | ~1.75 | ~2.19 | ~2.63 | ~3.50 |
| 60 | 3.871 | ~2.15 | ~2.69 | ~3.23 | ~4.30 |
| ≥64 | ≥4.129 | **2.50** | **3.13** | **3.75** | **5.00** |

> **注意**：以上數值為從圖表目視讀取的近似值。正式判定應以官方圖表為準。
> **圖片檔**：`projects/aec-q-standards/workspace/memos/figure_2017_4.png`

### 簡易公式（近似）

對於 Die Area ≤ 64 × 10⁻⁴ in² (4.129 mm²)：

```
1.0X Min Force (Kg) ≈ 0.037 × Die Area (×10⁻⁴ in²) + 0.05

或以 mm² 計算：
1.0X Min Force (Kg) ≈ 0.57 × Die Area (mm²) + 0.05
```

> 這是線性近似，實際曲線略微非線性。

---

## 5. Test Condition B — Mechanical Impact（機械衝擊法）

### 適用條件
- Die 面積 ≥ 0.25 in²（約 161 mm²）
- 一側或兩側有冶金鍵合（metallurgical bond）的 die

### 程序
1. Die 組件放置在適當砧座上
2. 用球頭錘（ball peen hammer）敲碎矽
3. 矽不會附著在有 void 的區域
4. 目視檢查 void 的大小與密度
5. 與建立的視覺標準比較

### Condition B 失效判定

| 條件 | 判定 |
|------|------|
| 任何**單一 void** 面積 > **3%** 的總 die 面積 | **FAIL** |
| 所有 **void 面積總和** > **6%** 的總 die 面積 | **FAIL** |

---

## 6. 與 AEC-Q101 的關聯

| Q101 項目 | 代號 | 引用 | 樣品數 | 說明 |
|-----------|------|------|--------|------|
| C5 | DS (Die Shear) | MIL-STD-750-2 **M2017** | 5 × 1 lot | Process change 前後比較 |

### Q101 中 Die Shear 的使用場景

1. **初始認證 (Qualification)**：必須執行 C5
2. **製程變更**：Die Attach 材料/方法變更時需重新測試
3. **DPA (Destructive Physical Analysis)**：C1 DPA 中包含 die attach 評估

---

## 7. 實務注意事項

### 測試操作要點
- 工具不可在施力過程中**上下移動**接觸到 header/substrate
- 如工具滑過 die，可替換新 die 或重新定位
- 矩形 die 優先對**長邊垂直方向**施力
- 受封裝限制時，可測試任何可用的 die 邊

### 常見失效模式解讀

| 分離類別 | 可能原因 | 改善方向 |
|---------|---------|---------|
| Die 剪斷有殘矽 (a) | 正常良好的 die attach | 最佳結果 |
| Die 從 attach 脫離 (b) | Die attach 材料或製程問題 | 檢查 D/A 材料、溫度 profile |
| Die+attach 從封裝脫離 (c) | Leadframe/header 表面處理問題 | 檢查 plating、清潔度 |

---

## 來源文件

| 文件 | 頁碼 | 內容 |
|------|------|------|
| MILSTD750.pdf Page 109 | Method 2017.2 第 1 頁 | 目的、設備、程序 |
| MILSTD750.pdf Page 110 | Method 2017.2 第 2 頁 | 失效/合格判定、分離類別 |
| MILSTD750.pdf Page 111 | Method 2017.2 第 3 頁 | Figure 2017-1, 2017-2, 2017-3 |
| MILSTD750.pdf Page 112 | Method 2017.2 第 4 頁 | **Figure 2017-4** 剪切力對照圖 |
| MILSTD750.pdf Page 113 | Method 2017.2 第 5/6 頁 | Test Condition B 機械衝擊法 |
