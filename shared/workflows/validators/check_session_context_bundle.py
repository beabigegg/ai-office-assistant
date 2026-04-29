"""Validator: check_session_context_bundle.

Ensures session_start generated a fresh bundle that combines decisions,
learnings, and open questions for the active project.
"""
from datetime import datetime, timezone
from pathlib import Path
import re


def validate(context: dict) -> tuple:
    _default_root = Path(__file__).resolve().parent.parent.parent.parent
    root = Path(context.get("root", _default_root))
    outputs = context.get("outputs", {}) or {}
    params = context.get("params", {}) or {}
    project = str(context.get("project", "") or "").strip()
    max_age = int(params.get("max_age_seconds", 600))

    raw_path = str(outputs.get("bundle_path", "")).strip()
    if not raw_path:
        return False, "bundle_path missing from outputs"

    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = (root / candidate).resolve()

    expected_dir = (root / "projects" / project / "workspace").resolve()
    try:
        candidate.relative_to(expected_dir)
    except ValueError:
        return False, f"bundle_path must live under {expected_dir}, got {candidate}"

    if not candidate.exists():
        return False, f"bundle_path does not exist: {candidate}"

    mtime = datetime.fromtimestamp(candidate.stat().st_mtime, tz=timezone.utc)
    age_sec = (datetime.now(timezone.utc) - mtime).total_seconds()
    if age_sec > max_age:
        return False, f"session context bundle is stale ({int(age_sec)}s old, max {max_age}s)"

    text = candidate.read_text(encoding="utf-8")
    for heading in ("## Active Decisions", "## Recent Learnings", "## Open Questions", "## Active Rules"):
        if heading not in text:
            return False, f"bundle missing section: {heading}"

    def _read_int(name: str) -> int:
        raw = outputs.get(name)
        if raw is None:
            raise ValueError(f"{name} missing from outputs")
        return int(raw)

    try:
        decision_count = _read_int("bundle_decision_count")
        learning_count = _read_int("bundle_learning_count")
        question_count = _read_int("bundle_open_question_count")
    except ValueError as exc:
        return False, str(exc)
    except (TypeError, ValueError):
        return False, "bundle counts must all be integers"

    if min(decision_count, learning_count, question_count) < 0:
        return False, "bundle counts must be >= 0"

    file_decisions = len(re.findall(r"^- \*\*D-\d{3}\*\*", text, re.MULTILINE))
    file_learnings = len(re.findall(r"^- \*\*[^*]+-L\d+\*\*", text, re.MULTILINE))
    question_block = re.search(r"## Open Questions\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
    file_questions = 0
    if question_block:
        file_questions = len(re.findall(r"^- ", question_block.group(1), re.MULTILINE))
        if "(none)" in question_block.group(1):
            file_questions = 0

    if decision_count != file_decisions:
        return False, f"bundle_decision_count={decision_count} but file shows {file_decisions}"
    if learning_count != file_learnings:
        return False, f"bundle_learning_count={learning_count} but file shows {file_learnings}"
    if question_count != file_questions:
        return False, f"bundle_open_question_count={question_count} but file shows {file_questions}"

    return True, (
        f"session context bundle loaded: {decision_count} decisions, "
        f"{learning_count} learnings, {question_count} open questions"
    )
