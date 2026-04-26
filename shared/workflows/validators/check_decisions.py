"""Validator: check_decisions
Verifies D-NNN sequential numbering with no gaps.
EVO-016: Reads from kb_index.db (source of truth) instead of decisions.md.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def validate(context: dict) -> tuple:
    """Check decision sequential numbering + L2 conflict detection.

    EVO-016: Reads from kb_index.db (source of truth) instead of decisions.md.
    """
    import sqlite3
    _default_root = Path(__file__).resolve().parent.parent.parent.parent
    root = Path(context.get('root', _default_root))
    db_path = root / 'shared' / 'kb' / 'knowledge_graph' / 'kb_index.db'

    if not db_path.exists():
        return True, "kb_index.db not found, skipped"

    outputs = context.get("outputs", {}) or {}
    decision_ids = outputs.get("decision_ids", [])
    if isinstance(decision_ids, str):
        decision_ids = [decision_ids]
    decision_ids = [str(x).strip() for x in decision_ids if str(x).strip()]

    if outputs.get("skipped"):
        return True, "no new decisions recorded"

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, target, meta_json FROM nodes "
            "WHERE node_type='decision' ORDER BY id"
        ).fetchall()

        numbers = []
        id_to_row = {}
        for r in rows:
            m = re.match(r'D-(\d+)', r['id'])
            if m:
                n = int(m.group(1))
                numbers.append(n)
                id_to_row[n] = r
        numbers.sort()

        if not numbers:
            return True, "no D-NNN entries in DB"

        # Gap check
        expected = list(range(numbers[0], numbers[-1] + 1))
        gaps = sorted(set(expected) - set(numbers))
        if gaps:
            gap_strs = [f"D-{g:03d}" for g in gaps[:5]]
            suffix = f" (and {len(gaps)-5} more)" if len(gaps) > 5 else ""
            return False, f"gaps in numbering: {', '.join(gap_strs)}{suffix}"

        message = f"{len(numbers)} entries, D-{numbers[0]:03d} to D-{numbers[-1]:03d}"

        if not decision_ids:
            return False, "decision_ids missing from outputs"

        missing_ids = [did for did in decision_ids if did not in {r["id"] for r in rows}]
        if missing_ids:
            return False, f"decision ids not found in DB: {', '.join(missing_ids)}"

        # Meta completeness + conflict checks only on decisions recorded this round.
        missing_meta = []
        recorded_targets = {}
        for did in decision_ids:
            m = re.match(r"D-(\d+)", did)
            if not m:
                continue
            r = id_to_row.get(int(m.group(1)))
            if r is None:
                continue
            meta_ok = False
            if r['meta_json']:
                try:
                    meta = json.loads(r['meta_json'])
                    if meta.get('status') and meta.get('target'):
                        meta_ok = True
                except Exception:
                    pass
            if not meta_ok:
                missing_meta.append(did)
            if r['target']:
                recorded_targets[did] = r['target']
        if missing_meta:
            message += f" | WARN: missing kb meta: {', '.join(missing_meta)}"
    finally:
        conn.close()

    # Delegate validate/check-conflict to kb.py (EVO-016).
    # Keep validator side-effect free: exports/index generation belongs to refresh_kb_exports.
    try:
        kb_script = str(root / 'shared' / 'tools' / 'kb.py')
        env = dict(os.environ, PYTHONIOENCODING='utf-8')
        val_result = subprocess.run(
            [sys.executable, kb_script, 'validate', '--quiet'],
            capture_output=True, timeout=10, cwd=str(root),
            encoding='utf-8', errors='replace', env=env
        )
        if val_result.returncode == 2:
            return False, f"KB consistency ERROR (must fix before proceeding): {val_result.stdout.strip()[:300]}"
        elif val_result.returncode == 1 and val_result.stdout.strip():
            message += f" | KB warnings: {val_result.stdout.strip()[:200]}"
        elif val_result.returncode not in (0, 1, 2):
            stderr = (val_result.stderr or '').strip()
            return False, f"kb.py validate failed unexpectedly: {stderr[:200] or val_result.returncode}"

        for did, target_text in recorded_targets.items():
            conflict_result = subprocess.run(
                [sys.executable, kb_script, 'check-conflict', target_text, '--threshold', '0.5'],
                capture_output=True, timeout=10, cwd=str(root),
                encoding='utf-8', errors='replace', env=env
            )
            if conflict_result.returncode == 1 and conflict_result.stdout.strip():
                conflict_lines = [
                    line for line in conflict_result.stdout.strip().split('\n')
                    if did not in line and line.strip().startswith(('D-', ' '))
                ]
                if conflict_lines:
                    return False, f"L2-CONFLICT {did}: {'; '.join(l.strip() for l in conflict_lines[:3])}"
            elif conflict_result.returncode not in (0, 1):
                stderr = (conflict_result.stderr or '').strip()
                return False, f"kb.py check-conflict failed for {did}: {stderr[:200] or conflict_result.returncode}"
    except Exception as exc:
        return False, f"decision validation subprocess failed: {exc}"

    return True, message
