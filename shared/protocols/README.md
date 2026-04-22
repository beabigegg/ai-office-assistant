# Agent Office v2.7 — 系統協議索引

> **Status: Legacy (v2.7)** — 這些協議為 v2.7 時代的產物，保留作為歷史參考。
> 現行系統以 `.claude/CLAUDE.md` v3.0 為行為規範來源。
> 協議中的設計概念（Skill Manifest、錯誤分層、知識生命週期等）已部分整合到 v3.0 架構中。
>
> ~~本目錄定義 Agent Office 的標準化協議。所有 Agent 必須遵守。~~

## 協議清單

| 協議 | 檔案 | 說明 | 版本 |
|------|------|------|------|
| Skill Manifest 規範 | `skill_manifest_spec.md` | .skill.yaml 的格式定義與欄位說明 | 1.0 |
| Agent Memo Protocol | `agent_memo_protocol.md` | Agent 間 memo 的 YAML frontmatter 格式 | 1.0 |
| Agent Dispatch Protocol | `agent_dispatch_protocol.md` | 專家 Agent 轉派協議（dispatch / action_plan / dispatch_result） | 1.0 |
| 三層錯誤處理協議 | `error_handling.md` | Tier 1/2/3 錯誤恢復策略 | 1.0 |
| 知識生命週期管理 | `knowledge_lifecycle.md` | 知識的 TTL、清理策略、交叉引用 | 1.0 |

## 使用方式

- **Leader**：派工前參考 Skill Manifest 做路由；錯誤發生時依 error_handling.md 分層處理；收到 action_plan 時依 Dispatch Protocol 逐步調度
- **專家 Agent**：需要職能 Agent 協助時，產出 dispatch_memo 或 action_plan 給 Leader
- **職能 Agent**：完成 dispatch 任務後，回傳 dispatch_result
- **各 Agent**：輸出 memo 時遵守 Agent Memo Protocol；內部錯誤用 Tier 1 處理
- **Promoter**：升級 Skill 時必須同時產出 .skill.yaml
- **Architect**：審查 error_patterns.md，識別需永久修復的錯誤模式
