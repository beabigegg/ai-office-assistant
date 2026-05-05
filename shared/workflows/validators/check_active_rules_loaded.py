"""Validator: check_active_rules_loaded (W1-5, sidecar-first).

Single source of truth for *active decisions per project* is the
``kb.py:generate-summary`` sidecar. Validators must NOT regex-parse the
generated Markdown to recompute counts — the sidecar is authoritative.

Checks:
  1. Sidecar JSON is provided and was written by kb.py:generate-summary.
  2. The Markdown summary file still exists, lives under the project
     workspace, and is not stale (<= max_age_seconds).
  3. The summary's bytes match the checksum recorded in the sidecar
     (catches manual edits between regen and validate).
  4. The Leader-reported active_decision_count (if any) matches the
     sidecar's authoritative count.
"""
from datetime import datetime, timezone
from pathlib import Path

from ._sidecar import read_sidecar, strict_require


def _sha256(p: Path) -> str:
    import hashlib
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
        "bash shared/tools/conda-python.sh shared/tools/kb.py generate-summary "
        f"--project {project or '<PROJECT_ID>'} "
        f"--output projects/{project or '<PROJECT_ID>'}/workspace/.active_rules_summary.md"
    )

    sc = read_sidecar(context, expected_tool="kb.py:generate-summary")
    ok, msg = strict_require(
        sc, context,
        node_name="load_active_context",
        regen_cmd=regen_cmd,
        expected_tool="kb.py:generate-summary",
    )
    if not ok:
        return False, msg

    sc_outputs = sc.get("outputs") or {}
    summary_path_raw = str(sc_outputs.get("summary_path") or "").strip()
    if not summary_path_raw:
        return False, (
            "[FAIL] sidecar is missing outputs.summary_path. "
            f"Regenerate with:\n     {regen_cmd}\n"
            "  -> If the command itself fails, run /evolve to call the architect agent."
        )

    md_path = Path(summary_path_raw)
    if not md_path.is_absolute():
        md_path = (root / md_path).resolve()

    if project:
        expected_dir = (root / "projects" / project / "workspace").resolve()
        try:
            md_path.relative_to(expected_dir)
        except ValueError:
            return False, (
                f"[FAIL] summary_path must live under {expected_dir}, got {md_path}. "
                f"Regenerate with:\n     {regen_cmd}"
            )

    if not md_path.exists():
        return False, (
            f"[FAIL] summary_path does not exist: {md_path}.\n"
            f"  -> Regenerate with:\n     {regen_cmd}\n"
            "  -> If the command itself fails, run /evolve to call the architect agent."
        )

    mtime = datetime.fromtimestamp(md_path.stat().st_mtime, tz=timezone.utc)
    age_sec = (datetime.now(timezone.utc) - mtime).total_seconds()
    if age_sec > max_age:
        return False, (
            f"[FAIL] active_rules_summary is stale ({int(age_sec)}s old, "
            f"max {max_age}s).\n"
            f"  -> Regenerate with:\n     {regen_cmd}\n"
            "  -> If the command itself fails, run /evolve to call the architect agent."
        )

    # Tamper / drift detection via checksum (when sidecar recorded one).
    checksums = sc.get("checksums") or {}
    expected_sha = checksums.get("markdown_sha256")
    if expected_sha:
        actual_sha = _sha256(md_path)
        if actual_sha != expected_sha:
            return False, (
                f"[FAIL] summary file checksum mismatch — Markdown was modified "
                f"after the sidecar was written.\n"
                f"  -> Regenerate with:\n     {regen_cmd}\n"
                "  -> If the command itself fails, run /evolve to call the architect agent."
            )

    sidecar_count = sc_outputs.get("active_decision_count")
    if not isinstance(sidecar_count, int) or sidecar_count < 0:
        return False, (
            f"[FAIL] sidecar outputs.active_decision_count is invalid: "
            f"{sidecar_count!r}. Regenerate with:\n     {regen_cmd}"
        )

    # If the Leader also reported a count in --outputs, demand it agrees.
    raw_reported = outputs.get("active_decision_count")
    if raw_reported is not None and raw_reported != sidecar_count:
        try:
            reported = int(raw_reported)
        except (TypeError, ValueError):
            return False, (
                f"[FAIL] active_decision_count must be an integer, got "
                f"{raw_reported!r}"
            )
        if reported != sidecar_count:
            return False, (
                f"[FAIL] active_decision_count={reported} (Leader-reported) "
                f"disagrees with sidecar={sidecar_count}. The sidecar is "
                f"authoritative — re-complete with the sidecar value."
            )

    return True, (
        f"active rules loaded: {sidecar_count} decisions "
        f"(file age {int(age_sec)}s, sidecar {context.get('outputs', {}).get('_sidecar_path')})"
    )
