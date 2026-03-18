"""Validator: check_project_state
Verifies that project_state.md was recently modified (within max_age_seconds).
"""
import time
from pathlib import Path


def validate(context: dict) -> tuple:
    root = Path(context.get('root', r'D:\AI_test'))
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

    mtime = target.stat().st_mtime
    age = time.time() - mtime
    age_str = f"{int(age)}s" if age < 60 else f"{int(age/60)}m {int(age%60)}s"

    if age <= max_age:
        return True, f"updated {age_str} ago ({target.name})"
    else:
        return False, f"last modified {age_str} ago (threshold: {max_age}s) — {target}"
