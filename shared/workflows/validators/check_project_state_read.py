"""Validator: check_project_state_read
Ensures session_start explicitly proves which project_state.md was read.
"""
from pathlib import Path


def validate(context: dict) -> tuple:
    _default_root = Path(__file__).resolve().parent.parent.parent.parent
    root = Path(context.get("root", _default_root))
    outputs = context.get("outputs", {}) or {}
    project = str(context.get("project", "") or "").strip()

    raw_path = str(outputs.get("state_path", "")).strip()
    if not raw_path:
        return False, "state_path missing from outputs"

    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = (root / candidate).resolve()

    expected = (root / "projects" / project / "workspace" / "project_state.md").resolve() if project else None

    if not candidate.exists():
        return False, f"state_path does not exist: {candidate}"
    if candidate.name != "project_state.md":
        return False, f"state_path must point to project_state.md: {candidate}"
    if expected is not None and candidate != expected:
        return False, f"state_path must match active project workspace: {expected}"

    return True, f"project_state read: {candidate.relative_to(root)}"
