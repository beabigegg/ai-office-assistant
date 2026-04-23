"""Validator: check_dynamic_kb_status.

Ensures recently written learning entries use the runtime-supported learning
status set. DB is the source of truth.
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
        requested_ids = context.get('outputs', {}).get('kb_entry_ids', [])
        if isinstance(requested_ids, str):
            requested_ids = [requested_ids]

        if requested_ids:
            placeholders = ",".join("?" for _ in requested_ids)
            rows = conn.execute(
                f"SELECT id, target, status FROM nodes "
                f"WHERE node_type='learning' AND id IN ({placeholders}) "
                f"ORDER BY id DESC",
                requested_ids,
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, target, status FROM nodes "
                "WHERE node_type='learning' ORDER BY id DESC LIMIT 3"
            ).fetchall()

        if not rows:
            return True, "no learning entries in DB"

        valid_status = {'draft', 'active', 'mature', 'promoted', 'stale', 'archived'}
        missing = []
        for r in rows:
            status = (r['status'] or '').strip().lower()
            if status not in valid_status:
                label = (r['target'] or r['id'])[:40]
                missing.append(f"{r['id']}({label}) status={r['status']!r}")

        if missing:
            return False, (
                f"M2: Recent learning entries have invalid status: "
                f"{'; '.join(missing)}. Fix via kb.py update <ID> --status <allowed-learning-status>."
            )

        scope = "requested" if requested_ids else "recent"
        return True, f"M2: {scope} learning entries have valid status"
    finally:
        conn.close()
