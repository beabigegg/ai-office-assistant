---
name: batch-refactor
scope: generic
tracking: tracked
description: |
  WHAT：大量變更任務的兩階段模式（Architect 出計畫 → general-purpose sub-agent 照單執行）。
  WHEN：單次任務需要修改 ≥5 個檔案、改動類型重複性高、需要 Leader 抽身做監督而非 hands-on。
  NOT：需要跨檔案深度推理的重構（Leader 親自做）；單檔少量編輯（Leader 直接 Edit）。
triggers:
  - 大量變更, 批次重構, batch refactor, 統一格式
  - EVO 變更計畫, 架構演進, 系統升級
  - 多檔案編輯, 跨檔修改, 重複性修改
  - architect 委派, general-purpose agent, sub-agent 執行
  - 兩階段模式, 計畫與執行分離
---

# Batch Refactor — 兩階段變更模式

> 適用於大量但重複的系統變更。Architect 專注於「想清楚」，executor 專注於「照做」。
> 核心價值：Leader 不用親手改每一個檔案，也不用擔心 executor 做出額外判斷。

---

## 觸發條件（何時選此模式）

**全部滿足時才走兩階段**：

1. 需要修改的檔案數 ≥ 5
2. 變更類型是**模式化**的（格式統一、路徑替換、欄位補全等），不需要 case-by-case 領域判斷
3. 變更可以被具體描述為「替換 X 為 Y」「新增欄位 Z」「刪除節 W」，不含「看情況決定」的步驟
4. Leader 希望抽身處理其他任務或做監督

## 不觸發條件（何時 Leader 直接做）

- 改 1-4 個檔案 → Leader 自己 Edit 比較快
- 每個檔案的改法都不一樣、需要讀完才能決定 → Architect 出計畫也要讀完，倒不如 Leader 親自做
- 需要跨檔案推理（A 改完後 B 的改法才確定）→ 兩階段會卡住
- 改動涉及敏感邏輯（資料庫 schema、認證、金流等）→ Leader 親自改並當下 review

---

## 兩階段流程

### Stage 1：Architect 出計畫

Leader 用自然語言描述需求，Architect 產出一份 `.md` 計畫文件寫入 `shared/kb/memory/`。

**計畫文件必須包含**：

1. **分節結構**：每節對應一個邏輯變更群，節之間用 `---` 分隔
2. **每個編輯點給出絕對路徑**（Windows `d:/...` 或 POSIX `/d/...`，一致即可）
3. **每個 Edit 提供 old_string / new_string**，old_string 有足夠上下文確保唯一
4. **新建檔案給完整內容**（整份，不要只給片段）
5. **bash 指令（刪除、移動）單獨列出**（不混入 Edit）
6. **執行順序總覽**放在文件開頭
7. **結束時提供 evolution_log.md 條目草稿**

### Stage 2：general-purpose sub-agent 執行

Leader 委派 general-purpose agent，brief 格式：

```
請照計畫執行：
- 計畫路徑：d:/ai-office/shared/kb/memory/{plan_name}.md
- 執行範圍：節 X 到節 Y（或「全部」）
- 順序：按計畫「執行順序總覽」走
- 原則：不要做計畫外的判斷，遇到 old_string 不唯一或檔案不存在時停下來回報
- 完成後：列出所有動到的檔案 + 簡短確認
```

---

## Architect Brief 模板

Leader 呼叫 Architect 時應提供：

```
任務：<一句話說明，e.g., 「統一 20 個 SKILL.md 格式」>

背景：
- 為什麼要做（e.g., EVO-016 收尾、發現格式漂移）
- 相關的先前決策或 EVO 編號
- 使用者明確的需求點

產出需求：
- 計畫文件寫入：d:/ai-office/shared/kb/memory/{name}.md
- 只做分析與計畫，不修改任何檔案
- 格式：節狀（每節對應一個變更群）+ old_string/new_string 精確到可直接套用

需要 Architect 先讀取的檔案清單：
- <絕對路徑1>
- <絕對路徑2>
- ...
```

---

## Sub-agent 選型指引

| 情境 | 選型 |
|------|------|
| 純粹按計畫替換字串、新建/刪除檔案 | **general-purpose**（最通用、最便宜） |
| 需要寫 Python/Node script 處理資料 | general-purpose（仍適合） |
| 需要 SQL 查大量資料 | `query-runner` |
| Office 檔案產出 | `office-report-engine` |
| 架構判斷或掃描 | `architect`（不要在執行階段再用 architect） |

**不要用的情境**：
- 需要「邊做邊判斷規格」→ 該讓 Leader 或 architect 在計畫階段決定，不要交給 executor

---

## 驗收原則（Leader 不用讀每個檔案就能確認完成）

Executor 回報後，Leader 做 3 項快速檢查：

### 1. 清單對位

讓 executor 列出所有動到的檔案，數量應等於計畫中提到的檔案數（±1 可接受，例如計畫漏算 _skill_template）。

### 2. 關鍵檔案抽樣

抽 2-3 個代表性檔案用 `Read` 工具確認：

- 格式類變更 → 檢查 frontmatter 是否符合計畫範本
- 路徑替換 → grep 舊路徑應為 0 命中
- 新建檔案 → 確認存在且首 30 行符合計畫內容

### 3. Validator 或 functional test

- SKILL.md 改動 → 跑 `python shared/tools/kb.py build-edges`（會掃 skills 引用）
- validator 改動 → 跑對應 workflow 的該節點（e.g., `coordinator.py start post_task`）
- 新 workflow 節點 → 跑一次 workflow 確認不會當

若三項通過 → 結案 + 寫 evolution_log 條目。

---

## 反例（以前的坑）

- **不要在計畫中寫「依情況調整」**：executor 會卡住或做出不一致的選擇
- **不要讓 executor 決定檔案要不要改**：決策都在計畫裡做完
- **不要 old_string 太短**：可能重複命中，editor 會失敗或改錯地方
- **不要混 Edit 和 bash 指令**：分開列清楚，否則 executor 順序會錯
- **不要跳過 Read**：Architect 必須先 Read 才能給精確的 old_string，即使要花 token

---

## 範例：EVO-016

本次 EVO-016 就是最典型的 batch-refactor：

- 20 個 SKILL.md 格式統一
- 3 個 validator 切 DB
- kb.py 吸收 kb_index.py 4 個指令
- 計畫文件：`shared/kb/memory/evo016_change_plan.md`
- Architect 階段：讀完所有相關檔案後產出精確計畫
- Executor 階段：general-purpose agent 逐節套用 Edit/Write/Bash
