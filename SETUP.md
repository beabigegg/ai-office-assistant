# Setup — 首次部署指引

> 一次性安裝文件。完成後日常使用請參考 `.claude/CLAUDE.md`。

---

## 系統需求

| 項目 | 版本／說明 |
|------|-----------|
| OS | Windows 10/11、macOS、Linux |
| Shell | Git Bash（Windows）或原生 bash/zsh |
| Python | 3.12（由 conda 管理，不需自行安裝） |
| Conda | Miniconda / Anaconda（必要） |
| GPU（選用） | NVIDIA GPU + CUDA 驅動（走 `ai-runtime-gpu` 群組時） |

---

## 快速開始

```bash
# 1. Clone
git clone <repo-url>
cd ai-office-assistant

# 2. 初始化（偵測硬體 → 產生 environment.yml）
python init.py

# 3. 建立 conda 環境（預設只裝 core 套件）
conda env create -f environment.yml
conda activate ai-office

# 4. 設定機密
cp .env.example .env
#    編輯 .env 填入實際金鑰
#    Windows：cp .mcp.json.example .mcp.json（init.py 會自動產生）

# 5. 建立第一個專案
python init.py --project <project-name>
```

---

## init.py 套件分組

`init.py` 產生的 `environment.yml` 預設只含 **Core 套件**（跨領域通用）。
特定領域（OCR、CAD、ML、MES、Oracle、AI runtime）透過 `--with <group>` 啟用。

### Core（預設安裝）

跨領域通用：`openpyxl`, `xlrd`, `chardet`, `pyyaml`, `requests`, `python-docx`, `python-pptx`, `PyMuPDF`, `pdfplumber`, `mcp`, `python-dotenv`, `pandas`, `sqlite-vec`, `transitions`, `pywin32`（Windows）

### Optional groups

| Group | 用途 | 套件 |
|-------|------|------|
| `ocr` | PDF OCR / 視覺辨識 | rapidocr, docling |
| `mes` | MES SSRS 整合、瀏覽器自動化 | requests-ntlm, playwright |
| `cad` | AutoCAD DXF、3D 建模 | ezdxf, trimesh, shapely, mapbox-earcut, manifold3d, matplotlib |
| `oracle` | Oracle DB 連線 | oracledb |
| `ml` | 機器學習／統計分析 | scikit-learn, statsmodels, matplotlib, lightgbm, shap, ruptures, mlxtend |
| `causal` | 因果／貝氏網路 | pgmpy |
| `ai-runtime-gpu` | PyTorch + ONNX（GPU） | torch(cu128), torchvision, onnxruntime-gpu |
| `ai-runtime-cpu` | PyTorch + ONNX（CPU） | torch(cpu), torchvision, onnxruntime |

### 用例

```bash
# 只要 core
python init.py

# core + OCR + ML
python init.py --with ocr --with ml

# core + GPU AI runtime（用於 Embedding、向量化）
python init.py --with ai-runtime-gpu

# 強制 CPU（即使偵測到 GPU）
python init.py --force-cpu --with ai-runtime-cpu
# 或不帶 --with 後續再手動擴充

# 強制 GPU（即使未偵測到 GPU）
python init.py --force-gpu --with ai-runtime-gpu
```

### 之後新增群組

```bash
# 重新產生 environment.yml（新群組加入）
python init.py --with ocr --with cad

# 套用到既有 conda env
conda env update -f environment.yml --prune
```

---

## 首次部署流程

```bash
git clone <repo-url>
cd <repo>
python init.py [--with <group>...]
conda env create -f environment.yml
conda activate ai-office
cp .env.example .env           # 填入實際金鑰
python init.py --project demo  # 建立第一個專案
```

完成後：
- `.claude/CLAUDE.md` 是 Claude 運行時的規則，每次會話自動載入
- 開始使用 Claude Code 即可

---

## 環境變數（.env）

| 檔案 | 用途 | 版控 |
|------|------|------|
| `.env.example` | 變數模板（無實際值） | 追蹤 |
| `.env` | 實際金鑰 | **忽略** |
| `.mcp.json.example` | MCP 設定模板（相對路徑） | 追蹤 |
| `.mcp.json` | 本機 MCP 設定（絕對路徑） | **忽略** |

Python 讀取範例：

```python
import os
api_key = os.environ.get('MASTER_API_KEY', '')
```

**機密嚴禁硬編碼於任何受版控檔案**。

---

## 手動同步已有環境

```bash
# init.py 改動後，套用到現有 conda env
python init.py [--with <group>...]
conda env update -f environment.yml --prune
```

---

## 疑難排解

### Windows 上 MCP COM servers 無法啟動

- 確認 `conda activate ai-office`
- 確認 `.mcp.json` 路徑為絕對路徑（`python init.py` 會自動產生）
- 確認 `pywin32` 已安裝：`python -c "import win32com.client"`

### Linux/macOS 上 MCP Office 功能不可用

COM 自動化僅支援 Windows。Linux/macOS 請改用 Python 層級 API：
- Excel：`openpyxl`
- Word：`python-docx`
- PowerPoint：`python-pptx`

### GPU 偵測失敗

- 確認 `nvidia-smi` 可執行
- 或手動指定：`python init.py --force-gpu --with ai-runtime-gpu`

### 套件衝突

```bash
conda env remove -n ai-office
python init.py [--with <group>...]
conda env create -f environment.yml
```

---

## 目錄結構

```
├── .claude/
│   ├── CLAUDE.md              # Claude 運行規則（框架層）
│   ├── agents/                # Sub-agent 定義
│   ├── commands/              # 快速指令
│   └── skills/                # 領域 Skill（gitignore）
│       └── _skill_template/
├── shared/
│   ├── kb/                    # 知識庫（gitignore）
│   ├── tools/                 # 共用工具
│   └── workflows/             # Workflow 引擎與定義
├── projects/
│   └── _template/             # 專案範本
├── environment.yml            # Conda 環境（init.py 產生）
├── init.py                    # 初始化腳本
├── .env.example
└── .mcp.json.example
```

---

## 版控邊界

| 追蹤（框架） | 忽略（資料／知識） |
|-------------|-------------------|
| `.claude/CLAUDE.md`、`.claude/agents/`、`.claude/commands/` | `.claude/skills-on-demand/*/` 實際內容、`.claude/agent-memory/` |
| `shared/tools/`、`shared/workflows/`、`shared/protocols/` | `shared/kb/` 全部、`shared/workflows/state/` |
| `projects/_template/` | `projects/*/` 實際專案資料 |
| `environment.yml`、`init.py`、`.env.example`、`.mcp.json.example` | `.env`、`.mcp.json`、`*.db`、`*.xlsx`、`*.pdf` |
