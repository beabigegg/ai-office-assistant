#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
KB_DB = ROOT / "shared" / "kb" / "knowledge_graph" / "kb_index.db"
REGISTRY_JSON = ROOT / "shared" / "registry" / "capability_registry.json"
REMINDER_PATH = ROOT / "shared" / "workflows" / "state" / "indexing_reminders.json"

CAPABILITY_KEYWORDS = {
    "tool", "tools", "skill", "skills", "agent", "agents", "workflow", "workflows",
    "command", "commands", "route", "routing", "capability", "registry",
    "工具", "技能", "工作流", "命令", "路由", "能力", "治理",
}


def load_registry() -> dict:
    return json.loads(REGISTRY_JSON.read_text(encoding="utf-8"))


def load_reminders() -> dict:
    if not REMINDER_PATH.exists():
        return {"version": 1, "updated": "", "reminders": []}
    return json.loads(REMINDER_PATH.read_text(encoding="utf-8"))


def save_reminders(data: dict) -> None:
    REMINDER_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(KB_DB))
    conn.row_factory = sqlite3.Row
    return conn


def _registry_aliases(registry: dict) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for entity in registry.get("entities", []):
        aliases[entity["name"].lower()] = entity["id"]
        aliases[entity["id"].lower()] = entity["id"]
        aliases[Path(entity["path"]).stem.lower()] = entity["id"]
    return aliases


def _detect_capability_refs(text: str, registry: dict) -> list[str]:
    aliases = _registry_aliases(registry)
    lower = text.lower()
    hits = {entity_id for alias, entity_id in aliases.items() if alias and alias in lower}
    return sorted(hits)


def _looks_capability_related(text: str) -> bool:
    lower = text.lower()
    return any(keyword in lower for keyword in CAPABILITY_KEYWORDS)


def build_reminder_record(node: sqlite3.Row, registry: dict) -> dict | None:
    text = " ".join(
        str(node[key] or "")
        for key in ("target", "summary", "content", "refs_skill")
    )
    detected_refs = _detect_capability_refs(text, registry)
    capability_related = bool(detected_refs) or _looks_capability_related(text)
    if not capability_related:
        return None

    return {
        "source_id": node["id"],
        "source_type": node["node_type"],
        "project": node["project"],
        "title": node["target"],
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "kb_embedding_status": "auto_written_by_kb",
        "capability_refs": detected_refs,
        "actions_required": ["semantic_relation_extraction"],
        "reason": "KB writeback appears capability-related and may imply semantic relations beyond deterministic registry wiring.",
    }


def cmd_sync_kb(args: argparse.Namespace) -> int:
    registry = load_registry()
    reminder_doc = load_reminders()
    existing = {item["source_id"]: item for item in reminder_doc.get("reminders", [])}

    with get_conn() as conn:
        placeholders = ",".join("?" for _ in args.entry_ids)
        rows = conn.execute(
            f"""
            SELECT id, node_type, project, target, summary, content, refs_skill
            FROM nodes
            WHERE id IN ({placeholders})
            """,
            tuple(args.entry_ids),
        ).fetchall()

    added = 0
    updated = 0
    skipped = 0
    for row in rows:
        record = build_reminder_record(row, registry)
        if record is None:
            skipped += 1
            continue
        if row["id"] in existing:
            existing[row["id"]].update(record)
            updated += 1
        else:
            reminder_doc.setdefault("reminders", []).append(record)
            added += 1

    reminder_doc["updated"] = datetime.now(timezone.utc).isoformat()
    save_reminders(reminder_doc)
    print(f"added: {added}")
    print(f"updated: {updated}")
    print(f"skipped: {skipped}")
    print(f"reminder_file: {REMINDER_PATH.relative_to(ROOT).as_posix()}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    reminders = load_reminders().get("reminders", [])
    rows = [
        item for item in reminders
        if args.status is None or item.get("status") == args.status
    ]
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    if not rows:
        print("(no rows)")
        return 0

    headers = ["source_id", "source_type", "status", "actions_required", "capability_refs"]
    widths = {h: len(h) for h in headers}
    for row in rows:
        for h in headers:
            value = row[h]
            if isinstance(value, list):
                value = ",".join(value)
            widths[h] = max(widths[h], len(str(value)))
    print(" | ".join(f"{h:<{widths[h]}}" for h in headers))
    print("-+-".join("-" * widths[h] for h in headers))
    for row in rows:
        values = []
        for h in headers:
            value = row[h]
            if isinstance(value, list):
                value = ",".join(value)
            values.append(f"{str(value):<{widths[h]}}")
        print(" | ".join(values))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Track KB writeback indexing reminders for capability-related entries.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_sync = sub.add_parser("sync-kb", help="Inspect KB entries and enqueue capability indexing reminders when needed.")
    p_sync.add_argument("--entry-id", dest="entry_ids", action="append", required=True)
    p_sync.set_defaults(func=cmd_sync_kb)

    p_list = sub.add_parser("list", help="List indexing reminders.")
    p_list.add_argument("--status")
    p_list.add_argument("--json", action="store_true")
    p_list.set_defaults(func=cmd_list)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
