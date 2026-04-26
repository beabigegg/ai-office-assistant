"""PreToolUse hook: guard governed agent/skill definition writes."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STATE_PATH = REPO_ROOT / "shared" / "workflows" / "state" / "current.json"
GOVERNED_PATH_RE = re.compile(
    r"[/\\]\.claude[/\\](agents[/\\][^/\\]+\.md|skills-on-demand[/\\][^/\\]+[/\\](SKILL\.md|\.skill\.yaml))$",
    re.IGNORECASE,
)


def _active_workflows() -> list[str]:
    if not STATE_PATH.exists():
        return []
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    return [
        str(inst.get("workflow", "")).strip()
        for inst in (state.get("active", {}) or {}).values()
        if str(inst.get("workflow", "")).strip()
    ]


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_input = data.get("tool_input", {}) or {}
    file_path = ""
    if isinstance(tool_input, dict):
        file_path = str(tool_input.get("file_path", "") or "")
    elif isinstance(tool_input, str):
        file_path = tool_input

    if not file_path:
        sys.exit(0)

    normalized = file_path.replace("\\", "/")
    if not GOVERNED_PATH_RE.search(normalized.replace("/", "\\")):
        sys.exit(0)

    if os.environ.get("AI_OFFICE_ALLOW_GOVERNED_WRITE") == "1":
        sys.exit(0)

    workflows = set(_active_workflows())
    if "skill_self_learning" in workflows:
        print(
            "BLOCKED: skill_self_learning may not create or modify SKILL.md/.skill.yaml/agent definition files.",
            file=sys.stderr,
        )
        sys.exit(2)

    print(
        "BLOCKED: governed agent/skill definition write. Route the lifecycle change through architect "
        "or use an explicit approved override (AI_OFFICE_ALLOW_GOVERNED_WRITE=1).",
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
