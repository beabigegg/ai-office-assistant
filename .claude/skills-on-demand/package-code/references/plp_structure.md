# PLP (Panel Level Package) 編碼結構

> 來源: F-RD0215 rev20, Sheet 2 "PLP package"
> PLP = Fan-out 封裝技術，使用面板級封裝（非傳統 Lead Frame）

## PLP Full_PKG_CODE 結構 -- 8 段

PLP 封裝使用擴展的 8 段結構（比標準 6 段多 2 段）：

```
XXXXXX - X  - XX - X  - X  - X  - X  - X
  |       |    |    |    |    |    |    +-- Reserve (Sub-code)
  |       |    |    |    |    |    +------- Vendor Code
  |       |    |    |    |    +------------ Metal finish
  |       |    |    |    +----------------- RDL Layer
  |       |    |    +---------------------- Stud layer
  |       |    +--------------------------- Dielectric layer
  |       +-------------------------------- Carrier Layer
  +---------------------------------------- Package Code (XX+XX+X+X)
```

## 各段定義

### Package Code (6 chars) -- 細分為 4 個子段

```
XX  XX  X  X
|   |   |  +-- Lead forming
|   |   +----- Body thickness
|   +--------- Package size
+------------- Package type
```

**Package type (2 char)**:
| Code | 含義 |
|------|------|
| FD | Fan out DFN |
| FQ | Fan out QFN |

**Package size (2 char)**:
| Code | 尺寸 |
|------|------|
| 01 | 0.4x0.2mm ~ 0.6x0.3mm |
| 10 | 1x0.6mm ~ 1.6x1.6mm |
| 22 | 2x2mm |
| 33 | 3x3mm |
| 56 | 5x6mm |
| 88 | 8x8mm |
| 55 | 5.5x1.5mm (Rev.20 新增) |
| AB | 10x12mm |

**Body thickness (1 char)**:
| Code | 厚度 |
|------|------|
| 1 | <0.25mm |
| 2 | 0.25~0.3mm |
| 3 | 0.31~0.4mm |
| 4 | 0.41~0.5mm |
| U | 0.51~0.65mm |
| W | 0.66~0.8mm |
| V | 0.81~1.0mm |
| T | 1.01~1.2mm |
| L | 1.21~1.7mm |
| B | >1.7mm |

**Lead forming (1 char)**:
| Code | 含義 |
|------|------|
| 1 | No Lead |
| 2 | No Lead + Heat Sink |
| 3 | No Lead + Double Heat Sink |
| 4 | Flat Lead |
| 5 | Flat Lead + Heat Sink |
| 6 | Flat Lead + Double Heat Sink |
| 7 | Solder Ball |

### Carrier Layer (1 char)

| Code | 含義 |
|------|------|
| V | VCB |
| E | EGP |
| T | TMV |
| P | PTH |
| X | X-via |
| N | NA (不適用) |

### Dielectric Layer (2 chars)

| Code | 含義 |
|------|------|
| 2T | TBF |
| TS | TBF+SM |
| 3E | EMC*3 |
| NA | 不適用 |

### Stud Layer (1 char)

| Code | 含義 |
|------|------|
| 1~9 | 層數 |
| A | Au+Cu |
| N | NA (不適用) |

### RDL Layer (1 char)

| Code | 含義 |
|------|------|
| 1~9 | 層數 |

### Metal Finish (1 char)

| Code | 含義 |
|------|------|
| A | NiAu |
| S | Sn |
| G | Silver |
| O | OSP |
| B | Solder Ball |

### Vendor Code (1 char)

目前 PLP 僅一家供應商：
| Code | 供應商 |
|------|--------|
| C | PANSTAR-合肥矽邁SMAT |

### Reserve / Sub-code (1 char)

預留子碼，目前未定義。

## PLP 範例

```
FD0131-V-2T-A-1-A-C-0
```
解碼：
- FD = Fan out DFN
- 01 = 0.4x0.2mm ~ 0.6x0.3mm
- 3 = Body thickness 0.31~0.4mm
- 1 = No Lead
- V = VCB Carrier
- 2T = TBF Dielectric
- A = Au+Cu Stud
- 1 = 1 layer RDL
- A = NiAu Metal finish
- C = SMAT Vendor
- 0 = Reserve

## 與標準 Full_PKG_CODE 的差異

| 項目 | 標準封裝 | PLP 封裝 |
|------|---------|---------|
| 段數 | 6 段 | 8 段 |
| Package Code | 封裝碼 (6 chars) | 分為 type+size+thickness+lead (6 chars) |
| LF Code | 腳架材質 | **Carrier Layer** (替代腳架概念) |
| D/A Code | 焊接方式 | **Dielectric layer** |
| Wires Code | 線材 | **Stud layer + RDL Layer** (2段) |
| Compound Code | 成型膠 | **Metal finish** |
| Vendor Code | 供應商 | 供應商 (同) |
| -- | -- | **Reserve** (新增第8段) |

**重要**: PLP 結構與標準結構完全不同，不能混用解碼邏輯。
