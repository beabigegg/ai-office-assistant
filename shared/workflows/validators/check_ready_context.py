"""Validator: check_ready_context (W1-5, sidecar-aware).

The ready report must be internally consistent with the upstream nodes:
the bundle path it cites must match what build_session_context produced
(sidecar-authoritative), and risk_status must agree with the open
question count.

risk_status rules:
  * "clear"           -> count must be 0
  * "open_questions"  -> count must be > 0
  * "mixed"           -> open questions plus another risk surface
                         (combination of risks; count may be 0 or > 0
                         but the Leader is asserting another risk).
"""
from pathlib import Path


def _sidecar_outputs_from_node(node_state: dict, root: Path) -> dict:
    """Read the sidecar referenced by ``node_state.outputs._sidecar_path``."""
    import json
    outputs = (node_state or {}).get("outputs") or {}
    raw = outputs.get("_sidecar_path") or outputs.get("sidecar_path")
    if not raw:
        return {}
    p = Path(raw)
    if not p.is_absolute():
        p = (root / p).resolve()
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data.get("outputs") or {}


def validate(context: dict) -> tuple:
    _default_root = Path(__file__).resolve().parent.parent.parent.parent
    root = Path(context.get("root", _default_root))
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
        return False, (
            f"reported_open_question_count must be an integer, "
            f"got {reported_open_raw!r}"
        )

    bundle_node = nodes.get("build_session_context", {}) or {}
    bundle_outputs = bundle_node.get("outputs", {}) or {}
    question_node = nodes.get("flag_open_questions", {}) or {}
    question_outputs = question_node.get("outputs", {}) or {}

    # Prefer sidecar-authoritative bundle path/count when available.
    bundle_sc_outputs = _sidecar_outputs_from_node(bundle_node, root)
    expected_bundle_raw = (
        str(bundle_sc_outputs.get("bundle_path") or "").strip()
        or str(bundle_outputs.get("bundle_path", "") or "").strip()
    )
    if expected_bundle_raw:
        def _norm(p: str) -> Path:
            pp = Path(p)
            if not pp.is_absolute():
                pp = (root / pp).resolve()
            else:
                pp = pp.resolve()
            return pp
        if _norm(bundle_path) != _norm(expected_bundle_raw):
            return False, (
                f"[FAIL] context_bundle_path must match build_session_context."
                f"bundle_path. expected={expected_bundle_raw!r}, got={bundle_path!r}"
            )

    # Sidecar-authoritative open-question count.
    question_sc_outputs = _sidecar_outputs_from_node(question_node, root)
    expected_open = None
    classification = ""
    if question_sc_outputs:
        try:
            expected_open = int(question_sc_outputs.get("open_question_count", 0) or 0)
        except (TypeError, ValueError):
            expected_open = None
        classification = str(
            question_sc_outputs.get("open_question_classification") or ""
        )
        if classification in {"placeholder", "empty", "missing"}:
            expected_open = 0
    if expected_open is None:
        try:
            expected_open = int(question_outputs.get("open_question_count", 0) or 0)
        except (TypeError, ValueError):
            expected_open = 0

    if reported_open != expected_open:
        return False, (
            f"[FAIL] reported_open_question_count={reported_open} does not "
            f"match flag_open_questions count={expected_open} "
            f"(classification={classification or 'unknown'}). "
            "The flag_open_questions sidecar is authoritative."
        )

    # Status / count consistency.
    if risk_status == "clear" and expected_open != 0:
        return False, (
            f"[FAIL] risk_status=clear requires open_question_count==0, "
            f"got {expected_open}."
        )
    if risk_status == "open_questions" and expected_open <= 0:
        return False, (
            "[FAIL] risk_status=open_questions requires "
            "open_question_count>0."
        )
    # 'mixed' is allowed in either direction — Leader is asserting an
    # additional risk surface beyond open questions; we don't second-guess.

    return True, (
        f"ready context validated: risk_status={risk_status}, "
        f"open_questions={expected_open}"
    )
