"""Validator: check_project_state
Verifies that project_state.md was recently modified (within max_age_seconds).
Also creates a single-version backup (.project_state.prev.md) before validation.
"""
import shutil
import time
from pathlib import Path


def validate(context: dict) -> tuple:
    _default_root = Path(__file__).resolve().parent.parent.parent.parent
    root = Path(context.get('root', _default_root))
    project = context.get('project', '')
    params = context.get('params', {})
    max_age = params.get('max_age_seconds', 600)

    # Find project_state.md
    if project:
        candidates = [
            root / 'projects' / project / 'workspace' / 'project_state.md',
            root / project / 'workspace' / 'project_state.md',
        ]
    else:
        candidates = list(root.glob('projects/*/workspace/project_state.md'))

    target = None
    for c in candidates:
        if c.exists():
            target = c
            break

    if target is None:
        return False, "project_state.md not found for any project"

    # Auto-backup before validation (single version, overwritten each time)
    backup_path = target.parent / '.project_state.prev.md'
    try:
        shutil.copy2(str(target), str(backup_path))
    except OSError:
        pass  # best-effort backup, don't block on failure

    mtime = target.stat().st_mtime
    age = time.time() - mtime
    age_str = f"{int(age)}s" if age < 60 else f"{int(age/60)}m {int(age%60)}s"

    if age <= max_age:
        return True, f"updated {age_str} ago ({target.name})"
    else:
        return False, f"last modified {age_str} ago (threshold: {max_age}s) — {target}"
