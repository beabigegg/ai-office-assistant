# 系統演進日誌

> 記錄所有架構變更、Agent 新增、工具建立等演進事件。
> Architect 負責維護此日誌。

---

## 演進記錄

### EVO-016: Harness-native 自我學習 Skill 迴圈（2026-04-24）

**觸發**：使用者要求基於現有 harness/workflow 架構，建立一套不繞過治理的「自我學習 skill」閉環，讓成熟 learning 能被系統持續掃描、評估、提案，但實際 Skill 建立仍保留人工批准。

**類型**：架構升級（已完成）
**影響範圍**：`coordinator.py`, `post_task.json`, 新增 `skill_self_learning.json`, `promotion_state.py`, `check_promotion_candidates.py`, `skill_usage_tracker.py`

#### 設計目標
- 不新增平行治理體系；沿用既有 `post_task` / `/promote` / `architect` authority model
- 不讓 workflow 直接建立或修改 `SKILL.md`
- 讓 promotion queue 具備 durable state，避免同一 candidate 無限反覆入隊
- 讓真實 skill 使用量能回饋 learning 成熟度，而不是只靠人工標記

#### 核心變更
- `post_task` 完成時由 coordinator Python 層直接掃描 `kb_index.db` 中成熟 learning，寫入 `promotion_queue.json`
- 新增 `skill_self_learning` workflow：`select_candidate` → `prepare_eval_set` → `run_skill_eval` → `propose_promotion`
- `propose_promotion` 只產生 `shared/workflows/state/proposals/<learning_id>_proposal.json`
- 真正建立 Skill 仍需使用者執行 `/promote`，再由 `architect` 進入正式治理流程

#### Queue / State 收斂
- 新增 `promotion_state.py` 管理 `promotion_queue.json` 與 `eval_history.json`
- `select_candidate` 完成時即 dequeue，並立刻寫入 `in_progress`
- workflow 結束後再寫入 `proposed` / `below_threshold` / `failed` / `unknown` / `overlap`
- 主掃描路徑與 validator 路徑共用同一套 suppress/cooldown 規則：
  - `proposed`：永久跳過，直到 KB `meta.status='promoted'`
  - `in_progress`：24 小時
  - `below_threshold` / `failed` / `unknown`：30 天
  - `overlap`：7 天

#### 工程護欄
- overlap guard 在 coordinator 主路徑與 validator 次路徑都會檢查 `.claude/skills-on-demand/*/SKILL.md`
- `refs_skill` 兼容 JSON array string 與 plain string 解析
- promotion queue / eval history 的 read-modify-write 改為 per-file advisory lock，降低並行覆寫風險
- 新增 `skill_usage_tracker.py`，將 SKILL.md 真實讀取回寫到 KB `usage_count`

**成果**：形成一條與現有 harness 相容的自我學習 promotion pipeline；系統可以自動發現成熟 learning、評估是否值得升級、產出治理相容的提案，同時避免 queue 卡死、無限重入隊與直接繞過 `architect` 建 Skill。

---

### EVO-015: Agent 委派可靠性 + 護欄硬化 + 工具預算（2026-04-07）

**觸發**：分析 Claude Code 原始碼後，發現 AI Office 的 agent 定義有結構性問題，且 CLAUDE.md 軟約束未善用 Claude Code 內建的 hooks/permissions 機制。

**類型**：架構補強（已完成）
**影響範圍**：agent definitions, settings.local.json, CLAUDE.md, kb.py, 新建 pretool_guard.py

#### 線 C: Agent 定義修正（根因修復）

**report-builder**（P0 — 最常失敗的 agent）：
- 根因：`tools: Read, Grep, Glob, Bash` 白名單排除了所有 MCP 工具（mcp__xlsx__*, mcp__docx__*, mcp__pptx__*）
- Claude Code 的 `resolveAgentTools()` 用精確名稱比對過濾工具池 → agent 無法操作 Office
- 修正：移除 `tools` 欄位（= 全部可用），改用 `disallowedTools` 黑名單

**所有 5 個 agent**：
- 新增 `maxTurns`（25-80），防止無限循環燒 token
- 新增 `disallowedTools: [WebFetch, WebSearch]`，排除不相關工具
- `tools` 欄位格式從 comma-separated string 改為 YAML array

**frontmatter 欄位確認**：
- `memory: project` — 確認 Claude Code 原生支援（loadAgentsDir.ts:594-605）
- `requiredMcpServers` — frontmatter 不解析此欄位，不使用

#### 線 A: 善用 Claude Code 內建功能

**settings.local.json — permissions.deny 規則**：
- 新增 deny: `powershell *`, `cmd /c *`, `chmod *`, `iconv *`
- 刪除矛盾的 allow: `Bash(xcopy:*)`, `Bash(powershell -Command:*)`, `Bash(iconv:*)`, `Bash(dir:*)`

**settings.local.json — PreToolUse hook**：
- 新增 Bash 指令攔截 hook → `shared/tools/pretool_guard.py`
- 9 個規則：powershell, cmd /c, chmod, iconv, 系統 Python, rm -rf /, git push --force, git reset --hard
- exit 0 放行、exit 2 阻止並回饋訊息給 AI

#### 線 B: 工具層改善

**kb.py search --budget**：
- 新增 `--budget` 參數（預設 0=無限），超出時截斷並提示 `kb.py read <ID>`
- 防止大量搜尋結果灌入 context window

#### CLAUDE.md §2: 委派 Briefing 原則

新增 5 點指導：含具體路徑、含具體操作、含上下文、不委派理解、不委派合成。
源自 Claude Code 系統提示：「Brief the agent like a smart colleague who just walked into the room」。

**成果**：修復 report-builder 根因、5 agent 加護欄、4 條 deny 規則、PreToolUse 硬攔截、工具輸出預算。

---

### EVO-014: Harness Engineering — 軟護欄升級硬護欄（2026-04-07）

**觸發**：架構審查發現系統有 13 個硬護欄但也有 13 個純 prompt 軟護欄（成熟度 3.0/5.0）。SQL Schema-First、Checklist 內容品質、資料追溯性、會話生命週期為最危險缺口。

**類型**：架構補強（已完成）
**影響範圍**：validators, coordinator.py, workflow definitions, checklists

#### R1: Schema-First 強制驗證（軟→硬）
- 新建 `check_schema_loaded.py` validator：驗證 outputs 含有效 schema_file 路徑
- `analysis_report.json` 的 `load_schema` 節點從 `validator: null` 升級為 `validator: "check_schema_loaded"`
- AI 必須提供 `--outputs '{"schema_file":"..."}'` 才能通過，否則 workflow 阻斷

#### R2: Checklist evidence_pattern（半硬→更硬）
- `check_checklist.py` 新增 `evidence_pattern` 支援：YAML item 可定義 regex pattern
- 回答不僅需 ≥10 字，還必須 match pattern 才算通過（如 cv-001 要求含 `sub_com`/`com`）
- 6 個高風險 checklist item 加入 evidence_pattern（cross_validate 3 個 + post_validation 3 個）

#### R3: 資料入庫追溯欄位驗證（軟→硬）
- 新建 `check_traceability.py` validator：檢查 table 是否含 `_operation_id`/`_source_file`/`_source_row`
- `data_ingestion.json` 的 `post_validation` 節點升級為 `["check_checklist", "check_traceability"]` 雙 validator
- 缺欄位 → ERROR 阻斷；欄位存在但有 NULL → WARNING 通過

#### R5: Stop Hook 無 workflow 警告（無→半硬）
- `coordinator.py` 的 `_handle_stop_hook()` 增加 `_detect_significant_work()` 啟發式檢查
- 近 30 分鐘內有 vault/outputs/ 或 workspace/db/ 修改但無 active workflow → 第一次阻斷提醒，第二次放行
- `start()` 函數啟動 workflow 時自動清除警告 flag

**成果**：3 個最高風險軟護欄升級為硬護欄，1 個新半硬護欄。預估成熟度 3.0 → 3.7。

---

### EVO-013: 三支柱架構補強 — 知識圖 + Checklist 機制 + 工具整併（2026-04-02）

**觸發**：使用者以 harness engineering 視角評估系統弱點，指出三個核心問題：
1. Validator 只擋格式不擋業務邏輯錯誤（cross_validate 是空殼）
2. 知識召回靠 AI 自覺，edges 表幾乎空（10 條），知識圖是假的
3. kb.py / kb_index.py 雙工具殘留造成混淆

**類型**：架構補強（已完成）
**影響範圍**：kb.py, coordinator.py, validators, workflow definitions, CLAUDE.md

#### Phase 1：知識圖真實化
- `kb.py build-edges`：把 refs_skill/refs_db/affects JSON 欄位 + SKILL.md 中的 D-NNN 引用轉為真 edges
- Edges 從 ~149 增長到 311（refs_skill 43 + refs_db 46 + affects 61 + cited_by_skill 12）
- `kb.py search` 結果附帶 `[→ SKILL:name]` 關聯標籤
- `kb.py trace / impacts` 從 kb_index.py 搬入

#### Phase 2：Checklist 機制（非確定性節點外部約束）
- 新 validator `check_checklist.py`：讀取 YAML 定義的驗證清單，強制 AI 逐條回答
- Checklist 儲存在 `shared/workflows/checklists/{workflow}__{node}.yaml`，Git 追蹤
- 初始 checklist 從使用者歷史回饋萃取（PKG CODE 猜測、BOM 雙層、die size 精度等）
- 套用到 5 個非確定性節點：cross_validate, post_validation, confirm_with_user, record_knowledge, classify_knowledge
- Checklist 項目由使用者回饋成長（AI 用 Edit tool 更新 YAML）
- coordinator.py 支援 `validator: [list]`（向下相容）

#### Phase 3：備份 + 工具整併
- project_state.md 自動備份（`.project_state.prev.md`，單版本）
- kb_index.py 的 trace/impacts 併入 kb.py，CLAUDE.md 統一引用 kb.py

**設計原則**：
- 不信任 AI 自我監督 → 用外部 validator 約束
- 不膨脹 context → lazy catalog 模式（給目錄不給全文）
- Checklist 從使用者回饋成長 → 非硬編碼，有生命週期
- Validator 不做業務判斷 → 只檢查「AI 有沒有回答所有項目」

**完整方案**：`shared/kb/evolution_proposals/architecture_plan_evaluation.md`

---

### EVO-012: Knowledge Base Database-First Architecture（2026-04-01）

**觸發**：知識庫成長到 320 nodes（145 decisions + 93 learning + 24 rules + 58 column semantics），.md 作為 source of truth 的讀寫成本持續增加。Skills 自動載入每次浪費 ~14K tokens。缺乏統一 catalog 讓 session start 無法快速掌握「系統裡有什麼知識」。

**類型**：架構重構（PROPOSAL，待確認）
**影響範圍**：kb_index.py, kb_writer.py, CLAUDE.md, validators, Skills 載入方式, session_start workflow

#### 核心設計

- **DB 成為 source of truth**：新建 `knowledge` 表（含 content 完整文字），取代 .md 的 truth 地位
- **.md 降格為匯出品**：`kb.py export` 自動產生，供人類 review + git 版控
- **輕量 catalog**：SQL VIEW，session start 載入 ~300 tokens（取代 14K Skills + 22K summary）
- **統一 CLI**：`kb.py` 整合 catalog/search/read/add/update/validate/export
- **四階段遷移**：Phase 0 (Skills on-demand, -14K tokens) → Phase 1 (DB schema) → Phase 2 (寫入切換) → Phase 3 (讀取切換)

#### Token 節省

- Phase 0 立即：~14,000 tokens/session（Skills 不自動載入）
- Phase 3 完成：~32,500 tokens/session（-98% 知識載入成本）

**完整方案**：`shared/kb/evolution_proposals/EVO-012_kb-database-first.md`

---

### EVO-011: Report-Builder 分層提示 + MEMORY.md 硬上限（2026-04-01）

**觸發**：分析 Claude Code 原始碼架構後，識別出兩個可快速落地的改進。

**類型**：品質提升 + 防護機制
**影響範圍**：report-builder agent、Excel/PPT/Word Skills、check_memory validator

#### 變更明細

1. **report-builder.md — 新增 Design Principles 區塊**（5 條原則）
   - DP1 視覺層次：標題→子標題→內容的字級/顏色/粗細規範
   - DP2 色彩一致性：7 色標準色盤，禁止隨意引入新顏色
   - DP3 排版規範：字型統一（正黑體+Calibri）、對齊規則、數字格式
   - DP4 版面結構：Excel 凍結/篩選、PPT 6×6 原則、Word 目錄結構
   - DP5 完成度檢查：7 項 Quality Gate checklist

2. **三個 Office Skills — 各新增 Q：品質規範區塊**（不在 git 追蹤中）
   - Q1 產出前必做清單（5-6 項）
   - Q2 常見錯誤規避表（6-7 項錯誤→正確對照）
   - Q3 結構建議（報告/簡報/工作表推薦結構）

3. **check_memory.py — MEMORY.md 行數硬上限**
   - > 200 行：ERROR 阻斷 post_task
   - > 160 行：WARN 附加警告
   - 借鑑 Claude Code 的 MEMORY.md 200 行 + 25KB 截斷策略

**參考來源**：Claude Code 原始碼分析（github.com/sanbuphy/claude-code-source-code）

---

### EVO-010: 配置文件 Token 瘦身（2026-04-01）

**觸發**：每次會話自動載入 ~47,500 tokens（~133KB），多數為低頻使用的靜態內容。

**類型**：配置精簡
**影響範圍**：Global CLAUDE.md、MEMORY.md、process-bom-semantics SKILL.md

#### 變更明細

| 項目 | Before | After | 節省 |
|------|--------|-------|------|
| Global CLAUDE.md | 417 行 / 11.5KB | 3 行 / 0.1KB | ~4,500 tokens |
| MEMORY.md (去重) | 120 行 / 7.0KB | 97 行 / 6.2KB | ~800 tokens |
| process-bom-semantics SKILL.md | 485 行 / 24.8KB | 220 行 / 8.9KB | ~5,500 tokens |
| **合計** | — | — | **~10,800 tokens/session** |

1. **Global CLAUDE.md 清空**：專案指令統一由 `D:\ai-office\.claude\CLAUDE.md` 管理，全域檔案僅保留遷移說明
2. **MEMORY.md 去重**：TS/TCDT/H3TRB/Schottky 定義已沉澱至 reliability-testing Skill，MEMORY.md 改為單行引用
3. **process-bom-semantics 精簡**：詳細範例/統計/SQL/修正歷史移至 `references/rule-details.md`（151 行），SKILL.md 保留規則摘要

#### Skills 按需載入評估（僅建議，未執行）

| Skill | 大小 | 使用頻率 | 建議 |
|-------|------|---------|------|
| graph-rag | 4.2KB | 低（僅 knowledge graph 查詢） | 移至 on-demand |
| questionnaire-response | 5.9KB | 低（僅客戶問卷場景） | 移至 on-demand |
| mes-report | 6.4KB | 低（僅 MES 報表場景） | 移至 on-demand |
| _skill_template | 245B | 從不使用 | 刪除 |
| bom-rules | 6.4KB | 高（BOM 分析核心） | 保留 |
| package-code | 16.6KB | 中（PKG CODE 場景） | 保留（但可考慮精簡） |
| reliability-testing | 11.4KB | 中（可靠性場景） | 保留 |
| process-bom-semantics | 8.9KB(已精簡) | 高（製程 BOM 核心） | 保留 |

移動 3 個低頻 Skill 可再省 ~5,500 tokens/session。刪除 _skill_template 省 ~80 tokens。

---

### EVO-009: Schema-First SQL 防護機制（2026-04-01）

**觸發**：AI（Leader/query-runner）寫 SQL 時常從記憶推斷不存在的 table/column 名稱，造成查詢報錯。屬系統性「schema 幻覺」問題，需架構層面根治。

**類型**：工具新增 + 流程強化 + Agent 更新
**影響範圍**：shared/tools/（新增 1）、shared/workflows/definitions/（修改 2）、.claude/agents/（修改 1）、CLAUDE.md

#### 設計決策

1. **三層防護**：Schema Cache（Layer 1）+ CLAUDE.md 鐵則（Layer 2）+ query-runner Step 0（Layer 3）
2. **Layer 4（SQL 語法解析）不做**：SQL parser 處理 CTEs/aliases/subqueries 過於複雜，ROI 不足。db_schema.py 內含 best-effort validate-sql 供手動檢查，但不強制。
3. **SCHEMA 命名**：`SCHEMA_{db_stem}.md`（如 `SCHEMA_ecr_ecn.md`），避免同目錄多 DB 互相覆蓋
4. **generate_schema_cache 作為獨立 workflow 節點**（非 post-action），與 coordinator.py 正交
5. **analysis_report 新增 load_schema 前置節點**，確保查詢前有 schema

#### 實作

- 新增 `shared/tools/db_schema.py`：
  - `generate <db_path>`：生成 SCHEMA_{db}.md（tables/columns/types/row count/sample values/indexes/views）
  - `show <db_path> [--compact]`：stdout 輸出（compact 格式一行一表，適合 agent context）
  - `validate-sql <db_path> <sql>`：best-effort table/column 名稱檢查（heuristic，非 full parser）
  - `generate-all`：掃描所有 projects/*/workspace/db/*.db + kb_index.db 批量生成
- 修改 `data_ingestion.json`：`ingest_to_db` → `generate_schema_cache` → `post_validation`
- 修改 `analysis_report.json`：新增 `load_schema` 節點作為 `query_db` 前置依賴
- 修改 `query-runner.md`：Step 0 Schema-First 協議（讀 SCHEMA 或動態查詢，禁止從記憶推斷）
- 修改 `CLAUDE.md` 第 8 節：新增 SQL Schema-First 鐵則

#### 未實作（評估後排除）

- **Layer 4 Pre-execution SQL Validator**：SQL 語法解析（sqlparse/sqlglot）遇到 CTEs、表別名、子查詢時誤報率高。db_schema.py 的 `validate-sql` 提供 best-effort 檢查作為手動工具，不整合進 workflow 強制閘門。

### EVO-008: 全域知識語意檢索（Embedding Semantic Search）（2026-03-25）

**觸發**：知識量達 306 nodes（137 decisions + 87 learning + 58 col_sem + 24 rules），LIKE keyword 匹配在中英混合語境下漏召回率已可感知（如搜 "family grouping" 找不到 "family_grouping"）。process-analysis 專案已有完整 embedding 基礎設施（Qwen3-Embedding-4b via Ollama），但未擴展到全域 KB。

**類型**：知識架構升級
**影響範圍**：shared/tools/（新增 1、修改 1）、shared/kb/knowledge_graph/（修改 1）、CLAUDE.md、README.md

#### 設計決策

1. **整合進 kb_index.py**（不另建工具）：查詢介面統一，Leader 不需記兩個工具名
2. **`--semantic` 為選項而非預設**：Ollama 不可用時自動 fallback 到 LIKE，不破壞現有行為
3. **製程 KG 和全域 KB 保持分離**：只共享 embedding 基礎設施（embedding_utils.py）
4. **增量 sync**：node_embeddings 記錄 embed_text + embed_model，文本或模型未變則 skip

#### 實作

- 新增 `shared/tools/embedding_utils.py`：通用 embedding 模組（get_embedding, cosine_similarity, is_ollama_available）
- 修改 `shared/tools/kb_index.py`：
  - 新增 `node_embeddings` 表（node_id, embedding BLOB, embed_text, embed_model, updated_at）
  - 新增 `sync --embed`（增量向量化）/ `sync --embed-force`（全量重建）
  - 新增 `related --target <topic> --semantic`（語意搜尋，cosine similarity）
  - 新增 `related_semantic()` 方法：query 向量化 → 對所有 active node 計算 cosine → top-k 排序
  - Ollama 離線自動 fallback 到 LIKE + 印 warning
- 修改 `shared/kb/knowledge_graph/kb_schema.sql`：新增 node_embeddings CREATE TABLE
- 修改 `projects/process-analysis/workspace/scripts/qar_embed.py`：改用 import embedding_utils

#### 驗證結果

- 269/307 active nodes 成功向量化（38 nodes 無 target+summary 故 skip）
- 首次全量 ~2 分鐘（RTX 4060 + Ollama Qwen3-Embedding-4b）
- 增量 sync：0 embedded, 269 skipped（文本未變全跳過）
- 語意搜尋品質：
  - "family grouping" → keyword 零結果 vs semantic 找到 D-109 (sim=0.719)
  - "die size precision" → 命中 ECR-L05, D-108, CS-028, D-021, D-066
  - "copper wire verification" → 跨語言命中 ECR-R1, ECR-R3, D-025

#### 後續規劃（Phase 2-3，非本次範圍）

- Phase 2：edges 關係豐富化（conflicts_with, depends_on, refines — 規則推導，不需 LLM）
- Phase 3：LLM 關係抽取（gpt-oss batch，等 decisions > 200 條再做）

---

### EVO-007: Mermaid Diagram Renderer Tool（2026-03-24）

**觸發**：Leader 需要一鍵從 Mermaid 語法產出 PNG 圖片，不用手動去網站渲染
**類型**：新增共用工具
**影響範圍**：shared/tools/ (新增 1 檔案)

#### 實作

- 新增 `shared/tools/mermaid_render.py`
- 技術方案：Playwright (headless Chromium) + Mermaid JS CDN
- 支援 CLI 和 Python import 兩種使用方式
- 4 種主題：default, dark, forest, neutral
- Retina 品質輸出（scale=2 預設）
- 自動裁切圖表範圍（無多餘空白）
- 中文字體支援（Microsoft JhengHei / Noto Sans TC）

#### 使用方式

```bash
# CLI
python shared/tools/mermaid_render.py render --code "graph TD; A-->B" --output out.png
python shared/tools/mermaid_render.py render --input diagram.mmd --output out.png --theme dark

# Python
from shared.tools.mermaid_render import render_mermaid
render_mermaid("graph TD\n  A-->B", "output.png")
```

#### 設計決策

- **不做成 Skill**：這是純工具（無領域知識），放 shared/tools/ 最合適
- **不依賴 MCP**：直接用 Playwright Python 套件，自包含完整流程
- **不做成 Agent**：渲染操作快速且輸出小，不需要 context 隔離
- **CDN 依賴**：Mermaid JS 從 jsDelivr CDN 載入，需要網路連線

---

### EVO-006: LangChain / LangGraph 導入可行性評估（2026-03-18）

**觸發**：使用者要求評估外部框架對現有系統的價值
**類型**：架構評估（純研究，無程式碼變更）
**決策**：待記錄至 decisions.md

---

#### 0. 執行摘要

**建議：不導入 LangChain / LangGraph。** 當前系統是一個以 Claude Code CLI 為 runtime 的單人 AI 工作助手，其核心價值在於 CLAUDE.md 軟治理 + coordinator.py 流程閘門 + Skills/Decisions 知識累積的有機整合。LangChain/LangGraph 設計目標是「Python 程式中編排 LLM 呼叫」，與本系統「AI Agent 直接在 CLI 中工作、由 markdown 指令驅動行為」的架構模式根本不同。導入會引入大量抽象層、破壞現有輕量級整合、且解決不了當前的實際痛點。改進應集中在 coordinator.py 的模組化重構和 Claude Agent SDK 的觀察評估上。

---

#### 1. 現狀分析

##### 1.1 coordinator.py 能力盤點

| 面向 | 現狀 | 評估 |
|------|------|------|
| 規模 | 518 行 Python，單檔案 | 適中，可維護 |
| 節點依賴 | JSON 定義 `depends_on`，完成後自動 unblock | 足夠（DAG 拓撲） |
| 驗證器 | 動態載入 `validators/*.py`，每個 validate() 回傳 (bool, msg) | 強大，可擴展 |
| 狀態持久化 | `state/current.json`，atomic write（tmp + rename） | 可靠 |
| Hook 整合 | Stop hook（阻止未完成時退出）、PostToolUse hook（匹配 required_outputs） | Claude Code 原生整合 |
| 歷史追蹤 | counters + history（最近 50 條） | 足夠 |
| 介面 | 純 CLI（`sys.argv` 解析） | 不支援 import 調用 |

**已知痛點**：
1. **CLI-only**：無法被 Python 程式 import 使用，所有調用必須走 `subprocess` 或 `sys.argv`
2. **無條件路由**：節點只有 depends_on（前置依賴），沒有 if/else 分支能力，所有條件判斷由 AI 在 CLAUDE.md 指令層處理
3. **無重試/超時**：validator 失敗後無自動重試機制，依賴 AI 手動修正後重試
4. **無並行執行**：節點是序列完成的（雖然多個 ready 節點理論上可並行，但 AI 一次只做一件事）
5. **Shell JSON 序列化**：`--context '{"key":"value"}'` 在 Windows Git Bash 中偶爾有跳脫問題

##### 1.2 現有 Agent 架構

3 個活躍 Agent（query-runner, report-builder, architect），全部是「工具型隔離器」而非「領域專家」。Claude Code 根據 YAML frontmatter 的 `description` 自動委派。Agent 之間不互相呼叫，由 Leader 串接。

##### 1.3 工具鏈

- **知識管理**：kb_index.py（sync/validate/generate-summary/generate-index/check-conflict）、kb_writer.py（append-only）
- **資料處理**：parsers/（desc_parser, pkg_code_parser）、searchers/（material_search, knowledge_store）
- **報告生成**：MCP servers（xlsx, docx, pptx）— COM 自動化
- **知識索引**：SQLite kb_index.db + graph_query.py

##### 1.4 Workflow 統計

| Workflow | 節點數 | Validators | 執行次數 |
|----------|--------|-----------|---------|
| session_start | 6 | check_knowledge_health | 21 |
| post_task | 5 | check_project_state, check_decisions, check_memory | 29 |
| data_ingestion | 6 | check_exclusion | ~5 |
| knowledge_lifecycle | 4 | check_dynamic_kb_status | ~3 |
| analysis_report | 4 | (none) | ~5 |

---

#### 2. LangChain 評估

##### 2.1 模組逐一分析

| LangChain 模組 | 功能 | 對本系統的價值 | 理由 |
|---------------|------|-------------|------|
| **Chains** | 串聯 LLM 呼叫步驟 | **無** | 本系統的「鏈」是 CLAUDE.md 指令 + coordinator.py 節點，AI Agent 自己就是執行者，不需要外部 Python 程式來「呼叫」AI |
| **Agents (ReAct)** | Tool-using LLM agent | **無** | Claude Code 本身就是一個完整的 ReAct agent（有 Read/Write/Bash/Glob/Grep 工具），不需要 LangChain 再包一層 |
| **Memory** | 對話記憶管理 | **低** | 本系統有自己的記憶體系（MEMORY.md + agent memory + project_state.md + decisions.md），比 LangChain 的 BufferMemory/SummaryMemory 更貼合領域 |
| **Retrievers/RAG** | 向量檢索 + 生成 | **低~中** | kb_index.py 的 SQLite 全文搜索 + check-conflict 的 Jaccard 相似度已覆蓋大部分需求。向量搜索對 110+ 條決策的規模是殺雞用牛刀 |
| **Tools** | 工具封裝 | **無** | MCP 工具已經有標準化封裝（settings.local.json 權限管理），Python 工具直接走 Bash 調用 |
| **Output Parsers** | 結構化輸出解析 | **低** | Sub-agent 輸出格式由 system prompt 控制（如 query-runner 的摘要格式），不需要 Pydantic parser |
| **Document Loaders** | 文件載入 | **無** | 本系統用 Read tool + Python (openpyxl/chardet) 處理，已有完善的編碼偵測和格式處理 |

##### 2.2 LangChain 導入成本

| 成本項 | 說明 |
|--------|------|
| **Runtime 衝突** | LangChain 假設你在 Python 程式中呼叫 LLM API。本系統的 LLM runtime 是 Claude Code CLI，不走 API。要用 LangChain 就得同時維護兩套 LLM 呼叫路徑 |
| **依賴膨脹** | langchain + langchain-community + langchain-core + 向量庫（faiss/chroma） = 數十個新依賴 |
| **抽象稅** | LangChain 的 Chain/Agent/Tool 抽象與 Claude Code 的 Sub-agent/MCP/Skills 抽象完全正交，無法自然映射 |
| **維護負擔** | LangChain 版本迭代極快（breaking changes 頻繁），本系統需要穩定性 |
| **學習成本** | 使用者是可靠性工程師，不是 AI 框架開發者，增加框架複雜度無益 |

##### 2.3 結論

**LangChain 對本系統價值為零到極低。** 本系統不是「Python 程式呼叫 LLM」的模式，而是「AI Agent 直接工作、由 markdown 驅動行為」的模式。兩者的架構前提根本不同。

---

#### 3. LangGraph 評估

##### 3.1 StateGraph 與 coordinator.py 比較

| 特性 | coordinator.py | LangGraph StateGraph |
|------|---------------|---------------------|
| **圖定義** | JSON 檔案（nodes + depends_on） | Python 程式碼（add_node + add_edge） |
| **狀態管理** | current.json（atomic write） | TypedDict + MemorySaver/SqliteSaver |
| **條件路由** | 無（AI 在指令層判斷） | add_conditional_edges（Python 函數） |
| **循環** | 不支援 | 支援（透過條件邊回到之前節點） |
| **人機交互** | PostToolUse hook + Stop hook | interrupt_before/interrupt_after |
| **檢查點** | 無（但有 state/current.json 快照） | 內建 Checkpointer（可回滾到任意節點） |
| **並行** | 理論可行但未使用 | Send API 支援 map-reduce 模式 |
| **可視化** | coordinator.py status（文字） | Mermaid 圖自動生成 |
| **執行者** | AI Agent（Claude Code CLI） | Python 函數（呼叫 LLM API 或工具） |

##### 3.2 LangGraph 的潛在優勢

1. **條件路由**：`data_ingestion` 的 `confirm_with_user` 節點後，理論上可以分支到「使用者拒絕→回到 detect_structure」或「使用者確認→continue」。但目前 AI 在 CLAUDE.md 指令層處理這個邏輯，運作正常。

2. **檢查點/回滾**：如果 validator 失敗，可以回滾到上一個檢查點重試。但目前系統的 validator 失敗模式是「AI 修正問題後重新 complete」，不需要自動回滾。

3. **Mermaid 可視化**：自動生成 workflow 流程圖。這個有輕微價值，但可以用 10 行 Python 從現有 JSON 定義生成。

##### 3.3 LangGraph 的根本衝突

**最關鍵的問題：LangGraph 的節點是 Python 函數，本系統的節點是 AI Agent 的行為步驟。**

coordinator.py 的設計哲學是：
```
JSON 定義「什麼時候做什麼」→ AI Agent 自己決定「怎麼做」→ Validator 驗證「做對了嗎」
```

LangGraph 的設計哲學是：
```
Python 定義「圖結構 + 每個節點的邏輯」→ LangGraph runtime 驅動執行 → State 傳遞
```

要用 LangGraph 取代 coordinator.py，需要把每個 workflow 節點包裝成 Python 函數，函數內部呼叫 Claude API 或執行工具。這意味著：

- 放棄 Claude Code CLI 的原生能力（Read/Write/Glob/Grep/MCP 工具都是 CLI 內建的）
- 需要自建 API 呼叫層（Anthropic SDK + 工具定義 + 結果解析）
- CLAUDE.md 的軟治理機制全部失效（LangGraph 節點函數不讀 CLAUDE.md）
- Skills 自動發現機制失效（需要手動把 SKILL.md 內容注入 system prompt）
- Sub-agent 委派機制需要重建（LangGraph 不認識 Claude Code 的 agent 定義格式）
- Hooks（Stop, PostToolUse, SubagentStop）全部需要用 LangGraph 的 interrupt 機制替代

**這不是「導入框架」，而是「重寫整個系統」。**

##### 3.4 與現有 JSON 定義的相容性

理論上可以寫一個適配層：讀取 `definitions/*.json` → 自動建立 StateGraph。但這只解決了圖定義的轉換，沒解決「誰來執行節點邏輯」的根本問題。

##### 3.5 結論

**LangGraph 對本系統價值為低，且導入成本極高。** 它能提供的條件路由和檢查點功能，可以用 20-30 行 Python 在 coordinator.py 中實現（見第 4 節替代方案），不值得引入完整框架。

---

#### 4. 替代方案分析

##### 4.1 方案 A：改進 coordinator.py（推薦）

**範圍**：針對第 1.1 節的 5 個痛點，逐一改進。

| 痛點 | 改進方案 | 預估工作量 |
|------|---------|-----------|
| CLI-only | 拆分為 `coordinator_core.py`（可 import）+ `coordinator_cli.py`（CLI wrapper） | 2-3 小時 |
| 無條件路由 | 在 JSON 定義中加入 `condition` 欄位（Python 表達式），complete() 時 eval | 1-2 小時 |
| 無重試 | validator 失敗時允許 `max_retries` 參數（JSON 定義中指定） | 1 小時 |
| 無並行 | 現實不需要（單 AI Agent），低優先級 | 不做 |
| Shell JSON | 改用 `--context-file /path/to/ctx.json` 或 stdin 輸入 | 30 分鐘 |

**優點**：零依賴新增、向後完全相容、改動精準可控
**風險**：低

##### 4.2 方案 B：Prefect / Temporal

| 框架 | 定位 | 適用性 |
|------|------|--------|
| Prefect | Python 資料管線編排 | 過重（需要 Prefect server + UI），設計給 ETL 管線不是 AI Agent |
| Temporal | 分散式 workflow 引擎 | 極過重（需要 Temporal server + worker），設計給微服務編排 |

**結論**：兩者都是伺服器級框架，為分散式生產環境設計。本系統是單機單人 AI 助手，完全不適用。

##### 4.3 方案 C：Claude Agent SDK

Anthropic 提供的 `claude-code-sdk`（Python/TypeScript）允許以程式碼方式呼叫 Claude Code。

| 面向 | 評估 |
|------|------|
| **價值** | 可實現批次任務（如夜間排程跑 session_start + data_ingestion）、多 session 管理 |
| **成熟度** | 較新，需觀察穩定性 |
| **整合度** | 高 — 使用相同的 Claude Code 環境（CLAUDE.md、Skills、Hooks 全部生效） |
| **導入條件** | 當出現「需要程式化調用 Claude Code」的需求時（如 nightly batch、CI/CD 觸發） |

**結論**：目前不需要，但是未來最有可能導入的方案。建議持續觀察，等以下觸發條件出現再行動：
- 需要排程自動化（如每晚自動 ingest 新資料）
- 需要程式化觸發 workflow（如 webhook 觸發分析報告）
- Claude Code CLI 的互動模式無法滿足新需求

##### 4.4 方案 D：自建輕量 DAG

在 coordinator.py 基礎上建一個極簡 DAG 引擎，支援條件邊和循環。本質上是方案 A 的加強版。

**評估**：可行但目前不需要。5 個 workflow 的節點數都在 4-6 個，線性依賴為主，條件路由的需求很弱。等 workflow 複雜度成長到需要循環/分支時再考慮。

---

#### 5. 方案比較總表

| 方案 | 價值 | 成本 | 風險 | 建議 |
|------|------|------|------|------|
| LangChain 導入 | 零~極低 | 高（依賴膨脹、抽象衝突、維護負擔） | 高（破壞現有架構） | **不導入** |
| LangGraph 導入 | 低 | 極高（等同系統重寫） | 極高（放棄 Claude Code CLI 生態） | **不導入** |
| coordinator.py 改進 | 中（解決實際痛點） | 低（5-7 小時增量改進） | 低（向後相容） | **推薦** |
| Prefect / Temporal | 零 | 極高（server 架設） | 高（過度工程） | **不導入** |
| Claude Agent SDK | 中~高（未來） | 中 | 中（需觀察成熟度） | **觀察，待觸發** |
| 自建 DAG | 低~中 | 中 | 低 | **觀察，待需求** |

---

#### 6. 最終建議

##### 6.1 短期（立即可做）

**不導入任何外部框架。** 集中在 coordinator.py 的模組化重構：
1. 拆分為 `coordinator_core.py` + `coordinator_cli.py`，使核心邏輯可 import
2. 加入 `--context-file` 選項，解決 shell JSON 跳脫問題
3. 以上兩項不改動任何 JSON 定義、validator、hook

##### 6.2 中期（3-6 個月觀察）

- 追蹤 Claude Agent SDK 的穩定性和功能完善度
- 若出現批次自動化需求，優先評估 SDK 方案
- coordinator.py 條件路由和重試機制按需加入（目前 5 個 workflow 都不需要）

##### 6.3 長期觸發條件

以下任一條件成立時，重新評估外部框架：
- 多使用者同時存取同一知識庫（需要併發控制）
- 生產管線自動化（nightly ERP → ingest → report → email）
- Claude Code CLI 被棄用或功能大幅縮減
- Workflow 複雜度增長到需要循環/分支/並行（15+ 節點、3+ 條件路由）

---

#### 7. 關鍵認知：為什麼傳統 AI 框架不適合本系統

本系統的獨特之處在於 **AI Agent 就是 runtime**：

```
傳統模式（LangChain/LangGraph）：
  Python 程式 → 呼叫 LLM API → 解析回應 → 執行工具 → 再呼叫 LLM
  （Python 是主控，LLM 是被呼叫方）

本系統模式（Claude Code CLI）：
  AI Agent → 讀取 CLAUDE.md 指令 → 自主決定行動 → 使用工具 → 自我驗證
  （AI 是主控，Python 工具是被呼叫方）
```

控制權的方向完全相反。LangChain/LangGraph 是「程式編排 AI」，本系統是「AI 編排工具」。試圖在後者之上疊加前者，不僅多餘而且有害。

coordinator.py 的角色不是「workflow 引擎」（在傳統意義上），而是「行為閘門」— 它不驅動執行，而是確保 AI Agent 按順序、有驗證地完成工作。這個定位與 LangGraph 的「圖執行引擎」定位根本不同。

**狀態**：評估完成，待記錄決策至 decisions.md

---

### EVO-005: Agent 架構重構：專家 → 工具人（2026-03-10）

**觸發**：使用者審查 + Leader 分析
**決策**：待記錄至 decisions.md

#### 根因分析

Agent 定位為「領域專家」但實際知識遠低於 Leader：
- Agent 無法存取 MEMORY.md（含使用者明確指示、核心行為準則、術語更正）
- Agent 無法存取 decisions.md 的 119 條已確認決策（或需額外 Read 消耗 token）
- Agent 無法存取對話上下文中的使用者偏好和即時修正
- 結果：Agent 做出的「領域判斷」品質反而低於 Leader 直接做

#### 核心原則轉變

**舊原則**：Agent 的價值在「懂」— 預載 Skill + 資料庫查詢 = 領域判斷
**新原則**：Agent 的價值在「隔離」— 隔離大量輸出、隔離工具複雜度、隔離掃描範圍

#### 變更內容

**砍掉 3 個假專家 Agent**（移至 `.claude/agents-legacy/`）：

| Agent | 原定位 | 砍掉理由 |
|-------|--------|---------|
| bom-process-expert | BOM/製程領域專家 | Leader 有完整 Skills + 119 條 Decisions + MEMORY.md，Agent 知道更少 |
| reliability-expert | 可靠性測試專家 | 同上，關鍵知識（TS/TCDT 更正、Schottky 注意事項）在 MEMORY.md，Agent 看不到 |
| data-quality-checker | 資料品質驗證 | haiku model 判斷深度不足，Leader 直接 SQL 更精準 |

**保留 2 個真工具人 Agent**：

| Agent | 定位 | 保留理由 |
|-------|------|---------|
| architect | 結構掃描器 + 大量文件產出器 | 隔離大量檔案掃描和批量修改的 context 汙染 |
| report-builder | MCP COM 工具操作器 | 隔離 Office COM 工具的複雜度和資源管理 |

**新增 1 個工具人 Agent**：

| Agent | 定位 | 新增理由 |
|-------|------|---------|
| query-runner | SQL 批量執行 + 結果摘要器 | 大量 SQL 結果灌進 Leader context window 是最大的 token 消耗來源之一 |

#### 影響範圍

| 檔案 | 動作 | 說明 |
|------|------|------|
| `.claude/agents/bom-process-expert.md` | 移至 agents-legacy/ | 保留歷史參考 |
| `.claude/agents/reliability-expert.md` | 移至 agents-legacy/ | 保留歷史參考 |
| `.claude/agents/data-quality-checker.md` | 移至 agents-legacy/ | 保留歷史參考 |
| `.claude/agents/query-runner.md` | 新建 | SQL 執行器 + 摘要器 |
| `shared/workflows/definitions/data_ingestion.json` | 修改 | post_validation 移除 delegate_to |
| `shared/workflows/definitions/analysis_report.json` | 修改 | cross_validate 移除 delegate_to |
| `.claude/CLAUDE.md` | 修改 | v3.0→v3.1，Agent 表格/委派原則/工作模式全面更新 |
| `shared/kb/evolution_log.md` | 修改 | 新增 EVO-005 |

**狀態**：完成

---

### EVO-004: Context Window 膨脹導致 RAM 過高（2026-03-09）

**觸發**：使用者報告 v3.0 改版後切換到 ecr-ecn 專案時 claude.exe RAM 大量佔用。Task Manager 確認為 claude.exe 本身。

#### 1. 根因鏈分析

Claude Code 的 RAM 使用與 context window token 數量正相關。context 越大，模型推理時需要的記憶體越多。問題不是單一原因，而是多個因素疊加：

```
CLAUDE.md (14KB)                    ─┐
+ global CLAUDE.md (user's, ~20KB)   │ 系統指令層（每次會話固定載入）
+ MEMORY.md (agent memory, ~5KB)     │
+ 9x SKILL.md (83KB total)          ─┘ ~122KB 基底

+ project_state.md (58KB)           ─┐
  其中 session_history 占 25KB       │ session_start 載入
  其中 當前階段 15KB（dense log）     │
+ active_rules_summary.md (22KB)     │ load_active_context 載入
+ kb_index.py validate 輸出          │ check_knowledge_health 載入
+ diff_db 查詢結果                   ─┘

+ decisions.md (85KB)               ─┐ post_task 流程中讀取
+ learning_notes.md (76KB)           │ （EVO-003 kb_writer 已緩解）
+ column_semantics.md (32KB)         │ 按需讀取
+ ecr_ecn_rules.md (26KB)           ─┘

+ PostToolUse hook additionalContext ─ 每次 Write/Edit 累積一行提示文字
+ Sub-agent context 複製             ─ 啟動 sub-agent 時整個 context 傳遞
```

**估計 context 量**：
- 會話開始後（session_start 完成）：~200KB = ~60K tokens
- 工作中期（含 KB 查詢、Write/Edit）：~350KB+ = ~100K+ tokens
- 觸發 sub-agent 時：額外複製 base context + agent 定義 + skill 預載

#### 2. 各因素影響評估

| # | 因素 | 大小 | 必要性 | 可優化？ | 優先級 |
|---|------|------|--------|---------|--------|
| F1 | project_state.md session_history | 25KB | 低（歷史記錄，工作時不需要） | **可大幅裁減** | **P0** |
| F2 | project_state.md 當前階段 | 15KB | 中（dense changelog，只需最新版） | **可精簡** | **P0** |
| F3 | 9 SKILL.md 全量預載 | 83KB | 低（多數 session 只用 2-3 個） | **可改為 lazy load** | **P1** |
| F4 | active_rules_summary.md | 22KB | 中（決策快速查詢用） | 可改為按需查詢 | P2 |
| F5 | PostToolUse additionalContext | 每次 ~100B 累積 | 低（提示訊息） | **可精簡或移除** | **P1** |
| F6 | CLAUDE.md (project + global) | 34KB | 高（行為規範） | 暫不動 | -- |
| F7 | Sub-agent context 複製 | 整個 base | 高（agent 需要上下文） | 暫不動 | P3 |

#### 3. 改善方案

##### P0-A: project_state.md 瘦身（預估省 30-35KB）

**問題**：project_state.md 58KB 中有 40KB 是歷史資料：
- `## 會話歷史摘要`（lines 352-413）：25KB，62 行超長文字，記錄從 2026-02-06 到 2026-03-06 的所有操作細節
- `## 當前階段`（lines 33-155）：15KB，密集的版本 changelog（v5 到 v23 的所有修正記錄）

**方案**：分離歷史資料為獨立檔案，project_state.md 只保留當前狀態。

具體步驟：
1. 建立 `{P}/workspace/project_history.md`，搬移 `## 會話歷史摘要` 全部內容
2. `## 當前階段` 只保留最新 2 個版本的描述（v23 + v5 report），舊版改為一行摘要指向 project_history.md
3. `## 關鍵決策記錄` 表格（42 行）可精簡為 "最近 10 條 + 指向 decisions.md" 格式
4. `## 下一步行動` 中已完成（~~strikethrough~~）的 17 條可移除，只留未完成的

**預估效果**：project_state.md 從 58KB 降至 ~20KB（省 ~38KB = ~12K tokens）
**影響範圍**：
- check_project_state.py validator 不受影響（只檢查 mtime）
- session_start 載入量大幅減少
- 歷史資料仍可在需要時讀取 project_history.md

##### P0-B: 會話啟動節省（配合 P0-A）

**現狀**：session_start 6 個節點中，Leader 通常全部執行：
1. read_project_state → 讀 58KB（P0-A 後降為 20KB）
2. load_active_context → 讀 active_rules_summary.md 22KB
3. check_knowledge_health → 跑 kb_index.py validate（輸出文字進 context）
4. diff_db → SQL 查詢結果進 context
5. flag_open_questions → 從 project_state 提取（已在步驟 1 中）
6. report_ready → 輸出摘要

**方案**：將 load_active_context 改為真正的 lazy loading——不在 session_start 時全量讀取 active_rules_summary.md，改為在 CLAUDE.md 中註明「需要查決策時用 kb_index.py related，不需在啟動時預載」。

**預估效果**：session_start 再省 ~22KB
**影響範圍**：session_start.json 的 load_active_context 節點描述更新；CLAUDE.md 第 5 節更新

##### P1-A: Skill 延遲載入

**現狀**：Claude Code 的 Skill 自動發現機制會在 session 開始時載入所有 `.claude/skills/*/SKILL.md`。9 個 SKILL.md 合計 83KB。但實際多數 session 只會用到 2-3 個 Skill（ecr-ecn 專案主要用 bom-rules + process-bom-semantics + reliability-testing + package-code）。

**方案**：目前 Claude Code 的 Skill 載入是自動機制，無法直接控制。可行的替代方案：
- 將較少使用的 Skill（pptx-operations 7KB, word-operations 5KB, excel-operations 8KB, mil-std-750 5KB, sqlite-operations 4KB）從 `.claude/skills/` 移到 `shared/kb/skills-on-demand/`，在 sub-agent 定義中用 `skills:` 欄位指定
- 保留高頻 Skill（bom-rules, process-bom-semantics, reliability-testing, package-code）在原位
- 效果：自動載入從 83KB 降至 ~54KB（省 ~29KB = ~9K tokens）

**風險**：移出的 Skill 不再被自動發現，Leader 需要手動查閱。但這些 Skill 本身就是 sub-agent 專用（report-builder 用 Office Skill，reliability-expert 用 mil-std-750），Leader 直接需要的機率低。

**替代方案**：若不想搬移檔案，可在不需要 Office 操作的專案中建立 `.claude/skills/.skillignore` 或類似機制（需確認 Claude Code 是否支援）。

##### P1-B: PostToolUse hook additionalContext 精簡

**現狀**：每次 Write/Edit 操作觸發 `coordinator.py hook_post`，若檔案路徑匹配到 workflow 節點的 `required_outputs.path_contains`，會回傳 `additionalContext` 文字。這些文字累積在 context 中不會消失。

**分析 hook_post 邏輯**（coordinator.py lines 383-428）：
- 只在 active workflow 有匹配的 required_outputs 時才回傳 additionalContext
- 典型訊息："File write matched workflow node 'update_project_state' in post_task_20260309_... Run: python shared/workflows/coordinator.py complete update_project_state"
- 每條約 100-200 bytes
- 一個 post_task workflow 通常有 2-3 個 required_outputs 匹配（project_state.md, decisions.md, memory/）

**方案**：這個問題影響不大（每個 workflow 最多累積 ~600 bytes），但可以優化為更短的提示。目前訊息格式可以精簡。

**預估效果**：微小（~1KB/session），優先級低。

##### P2: 知識查詢模式已最佳化

EVO-003 的 kb_writer.py 已解決寫入時的全量讀取問題。查詢面的 kb_index.py `--fmt line` 已是最省 token 的方式。active_rules_summary.md 22KB 的全量讀取可透過 P0-B 避免。

**結論**：知識查詢模式不需要額外改動。

##### P3: Sub-agent context（觀察，暫不動）

Sub-agent 啟動時，Claude Code 會將當前 context（含所有已讀取的內容）傳遞給 sub-agent。這是 Claude Code 的設計，無法在應用層面控制。

P0-A 和 P0-B 的瘦身會間接降低 sub-agent 收到的 context 大小。

#### 4. 實施計畫和優先序

| 順序 | 方案 | 預估省 tokens | 實施難度 | 風險 |
|------|------|-------------|---------|------|
| 1 | P0-A project_state.md 瘦身 | ~12K | 低 | 低 |
| 2 | P0-B load_active_context lazy | ~7K | 低 | 低 |
| 3 | P1-A Skill 延遲載入 | ~9K | 中 | 中（需驗證 sub-agent 能否讀到移出的 Skill） |
| 4 | P1-B hook additionalContext | <1K | 低 | 低 |

**Phase 1（P0-A + P0-B）立即可做**：
- 合計省 ~19K tokens（約 60KB 文字量）
- 零改動 coordinator.py / validators / kb_index.py
- 向後相容（歷史資料仍存在，只是分離到獨立檔案）

**Phase 2（P1-A）需使用者確認**：
- 涉及 Skill 檔案搬移，需確認哪些 Skill 可以從自動發現中移除
- 需驗證 sub-agent 的 `skills:` 欄位是否能正確預載移出的 Skill

#### 5. 預期效果

實施 P0-A + P0-B 後：
- session_start 完成後 context：~200KB → ~140KB（-30%）
- 每次 session 的 base token 開銷：~60K → ~42K tokens
- RAM 影響：context 縮小會降低推理時的記憶體需求，但幅度取決於 Claude Code 的內部實作

**注意**：RAM 問題的根本原因是 Claude Code CLI 的架構（整個 conversation context 在記憶體中）。應用層面的優化能減輕但無法徹底解決。如果 RAM 持續是問題，可考慮：
- 更頻繁地結束/重啟 session（清空 context）
- 避免在同一 session 中進行過多操作（每次 tool 調用的輸出都會累積）

#### 6. 不做的事

- 不改 coordinator.py
- 不改任何 validator
- 不改 kb_index.py
- 不改 CLAUDE.md 的核心行為規範
- 不改 settings.local.json hooks 結構
- 不拆分 decisions.md / learning_notes.md（EVO-003 已解決寫入問題）

**狀態**：全部實施完成（2026-03-09）

#### 7. 實施記錄（2026-03-09）

**P0-A: project_state.md 瘦身**
- `## 會話歷史摘要`（25KB, 62 行）完整搬移到 `workspace/project_history.md`
- `## 當前階段` 舊版本（v7~v22）壓縮為一行摘要指向 project_history.md，保留 v23 + v5 report 細節
- `## 關鍵決策記錄` 從 42 行表格精簡為 8 行（基礎規則 + 最近關鍵決策）+ 指向 decisions.md
- `## 下一步行動` 移除 17 條已完成項目，保留 1 條未完成
- **結果**：58KB / 413 行 → 18KB / 227 行（-68%，省 ~12K tokens/session）

**P0-B: session_start lazy loading**
- session_start.json：`load_active_context` 節點描述改為 LAZY 模式說明
- session_start.json：`check_knowledge_health` 依賴從 `load_active_context` 改為 `read_project_state`（不再需要先載入 active context）
- CLAUDE.md Section 5：啟動協議更新，標明 lazy 模式
- CLAUDE.md Section 7：「查知識時」指引調整，強調 kb_index.py 優先，active_rules_summary.md 為按需讀取
- **結果**：每次 session_start 省 ~22KB（~7K tokens）

**P1-A: Skill 延遲載入**
- 5 個 Skill 從 `.claude/skills/` 移至 `.claude/skills-on-demand/`：
  - pptx-operations (7KB), excel-operations (8KB), word-operations (5KB), mil-std-750 (5KB), sqlite-operations (4KB)
- 留在自動發現的 4 個核心 Skill：bom-rules, process-bom-semantics, reliability-testing, package-code（54KB）
- report-builder.md：移除 `skills:` frontmatter，改為 system prompt 中按需 Read 指引
- reliability-expert.md：保留 reliability-testing 在 skills，mil-std-750 改為按需 Read
- CLAUDE.md Section 3：知識架構更新，分為 Layer 1a（自動）+ Layer 1b（按需）
- **結果**：自動載入 83KB → 54KB（-29KB，省 ~9K tokens/session）
- **注意**：mil-std-750 在 `.claude/skills/` 中殘留一個空鎖定目錄（Windows 檔案鎖），無 SKILL.md，不影響功能

**變更檔案清單**：
| 檔案 | 動作 | 說明 |
|------|------|------|
| `projects/ecr-ecn/workspace/project_state.md` | 重寫 | 58KB→18KB |
| `projects/ecr-ecn/workspace/project_history.md` | 新建 | 分離的歷史資料 |
| `shared/workflows/definitions/session_start.json` | 修改 | lazy loading + 依賴調整 |
| `.claude/CLAUDE.md` | 修改 | Section 3/5/7/10 更新 |
| `.claude/agents/report-builder.md` | 修改 | skills→按需 Read |
| `.claude/agents/reliability-expert.md` | 修改 | mil-std-750→按需 Read |
| `.claude/skills-on-demand/` | 新建目錄 | 5 個按需 Skill |
| `.claude/skills/{5 dirs}` | 搬移 | 移至 skills-on-demand |

**合計節省**：~28K tokens/session（P0-A 12K + P0-B 7K + P1-A 9K）

---

### EVO-003: 大型 .md 檔案 Token 浪費問題評估（2026-03-06）

**觸發**：使用者提出架構問題 — Claude Code Edit tool 強制要求先 Read 整個檔案，導致「追加一條決策」這種簡單寫入操作也要消耗 ~27K tokens 讀取 decisions.md 全文。

#### 1. 現狀分析：受影響檔案

| 檔案 | 大小 | 估計 tokens | 寫入頻率 | 每次 post_task 的 Read 開銷 |
|------|------|------------|---------|--------------------------|
| decisions.md | 80KB / 1139L | ~27K | 每個任務 1-3 條 | 必須全讀才能 Edit 追加 |
| learning_notes.md | 74KB / 1116L | ~25K | 每個任務 0-2 條 | 必須全讀才能 Edit 追加 |
| column_semantics.md | 32KB / 872L | ~11K | 偶爾（新欄位時） | 偶爾 |
| ecr_ecn_rules.md | 26KB / 516L | ~9K | 偶爾（新規則時） | 偶爾 |
| evolution_log.md | 17KB / 360L | ~6K | 架構變更時 | 偶爾 |

**核心痛點**：decisions.md 和 learning_notes.md 合計 ~52K tokens，幾乎每個 post_task 都要完整讀取一次（用於 Edit 追加）。這兩個檔案還在持續成長。

**目前的查詢優化已到位**：kb_index.py SQLite 索引、active_rules_summary.md、`--fmt line`。問題不在查詢，而在寫入。

#### 2. 方案評估

**方案 A：維持現狀（忍受 Read 開銷）**

- 優點：零遷移成本；.md 是 source of truth，人類可直接閱讀和 Git diff；現有 validator 全部正常
- 缺點：每次 post_task 浪費 ~27K-52K tokens 在 Read 上；檔案只會繼續變大
- 風險：低（不改動任何東西）
- 結論：短期可行，長期不可持續

**方案 B：SQLite 為 source of truth，.md 變為自動生成快照**

- 優點：寫入零 Read 開銷（INSERT INTO）；查詢已有 kb_index.py 基礎
- 缺點：遷移成本極高 — 需重寫所有 validator（check_decisions、check_dynamic_kb_status 都直接讀 .md）；sync 方向反轉（目前 .md -> SQLite，要改為 SQLite -> .md）；人類可讀性依賴自動生成（生成掛了就看不到最新資料）；decisions.md 的 meta 行格式、block 結構都是精心設計的，SQLite schema 要完整映射；kb_index.py 的 `_auto_supersede_in_md()` 等函數全部要重寫
- 風險：高（改動面太大，系統核心可能中斷）
- 結論：**不建議** — 投入產出比極差，且打破「.md 是 source of truth」這個已驗證的核心架構決策

**方案 C：混合方案 — 追加操作用 Bash/Python 繞過 Edit tool**

- 核心思路：既然問題是「Edit tool 要求先 Read」，那**不用 Edit tool**就好。追加操作改用 `Bash(python append_decision.py ...)` 或 `Bash(echo '...' >> file.md)`，查詢繼續用 kb_index.py
- 具體實作：
  1. 新增 `shared/tools/kb_writer.py`，提供 CLI：
     - `kb_writer.py add-decision --id D-NNN --date YYYY-MM-DD --project X --target "..." --question "..." --decision "..." --impact "..."`
     - `kb_writer.py add-learning --title "..." --content "..." --confidence high`
  2. kb_writer.py 負責：格式化 markdown block、自動生成 meta 行、追加到檔案末尾、驗證 D-NNN 連號
  3. Leader 調用方式：`Bash(python shared/tools/kb_writer.py add-decision --id D-111 ...)`  — 零 Read 開銷
  4. 需要修改已有內容時（罕見），仍用 Read + Edit（但這種情況 < 5%）
- 優點：**寫入零 Read 開銷**；.md 仍為 source of truth；現有 validator 完全不改；kb_index.py 完全不改；人類可讀性完全保留；增量式改動，風險極低
- 缺點：新增一個工具（~150 行 Python）；Leader 的 CLAUDE.md 指令需更新（寫入方式從 Edit 改為 Bash）；多了一個維護點
- 風險：低（追加操作的正確性容易驗證，不影響現有讀取/驗證鏈路）

**方案 D：檔案分割 — 按時間段拆分大檔案**

- 核心思路：decisions.md 拆為 `decisions-001-050.md`、`decisions-051-100.md`、`decisions-101-xxx.md`（活躍檔案）
- 優點：活躍檔案小，Read 開銷降低
- 缺點：所有讀取 decisions.md 的程式碼都要改（kb_index.py sync、check_decisions.py、_auto_supersede_in_md、generate-summary）；跨檔案搜索變複雜；人類瀏覽不便；分割點選擇有爭議
- 風險：中（改動面中等，但收益不如方案 C 徹底）
- 結論：**不建議** — 方案 C 更直接解決問題，且零改動現有程式碼

#### 3. 建議：方案 C（追加寫入工具）

**理由**：
1. 精確解決問題：95% 的寫入操作是「追加新條目到末尾」，剩下 5% 是修改已有內容（supersede 回寫等，這些由 kb_index.py sync 處理，本就是 Python 腳本不走 Edit tool）
2. 最小改動原則：不改任何現有工具/validator/workflow，只新增一個追加工具
3. Token 節省量化：每次 post_task 省下 ~27K（decisions）+ ~25K（learning_notes）= ~52K tokens 的 Read 開銷。按平均每天 3-5 次 post_task，每天省 150K-250K tokens
4. 向後相容：.md 仍為 source of truth，任何時候都可以退回 Edit 方式

#### 4. 實施計畫

**Phase 1（立即可做）**：建立 `shared/tools/kb_writer.py`

```
kb_writer.py add-decision
  --id D-NNN
  --date YYYY-MM-DD
  --project <project>
  --target "<target text>"
  --question "<question>"
  --decision "<decision>"
  --impact "<impact>"
  [--status active]
  [--supersedes D-XXX]
  [--refs_skill <skill>]
  [--refs_db <db:table>]
  [--affects <scope>]
  [--review_by YYYY-MM-DD]
  [--source "<source>"]

kb_writer.py add-learning
  --title "<title>"
  --date YYYY-MM-DD
  --content "<observation text>"
  --confidence high|medium|low
  [--project <project>]
  [--status active]
  [--related_decision D-NNN]

kb_writer.py next-id
  # 回傳下一個可用的 D-NNN 編號
```

功能要點：
- 讀取檔案最後幾行確認追加位置（不需讀全文，用 `seek` 到末尾附近）
- 自動格式化 markdown block（含 meta 行）
- add-decision 自動驗證 D-NNN 連號（只需 grep 最後一個 D-NNN）
- add-learning 自動插入 `<!-- status: active -->` 標記
- 輸出 JSON 結果（成功/失敗 + 追加的行數）

**Phase 2（更新 CLAUDE.md 指令）**：

在 CLAUDE.md 第 6 節 Post-Task Checklist 中：
- 「記錄決策」改為使用 `kb_writer.py add-decision` 而非 Edit
- 「記錄知識」改為使用 `kb_writer.py add-learning` 而非 Edit
- 保留 Edit 作為「修改已有條目」的 fallback

**Phase 3（驗證）**：
- 手動執行幾次 add-decision / add-learning
- 確認 check_decisions.py validator 通過
- 確認 check_dynamic_kb_status.py validator 通過
- 確認 kb_index.py sync 正常索引新條目

#### 5. 不做的事

- **不改 kb_index.py**（sync/validate/generate-summary 全部不動）
- **不改任何 validator**
- **不改 coordinator.py**
- **不改檔案結構**（.md 仍為 source of truth）
- **不拆分檔案**
- **不引入 SQLite 為 source of truth**

#### 6. 長期觀察

- 若 decisions.md 成長到 200K+ tokens（~600 條決策），考慮方案 D 檔案分割作為補充
- 若 Claude Code 未來版本支援「只讀檔案末尾 N 行後追加」的 Edit 模式，此工具可退役
- column_semantics.md 和 ecr_ecn_rules.md 目前成長速度慢，暫不處理

**狀態**：已實施完成（2026-03-09）

#### 實施記錄（2026-03-09）

- **Phase 1**：建立 `shared/tools/kb_writer.py`（~170 行）
  - `next-id`：讀尾部 8KB 取最大 D-NNN，回傳下一個可用 ID
  - `add-decision`：自動格式化 markdown block + meta 行 + 連號驗證 + 追加寫入
  - `add-learning`：自動插入 `<!-- status: active -->` + 追加寫入
  - 跳號保護：ID 不連續時 exit code 1 拒絕寫入
- **Phase 2**：更新 CLAUDE.md 第 6 節 Post-Task Checklist
  - 記錄決策/知識改為 `Bash(python shared/tools/kb_writer.py ...)`
  - 明確禁止用 Edit tool 追加（會浪費 ~52K tokens Read 全文）
  - 修改已有條目仍保留 Read + Edit 路徑
- **Phase 3**：驗證通過
  - `kb_index.py validate` — Meta coverage 100%，無 ERROR
  - `kb_index.py sync` — 新條目正常索引
  - D-116 + ECR-L49 作為測試條目寫入，同時為此變更的正式記錄

---

### EVO-002: 索引文檔自動生成機制（2026-03-06）

**觸發**：架構審查發現 _index.md 和 tool_registry.md 因無 validator 保護而漂移（Skills 數量、專案清單、工具清單均落後現實）
**問題根因**：v3.0 遷移時，原由 learner/promoter agent 負責的索引更新職責未被 workflow 接手

#### 設計決策

- 有 validator 保護的文檔從未漂移（decisions, project_state, learning_notes），沒有 validator 的就會漂移
- 解法：讓 _index.md 從「手動維護」改為「腳本自動生成」，整合到現有 post_task workflow
- 整合方式：Method B — 在 check_decisions.py validator 成功時附帶觸發 generate-index（同 generate-summary 模式）
- tool_registry.md 保留為詳細參考文件（含使用範例、格式速查），工具摘要表由 _index.md 自動維護

#### 變更項目

1. **kb_index.py** — 新增 `generate_index()` 方法和 `generate-index` CLI 命令。自動掃描：
   - `.claude/skills/*/` — 讀取 .skill.yaml 取得名稱、規則數、觸發詞、更新日期；SKILL.md 行數
   - `shared/kb/dynamic/` — 統計各檔案條目數
   - `shared/kb/decisions.md` — 找最後一個 D-NNN 編號
   - `projects/*/` — 讀取 project.md 取標題，掃描 workspace/db/ 取 DB 名稱
   - `shared/tools/**/*.py` — 讀取 docstring 作為說明
   - 規則明細、外部標準、升級歷程為靜態模板（module-level 常量）
   - 產出格式與現有 _index.md 完全一致

2. **check_decisions.py** — 在 generate-summary 觸發之後追加 generate-index 觸發，每次 post_task 的 record_decisions 完成時自動重建 _index.md

3. **CLAUDE.md** — 第 7 節「查知識時」區塊新增第 6 點：generate-index 說明及自動觸發時機

4. **tool_registry.md** — 加入 Note 指向 _index.md 自動維護的工具摘要表，保留詳細內容作深度參考

5. **_index.md** — 現在由腳本產生，新增「由 kb_index.py generate-index 自動產生，請勿手動編輯」提示

#### 技術實作

- `generate_index()` 方法約 130 行（含 5 個掃描區塊 + markdown 組裝）
- 3 個靜態模板常量（`_RULES_DETAIL_TEMPLATE`, `_EXTERNAL_STANDARDS_TEMPLATE`, `_UPGRADE_HISTORY_TEMPLATE`）定義在 module level
- 依賴 pyyaml（已是系統依賴）和 ast（標準庫）
- 產出 UTF-8 編碼，約 6.7K chars

**狀態**：全部完成

---

### EVO-001: 架構審查修正（2026-03-06）

**觸發**：外部架構審查報告 + architect agent 評估
**評估報告**：shared/kb/memory/2026-03-06-architecture-review-response.md

#### 變更項目

1. **H8 — settings.local.json**：補上 3 個 xlsx MCP 工具的 allow 權限（`apply_style_preset`, `auto_fit_columns`, `add_conditional_format`），與 excel-operations/.skill.yaml 的 requires.tools 對齊
2. **M3 — learning_notes.md**：補齊近期 3 筆條目（ECR-L50, ECR-L43, ECR-L44）的 `<!-- status: active -->` 標記，check_dynamic_kb_status validator 現在通過
3. **H3 — CLAUDE.md**：Skills 數量從 6 更新為 9，清單補上 excel-operations, word-operations, sqlite-operations（第 76 行 + 第 259 行）
4. **H4 — _index.md**：專案清單補上 clip-bond-sim 和 electrical-analysis；Skills 表補上 3 個新 Skill
5. **H2 — protocols/README.md**：加入 `Status: Legacy (v2.7)` 標記，說明現行系統以 CLAUDE.md v3.0 為準
6. **M4 — post_task.json**：check_project_state 的 max_age_seconds 從 300 放寬到 600，避免長操作時 false negative
7. **H7 — check_exclusion.py + data_ingestion.json**：validator 新增 scope 參數支援（`full_db`/`current_batch`），data_ingestion workflow 預設使用 `current_batch` 避免歷史資料阻斷新 ingestion

#### 未採納項目

- **H1**（powershell 禁止 vs 允許）：settings 放行不等於鼓勵使用，CLAUDE.md 指令約束有效
- **H5**（delegate_to 不被強制）：設計意圖，coordinator 管流程順序，委派是 AI 語意行為
- **H6**（required_outputs 不強制）：PostToolUse hook 提醒機制足夠，AI Agent 主動遵守
- **M1**（session_start optional 節點）：optional 是設計意圖，不是每次會話都需要全部檢查
- **M2**（check_memory 預設通過）：條件觸發機制，不滿足條件就應該通過
- **L2**（版本號混雜）：各文件獨立版本號，不是同一版本體系
- **L3**（歷史資產界線）：命名慣例已足夠區分

**核心判斷依據**：外部報告以傳統軟體「code enforcement」思維評估 AI Agent 系統，導致把 CLAUDE.md 軟治理機制誤判為「無效」。16 項發現中 5 項真正需修、4 項部分有效、7 項非問題。

**狀態**：完成（H7 scope 修正有殘餘問題，見 EVO-001a）

---

### EVO-001a: EVO-001 殘餘問題補修（2026-03-06）

**觸發**：EVO-001 完成後完整掃描發現 7 項殘餘問題

#### 變更項目

1. **R1（高）— check_exclusion.py**：修正 operation_id 取值邏輯，現在同時從 `context["outputs"]`（runtime，優先）和 `context["params"]`（static）嘗試取得。AI 在 complete 時傳入 `--outputs '{"operation_id":"xxx"}'` 即可正確啟用 current_batch scope
2. **R2（高）— CLAUDE.md:191**：更新 apply_exclusions 描述，反映 scope=current_batch 新行為及 operation_id 傳遞方式
3. **R3（中）— check_project_state.py:12**：fallback 預設值從 300 改為 600，與 post_task.json 的 max_age_seconds=600 一致
4. **R4（中）— _index.md:4**：最後更新日期從 2026-02-25 改為 2026-03-06
5. **R5（中）— _index.md:125**：決策範圍從 D-001~D-055+ 更新為 D-001~D-110+
6. **R6（低）— evolution_log.md**：EVO-001 狀態改為標註 H7 有殘餘問題，新增本 EVO-001a 補修記錄
7. **R7（低）— _index.md 共用工具表**：從 2 項擴充為 12 項，涵蓋 shared/tools/ 全部 .py 檔案（含 parsers/、searchers/、reporters/ 子目錄）

**狀態**：全部完成

---

### 2026-03-06：知識一致性管理機制（5 項強化）

**類型**：架構升級（完成）
**觸發**：使用者提問「是否有引入狀態機概念？」→ 分析後發現偵測/阻斷/自動修復三方面均有缺口
**決策**：D-110

**問題分析**：
- 決策的 supersede 只有標記、無自動回寫（手動容易忘）
- Dynamic KB（learning_notes）無生命週期狀態
- validate 偵測到 ERROR 不阻斷流程（形同虛設）
- 同 target 衝突只做精確字串比對（漏掉語意重疊）
- 無 TTL 機制（過時決策永遠 active）

**實施內容（5 項機制）**：

| # | 機制 | 自動觸發點 | 阻斷？ | 改動 |
|---|------|-----------|--------|------|
| M1 | 自動 supersede 回寫 | post_task → sync | 否（靜默修復） | `kb_index.py` sync 逐區塊偵測 supersedes 邊 → 改 .md |
| M2 | Dynamic KB 狀態標記 | knowledge_lifecycle → write_to_dynamic | **是** | 新 validator `check_dynamic_kb_status.py` |
| L1 | ERROR 阻斷 | post_task → record_decisions | **是** | `check_decisions.py` returncode=2 → return False |
| L2 | 模糊衝突偵測 | post_task（主動）+ validate（被動）+ CLI | 否（WARN） | `kb_index.py` check-conflict + validate 2b |
| L3 | 決策 TTL | session_start + validate | 否（WARN） | meta 行 `review_by=YYYY-MM-DD` |

**檔案變更清單**：

| 檔案 | 類型 | 內容 |
|------|------|------|
| `shared/tools/kb_index.py` | 修改 | M1 `_auto_supersede_in_md()`、M2 `_parse_learning()` status 解析、L2 `check_conflict()` + CLI、L3 validate TTL 檢查、stdout 修復 |
| `shared/workflows/validators/check_decisions.py` | 修改 | L1 ERROR 阻斷 + L2 主動 conflict 掃描 + 編碼修復 |
| `shared/workflows/validators/check_knowledge_health.py` | **新增** | session_start 知識健康檢查（L3 TTL + L2 語意重疊） |
| `shared/workflows/validators/check_dynamic_kb_status.py` | **新增** | M2 learning_notes 條目 status 標記強制 |
| `shared/workflows/definitions/session_start.json` | 修改 | 新增 `check_knowledge_health` 節點 |
| `shared/workflows/definitions/knowledge_lifecycle.json` | 修改 | `write_to_dynamic` 加 validator `check_dynamic_kb_status` |
| `.claude/CLAUDE.md` | 修改 | 第 5/6/7 節更新（流程說明 + 新機制描述） |
| `shared/kb/decisions.md` | 修改 | D-110 + 4 筆 auto-supersede 修正 |

**開發過程教訓**：
- M1 初版使用全文 `re.DOTALL` 正則導致跨區塊匹配，錯誤 supersede 28 筆決策
- 修正為逐區塊 `re.split` + 區塊內 `re.sub` 後問題解決
- 教訓：**對 .md source of truth 的自動修改必須用區塊隔離，禁用 DOTALL 全文匹配**

**自動流程整合鏈**：
```
session_start → check_knowledge_health [L3+L2 報告]
post_task → record_decisions [M1 sync 修復 + L1 阻斷 + L2 衝突]
knowledge_lifecycle → write_to_dynamic [M2 status 標記強制]
```

**狀態**：✅ 全部完成

---

### 2026-02-06：v2.6 Protocol & Resilience 升級完成（Architect）

**類型**：架構升級（完成）
**觸發**：使用者要求（基於 OpenClaw 架構分析）
**評估報告**：`shared/kb/v26_architect_assessment.md`

**背景**：
- 分析了 OpenClaw 的 10 大架構模式，6 個適合採用，4 個不適合
- 訂閱制環境決定 v2.6 聚焦於架構品質（協議、Manifest、錯誤處理），不做模型路由
- 識別出 8 個瓶頸（B1-B8），v2.6 解決其中 5 個（B1/B2/B3/B5/B7）

**v2.6 版本定義：Protocol & Resilience**

| 特性 | 說明 | 來源模式 |
|------|------|---------|
| F1 Skill Manifest | .skill.yaml 機器可讀元資料 | OpenClaw #3 |
| F2 Agent Memo Protocol | Agent 間標準通訊格式 | OpenClaw #2 |
| F3 三層錯誤恢復 | Tier 1/2/3 分層處理 | OpenClaw #5 |
| F4 冪等性保護 | _operation_id + 重跑安全 | OpenClaw #10 |
| F5 Tool Registry 升級 | capabilities/constraints | OpenClaw #9 |
| F6 結構化操作日誌 | 補充式 JSONL | OpenClaw #6 |
| F7 Skill 交叉引用 | related_skills | 自有需求 |
| F8 知識生命週期 | TTL + 清理策略 | 自有需求 |

**實施記錄**：
- Phase 1 基礎協議層：✅ 完成（12 新檔案 + 3 新目錄）
  - `shared/protocols/` — README.md, agent_memo_protocol.md, error_handling.md, skill_manifest_spec.md, knowledge_lifecycle.md
  - `.claude/skills/*/.skill.yaml` — 3 個 Skill Manifest
  - `shared/kb/error_patterns.md`, `shared/kb/ops_log/`
- Phase 2 Agent 升級：✅ 完成（10 檔案修改）
  - 9 個 Agent 定義全部加入 v2.6 內容（Memo 協議 + Tier 1 錯誤處理）
  - tool_registry.md 升級為結構化格式 v2.6
- Phase 3 核心手冊 + 驗證：✅ 完成（3 檔案修改 + 1 新檔案）
  - CLAUDE.md v2.5 → v2.6
  - _index.md 更新協議區塊
  - evolution_log.md 追記
  - knowledge_lifecycle.md 新建

**狀態**：✅ 全部完成

---

### 2026-02-05：建立 reliability-testing Skill

**類型**：新 Skill 建立
**觸發**：使用者要求

**變更內容**：
從 `external/standards/` 外部知識轉化為可執行的應用規則 Skill：

**`.claude/skills/reliability-testing/`** (8 條規則)：
| 規則 | 內容 |
|------|------|
| R1 | 產品適用標準判斷（分立→Q101, IC→Q100, Cu wire→+Q006）|
| R2 | 變更測試矩陣（DA/WB/LF/MC/AST/WF 對應測試）|
| R3 | Q006 銅線加長條件（HAST 192h, HTOL 2000h）|
| R4 | MSL 濕敏等級處理（floor life, 烘烤程序）|
| R5 | 測試方法標準對照（JESD22/MIL-STD-883）|
| R6 | Grade 溫度範圍（Q100 vs Q101）|
| R7 | 高效驗證策略（Family Qual, Worst-Case）|
| R8 | 客戶通知流程（PCN 90天）|

**設計理念**：
- External 知識 = 參考資料（原文查詢）
- Skill = 應用規則（操作指引）
- 兩者互補：Skill 提供快速查詢，External 提供詳細內容

---

### 2026-02-05：國際測試標準知識庫完成

**類型**：知識擴充
**觸發**：使用者學習需求

**變更內容**：
1. **AEC-Q 汽車電子標準** (`external/standards/aec-q/`)
   - AEC-Q100 Rev J：IC 可靠性標準
   - AEC-Q101 Rev E：分立半導體標準（**公司產品適用**）
   - AEC-Q006 Rev B：銅線互連驗證（**Cu wire 必須**）
   - 變更測試矩陣：材料/製程變更對應的重新驗證測試

2. **MIL-STD 軍規標準** (`external/standards/mil-std/`)
   - MIL-STD-883 Rev L：微電子測試方法
     - Method 2019：Die Shear 晶粒剪切
     - Method 2011：Wire Bond Pull 打線拉力

3. **JEDEC 商業標準** (`external/standards/jedec/`)
   - JESD22 系列測試方法
     - A 系列：環境/壽命測試（THB, HAST, TC, HTOL, HTRB 等）
     - B 系列：機械測試（WBS, WBP 等）

4. **IPC/JEDEC 聯合標準** (`external/standards/ipc-jedec/`)
   - J-STD-020：MSL 濕敏等級分類（MSL 1~6）
   - J-STD-033：濕敏元件處理規範

**知識關係**：
```
AEC-Q101 (公司產品驗證要求)
  ├─ 引用 JESD22 (測試條件)
  ├─ 引用 MIL-STD-883 (機械測試)
  └─ 引用 J-STD-020 (前處理)
```

**統計**：
- 外部標準文件：9 個 JSON 檔案
- 涵蓋測試方法：20+ 種
- 總資料量：~3000 行知識結構

---

### 2026-02-05：自我演進機制建立

**類型**：架構升級
**觸發**：使用者要求

**變更內容**：
1. **新增 Architect Agent** (`.claude/agents/architect.md`)
   - 負責建立新 Agent
   - 負責優化架構
   - 追蹤使用模式

2. **新增 /evolve 指令** (`.claude/commands/evolve.md`)
   - 觸發自我演進審查
   - 支援標準/深度/專項審查

3. **更新權限設定** (`~/.claude/settings.json`)
   - 開放 `Bash(*)` 完整權限
   - 開放 `WebFetch(*)` 網頁抓取
   - 開放 `WebSearch(*)` 網路搜索
   - 開放 `mcp__*` 所有 MCP 操作

4. **建立演進日誌** (`shared/kb/evolution_log.md`)
   - 追蹤所有架構變更

**預期效益**：
- 系統可自主識別改進機會
- 減少重複性手動操作
- 越用越好用

---

## Agent 清單演進

| 日期 | 動作 | Agent | 說明 |
|------|------|-------|------|
| 初始 | 建立 | librarian | 文管中心 |
| 初始 | 建立 | toolsmith | 工具鍛造師 |
| 初始 | 建立 | explorer | 偵察員 |
| 初始 | 建立 | learner | 學習員 |
| 初始 | 建立 | promoter | 品管升級官 |
| 初始 | 建立 | intake | 入庫組 |
| 初始 | 建立 | analyst | 分析師 |
| 初始 | 建立 | reporter | 報告組 |
| 2026-02-05 | 建立 | **architect** | 系統架構師（自我演進） |

---

## 工具清單演進

| 日期 | 動作 | 工具 | 路徑 |
|------|------|------|------|
| 2026-02-05 | 建立 | DescParser | `shared/tools/parsers/desc_parser.py` |
| 2026-02-05 | 建立 | MaterialSearcher | `shared/tools/searchers/material_search.py` |
| 2026-02-05 | 建立 | KnowledgeStore | `shared/tools/searchers/knowledge_store.py` |

---

## 知識庫演進

| 日期 | 動作 | 知識 | 說明 |
|------|------|------|------|
| 2026-02-05 | 升級 | process-bom-semantics | R8-R11 新增/強化 |
| 2026-02-05 | 建立 | external/materials | 外部材料知識庫（銀膠 Henkel 84-1LMISR4） |
| 2026-02-05 | **完成** | external/standards/aec-q | AEC-Q100/Q101/Q006 + 變更測試矩陣 |
| 2026-02-05 | **完成** | external/standards/mil-std | MIL-STD-883 Rev L（Die Shear, Wire Pull） |
| 2026-02-05 | **完成** | external/standards/jedec | JESD22 系列（THB, HAST, TC, HTOL 等） |
| 2026-02-05 | **完成** | external/standards/ipc-jedec | J-STD-020/033（MSL 分類與處理） |
| 2026-02-05 | **🆕 新建** | reliability-testing Skill | 8 條標準應用規則（從 external 轉化） |

---

## 待處理改進

| 優先級 | 建議 | 狀態 |
|-------|------|------|
| ~~高~~ | ~~學習 AEC-Q 標準~~ | ✅ **完成** (2026-02-05) |
| ~~高~~ | ~~學習 MIL-STD/JEDEC/J-STD 測試方法~~ | ✅ **完成** (2026-02-05) |
| ~~最高~~ | ~~v2.6 升級：Protocol & Resilience~~ | ✅ **完成** (2026-02-06) |
| 中 | 建立 researcher Agent（網路搜索+知識存儲） | 待審查（可能納入 v2.7） |
| 低 | 優化 Playwright 搜索流程 | 待評估 |
| 新 | 擴充材料知識庫（封膠、腳架鍍層等） | 待規劃 |
| 新 | Learner 職責拆分 | 待 v2.6 穩定後（v2.7 候選） |

---

## 使用模式追蹤

> 此區塊記錄重複性任務模式，供 Architect 分析

### 常見任務類型
1. BOM 資料查詢與分析
2. 原物料規格搜索
3. 知識學習與存儲

### 常見操作組合
1. `WebSearch` → `WebFetch/Playwright` → `KnowledgeStore.save` （網路學習流程）
2. `SQLite 查詢` → `Analyst 分析` → `Reporter 報告` （分析報告流程）
3. `Librarian 歸檔` → `Explorer 偵察` → `Learner 學習` （新資料處理流程）

---

## 2026-04-15 — Harness Hardening Audit（第一輪）

### 背景
- 使用者明確將此辦公助手定位為「harness」：目標不是擴張 AI 自由度，而是以 workflow、證據、業務規則和事實來源限制 AI，降低飄移。
- 關鍵設計前提：在改成 hard-force 前，必須先確保系統不存在「正確完成流程卻仍無法依正規規則 close」的 false block。

### 本次架構判斷
- 現有架構可降低飄移，但尚未達到完整 harness。
- 主要原因：
  - `required_outputs` 目前偏提醒，不是 closure proof。
  - 多個 checklist 類節點只驗證「有回答」，不驗證「回答正確」。
  - `validator not found -> pass`、required node 可被 `skipped` 視為完成，屬於 fail-open。
  - `force_close` 是 AI 可直接使用的 escape hatch。

### Closure Audit 結論
- 可先硬化的客觀節點：
  - `data_ingestion.archive_original`
  - `data_ingestion.ingest_to_db`
  - `data_ingestion.generate_schema_cache`
  - `analysis_report.load_schema`
  - `analysis_report.generate_report`
  - `analysis_report.record_output_path`
- 暫不直接硬封的節點（false block 風險較高）：
  - `data_ingestion.confirm_with_user`
  - `analysis_report.cross_validate`
  - `knowledge_lifecycle.classify_knowledge`
  - `post_task.record_knowledge`
  - `post_task.update_project_state`
  - `post_task.check_memory_trigger`

### 已實施的第一輪改版
- `shared/workflows/engine.py`
  - `validator` 缺失改為 fail-closed（不再自動 pass）
  - required node terminal state 只接受 `completed`，不再接受 `skipped`
  - 新增 `enforce_required_outputs` 支援：節點可要求 `outputs` 中提交可解析的 artifact path proof
- `shared/workflows/coordinator.py`
  - `force_close` 改為需要 `--approved-by-user --reason ...`
  - 新增 `shared/workflows/state/force_close_audit.jsonl` 記錄 override
  - Stop hook 訊息改為只允許使用者顯式 override，不再作為一般逃生口提示
- `shared/workflows/definitions/data_ingestion.json`
  - `archive_original`
  - `ingest_to_db`
  - `generate_schema_cache`
  - 以上節點啟用 `enforce_required_outputs: true`
- `shared/workflows/definitions/analysis_report.json`
  - `generate_report`
  - `record_output_path`
  - 以上節點啟用 `enforce_required_outputs: true`

### 後續改版方向
- 第二輪重點不是再加封鎖，而是把主觀節點改成結構化 proof：
  - `confirm_with_user`：欄位 mapping + unresolved items + user confirmation reference
  - `cross_validate`：query refs + rule ids + contradiction list
  - `update_project_state`：section-level completeness proof，而非單看 mtime
  - `record_knowledge`：新增 KB IDs 或明確 no-new-knowledge reason
- 長期原則：
  - no proof, no complete
  - no AI-level escape hatch

---

## EVO-016（2026-04-23）DB-First 收尾 + Skills 整併 + SKILL 格式統一

### 動機
EVO-012 宣告 DB-First 但僅完成半數遷移：
- validators（`check_decisions.py` / `check_dynamic_kb_status.py`）仍直讀 .md
- `kb.py` 缺 `sync/generate-summary/generate-index/check-conflict` 四個指令，validators 必須 shell out 到 `kb_index.py`
- `kb.py add-decision` / `add-learning` 仍 dual write DB + .md

另外發現兩個相關清理項目：
- `.claude/skills/` 只剩 `_skill_template/SKILL.md` 空殼，整個目錄應廢除
- 20 個 SKILL.md frontmatter 格式漂移（有些缺 `name`、有些缺 `description`、有些有 `plm-pdf-ingestion` 的 dynamic-meta 殘留欄位）

### 變更
1. **SKILL.md 統一格式**：所有 skills-on-demand/*/SKILL.md 改為 `name + description(block scalar 3-5 行) + triggers(主題分組)`，禁用 `id/title/version/status` 等非 Claude Code 原生欄位。
2. **廢除 `.claude/skills/`**：模板移至 `.claude/skills-on-demand/_skill_template/`；`commands/status.md`、`commands/promote.md` 路徑同步更新。
3. **新增 `batch-refactor` Skill**：教 Leader 兩階段變更模式（Architect 出計畫 → general-purpose agent 照單執行）。
4. **validators 切 DB**：
   - `check_decisions.py` 改查 `kb_index.db` 的 `nodes` 表；subprocess target 從 `kb_index.py` 換成 `kb.py`
   - `check_dynamic_kb_status.py` 改查 `nodes.status` 欄位（不再解析 `<!-- status: active -->`）
   - `check_knowledge_health.py` subprocess target 換成 `kb.py`
5. **kb.py 吸收 kb_index.py 四個指令**：`sync / generate-summary / generate-index / check-conflict` 全部整合至 kb.py；`kb_index.py` 的 CLI 入口改為 deprecation shim（forward 到 kb.py）。保留 KBIndex class 給 kb.py import。
6. **停止 dual write**：`kb.py add-decision` / `add-learning` 不再 append .md；新增 `post_task.refresh_kb_exports` 非必要節點，在任務結尾統一跑 `kb.py export all`。
7. **workflow 文件更新**：`knowledge_lifecycle.json` 不再提「MUST include <!-- status: active --> marker」；SKILL.md 中 `(learning_notes.md)` 引用改為 `(kb.py read <ID>)`。

### 影響
- validators 平均節省 1-2 次 .md 全檔讀取（約 10-50KB）
- `kb.py` 成為唯一 CLI 入口，`kb_index.py` 降級為 internal library
- dual write 移除後，`kb.py add-*` 速度略升，且不再有 DB/.md 漂移風險
- SKILL.md 格式統一後，`generate-index` 掃描更準確（之前因 frontmatter 異常會漏 graph-rag / questionnaire-response 的 name）

### 相關資料
- 計畫文件：`shared/kb/memory/evo016_change_plan.md`
- 相關 decisions：TBD（執行後新增 D-NNN 紀錄此變更）
- 相關 learning：TBD

### 後續
- 觀察 3-5 次 post_task 看 `refresh_kb_exports` 節點的實際使用率，若每次都跑可考慮改 required=true
- 追蹤 `.md` 文件是否仍被手工編輯（若是，代表還有工作流程沒切過來）
- 下一階段：考慮完全移除 `kb_index.py`（把 KBIndex class 搬進 kb.py 或拆成 kb_internal.py）
  - user override allowed, but audited
