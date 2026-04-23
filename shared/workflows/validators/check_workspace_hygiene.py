"""Validator: check_workspace_hygiene
Enforces CLAUDE.md §8 零散落原則 — temp files must not accumulate in workspace/.
Soft limit: 5 (WARN); Hard limit: 15 (FAIL).
"""
from pathlib import Path


def validate(context: dict) -> tuple:
    root = Path(context.get('root', Path(__file__).resolve().parents[3]))
    project = context.get('project', '')
    if not project:
        return True, "no project context, skip hygiene check"

    ws = root / 'projects' / project / 'workspace'
    if not ws.exists():
        return True, "no workspace dir, skip"

    stray = []
    for pat in ('_*.txt', 'tmp_*.txt', '_*.json', 'tmp_*.py', '_*.csv'):
        stray.extend(ws.glob(pat))

    count = len(stray)
    if count > 15:
        samples = [p.name for p in sorted(stray)[:5]]
        return False, (
            f"HYGIENE FAIL: {count} temp files in workspace/ (hard limit 15). "
            f"Examples: {samples}. Clean per CLAUDE.md §8: move to memos/_archive/ or delete."
        )
    if count > 5:
        samples = [p.name for p in sorted(stray)[:3]]
        return True, (
            f"HYGIENE WARN: {count} temp files (soft limit 5). "
            f"Examples: {samples}. Consider cleanup."
        )
    return True, f"workspace clean ({count} temp files)"
