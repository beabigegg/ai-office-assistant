# 知識生命週期管理 v1.0

> Status: runtime authority for KB lifecycle. If this file conflicts with older notes,
> this file and `shared/kb/kb_status_spec.md` win.
> 定義 Agent Office 中知識的建立、成熟、升級、老化與清理策略。
> Learner 和 Promoter 共同遵守此協議。

---

## 知識狀態機

```
        建立             驗證 (2+次)        升級審查
[draft] ───→ [active] ─────────→ [mature] ───────→ [promoted]
                │                    │                  │
                │ 180天無引用         │ 180天無引用       │ SKILL.md 更新
                ▼                    ▼                  ▼
            [stale]              [stale]           [skills-on-demand]
                │                    │
                │ 使用者確認          │ 使用者確認
                ▼                    ▼
            [archived]           [archived]
```

## 狀態定義

| 狀態 | 位置 | 說明 |
|------|------|------|
| `draft` | `shared/kb/dynamic/` | 新建立的知識，單次觀察，未驗證 |
| `active` | `shared/kb/dynamic/` | 正在使用中，至少被引用 1 次 |
| `mature` | `shared/kb/dynamic/` | 已驗證 2+ 次，穩定度高，待升級 |
| `promoted` | `kb_index.db` / export | 已通過升級審查，知識本體保留於 KB |
| `stale` | `shared/kb/dynamic/` | 超過 180 天未被引用或驗證 |
| `archived` | `shared/kb/dynamic/archive/` | 已退役，保留供追溯 |
| `skills-on-demand` | `.claude/skills-on-demand/` | Claude Code 實際使用的 Skill 載體，不是 KB status |

## TTL（存活期限）規則

### Layer 2 知識（shared/kb/dynamic/）

| 知識類型 | 預設 TTL | 延長條件 | 過期動作 |
|---------|---------|---------|---------|
| 欄位語意（column_semantics.md）| 無限 | — | 永不過期（核心字典）|
| 資料模式（patterns/）| 180 天 | 每次引用重置計時 | 標記 stale → 詢問使用者 |
| 分析案例（cases/）| 90 天 | 每次引用重置計時 | 歸檔到 archive/ |
| 學習筆記（learning_notes.md）| 180 天 | 升級為 Skill 後移除 | 標記 stale |
| 外部知識（external/）| 365 天 | 官方文件更新版本時 | 標記版本過期 |

### Layer 1 知識（.claude/skills-on-demand/）

| 知識類型 | TTL | 更新策略 |
|---------|-----|---------|
| SKILL.md | 無限 | Promoter 或 Learner 主動更新 |
| .skill.yaml | 無限 | 和 SKILL.md 同步更新 |
| references/ | 無限 | 追加式更新 |

## Runtime Status 規格

現行系統允許的狀態以 `shared/kb/kb_status_spec.md` 為準：

- decision：`active | superseded`
- learning：`draft | active | mature | promoted | stale | archived`

`native_skill`、`obsolete`、`deprecated` 僅作為舊文件詞彙，不作為新資料寫入值。

## 清理策略

### 自動清理（Promoter 在 /promote 時執行）

1. **掃描 TTL**：檢查 `shared/kb/dynamic/` 所有知識條目的 `last_referenced` 日期
2. **標記 stale**：超過 TTL 且未被引用的 → 在 `_index.md` 標記 `[stale]`
3. **不自動刪除**：stale 知識只標記，不刪除。使用者確認後才歸檔

### 手動清理（使用者或 Architect 觸發）

1. `/promote` 時 Promoter 附帶 stale 清單
2. 使用者確認哪些可以歸檔
3. 歸檔到 `shared/kb/dynamic/archive/YYYY-MM-DD/`
4. 更新 `_index.md` 移除條目

## Skill 交叉引用

### 引用格式

在 SKILL.md 中使用 `related_skills` 標記：
```markdown
## 相關 Skills
- `process-bom-semantics`：本 Skill 的 BOM 層級規則依賴製程 BOM 的站別定義
- `reliability-testing`：材料變更觸發 AEC-Q 驗證流程
```

在 .skill.yaml 中使用 `requires.related_skills`：
```yaml
requires:
  related_skills:
    - process-bom-semantics  # BOM 層級定義
    - reliability-testing     # 變更驗證流程
```

### 交叉引用規則

1. **強引用（requires）**：被引用的 Skill 不存在時，本 Skill 功能受限
2. **弱引用（related）**：被引用的 Skill 不存在不影響本 Skill 功能
3. **Promoter 升級時**：必須檢查新 Skill 是否需要引用現有 Skill
4. **刪除/歸檔 Skill 時**：必須檢查是否有其他 Skill 強引用它

### 目前交叉引用地圖

```
bom-rules
  ├─ related: process-bom-semantics（製程細節）
  └─ related: reliability-testing（變更驗證）

process-bom-semantics
  ├─ requires: bom-rules（BOM 基礎規則）
  └─ related: reliability-testing（材料變更測試）

reliability-testing
  ├─ related: bom-rules（物料識別）
  └─ related: process-bom-semantics（製程變更影響）
```

## 品質指標

### 知識條目評分標準（Promoter 使用）

| 指標 | 權重 | 評分範圍 | 說明 |
|------|------|---------|------|
| 信心度 | 0.3 | 0.0-1.0 | 規則的確定程度（猜測 0.3 / 推斷 0.6 / 確認 0.9）|
| 驗證次數 | 0.3 | 0.0-1.0 | 被實際資料驗證的次數（1次 0.3 / 2次 0.6 / 3+次 0.9）|
| 穩定度 | 0.2 | 0.0-1.0 | 規則是否曾被修改（未改 0.5 / 微調 0.3 / 大改 0.1）|
| 來源品質 | 0.2 | 0.0-1.0 | 來源可靠度（官方文件 1.0 / 使用者確認 0.5 / 推斷 0.3）|

**升級門檻**：加權總分 >= 2.50

### 知識健康度儀表板

Promoter 在 `/promote` 時輸出：

```
知識健康度摘要：
- Layer 1 Skills：3 個（bom-rules, process-bom-semantics, reliability-testing）
- Layer 2 Active：15 條
- Layer 2 Mature：3 條（待升級候選）
- Layer 2 Stale：0 條
- 交叉引用完整性：✅ 無斷裂引用
```

## 版本同步檢查

### SKILL.md 與 .skill.yaml 同步規則

1. `version` 欄位必須一致
2. `last_updated` 欄位必須一致
3. Promoter 升級時兩者同時產出
4. 手動修改 SKILL.md 後，必須同步更新 .skill.yaml

### 同步檢查觸發

- Promoter `/promote` 時自動檢查
- Architect `/evolve` 時自動檢查
- 發現不同步 → 以 SKILL.md 為準，重新生成 .skill.yaml

---

> 本協議由 Architect 和 Promoter 共同維護。變更需記錄到 `shared/kb/evolution_log.md`。
