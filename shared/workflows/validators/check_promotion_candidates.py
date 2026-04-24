"""Validator: check_promotion_candidates

Scans `nodes` table for `learning` entries whose `meta_json.usage_count`
exceeds the `min_usage` threshold (default 3), and enqueues them into
`shared/workflows/state/promotion_queue.json`.

Non-blocking — always returns (True, msg). Does not mutate the KB itself;
only the queue file is written.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _import_promotion_state(root: Path):
    tools_dir = str(root / 'shared' / 'tools')
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    import promotion_state  # noqa: E402
    return promotion_state


def validate(context: dict) -> tuple:
    _default_root = Path(__file__).resolve().parent.parent.parent.parent
    root = Path(context.get('root', _default_root))
    db_path = root / 'shared' / 'kb' / 'knowledge_graph' / 'kb_index.db'
    if not db_path.exists():
        return True, "kb_index.db not found, skipped"

    params = context.get('params') or {}
    try:
        min_usage = int(params.get('min_usage', 3))
    except (TypeError, ValueError):
        min_usage = 3

    try:
        promotion_state = _import_promotion_state(root)
    except Exception as e:
        return True, f"promotion_state import failed: {e}"

    try:
        existing = {
            entry.get('learning_id')
            for entry in promotion_state.load_queue(root)
        }
    except Exception:
        existing = set()

    eval_history: dict = {}
    if hasattr(promotion_state, 'load_eval_history'):
        try:
            eval_history = promotion_state.load_eval_history(root)
        except Exception:
            pass

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    new_candidates: list[tuple[str, dict, str | None]] = []
    # Build set of existing skill directory names to detect overlap
    skills_dir = root / '.claude' / 'skills-on-demand'
    existing_skills: set[str] = set()
    if skills_dir.exists():
        existing_skills = {
            d.name for d in skills_dir.iterdir()
            if d.is_dir() and (d / 'SKILL.md').exists()
        }

    try:
        rows = conn.execute(
            "SELECT id, meta_json, status, refs_skill FROM nodes "
            "WHERE node_type='learning' AND status='active'"
        ).fetchall()
        for r in rows:
            nid = r['id']
            if nid in existing:
                continue
            raw = r['meta_json']
            if not raw:
                continue
            try:
                meta = json.loads(raw)
            except Exception:
                continue
            if not isinstance(meta, dict):
                continue
            if meta.get('status') == 'promoted':
                continue
            try:
                usage = int(meta.get('usage_count', 0) or 0)
            except (TypeError, ValueError):
                usage = 0
            if usage >= min_usage:
                # Eval-history exclusion — mirrors _scan_and_queue_candidates logic
                _eval = eval_history.get(nid)
                if _eval:
                    _eval_result = _eval.get('result', '')
                    if _eval_result == 'proposed':
                        continue
                    if _eval_result in ('below_threshold', 'failed', 'unknown'):
                        try:
                            _dt = datetime.fromisoformat(_eval.get('evaluated_at', ''))
                            if datetime.now(timezone.utc) - _dt < timedelta(days=30):
                                continue
                        except Exception:
                            continue
                    if _eval_result == 'overlap':
                        try:
                            _dt = datetime.fromisoformat(_eval.get('evaluated_at', ''))
                            if datetime.now(timezone.utc) - _dt < timedelta(days=7):
                                continue
                        except Exception:
                            continue
                    if _eval_result == 'in_progress':
                        try:
                            _dt = datetime.fromisoformat(_eval.get('evaluated_at', ''))
                            if datetime.now(timezone.utc) - _dt < timedelta(hours=24):
                                continue
                        except Exception:
                            continue
                # Parse refs_skill: DB stores JSON array like '["bom-rules"]' or plain string
                suggested: str | None = None
                raw_refs = r['refs_skill']
                if raw_refs:
                    try:
                        parsed = json.loads(raw_refs)
                        if isinstance(parsed, list) and parsed:
                            suggested = str(parsed[0])
                        elif isinstance(parsed, str):
                            suggested = parsed
                    except (json.JSONDecodeError, TypeError):
                        suggested = raw_refs
                # Skip if a skill with the same name already exists (overlap guard)
                if suggested and suggested in existing_skills:
                    continue
                new_candidates.append((nid, meta, suggested))
    finally:
        conn.close()

    if not new_candidates:
        return True, "no new promotion candidates"

    added_ids: list[str] = []
    for nid, meta, refs_skill in new_candidates:
        try:
            if promotion_state.add_candidate(root, nid, meta, suggested_skill=refs_skill):
                added_ids.append(nid)
        except Exception:
            pass

    if not added_ids:
        return True, "no new promotion candidates"

    preview = ', '.join(added_ids[:5])
    suffix = f" (+{len(added_ids) - 5} more)" if len(added_ids) > 5 else ""
    return True, f"queued {len(added_ids)} promotion candidates: {preview}{suffix}"
