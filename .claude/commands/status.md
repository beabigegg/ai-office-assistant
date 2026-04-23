---
name: status
description: |
  顯示 Agent Office 系統狀態總覽。包含：各專案狀態、知識庫統計、
  工具清單、最近活動。適用於了解系統全景或排查問題。
---

產出 Agent Office 系統狀態報告：

1. **專案清單**：列出 projects/ 下所有專案，各自的 vault 檔案數、DB 表數
2. **知識庫統計**：
   - .claude/skills-on-demand/ 中有多少 Skill
   - kb_index.db 中有多少 learning / decision / snapshot
   - 接近升級的候選數量
3. **工具清單**：shared/tools/ 中已註冊的工具
4. **最近決策**：從 DB 查最近 5 條 decision，不直接讀 decisions.md 末尾
5. **當前專案**：目前的 `{PROJECT_ID}` 是什麼，最近的 `{PROJECT_ROOT}` vault 和 DB 活動

步驟：
- 先執行 `bash shared/tools/conda-python.sh shared/tools/kb.py catalog`
- 如需最近項目，再用 `bash shared/tools/conda-python.sh shared/tools/kb.py search "<topic>" --top N` 或 DB 查詢輕量摘要
- 掃描 .claude/skills-on-demand/ 目錄
- 掃描 projects/ 目錄
- 彙整為結構化報告
