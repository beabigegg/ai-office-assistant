---
name: promote
description: |
  手動觸發知識升級審查。Promoter 會以 DB-first 方式檢查 kb_index.db 中的 learning /
  decision 關聯，評估哪些知識值得升級為 .claude/skills-on-demand/ 的 Skill。
---

執行知識升級深度審查：

1. 使用 `promoter` agent，以 `bash shared/tools/conda-python.sh shared/tools/kb.py catalog` 與 `search/read` 從 DB 收斂候選
2. 檢查 learning 的信心度、引用價值、關聯 decision、與既有 Skill 的重疊程度
3. 檢查 `.claude/skills-on-demand/` 是否已有覆蓋，避免重複建立 Skill
4. 產出 promotion review：建議升級、暫緩觀察、已有 Skill 覆蓋、stale/conflicting
5. 只有在使用者明確批准後，才建立或更新 Skill 檔案
