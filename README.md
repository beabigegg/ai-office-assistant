# AI Office Assistant

半導體／製造業場景的 AI 工作助手框架。基於 Claude Code，提供知識驅動的多專案工作流程管理。

## 功能特色

- **多專案管理**：標準化的專案結構（vault / workspace / scripts）
- **知識架構**：雙層知識庫（Skills 領域規則 + Dynamic 動態學習）+ 知識圖譜索引
- **Workflow 引擎**：資料入庫、分析報告、知識生命週期、Post-Task Checklist
- **Sub-agent 委派**：query-runner（SQL 隔離）、report-builder（Office COM）、architect（架構掃描）
- **MCP 伺服器**：Excel / Word / PowerPoint COM 自動化

## 快速開始

```bash
# 1. Clone
git clone <repo-url>
cd ai-office-assistant

# 2. 建立 conda 環境
conda env create -f environment.yml
conda activate ai-office

# 3. 初始化
python init.py

# 4. 設定環境變數
#    編輯 .env 填入 API key
#    確認 .mcp.json 路徑正確

# 5. 建立第一個專案
python init.py --project <project-name>

# 6. 建立領域 Skill
cp -r .claude/skills/_skill_template .claude/skills/<skill-name>
#    編輯 SKILL.md 和 .skill.yaml
```

## 專案結構

```
├── .claude/
│   ├── CLAUDE.md              # 核心指令（框架規則）
│   ├── agents/                # Sub-agent 定義
│   ├── commands/              # 快速指令（/promote, /status, /evolve）
│   ├── skills/                # 領域 Skill（gitignore，由使用者建立）
│   │   └── _skill_template/   # Skill 空白範本
│   └── skills-on-demand/      # 按需載入 Skill（gitignore）
├── shared/
│   ├── kb/                    # 知識庫（gitignore，由 init.py 建立骨架）
│   ├── tools/                 # 共用工具腳本
│   ├── workflows/             # Workflow 定義 + Coordinator + Validators
│   └── protocols/             # 參考協議
├── projects/
│   └── _template/             # 專案範本
├── environment.yml            # Conda 環境定義
├── init.py                    # 初始化腳本
├── .env.example               # 環境變數模板
└── .mcp.json.example          # MCP 設定模板
```

## 版控邊界

| 追蹤（框架） | 忽略（資料） |
|-------------|-------------|
| CLAUDE.md, agents, commands, workflows | skills 內容, kb 內容, agent-memory |
| shared/tools/, shared/protocols/ | *.db, *.xlsx, *.pdf, *.csv |
| projects/_template/ | projects/*（實際專案資料） |
| environment.yml, init.py | .env, .mcp.json |

## 技術棧

- **Runtime**：Python 3.13 + Conda
- **AI**：Claude Code（Anthropic）
- **資料處理**：openpyxl, PyMuPDF, chardet, SQLite
- **文件產出**：python-docx, python-pptx, pywin32（COM）
- **MCP**：自建 Excel/Word/PowerPoint COM 伺服器

## 授權

Private — 內部使用。
