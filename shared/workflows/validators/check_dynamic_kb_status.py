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
        requested_ids = [str(entry_id).strip() for entry_id in requested_ids if str(entry_id).strip()]

        if not requested_ids:
            return False, "kb_entry_ids missing from outputs; validator must check exact DB rows written this round"

        placeholders = ",".join("?" for _ in requested_ids)
        rows = conn.execute(
            f"SELECT id, node_type, target, status FROM nodes "
            f"WHERE id IN ({placeholders}) "
            f"ORDER BY id DESC",
            requested_ids,
        ).fetchall()

        found_ids = {row["id"] for row in rows}
        missing_ids = [entry_id for entry_id in requested_ids if entry_id not in found_ids]
        if missing_ids:
            return False, f"kb_entry_ids not found in DB: {', '.join(missing_ids)}"

        learning_rows = [row for row in rows if row["node_type"] == "learning"]

        if not learning_rows:
            return True, "requested KB entries are decisions only; learning status check not applicable"

        valid_status = {'draft', 'active', 'mature', 'promoted', 'stale', 'archived'}
        missing = []
        for r in learning_rows:
            status = (r['status'] or '').strip().lower()
            if status not in valid_status:
                label = (r['target'] or r['id'])[:40]
                missing.append(f"{r['id']}({label}) status={r['status']!r}")

        if missing:
            return False, (
                f"M2: Recent learning entries have invalid status: "
                f"{'; '.join(missing)}. Fix via kb.py update <ID> --status <allowed-learning-status>."
            )

        return True, "M2: requested learning entries have valid status"
    finally:
        conn.close()
