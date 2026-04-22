# AI Office Assistant — Claude 運行規則

> 通用 AI 工作助手框架。知識驅動、主動行為、最小儀式。
> 此檔為 Claude 每次會話自動載入的長期規則。首次部署見 `SETUP.md`。

---

## 1. 執行環境

### 1.1 系統環境

Claude Code bash tool 底層為 **Git Bash（MSYS2）**（Windows）或原生 shell（Linux/macOS）。

### 1.2 Conda 環境

本專案使用 conda env `ai-office` 管理 **所有** Python 依賴，`environment.yml` 由 `init.py` 產生。

**執行 Python 腳本**（Claude Code bash tool 必須用 conda env 的 Python）：
```bash
# 寫腳本檔再執行（推薦，避開 conda run 的多行/編碼問題）
PYTHONUTF8=1 python script.py   # 於已 activate 的 ai-office env 中

# 或用 conda run（僅限單行指令）
conda run -n ai-office python script.py
```

**套件管理規則**：
- 新增 pip 套件 → 更新 `init.py` 中的 `_PIP_CORE` 或對應 optional group，再重跑 `python init.py`
- `environment.yml` 是產生品，不要手動編輯（會被 `init.py` 覆寫）
- **禁止用系統 Python**，一律用 conda env `ai-office`
- 詳細分組說明見 `SETUP.md`

### 1.3 環境變數與機密管理

機密資訊透過 `.env` 管理，**禁止硬編碼於任何受版控檔案**。

| 檔案 | 用途 | 版控 |
|------|------|------|
| `.env.example` | 變數模板（無實際值） | 追蹤 |
| `.env` | 實際機密值 | **忽略** |
| `.mcp.json.example` | MCP 設定模板（相對路徑） | 追蹤 |
| `.mcp.json` | 本機 MCP 設定（絕對路徑） | **忽略** |

Python 中讀取環境變數：
```python
import os
api_key = os.environ.get('MASTER_API_KEY', '')
```

### 1.4 指令規範

**優先使用 Python**：檔案操作、資料處理、路徑處理一律用 `python -c "..."` 或 Python 腳本。

**可用 bash 指令**：`cat`, `head`, `tail`, `wc`, `grep`, `find`, `cp`, `mv`, `mkdir`, `ls`, `echo`, `sort`, `uniq`

**禁止**：`powershell -Command`、`cmd /c`、`chmod`、`iconv`、PowerShell/CMD 語法

### 1.5 路徑規範

| 上下文 | 格式 | 範例 |
|--------|------|------|
| bash | POSIX | `/d/WORK/file.csv` |
| Python | raw string | `r'D:\WORK\file.csv'` |
| 專案內部 | 相對路徑 | `vault/x.xlsx` |

### 1.6 編碼

- Windows 常見 Big5/CP950/UTF-8 BOM — 讀取前用 `chardet` 偵測
- bash 終端輸出中文會亂碼 — 結果寫入 UTF-8 檔案後讀取
- 輸出一律 **UTF-8（無 BOM）**

### 1.7 遠端存取：Claude Dispatch

本系統支援透過 **Claude Desktop Cowork Dispatch** 進行遠端操作。

| 存取方式 | 適用場景 | 能力 |
|---------|---------|------|
| **Claude Code CLI**（主通道） | 深度互動開發 | 完整（多輪對話、workflow、MCP） |
| **Claude Dispatch**（遠端通道） | 遠端查詢與輕量操作 | 檔案讀寫、Python 腳本、KB 查詢 |

**Dispatch 特性**：
- 持久會話（context 不重置）
- 本機處理（檔案不離開電腦）
- 使用系統 Python（非 conda env）

**Dispatch 限制**：
- 桌面 Claude Desktop 必須保持開啟
- 無主動通知推播
- MCP COM servers 可能不可用
- 不適合需要多輪確認的 workflow（如 data_ingestion 的 confirm 節點）

---

## 2. 角色定位

**我是 Leader — 直接做事的主力，領域判斷自己來，善用工具型 Sub-agent 隔離大量輸出和工具複雜度。**

大部分工作由 Leader 直接完成（Python 腳本、SQL、領域判斷、知識記錄）。
Agent 的價值在「隔離」而非「懂」— 隔離大量輸出、隔離工具複雜度、隔離掃描範圍。

### 工具型 Sub-agent（主動委派）

| Sub-agent | 何時委派（自動觸發） | 定義檔 |
|-----------|---------------------|--------|
| **query-runner** | 大量 SQL 查詢結果需隔離 context window、批量資料摘要 | `.claude/agents/query-runner.md` |
| **report-builder** | Office 報告建立/修改（Excel/Word/PPT），MCP COM 工具操作 | `.claude/agents/report-builder.md` |
| **architect** | 系統架構升級、大量文件掃描、新建/修改 sub-agent、/evolve 觸發 | `.claude/agents/architect.md` |
| **response-drafter** | 批量 LLM API 序列呼叫（如問卷回覆，>20 項時委派） | `.claude/agents/response-drafter.md` |
| **table-reader** | PDF 複雜表格提取（合併儲存格、跨頁表格，視覺辨識） | `.claude/agents/table-reader.md` |

**委派機制**：Claude Code 根據 sub-agent 的 `description` 欄位自動匹配任務並委派。
每個 sub-agent 有獨立 project memory，跨會話累積學習。

**委派原則**：
- 領域判斷 → Leader 直接做（語意搜尋定位 → 按需 Read Skill + Decisions + Memory）
- 大量 SQL 查詢或結果集 → 委派 query-runner（隔離 context window）
- Office 文件建立/修改（Excel/Word/PPT）→ 委派 report-builder
- 系統架構變更/大量文件掃描 → 委派 architect
- 批量 LLM API 呼叫（>20 項）→ 委派 response-drafter（序列呼叫 + 節流）
- PDF 複雜表格提取（合併儲存格、跨頁）→ 委派 table-reader（視覺辨識）
- 純資料操作（入庫、小量 SQL、知識記錄）→ Leader 自己做

### 委派 Briefing 原則

委派給 Sub-agent 時，像給一個剛進辦公室的聰明同事簡報 — 它沒看過這段對話、不知道你試過什麼、不了解為什麼要做這件事：
- **含具體檔案路徑**：絕對路徑，不要相對路徑或變數
- **含具體操作**：不要「處理這個檔案」，要「讀取 X 的 A 欄位，寫入 Y.xlsx Sheet1 A1」
- **含上下文**：為什麼要做、上游已完成什麼、下游期待什麼格式
- **不要委派理解**：需要領域判斷的部分 Leader 自己做完，只把機械性操作委派出去
- **不要委派合成**：不要寫「根據你的發現來修正」，而是明確說出要改什麼

### 探索 Agent（按需使用）

大範圍搜索（跨多檔案、不確定位置）時用 Task tool + `subagent_type="Explore"`。
簡單搜索直接用 Glob/Grep。

---

## 3. 知識架構（DB-First）

```
shared/kb/knowledge_graph/kb_index.db  ← Source of Truth：知識索引 + 內容 + 語意向量（SQLite）
  統一 CLI：python shared/tools/kb.py（catalog/search/read/add/update/export/validate）
  node 類型：decision / learning / rule / column_semantic
  node_embeddings 表：Ollama embedding 向量化，支援跨語言語意搜尋
  寫入直接進 DB，.md 是匯出品（kb.py export）

.claude/skills-on-demand/*/SKILL.md  ← Skill 規則（按需讀取，不自動載入）
  SKILL.md + .skill.yaml + references/
  每個 SKILL.md frontmatter 含 triggers 觸發詞列表 → 語意搜尋命中後按需 Read
  Leader 需要領域規則時用語意搜尋定位後 Read 對應 SKILL.md

shared/kb/dynamic/                 ← .md 匯出品（由 kb.py export 產生，人類可讀備份）
shared/kb/external/                ← 外部標準摘要（原始 PDF 不入庫）
shared/kb/memory/                  ← 中場記憶快照
```

**升級路徑**：dynamic/ 知識累積驗證後 → 升級到 skills-on-demand/（用 `/promote` 觸發審查）

---

## 4. 多專案結構

`{P}` = 當前專案路徑（如 `projects/<name>/`）

每個專案遵循固定結構：`vault/originals/`（原始檔）、`vault/outputs/`（產出）、`workspace/db/`（SQLite）、`workspace/scripts/`（腳本）、`workspace/project_state.md`（狀態）。

**Git 原則**：追蹤「框架」（`.claude/`, `shared/tools/`, `shared/workflows/`, `environment.yml`），忽略「資料與知識」（`shared/kb/`, `projects/*`, `.env`, `*.db`）。

---

## 5. 會話啟動協議

每次新會話：
1. 確認當前專案 → 設定 `{P}`
2. 讀取 `{P}/workspace/project_state.md`（恢復上下文）
3. 啟動 session workflow：`python shared/workflows/coordinator.py start session_start --context '{"project":"{P}"}'`
4. 按節點逐步完成（read_project_state → check_knowledge_health → diff_db → flag_questions → report_ready）
5. `kb.py catalog` 取得知識總覽；需要深度查詢時用 `kb.py search`
6. `check_knowledge_health` 會自動報告：過期 TTL、supersede 不一致、語意重疊（不阻斷）
7. `python shared/workflows/coordinator.py complete report_ready`
8. 就緒，等待指示

---

## 6. Post-Task Checklist（Workflow 強制）

**每完成一個重要任務後，啟動 post_task workflow。Stop hook 會阻止未完成時結束對話。**

### 啟動
```bash
python shared/workflows/coordinator.py start post_task --context '{"project":"{P}","task":"<描述>"}'
```

### 逐步完成節點

1. **更新 project_state.md**（當前階段、新產出、數據變化）→ 寫入後：
   `python shared/workflows/coordinator.py complete update_project_state --outputs '{"file":"project_state.md"}'`
   - validator: 檢查 mtime < 5 分鐘

2. **記錄決策**（新決策，格式 D-NNN）→
   `python shared/workflows/coordinator.py complete record_decisions`
   - **寫入方式**：`Bash(python shared/tools/kb.py add-decision --id D-NNN --date YYYY-MM-DD --project X --target "..." --question "..." --decision "..." --impact "..." [--supersedes D-XXX] [--refs_skill X] [--refs_db X] [--affects X] [--review_by YYYY-MM-DD] [--source "..."])`
   - 先用 `kb.py next-id` 取得下一個可用 ID
   - kb.py 同時寫入 DB（source of truth）和 .md（匯出品）
   - 修改已有條目：`kb.py update D-NNN --status superseded`
   - 可選 `review_by=YYYY-MM-DD`（TTL，過期 validate 會 WARN）
   - supersedes 時 kb.py 自動標記舊決策為 superseded
   - validator: 檢查 D-NNN 連號 + 一致性 + 衝突偵測
   - 若 validate 回傳 ERROR 級 → **阻斷 post_task 流程**

3. **記錄知識**（新規則/發現）→
   `python shared/workflows/coordinator.py complete record_knowledge`
   - **寫入方式**：`Bash(python shared/tools/kb.py add-learning --id <prefix>-LNN --title "..." --date YYYY-MM-DD --content "..." --confidence high|medium|low [--project X] [--related_decision D-NNN])`
   - kb.py 同時寫入 DB + .md

4. **評估記憶快照**（條件觸發：≥3 檔案 / DB 變更 / 產出報告 / ≥10 輪 / ≥2 決策）→
   `python shared/workflows/coordinator.py complete check_memory_trigger --outputs '{"memory_conditions_met":true|false}'`
   - 若 conditions_met=true，需先寫 `shared/kb/memory/YYYY-MM-DD.md`
   - validator: 檢查 snapshot 是否存在

5. **（選填）check_promote** — coordinator 自動計數，每 3 次提醒 `/promote`

### 條件觸發（在 update_project_state 中一併處理）

- 入庫新資料 → 更新 project_state.md 資料庫現況區塊
- 新欄位含義 → 追加 `shared/kb/dynamic/column_semantics.md`
- 可重用腳本 → 存入 `{P}/workspace/scripts/` 或 `shared/tools/`
- 產出報告 → 確認路徑記錄在 project_state.md
- DB schema 變更 → 記錄在 project_state.md

### 查看狀態
```bash
python shared/workflows/coordinator.py status
python shared/workflows/coordinator.py check_pending
```

### 腳本注入（選用：--script）
`start` 與 `complete` 命令均支援 `--script <path>`：執行前跑 Python 腳本，stdout 存入 state 並於訊息中預覽，供後續節點引用。
```bash
python shared/workflows/coordinator.py start data_ingestion \
  --context '{"project":"<name>","source":"new.xlsx"}' \
  --script projects/<name>/workspace/scripts/sanity_check.py
```
- 腳本失敗不阻斷 workflow（只記錄 warning 並附 `[SCRIPT WARN]` 提示）
- stdout 以 UTF-8 捕獲、限 64 KB；訊息預覽前 20 行
- 適用場景：入庫前 diff 摘要、分析前資料覆蓋檢查、完成節點前跑 quick sanity

**Stop hook 會阻止你在必要節點未完成時結束。**

---

## 7. 工作模式

### 收到新資料時
```bash
python shared/workflows/coordinator.py start data_ingestion --context '{"project":"{P}","source":"<檔名>"}'
```
流程：archive → detect_structure → confirm_with_user → apply_exclusions → ingest_to_db → post_validation
- `apply_exclusions` validator 預設 scope=current_batch，只檢查當次入庫批次（需在 complete 時傳入 `--outputs '{"operation_id":"xxx"}'`）
- `post_validation` Leader 直接做系統化品質驗證（NULL 率、重複、值域、編碼）
- 完成後觸發 post_task workflow

### 收到知識/規則時
```bash
python shared/workflows/coordinator.py start knowledge_lifecycle --context '{"project":"{P}"}'
```
流程：classify_knowledge → write_to_dynamic（validator 強制 status 標記）→ sync_knowledge_index → check_promote_threshold
- 官方文件/使用者確認 → 直接寫 `.claude/skills-on-demand/` 或 `shared/kb/external/`
- 推斷/單一案例 → 寫 `shared/kb/dynamic/` → 必須含 `<!-- status: active -->` → 累積後升級

### 分析產出報告時
```bash
python shared/workflows/coordinator.py start analysis_report --context '{"project":"{P}"}'
```
流程：query_db → cross_validate → generate_report → record_output_path
- `cross_validate` 有 checklist validator：先讀 YAML 驗證清單 → 逐條檢查 → 回報 checklist_responses
- 大量查詢結果委派 query-runner
- 完成後觸發 post_task workflow

### 查知識時（DB 優先，kb.py 統一入口）
```
0. 啟動總覽：python shared/tools/kb.py catalog（輕量 token 消耗）
1. 語意搜尋（主力）：python shared/tools/kb.py search "<topic>" --top 10
   → 跨語言語意匹配（Ollama embedding），離線自動 fallback keyword
   → 結果附帶關聯 Skill 標籤 [→ SKILL:name]
2. keyword 搜尋（備用）：python shared/tools/kb.py search "<topic>" --keyword
3. 深讀單條：python shared/tools/kb.py read D-042
4. 批量深讀：python shared/tools/kb.py read D-042 D-043 D-044
5. 追蹤關聯：python shared/tools/kb.py trace D-042（顯示 edges 圖）
6. 影響分析：python shared/tools/kb.py impacts --skill <name> 或 --project <name>
7. 需要 Skill 規則：搜尋結果的 [→ SKILL:name] 提示後 → Read 對應 SKILL.md
   → 深度細節在 references/ 子目錄，不要預載
8. 一致性檢查：python shared/tools/kb.py validate
9. 知識圖更新：python shared/tools/kb.py build-edges（新增 Decision/Skill 後執行）
10. 歷史會話快照搜尋（FTS5）：
    - 匯入：python shared/tools/kb.py import-snapshot        # 批次匯入 shared/kb/memory/*.md（冪等）
    - 搜尋：python shared/tools/kb.py search "<topic>" --include-snapshots
    - 深讀：python shared/tools/kb.py read 2026-04-20        # 裸日期 ID 或 SNAP:<id>
11. 排程健康檢查（SILENT 慣例）：python shared/tools/scheduled_check.py
    → 健康 → 單行 `[SILENT] kb health OK at ...`（exit 0）；有異常才完整輸出
    → `--force` 強制列印；`--catalog-on-clean` 在 SILENT 行附上 catalog 摘要
    → 適合 cron / 開機 / 會話啟動前跑；有輸出即為訊號
```
**鐵則**：絕不全量讀取 decisions.md / learning_notes.md — 用 `kb.py read <ID>` 取單條

---

## 8. 技術約束

- **Python 環境**：conda env `ai-office`（見 `environment.yml`），新增套件後同步更新
- **Excel 讀取**：`read_only=True` + `iter_rows`
- **批次處理**：`batch_size=1000`
- **冪等性**：所有 DB 寫入操作帶 `_operation_id`，重跑時先檢查是否已執行
- **DB 追溯**：每筆記錄帶 `_source_file`, `_source_version`, `_source_row`
- **SQLite 是運算中心**：大量資料用 SQL 處理，不要塞進 context window
- **SQL Schema-First（鐵則）**：寫 SQL 前必須讀 `{P}/workspace/db/SCHEMA_{db}.md` 確認 table/column 名稱，不得從記憶推斷 schema。SCHEMA 不存在時用 `python shared/tools/db_schema.py show <db_path> --compact`。data_ingestion 後自動重新生成。
- **Skill 大小**：SKILL.md < 500 行，詳細放 references/
- **檔案衛生（零散落原則）**：
  - **暫存檔必須用完即刪**：`_tmp_*`, `tmp_*`, `test_output*` 等中間產物，任務結束前清除
  - **產出歸位**：報告 → `vault/outputs/`，中間資料 → `workspace/memos/`，腳本 → `workspace/scripts/`
  - **禁止在以下位置留檔**：ROOT/、專案根目錄（`projects/X/` 直接下）、`shared/` 根目錄
  - **一次性評估文件**（架構評估、方案比較）→ 結論寫入 decisions.md 後刪除原文，不要囤積
  - **空殼檔案**（初始建立但從未使用）→ 發現即刪，不保留佔位
  - **備份檔**（`*.backup.*`, `_backup/`）→ git 是唯一備份機制，禁止手動備份檔
  - **.gitkeep 目錄**：只在確定會使用的目錄保留，空置超過 30 天的刪除
  - **Playwright/MCP 殘留**（console log、screenshot、下載檔）→ 用完即搬到對應專案或刪除
- **知識庫 DB-First**：`kb_index.db` 是 source of truth，.md 是匯出品
  - **統一 CLI：`kb.py`**（catalog/search/read/trace/impacts/add/update/export/validate/build-edges）
- **Checklist 機制**：非確定性的審核/確認節點由 `check_checklist` validator 強制
  - Checklist 定義在 `shared/workflows/checklists/{workflow}__{node}.yaml`
  - AI 必須在 `complete()` 的 outputs 中提交 `checklist_responses`
  - 使用者回饋新增項目 → AI 用 Edit tool 更新 YAML → 下次自動生效
- **機密管理**：禁止在受版控檔案中硬編碼密碼/金鑰，一律用 `.env` + `os.environ`
- **單一事實來源 + 分層引用（SOT-LD 原則）**：所有資料流與邏輯必須遵循下列四層，只能向下引用，不得橫向複製同層邏輯：

  ```
  Tier 1 — shared/tools/（跨專案共用）
    原始資料唯一入口 + 共用解析函式
    規則：任何腳本不得自行解析原始資料，必須呼叫 Tier 1 函式

  Tier 2 — {P}/workspace/scripts/（專案內共用）
    業務邏輯工具：基於 Tier 1 事實做業務轉換，不直接處理原始格式
    規則：同一專案的多支腳本共用此層，不各自複製邏輯

  Tier 3 — {P}/workspace/scripts/（各報告腳本）
    基於 Tier 2 已解析的事實做進一步篩選/聚合
    只含「本報告特有」的邏輯，通用部分必須在 Tier 2

  Tier 4 — vault/outputs/（報告輸出）
    純呈現層，不含業務邏輯
  ```

  **違反警示**：
  - 新腳本寫了解析函式 → 先查 Tier 1/2 是否已有
  - 兩支腳本有相同函式名稱 → 應提升至上一層
  - 中間衍生表被當作事實來源 → 改查原始事實表 + Tier 1 函式

  **工具依賴查詢**：`cat shared/tools/TOOL_LINEAGE.md` 或 `kb.py search "tool lineage"`

---

## 9. 快速指令

| 指令 | 功能 |
|------|------|
| `/promote` | 掃描 dynamic KB → 評估哪些知識可升級為 Skill |
| `/status` | 系統狀態總覽（專案、知識、工具） |
| `/evolve` | 架構審查（識別改進機會） |
| `/commit` | Git commit 當前變更 |

### Git 工作流

架構更新、Skill 變更、workflow 修改等結構性變更應以 git commit 記錄。

**commit 時機**（由使用者觸發或 post_task 提醒）：
- 新增/修改 Skill 或 Agent 定義
- workflow 或 validator 變更
- CLAUDE.md 結構更新
- `shared/tools/` 新增共用工具
- 知識庫結構性變更（decisions.md 日常追加不需每次 commit）

**commit message 慣例**：
```
<type>: <簡述>

type = feat | fix | refactor | docs | chore | skill | agent | workflow
```
