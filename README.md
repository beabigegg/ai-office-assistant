# AI Office Assistant

通用 AI 工作助手框架。基於 Claude Code，提供知識驅動的多專案工作流程管理。

## 功能特色

- **多專案管理**：標準化的專案結構（vault / workspace / scripts）
- **知識架構**：DB-first 知識圖譜（SQLite + Embedding 語意檢索）+ 按需載入 Skill
- **Workflow 引擎**：資料入庫、分析報告、知識生命週期、Post-Task Checklist
- **Office 文件建立**：Code-based 首選（openpyxl / docx-js / pptxgenjs），MCP COM 編輯已有檔案
- **Sub-agent 委派**：report-builder、query-runner、architect、table-reader、response-drafter 及 ingest-* 系列
- **MCP 伺服器**：Excel / Word / PowerPoint COM 自動化（Windows，編輯已有檔案）
- **PDF 處理**：pypdf / pdfplumber / reportlab（文字提取、合併、新建）

## 快速開始

詳細步驟見 [`SETUP.md`](SETUP.md)。

```bash
git clone <repo-url>
cd <repo>
python init.py                    # 預設只裝 core 套件
conda env create -f environment.yml
conda activate ai-office
cp .env.example .env              # 填入金鑰
python init.py --project <name>   # 建立第一個專案
```

啟用特定領域套件群組：

```bash
python init.py --with ocr --with ml --with ai-runtime-gpu
conda env update -f environment.yml --prune
```

## 存取方式

| 通道 | 適用場景 | 能力範圍 |
|------|---------|---------|
| **Claude Code CLI** | 深度互動開發 | 完整（多輪對話、workflow、MCP、sub-agent） |
| **Claude Dispatch** | 遠端操作 | 檔案讀寫、Python 腳本、KB 查詢（持久會話） |

## 專案結構

```
├── .claude/
│   ├── CLAUDE.md              # Claude 運行規則（每次會話自動載入）
│   ├── agents/                # Sub-agent 定義（git 追蹤）
│   ├── commands/              # 快速指令
│   ├── skills/                # 領域 Skill（gitignore，由使用者建立）
│   │   └── _skill_template/
│   └── skills-on-demand/      # 按需載入 Skill（SKILL.md 納入 git 追蹤）
│       ├── docx-authoring/    # Word 新建（docx-js）
│       ├── docx-operations/   # Word 編輯已有（MCP COM）
│       ├── xlsx-authoring/    # Excel 新建（openpyxl + recalc.py）
│       ├── excel-operations/  # Excel 編輯已有（MCP COM）
│       ├── pptx-authoring/    # PPT 新建（pptxgenjs / unpack-edit-pack）
│       ├── pptx-template/     # PPT 公司模板（pptx_panjit）
│       ├── marp-pptx/         # PPT 快速/PDF（Marp）
│       ├── pptx-operations/   # PPT 精修已有（MCP COM）
│       ├── pdf/               # PDF 操作（pypdf / reportlab）
│       └── skill-creator/     # 建立/評測新 Skill（eval loop）
├── shared/
│   ├── kb/                    # 知識庫（gitignore，由 init.py 建立骨架）
│   ├── tools/                 # 共用工具腳本（git 追蹤）
│   │   ├── office/            # soffice.py / pack.py / unpack.py（共用）
│   │   ├── pptx/              # thumbnail.py / add_slide.py / clean.py
│   │   ├── docx/              # accept_changes.py / comment.py
│   │   ├── pdf/               # PDF 表單處理腳本
│   │   └── recalc.py          # Excel 公式重算（LibreOffice）
│   ├── workflows/             # Workflow 定義 + Coordinator + Validators
│   └── protocols/             # 參考協議
├── projects/
│   └── _template/             # 專案範本
├── skill-creator/             # Skill 評測基礎設施（eval-viewer / scripts）
├── environment.yml            # Conda 環境定義（由 init.py 產生）
├── init.py                    # 初始化腳本（平台感知 + 套件分組）
├── SETUP.md                   # 首次部署指引
├── .env.example               # 環境變數模板
└── .mcp.json.example          # MCP 設定模板
```

## Sub-agent 清單

| Agent | 功能 |
|-------|------|
| `report-builder` | Office 文件建立/修改（Excel / Word / PPT / PDF） |
| `query-runner` | SQL 查詢執行（大量結果隔離） |
| `architect` | 架構審查、系統演化（/evolve） |
| `table-reader` | PDF 複雜表格視覺提取 |
| `response-drafter` | 批量 LLM API 呼叫（>20 項問卷） |
| `ingest-archiver` | 資料入庫：封存原始檔 |
| `ingest-structure-detector` | 資料入庫：偵測欄位結構 |
| `ingest-exclusion-applier` | 資料入庫：套用排除規則 |
| `ingest-db-writer` | 資料入庫：寫入 SQLite |
| `ingest-validator` | 資料入庫：後驗品質檢查 |

## Office 文件建立策略

| 任務 | 首選（穩定）| 備選 |
|------|-----------|------|
| Excel 新建 | openpyxl + recalc.py | MCP COM |
| Word 新建 | docx-js（Node.js） | MCP COM |
| PPT 新建（自由設計） | pptxgenjs（Node.js） | pptx-template |
| PPT 新建（公司模板） | pptx_panjit（Python） | — |
| PPT 快速/PDF | Marp | — |
| 任何格式**編輯已有** | MCP COM | unpack/edit/pack |

## 跨平台支援

| 元件 | Windows | Linux / macOS |
|------|---------|---------------|
| 核心框架 | 完整支援 | 完整支援 |
| Office 新建（code-based） | openpyxl / docx-js / pptxgenjs | 同左 |
| MCP COM 伺服器（編輯已有） | pywin32 自動安裝 | 不支援 |
| LibreOffice（recalc / PDF） | 需手動安裝 | 套件管理器安裝 |

## 版控邊界

| 追蹤（框架） | 忽略（資料與知識） |
|-------------|-------------------|
| CLAUDE.md, agents/, commands/, workflows/ | skills/ 實際內容、agent-memory |
| skills-on-demand/*/SKILL.md | .skill.yaml（eval 元數據） |
| shared/tools/（含 office/ pptx/ docx/ pdf/） | shared/kb/（知識庫內容） |
| projects/_template/ | projects/* 實際專案資料 |
| environment.yml, init.py | `.env`, `.mcp.json`, `*.db` |

## 延伸閱讀

- [`SETUP.md`](SETUP.md) — 首次部署、套件分組、疑難排解
- [`.claude/CLAUDE.md`](.claude/CLAUDE.md) — Claude 運行規則（Agent 行為、workflow、技術約束）

## 授權

Private — 內部使用。
