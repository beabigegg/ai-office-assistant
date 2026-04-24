# Skill Manifest 規範 v1.0

> 每個 `.claude/skills-on-demand/{name}/` 除了 SKILL.md 外，必須有 `.skill.yaml`。
> Manifest 提供機器可讀的元資料，讓 Leader 能自動匹配任務到 Skill。

---

## 檔案位置

```
.claude/skills-on-demand/{skill-name}/
├── SKILL.md          # 人類可讀的規則文件（按需讀取）
├── .skill.yaml       # 機器可讀的 Manifest（本規範定義）
└── references/       # 詳細參考資料
```

## 欄位定義

```yaml
# === 必填 ===
name: string              # Skill 名稱（與目錄名一致）
version: string           # 語意版本號（如 "1.2"）
category: enum            # analysis | creation | integration | automation | reference
description: string       # 一句話說明（50 字內）

# === 觸發條件（Leader 用來匹配任務）===
triggers:
  keywords: [string]      # 使用者輸入中的關鍵字匹配
  file_patterns: [string] # 涉及的檔案名模式（glob）
  data_columns: [string]  # 涉及的資料欄位名（出現在 DB 或 Excel 中）

# === 依賴 ===
requires:
  tools: [string]         # 需要的 Python 套件或工具
  knowledge: [string]     # 需要讀取的知識庫檔案路徑
  related_skills: [string] # 相關 Skill 名稱（交叉引用）

# === 約束 ===
constraints:
  must_not: [string]      # 此 Skill 絕對不能做的事

# === 品質指標 ===
rules_count: int          # 規則數量
confidence: enum          # high | medium | low
tested_scenarios: int     # 已驗證的場景數
last_updated: date        # 最後更新日期（YYYY-MM-DD）

# === 專家 Agent 關聯（v2.7 新增）===
expert_agent: string      # 對應的專家 Agent 名稱（如 "bom-process-expert"）
consult_agents: [string]  # 此專家可諮詢的其他專家（allowlist）

# === 可選 ===
promoted_from: string     # 升級前在 dynamic/ 的來源路徑
upgrade_history: [string] # 升級記錄摘要
```

## 觸發匹配邏輯

Leader 在派工前按以下順序匹配：

1. **keywords**：使用者輸入包含任一關鍵字 → 命中
2. **file_patterns**：涉及的檔案名匹配任一模式 → 命中
3. **data_columns**：涉及的資料欄位匹配任一 → 命中
4. 命中多個 Skill → 看 `related_skills` 判斷是否需要組合使用
5. 命中的 Skill 有 `expert_agent` → 優先調度該專家 Agent（Dispatch Protocol）
6. 無命中 → 退回到 CLAUDE.md 的人工派工決策表

## Promoter 職責

Promoter 升級 Skill 時必須：
1. 從 SKILL.md 的內容推斷 triggers（keywords、file_patterns、data_columns）
2. 從規則中提取 constraints（must_not）
3. 盤點 requires（工具、知識、相關 Skill）
4. 填寫品質指標（rules_count、confidence、tested_scenarios）
5. 記錄 promoted_from 和 upgrade_history

## 範例

見各 Skill 目錄下的 `.skill.yaml` 實例。
