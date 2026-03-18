# 三層錯誤恢復協議 v1.0

> 解決 Agent Office v2.5 的瓶頸 B2：錯誤處理缺乏分層策略。
> 借鑑 OpenClaw 的三層韌性架構，適配 Claude Code subagent 環境。

---

## 總覽

```
Tier 1（Agent 內部）→ Tier 2（Leader 層面）→ Tier 3（跨會話）
     自動恢復              降級/跳過              累積學習
```

---

## Tier 1：Agent 內部自動恢復

> 每個 Agent 在自身執行範圍內處理，不需要上報 Leader。

### 通用策略（所有 Agent 適用）

| 錯誤類型 | 恢復策略 | 最大重試 |
|---------|---------|---------|
| 工具/函數呼叫失敗 | 重試 2 次，間隔 2 秒 → 4 秒（指數退避）| 2 |
| 檔案編碼偵測失敗 | 依序嘗試 utf-8 → big5 → cp950 → latin1 | 4 |
| 路徑格式錯誤 | 自動轉換 Windows ↔ POSIX 格式 | 1 |
| 超時（>120 秒）| 保留已完成部分，標記 status: partial | 0 |
| JSON/YAML 解析失敗 | 嘗試修復常見問題（尾部逗號、引號不匹配）| 1 |

### Agent 專屬 Tier 1 策略

| Agent | 常見錯誤 | Tier 1 策略 |
|-------|---------|------------|
| **Librarian** | 檔案已存在（hash 相同）| 跳過（冪等），記錄到 catalog |
| **Toolsmith** | pip install 失敗 | 使用標準庫替代方案 |
| **Explorer** | Excel 讀取失敗（合併格/加密）| 改用 csv.reader 或報告為 partial |
| **Learner** | 知識衝突（新舊矛盾）| 保留兩者，標記衝突，帶入問題清單 |
| **Promoter** | 評分低於閾值 | 正常流程，記錄到「尚在觀察」 |
| **Intake** | DB 寫入失敗（型別/約束）| 回滾該批次，記錄問題列 |
| **Analyst** | SQL 語法錯誤 | 簡化查詢，移除可能有問題的條件 |
| **Reporter** | Excel 寫入失敗 | 改為 CSV + Markdown 輸出 |
| **Architect** | 檔案讀取失敗 | 跳過該檔案，基於已有資訊評估 |

---

## Tier 2：Leader 層面降級處理

> Agent 回報 status: failed 或 status: partial 時，Leader 依此表處理。

### 降級決策表

| 失敗 Agent | 降級方案 | 流程影響 |
|-----------|---------|---------|
| **Librarian 失敗** | 手動記錄到 vault/_catalog，跳過自動分類 | Explorer 可直接從 vault/ 讀取 |
| **Toolsmith 失敗** | 跳過專用工具，用通用 Python 腳本 | Explorer 用基本偵察 |
| **Explorer 失敗** | 改用 Grep/Glob 基本偵察 + head 預覽 | Learner 接收的資訊較少 |
| **Learner 失敗** | Leader 直接用已有知識繼續 | 可能遺漏新模式 |
| **Intake 失敗** | 保留 raw 表，跳過 std 表 | Analyst 可查 raw 表 |
| **Analyst 失敗** | 手動 SQL 查詢替代 | Reporter 接收手動結果 |
| **Reporter 失敗** | 改用 Markdown 純文字報告 | 使用者收到 .md 而非 .xlsx |

### Leader 通知使用者的時機

| 情況 | 通知方式 |
|------|---------|
| Agent 降級但流程繼續 | 簡短告知：「XX 遇到問題，已用備援方案繼續」 |
| Agent 失敗且無降級方案 | 暫停流程，說明問題，請使用者決定 |
| 連續 3 個 Agent 失敗 | 建議使用者檢查輸入資料品質 |

---

## Tier 3：跨會話累積學習

> 將錯誤模式記錄到持久化存儲，下次遇到同類問題可直接用降級方案。

### 記錄位置

`shared/kb/error_patterns.md` — 所有 Agent 共享

### 記錄格式

```markdown
### EP-{序號}：{錯誤摘要}

- **首次發生**：{日期}
- **發生次數**：{N}
- **Agent**：{agent name}
- **觸發條件**：{什麼情況下會觸發}
- **根因**：{已知 | 未知}
- **Tier 1 有效嗎**：{是/否}
- **建議方案**：{具體操作}
- **狀態**：{active | resolved | wontfix}
```

### Architect 定期審查

Architect 在 `/evolve` 或自動審查時：
1. 掃描 error_patterns.md
2. 發生次數 >= 3 的 active 錯誤 → 評估是否需永久修復
3. 可能的修復：請 Toolsmith 建新工具 / 修改 Agent 定義 / 更新 Skill
4. 修復後標記為 resolved

---

## 實施要點

1. **Tier 1 是靜默的** — Agent 自行處理，不打擾使用者
2. **Tier 2 要簡報** — 一句話告知使用者降級了什麼
3. **Tier 3 是長期的** — 慢慢累積，不急於修復每個錯誤
4. **不要過度重試** — 同一個操作最多重試 2 次，避免浪費 token
