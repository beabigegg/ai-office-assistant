"""Validator: check_memory
Checks if memory snapshot conditions are met and if snapshot exists.
Also checks MEMORY.md line count against 200-line hard limit.
"""
import sqlite3
from pathlib import Path
import re

MEMORY_MD_LINE_LIMIT = 200
MEMORY_MD_WARN_THRESHOLD = 160


def _resolve_snapshot(outputs: dict, memory_dir: Path):
    """Resolve snapshot path/id from explicit outputs before falling back.

    Avoid inferring the expected snapshot name from local date, because
    workflow timestamps may be UTC while file naming is local-project policy.
    """
    raw_path = str(outputs.get("snapshot_path", "")).strip()
    snapshot_id = str(outputs.get("snapshot_id", "")).strip()

    path = None
    if raw_path:
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = (memory_dir.parent.parent.parent / candidate).resolve()
        path = candidate
        if not snapshot_id:
            snapshot_id = candidate.stem
    elif snapshot_id:
        path = memory_dir / f"{snapshot_id}.md"

    if path is None:
        return None, None

    if not snapshot_id:
        snapshot_id = path.stem

    if not re.match(r"^\d{4}-\d{2}-\d{2}(?:_.+)?$", snapshot_id):
        return path, snapshot_id
    return path, snapshot_id


def validate(context: dict) -> tuple:
    _default_root = Path(__file__).resolve().parent.parent.parent.parent
    root = Path(context.get('root', _default_root))
    outputs = context.get('outputs', {})
    memory_dir = root / 'shared' / 'kb' / 'memory'

    warnings = []

    # --- Check 1: MEMORY.md line count ---
    memory_md_path = Path.home() / '.claude' / 'projects' / 'D--ai-office' / 'memory' / 'MEMORY.md'
    if memory_md_path.exists():
        line_count = len(memory_md_path.read_text(encoding='utf-8').splitlines())
        if line_count > MEMORY_MD_LINE_LIMIT:
            return False, (
                f"MEMORY.md has {line_count} lines (limit: {MEMORY_MD_LINE_LIMIT}). "
                f"Must consolidate or remove stale entries before continuing."
            )
        elif line_count > MEMORY_MD_WARN_THRESHOLD:
            warnings.append(
                f"MEMORY.md approaching limit: {line_count}/{MEMORY_MD_LINE_LIMIT} lines"
            )

    # --- Check 2: Memory snapshot ---
    conditions_met = outputs.get('memory_conditions_met', False)

    if not conditions_met:
        msg = "memory conditions not met, snapshot not required"
        if warnings:
            msg += f" [WARN: {'; '.join(warnings)}]"
        return True, msg

    snapshot_path, snapshot_id = _resolve_snapshot(outputs, memory_dir)
    if snapshot_path is None:
        return False, (
            "memory conditions met but snapshot_path missing. "
            "Complete with outputs like "
            "{\"memory_conditions_met\":true,"
            "\"snapshot_path\":\"shared/kb/memory/YYYY-MM-DD.md\"}"
        )

    if not snapshot_path.exists():
        return False, f"conditions met but no snapshot found at {snapshot_path}"

    db_path = root / 'shared' / 'kb' / 'knowledge_graph' / 'kb_index.db'
    if not db_path.exists():
        return False, f"snapshot written but KB DB missing: {db_path}"

    try:
        conn = sqlite3.connect(str(db_path))
        row = conn.execute(
            "SELECT id FROM session_snapshots WHERE id=?",
            (snapshot_id,),
        ).fetchone()
    except sqlite3.Error as exc:
        return False, f"snapshot written but snapshot index unreadable: {exc}"
    finally:
        try:
            conn.close()
        except Exception:
            pass

    if row is None:
        return False, (
            f"snapshot written but not indexed in session_snapshots: {snapshot_id}. "
            f"Run: bash shared/tools/conda-python.sh shared/tools/kb.py import-snapshot {snapshot_path}"
        )

    msg = f"snapshot written and indexed: {snapshot_path.name}"
    if warnings:
        msg += f" [WARN: {'; '.join(warnings)}]"
    return True, msg
