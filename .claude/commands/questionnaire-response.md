---
name: questionnaire-response
description: |
  客戶問卷回覆流程。適用於 CSR/CQR/PQR/CTPP/Cu Wire Risk Assessment
  等問卷的解析、檢索、草稿生成與 Excel 輸出。
---

產出客戶問卷回覆草稿：

1. 先依 `questionnaire-response` skill 的 Leader 流程解析問卷、分類題目、檢索知識
2. 題數 `<=20` 時由 Leader 逐題處理
3. 題數 `>20` 時使用 `questionnaire-response-drafter` agent 進行批量草稿生成
4. 需要交付 Excel 時，使用 `office-report-engine` 產出 `vault/outputs/QAR_<customer>_<date>.xlsx`
5. 回報策略分布、信心分布、需要人工複核的低信心題目

步驟：
- 先讀 `.claude/skills-on-demand/questionnaire-response/SKILL.md`
- 若題數超過 20，使用 `questionnaire-response-drafter` agent
- 若需要正式 Office 交付物，使用 `office-report-engine`
- 回報輸出檔路徑與待確認題目清單
