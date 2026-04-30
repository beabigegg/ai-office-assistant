#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
REGISTRY_JSON = ROOT / "shared" / "registry" / "capability_registry.json"
REGISTRY_DB = ROOT / "shared" / "registry" / "capability_registry.db"
DEFAULT_RELATION_PAYLOAD = ROOT / "shared" / "registry" / "semantic_relation_payload.json"
CLAUDE_DIR = ROOT / ".claude"
AGENTS_DIR = CLAUDE_DIR / "agents"
COMMANDS_DIR = CLAUDE_DIR / "commands"
WORKFLOWS_DIR = ROOT / "shared" / "workflows" / "definitions"


SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS meta (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS entities (
        id TEXT PRIMARY KEY,
        type TEXT NOT NULL,
        name TEXT NOT NULL,
        status TEXT NOT NULL,
        scope TEXT NOT NULL,
        path TEXT NOT NULL,
        summary TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS relations (
        from_id TEXT NOT NULL,
        relation_type TEXT NOT NULL,
        to_id TEXT NOT NULL,
        notes TEXT NOT NULL DEFAULT '',
        PRIMARY KEY (from_id, relation_type, to_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS capability_embeddings (
        entity_id TEXT PRIMARY KEY,
        embedding BLOB NOT NULL,
        embed_text TEXT NOT NULL,
        embed_model TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pending_actions (
        id TEXT PRIMARY KEY,
        target TEXT NOT NULL,
        action TEXT NOT NULL,
        mode TEXT NOT NULL,
        status TEXT NOT NULL,
        summary TEXT NOT NULL,
        recommended_trigger TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type)",
    "CREATE INDEX IF NOT EXISTS idx_entities_status ON entities(status)",
    "CREATE INDEX IF NOT EXISTS idx_relations_from ON relations(from_id)",
    "CREATE INDEX IF NOT EXISTS idx_relations_to ON relations(to_id)",
    "CREATE INDEX IF NOT EXISTS idx_embeddings_model ON capability_embeddings(embed_model)",
    "CREATE INDEX IF NOT EXISTS idx_pending_status ON pending_actions(status)",
]


def load_registry() -> dict:
    return json.loads(REGISTRY_JSON.read_text(encoding="utf-8"))


def save_registry(registry: dict) -> None:
    REGISTRY_JSON.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def get_conn(db_path: Path = REGISTRY_DB) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    for stmt in SCHEMA:
        conn.execute(stmt)
    conn.commit()


def has_schema(conn: sqlite3.Connection) -> bool:
    required = {"meta", "entities", "relations", "capability_embeddings", "pending_actions"}
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    found = {row["name"] for row in rows}
    return required.issubset(found)


def rebuild_db(conn: sqlite3.Connection, registry: dict) -> None:
    init_db(conn)
    with conn:
        conn.execute("DELETE FROM meta")
        conn.execute("DELETE FROM entities")
        conn.execute("DELETE FROM relations")
        conn.execute("DELETE FROM pending_actions")
        conn.executemany(
            """
            INSERT INTO entities (id, type, name, status, scope, path, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    entity["id"],
                    entity["type"],
                    entity["name"],
                    entity["status"],
                    entity["scope"],
                    entity["path"],
                    entity.get("summary", ""),
                )
                for entity in registry.get("entities", [])
            ],
        )
        conn.executemany(
            """
            INSERT INTO relations (from_id, relation_type, to_id, notes)
            VALUES (?, ?, ?, ?)
            """,
            [
                (
                    relation["from"],
                    relation["type"],
                    relation["to"],
                    relation.get("notes", ""),
                )
                for relation in registry.get("relations", [])
            ],
        )
        conn.executemany(
            """
            INSERT INTO pending_actions
            (id, target, action, mode, status, summary, recommended_trigger)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    action["id"],
                    action["target"],
                    action["action"],
                    action["mode"],
                    action["status"],
                    action.get("summary", ""),
                    action.get("recommended_trigger", ""),
                )
                for action in registry.get("pending_actions", [])
            ],
        )
        conn.executemany(
            "INSERT INTO meta (key, value) VALUES (?, ?)",
            [
                ("registry_path", REGISTRY_JSON.relative_to(ROOT).as_posix()),
                ("registry_version", str(registry.get("version", ""))),
                ("registry_updated", str(registry.get("updated", ""))),
            ],
        )


def ensure_synced(conn: sqlite3.Connection) -> bool:
    if not REGISTRY_DB.exists():
        rebuild_db(conn, load_registry())
        return True
    if not has_schema(conn):
        rebuild_db(conn, load_registry())
        return True
    if REGISTRY_JSON.stat().st_mtime > REGISTRY_DB.stat().st_mtime:
        rebuild_db(conn, load_registry())
        return True
    return False


def _get_embedding_utils() -> dict:
    try:
        from embedding_utils import (
            get_embedding,
            embedding_to_blob,
            blob_to_embedding,
            cosine_similarity,
            is_ollama_available,
            MODEL,
        )
        return {
            "get_embedding": get_embedding,
            "embedding_to_blob": embedding_to_blob,
            "blob_to_embedding": blob_to_embedding,
            "cosine_similarity": cosine_similarity,
            "is_ollama_available": is_ollama_available,
            "model": MODEL,
        }
    except Exception:
        return {}


def _entity_maps(registry: dict) -> tuple[dict[str, dict], dict[str, str]]:
    by_id = {entity["id"]: entity for entity in registry.get("entities", [])}
    by_name = {
        f"{entity['type']}:{entity['name']}": entity["id"]
        for entity in registry.get("entities", [])
    }
    return by_id, by_name


def _workflow_relations(registry: dict) -> list[dict]:
    _, by_name = _entity_maps(registry)
    found: list[dict] = []
    for path in sorted(WORKFLOWS_DIR.glob("*.json")):
        workflow_id = by_name.get(f"workflow:{path.stem}")
        if not workflow_id:
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for node in data.get("nodes", []):
            agent_name = node.get("delegate_to")
            if not agent_name:
                continue
            agent_id = by_name.get(f"agent:{agent_name}")
            if not agent_id:
                continue
            found.append({
                "from": workflow_id,
                "type": "delegates_to",
                "to": agent_id,
                "notes": f"auto-discovered from {path.relative_to(ROOT).as_posix()}:{node.get('id', '<unknown>')}",
            })
    return found


def _agent_relations(registry: dict) -> list[dict]:
    _, by_name = _entity_maps(registry)
    found: list[dict] = []
    pattern = re.compile(r"\.claude/skills-on-demand/([^/\s]+)/SKILL\.md")
    tool_pattern = re.compile(r"shared/tools/([A-Za-z0-9_-]+)\.py")
    for path in sorted(AGENTS_DIR.glob("*.md")):
        agent_id = by_name.get(f"agent:{path.stem}")
        if not agent_id:
            continue
        text = path.read_text(encoding="utf-8")
        for skill_name in sorted(set(pattern.findall(text))):
            skill_id = by_name.get(f"skill:{skill_name}")
            if skill_id:
                found.append({
                    "from": agent_id,
                    "type": "guided_by",
                    "to": skill_id,
                    "notes": f"auto-discovered from {path.relative_to(ROOT).as_posix()}",
                })
        for tool_name in sorted(set(tool_pattern.findall(text))):
            tool_id = by_name.get(f"tool:{tool_name.replace('_', '-')}")
            if tool_id:
                found.append({
                    "from": agent_id,
                    "type": "uses",
                    "to": tool_id,
                    "notes": f"auto-discovered from {path.relative_to(ROOT).as_posix()}",
                })
    return found


def _command_relations(registry: dict) -> list[dict]:
    _, by_name = _entity_maps(registry)
    found: list[dict] = []
    tool_pattern = re.compile(r"shared/tools/([A-Za-z0-9_-]+)\.py")
    skill_pattern = re.compile(r"\.claude/skills-on-demand/([^/\s]+)/SKILL\.md")
    agent_patterns = [
        re.compile(r"`([a-z0-9-]+)` agent"),
        re.compile(r"use `?([a-z0-9-]+)`? agent", re.IGNORECASE),
        re.compile(r"使用 `([a-z0-9-]+)` agent"),
    ]
    escalate_patterns = [
        re.compile(r"升級到 `([a-z0-9-]+)`"),
        re.compile(r"改用 `([a-z0-9-]+)`"),
        re.compile(r"escalate to `?([a-z0-9-]+)`?", re.IGNORECASE),
    ]
    for path in sorted(COMMANDS_DIR.glob("*.md")):
        command_id = by_name.get(f"command:{path.stem}")
        if not command_id:
            continue
        text = path.read_text(encoding="utf-8")
        for tool_name in sorted(set(tool_pattern.findall(text))):
            tool_id = by_name.get(f"tool:{tool_name.replace('_', '-')}")
            if tool_id:
                found.append({
                    "from": command_id,
                    "type": "uses",
                    "to": tool_id,
                    "notes": f"auto-discovered from {path.relative_to(ROOT).as_posix()}",
                })
        for skill_name in sorted(set(skill_pattern.findall(text))):
            skill_id = by_name.get(f"skill:{skill_name}")
            if skill_id:
                found.append({
                    "from": command_id,
                    "type": "guided_by",
                    "to": skill_id,
                    "notes": f"auto-discovered from {path.relative_to(ROOT).as_posix()}",
                })
        for pattern in agent_patterns:
            for agent_name in pattern.findall(text):
                agent_id = by_name.get(f"agent:{agent_name}")
                if agent_id:
                    found.append({
                        "from": command_id,
                        "type": "delegates_to",
                        "to": agent_id,
                        "notes": f"auto-discovered from {path.relative_to(ROOT).as_posix()}",
                    })
        for pattern in escalate_patterns:
            for token in pattern.findall(text):
                if token == path.stem:
                    continue
                command_target_id = by_name.get(f"command:{token}")
                if command_target_id:
                    found.append({
                        "from": command_id,
                        "type": "escalates_to",
                        "to": command_target_id,
                        "notes": f"auto-discovered from {path.relative_to(ROOT).as_posix()}",
                    })
    return found


def discover_relations(registry: dict) -> list[dict]:
    discovered = (
        _workflow_relations(registry)
        + _agent_relations(registry)
        + _command_relations(registry)
    )
    dedup: dict[tuple[str, str, str], dict] = {}
    for rel in discovered:
        key = (rel["from"], rel["type"], rel["to"])
        dedup.setdefault(key, rel)
    return sorted(dedup.values(), key=lambda r: (r["from"], r["type"], r["to"]))


def _build_embed_text(entity: sqlite3.Row, outgoing_relations: list[sqlite3.Row]) -> str:
    rel_text = "; ".join(
        f"{row['relation_type']} {row['to_id']}" for row in outgoing_relations
    )
    parts = [
        f"id: {entity['id']}",
        f"type: {entity['type']}",
        f"name: {entity['name']}",
        f"status: {entity['status']}",
        f"scope: {entity['scope']}",
        f"path: {entity['path']}",
        f"summary: {entity['summary']}",
    ]
    if rel_text:
        parts.append(f"relations: {rel_text}")
    return "\n".join(parts)


def print_rows(rows: list[sqlite3.Row]) -> None:
    if not rows:
        print("(no rows)")
        return
    headers = rows[0].keys()
    widths = {h: len(h) for h in headers}
    for row in rows:
        for h in headers:
            widths[h] = max(widths[h], len(str(row[h])))
    lines = []
    lines.append(" | ".join(f"{h:<{widths[h]}}" for h in headers))
    lines.append("-+-".join("-" * widths[h] for h in headers))
    for row in rows:
        lines.append(" | ".join(f"{str(row[h]):<{widths[h]}}" for h in headers))
    sys.stdout.buffer.write(("\n".join(lines) + "\n").encode("utf-8"))


def cmd_sync(args: argparse.Namespace) -> int:
    registry = load_registry()
    with get_conn() as conn:
        rebuild_db(conn, registry)
        entity_count = conn.execute("SELECT COUNT(*) AS n FROM entities").fetchone()["n"]
        relation_count = conn.execute("SELECT COUNT(*) AS n FROM relations").fetchone()["n"]
        pending_count = conn.execute("SELECT COUNT(*) AS n FROM pending_actions").fetchone()["n"]
    print(f"synced: {REGISTRY_DB.relative_to(ROOT).as_posix()}")
    print(f"entities: {entity_count}")
    print(f"relations: {relation_count}")
    print(f"pending_actions: {pending_count}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    with get_conn() as conn:
        ensure_synced(conn)
        sql = """
            SELECT id, type, name, status, scope, path
            FROM entities
            WHERE (? IS NULL OR type = ?)
              AND (? IS NULL OR status = ?)
            ORDER BY type, id
        """
        rows = conn.execute(sql, (args.type, args.type, args.status, args.status)).fetchall()
    print_rows(rows)
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    with get_conn() as conn:
        ensure_synced(conn)
        row = conn.execute(
            """
            SELECT id, type, name, status, scope, path, summary
            FROM entities
            WHERE id = ?
            """,
            (args.entity_id,),
        ).fetchone()
        if row is None:
            print(f"entity not found: {args.entity_id}")
            return 1
        print_rows([row])
        rels = conn.execute(
            """
            SELECT relation_type, to_id, notes
            FROM relations
            WHERE from_id = ?
            ORDER BY relation_type, to_id
            """,
            (args.entity_id,),
        ).fetchall()
        if rels:
            print()
            print("outgoing_relations:")
            print_rows(rels)
    return 0


def cmd_relations(args: argparse.Namespace) -> int:
    with get_conn() as conn:
        ensure_synced(conn)
        sql = """
            SELECT from_id, relation_type, to_id, notes
            FROM relations
            WHERE (? IS NULL OR from_id = ?)
              AND (? IS NULL OR to_id = ?)
              AND (? IS NULL OR relation_type = ?)
            ORDER BY from_id, relation_type, to_id
        """
        rows = conn.execute(
            sql,
            (args.from_id, args.from_id, args.to_id, args.to_id, args.relation_type, args.relation_type),
        ).fetchall()
    print_rows(rows)
    return 0


def cmd_pending(args: argparse.Namespace) -> int:
    with get_conn() as conn:
        ensure_synced(conn)
        sql = """
            SELECT id, action, mode, status, target, recommended_trigger
            FROM pending_actions
            WHERE (? IS NULL OR status = ?)
            ORDER BY
                CASE status WHEN 'pending' THEN 0 WHEN 'completed' THEN 1 ELSE 2 END,
                id
        """
        rows = conn.execute(sql, (args.status, args.status)).fetchall()
    print_rows(rows)
    return 0


def cmd_sql(args: argparse.Namespace) -> int:
    with get_conn() as conn:
        ensure_synced(conn)
        rows = conn.execute(args.query).fetchall()
    print_rows(rows)
    return 0


def cmd_discover_relations(args: argparse.Namespace) -> int:
    registry = load_registry()
    discovered = discover_relations(registry)
    current = {
        (r["from"], r["type"], r["to"])
        for r in registry.get("relations", [])
    }
    rows = []
    for rel in discovered:
        rows.append({
            "from_id": rel["from"],
            "relation_type": rel["type"],
            "to_id": rel["to"],
            "present_in_registry": "yes" if (rel["from"], rel["type"], rel["to"]) in current else "no",
        })
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        print_rows(rows)
    return 0


def cmd_sync_relations(args: argparse.Namespace) -> int:
    registry = load_registry()
    current = {
        (r["from"], r["type"], r["to"]): r
        for r in registry.get("relations", [])
    }
    discovered = discover_relations(registry)
    discovered_keys = {
        (r["from"], r["type"], r["to"])
        for r in discovered
    }
    added = 0
    for rel in discovered:
        key = (rel["from"], rel["type"], rel["to"])
        if key not in current:
            registry.setdefault("relations", []).append(rel)
            current[key] = rel
            added += 1

    removed = 0
    kept_relations = []
    for rel in registry.get("relations", []):
        key = (rel["from"], rel["type"], rel["to"])
        if rel.get("notes", "").startswith("auto-discovered from ") and key not in discovered_keys:
            removed += 1
            continue
        kept_relations.append(rel)
    registry["relations"] = kept_relations

    for action in registry.get("pending_actions", []):
        if action.get("id") == "registry-relations-bootstrap":
            action["mode"] = "auto"
            action["status"] = "completed"
            action["summary"] = "Deterministic relation sync is implemented via capability_registry.py sync-relations."

    registry["updated"] = registry.get("updated") or ""
    save_registry(registry)

    with get_conn() as conn:
        rebuild_db(conn, registry)

    print(f"relations_added: {added}")
    print(f"relations_removed: {removed}")
    print("registry_relations_bootstrap: completed")
    return 0


def cmd_sync_embeddings(args: argparse.Namespace) -> int:
    eu = _get_embedding_utils()
    if not eu:
        print("embedding utils unavailable; leaving embedding bootstrap pending")
        return 0
    if not eu["is_ollama_available"]():
        print("Ollama embedding service unavailable; leaving embedding bootstrap pending")
        return 0

    registry = load_registry()
    now_iso = datetime.now(timezone.utc).isoformat()
    embedded = 0
    skipped = 0
    with get_conn() as conn:
        ensure_synced(conn)
        entities = conn.execute(
            "SELECT id, type, name, status, scope, path, summary FROM entities ORDER BY id"
        ).fetchall()
        if args.limit:
            entities = entities[:args.limit]
        for entity in entities:
            outgoing = conn.execute(
                """
                SELECT relation_type, to_id
                FROM relations
                WHERE from_id = ?
                ORDER BY relation_type, to_id
                """,
                (entity["id"],),
            ).fetchall()
            embed_text = _build_embed_text(entity, outgoing)
            existing = None if args.force else conn.execute(
                "SELECT embed_text, embed_model FROM capability_embeddings WHERE entity_id = ?",
                (entity["id"],),
            ).fetchone()
            if existing and existing["embed_text"] == embed_text and existing["embed_model"] == eu["model"]:
                skipped += 1
                continue
            vec = eu["get_embedding"](embed_text)
            blob = eu["embedding_to_blob"](vec)
            conn.execute(
                """
                INSERT INTO capability_embeddings
                (entity_id, embedding, embed_text, embed_model, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(entity_id) DO UPDATE SET
                    embedding=excluded.embedding,
                    embed_text=excluded.embed_text,
                    embed_model=excluded.embed_model,
                    updated_at=excluded.updated_at
                """,
                (entity["id"], blob, embed_text, eu["model"], now_iso),
            )
            embedded += 1

    for action in registry.get("pending_actions", []):
        if action.get("id") == "registry-embeddings-bootstrap":
            action["mode"] = "auto"
            action["status"] = "completed"
            action["summary"] = (
                f"Capability embeddings built via capability_registry.py sync-embeddings using {eu['model']}."
            )
    save_registry(registry)
    with get_conn() as conn:
        rebuild_db(conn, registry)
        # restore embedding table content after metadata rebuild
        # rebuild_db intentionally preserves capability_embeddings table rows
    print(f"embedded: {embedded}")
    print(f"skipped: {skipped}")
    print(f"model: {eu['model']}")
    print("registry_embeddings_bootstrap: completed")
    return 0


def cmd_search_semantic(args: argparse.Namespace) -> int:
    eu = _get_embedding_utils()
    if not eu:
        print("embedding utils unavailable")
        return 1
    if not eu["is_ollama_available"]():
        print("Ollama embedding service unavailable")
        return 1

    with get_conn() as conn:
        ensure_synced(conn)
        count = conn.execute("SELECT COUNT(*) AS n FROM capability_embeddings").fetchone()["n"]
        if count == 0:
            print("no capability embeddings found; run sync-embeddings first")
            return 1
        query_vec = eu["get_embedding"](args.query)
        rows = conn.execute(
            """
            SELECT ce.entity_id, ce.embedding, e.type, e.name, e.status, e.scope, e.path, e.summary
            FROM capability_embeddings ce
            JOIN entities e ON e.id = ce.entity_id
            """
        ).fetchall()

    scored = []
    for row in rows:
        emb = eu["blob_to_embedding"](row["embedding"])
        sim = eu["cosine_similarity"](query_vec, emb)
        scored.append({
            "entity_id": row["entity_id"],
            "type": row["type"],
            "name": row["name"],
            "status": row["status"],
            "scope": row["scope"],
            "path": row["path"],
            "similarity": round(sim, 4),
            "summary": row["summary"],
        })
    scored.sort(key=lambda item: item["similarity"], reverse=True)
    top = scored[:args.top]
    if args.json:
        print(json.dumps(top, ensure_ascii=False, indent=2))
        return 0

    if not top:
        print("(no rows)")
        return 0
    widths = {
        "entity_id": max(len("entity_id"), max(len(item["entity_id"]) for item in top)),
        "type": max(len("type"), max(len(item["type"]) for item in top)),
        "similarity": len("similarity"),
    }
    print(f"{'entity_id':<{widths['entity_id']}} | {'type':<{widths['type']}} | similarity | summary")
    print(f"{'-' * widths['entity_id']}-+-{'-' * widths['type']}-+-{'-' * len('similarity')}-+-{'-' * 40}")
    for item in top:
        print(
            f"{item['entity_id']:<{widths['entity_id']}} | "
            f"{item['type']:<{widths['type']}} | "
            f"{item['similarity']:<10} | "
            f"{item['summary']}"
        )
    return 0


def cmd_export_semantic_relations(args: argparse.Namespace) -> int:
    registry = load_registry()
    rows = []
    with get_conn() as conn:
        ensure_synced(conn)
        entities = conn.execute(
            "SELECT id, type, name, status, scope, path, summary FROM entities ORDER BY id"
        ).fetchall()
        if args.entity_id:
            entities = [entity for entity in entities if entity["id"] in set(args.entity_id)]
        catalog = [
            {
                "id": entity["id"],
                "type": entity["type"],
                "name": entity["name"],
                "summary": entity["summary"],
            }
            for entity in conn.execute(
                "SELECT id, type, name, summary FROM entities ORDER BY id"
            ).fetchall()
        ]
        for entity in entities:
            outgoing = conn.execute(
                """
                SELECT relation_type, to_id, notes
                FROM relations
                WHERE from_id = ?
                ORDER BY relation_type, to_id
                """,
                (entity["id"],),
            ).fetchall()
            rows.append({
                "entity_id": entity["id"],
                "type": entity["type"],
                "name": entity["name"],
                "status": entity["status"],
                "scope": entity["scope"],
                "path": entity["path"],
                "summary": entity["summary"],
                "embed_text": _build_embed_text(entity, outgoing),
                "existing_relations": [
                    {
                        "type": row["relation_type"],
                        "to": row["to_id"],
                        "notes": row["notes"],
                    }
                    for row in outgoing
                ],
                "candidate_targets": catalog,
                "suggestion_contract": {
                    "provider": "remote_api_gpt_oss",
                    "allowed_relation_types": [
                        "guided_by",
                        "uses",
                        "delegates_to",
                        "escalates_to",
                        "defers_to",
                        "prefers",
                    ],
                    "must_not_repeat_existing_relations": True,
                    "output_fields": [
                        "from",
                        "type",
                        "to",
                        "confidence",
                        "reason",
                    ],
                },
            })

    out_path = (ROOT / args.output).resolve() if args.output else DEFAULT_RELATION_PAYLOAD
    out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        shown = out_path.relative_to(ROOT).as_posix()
    except ValueError:
        shown = str(out_path)
    print(f"exported: {shown}")
    print(f"entities: {len(rows)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SQLite query surface for shared/registry/capability_registry.json.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_sync = sub.add_parser("sync", help="Rebuild capability_registry.db from JSON authority.")
    p_sync.set_defaults(func=cmd_sync)

    p_list = sub.add_parser("list", help="List entities.")
    p_list.add_argument("--type", choices=["tool", "skill", "agent", "command", "workflow"])
    p_list.add_argument("--status")
    p_list.set_defaults(func=cmd_list)

    p_show = sub.add_parser("show", help="Show one entity and its outgoing relations.")
    p_show.add_argument("entity_id")
    p_show.set_defaults(func=cmd_show)

    p_rel = sub.add_parser("relations", help="Query relations.")
    p_rel.add_argument("--from", dest="from_id")
    p_rel.add_argument("--to", dest="to_id")
    p_rel.add_argument("--type", dest="relation_type")
    p_rel.set_defaults(func=cmd_relations)

    p_pending = sub.add_parser("pending", help="List pending registry actions.")
    p_pending.add_argument("--status")
    p_pending.set_defaults(func=cmd_pending)

    p_sql = sub.add_parser("sql", help="Run a read-only SQL query against capability_registry.db.")
    p_sql.add_argument("query")
    p_sql.set_defaults(func=cmd_sql)

    p_disc = sub.add_parser("discover-relations", help="Discover deterministic relations from workflow, agent, and command surfaces.")
    p_disc.add_argument("--json", action="store_true")
    p_disc.set_defaults(func=cmd_discover_relations)

    p_sync_rel = sub.add_parser("sync-relations", help="Merge discovered deterministic relations into the JSON authority and rebuild the DB.")
    p_sync_rel.set_defaults(func=cmd_sync_relations)

    p_sync_emb = sub.add_parser("sync-embeddings", help="Build capability embeddings using the configured local embedding service.")
    p_sync_emb.add_argument("--force", action="store_true", help="Re-embed all entities even if embed_text has not changed.")
    p_sync_emb.add_argument("--limit", type=int, help="Only embed the first N entities for smoke testing or staged bootstrap.")
    p_sync_emb.set_defaults(func=cmd_sync_embeddings)

    p_sem = sub.add_parser("search-semantic", help="Semantic search across capability entities.")
    p_sem.add_argument("query")
    p_sem.add_argument("--top", type=int, default=5)
    p_sem.add_argument("--json", action="store_true")
    p_sem.set_defaults(func=cmd_search_semantic)

    p_exp_rel = sub.add_parser(
        "export-semantic-relations",
        help="Export registry entities and current relations as a payload for remote api-gpt oss semantic relation extraction.",
    )
    p_exp_rel.add_argument("--output", help="Output JSON path. Default: shared/registry/semantic_relation_payload.json")
    p_exp_rel.add_argument("--entity-id", action="append", help="Only export specific entity ids. Can be passed multiple times.")
    p_exp_rel.set_defaults(func=cmd_export_semantic_relations)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
