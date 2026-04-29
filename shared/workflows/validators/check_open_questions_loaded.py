"""Validator: check_open_questions_loaded.

Ensures session_start explicitly loaded the project's unresolved questions instead
of silently skipping the uncertainty surface.
"""
from pathlib import Path
import re


def _extract_open_question_lines(text: str) -> list[str]:
    match = re.search(r"## 未解問題\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
    if not match:
        return []

    lines = []
    for raw_line in match.group(1).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("<!--"):
            continue
        if "（無）" in line or line.lower() in {"none", "(none)"}:
            return []
        if re.match(r"^[-*]\s+", line):
            lines.append(re.sub(r"^[-*]\s+", "", line))
            continue
        if re.match(r"^\d+\.\s+", line):
            lines.append(re.sub(r"^\d+\.\s+", "", line))
            continue
        lines.append(line)
    return lines


def validate(context: dict) -> tuple:
    _default_root = Path(__file__).resolve().parent.parent.parent.parent
    root = Path(context.get("root", _default_root))
    outputs = context.get("outputs", {}) or {}
    project = str(context.get("project", "") or "").strip()

    raw_count = outputs.get("open_question_count")
    if raw_count is None:
        return False, "open_question_count missing from outputs"
    try:
        reported = int(raw_count)
    except (TypeError, ValueError):
        return False, f"open_question_count must be an integer, got {raw_count!r}"
    if reported < 0:
        return False, f"open_question_count must be >= 0, got {reported}"

    summary = str(outputs.get("open_questions_summary", "") or "").strip()
    if not summary:
        return False, "open_questions_summary missing from outputs"

    state_path = root / "projects" / project / "workspace" / "project_state.md"
    if not state_path.exists():
        return False, f"project_state.md not found: {state_path}"

    file_questions = _extract_open_question_lines(state_path.read_text(encoding="utf-8"))
    file_count = len(file_questions)

    if file_count > 0 and reported == 0:
        return False, (
            f"project_state.md contains {file_count} open question(s) but output count is 0"
        )
    if file_count == 0 and reported == 0 and summary.lower() not in {"(none)", "none", "no open questions"}:
        return False, "when open_question_count=0, open_questions_summary must explicitly say none"
    if reported > 0 and summary.lower() in {"(none)", "none", "no open questions"}:
        return False, "open_questions_summary contradicts open_question_count>0"

    return True, f"open questions loaded: reported={reported}, project_state={file_count}"
