"""Validator: check_memory.

Checks:
1. A repo-local MEMORY.md stays under the hard line limit.
2. A required snapshot both exists on disk and is indexed in DB.
3. `memory_conditions_met` is backed by structured trigger evidence instead of a
   free-form self-declaration.
"""
import sqlite3
from pathlib import Path
import re

MEMORY_MD_LINE_LIMIT = 200
MEMORY_MD_WARN_THRESHOLD = 160
VALID_TRIGGER_REASONS = {
    "files_written",
    "db_schema_changed",
    "report_produced",
    "conversation_rounds",
    "new_decisions",
}


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


def _resolve_memory_md(root: Path) -> Path | None:
    """Prefer repo-local agent memory; fall back to Claude project memories."""
    candidates = [
        root / ".claude" / "agent-memory" / "architect" / "MEMORY.md",
    ]
    home_projects = Path.home() / ".claude" / "projects"
    if home_projects.exists():
        try:
            candidates.extend(sorted(home_projects.glob("*/memory/MEMORY.md")))
        except OSError:
            pass

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _normalize_reason_list(raw) -> list[str]:
    if isinstance(raw, str):
        return [raw.strip()] if raw.strip() else []
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    return []


def _node_outputs(instance: dict, node_id: str) -> dict:
    return (instance.get("nodes", {}).get(node_id, {}).get("outputs", {}) or {})


def _validate_trigger_evidence(instance: dict, outputs: dict) -> tuple[bool, str]:
    reasons = _normalize_reason_list(outputs.get("trigger_reasons"))
    if not reasons:
        return False, "memory_conditions_met=true requires trigger_reasons"

    invalid = [reason for reason in reasons if reason not in VALID_TRIGGER_REASONS]
    if invalid:
        return False, f"invalid trigger_reasons: {', '.join(invalid)}"

    evidence = outputs.get("trigger_evidence", {})
    if not isinstance(evidence, dict):
        return False, "trigger_evidence must be an object"

    decision_ids = _node_outputs(instance, "record_decisions").get("decision_ids", [])
    if isinstance(decision_ids, str):
        decision_ids = [decision_ids]
    decision_count = len([did for did in decision_ids if str(did).strip()])

    verified = []
    for reason in reasons:
        if reason == "new_decisions":
            if decision_count >= 2:
                verified.append(reason)
                continue
            return False, (
                "trigger reason 'new_decisions' requires at least 2 decisions from record_decisions"
            )

        if reason == "conversation_rounds":
            rounds = evidence.get("conversation_rounds")
            if isinstance(rounds, int) and rounds >= 10:
                verified.append(reason)
                continue
            return False, "trigger reason 'conversation_rounds' requires trigger_evidence.conversation_rounds >= 10"

        if reason == "files_written":
            files_written = evidence.get("files_written", [])
            if isinstance(files_written, list) and len([p for p in files_written if str(p).strip()]) >= 3:
                verified.append(reason)
                continue
            return False, "trigger reason 'files_written' requires at least 3 file paths in trigger_evidence.files_written"

        if reason == "report_produced":
            report_paths = evidence.get("report_paths", [])
            if isinstance(report_paths, list) and any(str(p).strip() for p in report_paths):
                verified.append(reason)
                continue
            return False, "trigger reason 'report_produced' requires trigger_evidence.report_paths"

        if reason == "db_schema_changed":
            schema_changed = evidence.get("db_schema_changed")
            db_paths = evidence.get("db_paths", [])
            if schema_changed is True and isinstance(db_paths, list) and any(str(p).strip() for p in db_paths):
                verified.append(reason)
                continue
            return False, (
                "trigger reason 'db_schema_changed' requires "
                "trigger_evidence.db_schema_changed=true and trigger_evidence.db_paths"
            )

    if not verified:
        return False, "no trigger reason could be verified"
    return True, f"verified trigger reasons: {', '.join(verified)}"


def validate(context: dict) -> tuple:
    _default_root = Path(__file__).resolve().parent.parent.parent.parent
    root = Path(context.get('root', _default_root))
    outputs = context.get('outputs', {})
    memory_dir = root / 'shared' / 'kb' / 'memory'

    warnings = []

    # --- Check 1: MEMORY.md line count ---
    memory_md_path = _resolve_memory_md(root)
    if memory_md_path and memory_md_path.exists():
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
    else:
        warnings.append("MEMORY.md not found; line-limit check skipped")

    # --- Check 2: Memory snapshot ---
    conditions_met = outputs.get('memory_conditions_met', False)
    evidence_ok, evidence_msg = _validate_trigger_evidence(context.get("instance", {}) or {}, outputs) if conditions_met else (True, "")

    if not conditions_met:
        decision_ids = _node_outputs(context.get("instance", {}) or {}, "record_decisions").get("decision_ids", [])
        if isinstance(decision_ids, str):
            decision_ids = [decision_ids]
        if len([did for did in decision_ids if str(did).strip()]) >= 2:
            return False, (
                "memory_conditions_met=false conflicts with record_decisions output "
                "(>=2 new decisions should trigger a snapshot)"
            )

        msg = "memory conditions not met, snapshot not required"
        if warnings:
            msg += f" [WARN: {'; '.join(warnings)}]"
        return True, msg

    if not evidence_ok:
        return False, evidence_msg

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

    msg = f"snapshot written and indexed: {snapshot_path.name} ({evidence_msg})"
    if warnings:
        msg += f" [WARN: {'; '.join(warnings)}]"
    return True, msg
