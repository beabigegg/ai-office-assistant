"""Validator: check_dynamic_kb_status
M2 (EVO-016): Ensures the last 3 learning entries in kb_index.db have a valid
status value (active | promoted | obsolete). DB is the source of truth.
"""
import sqlite3
from pathlib import Path


def validate(context: dict) -> tuple:
    _default_root = Path(__file__).resolve().parent.parent.parent.parent
    root = Path(context.get('root', _default_root))
    db_path = root / 'shared' / 'kb' / 'knowledge_graph' / 'kb_index.db'

    if not db_path.exists():
        return True, "kb_index.db not found, skipped"

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, target, status FROM nodes "
            "WHERE node_type='learning' ORDER BY id DESC LIMIT 3"
        ).fetchall()

        if not rows:
            return True, "no learning entries in DB"

        valid_status = {'active', 'promoted', 'obsolete'}
        missing = []
        for r in rows:
            status = (r['status'] or '').strip().lower()
            if status not in valid_status:
                label = (r['target'] or r['id'])[:40]
                missing.append(f"{r['id']}({label}) status={r['status']!r}")

        if missing:
            return False, (
                f"M2: Recent learning entries have invalid status: "
                f"{'; '.join(missing)}. Fix via kb.py update <ID> --status active."
            )

        return True, f"M2: last {len(rows)} learning entries have valid status"
    finally:
        conn.close()
