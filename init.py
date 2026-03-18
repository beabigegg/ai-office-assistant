#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI Office Assistant — 初始化腳本

首次 clone 後執行，建立所有必要的目錄結構、模板檔案與知識庫骨架。
已存在的檔案不會被覆蓋。

使用方式：
    conda activate ai-office
    python init.py [--project <name>]   # --project 可選，建立一個新專案
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


# ============================================================
# 1. 目錄結構定義
# ============================================================

DIRS = [
    # 知識庫
    "shared/kb/dynamic/cases",
    "shared/kb/dynamic/patterns",
    "shared/kb/external/standards",
    "shared/kb/external/materials",
    "shared/kb/memory",
    "shared/kb/knowledge_graph",
    "shared/kb/ops_log",

    # Skills（空殼，由使用者/Claude 填入領域知識）
    ".claude/skills",
    ".claude/skills-on-demand",
    ".claude/agent-memory",

    # 專案範本
    "projects/_template/vault/originals",
    "projects/_template/vault/outputs",
    "projects/_template/workspace/db",
    "projects/_template/workspace/memos",
    "projects/_template/workspace/scripts/_deprecated",
]


# ============================================================
# 2. 模板檔案定義（路徑 → 內容）
# ============================================================

TEMPLATES = {}

# --- .env ---
TEMPLATES[".env"] = """\
# AI Office Assistant - Local Environment (DO NOT COMMIT)
# 從 .env.example 複製後填入實際值

# MASTER_API_KEY=
"""

# --- .mcp.json ---
TEMPLATES[".mcp.json"] = """\
{
  "mcpServers": {
    "pptx": {
      "command": "python",
      "args": ["__ROOT__/shared/tools/mcp_pptx_server.py"]
    },
    "xlsx": {
      "command": "python",
      "args": ["__ROOT__/shared/tools/mcp_xlsx_server.py"]
    },
    "docx": {
      "command": "python",
      "args": ["__ROOT__/shared/tools/mcp_docx_server.py"]
    }
  }
}
"""

# --- shared/kb 骨架 ---
TEMPLATES["shared/kb/decisions.md"] = """\
# 決策日誌

> 所有使用者確認的決策記錄。格式：D-NNN
> 由 kb_writer.py add-decision 寫入，禁止手動 Edit 追加。

<!-- 初始化時建立，尚無決策 -->
"""

TEMPLATES["shared/kb/active_rules_summary.md"] = """\
# Active Rules Summary

> 由 kb_index.py generate-summary 自動產生。
> 不要手動編輯此檔案。

<!-- 初始化時建立，尚無摘要 -->
"""

TEMPLATES["shared/kb/_index.md"] = """\
# 知識庫索引

> 由 kb_index.py generate-index 自動產生。

<!-- 初始化時建立 -->
"""

TEMPLATES["shared/kb/evolution_log.md"] = """\
# 架構演進日誌

> 記錄系統架構變更（workflow/validator/agent/hook/CLAUDE.md）。
> decisions.md 放精簡摘要，此處放詳細內容。

<!-- 初始化時建立 -->
"""

TEMPLATES["shared/kb/dynamic/learning_notes.md"] = """\
# 學習筆記

> 由 kb_writer.py add-learning 寫入。
> 每條必須含 <!-- status: active --> 標記。

<!-- 初始化時建立 -->
"""

TEMPLATES["shared/kb/dynamic/column_semantics.md"] = """\
# 欄位語意定義

> 記錄資料庫欄位的業務含義、值域、注意事項。

<!-- 初始化時建立 -->
"""

TEMPLATES["shared/kb/dynamic/ecr_ecn_rules.md"] = """\
# ECR/ECN 規則

> 工程變更相關的業務規則與學習記錄。

<!-- 初始化時建立 -->
"""

TEMPLATES["shared/kb/external/README.md"] = """\
# 外部標準

存放外部標準文件的結構化摘要（AEC-Q, MIL-STD, JEDEC 等）。
原始 PDF 不入庫，僅存結構化 JSON/MD 摘要。
"""

TEMPLATES["shared/kb/memory/README.md"] = """\
# 中場記憶快照

格式：YYYY-MM-DD.md
觸發條件：≥3 檔案 / DB 變更 / 產出報告 / ≥10 輪對話 / ≥2 決策
"""

TEMPLATES["shared/kb/ops_log/README.md"] = """\
# 操作日誌

記錄資料入庫、批次操作等操作紀錄。
"""

TEMPLATES["shared/kb/knowledge_graph/kb_schema.sql"] = """\
-- Knowledge Graph Index Schema
-- 由 kb_index.py sync 自動建立，此處為參考

CREATE TABLE IF NOT EXISTS decisions (
    id TEXT PRIMARY KEY,          -- D-001, D-002, ...
    date TEXT,
    project TEXT,
    target TEXT,
    question TEXT,
    decision TEXT,
    impact TEXT,
    status TEXT DEFAULT 'active', -- active | superseded | deprecated
    supersedes TEXT,              -- D-XXX
    refs_skill TEXT,
    refs_db TEXT,
    affects TEXT,
    review_by TEXT,               -- YYYY-MM-DD (TTL)
    source TEXT
);

CREATE TABLE IF NOT EXISTS learnings (
    id TEXT PRIMARY KEY,          -- ECR-L01, ECR-L02, ...
    title TEXT,
    date TEXT,
    content TEXT,
    confidence TEXT,              -- high | medium | low
    project TEXT,
    related_decision TEXT,
    status TEXT DEFAULT 'active'
);
"""

# --- Skill 範本 ---
TEMPLATES[".claude/skills/_skill_template/.skill.yaml"] = """\
name: my-skill-name
version: "1.0"
category: analysis          # analysis | testing | coding | reporting
description: "一句話描述此 Skill 的用途"

triggers:
  keywords:
    - "關鍵詞1"
    - "關鍵詞2"
  file_patterns:
    - "*pattern*"
  data_columns: []

requires:
  tools:
    - sqlite3
  knowledge:
    - shared/kb/dynamic/column_semantics.md
  related_skills: []

constraints:
  must_not:
    - "修改原始檔案"
    - "刪除 vault 資料"

rules_count: 0
confidence: low
tested_scenarios: 0
last_updated: "YYYY-MM-DD"
"""

TEMPLATES[".claude/skills/_skill_template/SKILL.md"] = """\
---
name: my-skill-name
description: 一句話描述
triggers:
  - 關鍵詞1
  - 關鍵詞2
---

# Skill: my-skill-name

## 規則

### R1: 規則名稱
**描述**：...
**範例**：...

## 參考
- 詳見 references/ 目錄
"""


# ============================================================
# 3. 初始化邏輯
# ============================================================

def create_dirs():
    """建立所有必要目錄。"""
    created = []
    for d in DIRS:
        path = ROOT / d
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created.append(d)
    return created


def create_templates():
    """建立模板檔案（不覆蓋已存在的）。"""
    created = []
    skipped = []
    for rel_path, content in TEMPLATES.items():
        path = ROOT / rel_path
        # .mcp.json 需要替換路徑佔位符
        if rel_path == ".mcp.json":
            content = content.replace("__ROOT__", str(ROOT).replace("\\", "/"))

        # 確保父目錄存在
        path.parent.mkdir(parents=True, exist_ok=True)

        if path.exists():
            skipped.append(rel_path)
        else:
            path.write_text(content, encoding="utf-8")
            created.append(rel_path)
    return created, skipped


def create_project(name: str):
    """從 _template 建立新專案。"""
    template_dir = ROOT / "projects" / "_template"
    target_dir = ROOT / "projects" / name

    if target_dir.exists():
        print(f"  [SKIP] projects/{name}/ 已存在")
        return False

    if not template_dir.exists():
        print(f"  [ERROR] projects/_template/ 不存在")
        return False

    shutil.copytree(template_dir, target_dir)
    # 更新 project.md
    project_md = target_dir / "project.md"
    if project_md.exists():
        text = project_md.read_text(encoding="utf-8")
        text = text.replace("{project-name}", name)
        project_md.write_text(text, encoding="utf-8")

    print(f"  [OK] projects/{name}/ 已從範本建立")
    return True


def init_kb_index():
    """初始化 kb_index.db（如果 kb_index.py 存在）。"""
    kb_index_script = ROOT / "shared" / "tools" / "kb_index.py"
    db_path = ROOT / "shared" / "kb" / "knowledge_graph" / "kb_index.db"

    if db_path.exists():
        print("  [SKIP] kb_index.db 已存在")
        return

    if kb_index_script.exists():
        schema_path = ROOT / "shared" / "kb" / "knowledge_graph" / "kb_schema.sql"
        if schema_path.exists():
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            conn.executescript(schema_path.read_text(encoding="utf-8"))
            conn.close()
            print("  [OK] kb_index.db 已初始化")
        else:
            print("  [WARN] kb_schema.sql 不存在，跳過 DB 初始化")
    else:
        print("  [WARN] kb_index.py 不存在，跳過 DB 初始化")


def check_conda_env():
    """檢查是否在正確的 conda 環境中。"""
    conda_env = os.environ.get("CONDA_DEFAULT_ENV", "")
    if conda_env == "ai-office":
        print("  [OK] conda env: ai-office")
        return True
    elif conda_env:
        print(f"  [WARN] 目前在 conda env '{conda_env}'，建議切換到 'ai-office'")
        return False
    else:
        print("  [WARN] 未偵測到 conda 環境，建議執行: conda env create -f environment.yml")
        return False


def check_env_file():
    """檢查 .env 是否已設定。"""
    env_path = ROOT / ".env"
    if not env_path.exists():
        print("  [WARN] .env 不存在（已從模板建立空檔）")
        return False

    text = env_path.read_text(encoding="utf-8")
    if "MASTER_API_KEY=" in text and not text.split("MASTER_API_KEY=")[1].strip().startswith("#"):
        api_val = text.split("MASTER_API_KEY=")[1].split("\n")[0].strip()
        if api_val and api_val != "your_api_key_here":
            print("  [OK] .env MASTER_API_KEY 已設定")
            return True

    print("  [WARN] .env 中 MASTER_API_KEY 尚未填入")
    return False


# ============================================================
# 4. Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="AI Office Assistant 初始化")
    parser.add_argument("--project", "-p", help="同時建立一個新專案")
    args = parser.parse_args()

    print("=" * 50)
    print("AI Office Assistant — 初始化")
    print("=" * 50)

    # Step 1: 環境檢查
    print("\n[1/5] 環境檢查")
    check_conda_env()

    # Step 2: 建立目錄
    print("\n[2/5] 建立目錄結構")
    created_dirs = create_dirs()
    if created_dirs:
        for d in created_dirs:
            print(f"  [OK] {d}/")
    else:
        print("  [SKIP] 所有目錄已存在")

    # Step 3: 建立模板檔案
    print("\n[3/5] 建立模板檔案")
    created_files, skipped_files = create_templates()
    if created_files:
        for f in created_files:
            print(f"  [OK] {f}")
    if skipped_files:
        print(f"  [SKIP] {len(skipped_files)} 個檔案已存在")

    # Step 4: 初始化 KB 索引
    print("\n[4/5] 初始化知識庫索引")
    init_kb_index()

    # Step 5: 環境變數檢查
    print("\n[5/5] 環境變數檢查")
    check_env_file()

    # 可選：建立新專案
    if args.project:
        print(f"\n[+] 建立專案: {args.project}")
        create_project(args.project)

    # 完成摘要
    print("\n" + "=" * 50)
    print("初始化完成！")
    print()
    print("下一步：")
    print("  1. 編輯 .env 填入 API key")
    print("  2. 確認 .mcp.json 路徑正確")
    print("  3. 建立領域 Skill：")
    print("     cp -r .claude/skills/_skill_template .claude/skills/<your-skill>")
    print("     編輯 SKILL.md 和 .skill.yaml")
    print("  4. 建立新專案：")
    print("     python init.py --project <name>")
    print("=" * 50)


if __name__ == "__main__":
    main()
