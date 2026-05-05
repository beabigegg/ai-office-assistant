"""Sidecar JSON envelope helper for AI Office tools.

A "sidecar" is a small machine-readable JSON file written alongside a
human-facing artifact (typically Markdown). It carries the *semantic
values* that downstream validators need, so they no longer have to
regex-parse Markdown and risk drifting from the producer's definitions.

Usage (in a tool):
    from sidecar import Sidecar

    sc = Sidecar("kb.py:generate-summary", project="my-project")
    sc.set_input("db_path", str(db_path))
    sc.set_output("active_decision_count", 0)
    sc.set_stat("superseded_decisions", 13)
    sc.write(
        Path("projects/my-project/workspace/.active_rules_summary.json"),
        paired_md=Path("projects/my-project/workspace/.active_rules_summary.md"),
    )
    print(sc.stdout_hint())  # -> "Sidecar: projects/..."
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0"


class Sidecar:
    """Builder + atomic writer for a sidecar JSON envelope."""

    def __init__(self, tool: str, project: str | None = None):
        self._tool = tool
        self._project = project
        self._outputs: dict[str, Any] = {}
        self._stats: dict[str, Any] = {}
        self._inputs: dict[str, Any] = {}
        self._path: Path | None = None

    def set_input(self, key: str, value: Any) -> "Sidecar":
        self._inputs[key] = value
        return self

    def set_output(self, key: str, value: Any) -> "Sidecar":
        self._outputs[key] = value
        return self

    def set_stat(self, key: str, value: Any) -> "Sidecar":
        self._stats[key] = value
        return self

    def write(self, path: Path, paired_md: Path | None = None) -> Path:
        """Write sidecar atomically. Returns the path written."""
        path = Path(path)
        data: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "tool": self._tool,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generator_pid": os.getpid(),
        }
        if self._project:
            data["project"] = self._project
        if self._inputs:
            data["inputs"] = self._inputs
        data["outputs"] = self._outputs
        if self._stats:
            data["stats"] = self._stats
        if paired_md is not None:
            paired_md = Path(paired_md)
            if paired_md.exists():
                data["checksums"] = {
                    "markdown_path": str(paired_md),
                    "markdown_sha256": _sha256(paired_md),
                    "markdown_size": paired_md.stat().st_size,
                }
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(tmp, path)
        self._path = path
        return path

    def stdout_hint(self) -> str:
        return f"Sidecar: {self._path}"


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
