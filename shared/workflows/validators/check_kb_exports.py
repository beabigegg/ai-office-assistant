"""Validator: check_kb_exports
Ensures markdown exports are refreshed when post_task recorded new KB entries.
DB remains the source of truth; this validator only enforces export freshness.
"""
from datetime import datetime, timezone
from pathlib import Path


def _parse_ts(raw: str | None):
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def validate(context: dict) -> tuple:
    _default_root = Path(__file__).resolve().parent.parent.parent.parent
    root = Path(context.get("root", _default_root))
    outputs = context.get("outputs", {})
    instance = context.get("instance", {})
    nodes = instance.get("nodes", {})

    decisions_outputs = nodes.get("record_decisions", {}).get("outputs", {}) or {}
    knowledge_outputs = nodes.get("record_knowledge", {}).get("outputs", {}) or {}

    decision_ids = decisions_outputs.get("decision_ids", [])
    learning_ids = knowledge_outputs.get("learning_ids", [])
    if isinstance(decision_ids, str):
        decision_ids = [decision_ids]
    if isinstance(learning_ids, str):
        learning_ids = [learning_ids]

    has_new_kb = bool(decision_ids or learning_ids)
    if not has_new_kb:
        return True, "no new decisions/learnings recorded, export refresh optional"

    if outputs.get("skipped"):
        return False, (
            "new KB entries were recorded but refresh_kb_exports was skipped. "
            "Run: bash shared/tools/conda-python.sh shared/tools/kb.py export all"
        )

    decisions_md = root / "shared" / "kb" / "decisions.md"
    learning_md = root / "shared" / "kb" / "dynamic" / "learning_notes.md"
    missing = [str(p.relative_to(root)) for p in (decisions_md, learning_md) if not p.exists()]
    if missing:
        return False, f"KB export files missing after refresh: {', '.join(missing)}"

    upstream_times = [
        _parse_ts(nodes.get("record_decisions", {}).get("completed_at")),
        _parse_ts(nodes.get("record_knowledge", {}).get("completed_at")),
    ]
    upstream_times = [ts for ts in upstream_times if ts is not None]
    latest_upstream = max(upstream_times) if upstream_times else None

    stale = []
    for path in (decisions_md, learning_md):
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        if latest_upstream and mtime < latest_upstream:
            stale.append(str(path.relative_to(root)))

    if stale:
        return False, (
            "KB exports appear stale after new DB writes: "
            f"{', '.join(stale)}. Run: bash shared/tools/conda-python.sh "
            "shared/tools/kb.py export all"
        )

    exported = outputs.get("export_targets", [])
    if isinstance(exported, str):
        exported = [exported]

    msg = "KB exports refreshed after new DB writes"
    if exported:
        msg += f" ({', '.join(exported)})"
    return True, msg
