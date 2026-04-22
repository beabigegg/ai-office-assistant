---
name: promote
description: |
  手動觸發知識升級審查。Promoter 會深度掃描 shared/kb/dynamic/ 中所有知識，
  評估哪些已經成熟到可以升級為 .claude/skills/ 原生 Skill。
---

執行知識升級深度審查：

1. 使用 Promoter agent 對 shared/kb/dynamic/ 進行完整掃描
2. 評估每條知識的信心度、驗證次數、穩定度、來源品質
3. 達標的自動升級為 .claude/skills/ 原生 Skill
4. 產出升級報告，列出已升級、接近升級、尚早的知識
