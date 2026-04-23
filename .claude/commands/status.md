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
   - shared/kb/dynamic/ 中有多少條動態知識
   - 接近升級的候選數量
3. **工具清單**：shared/tools/ 中已註冊的工具
4. **最近決策**：shared/kb/decisions.md 最後 5 條
5. **當前專案**：{P} 是什麼，最近的 vault 和 DB 活動

步驟：
- 讀 shared/kb/_index.md
- 掃描 .claude/skills-on-demand/ 目錄
- 掃描 shared/kb/dynamic/ 目錄
- 掃描 projects/ 目錄
- 讀 shared/kb/decisions.md 末尾
- 彙整為結構化報告
