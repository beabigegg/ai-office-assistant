"""Validator: check_select_candidate.

Ensures skill_self_learning starts from a real DB learning and a valid
governance-friendly skill name.
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate(context: dict) -> tuple[bool, str]:
    _default_root = Path(__file__).resolve().parent.parent.parent.parent
    root = Path(context.get("root", _default_root))
    outputs = context.get("outputs", {}) or {}
    learning_id = str(outputs.get("learning_id", "")).strip()
    suggested_skill = str(outputs.get("suggested_skill", "")).strip()
    overlap_found = outputs.get("overlap_found")

    if not learning_id:
        return False, "learning_id missing"
    if not suggested_skill:
        return False, "suggested_skill missing"
    if not SKILL_NAME_RE.match(suggested_skill):
        return False, (
            "suggested_skill must be lowercase kebab-case "
            f"(got: {suggested_skill!r})"
        )
    if not isinstance(overlap_found, bool):
        return False, "overlap_found must be true/false"

    queue_path = root / "shared" / "workflows" / "state" / "promotion_queue.json"
    if queue_path.exists():
        try:
            queue = json.loads(queue_path.read_text(encoding="utf-8"))
            if isinstance(queue, list) and queue:
                first_id = str((queue[0] or {}).get("learning_id", "")).strip()
                if first_id and first_id != learning_id:
                    return False, (
                        f"select_candidate must use the first queued learning_id "
                        f"({first_id}), got {learning_id}"
                    )
        except Exception as exc:
            return False, f"promotion_queue.json unreadable: {exc}"

    db_path = root / "shared" / "kb" / "knowledge_graph" / "kb_index.db"
    if not db_path.exists():
        return False, f"KB DB missing: {db_path}"

    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute(
            "SELECT node_type, status FROM nodes WHERE id=?",
            (learning_id,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return False, f"learning_id not found in DB: {learning_id}"
    if row[0] != "learning":
        return False, f"learning_id must point to a learning node, got {row[0]!r}"

    return True, f"candidate validated: {learning_id} -> {suggested_skill}"
