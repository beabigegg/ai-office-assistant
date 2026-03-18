# Agent Dispatch Protocol v1.1

> 結構化轉派協議 -- 借鑑 Moltbot/OpenClaw 的 sessions_send + Orchestrator Pattern
> 解決痛點：sub-agent 無法嵌套調用 sub-agent
> v1.0：2026-02-11 — 協議設計
> v1.1：2026-02-11 — 加入實施層（Sub-agent Simulation）

---

## 設計理念

Claude Code 的 sub-agent **無法嵌套調用**其他 sub-agent。Moltbot 也有同樣限制，
但它透過 `sessions_send`（對等訊息傳遞）+ Main Session 編排來繞過。

本協議將此模式適配到 Agent Office：

```
                    Leader（Main Session = Gateway）
                           |
        ┌──────────────────┼──────────────────┐
        |                  |                  |
   Expert Agent      職能 Agent          Expert Agent
   (判斷+行動清單)   (執行操作)          (判斷+行動清單)
        |                  |                  |
        └─── dispatch_memo ┘                  |
              (轉派請求)                      |
              Leader 讀取後調度               |
              ←── result_memo ────────────────┘
```

**核心原則**：Agent 不直接調用 Agent，而是透過 **dispatch_memo** 向 Leader 請求轉派。

---

## 1. Dispatch Memo 格式

當一個 Agent（通常是專家）需要另一個 Agent 的協助時，產出 dispatch_memo：

```yaml
---
memo_id: "{agent}_{YYYYMMDD}_{seq}"
type: dispatch                          # 新類型：轉派請求
from: bom-process-expert                # 發起者
to: [leader]                            # 固定寄給 leader
dispatch_target: analyst                # 請求轉派的目標 Agent
priority: high | normal | low
project: "{P}"
timestamp: "YYYY-MM-DDTHH:MM:SS"
depends_on: []
status: pending                         # pending -> dispatched -> complete
---

# 轉派請求：[簡短描述]

## 請求內容
（清楚描述需要目標 Agent 做什麼）

## 輸入資料
（提供目標 Agent 需要的所有上下文、檔案路徑、查詢條件）

## 預期輸出
（描述期望的輸出格式和內容）

## 領域背景（由專家提供）
（專家對此任務的領域判斷、注意事項、陷阱提醒）
```

### dispatch_target 允許值

| dispatch_target | 典型請求場景 |
|-----------------|-------------|
| `analyst` | 需要 SQL 查詢或資料分析 |
| `reporter` | 需要產出報表 |
| `intake` | 需要資料入庫 |
| `toolsmith` | 需要建造工具 |
| `explorer` | 需要探測新資料 |
| `learner` | 需要知識確認或更新 |
| `bom-process-expert` | 需要 BOM/製程領域判斷 |
| `reliability-expert` | 需要可靠性測試領域判斷 |

### 專家間諮詢

專家 Agent 也可以請求諮詢另一位專家：

```yaml
type: dispatch
from: reliability-expert
dispatch_target: bom-process-expert
```

Leader 看到後轉派給目標專家，結果再回傳給原始請求者。

---

## 2. Action Plan 格式（Orchestrator Pattern）

專家 Agent 分析完畢後，不只返回結論，還返回結構化的 **行動清單**，
Leader 照清單逐步調度職能 Agent。

```yaml
---
memo_id: "{agent}_{YYYYMMDD}_{seq}"
type: action_plan                       # 新類型：行動清單
from: bom-process-expert
to: [leader]
project: "{P}"
timestamp: "YYYY-MM-DDTHH:MM:SS"
status: complete
---

# 行動清單：[任務標題]

## 領域判斷摘要
（專家的核心結論，1-3 句）

## 行動步驟

### Step 1
- target: analyst
- action: "執行 SQL 查詢，取出所有涉及料號的 BOP 第三碼"
- input: |
    DB: {P}/workspace/db/ecr_ecn.db
    Table: std_au_cu_detail
    Filter: involvement = '涉及' AND bop_gold IS NOT NULL
- expected_output: "CSV 或 memo，包含 part_number, bop_gold, bop_silver, bop_copper"
- domain_notes: |
    注意 BOP 第三碼 A=金線, G=銀線, C=銅線。
    如果 bop_copper 為空但 bop_gold 有值，表示該料號尚未建立銅線 BOP。

### Step 2
- target: reliability-expert
- action: "根據 Step 1 結果，判斷需要哪些可靠性測試"
- input: "Step 1 的輸出"
- depends_on: "Step 1"
- expected_output: "測試矩陣：每個 Technology Family 需要的測試項目和樣品數"

### Step 3
- target: reporter
- action: "彙整 Step 1 + Step 2 產出最終報告"
- input: "Step 1 + Step 2 的輸出"
- depends_on: "Step 1, Step 2"
- expected_output: "Excel 報表 + Markdown 摘要"

## 風險提醒
（專家認為可能出問題的地方）

## 備註
（其他補充資訊）
```

---

## 3. Leader 的調度流程

Leader 收到 action_plan 後的處理：

```
Leader 收到 action_plan
  |
  v
解析步驟和依賴關係
  |
  ├─ 無依賴的步驟 → 可並行調度
  ├─ 有依賴的步驟 → 等前置完成後調度
  |
  v
逐步調度：
  1. 呼叫 target Agent（透過 Task tool）
  2. 將 action + input + domain_notes 作為 prompt
  3. 收到結果後，檢查是否滿足 expected_output
  4. 如果有 depends_on 指向此步驟的後續步驟，繼續調度
  |
  v
所有步驟完成 → 彙整結果呈給使用者
```

### 並行調度規則

- Step 之間如果沒有 `depends_on` 關係 → **並行執行**（多個 Task tool 同時調用）
- 有 `depends_on` → **串行等待**
- 這直接對應 Claude Code 的多 tool call 並行能力

---

## 4. Result Memo 格式

職能 Agent 完成 dispatch 任務後，回傳標準的 result_memo：

```yaml
---
memo_id: "{agent}_{YYYYMMDD}_{seq}"
type: dispatch_result                   # 新類型：轉派結果
from: analyst
to: [leader]
in_response_to: "bpe_20260211_001"      # 原始 dispatch_memo 的 memo_id
project: "{P}"
timestamp: "YYYY-MM-DDTHH:MM:SS"
status: complete | partial | failed
---

# 結果：[簡短描述]

## 執行結果
（具體的查詢結果、分析結論等）

## 產出檔案
（如有產出檔案，列出路徑）

## 異常說明
（如有異常或部分失敗，說明原因）
```

---

## 5. 專家間諮詢流程（模擬 sessions_send reply-back）

```
BOM 專家分析中 → 發現需要可靠性測試判斷
  |
  v
BOM 專家產出 dispatch_memo:
  type: dispatch
  from: bom-process-expert
  dispatch_target: reliability-expert
  (附帶已知的 BOM 資訊作為輸入)
  |
  v
Leader 轉派給 reliability-expert
  |
  v
reliability-expert 回傳 dispatch_result
  |
  v
Leader 將結果帶回給 BOM 專家（如果 BOM 專家的 action_plan 尚未完成）
  或
Leader 直接用結果繼續執行 action_plan 的後續步驟
```

---

## 6. 與現有協議的整合

### 與 Agent Memo Protocol 的關係

本協議是 Agent Memo Protocol 的**擴展**，新增了三個 memo type：

| type | 說明 | 新增 |
|------|------|------|
| `dispatch` | 轉派請求 | v1.0 新增 |
| `action_plan` | 行動清單 | v1.0 新增 |
| `dispatch_result` | 轉派結果 | v1.0 新增 |

所有新 type 遵守 Agent Memo Protocol 的 frontmatter 格式，
並在其上擴展 `dispatch_target`、`in_response_to` 等欄位。

### 與 Agent 通訊協議 (agent-comm.md) 的關係

agent-comm.md 的 `handoff` type 是**順序交接**（A 完成 → B 接手）。
本協議的 `dispatch` 是**請求協助**（A 需要 B 幫忙 → B 回傳結果 → A 繼續）。

兩者互補，不衝突：
- `handoff`：管線式流程（Flow A 的 Phase 串接）
- `dispatch`：星狀協作（專家間諮詢、跨職能請求）

### 與 Skill Manifest 的關係

`.skill.yaml` 新增 `expert_agent` 欄位：

```yaml
# .claude/skills/bom-rules/.skill.yaml 擴展
expert_agent: bom-process-expert    # 對應的專家 Agent
consult_agents:                     # 此專家可諮詢的其他專家（allowlist）
  - reliability-expert
```

---

## 7. Agent 縮寫更新

新增專家 Agent 的縮寫：

| Agent | 縮寫 |
|-------|------|
| bom-process-expert | bpe |
| reliability-expert | rle |

---

## 8. 實施層：Sub-agent Simulation（v1.1）

### 技術限制

Claude Code 的 Task tool `subagent_type` 只接受預定義類型（librarian, analyst, ...），
**不支援自定義的 expert agent type**。因此專家 Agent 透過以下方式模擬：

```
subagent_type: "general-purpose"    ← 擁有全部工具
model: "opus"                       ← 最強推理能力
prompt: [組裝後的專家 prompt]        ← 注入身份 + 知識 + 任務
```

### Leader 調度專家的標準步驟

```
Leader 判斷需要專家 Agent
  │
  ├─ Step 1：讀取 .claude/agents/{expert-name}.md    （角色定義）
  ├─ Step 2：讀取相關 .claude/skills/*/SKILL.md       （領域知識）
  ├─ Step 3：組裝 prompt（見下方模板）
  │
  ▼
  Task tool 調用：
    subagent_type = "general-purpose"
    model = "opus"
    prompt = 組裝後的 prompt
  │
  ▼
  Sub-agent 返回 action_plan 文本
  │
  ▼
  Leader 解析 action_plan，逐步調度職能 Agent
```

### Prompt 組裝模板

Leader 在調度專家時，**必須**按以下結構組裝 prompt：

```
你是 {expert_name}（{角色定位}）。

## 你的身份與職責
{貼入 .claude/agents/{expert-name}.md 的核心內容}

## 你的領域知識
{貼入相關 SKILL.md 的關鍵規則，不超過 2000 字}

## 當前專案上下文
- 專案：{P}
- 資料庫：{P}/workspace/db/{db_name}
- 已知事實：{從 project_state.md 摘取的關鍵資訊}

## 你的任務
{使用者的具體請求或 Leader 轉述的分析需求}

## 輸出要求
你必須返回一個 action_plan，格式如下：
1. **領域判斷摘要**（1-3 句核心結論）
2. **行動步驟**（每步包含 target / action / input / expected_output / domain_notes）
3. **風險提醒**

你只做判斷和規劃，不直接執行操作。所有操作步驟指派給職能 Agent。
如果某些判斷你不確定，在風險提醒中標記「需使用者確認」。
```

### 知識注入的精簡原則

sub-agent 的 context window 有限，注入時遵守：

| 來源 | 注入方式 | 上限 |
|------|---------|------|
| agent 定義檔 (.md) | 全文貼入 | ~60 行 |
| SKILL.md | 摘取與任務相關的規則 | ~2000 字 |
| project_state.md | 摘取「變更案摘要」+「關鍵決策」 | ~500 字 |
| DB schema | 只列相關表的欄位名 | ~300 字 |
| 前序步驟結果 | 摘要或全文（依大小） | ~1000 字 |

**Leader 的責任**：在組裝 prompt 時做好精簡，不要把整個知識庫丟進去。

### 專家間諮詢的實施

當專家 A 的 action_plan 中有 `target: {另一位專家}` 時：

```
Leader 收到專家 A 的 action_plan
  │
  ├─ Step N 的 target = "reliability-expert"
  │
  ├─ Leader 重複「調度專家」的標準步驟：
  │   ├─ 讀取 reliability-expert.md
  │   ├─ 讀取相關 SKILL.md
  │   ├─ 組裝 prompt（包含專家 A 提供的 input 和 domain_notes）
  │   └─ Task tool 調用 general-purpose + opus
  │
  ├─ 收到專家 B 的結果
  │
  └─ 繼續執行 action_plan 的後續步驟
```

**注意**：這不是 sub-agent 嵌套調用，而是 **Leader 串行調度兩次 sub-agent**。

### 降級策略

當 sub-agent 模擬失敗或返回不符格式時：

| 情況 | 降級方式 |
|------|---------|
| 專家返回的不是 action_plan 格式 | Leader 從返回內容中提取判斷，自行組織行動步驟 |
| 專家的某個步驟不可執行 | Leader 跳過該步驟，在最終報告中標記 |
| 知識注入太多導致 context 溢出 | 減少 SKILL.md 注入量，僅保留最相關的 5 條規則 |
| sub-agent 超時或錯誤 | Leader 在主對話中直接做簡化版判斷（標記為降級） |

---

## 附錄：完整流程範例

### 範例：「分析金線轉銅線對 BSOB 料號的影響」

```
使用者: 「分析金線轉銅線對 BSOB 料號的影響」
  |
Leader 匹配 Skill: bom-rules + package-code → expert_agent: bom-process-expert
  |
Leader 調度 bom-process-expert，prompt 包含使用者請求
  |
bom-process-expert 返回 action_plan:
  Step 1: analyst → 查詢 BSOB 34 筆料號的 BOP 編碼和封裝資訊
  Step 2: bom-process-expert → 根據 Step 1 判斷哪些需要新建銅線 BOP
  Step 3: reliability-expert → 判斷 Wire Bonding 變更需要哪些 Q006 測試
  Step 4: reporter → 彙整報告
  |
Leader 執行 Step 1（調度 analyst）
  |
analyst 回傳 dispatch_result（34 筆料號的 BOP 資訊）
  |
Leader 並行執行 Step 2 + Step 3（因為兩者只依賴 Step 1）
  |
bom-process-expert 回傳判斷 + reliability-expert 回傳測試矩陣
  |
Leader 執行 Step 4（調度 reporter）
  |
reporter 產出最終報告
  |
Leader 呈給使用者
```
