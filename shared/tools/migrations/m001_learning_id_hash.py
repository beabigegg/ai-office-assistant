#!/usr/bin/env python3
"""Migration m001: learning nodes ECR-LXX → LRN-{hash} ID stabilization.

Usage:
    python m001_learning_id_hash.py --dry-run    # 印出 mapping，不寫 DB
    python m001_learning_id_hash.py --execute    # 實際執行
    python m001_learning_id_hash.py --rebuild-edges-only  # 只修邊，不改 node id
"""
import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = REPO_ROOT / 'shared' / 'kb' / 'knowledge_graph' / 'kb_index.db'
KG_DIR = REPO_ROOT / 'shared' / 'kb' / 'knowledge_graph'
LEARNING_PATH = REPO_ROOT / 'shared' / 'kb' / 'dynamic' / 'learning_notes.md'


def _compute_new_id(legacy_id: str, title: str, date: str | None) -> str:
    raw = f"{date or ''}|{title}"
    hash8 = hashlib.sha1(raw.encode('utf-8')).hexdigest()[:8].upper()
    return f"LRN-{hash8}"


def _build_mapping(conn) -> dict:
    """Build {old_id: new_id} mapping from DB."""
    rows = conn.execute(
        "SELECT id, target, created_date FROM nodes WHERE node_type='learning' AND id LIKE 'ECR-L%'"
    ).fetchall()
    mapping = {}
    for r in rows:
        old_id = r[0]
        title = r[1] or ''
        date = r[2]
        new_id = _compute_new_id(old_id, title, date)
        mapping[old_id] = new_id
    return mapping


def run_migration(dry_run=True, rebuild_edges_only=False):
    # Backup first
    if not dry_run:
        date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup = DB_PATH.with_suffix(f'.db.bak.p2-t1-{date_str}')
        shutil.copy2(str(DB_PATH), str(backup))
        print(f"Backup: {backup}")

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    mapping = _build_mapping(conn)

    if not mapping:
        print("No ECR-L* learning nodes found. Nothing to migrate.")
        conn.close()
        return

    print(f"Found {len(mapping)} learning nodes to migrate:")
    for old, new in sorted(mapping.items()):
        print(f"  {old} -> {new}")

    # Save mapping file
    map_path = KG_DIR / 'learning_id_legacy_map.json'
    with open(str(map_path), 'w', encoding='utf-8') as f:
        json.dump({old: new for old, new in mapping.items()}, f, indent=2, ensure_ascii=False)
    print(f"Mapping saved: {map_path}")

    if dry_run:
        print("Dry-run mode: no DB changes made.")
        conn.close()
        return

    if not rebuild_edges_only:
        # Check for potential hash collisions
        new_ids = list(mapping.values())
        if len(new_ids) != len(set(new_ids)):
            print("WARNING: hash collisions detected — duplicate LRN-* IDs generated. Aborting.")
            conn.close()
            sys.exit(1)

        # Determine which LRN-* nodes already exist (e.g. from a sync run after code change)
        existing_lrn = {
            r[0] for r in conn.execute(
                "SELECT id FROM nodes WHERE node_type='learning' AND id LIKE 'LRN-%'"
            ).fetchall()
        }

        # For ECR-L* nodes whose LRN-* counterpart already exists: delete the ECR-L* duplicate.
        # For ECR-L* nodes with no LRN-* yet: rename in-place via UPDATE.
        rename_count = 0
        delete_count = 0
        for old_id, new_id in mapping.items():
            if new_id in existing_lrn:
                # LRN-* already created by sync — delete the stale ECR-L* node
                conn.execute("DELETE FROM nodes WHERE id=?", (old_id,))
                delete_count += 1
            else:
                # Rename: UPDATE id and set legacy_id
                conn.execute(
                    "UPDATE nodes SET id=?, legacy_id=? WHERE id=?",
                    (new_id, old_id, old_id)
                )
                # Update node_embeddings for renamed node
                conn.execute(
                    "UPDATE node_embeddings SET node_id=? WHERE node_id=?",
                    (new_id, old_id)
                )
                rename_count += 1

        print(f"  Nodes renamed: {rename_count}, deleted (already migrated by sync): {delete_count}")

    # Update edges: replace ECR-L* source/target with LRN-* equivalent,
    # using INSERT OR IGNORE + DELETE to avoid PK violations when the edge already exists.
    edge_migrated = 0
    edge_dropped = 0
    for old_id, new_id in mapping.items():
        # Source-side
        old_src_edges = conn.execute(
            "SELECT source_id, target_id, relation FROM edges WHERE source_id=?", (old_id,)
        ).fetchall()
        for e in old_src_edges:
            conn.execute(
                "INSERT OR IGNORE INTO edges (source_id, target_id, relation) VALUES (?, ?, ?)",
                (new_id, e[1], e[2])
            )
            conn.execute(
                "DELETE FROM edges WHERE source_id=? AND target_id=? AND relation=?",
                (old_id, e[1], e[2])
            )
            edge_migrated += 1

        # Target-side
        old_tgt_edges = conn.execute(
            "SELECT source_id, target_id, relation FROM edges WHERE target_id=?", (old_id,)
        ).fetchall()
        for e in old_tgt_edges:
            conn.execute(
                "INSERT OR IGNORE INTO edges (source_id, target_id, relation) VALUES (?, ?, ?)",
                (e[0], new_id, e[2])
            )
            conn.execute(
                "DELETE FROM edges WHERE source_id=? AND target_id=? AND relation=?",
                (e[0], old_id, e[2])
            )
            edge_migrated += 1

    print(f"  Edges migrated: {edge_migrated}")

    conn.commit()
    conn.close()
    print(f"Migration complete: {len(mapping)} ECR-L* nodes processed.")


def main():
    parser = argparse.ArgumentParser(description="Migration m001: learning node ID stabilization")
    parser.add_argument('--dry-run', action='store_true', help='Print mapping without writing DB')
    parser.add_argument('--execute', action='store_true', help='Execute the migration')
    parser.add_argument('--rebuild-edges-only', action='store_true',
                        help='Only update edges (not node IDs) using saved mapping')
    args = parser.parse_args()

    if args.execute or args.rebuild_edges_only:
        run_migration(dry_run=False, rebuild_edges_only=args.rebuild_edges_only)
    else:
        run_migration(dry_run=True)


if __name__ == '__main__':
    main()
