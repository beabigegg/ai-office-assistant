"""Validator: check_open_questions_loaded (W1-5, sidecar-first).

Authoritative source: ``kb.py:project-state-index`` sidecar at
``projects/<project>/workspace/.project_state.json``.

The sidecar reports both the count and a *classification* so that
'(無)' / 'none' / 'no open questions' are normalised to count=0
without the validator having to re-implement the placeholder list.
"""
from pathlib import Path

from ._sidecar import read_sidecar, strict_require


def validate(context: dict) -> tuple:
    _default_root = Path(__file__).resolve().parent.parent.parent.parent
    root = Path(context.get("root", _default_root))
    outputs = context.get("outputs", {}) or {}
    project = str(context.get("project", "") or "").strip()

    regen_cmd = (
        "bash shared/tools/conda-python.sh shared/tools/kb.py project-state-index "
        f"--project {project or '<PROJECT_ID>'}"
    )

    sc = read_sidecar(context, expected_tool="kb.py:project-state-index")
    ok, msg = strict_require(
        sc, context,
        node_name="flag_open_questions",
        regen_cmd=regen_cmd,
        expected_tool="kb.py:project-state-index",
    )
    if not ok:
        return False, msg

    sc_outputs = sc.get("outputs") or {}
    classification = str(sc_outputs.get("open_question_classification") or "").strip()
    sidecar_count = sc_outputs.get("open_question_count")
    if not isinstance(sidecar_count, int) or sidecar_count < 0:
        return False, (
            f"[FAIL] sidecar outputs.open_question_count is invalid: "
            f"{sidecar_count!r}.\n  -> Regenerate with:\n     {regen_cmd}"
        )

    # Placeholder / empty / missing => the count MUST be 0 regardless of body.
    if classification in {"placeholder", "empty", "missing"}:
        sidecar_count = 0

    # Cross-check Leader-reported count if provided.
    raw_reported = outputs.get("open_question_count")
    if raw_reported is not None:
        try:
            reported = int(raw_reported)
        except (TypeError, ValueError):
            return False, (
                f"[FAIL] open_question_count must be an integer, got "
                f"{raw_reported!r}"
            )
        if reported != sidecar_count:
            return False, (
                f"[FAIL] open_question_count={reported} (Leader-reported) "
                f"disagrees with sidecar={sidecar_count} "
                f"(classification={classification or 'unknown'}). "
                f"The sidecar is authoritative — re-complete with the sidecar value.\n"
                f"  -> If the sidecar is wrong, regenerate it:\n     {regen_cmd}"
            )

    summary = str(outputs.get("open_questions_summary", "") or "").strip()
    if summary:
        none_markers = {"(none)", "none", "no open questions"}
        if sidecar_count == 0 and summary.lower() not in none_markers:
            return False, (
                f"[FAIL] when open_question_count=0, open_questions_summary "
                f"must explicitly say none (got: {summary!r})."
            )
        if sidecar_count > 0 and summary.lower() in none_markers:
            return False, (
                "[FAIL] open_questions_summary contradicts open_question_count>0"
            )

    # The sidecar's checksum proves the .md hasn't drifted. Surface as info.
    return True, (
        f"open questions loaded: count={sidecar_count} "
        f"(classification={classification or 'unknown'})"
    )
