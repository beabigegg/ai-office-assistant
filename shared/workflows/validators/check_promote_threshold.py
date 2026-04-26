"""Validator: check_promote_threshold.

Requires the workflow to compute the current active+high learning count instead
of relying on a free-form suggestion.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path


def validate(context: dict) -> tuple[bool, str]:
    _default_root = Path(__file__).resolve().parent.parent.parent.parent
    root = Path(context.get("root", _default_root))
    outputs = context.get("outputs", {}) or {}

    if "active_high_count" not in outputs:
        return False, "active_high_count missing from outputs"
    if "suggest_run_promote" not in outputs:
        return False, "suggest_run_promote missing from outputs"

    try:
        reported_count = int(outputs.get("active_high_count"))
    except (TypeError, ValueError):
        return False, "active_high_count must be an integer"

    suggested = outputs.get("suggest_run_promote")
    if not isinstance(suggested, bool):
        return False, "suggest_run_promote must be true/false"

    db_path = root / "shared" / "kb" / "knowledge_graph" / "kb_index.db"
    if not db_path.exists():
        return False, f"KB DB missing: {db_path}"

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT meta_json FROM nodes WHERE node_type='learning' AND status='active'"
        ).fetchall()
    finally:
        conn.close()

    actual_count = 0
    for row in rows:
        try:
            meta = json.loads(row["meta_json"] or "{}")
        except Exception:
            meta = {}
        if str(meta.get("confidence", "")).strip().lower() == "high":
            actual_count += 1

    if reported_count != actual_count:
        return False, (
            f"active_high_count mismatch: outputs={reported_count}, DB={actual_count}"
        )

    expected = actual_count >= 5
    if suggested != expected:
        return False, (
            "suggest_run_promote mismatch: "
            f"active_high_count={actual_count} implies {expected}"
        )

    return True, f"promote threshold checked: active_high_count={actual_count}, suggest_run_promote={suggested}"
