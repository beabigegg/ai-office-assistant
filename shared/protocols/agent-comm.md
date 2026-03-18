# Agent 通訊協議 v1.0

## 訊息格式（Memo 標準化）

所有 Agent 間的通訊 memo 統一使用以下格式：

\```yaml
---
from: explorer
to: leader
type: report | question | alert | handoff
priority: high | normal | low
timestamp: 2026-02-05T14:30:00
project: {project-name}
related_files: [file1.xlsx, file2.csv]
---
\```

## 訊息類型定義

### report（回報）
Agent 完成任務後的結果報告。
- Explorer → Leader：偵察報告
- Analyst → Leader：分析結果
- Intake → Leader：入庫完成確認

### question（提問）
需要使用者或其他 Agent 確認的問題。
- Explorer → Learner：欄位含義疑問
- Librarian → Learner：分類不確定的檔案
- Analyst → Rules Keeper：規則衝突

### alert（警報）
異常狀況的緊急通知。
- Intake → Leader：資料損壞/格式異常
- Librarian → Leader：版本衝突
- Analyst → Leader：規則衝突無法自動解決

### handoff（交接）
任務完成，移交給下一個 Agent。
- Explorer → Learner：偵察完成，請綜合提問
- Learner → Intake：確認完成，可以入庫
- Analyst → Reporter：分析完成，請生成報告

## Agent 狀態追蹤

Leader 在 `{P}/workspace/memos/agent_status.json` 維護即時狀態：

\```json
{
  "timestamp": "2026-02-05T14:30:00",
  "project": "project-A",
  "agents": {
    "explorer": { "status": "completed", "last_task": "偵察 supplier_bom.xlsx" },
    "learner": { "status": "working", "last_task": "綜合提問清單" },
    "intake": { "status": "idle" },
    "analyst": { "status": "idle" },
    "reporter": { "status": "idle" }
  }
}
\```

## Announce 機制（任務完成自動通知）

借鑑 OpenClaw 的 Announce 設計：
- Agent 完成任務後，除了寫 memo，還應在 memo 的 `type` 標記為 `handoff`
- Leader 看到 `handoff` 類型的 memo 時，自動派發下一個 Agent
- 這樣可以減少 Leader 的輪詢，讓流程更自動化