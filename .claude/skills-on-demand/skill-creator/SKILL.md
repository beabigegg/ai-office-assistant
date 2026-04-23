---
name: skill-creator
description: |
  建立新 Skill、改善現有 Skill、評測 Skill 效能。
  使用時機：從零建立新 skill、修改/優化現有 skill、執行 eval 測試、
  對 skill description 做觸發準確率最佳化（run_loop.py）、
  閱覽 eval 結果（eval-viewer）。
---

# Skill Creator（Meta-Skill）

腳本位於：`/d/ai-office/skill-creator/scripts/`
eval 閱覽器：`/d/ai-office/skill-creator/eval-viewer/`

---

## 建立 Skill 的流程

```
1. 釐清目標：要做什麼、怎麼做、輸入輸出格式
2. 撰寫草稿（SKILL.md frontmatter + 內容）
3. 寫測試提示（3-5 個 trigger prompts + 3-5 個 non-trigger prompts）
4. 執行 eval：with-skill vs baseline，平行跑
5. 評估結果：定量（pass rate）+ 定性（使用者審查）
6. 修訂 skill → 重複直到滿意
7. 擴大測試集，跑 run_loop.py 最佳化 description
```

---

## 關鍵腳本

```bash
# 執行單次 eval
PYTHONUTF8=1 "C:\Users\lin46\.conda\envs\ai-office\python.exe" \
  /d/ai-office/skill-creator/scripts/run_eval.py \
  --skill path/to/SKILL.md \
  --prompts path/to/test_cases.json

# 最佳化 description（20次觸發測試，60/40 train/test）
PYTHONUTF8=1 "C:\Users\lin46\.conda\envs\ai-office\python.exe" \
  /d/ai-office/skill-creator/scripts/run_loop.py \
  --skill path/to/SKILL.md

# 產生 HTML 結果閱覽頁
PYTHONUTF8=1 "C:\Users\lin46\.conda\envs\ai-office\python.exe" \
  /d/ai-office/skill-creator/eval-viewer/generate_review.py \
  --results path/to/eval_results.json
```

---

## Skill 格式（frontmatter 必填欄位）

```markdown
---
name: skill-name
description: |
  一段描述，告訴 Claude 何時觸發此 Skill。
  觸發詞、使用情境、適用範圍要明確。
---

# Skill 標題

## 環境 / 前提

## 主要流程

## 關鍵規則與陷阱

## 快速參考表
```

---

## 放置位置

AI Office 系統的 skills-on-demand 目錄：

```
.claude/skills-on-demand/<skill-name>/SKILL.md
```

建立後在 `report-builder.md`（或其他 agent）的 Skill Loading 表格中登記。

---

## 評估策略

| 階段 | 行動 |
|------|------|
| 草稿 | 3-5 個 trigger + 3-5 個 non-trigger 提示 |
| 初測 | 平行跑 with-skill vs baseline，比較輸出品質 |
| 量化 | 定義 pass criteria（JSON），run_eval.py 計分 |
| 優化 | run_loop.py 自動迭代 description（20 次試驗） |
| 定稿 | 擴大到 20+ 測試，確認 train/test 均通過 |
