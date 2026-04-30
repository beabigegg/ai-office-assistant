#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:
    print("ERROR: PyYAML is required.", flush=True)
    raise SystemExit(2)


ROOT = Path(__file__).resolve().parent.parent.parent
CLAUDE_DIR = ROOT / ".claude"
AGENTS_DIR = CLAUDE_DIR / "agents"
AGENT_MEMORY_DIR = CLAUDE_DIR / "agent-memory"
COMMANDS_DIR = CLAUDE_DIR / "commands"
SKILLS_DIR = CLAUDE_DIR / "skills-on-demand"
WORKFLOWS_DIR = ROOT / "shared" / "workflows" / "definitions"


def _load_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        return {}
    try:
        return yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}


def _exact_token_pattern(token: str) -> str:
    escaped = re.escape(token)
    return rf"(?<![A-Za-z0-9_-]){escaped}(?![A-Za-z0-9_-])"


def _load_workflow_delegate_refs() -> dict[str, list[str]]:
    refs: dict[str, list[str]] = {}
    for path in sorted(WORKFLOWS_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for node in data.get("nodes", []):
            agent_name = node.get("delegate_to")
            if not agent_name:
                continue
            refs.setdefault(agent_name, []).append(
                f"{path.stem}:{node.get('id', '<unknown>')}"
            )
    return refs


def _scan_command_refs() -> dict[str, list[str]]:
    patterns = [
        re.compile(r"`([a-z0-9-]+)` agent"),
        re.compile(r"use ([a-z0-9-]+) agent", re.IGNORECASE),
        re.compile(r"使用 `([a-z0-9-]+)` agent"),
    ]
    refs: dict[str, list[str]] = {}
    for path in sorted(COMMANDS_DIR.glob("*.md")):
        lines = path.read_text(encoding="utf-8").splitlines()
        for idx, line in enumerate(lines, start=1):
            for pattern in patterns:
                for match in pattern.finditer(line):
                    refs.setdefault(match.group(1), []).append(f"{path.name}:{idx}")
    return refs


def _scan_documented_refs(agent_names: set[str]) -> dict[str, list[str]]:
    refs: dict[str, list[str]] = {}
    scan_paths = [CLAUDE_DIR / "CLAUDE.md"]
    scan_paths.extend(sorted(SKILLS_DIR.glob("*/SKILL.md")))
    scan_paths.extend(sorted(WORKFLOWS_DIR.glob("*.json")))
    for path in scan_paths:
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = path.relative_to(ROOT).as_posix()
        for agent_name in agent_names:
            if re.search(_exact_token_pattern(agent_name), text):
                refs.setdefault(agent_name, []).append(rel)
    return refs


def _format_ts(ts: float | None) -> str:
    if ts is None:
        return "-"
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%MZ")


def _memory_summary(agent_name: str) -> dict:
    memory_dir = AGENT_MEMORY_DIR / agent_name
    if not memory_dir.exists():
        return {
            "has_memory_dir": False,
            "memory_files": 0,
            "memory_bytes": 0,
            "memory_last_updated": None,
        }

    files = [p for p in memory_dir.rglob("*") if p.is_file()]
    total_bytes = sum(p.stat().st_size for p in files)
    latest_ts = max((p.stat().st_mtime for p in files), default=None)
    return {
        "has_memory_dir": True,
        "memory_files": len(files),
        "memory_bytes": total_bytes,
        "memory_last_updated": latest_ts,
    }


def _activation_status(workflow_refs: list[str], command_refs: list[str], documented_refs: list[str]) -> str:
    if workflow_refs:
        return "workflow"
    if command_refs:
        return "command"
    if documented_refs:
        return "documented_only"
    return "orphan"


def build_rows() -> list[dict]:
    workflow_refs = _load_workflow_delegate_refs()
    command_refs = _scan_command_refs()

    agent_meta: dict[str, dict] = {}
    agent_names: set[str] = set()
    for path in sorted(AGENTS_DIR.glob("*.md")):
        meta = _load_frontmatter(path)
        name = meta.get("name") or path.stem
        agent_names.add(name)
        agent_meta[name] = {
            "scope": meta.get("scope", ""),
            "tracking": meta.get("tracking", ""),
            "memory_scope": meta.get("memory", ""),
            "path": path.relative_to(ROOT).as_posix(),
        }

    documented_refs = _scan_documented_refs(agent_names)

    rows: list[dict] = []
    for name in sorted(agent_names):
        memory = _memory_summary(name)
        wf_refs = workflow_refs.get(name, [])
        cmd_refs = command_refs.get(name, [])
        doc_refs = documented_refs.get(name, [])
        row = {
            "agent": name,
            **agent_meta[name],
            **memory,
            "memory_last_updated_iso": _format_ts(memory["memory_last_updated"]),
            "workflow_delegate_refs": wf_refs,
            "workflow_delegate_count": len(wf_refs),
            "command_refs": cmd_refs,
            "command_ref_count": len(cmd_refs),
            "documented_refs": doc_refs,
            "documented_ref_count": len(doc_refs),
            "activation_status": _activation_status(wf_refs, cmd_refs, doc_refs),
            # Current runtime lacks a dedicated sub-agent invocation log.
            # Use latest memory write as the closest durable proxy instead of
            # inventing a precise "last used" timestamp.
            "last_usage_proxy": _format_ts(memory["memory_last_updated"]),
        }
        rows.append(row)
    return rows


def print_text(rows: list[dict]) -> None:
    print("== Agent Coverage ==")
    print("last_usage_proxy = latest memory file update; no dedicated sub-agent invocation log exists yet")
    print()
    header = f"{'agent':<34} {'act':<15} {'mem':<5} {'files':>5} {'bytes':>8} {'last_usage_proxy':<18} {'wf':>3} {'cmd':>3} {'doc':>3}"
    print(header)
    print("-" * len(header))
    for row in rows:
        mem_flag = "yes" if row["has_memory_dir"] else "no"
        print(
            f"{row['agent']:<34} "
            f"{row['activation_status']:<15} "
            f"{mem_flag:<5} "
            f"{row['memory_files']:>5} "
            f"{row['memory_bytes']:>8} "
            f"{row['last_usage_proxy']:<18} "
            f"{row['workflow_delegate_count']:>3} "
            f"{row['command_ref_count']:>3} "
            f"{row['documented_ref_count']:>3}"
        )

    orphans = [r["agent"] for r in rows if r["activation_status"] == "orphan"]
    memory_gaps = [r["agent"] for r in rows if r["memory_scope"] in {"project", "user"} and not r["has_memory_dir"]]
    print()
    print(f"agents: {len(rows)}")
    print(f"workflow-backed: {sum(1 for r in rows if r['activation_status'] == 'workflow')}")
    print(f"command-backed: {sum(1 for r in rows if r['activation_status'] == 'command')}")
    print(f"documented-only: {sum(1 for r in rows if r['activation_status'] == 'documented_only')}")
    print(f"orphans: {len(orphans)}")
    print(f"memory gaps: {len(memory_gaps)}")
    if orphans:
        print("orphan agents: " + ", ".join(orphans))
    if memory_gaps:
        print("memory gap agents: " + ", ".join(memory_gaps))


def main() -> int:
    parser = argparse.ArgumentParser(description="Report sub-agent coverage and memory scaffolding.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    args = parser.parse_args()

    rows = build_rows()
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        print_text(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
