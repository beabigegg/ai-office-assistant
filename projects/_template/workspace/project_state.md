<!-- type: knowledge -->
# {專案名稱} — 狀態快照

> 更新：{YYYY-MM-DD}｜**熱資料上限：150 行（knowledge）/ 200 行（project_management）**
> 已完成/歷史 → `project_history.md`；project_management 型的任務 → `backlog.py list`

---

## 當前階段
<!-- block: phase | max: 10 lines -->

- **Phase**：{待啟動 | 資料入庫中 | 分析中 | 報告產出中 | 已完成}
- **進行中**：{1-3 個主要活動，一行一項}

## 活躍任務
<!-- block: tasks | max: 15 lines -->

- [ ] {任務描述}（knowledge 型直接列；project_management 型用 `bash shared/tools/conda-python.sh shared/tools/backlog.py list --status open`）

## 資料庫現況
<!-- block: db_status | max: 10 lines -->

- **路徑**：`workspace/db/{db-name}.db`
- **表**：{表名} — {筆數} 筆（{YYYY-MM-DD} 更新）

## 活躍知識依賴
<!-- block: knowledge_deps | max: 5 lines -->

- Skills：{skill-name}
- 相關決策：{D-NNN}

## 未解問題
<!-- block: open_questions | max: 5 items -->

- 超過 5 條 → 轉 `backlog.py add` 或 `kb.py add-learning`

## 主要產出（當前版本）
<!-- block: outputs | max: 10 lines -->

| 檔案 | 路徑 | 說明 |
|------|------|------|
| {檔名} | vault/outputs/ | {用途} |

---
<!-- 延伸資料指針（不計入行數限制） -->
- 決策鏈：`bash shared/tools/conda-python.sh shared/tools/kb.py search "<主題>"`
- 歷史：`workspace/project_history.md`
- project_management 型任務：`bash shared/tools/conda-python.sh shared/tools/backlog.py list`
