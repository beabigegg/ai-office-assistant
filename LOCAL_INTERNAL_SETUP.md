# Local Internal Assets

這份文件說明哪些 agent / skill 屬於公司內部資產，已從 git 追蹤移除，只保留在本機。

原則：

- `generic`：可追蹤、可提交、可跨公司重用
- `internal`：含公司流程、內部判讀、客戶案例、公司模板、專案知識，不進版控

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
- `.claude/skills-on-demand/pptx-template/`

## 2. 哪些流程依賴它們

### `data_ingestion`

依賴 internal agents：

- `ingest-archiver`
- `ingest-structure-detector`
- `bom-ingest-exclusion-applier`
- `ingest-db-writer`
- `ingest-validator`

若這些檔不在本機，`data_ingestion` 雖仍有 workflow 定義，但無法實際委派到對應 agent。

另外 `apply_exclusions` 的 embedded rules 依賴 internal skills：

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

workflow 本身仍可跑，但若實際輸出需要公司模板或內部報表工作方式，會依賴：

- `report-builder`
- `pptx-template`
- `reliability-testing`
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
python shared/tools/system_audit.py
python shared/tools/sync_agent_rules.py --dry-run
```

若要讓 `data_ingestion` 的 embedded rules 與本機 internal skills 對齊，再跑：

```bash
python shared/tools/sync_agent_rules.py --apply
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

## 6. 後續建議

之後若要讓 internal 能力更好管理，建議做：

1. 建立 private internal bundle（zip / private repo / encrypted backup）
2. 建立 `restore_internal_assets.ps1` 或類似腳本
3. 把混合型 skill 逐步拆成：
   - generic base
   - internal overlay

目前最值得優先拆的：

- `reliability-testing`
- `report-builder`
- `bom-ingest-exclusion-applier`
