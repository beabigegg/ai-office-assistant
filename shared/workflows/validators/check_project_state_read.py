"""Validator: check_project_state_read (W1-5, sidecar-aware).

Ensures the Leader actually read the active project's project_state.md.
When a ``kb.py:project-state-index`` sidecar is provided, also verifies
the file's sha256 matches what the indexer recorded — catches the case
where the file was modified between indexing and node completion.
"""
import hashlib
import sys as _sys
from pathlib import Path

from ._sidecar import read_sidecar

# Tool-name constants live in shared/tools/sidecar_tools.py.
_TOOLS_DIR = str(Path(__file__).resolve().parent.parent.parent / "tools")
if _TOOLS_DIR not in _sys.path:
    _sys.path.insert(0, _TOOLS_DIR)
from sidecar_tools import TOOL_KB_PROJECT_STATE_INDEX  # noqa: E402


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


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

    expected = (
        (root / "projects" / project / "workspace" / "project_state.md").resolve()
        if project else None
    )

    if not candidate.exists():
        return False, f"state_path does not exist: {candidate}"
    if candidate.name != "project_state.md":
        return False, f"state_path must point to project_state.md: {candidate}"
    if expected is not None and candidate != expected:
        return False, f"state_path must match active project workspace: {expected}"

    # Optional sidecar checksum cross-check.
    sc = read_sidecar(context, expected_tool=TOOL_KB_PROJECT_STATE_INDEX)
    if sc is not None:
        checksums = sc.get("checksums") or {}
        expected_sha = checksums.get("markdown_sha256")
        if expected_sha:
            actual_sha = _sha256(candidate)
            if actual_sha != expected_sha:
                regen_cmd = (
                    "bash shared/tools/conda-python.sh shared/tools/kb.py "
                    f"project-state-index --project {project or '<PROJECT_ID>'}"
                )
                return False, (
                    f"[FAIL] project_state.md checksum mismatch — file changed "
                    f"after .project_state.json was written.\n"
                    f"  -> Regenerate with:\n     {regen_cmd}\n"
                    "  -> If the command itself fails, run /evolve to call the architect agent."
                )

    return True, f"project_state read: {candidate.relative_to(root)}"
