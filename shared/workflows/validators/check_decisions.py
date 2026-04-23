"""Validator: check_decisions
Verifies D-NNN sequential numbering with no gaps.
EVO-016: Reads from kb_index.db (source of truth) instead of decisions.md.
"""
import re
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

        # Meta completeness check on last 5 (meta_json must carry status/target)
        recent_ids = numbers[-5:]
        missing_meta = []
        recent_targets = {}
        for n in recent_ids:
            r = id_to_row[n]
            did = f"D-{n:03d}"
            meta_ok = False
            if r['meta_json']:
                try:
                    import json as _json
                    meta = _json.loads(r['meta_json'])
                    if meta.get('status') and meta.get('target'):
                        meta_ok = True
                except Exception:
                    pass
            if not meta_ok:
                missing_meta.append(did)
            if r['target']:
                recent_targets[did] = r['target']
        if missing_meta:
            message += f" | WARN: missing kb meta: {', '.join(missing_meta)}"
    finally:
        conn.close()

    # Delegate sync/validate/check-conflict/regenerate to kb.py (EVO-016)
    try:
        import subprocess, os
        kb_script = str(root / 'shared' / 'tools' / 'kb.py')
        env = dict(os.environ, PYTHONIOENCODING='utf-8')
        subprocess.run(
            ['python', kb_script, 'sync', '--quiet'],
            capture_output=True, timeout=10, cwd=str(root), env=env
        )
        val_result = subprocess.run(
            ['python', kb_script, 'validate', '--quiet'],
            capture_output=True, timeout=10, cwd=str(root),
            encoding='utf-8', errors='replace'
        )
        if val_result.returncode == 2:
            return False, f"KB consistency ERROR (must fix before proceeding): {val_result.stdout.strip()[:300]}"
        elif val_result.returncode == 1 and val_result.stdout.strip():
            message += f" | KB warnings: {val_result.stdout.strip()[:200]}"

        for did, target_text in recent_targets.items():
            conflict_result = subprocess.run(
                ['python', kb_script, 'check-conflict', target_text, '--threshold', '0.5'],
                capture_output=True, timeout=10, cwd=str(root),
                encoding='utf-8', errors='replace'
            )
            if conflict_result.returncode == 1 and conflict_result.stdout.strip():
                conflict_lines = [
                    line for line in conflict_result.stdout.strip().split('\n')
                    if did not in line and line.strip().startswith(('D-', ' '))
                ]
                if conflict_lines:
                    message += f" | L2-CONFLICT {did}: {'; '.join(l.strip() for l in conflict_lines[:3])}"

        subprocess.run(
            ['python', kb_script, 'generate-summary'],
            capture_output=True, timeout=15, cwd=str(root), env=env
        )
        message += " | active_rules_summary.md regenerated"

        subprocess.run(
            ['python', kb_script, 'generate-index'],
            capture_output=True, timeout=15, cwd=str(root), env=env
        )
        message += " | _index.md regenerated"
    except Exception:
        pass

    return True, message
