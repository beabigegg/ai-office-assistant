# AI Office Assistant

通用 AI 工作助手框架。基於 Claude Code，提供知識驅動的多專案工作流程管理。

## 功能特色

- **多專案管理**：標準化的專案結構（vault / workspace / scripts）
- **知識架構**：DB-first 知識圖譜（SQLite + Embedding 語意檢索）+ 按需載入 Skill
- **Workflow 引擎**：資料入庫、分析報告、知識生命週期、Post-Task Checklist
- **Sub-agent 委派**：query-runner（SQL 隔離）、report-builder（Office COM）、architect（架構掃描）、response-drafter（批量 LLM 呼叫）、table-reader（PDF 視覺辨識）
- **MCP 伺服器**：Excel / Word / PowerPoint COM 自動化（Windows）
- **遠端存取**：Claude Dispatch 持久會話支援

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
│   ├── agents/                # Sub-agent 定義
│   ├── commands/              # 快速指令
│   ├── skills/                # 領域 Skill（gitignore，由使用者建立）
│   │   └── _skill_template/
│   └── skills-on-demand/      # 按需載入 Skill（gitignore）
├── shared/
│   ├── kb/                    # 知識庫（gitignore，由 init.py 建立骨架）
│   ├── tools/                 # 共用工具腳本
│   ├── workflows/             # Workflow 定義 + Coordinator + Validators
│   └── protocols/             # 參考協議
├── projects/
│   └── _template/             # 專案範本
├── environment.yml            # Conda 環境定義（由 init.py 產生）
├── init.py                    # 初始化腳本（平台感知 + 套件分組）
├── CLAUDE.md                  # 本檔首頁說明（→ .claude/CLAUDE.md 為運行規則）
├── SETUP.md                   # 首次部署指引
├── .env.example               # 環境變數模板
└── .mcp.json.example          # MCP 設定模板
```

## 跨平台支援

| 元件 | Windows | Linux / macOS |
|------|---------|---------------|
| 核心框架 | 完整支援 | 完整支援 |
| MCP COM 伺服器 | pywin32 自動安裝 | 自動跳過（用 openpyxl/python-docx） |
| Claude Dispatch | 支援 (x64) | macOS 支援 |

## 版控邊界

| 追蹤（框架） | 忽略（資料與知識） |
|-------------|-------------------|
| CLAUDE.md, agents, commands, workflows | skills/kb 實際內容、agent-memory |
| shared/tools/, shared/protocols/ | `*.db`, `*.xlsx`, `*.pdf`, `*.csv` |
| projects/_template/ | projects/* 實際專案資料 |
| environment.yml, init.py | `.env`, `.mcp.json` |

## 延伸閱讀

- [`SETUP.md`](SETUP.md) — 首次部署、套件分組、疑難排解
- [`.claude/CLAUDE.md`](.claude/CLAUDE.md) — Claude 運行規則（Agent 行為、workflow、技術約束）

## 授權

Private — 內部使用。
