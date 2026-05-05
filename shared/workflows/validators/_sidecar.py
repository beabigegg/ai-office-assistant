"""Sidecar reader helper for validators.

Validators should read semantic values from the producer's sidecar JSON
rather than re-parsing Markdown. This keeps a single source of truth and
removes the regex/Markdown drift class of bugs.

Usage in a validator:
    from ._sidecar import read_sidecar, strict_require

    sc = read_sidecar(context, expected_tool="kb.py:generate-summary")
    ok, msg = strict_require(
        sc, context,
        node_name="load_active_context",
        regen_cmd=(
            "bash shared/tools/conda-python.sh shared/tools/kb.py "
            "generate-summary --project <PID> --output projects/<PID>/"
            "workspace/.active_rules_summary.md"
        ),
        expected_tool="kb.py:generate-summary",
    )
    if not ok:
        return {"status": "FAIL", "message": msg}
    count = sc["outputs"]["active_decision_count"]
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_sidecar(
    context: dict[str, Any],
    expected_tool: str | None = None,
) -> dict[str, Any] | None:
    """Read the sidecar referenced by ``context`` outputs.

    Returns ``None`` when:
      * no sidecar path was provided,
      * the file does not exist,
      * the file is unreadable / not JSON,
      * an ``expected_tool`` was given and the sidecar was produced by a
        different tool.
    """
    outputs = context.get("outputs") or {}
    raw = outputs.get("_sidecar_path") or outputs.get("sidecar_path")
    if not raw:
        return None
    root_raw = context.get("root")
    if root_raw is None:
        # validators/_sidecar.py -> validators -> workflows -> shared -> repo
        root = Path(__file__).resolve().parents[3]
    else:
        root = Path(root_raw)
    p = Path(raw)
    if not p.is_absolute():
        p = (root / p).resolve()
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if expected_tool and data.get("tool") != expected_tool:
        return None
    return data


def strict_require(
    sidecar: dict[str, Any] | None,
    context: dict[str, Any],
    *,
    node_name: str,
    regen_cmd: str,
    expected_tool: str | None = None,
) -> tuple[bool, str]:
    """Strict mode: missing sidecar = FAIL with an actionable message.

    Returns ``(ok, message)``. When ``ok`` is ``False`` the message is
    ready to surface to the caller — it includes the missing path, the
    full regeneration command, and a pointer to ``/evolve``.
    """
    outputs = context.get("outputs") or {}
    sidecar_path = (
        outputs.get("_sidecar_path")
        or outputs.get("sidecar_path")
        or "(not provided)"
    )
    if sidecar is None:
        return False, (
            f"[FAIL] Node '{node_name}': sidecar JSON not found at "
            f"{sidecar_path!r}.\n"
            f"  -> Regenerate with:\n"
            f"     {regen_cmd}\n"
            f"  -> Then re-complete this node with --sidecar <path>.\n"
            f"  -> If the command itself fails, run /evolve to call the "
            f"architect agent."
        )
    if expected_tool and sidecar.get("tool") != expected_tool:
        return False, (
            f"[FAIL] Node '{node_name}': sidecar tool mismatch. "
            f"Expected {expected_tool!r}, got {sidecar.get('tool')!r}.\n"
            f"  -> Regenerate with:\n"
            f"     {regen_cmd}\n"
            f"  -> If the command itself fails, run /evolve to call the "
            f"architect agent."
        )
    return True, "ok"
