# AI Office — Claude 運行規則

> 路由層：When → What command。流程引導交給 coordinator.py，規則強制交給 validator/hook，備忘查詢交給 kb.py/SKILL.md。

---

## 1. 執行環境（必要前提）

- **Shell**：Windows Git Bash (MSYS2) / Linux-macOS 原生。禁 PowerShell/cmd/chmod/iconv（pretool_guard.py 阻擋）
- **Python**：一律 conda env `ai-office`（`environment.yml`）。禁系統 Python
- **標準啟動**：Claude/Git Bash 內執行 repo Python 時，一律用 `bash shared/tools/conda-python.sh <script> ...`。這仍是 conda env `ai-office`，但避開 Windows `conda run`/CP950 亂碼
- **路徑**：bash 用 POSIX（`/d/...`）、Python 用 raw string（`r'D:\...'`）、專案內部用相對路徑
- **機密**：全走 `.env` + `os.environ`，禁硬編碼（細節見 `SETUP.md`）
- **輸出編碼**：UTF-8 無 BOM

---

## 2. 角色分工

**Leader — 直接做事，領域判斷自己來，用 Sub-agent 隔離大量輸出與工具複雜度（不是隔離「懂」）。**

- 具體的 tool / skill / agent / command / workflow 路由，不再以本檔表列維護；authority 改為 `shared/registry/capability_registry.json`
- 本檔只保留抽象分工原則：
  - 領域判斷、結論整合、知識寫回由 Leader 負責
  - 大量輸出、重查詢、專門格式處理由 sub-agent / command / workflow 分流
  - 具體該叫哪個 surface，由 capability registry、workflow definition、command 說明共同決定
  - Agent Teams 只用於需要互傳訊息或並行競爭假設的情境

委派 Briefing：給絕對路徑、具體操作、上下文；不委派理解與合成。委派 ingest-* agent 時，在 brief 中明列相關決策 ID（D-NNN），避免 agent 依賴過期嵌入知識。

---

## 3. 知識架構（DB-First）

```
shared/kb/knowledge_graph/kb_index.db   ← Source of Truth（decision/learning/rule + 語意向量）
.claude/skills-on-demand/*/SKILL.md     ← Skill 規則（按需 Read，不自動載入）
shared/kb/{dynamic,external,memory}/    ← 匯出品 / 外部標準摘要 / 會話快照
```

**鐵則**：絕不全量讀 decisions.md / learning_notes.md，一律 `kb.py` 入口。Skill 升級走 `/promote`。

---

## 4. 專案結構

`{PROJECT_ID}` = canonical project id，例如 `ecr-ecn`、`process-analysis`、`BOM資料結構分析`。
`{PROJECT_ROOT}` = `projects/<name>/` 專案根目錄。

- 啟動 workflow 時，`--context '{"project":"..."}'` 裡的 `project` **只能填 `{PROJECT_ID}`**，不可填 `projects/<name>`、`projects/`、空字串
- 只有在描述檔案路徑時才使用 `{PROJECT_ROOT}`，例如 `{PROJECT_ROOT}/workspace/project_state.md`
- 固定子目錄：`vault/originals`、`vault/outputs`、`workspace/{db,scripts,memos,project_state.md}`

- **project_state.md** 首行標注 `<!-- type: knowledge -->` 或 `<!-- type: project_management -->`
- **Block Memory**（冷熱分離）：熱資料寫 project_state.md 區塊、冷資料進 project_history.md / kb_index.db / backlog.db
- **Git 原則**：追蹤框架（`.claude/`, `shared/tools/`, `shared/workflows/`），忽略資料（`shared/kb/`, `projects/*`, `*.db`, `.env`）

---

## 5. 觸發點（Workflow / Command）

| 情境 | 啟動命令 |
|------|----------|
| 新會話開始 | `bash shared/tools/conda-python.sh shared/workflows/coordinator.py start session_start --context '{"project":"{PROJECT_ID}"}'` |
| 完成重要任務 | `bash shared/tools/conda-python.sh shared/workflows/coordinator.py start post_task --context '{"project":"{PROJECT_ID}","task":"..."}'` |
| 收到新資料（確認需入庫） | `bash shared/tools/conda-python.sh shared/workflows/coordinator.py start data_ingestion --context '{"project":"{PROJECT_ID}","source":"<file>"}'` |
| 收到新知識/規則 | `bash shared/tools/conda-python.sh shared/workflows/coordinator.py start knowledge_lifecycle --context '{"project":"{PROJECT_ID}"}'` |
| 產出分析報告 | `bash shared/tools/conda-python.sh shared/workflows/coordinator.py start analysis_report --context '{"project":"{PROJECT_ID}"}'` |
| 查知識 | `conda-python.sh shared/tools/kb.py catalog` → `search "<topic>"` → `read <ID>` |
| 查 schema | `conda-python.sh shared/tools/db_schema.py show <db_path> --compact` 或讀 `SCHEMA_{db}.md` |

**收到新資料：先判斷再入庫。** 小量（≤500 行）/活文件/格式複雜 → Leader 直接讀寫，禁止預設走 data_ingestion 或先寫解析腳本。

**具體 capability 路由 authority：** `shared/registry/capability_registry.json`
- command / skill / agent / tool 的關聯由 registry 管理
- workflow 的硬性節點與委派由 `shared/workflows/definitions/` 管理
- provider overlay 不應自行長期維護具體工具路由表

**workflow 啟動後按 coordinator 提示逐步 complete。** 每個節點的詳細 how-to 在節點 `instruction` 欄位中，workflow 啟動時自動顯示。

---

## 6. 鐵則（程式強制）

- **SQL Schema-First**：寫 SQL 前必讀 `SCHEMA_{db}.md`（`analysis_report` 的 `load_schema` 節點強制）
- **SQLite 為運算中心**：大量資料走 SQL，不塞 context window
- **禁止 `2>/dev/null` 遮蔽工具錯誤**：對 `kb.py`、`process_kb_query.py`、`graph_query.py`、`coordinator.py` 等 AI Office 工具的呼叫，禁止附加 `2>/dev/null`。這些工具的 stderr 是診斷依據，遮蔽後無法判斷失敗原因。
- **DB-First 知識**：不讀 .md 全文，一律 `kb.py read <ID>`
- **KB CLI 不猜參數**：寫 learning 前先看 `bash shared/tools/conda-python.sh shared/tools/kb.py add-learning -h`。`--confidence` 只用 `high|medium|low`；不要把內部評分尺度 `0.90` 直接當 CLI 參數。
- **檔案衛生**：暫存/散落/備份/空殼檔禁止留存（`check_hygiene` 節點掃描）
- **SOT-LD 四層**：Tier1=shared/tools/（原始解析）→ Tier2=專案共用業務邏輯 → Tier3=報告特有邏輯 → Tier4=純輸出
- **冪等 + 追溯**：DB 寫入帶 `_operation_id/_source_file/_source_version/_source_row`（ingest-* agent 內建）
- **Stop hook**：post_task required 節點未完成不得結束對話
- **Skill-First**：新需求先問「有沒有 Skill 或 `shared/tools/` 工具可完成？」。有則用，無則評估是否補建 Skill/工具。**禁止**為單次需求在 `projects/*/scripts/` 建立一次性腳本；若確實需要專案腳本，必須說明為何不可複用。
- **Architect-Only Lifecycle**：新 agent / skill 的建立、改名、拆分、整併、退休，一律先交 `architect`。只有在既有治理基線與明確觸發條件成立後，才可新增 agent/skill。
- **Tier-3 重寫三步驟**：重寫任何 `projects/*/scripts/*.py`（>100 行或替換既有邏輯）前，必須：(1) `bash shared/tools/conda-python.sh shared/tools/kb.py catalog --project {PROJECT_ID}` 取得 active decisions 清單；(2) 新檔頂端 docstring 明列將遵循的 D-NNN；(3) active 清單中未列入 (2) 的 decision，須在 docstring 明示「不適用」並說明理由。

---

## 7. 快速指令

| 指令 | 功能 |
|------|------|
| `/promote` | 掃描 dynamic KB，評估升級為 Skill |
| `/status` | 系統狀態總覽 |
| `/evolve` | 架構審查（委派 architect） |
| `/commit` | Git commit 當前變更 |

工具語法查 `--help`：`kb.py -h`、`backlog.py -h`、`db_schema.py -h`、`coordinator.py -h`。
