"""Validator: check_active_rules_loaded

Ensures session_start actually generated and read a fresh project-scoped
active_rules_summary, so Tier-3 rewrites and follow-up tasks have the active
D-NNN ruleset in context.

Checks:
  1. outputs.summary_path is provided and resolves under the active project workspace.
  2. The summary file exists.
  3. The summary file mtime is no older than `max_age_seconds` (default 600s)
     — proves it was regenerated for THIS session, not stale from a prior run.
  4. outputs.active_decision_count is a non-negative integer that does not
     exceed the total unique D-NNN tokens present in the file. We do NOT
     require an exact match because the summary mixes multiple sections
     (active per-project decisions, superseded crosslinks, ECR rules, etc.);
     the reported count is meant to be the active-for-this-project subset.
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

    raw_path = str(outputs.get("summary_path", "")).strip()
    if not raw_path:
        return False, "summary_path missing from outputs"

    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = (root / candidate).resolve()

    if project:
        expected_dir = (root / "projects" / project / "workspace").resolve()
        try:
            candidate.relative_to(expected_dir)
        except ValueError:
            return False, (
                f"summary_path must live under {expected_dir}, got {candidate}"
            )

    if not candidate.exists():
        return False, f"summary_path does not exist: {candidate}"

    mtime = datetime.fromtimestamp(candidate.stat().st_mtime, tz=timezone.utc)
    age_sec = (datetime.now(timezone.utc) - mtime).total_seconds()
    if age_sec > max_age:
        return False, (
            f"active_rules_summary is stale ({int(age_sec)}s old, max {max_age}s). "
            "Re-run kb.py generate-summary --project ... to refresh before continuing."
        )

    raw_count = outputs.get("active_decision_count")
    if raw_count is None:
        return False, "active_decision_count missing from outputs"
    try:
        reported = int(raw_count)
    except (TypeError, ValueError):
        return False, f"active_decision_count must be an integer, got {raw_count!r}"
    if reported < 0:
        return False, f"active_decision_count must be >= 0, got {reported}"

    try:
        text = candidate.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return False, f"cannot read summary file: {e}"

    file_count = len(set(re.findall(r"\bD-\d{3}\b", text)))
    if reported > file_count:
        return False, (
            f"active_decision_count={reported} exceeds unique D-NNN in file ({file_count}). "
            "Recount and re-complete."
        )
    if file_count > 0 and reported == 0:
        return False, (
            f"active_decision_count=0 but file contains {file_count} D-NNN tokens. "
            "Did you actually read the summary?"
        )

    return True, (
        f"active rules loaded: {reported} decisions, "
        f"file age {int(age_sec)}s ({candidate.relative_to(root)})"
    )
