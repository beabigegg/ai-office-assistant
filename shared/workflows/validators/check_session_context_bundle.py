"""Validator: check_session_context_bundle (W1-5, sidecar-first).

Authoritative source: ``kb.py:generate-session-context`` sidecar at
``projects/<project>/workspace/.session_context_bundle.json``.

The Markdown bundle still has to exist, live in the right workspace, be
fresh, and contain the four canonical sections — the sidecar adds the
semantic counts that no longer require regex parsing.
"""
import hashlib
import sys as _sys
from datetime import datetime, timezone
from pathlib import Path

from ._sidecar import read_sidecar, strict_require

# Tool-name constants live in shared/tools/sidecar_tools.py.
_TOOLS_DIR = str(Path(__file__).resolve().parent.parent.parent / "tools")
if _TOOLS_DIR not in _sys.path:
    _sys.path.insert(0, _TOOLS_DIR)
from sidecar_tools import TOOL_KB_GENERATE_SESSION_CONTEXT  # noqa: E402


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
    params = context.get("params", {}) or {}
    project = str(context.get("project", "") or "").strip()
    max_age = int(params.get("max_age_seconds", 600))

    regen_cmd = (
        "bash shared/tools/conda-python.sh shared/tools/kb.py "
        f"generate-session-context --project {project or '<PROJECT_ID>'} "
        f"--output projects/{project or '<PROJECT_ID>'}/workspace/.session_context_bundle.md"
    )

    sc = read_sidecar(context, expected_tool=TOOL_KB_GENERATE_SESSION_CONTEXT)
    ok, msg = strict_require(
        sc, context,
        node_name="build_session_context",
        regen_cmd=regen_cmd,
        expected_tool=TOOL_KB_GENERATE_SESSION_CONTEXT,
    )
    if not ok:
        return False, msg

    sc_outputs = sc.get("outputs") or {}
    bundle_path_raw = str(sc_outputs.get("bundle_path") or "").strip()
    if not bundle_path_raw:
        return False, (
            f"[FAIL] sidecar is missing outputs.bundle_path.\n"
            f"  -> Regenerate with:\n     {regen_cmd}"
        )

    candidate = Path(bundle_path_raw)
    if not candidate.is_absolute():
        candidate = (root / candidate).resolve()

    expected_dir = (root / "projects" / project / "workspace").resolve()
    try:
        candidate.relative_to(expected_dir)
    except ValueError:
        return False, (
            f"[FAIL] bundle_path must live under {expected_dir}, got {candidate}"
        )

    if not candidate.exists():
        return False, (
            f"[FAIL] bundle_path does not exist: {candidate}.\n"
            f"  -> Regenerate with:\n     {regen_cmd}"
        )

    mtime = datetime.fromtimestamp(candidate.stat().st_mtime, tz=timezone.utc)
    age_sec = (datetime.now(timezone.utc) - mtime).total_seconds()
    if age_sec > max_age:
        return False, (
            f"[FAIL] session context bundle is stale "
            f"({int(age_sec)}s old, max {max_age}s).\n"
            f"  -> Regenerate with:\n     {regen_cmd}"
        )

    text = candidate.read_text(encoding="utf-8")
    for heading in (
        "## Active Decisions",
        "## Recent Learnings",
        "## Open Questions",
        "## Active Rules",
    ):
        if heading not in text:
            return False, (
                f"[FAIL] bundle missing section: {heading}.\n"
                f"  -> Regenerate with:\n     {regen_cmd}"
            )

    # Tamper detection.
    checksums = sc.get("checksums") or {}
    expected_sha = checksums.get("markdown_sha256")
    if expected_sha and _sha256(candidate) != expected_sha:
        return False, (
            f"[FAIL] bundle checksum mismatch — Markdown was modified after "
            f"sidecar was written.\n  -> Regenerate with:\n     {regen_cmd}"
        )

    sc_open_q = sc_outputs.get("bundle_open_question_count")
    sc_decisions = sc_outputs.get("active_decision_count")
    sc_learnings = sc_outputs.get("recent_learning_count")
    if not isinstance(sc_open_q, int) or sc_open_q < 0:
        return False, (
            f"[FAIL] sidecar bundle_open_question_count invalid: {sc_open_q!r}"
        )

    # If the Leader supplied bundle_*_count outputs, demand they match the sidecar.
    def _check(name: str, sidecar_value):
        raw = outputs.get(name)
        if raw is None:
            return None
        try:
            reported = int(raw)
        except (TypeError, ValueError):
            return f"[FAIL] {name} must be an integer, got {raw!r}"
        if sidecar_value is not None and reported != sidecar_value:
            return (
                f"[FAIL] {name}={reported} (Leader-reported) disagrees with "
                f"sidecar={sidecar_value}. Sidecar is authoritative."
            )
        return None

    for name, sv in (
        ("bundle_open_question_count", sc_open_q),
        ("bundle_decision_count", sc_decisions),
        ("bundle_learning_count", sc_learnings),
    ):
        err = _check(name, sv)
        if err:
            return False, err

    return True, (
        f"session context bundle loaded: {sc_decisions or 0} decisions, "
        f"{sc_learnings or 0} learnings, {sc_open_q} open questions"
    )
