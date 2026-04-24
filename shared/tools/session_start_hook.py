"""UserPromptSubmit hook: inject session_start reminder when appropriate."""
import json
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = ROOT / "shared" / "workflows"
STATE_FILE = WORKFLOWS_DIR / "state" / "current.json"
SESSION_COOLDOWN = 1800  # 30 minutes — don't re-remind within same session

if str(WORKFLOWS_DIR) not in sys.path:
    sys.path.insert(0, str(WORKFLOWS_DIR))

from project_ref import normalize_project_id  # noqa: E402


def _load_state() -> dict:
    try:
        with STATE_FILE.open(encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def main():
    try:
        hook_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, OSError):
        sys.exit(0)

    state = _load_state()
    active = state.get("active", {})

    # Already has an active workflow — no reminder needed
    if active:
        sys.exit(0)

    # Check if session_start was recently completed (within cooldown)
    last_completed = state.get("last_workflow_completed_at", "")
    if last_completed:
        try:
            from datetime import datetime, timezone
            completed_dt = datetime.fromisoformat(last_completed)
            age_seconds = (datetime.now(timezone.utc) - completed_dt).total_seconds()
            if age_seconds < SESSION_COOLDOWN:
                sys.exit(0)
        except (ValueError, ImportError):
            pass

    # Check counters: if session_start has run before, use shorter cooldown from history
    history = state.get("history", [])
    for entry in history[:5]:
        if entry.get("workflow") == "session_start":
            # session_start ran recently (in history) — skip reminder
            sys.exit(0)

    # No active workflow and no recent session_start — inject reminder
    cwd = hook_input.get("cwd", "") or os.getcwd()
    cwd_posix = cwd.replace("\\", "/")

    # Try to infer project path from cwd
    project_hint = "<project-id>"
    if "projects/" in cwd_posix:
        parts = cwd_posix.split("projects/")
        if len(parts) > 1:
            project_name = normalize_project_id(parts[1].split("/")[0])
            project_hint = project_name

    hint = (
        "[SESSION] 尚未啟動 session_start workflow。\n"
        f"建議執行：bash shared/tools/conda-python.sh shared/workflows/coordinator.py start session_start "
        f'--context \'{{"project":"{project_hint}"}}\'\n'
        f"PowerShell 可改用：powershell -ExecutionPolicy Bypass -File shared/tools/conda-python.ps1 "
        f"shared/workflows/coordinator.py start session_start --context '{{\"project\":\"{project_hint}\"}}'\n"
        "注意：`project` 必須是 canonical project id，例如 `ecr-ecn`，不可寫 `projects/ecr-ecn`。\n"
        "（若已在另一個 workflow 中，忽略此提示）"
    )
    result = {"additionalContext": hint}
    print(json.dumps(result))
    sys.exit(0)


if __name__ == "__main__":
    main()
