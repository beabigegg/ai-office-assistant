# Agent Memo Protocol v1.0

> Agent 之間傳遞的 memo 文件必須包含 YAML frontmatter。
> 提供機器可讀的追蹤資訊，解決 memo 格式不一致的問題（瓶頸 B1）。

---

## 格式定義

每個 memo 文件以 YAML frontmatter 開頭，後接 Markdown body：

```yaml
---
memo_id: "{agent}_{YYYYMMDD}_{seq}"     # 唯一識別碼
type: string                             # memo 類型（見下方列表）
from: string                             # 來源 Agent
to: [string]                             # 目標 Agent（可多個）
project: string                          # 專案路徑（{P}）
timestamp: "YYYY-MM-DDTHH:MM:SS"        # 產出時間
depends_on: [string]                     # 前置 memo_id（可選）
status: enum                             # complete | partial | failed
---

# Memo 標題

## 摘要
（簡短描述此 memo 的核心內容）

## 詳細內容
（結構化的資料、表格、分析結果等）
```

## memo_id 格式

```
{agent 縮寫}_{日期}_{三位序號}

範例：
  lib_20260206_001   # Librarian 第一份 memo
  exp_20260206_001   # Explorer 第一份
  lrn_20260206_003   # Learner 第三份
```

Agent 縮寫對照：

| Agent | 縮寫 |
|-------|------|
| librarian | lib |
| toolsmith | tsm |
| explorer | exp |
| learner | lrn |
| promoter | prm |
| intake | itk |
| analyst | anl |
| reporter | rpt |
| architect | arc |

## Memo 類型列表

| type | 產出 Agent | 說明 |
|------|-----------|------|
| `catalog_update` | librarian | 檔案歸檔/版本更新通知 |
| `tool_registration` | toolsmith | 新工具建造完成通知 |
| `exploration_report` | explorer | 資料偵察報告 |
| `question_list` | learner | 待確認問題清單 |
| `knowledge_update` | learner | 知識更新通知 |
| `promotion_report` | promoter | Skill 升級報告 |
| `intake_report` | intake | 入庫結果報告 |
| `analysis_result` | analyst | 分析結果 |
| `final_report` | reporter | 最終報告 |
| `evolution_proposal` | architect | 架構改進提案 |

## status 說明

| status | 含義 | 下游處理 |
|--------|------|---------|
| `complete` | 全部完成 | 正常繼續 |
| `partial` | 部分完成（含已完成和未完成的說明）| 下游 Agent 處理已完成部分，跳過未完成 |
| `failed` | 失敗（含錯誤說明）| 觸發 Tier 2 錯誤處理 |

## 向後相容

- 如果 memo 沒有 YAML frontmatter → Agent 仍可處理（退回 v2.5 模式）
- 新建的 memo 必須包含 frontmatter
- 舊 memo 不需要補加
