"""Validator: check_sync_knowledge_index.

Ensures knowledge_lifecycle did not stop after DB writes while leaving the edge
queue stale.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path


def validate(context: dict) -> tuple[bool, str]:
    _default_root = Path(__file__).resolve().parent.parent.parent.parent
    root = Path(context.get("root", _default_root))
    outputs = context.get("outputs", {}) or {}

    if outputs.get("skipped"):
        return False, "sync_knowledge_index may not be skipped after write_to_dynamic"
    if outputs.get("index_synced") is not True:
        return False, "complete with {\"index_synced\": true} after running kb.py build-edges"

    db_path = root / "shared" / "kb" / "knowledge_graph" / "kb_index.db"
    if not db_path.exists():
        return False, f"KB DB missing: {db_path}"

    conn = sqlite3.connect(str(db_path))
    try:
        pending = conn.execute(
            "SELECT COUNT(DISTINCT source_id) FROM pending_edge_queue"
        ).fetchone()[0]
    finally:
        conn.close()

    if pending:
        return False, (
            f"pending_edge_queue still has {pending} node(s). "
            "Run: bash shared/tools/conda-python.sh shared/tools/kb.py build-edges"
        )

    return True, "knowledge index synced; pending_edge_queue is empty"
