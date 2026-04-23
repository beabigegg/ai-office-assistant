"""Validator: check_backlog_sync
Verifies that backlog.db was updated after a task completion for project_management type projects.
For knowledge-type projects, always passes.
"""
from pathlib import Path
import sys

WORKFLOWS_DIR = Path(__file__).resolve().parents[1]
if str(WORKFLOWS_DIR) not in sys.path:
    sys.path.insert(0, str(WORKFLOWS_DIR))

from project_ref import normalize_project_id, project_db_dir, project_workspace


def validate(context: dict) -> tuple:
    root = Path(context.get('root', Path(__file__).resolve().parents[3]))
    project = normalize_project_id(context.get('project', ''))
    params = context.get('params', {})
    required_for_type = params.get('required_for_type', 'project_management')

    if not project:
        return True, "no project context, skip backlog sync check"

    # Detect project type from project_state.md
    state_file = project_workspace(root, project) / 'project_state.md'
    if state_file.exists():
        content = state_file.read_text(encoding='utf-8', errors='replace')
        is_pm = (
            'project_type: project_management' in content
            or '<!-- type: project_management' in content
        )
    else:
        is_pm = False

    if required_for_type == 'project_management' and not is_pm:
        return True, f"project '{project}' is knowledge-type, backlog sync not required"

    # Check backlog.db exists
    backlog_db = project_db_dir(root, project) / 'backlog.db'
    if not backlog_db.exists():
        if is_pm:
            return True, (
                f"WARN: project '{project}' is project_management type but has no backlog.db yet. "
                f"Run: bash shared/tools/conda-python.sh shared/tools/backlog.py "
                f"--project {project} add --title '...' to initialize."
            )
        return True, "no backlog.db, skip"

    # Check backlog.db was recently updated (within 1 hour)
    import time
    age = time.time() - backlog_db.stat().st_mtime
    if age > 3600:
        return True, (
            f"WARN: backlog.db last updated {int(age/60)}m ago. "
            f"Did you update action items? Run: bash shared/tools/conda-python.sh "
            f"shared/tools/backlog.py --project {project} list --status open"
        )

    return True, f"backlog.db updated {int(age)}s ago"
