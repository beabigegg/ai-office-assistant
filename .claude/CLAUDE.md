# AI 工作助手 v3.2 — Lean & Proactive

> 半導體/製造業場景。知識驅動、主動行為、最小儀式。
> 版本歷程以 git 管理，v2.7 備份於 `.claude/CLAUDE.v2.7.backup.md`

---

## 1. 執行環境

### 1.1 系統環境（Windows）

本系統運行在 **Windows 環境**，Claude Code bash tool 底層為 **Git Bash（MSYS2）**。

### 1.2 Conda 環境

本專案使用 conda 管理 Python 依賴，定義於 `environment.yml`。

```bash
# 首次安裝
conda env create -f environment.yml
conda activate ai-office

# 新增套件後更新 environment.yml（僅更新有變動的套件）
conda env export --from-history > environment.yml   # conda 套件
pip freeze > requirements-lock.txt                  # 完整鎖定（參考用）

# 同步已有環境
conda env update -f environment.yml --prune
```

**套件管理規則**：
- 新增 pip 套件後，必須同步更新 `environment.yml` 的 `pip:` 區塊
- `environment.yml` 只列頂層依賴（不鎖版本），讓 conda solver 處理相容性
- 需要精確重現時用 `requirements-lock.txt`（gitignore 不追蹤，按需產生）

### 1.3 環境變數與機密管理

機密資訊透過 `.env` 管理，**禁止硬編碼於任何受版控檔案**。

| 檔案 | 用途 | 版控 |
|------|------|------|
| `.env.example` | 變數模板（無實際值） | 追蹤 |
| `.env` | 實際機密值 | **忽略** |
| `.mcp.json.example` | MCP 設定模板（相對路徑） | 追蹤 |
| `.mcp.json` | 本機 MCP 設定（絕對路徑） | **忽略** |
| `MASTER_API_KEY.txt` | 遺留金鑰檔 | **忽略** |

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

**委派機制**：Claude Code 根據 sub-agent 的 `description` 欄位自動匹配任務並委派。
每個 sub-agent 有獨立 project memory，跨會話累積學習。

**委派原則**：
- 領域判斷（BOM/製程/可靠性）→ Leader 直接做（有完整 Skills + Decisions + Memory）
- 大量 SQL 查詢或結果集 → 委派 query-runner（隔離 context window）
- Office 文件建立/修改（Excel/Word/PPT）→ 委派 report-builder
- 系統架構變更/大量文件掃描 → 委派 architect
- 純資料操作（入庫、小量 SQL、知識記錄）→ Leader 自己做

### 探索 Agent（按需使用）

大範圍搜索（跨多檔案、不確定位置）時用 Task tool + `subagent_type="Explore"`。
簡單搜索直接用 Glob/Grep。

---

## 3. 知識架構（雙層，全部保留）

```
.claude/skills/*/SKILL.md          ← Layer 1a：核心 Skill（Claude Code 自動發現，每次會話載入）
  穩定規則。SKILL.md + .skill.yaml + references/
  每個 SKILL.md frontmatter 含 triggers 觸發詞列表 → 自動路由匹配
  目前 4 個（自動載入）：bom-rules, process-bom-semantics, reliability-testing, package-code

.claude/skills-on-demand/*/SKILL.md  ← Layer 1b：按需 Skill（sub-agent 啟動時手動讀取，EVO-004）
  5 個（不自動載入，省 ~29KB/session）：pptx-operations, excel-operations, word-operations, mil-std-750, sqlite-operations
  report-builder agent 啟動時讀取 Office Skills，Leader 按需讀取 mil-std-750

shared/kb/dynamic/                 ← Layer 2：動態學習知識（成長中）
  column_semantics.md (43條), ecr_ecn_rules.md (24條),
  learning_notes.md, patterns/, cases/

shared/kb/external/                ← 外部標準（AEC-Q, MIL-STD, JEDEC, J-STD）
shared/kb/decisions.md             ← 決策日誌（所有使用者確認的決策）
shared/kb/memory/                  ← 中場記憶快照

shared/kb/knowledge_graph/kb_index.db  ← Layer 3：知識索引（SQLite，機器查詢用）
  由 kb_index.py sync 從 .md 自動建立，.md 是 source of truth
  提供：active 決策摘要、影響追溯、衝突偵測、跨專案引用查詢
  AI 查知識時優先用 kb_index.py（省 token），只在需要全文時才讀 .md
```

**升級路徑**：dynamic/ 知識累積驗證後 → 升級到 .claude/skills/（用 /promote 觸發審查）

---

## 4. 多專案結構

```
ROOT/
├── .claude/skills/          # 原生 Skill（自動發現）[git 追蹤]
├── .claude/agents/          # 專家定義（按需諮詢）[git 追蹤]
├── .claude/commands/        # /promote, /status, /evolve [git 追蹤]
├── .claude/agent-memory/    # Agent 個人記憶 [git 忽略]
├── .claude/settings.local.json  # 個人設定 [git 忽略]
├── shared/kb/               # 共用知識庫 [git 追蹤]
├── shared/tools/            # 共用工具腳本 [git 追蹤]
├── shared/protocols/        # 參考協議（歷史留存）[git 追蹤]
├── shared/workflows/        # Workflow 定義 [git 追蹤]
├── environment.yml          # Conda 環境定義 [git 追蹤]
├── .env.example             # 環境變數模板 [git 追蹤]
├── .env                     # 實際機密 [git 忽略]
├── .mcp.json.example        # MCP 設定模板 [git 追蹤]
├── .mcp.json                # 本機 MCP 設定 [git 忽略]
└── projects/
    └── {project-name}/
        ├── vault/originals/    # 原始檔案（唯一真相）[git 忽略]
        ├── vault/outputs/      # 報告輸出 [git 忽略]
        ├── workspace/db/       # SQLite [git 忽略]
        ├── workspace/scripts/  # 專案腳本 [git 追蹤]
        └── workspace/project_state.md  # 跨會話狀態 [git 追蹤]
```

`{P}` = 當前專案路徑（如 `projects/ecr-ecn/`）

### Git 版控分界

**原則：追蹤「框架」，忽略「資料與知識」。**

| 追蹤（框架/可移植） | 忽略（公司專屬/機密/大型） |
|---------------------|---------------------------|
| CLAUDE.md, agents/, commands/ | agent-memory/, settings.local.json |
| shared/tools/, shared/workflows/, shared/protocols/ | shared/kb/ 全部內容（decisions, dynamic, external, memory） |
| projects/_template/ | projects/*（除 _template） |
| environment.yml, .env.example, .mcp.json.example, init.py | .env, .mcp.json, MASTER_API_KEY.txt, *.db |
| .claude/skills/.gitkeep（空殼） | .claude/skills/*/（SKILL.md, .skill.yaml, references/） |

### 首次部署

```bash
git clone <repo>
conda env create -f environment.yml
conda activate ai-office
python init.py                     # 建立目錄、模板、KB 骨架
# 編輯 .env 填入 API key
# 確認 .mcp.json 路徑
python init.py --project <name>    # 建立第一個專案
```

### 建立領域 Skill

```bash
cp -r .claude/skills/_skill_template .claude/skills/<skill-name>
# 編輯 SKILL.md（規則）和 .skill.yaml（觸發詞、依賴）
```

---

## 5. 會話啟動協議

每次新會話：
1. 確認當前專案 → 設定 `{P}`
2. 讀取 `{P}/workspace/project_state.md`（恢復上下文，歷史已分離至 project_history.md）
3. 啟動 session workflow：`python shared/workflows/coordinator.py start session_start --context '{"project":"{P}"}'`
4. 按節點逐步完成（read_project_state → check_knowledge_health → diff_db → flag_questions → report_ready）
5. `load_active_context` 為 **lazy 模式**：不在啟動時讀取 active_rules_summary.md（省 ~22KB），需要時用 `kb_index.py related` 按需查詢
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

2. **記錄決策**（新決策 → `shared/kb/decisions.md`，格式 D-NNN）→
   `python shared/workflows/coordinator.py complete record_decisions`
   - **寫入方式**：`Bash(python shared/tools/kb_writer.py add-decision --id D-NNN --date YYYY-MM-DD --project X --target "..." --question "..." --decision "..." --impact "..." [--supersedes D-XXX] [--refs_skill X] [--refs_db X] [--affects X] [--review_by YYYY-MM-DD] [--source "..."])`
   - 先用 `kb_writer.py next-id` 取得下一個可用 ID
   - **禁止用 Edit tool 追加決策**（會浪費 ~27K tokens Read 全文）
   - 修改已有條目（罕見）仍用 Read + Edit
   - 可選 `review_by=YYYY-MM-DD`（L3 TTL，超過日期 validate 會 WARN）
   - validator: 檢查 D-NNN 連號 + kb_index.py validate 一致性 + L2 衝突偵測（自動對最近 5 條做 check-conflict）
   - supersedes 某條舊決策時：sync 會自動回寫舊決策 status=superseded（M1）
   - 若 validate 回傳 ERROR 級→**阻斷 post_task 流程**（L1）

3. **記錄知識**（新規則/發現 → `shared/kb/dynamic/learning_notes.md`）→
   `python shared/workflows/coordinator.py complete record_knowledge`
   - **寫入方式**：`Bash(python shared/tools/kb_writer.py add-learning --id ECR-LNN --title "..." --date YYYY-MM-DD --content "..." --confidence high|medium|low [--project X] [--related_decision D-NNN])`
   - **禁止用 Edit tool 追加學習筆記**（會浪費 ~25K tokens Read 全文）
   - 修改已有條目（罕見）仍用 Read + Edit
   - kb_writer.py 自動插入 `<!-- status: active -->` 標記（M2）

4. **評估記憶快照**（條件觸發：≥3 檔案 / DB 變更 / 產出報告 / ≥10 輪 / ≥2 決策）→
   `python shared/workflows/coordinator.py complete check_memory_trigger --outputs '{"memory_conditions_met":true|false}'`
   - 若 conditions_met=true，需先寫 `shared/kb/memory/YYYY-MM-DD.md`
   - validator: 檢查 snapshot 是否存在

5. **（選填）check_promote** — coordinator 自動計數，每 3 次提醒 /promote

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

**Stop hook 會阻止你在必要節點未完成時結束。**

---

## 7. 工作模式

### 收到新資料時
```bash
python shared/workflows/coordinator.py start data_ingestion --context '{"project":"{P}","source":"<檔名>"}'
```
流程：archive → detect_structure → confirm_with_user → apply_exclusions → ingest_to_db → post_validation
- `apply_exclusions` validator 預設 scope=current_batch，只檢查當次入庫批次無 RD-/PE- 記錄（需在 complete 時傳入 `--outputs '{"operation_id":"xxx"}'`）
- `post_validation` Leader 直接做系統化品質驗證（NULL 率、重複、值域、編碼）
- 完成後觸發 post_task workflow

### 收到知識/規則時
```bash
python shared/workflows/coordinator.py start knowledge_lifecycle --context '{"project":"{P}"}'
```
流程：classify_knowledge → write_to_dynamic（M2 validator 強制 status 標記）→ sync_knowledge_index → check_promote_threshold
- 官方文件/使用者確認 → 直接寫 .claude/skills/ 或 shared/kb/external/
- 推斷/單一案例 → 寫 shared/kb/dynamic/ → 必須含 `<!-- status: active -->` → 累積後升級

### 分析產出報告時
```bash
python shared/workflows/coordinator.py start analysis_report --context '{"project":"{P}"}'
```
流程：query_db → cross_validate → generate_report → record_output_path
- `cross_validate` Leader 直接應用領域規則（Skills + Decisions），大量查詢結果委派 query-runner
- 完成後觸發 post_task workflow

### 查知識時（取代直接讀 .md）
```
0. 特定主題（優先）：python shared/tools/kb_index.py related --target <topic> --fmt line → 相關決策摘要（最省 token）
0a. 需要全量總覽時才讀：Read shared/kb/active_rules_summary.md（22KB，不要在 session_start 時預載）
1. 特定主題：python shared/tools/kb_index.py related --target <topic> --fmt line → 相關決策摘要
2. 需要深讀：--fmt ids 取 ID → Read decisions.md 對應段落
3. 跨專案：kb_index.py impacts --skill <name> 或 --db <db:table>
4. 絕不全量讀取 decisions.md（11K+ tokens）
5. 重建摘要：python shared/tools/kb_index.py generate-summary → 更新 active_rules_summary.md
6. 重建索引：python shared/tools/kb_index.py generate-index → 更新 _index.md（自動掃描 skills/projects/tools）
   - post_task workflow 的 check_decisions validator 會自動觸發，通常不需手動執行
```

### 需要領域判斷時
```
BOM/製程/封裝/可靠性 → Leader 直接做（有完整 Skills + 119 條 Decisions + MEMORY.md）
大量 SQL 查詢結果（50+ 行）→ 委派 query-runner（結果寫檔 + 只回傳摘要）
Office 報告產出 → 委派 report-builder
純資料操作/小量 SQL → Leader 直接做
```

---

## 8. 技術約束

- **Python 環境**：conda env `ai-office`（見 `environment.yml`），新增套件後同步更新
- **Excel 讀取**：`read_only=True` + `iter_rows`
- **批次處理**：`batch_size=1000`
- **冪等性**：所有 DB 寫入操作帶 `_operation_id`，重跑時先檢查是否已執行
- **DB 追溯**：每筆記錄帶 `_source_file`, `_source_version`, `_source_row`
- **SQLite 是運算中心**：大量資料用 SQL 處理，不要塞進 context window
- **Skill 大小**：SKILL.md < 500 行，詳細放 references/
- **根目錄整潔**：禁止暫存檔散落在 ROOT/，產出歸位到 vault/outputs/ 或 workspace/
- **知識查詢**：一律用 `kb_index.py`，預設 `--fmt line`（最省 token）
- **decisions.md**：每條決策須含 `<!-- kb: ... -->` meta 行
- **機密管理**：禁止在受版控檔案中硬編碼密碼/金鑰，一律用 `.env` + `os.environ`

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
- shared/tools/ 新增共用工具
- 知識庫結構性變更（decisions.md 日常追加不需每次 commit）

**commit message 慣例**：
```
<type>: <簡述>

type = feat | fix | refactor | docs | chore | skill | agent | workflow
```

---

## 10. 遷移備註

### v2.7 → v3.0
- CLAUDE.md 從 ~600 行精簡到 ~200 行
- 移除 9 個從未實際調用的職能 Agent 定義（功能由 Leader 直接執行）→ 移至 `.claude/agents-legacy/`
- 移除冗長的 Flow 定義（A/B/C/D/E/P/X/O）→ 精簡為工作模式
- 移除 Codex 外包流程（未使用過）
- 新增 Post-Task Checklist（嵌入式主動行為）
- 原始 CLAUDE.md 備份：`.claude/CLAUDE.v2.7.backup.md`

### v3.0 → v3.1（EVO-005: Agent 架構重構）
- 砍掉 3 個「假專家」Agent → 移至 `.claude/agents-legacy/`
- 保留 2 個「真工具人」Agent + 新增 query-runner
- 核心原則轉變：Agent 的價值在「隔離」而非「懂」

### v3.1 → v3.2（可移植化）
- 納入 git 版控：追蹤框架，忽略資料與知識
- conda 環境標準化（`environment.yml`）
- 機密資訊 .env 化（API key、MCP 絕對路徑）
- Skills / KB / projects 內容全部 gitignore（公司專屬知識）
- 新增 `init.py` 初始化腳本（建目錄、模板、KB 骨架、Skill 範本）
- 新增 `.env.example`、`.mcp.json.example` 模板
- 部署流程：`git clone → conda env create → python init.py`
