---
name: automotive-reliability-standards
scope: generic
tracking: tracked
description: |
  WHAT：汽車電子可靠性測試的通用標準層查詢入口。
  WHEN：查 AEC-Q101 / AEC-Q006 / JESD22 / MIL-STD-750 / MIL-STD-883 的測試結構、方法對照、樣品數、fail criteria、grade 定義。
  NOT：公司內部規範映射、F-PE0404、ECR/ECN 套用層請改讀 internal-reliability-practice。
triggers:
  - AEC-Q101, AEC-Q006, Q101, Q006, 可靠性, qualification, 認證
  - HAST, H3TRB, HTSL, HTGB, TC, Temperature Cycling
  - HBM, CDM, WBS, WBP, Die Shear, Terminal Strength
  - JESD22, MIL-STD-750, MIL-STD-883, J-STD-020
  - sample size, fail criteria, release criteria, family definition
---

# Automotive Reliability Standards

## 路由

| 問題類型 | 讀取 |
|---------|------|
| Q101 完整測試項目（A1-E6 條件/樣品數/標準） | `references/q101-q006-test-details.md` §AEC-Q101 |
| Q006 銅線驗證（Table 3 序列/Option 1 vs 2/Release Criteria/Family） | `references/q101-q006-test-details.md` §AEC-Q006 |
| 失效定義（漂移/漏電/RDSon 判定門檻） | `references/q101-q006-test-details.md` §失效定義 |
| 樣品數與允收標準（77×3 lots 統計意義） | `references/q101-q006-test-details.md` §樣品數 |
| HBM/CDM ESD 分級、WBS 最低力、UIS/DPA、Short Circuit | `references/test-methods-detail.md` |

## 核心範圍

- Q101 / Q006 test group 結構
- JESD22 / MIL-STD 方法對照
- HAST / H3TRB / HTSL / HTGB 差異
- WBP / WBS / DS / TS method mapping
- Grade 0/1/2/3 定義
- sample size / release criteria / family definition

## 不含內容

- F-PE0404
- 公司內部測試佈局
- ECR / ECN 變更映射
- 特定產品線偏好或內部裁剪

## 備註

本 skill 只保留 generic standards core。若問題已進入公司內部套用層，改讀 `internal-reliability-practice`。

## 已完成拆分

- generic references 已搬入本 skill 的 `references/`
- 舊 `reliability-testing/` 名稱僅保留為 compat shim；新引用應直接指向本 skill
