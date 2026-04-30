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
3. **Agent Coverage**：
   - 執行 `bash shared/tools/conda-python.sh shared/tools/agent_coverage.py`
   - 檢查每個 agent 的 activation surface、memory dir、memory 檔案數、最近 memory 更新時間
4. **工具清單**：shared/tools/ 中已註冊的工具
   - 執行 `bash shared/tools/conda-python.sh shared/tools/tool_audit.py`
   - 檢查哪些工具屬於 core_shared / domain_shared / maintenance / temporary_candidate
5. **Capability Registry**
   - 執行 `bash shared/tools/conda-python.sh shared/tools/capability_registry.py pending`
   - 執行 `bash shared/tools/conda-python.sh shared/tools/capability_audit.py`
   - 檢查 command / skill / agent / workflow / tool 的關聯是否完整
   - 檢查是否還有待處理的 relation extraction / embedding indexing 提醒
   - 若要跑 remote semantic relation suggestion：先 `bash shared/tools/conda-python.sh shared/tools/capability_registry.py export-semantic-relations`，再 `bash shared/tools/conda-python.sh shared/tools/semantic_relation_extractor.py extract`
   - semantic suggestion 不可直接寫回 authority；先 `bash shared/tools/conda-python.sh shared/tools/semantic_relation_review.py prepare`，審核後再 `approve/reject/apply`
6. **KB Indexing Reminders**
   - 執行 `bash shared/tools/conda-python.sh shared/tools/indexing_reminder.py list`
   - 檢查哪些新 decision / learning 與 capability 治理相關，需後續做 remote semantic relation extraction
7. **最近決策**：從 DB 查最近 5 條 decision，不直接讀 decisions.md 末尾
8. **當前專案**：目前的 `{PROJECT_ID}` 是什麼，最近的 `{PROJECT_ROOT}` vault 和 DB 活動

步驟：
- 先執行 `bash shared/tools/conda-python.sh shared/tools/kb.py catalog`
- 再執行 `bash shared/tools/conda-python.sh shared/tools/agent_coverage.py`
- 再執行 `bash shared/tools/conda-python.sh shared/tools/tool_audit.py`
- 再執行 `bash shared/tools/conda-python.sh shared/tools/capability_registry.py pending`
- 再執行 `bash shared/tools/conda-python.sh shared/tools/capability_audit.py`
- 再執行 `bash shared/tools/conda-python.sh shared/tools/indexing_reminder.py list`
- 如需最近項目，再用 `bash shared/tools/conda-python.sh shared/tools/kb.py search "<topic>" --top N` 或 DB 查詢輕量摘要
- 掃描 .claude/skills-on-demand/ 目錄
- 掃描 projects/ 目錄
- 彙整為結構化報告
