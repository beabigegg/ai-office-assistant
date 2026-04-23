---
name: sqlite-operations
description: |
  WHAT：Windows Git Bash 環境下 SQLite / Python 操作的防錯規則（編碼/引號/型別）。
  WHEN：寫 python -c 查 .db、寫 Python 腳本操作 SQLite、處理 UnicodeEncodeError。
  NOT：查特定 DB schema 請用 db_schema.py；查知識 DB 請用 kb.py。
triggers:
  - SQLite, .db, sqlite3, python sqlite
  - python -c, SQL 查詢, Windows cp950
  - UnicodeEncodeError, UTF-8 編碼, 中文輸出
  - row_factory, 參數化查詢, SQL 注入
  - _tmp_query, 臨時腳本
---

# SQLite 操作 — Windows Git Bash 防錯規則

## R1: 中文輸出必須強制 UTF-8

**問題**：Windows console 預設 cp950，中文字元輸出會 `UnicodeEncodeError`。

**正確做法**：
```python
# 腳本開頭加
import sys
if sys.platform == 'win32':
    sys.stdout = open(sys.stdout.fileno(), 'w', encoding='utf-8', errors='replace', closefd=False)
    sys.stderr = open(sys.stderr.fileno(), 'w', encoding='utf-8', errors='replace', closefd=False)
```

**適用**：所有會輸出中文的 Python 腳本和 `python -c`。

---

## R2: 複雜查詢寫腳本，不用 `python -c`

**問題**：`python -c "..."` 在 bash 中，外層雙引號與 Python/SQL 雙引號衝突，多行邏輯難以維護。

**判斷標準**：
- ≤5 行、無中文、無雙引號 SQL → 可用 `python -c`
- 其他情況 → 寫臨時腳本 `workspace/scripts/_tmp_query.py` 或用現有工具

**錯誤案例**：
```bash
# ✗ 雙引號衝突，SQL 中 != "" 會被 bash 吃掉
python -c "conn.execute('SELECT * FROM nodes WHERE target != \"\"')"
```

**正確做法**：
```bash
# ✓ 寫腳本
python workspace/scripts/_tmp_query.py

# ✓ 或用 kb_index.py 等現有工具
python shared/tools/kb_index.py active --project ecr-ecn
```

---

## R3: SQL 字串用單引號，Python 字串用雙引號

**問題**：bash 外層用雙引號時，內層 Python 字串也用雙引號會衝突。

**正確模式**：
```python
# ✓ Python 字串雙引號，SQL 值單引號
conn.execute("SELECT * FROM nodes WHERE status='active' AND target != ''")

# ✗ 混用導致 unrecognized token
conn.execute('SELECT * FROM nodes WHERE status="active"')  # bash 下會失敗
```

---

## R4: 解析結果確保型別（list vs str）

**問題**：從 config/meta 解析出的值可能是 str 或 list，直接 `.append()` 會 `AttributeError`。

**正確做法**：
```python
def _ensure_list(val):
    if val is None:
        return []
    if isinstance(val, str):
        return [v.strip() for v in val.split('|') if v.strip()]
    return list(val)

refs = _ensure_list(meta.get('refs_skill'))  # 保證是 list
```

---

## R5: 讀取 .db 檔案時指定完整路徑

**問題**：相對路徑在不同 cwd 下結果不同。

**正確做法**：
```python
from pathlib import Path
DB_PATH = Path(__file__).resolve().parent.parent / 'kb' / 'knowledge_graph' / 'kb_index.db'
conn = sqlite3.connect(str(DB_PATH))
```

---

## R6: 查詢結果用 `row_factory` 提升可讀性

```python
conn.row_factory = sqlite3.Row
row = conn.execute("SELECT id, status FROM nodes WHERE id=?", (node_id,)).fetchone()
print(row['status'])  # ✓ 比 row[1] 更清楚
```

---

## R7: 參數化查詢防注入

```python
# ✓ 參數化
conn.execute("SELECT * FROM nodes WHERE id=?", (user_input,))

# ✗ 字串拼接
conn.execute(f"SELECT * FROM nodes WHERE id='{user_input}'")
```

---

## R8: bash 中 `!=` 的轉義

**問題**：bash 的 `!` 在雙引號內觸發 history expansion。

**正確做法**：
```bash
# ✓ 用單引號包 Python 程式碼（但內部不能再用單引號）
python -c 'import sqlite3; ...'

# ✓ 或在腳本中寫，避開 bash 解釋
python my_script.py
```

---

## 決策流程圖

```
需要查 SQLite 資料？
  ├── 有現成工具（kb_index.py 等）？ → 直接用工具
  ├── 簡單查詢（≤5行、無中文）？ → python -c（單引號包裹）
  └── 複雜查詢？ → 寫 .py 腳本，開頭加 R1 的 UTF-8 設定
```
