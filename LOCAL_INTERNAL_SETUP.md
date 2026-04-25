# Local Internal Assets

這份文件說明哪些 agent / skill 屬於公司內部資產，已從 git 追蹤移除，只保留在本機。
它也說明 generic engine / internal overlay 拆分後，哪些 transitional 依賴仍然存在。

原則：

- `generic`：可追蹤、可提交、可跨公司重用
- `internal`：含公司流程、內部判讀、客戶案例、公司母片/品牌規範、專案知識，不進版控

## 1. Internal Assets 清單

### Agents

以下 agent 為 `internal + local-only`，repo 不再追蹤，但 Claude runtime 仍會使用：

- `.claude/agents/questionnaire-response-drafter.md`
- `.claude/agents/report-builder.md`
- `.claude/agents/promoter.md`
- `.claude/agents/ingest-archiver.md`
- `.claude/agents/ingest-structure-detector.md`
- `.claude/agents/bom-ingest-exclusion-applier.md`
- `.claude/agents/ingest-db-writer.md`
- `.claude/agents/ingest-validator.md`

### Skills

以下 skill 為 `internal + local-only`，repo 不再追蹤，但本機保留：

- `.claude/skills-on-demand/mil-std-750/`
- `.claude/skills-on-demand/graph-rag/`
- `.claude/skills-on-demand/mes-report/`
- `.claude/skills-on-demand/questionnaire-response/`
- `.claude/skills-on-demand/bom-rules/`
- `.claude/skills-on-demand/package-code/`
- `.claude/skills-on-demand/process-bom-semantics/`
- `.claude/skills-on-demand/reliability-testing/`
- `.claude/skills-on-demand/plm-pdf-ingestion/`
- `.claude/skills-on-demand/pptx-brand-master/`

## 2. 哪些流程依賴它們

### `data_ingestion`

依賴 internal agents：

- `ingest-archiver`
- `ingest-structure-detector`
- `bom-ingest-exclusion-applier`
- `ingest-db-writer`
- `ingest-validator`

若這些檔不在本機，`data_ingestion` 雖仍有 workflow 定義，但無法實際委派到對應 agent。

現況（2026-04-24）：`ingest-archiver` / `ingest-structure-detector` / `ingest-db-writer` / `ingest-validator` 四個 agent 在本機是 `internal + local-only + candidate_future_generic`，目前正常運作。它們還不是缺失狀態，只是尚未拆分為 generic engine + internal overlay；拆分時機見 `AGENT_SKILL_GOVERNANCE.md` 的 graduation criterion。

另外 `apply_exclusions` 的 runtime 已改由 `ingest-exclusion-engine` 執行，但 embedded rules 與專案排除政策仍依賴 internal skills：

- `bom-rules`
- `package-code`
- `process-bom-semantics`

### `/promote`

依賴 internal agent：

- `promoter`

若缺少，`/promote` 會變成只有 command 規範、沒有執行主體。

### `questionnaire-response`

依賴 internal skill：

- `questionnaire-response`

以及 internal agent：

- `questionnaire-response-drafter`

若缺少，超過 20 題的批量問卷生成流程會失效。

### `analysis_report`

workflow 的 generic 產出已改由 `office-report-engine` 執行，但若實際輸出需要公司母片/品牌規範或內部報表工作方式，仍會依賴：

- `report-builder`
- `pptx-brand-master`
- `internal-reliability-practice`
- 其他 internal domain skills

### `process-analysis` / `graph-rag` / `MES`

依賴：

- `graph-rag`
- `mes-report`
- `plm-pdf-ingestion`

這些都不是 generic 能力。

## 3. 新機器 / 新 clone 時怎麼處理

repo clone 完後，generic 框架會齊，但 internal 資產不會跟著下來。

必做：

1. 從你自己的安全備份或內部私有來源恢復上述 internal agent / skill 目錄
2. 放回相同路徑
3. 跑一次：

```bash
bash shared/tools/conda-python.sh shared/tools/system_audit.py
bash shared/tools/conda-python.sh shared/tools/sync_agent_rules.py --dry-run
```

若要讓 `data_ingestion` 的 embedded rules 與本機 internal skills 對齊，再跑：

```bash
bash shared/tools/conda-python.sh shared/tools/sync_agent_rules.py --apply
```

## 4. 建議備份方式

不要只靠這個工作目錄。

至少保留一份 private backup，內容包含：

- `.claude/agents/` 中的 internal agents
- `.claude/skills-on-demand/` 中的 internal skills
- internal skills 的 `references/`
- 若未來 internal `.skill.yaml` 增加，也一併備份

## 5. 目前的設計限制

目前 repo 已改為：

- framework / generic 能力：版本控管
- internal 能力：本機保留，不追蹤

因此：

- `system_audit.py` 的「全綠」代表 **本機 runtime 一致**
- 不代表一個全新 clone 的 repo 單靠 git 就能跑出完整 office assistant

這是刻意的 tradeoff，用來避免公司內部知識被 push。

## 5.1 現在版本的殘留重評估（2026-04-24）

### 已解決

- framework 文件/模板中的 legacy skill-path、mixed placeholder、old Windows launch patterns、以及 bare repo-Python 示例已清理。
- `system_audit.py` 現在同時覆蓋治理一致性與結構漂移，當前基線為 `0 errors / 0 warnings`。
- `report-builder` / `bom-ingest-exclusion-applier` / `reliability-testing` 已完成第一輪 generic-vs-overlay / compat 分流，不再屬於活躍架構殘留。

### 真正未解

- 新 clone 仍需自行恢復 internal assets；repo 本身不提供完整 runtime。
- `data_ingestion` 的四個 local runtime agents 仍是過渡型資產，不是 generic engine。
- standards/document-derived skills 的 source-version 更新治理仍未完成。

### 可延後

- private bundle / restore script 自動化
- `kb.py` CLI 可發現性優化
- 進一步壓縮 `post_task` / `data_ingestion` 的 runtime 成本

## 6. 後續建議

之後若要讓 internal 能力更好管理，建議做：

1. 建立 private internal bundle（zip / private repo / encrypted backup）
2. 建立 `restore_internal_assets.ps1` 或類似腳本
3. 把尚未 generic 化完成的 internal 能力逐步拆成：
    - generic base
    - internal overlay

目前最值得優先收尾的 transitional 項目：

- `ingest-archiver`
- `ingest-structure-detector`
- `ingest-db-writer`
- `ingest-validator`

已完成第一輪拆分、但仍需持續防回歸的項目：

- `reliability-testing`：現為 compat shim，新引用應改用 `automotive-reliability-standards`
- `report-builder`：現為 internal overlay，generic Office 預設應走 `office-report-engine`
- `bom-ingest-exclusion-applier`：現為 internal overlay，generic exclusion 預設應走 `ingest-exclusion-engine`
