---
name: skill-creator
description: |
  建立新 Skill、改善現有 Skill、評測 Skill 效能。
  使用時機：從零建立新 skill、修改/優化現有 skill、
  執行觸發率測試（run_eval / run_loop）、
  執行輸出品質對比評估（grader / comparator / analyzer agent）、
  對 skill description 做最佳化、閱覽 eval 結果報告。
---

# Skill Creator（Meta-Skill）

腳本位於：`/d/ai-office/skill-creator/scripts/`
eval 閱覽器：`/d/ai-office/skill-creator/eval-viewer/`

---

## 建立 Skill 的完整流程

```
1. 釐清目標 → 確認做什麼、怎麼做、輸入/輸出格式
2. 撰寫草稿（SKILL.md frontmatter + 內容）
3. 放進 .claude/skills-on-demand/<name>/SKILL.md
4. 寫測試提示（trigger + non-trigger）
5. 測觸發率 → run_eval.py
6. 測輸出品質 → with-skill vs baseline → grader/comparator/analyzer
7. 根據結果修訂 skill，重複直到滿意
8. 擴大測試集 → run_loop.py 最佳化 description
```

---

## 第一部分：觸發率測試（Description Accuracy）

測試 skill description 是否在正確時機觸發（Claude 讀到此 skill）。

```bash
# 單次 eval（指定 skill 路徑 + 測試提示 JSON）
PYTHONUTF8=1 "C:\Users\lin46\.conda\envs\ai-office\python.exe" \
  /d/ai-office/skill-creator/scripts/run_eval.py \
  --skill .claude/skills-on-demand/<name>/SKILL.md \
  --prompts path/to/test_cases.json

# 迭代最佳化 description（20次，60/40 train/test）
PYTHONUTF8=1 "C:\Users\lin46\.conda\envs\ai-office\python.exe" \
  /d/ai-office/skill-creator/scripts/run_loop.py \
  --skill .claude/skills-on-demand/<name>/SKILL.md \
  --output results.json

# 產生 HTML 閱覽頁
PYTHONUTF8=1 "C:\Users\lin46\.conda\envs\ai-office\python.exe" \
  /d/ai-office/skill-creator/scripts/generate_report.py \
  results.json -o report.html
```

**test_cases.json 格式：**
```json
[
  {"query": "幫我建立 Excel 報告", "should_trigger": true},
  {"query": "幫我建立 Word 文件", "should_trigger": true},
  {"query": "查詢資料庫中的零件", "should_trigger": false}
]
```

---

## 第二部分：輸出品質評估（Output Quality）

比較「有 skill」vs「無 skill」的實際產出品質。

### 步驟

1. **平行跑兩個版本**（Leader 使用 Agent tool）
   - with-skill：提供 SKILL.md 內容給子 agent
   - baseline：不提供 skill，讓 agent 自由處理

2. **品質評分**（skill-eval-grader agent）
   - 輸入：expectations（期望清單）+ transcript + outputs 目錄
   - 輸出：grading.json（pass/fail + 證據）

3. **盲測比對**（skill-eval-comparator agent）
   - 輸入：output A 路徑 + output B 路徑 + eval prompt
   - 輸出：comparison.json（winner + rubric 評分）

4. **改善建議**（skill-eval-analyzer agent）
   - 輸入：comparator 結果 + 兩份 skill + transcript
   - 輸出：analysis.json（弱點分析 + 改善建議）

### 呼叫範例

```
# Leader 在內文中呼叫（不需要寫 script）：
使用 skill-eval-grader agent，inputs：
  expectations: ["輸出為 xlsx", "有凍結首列", "有標題樣式"]
  transcript_path: workspace/run_a/transcript.md
  outputs_dir: workspace/run_a/outputs/

使用 skill-eval-comparator agent，inputs：
  output_a_path: workspace/run_a/outputs/
  output_b_path: workspace/run_b/outputs/
  eval_prompt: "建立月報 Excel，含 KPI 摘要表"

使用 skill-eval-analyzer agent，inputs：
  winner: "A"
  winner_skill_path: .claude/skills-on-demand/xlsx-authoring/SKILL.md
  loser_skill_path: (baseline，無 skill)
  comparison_result_path: workspace/comparison.json
  output_path: workspace/analysis.json
```

---

## Skill 格式（frontmatter 必填）

```markdown
---
name: skill-name
description: |
  一段描述，明確告訴 Claude 何時觸發此 Skill。
  觸發詞、使用情境、適用範圍要具體。
  不適用的情境也可以列出（避免誤觸發）。
---

# Skill 標題

## 環境

## 主要流程

## 關鍵規則與陷阱

## 快速參考表
```

---

## 放置位置

```
.claude/skills-on-demand/<skill-name>/SKILL.md
```

建立後在對應 agent（如 report-builder.md）的 Skill Loading 表格中登記。

---

## 評估策略速查

| 階段 | 工具 | 目的 |
|------|------|------|
| 草稿 | 3-5 trigger + 3-5 non-trigger | 快速驗證觸發意圖 |
| 觸發率測試 | `run_eval.py` | 確認 description 準確率 |
| 品質評比 | grader/comparator agents | 確認 skill 是否提升產出 |
| Description 優化 | `run_loop.py` | 自動迭代到最佳 description |
| 結果閱覽 | `generate_report.py` → HTML | 視覺化觸發率歷程 |
