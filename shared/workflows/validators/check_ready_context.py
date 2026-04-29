"""Validator: check_ready_context.

Ensures the final session_start ready report references the generated context
bundle and does not hide unresolved questions behind a "clear" status.
"""


def validate(context: dict) -> tuple:
    outputs = context.get("outputs", {}) or {}
    instance = context.get("instance", {}) or {}
    nodes = instance.get("nodes", {}) or {}

    summary = str(outputs.get("ready_summary", "") or "").strip()
    risk_status = str(outputs.get("risk_status", "") or "").strip()
    bundle_path = str(outputs.get("context_bundle_path", "") or "").strip()
    reported_open_raw = outputs.get("reported_open_question_count")

    if not summary:
        return False, "ready_summary missing from outputs"
    if risk_status not in {"clear", "open_questions", "mixed"}:
        return False, "risk_status must be one of: clear, open_questions, mixed"
    if not bundle_path:
        return False, "context_bundle_path missing from outputs"

    try:
        reported_open = int(reported_open_raw)
    except (TypeError, ValueError):
        return False, f"reported_open_question_count must be an integer, got {reported_open_raw!r}"

    bundle_outputs = (nodes.get("build_session_context", {}) or {}).get("outputs", {}) or {}
    question_outputs = (nodes.get("flag_open_questions", {}) or {}).get("outputs", {}) or {}

    expected_bundle = str(bundle_outputs.get("bundle_path", "") or "").strip()
    if expected_bundle and bundle_path != expected_bundle:
        return False, "context_bundle_path must match build_session_context.bundle_path"

    try:
        expected_open = int(question_outputs.get("open_question_count", 0) or 0)
    except (TypeError, ValueError):
        expected_open = 0

    if reported_open != expected_open:
        return False, (
            f"reported_open_question_count={reported_open} does not match "
            f"flag_open_questions.open_question_count={expected_open}"
        )
    if expected_open > 0 and risk_status == "clear":
        return False, "risk_status cannot be clear when open questions exist"
    if expected_open == 0 and risk_status == "open_questions":
        return False, "risk_status=open_questions but no open questions were loaded"

    return True, f"ready context validated: risk_status={risk_status}, open_questions={expected_open}"
