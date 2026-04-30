#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
REGISTRY_PATH = ROOT / "shared" / "registry" / "capability_registry.json"
ALLOWED_TYPES = {"tool", "skill", "agent", "command", "workflow"}
ALLOWED_RELATIONS = {
    "uses",
    "guided_by",
    "delegates_to",
    "escalates_to",
    "defers_to",
    "prefers",
}
ALLOWED_PENDING_ACTIONS = {
    "relation_extraction",
    "semantic_relation_extraction",
    "embedding_index",
    "writeback_indexing_policy",
}
ALLOWED_AUTOMATION_MODES = {"auto", "remind"}
ALLOWED_PENDING_STATUSES = {"pending", "completed", "waived"}


def load_registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def rel_exists(rel_path: str) -> bool:
    return (ROOT / Path(rel_path)).exists()


def audit_registry(registry: dict) -> tuple[list[dict], list[str], list[str]]:
    rows: list[dict] = []
    errors: list[str] = []
    warnings: list[str] = []

    entities = registry.get("entities", [])
    relations = registry.get("relations", [])
    pending_actions = registry.get("pending_actions", [])
    entity_ids: set[str] = set()
    path_to_ids: dict[str, list[str]] = {}

    for entity in entities:
        entity_id = entity.get("id", "")
        entity_type = entity.get("type", "")
        path = entity.get("path", "")
        rows.append({
            "id": entity_id,
            "type": entity_type,
            "status": entity.get("status", ""),
            "scope": entity.get("scope", ""),
            "path": path,
        })

        if not entity_id:
            errors.append("entity missing id")
            continue
        if entity_id in entity_ids:
            errors.append(f"duplicate entity id: {entity_id}")
        entity_ids.add(entity_id)

        if entity_type not in ALLOWED_TYPES:
            errors.append(f"entity has invalid type: {entity_id} -> {entity_type}")

        if not path:
            errors.append(f"entity missing path: {entity_id}")
        elif not rel_exists(path):
            errors.append(f"entity path missing: {entity_id} -> {path}")

        path_to_ids.setdefault(path, []).append(entity_id)

    for path, ids in sorted(path_to_ids.items()):
        if len(ids) > 1:
            warnings.append(f"multiple entities share the same path: {path} -> {', '.join(ids)}")

    for relation in relations:
        src = relation.get("from", "")
        rel_type = relation.get("type", "")
        dst = relation.get("to", "")
        if src not in entity_ids:
            errors.append(f"relation source missing: {src}")
        if dst not in entity_ids:
            errors.append(f"relation target missing: {dst}")
        if rel_type not in ALLOWED_RELATIONS:
            errors.append(f"relation has invalid type: {src} -[{rel_type}]-> {dst}")

    relation_pairs = {(r.get("from"), r.get("type"), r.get("to")) for r in relations}
    if len(relation_pairs) != len(relations):
        warnings.append("registry contains duplicate relations")

    for action in pending_actions:
        action_id = action.get("id", "")
        action_type = action.get("action", "")
        mode = action.get("mode", "")
        status = action.get("status", "")
        target = action.get("target", "")

        if not action_id:
            errors.append("pending_action missing id")
            continue
        if action_type not in ALLOWED_PENDING_ACTIONS:
            errors.append(f"pending_action has invalid action: {action_id} -> {action_type}")
        if mode not in ALLOWED_AUTOMATION_MODES:
            errors.append(f"pending_action has invalid mode: {action_id} -> {mode}")
        if status not in ALLOWED_PENDING_STATUSES:
            errors.append(f"pending_action has invalid status: {action_id} -> {status}")
        if not target:
            errors.append(f"pending_action missing target: {action_id}")
        elif "/" in target and not rel_exists(target):
            errors.append(f"pending_action target missing: {action_id} -> {target}")

        if status == "pending":
            warnings.append(
                f"pending {action_type} ({mode}): {action_id} -> {target}"
            )

    return rows, errors, warnings


def print_text(rows: list[dict], errors: list[str], warnings: list[str]) -> None:
    type_counts = Counter(row["type"] for row in rows)
    status_counts = Counter(row["status"] for row in rows)
    print("== Capability Audit ==")
    print(f"registry: {REGISTRY_PATH.relative_to(ROOT).as_posix()}")
    print(f"entities: {len(rows)}")
    registry = load_registry()
    pending_actions = registry.get("pending_actions", [])
    pending_counts = Counter(action.get("status", "") for action in pending_actions)
    print("type_counts:")
    for key, value in sorted(type_counts.items()):
        print(f"  {key}: {value}")
    print("status_counts:")
    for key, value in sorted(status_counts.items()):
        print(f"  {key}: {value}")
    print("pending_action_counts:")
    for key, value in sorted(pending_counts.items()):
        print(f"  {key}: {value}")

    print()
    print(f"{'id':<40} {'type':<10} {'status':<18} path")
    print("-" * 110)
    for row in rows:
        print(f"{row['id']:<40} {row['type']:<10} {row['status']:<18} {row['path']}")

    if errors:
        print("\n[ERROR]")
        for item in errors:
            print(f"- {item}")
    if warnings:
        print("\n[WARN]")
        for item in warnings:
            print(f"- {item}")
    if not errors and not warnings:
        print("\n[OK] No capability registry issues detected.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit shared/registry/capability_registry.json.")
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    args = parser.parse_args()

    registry = load_registry()
    rows, errors, warnings = audit_registry(registry)
    pending_actions = registry.get("pending_actions", [])

    if args.json:
        print(json.dumps({
            "rows": rows,
            "pending_actions": pending_actions,
            "errors": errors,
            "warnings": warnings,
        }, ensure_ascii=False, indent=2))
    else:
        print_text(rows, errors, warnings)

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
