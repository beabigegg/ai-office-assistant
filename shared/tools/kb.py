#!/usr/bin/env python3
"""Knowledge Base CLI — Unified entry point for KB queries and writes.

EVO-012: DB as source of truth. .md files are export products.

Usage:
    python kb.py catalog                          # lightweight summary (~300 tokens)
    python kb.py search "topic" [--top N]         # semantic search (default)
    python kb.py search "topic" --keyword         # keyword fallback
    python kb.py read D-042 [D-043 ...]           # read full content by ID
    python kb.py next-id                          # next available D-NNN
    python kb.py add decision --id D-146 ...      # add decision (DB + .md)
    python kb.py add learning --id ECR-L95 ...    # add learning note (DB + .md)
    python kb.py update D-042 --status superseded # update entry status
    python kb.py export decisions                 # export DB -> .md
    python kb.py export learning                  # export DB -> .md
    python kb.py validate                         # consistency checks
    python kb.py migrate --execute                # one-time .md -> DB migration
"""
import argparse
import ast
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Resolve paths
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent.parent
KB_ROOT = ROOT / 'shared' / 'kb'
KG_DIR = KB_ROOT / 'knowledge_graph'
DB_PATH = KG_DIR / 'kb_index.db'

DECISIONS_PATH = KB_ROOT / 'decisions.md'
RULES_PATH = KB_ROOT / 'dynamic' / 'ecr_ecn_rules.md'
COLUMN_SEM_PATH = KB_ROOT / 'dynamic' / 'column_semantics.md'
LEARNING_PATH = KB_ROOT / 'dynamic' / 'learning_notes.md'

# Embedding support (lazy)
_embedding_utils = None

# sqlite-vec availability (set at connection time)
_VEC_AVAILABLE = False

def _get_embedding_utils():
    global _embedding_utils
    if _embedding_utils is None:
        try:
            sys.path.insert(0, str(SCRIPT_DIR))
            from embedding_utils import (
                get_embedding, embedding_to_blob, blob_to_embedding,
                cosine_similarity, is_ollama_available,
            )
            _embedding_utils = {
                'get_embedding': get_embedding,
                'embedding_to_blob': embedding_to_blob,
                'blob_to_embedding': blob_to_embedding,
                'cosine_similarity': cosine_similarity,
                'is_ollama_available': is_ollama_available,
            }
        except ImportError:
            _embedding_utils = {}
    return _embedding_utils


def _get_conn():
    global _VEC_AVAILABLE
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    # Try to load sqlite-vec extension for ANN vector search
    try:
        import sqlite_vec
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        _VEC_AVAILABLE = True
    except Exception:
        _VEC_AVAILABLE = False  # fallback to numpy cosine
    return conn


def _ensure_vec_table(conn):
    """Create vec0 virtual table for ANN search (idempotent)."""
    if not _VEC_AVAILABLE:
        return
    try:
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS node_vec USING vec0(
                node_id TEXT PRIMARY KEY,
                embedding FLOAT[2560]
            )
        """)
        conn.commit()
    except Exception:
        pass


def _ensure_schema(conn):
    """Ensure content + meta_json columns exist (Phase 1 upgrade)."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(nodes)").fetchall()}
    if 'content' not in cols:
        conn.execute("ALTER TABLE nodes ADD COLUMN content TEXT")
        conn.commit()
    if 'meta_json' not in cols:
        conn.execute("ALTER TABLE nodes ADD COLUMN meta_json TEXT")
        conn.commit()


def _ensure_snapshots_schema(conn):
    """Ensure session_snapshots table + FTS5 virtual table exist (idempotent).

    Schema:
      session_snapshots(id, date, title, content, source_file, imported_at)
      session_snapshots_fts(title, content) — FTS5 over title+content
    id = snapshot basename without .md (e.g. '2026-04-20', '2026-03-09_evo004')
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS session_snapshots (
            id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            source_file TEXT NOT NULL,
            imported_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS session_snapshots_fts USING fts5(
            title, content, content='session_snapshots', content_rowid='rowid',
            tokenize='unicode61'
        )
    """)
    # Triggers keep FTS in sync with the source table
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS session_snapshots_ai AFTER INSERT ON session_snapshots BEGIN
            INSERT INTO session_snapshots_fts(rowid, title, content)
            VALUES (new.rowid, new.title, new.content);
        END
    """)
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS session_snapshots_ad AFTER DELETE ON session_snapshots BEGIN
            INSERT INTO session_snapshots_fts(session_snapshots_fts, rowid, title, content)
            VALUES ('delete', old.rowid, old.title, old.content);
        END
    """)
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS session_snapshots_au AFTER UPDATE ON session_snapshots BEGIN
            INSERT INTO session_snapshots_fts(session_snapshots_fts, rowid, title, content)
            VALUES ('delete', old.rowid, old.title, old.content);
            INSERT INTO session_snapshots_fts(rowid, title, content)
            VALUES (new.rowid, new.title, new.content);
        END
    """)
    conn.commit()


def _enqueue_for_edges(conn, node_id: str):
    """Add node to pending_edge_queue for auto-edge processing. Idempotent."""
    try:
        conn.execute(
            "INSERT OR IGNORE INTO pending_edge_queue (source_id, queued_at) VALUES (?, ?)",
            (node_id, datetime.now().isoformat())
        )
    except Exception:
        pass  # best-effort, never block writes


def _process_edge_queue(conn, threshold: float = 0.85) -> tuple:
    """Process pending_edge_queue: auto-write high-confidence semantic edges.

    Returns (auto_added, pending_review_list) where:
    - auto_added: count of edges written with auto_generated=1, relation='references'
    - pending_review_list: list of (source_id, target_id, sim, target_text) for cosine 0.70–threshold
    """
    eu = _get_embedding_utils()
    if not eu:
        return 0, []

    queue_nodes = conn.execute(
        "SELECT DISTINCT source_id FROM pending_edge_queue ORDER BY queued_at"
    ).fetchall()
    if not queue_nodes:
        return 0, []

    auto_added = 0
    pending_review = []
    low_bound = 0.70  # below this, not worth reporting

    for qrow in queue_nodes:
        node_id = qrow['source_id']

        emb_row = conn.execute(
            "SELECT embedding FROM node_embeddings WHERE node_id=?", (node_id,)
        ).fetchone()
        if not emb_row:
            # No embedding yet; leave in queue
            continue

        query_emb = eu['blob_to_embedding'](emb_row['embedding'])
        if not query_emb:
            continue

        existing_targets = {r[0] for r in conn.execute(
            "SELECT target_id FROM edges WHERE source_id=?", (node_id,)
        ).fetchall()}
        existing_sources = {r[0] for r in conn.execute(
            "SELECT source_id FROM edges WHERE target_id=?", (node_id,)
        ).fetchall()}
        skip_set = existing_targets | existing_sources | {node_id}

        all_embs = conn.execute(
            "SELECT ne.node_id, ne.embedding, n.target "
            "FROM node_embeddings ne JOIN nodes n ON ne.node_id = n.id "
            "WHERE ne.node_id != ? AND n.status='active'",
            (node_id,)
        ).fetchall()

        for other in all_embs:
            other_id = other['node_id']
            if other_id in skip_set:
                continue
            other_emb = eu['blob_to_embedding'](other['embedding'])
            if not other_emb:
                continue
            sim = eu['cosine_similarity'](query_emb, other_emb)
            if sim >= threshold:
                conn.execute(
                    "INSERT OR IGNORE INTO edges (source_id, target_id, relation, auto_generated) "
                    "VALUES (?, ?, 'references', 1)",
                    (node_id, other_id)
                )
                auto_added += 1
                skip_set.add(other_id)
            elif sim >= low_bound:
                pending_review.append((node_id, other_id, sim, (other['target'] or '')[:60]))

        conn.execute("DELETE FROM pending_edge_queue WHERE source_id=?", (node_id,))

    # Sort pending review by similarity desc
    pending_review.sort(key=lambda x: x[2], reverse=True)
    return auto_added, pending_review


def _try_embed(conn, node_id, text):
    """Try to create/update embedding for a node. Silently skip on any failure."""
    try:
        eu = _get_embedding_utils()
        if not eu or not eu.get('is_ollama_available') or not eu['is_ollama_available']():
            return
        emb = eu['get_embedding'](text)
        if emb is None:
            return
        blob = eu['embedding_to_blob'](emb)
        # Primary store: node_embeddings (backup, always written)
        conn.execute("""
            INSERT INTO node_embeddings (node_id, embedding, embed_text, embed_model, updated_at)
            VALUES (?, ?, ?, 'qwen3-embedding:4b', ?)
            ON CONFLICT(node_id) DO UPDATE SET embedding=excluded.embedding,
                embed_text=excluded.embed_text, updated_at=excluded.updated_at
        """, (node_id, blob, text[:500], datetime.now().isoformat()))
        # Secondary store: node_vec (ANN search, dual-write when sqlite-vec available)
        if _VEC_AVAILABLE:
            _ensure_vec_table(conn)
            conn.execute(
                "INSERT OR REPLACE INTO node_vec (node_id, embedding) VALUES (?, ?)",
                (node_id, blob)
            )
    except Exception:
        pass  # embedding is best-effort, never block writes


# ═══════════════════════════════════════════════════════════
# catalog
# ═══════════════════════════════════════════════════════════

def cmd_catalog(args):
    conn = _get_conn()
    _ensure_schema(conn)

    rows = conn.execute("""
        SELECT node_type,
               COUNT(*) AS total,
               SUM(CASE WHEN status='active' THEN 1 ELSE 0 END) AS active,
               SUM(CASE WHEN status='superseded' THEN 1 ELSE 0 END) AS superseded,
               MAX(created_date) AS latest
        FROM nodes GROUP BY node_type ORDER BY node_type
    """).fetchall()

    with_content = conn.execute("SELECT COUNT(*) FROM nodes WHERE content IS NOT NULL AND content != ''").fetchone()[0]
    total_nodes = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    embedded = conn.execute("SELECT COUNT(*) FROM node_embeddings").fetchone()[0]

    proj_rows = conn.execute("""
        SELECT project, COUNT(*) AS cnt FROM nodes
        WHERE status='active' AND project IS NOT NULL
        GROUP BY project ORDER BY cnt DESC
    """).fetchall()

    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    recent = conn.execute(
        "SELECT id FROM nodes WHERE created_date >= ? ORDER BY created_date DESC, id DESC LIMIT 10",
        (week_ago,)
    ).fetchall()

    today_str = datetime.now().strftime('%Y-%m-%d')
    expired_rows = conn.execute("""
        SELECT id, meta_json FROM nodes
        WHERE status='active' AND meta_json IS NOT NULL AND meta_json LIKE '%review_by%'
    """).fetchall()
    expired_ids = []
    for e in expired_rows:
        try:
            meta = json.loads(e['meta_json']) if e['meta_json'] else {}
            rb = meta.get('review_by', '')
            if rb and rb < today_str:
                expired_ids.append(f"{e['id']}(review_by={rb})")
        except (json.JSONDecodeError, TypeError):
            pass

    print("=== Knowledge Base Catalog ===")
    sync_time = conn.execute('SELECT MAX(synced_at) FROM sync_log').fetchone()[0] or 'never'
    print(f"Last sync: {sync_time}")
    print()
    print(f"{'Kind':<20} | {'Active':>6} | {'Superseded':>10} | {'Latest':<10}")
    print(f"{'-'*20}-+-{'-'*6}-+-{'-'*10}-+-{'-'*10}")
    for r in rows:
        print(f"{r['node_type']:<20} | {r['active'] or 0:>6} | {r['superseded'] or 0:>10} | {r['latest'] or '-':<10}")
    print()
    print(f"Content in DB: {with_content}/{total_nodes} nodes")
    print(f"Embeddings: {embedded}/{total_nodes} nodes")
    projects_str = ', '.join(f"{r['project']}({r['cnt']})" for r in proj_rows[:6])
    print(f"Projects: {projects_str}")
    if recent:
        print(f"Recent (7d): {', '.join(r['id'] for r in recent)}")
    if expired_ids:
        print(f"Expired TTL: {', '.join(expired_ids)}")
    conn.close()


# ═══════════════════════════════════════════════════════════
# suggest-edges: semantic neighbor lookup for Leader edge review
# ═══════════════════════════════════════════════════════════

def _semantic_neighbors(conn, node_id: str, top: int = 8) -> list:
    """Return top-N semantically similar nodes for Leader edge review.

    Uses sqlite-vec ANN (fast) with cosine fallback. No distance threshold —
    returns all candidates ranked by distance so Leader can decide relevance.
    Excludes the node itself and already-existing edge targets.
    """
    eu = _get_embedding_utils()
    if not eu:
        return []

    row = conn.execute(
        "SELECT embedding FROM node_embeddings WHERE node_id=?", (node_id,)
    ).fetchone()
    if not row:
        return []

    existing_targets = {r[0] for r in conn.execute(
        "SELECT target_id FROM edges WHERE source_id=?", (node_id,)
    ).fetchall()}

    query_emb = eu['blob_to_embedding'](row['embedding'])
    query_blob = eu['embedding_to_blob'](query_emb)
    results = []

    if _VEC_AVAILABLE:
        try:
            _ensure_vec_table(conn)
            vec_rows = conn.execute("""
                SELECT v.node_id, v.distance, n.node_type, n.status, n.target, n.summary
                FROM node_vec v JOIN nodes n ON v.node_id = n.id
                WHERE v.embedding MATCH ? AND k = ?
                ORDER BY v.distance
            """, (query_blob, top + 1)).fetchall()
            results = [dict(r) for r in vec_rows
                       if r['node_id'] != node_id
                       and r['node_id'] not in existing_targets][:top]
        except Exception:
            pass

    if not results:
        all_embs = conn.execute(
            "SELECT ne.node_id, ne.embedding, n.node_type, n.status, n.target, n.summary "
            "FROM node_embeddings ne JOIN nodes n ON ne.node_id = n.id "
            "WHERE ne.node_id != ?", (node_id,)
        ).fetchall()
        scored = []
        for r in all_embs:
            if r['node_id'] in existing_targets:
                continue
            emb = eu['blob_to_embedding'](r['embedding'])
            if emb:
                sim = eu['cosine_similarity'](query_emb, emb)
                scored.append((1.0 - sim, dict(r)))  # convert to pseudo-distance
        scored.sort(key=lambda x: x[0])
        results = [r for _, r in scored[:top]]

    return results


# ═══════════════════════════════════════════════════════════
# search
# ═══════════════════════════════════════════════════════════

def _vec_cosine_fallback(conn, eu, query_emb, top, lines):
    """Legacy full-scan cosine search (used when sqlite-vec is unavailable)."""
    all_embs = conn.execute("""
        SELECT ne.node_id, ne.embedding, n.node_type, n.status, n.target, n.summary, n.created_date
        FROM node_embeddings ne JOIN nodes n ON ne.node_id = n.id
        WHERE n.status = 'active'
    """).fetchall()
    results = []
    for row in all_embs:
        emb = eu['blob_to_embedding'](row['embedding'])
        if emb is not None:
            sim = eu['cosine_similarity'](query_emb, emb)
            results.append((sim, row))
    results.sort(key=lambda x: x[0], reverse=True)
    for sim, row in results[:top]:
        skills = _get_related_skills(conn, row['node_id'])
        skill_tag = f"  [→ {', '.join(skills)}]" if skills else ""
        lines.append(f"{row['node_id']:<10} | sim={sim:.3f} | {row['target'][:60]}{skill_tag}")


def cmd_search(args):
    conn = _get_conn()
    _ensure_schema(conn)
    _ensure_vec_table(conn)
    include_snapshots = getattr(args, 'include_snapshots', False)
    if include_snapshots:
        _ensure_snapshots_schema(conn)
    top = args.top or 10
    query = args.query
    budget = getattr(args, 'budget', 0) or 0

    # Collect output lines, then apply budget truncation
    lines = []

    if args.keyword:
        pattern = f"%{query}%"
        rows = conn.execute("""
            SELECT id, node_type, status, target, summary, created_date
            FROM nodes
            WHERE (target LIKE ? OR summary LIKE ? OR content LIKE ?)
              AND status = 'active'
            ORDER BY created_date DESC LIMIT ?
        """, (pattern, pattern, pattern, top)).fetchall()
        for r in rows:
            skills = _get_related_skills(conn, r['id'])
            skill_tag = f"  [→ {', '.join(skills)}]" if skills else ""
            lines.append(f"{r['id']:<10} | {r['node_type']:<18} | {r['target'][:60]}{skill_tag}")
    else:
        eu = _get_embedding_utils()
        if not eu or not eu.get('is_ollama_available') or not eu['is_ollama_available']():
            print("Ollama not available, falling back to keyword search", file=sys.stderr)
            args.keyword = True
            conn.close()
            return cmd_search(args)

        query_emb = eu['get_embedding'](query)
        if query_emb is None:
            print("Failed to get embedding, falling back to keyword", file=sys.stderr)
            args.keyword = True
            conn.close()
            return cmd_search(args)

        query_blob = eu['embedding_to_blob'](query_emb)

        # Prefer sqlite-vec ANN search; fallback to numpy cosine full-scan
        if _VEC_AVAILABLE:
            _ensure_vec_table(conn)
            try:
                vec_rows = conn.execute("""
                    SELECT v.node_id, v.distance,
                           n.node_type, n.status, n.target, n.summary, n.created_date
                    FROM node_vec v
                    JOIN nodes n ON v.node_id = n.id
                    WHERE n.status = 'active'
                      AND v.embedding MATCH ?
                      AND k = ?
                    ORDER BY v.distance
                """, (query_blob, top)).fetchall()
                for row in vec_rows:
                    # sqlite-vec returns L2 distance; convert to approx similarity for display
                    sim = max(0.0, 1.0 - row['distance'])
                    skills = _get_related_skills(conn, row['node_id'])
                    skill_tag = f"  [→ {', '.join(skills)}]" if skills else ""
                    lines.append(f"{row['node_id']:<10} | sim={sim:.3f} | {row['target'][:60]}{skill_tag}")
            except Exception as vec_err:
                print(f"sqlite-vec search failed ({vec_err}), falling back to cosine", file=sys.stderr)
                _vec_cosine_fallback(conn, eu, query_emb, top, lines)
        else:
            _vec_cosine_fallback(conn, eu, query_emb, top, lines)

    if include_snapshots:
        snap_rows = _search_snapshots_fts(conn, query, top)
        if snap_rows:
            lines.append("")
            lines.append(f"--- Session snapshots (FTS5, top {len(snap_rows)}) ---")
            for r in snap_rows:
                snip = (r['snip'] or '').replace('\n', ' ').strip()
                date_tag = r['date'] or '?'
                title = (r['title'] or '')[:50]
                lines.append(f"SNAP:{r['id']:<22} | {date_tag} | {title} — {snip[:80]}")
    conn.close()

    # Apply budget truncation
    if budget > 0:
        total_chars = 0
        for i, line in enumerate(lines):
            total_chars += len(line) + 1  # +1 for newline
            if total_chars > budget:
                for ln in lines[:i]:
                    print(ln)
                remaining = len(lines) - i
                print(f"... ({remaining} more results truncated, budget={budget})")
                print(f"Use `kb.py read <ID>` to read specific entries.")
                return
    for line in lines:
        print(line)


# ═══════════════════════════════════════════════════════════
# read
# ═══════════════════════════════════════════════════════════

def cmd_read(args):
    conn = _get_conn()
    _ensure_schema(conn)
    _ensure_snapshots_schema(conn)
    for entry_id in args.ids:
        # Snapshot read: SNAP:<id> or bare date-like stem
        snap_id = None
        if entry_id.startswith('SNAP:'):
            snap_id = entry_id.split(':', 1)[1]
        elif _SNAPSHOT_DATE_RE.match(entry_id):
            snap_id = entry_id
        if snap_id:
            srow = conn.execute(
                "SELECT id, date, title, content, source_file FROM session_snapshots WHERE id=?",
                (snap_id,)
            ).fetchone()
            if srow:
                print(f"### SNAP:{srow['id']} -- {srow['date']} -- {srow['source_file']}")
                print(f"# {srow['title']}")
                print(srow['content'])
                print()
                continue
            # fall through to node lookup if not found as snapshot

        row = conn.execute(
            "SELECT id, node_type, status, project, target, summary, content, meta_json, created_date FROM nodes WHERE id = ?",
            (entry_id,)
        ).fetchone()
        if not row:
            print(f"[NOT FOUND] {entry_id}")
            continue
        print(f"### {row['id']} -- {row['created_date'] or '?'} -- {row['project'] or '?'}")
        if row['meta_json']:
            print(f"<!-- kb: {row['meta_json']} -->")
        if row['content']:
            print(row['content'])
        else:
            print(f"Target: {row['target']}")
            print(f"Summary: {row['summary']}")
        print()
    conn.close()


# ═══════════════════════════════════════════════════════════
# next-id
# ═══════════════════════════════════════════════════════════

def cmd_next_id(args):
    conn = _get_conn()
    row = conn.execute("SELECT id FROM nodes WHERE node_type='decision' ORDER BY id DESC LIMIT 1").fetchone()
    if row:
        m = re.match(r'D-(\d+)', row['id'])
        last_num = int(m.group(1)) if m else 0
    else:
        last_num = 0
    # Also check .md for safety during transition
    if DECISIONS_PATH.exists():
        tail_bytes = min(DECISIONS_PATH.stat().st_size, 8192)
        with open(DECISIONS_PATH, 'rb') as f:
            if DECISIONS_PATH.stat().st_size > tail_bytes:
                f.seek(-tail_bytes, 2)
            tail = f.read().decode('utf-8', errors='replace')
        md_ids = [int(x) for x in re.findall(r'### D-(\d+)', tail)]
        if md_ids:
            last_num = max(last_num, max(md_ids))
    next_num = last_num + 1
    print(json.dumps({"next_id": f"D-{next_num:03d}", "last_id": f"D-{last_num:03d}"}))
    conn.close()


# ═══════════════════════════════════════════════════════════
# add decision / add learning
# ═══════════════════════════════════════════════════════════

def cmd_add_decision(args):
    """Write decision to DB (source of truth) + append to .md (export)."""
    conn = _get_conn()
    _ensure_schema(conn)

    node_id = args.id
    m = re.match(r'^D-(\d+)$', node_id)
    if not m:
        print(json.dumps({"ok": False, "error": f"Invalid ID: {node_id}"}))
        sys.exit(1)

    # Check sequential
    row = conn.execute("SELECT id FROM nodes WHERE node_type='decision' ORDER BY id DESC LIMIT 1").fetchone()
    if row:
        last_m = re.match(r'D-(\d+)', row['id'])
        last_num = int(last_m.group(1)) if last_m else 0
    else:
        last_num = 0
    # Also check .md
    if DECISIONS_PATH.exists():
        tail_bytes = min(DECISIONS_PATH.stat().st_size, 8192)
        with open(DECISIONS_PATH, 'rb') as f:
            if DECISIONS_PATH.stat().st_size > tail_bytes:
                f.seek(-tail_bytes, 2)
            tail = f.read().decode('utf-8', errors='replace')
        md_ids = [int(x) for x in re.findall(r'### D-(\d+)', tail)]
        if md_ids:
            last_num = max(last_num, max(md_ids))

    new_num = int(m.group(1))
    if new_num != last_num + 1:
        print(json.dumps({"ok": False, "error": f"ID not sequential: {node_id}, expected D-{last_num+1:03d}"}))
        sys.exit(1)

    # Build meta
    _ignore = {'n/a', 'na', 'none', '', '-'}
    meta = {"status": args.status or "active", "target": args.target}
    if args.supersedes:
        meta["supersedes"] = args.supersedes
    if args.refs_skill and args.refs_skill.strip().lower() not in _ignore:
        meta["refs_skill"] = args.refs_skill
    if args.refs_db and args.refs_db.strip().lower() not in _ignore:
        meta["refs_db"] = args.refs_db
    if args.affects and args.affects.strip().lower() not in _ignore:
        meta["affects"] = args.affects
    if args.review_by:
        meta["review_by"] = args.review_by

    # Build content body
    content_lines = [
        f"- 問題：{args.question}",
        f"- 決定：{args.decision}",
        f"- 影響：{args.impact}",
    ]
    if args.source:
        content_lines.append(f"- 來源：{args.source}")
    content_body = '\n'.join(content_lines)

    # Build summary
    summary = args.decision[:120]

    # Refs as JSON arrays
    def _to_list(val):
        if not val or val.strip().lower() in _ignore:
            return None
        return json.dumps([v.strip() for v in val.split('|') if v.strip()])

    refs_skill_json = _to_list(args.refs_skill)
    refs_db_json = _to_list(args.refs_db)
    affects_json = _to_list(args.affects)

    # ── Write to DB ──
    conn.execute("""
        INSERT OR REPLACE INTO nodes
        (id, node_type, project, status, target, summary, content, meta_json,
         refs_skill, refs_db, affects_project, created_date, last_synced)
        VALUES (?, 'decision', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        node_id, args.project, args.status or 'active', args.target, summary,
        content_body, json.dumps(meta, ensure_ascii=False),
        refs_skill_json, refs_db_json, affects_json,
        args.date, datetime.now().isoformat()
    ))

    # Build edges for supersedes
    if args.supersedes:
        for sid in [s.strip() for s in args.supersedes.split(',')]:
            conn.execute("INSERT OR IGNORE INTO edges (source_id, target_id, relation) VALUES (?, ?, 'supersedes')", (node_id, sid))
            conn.execute("INSERT OR IGNORE INTO edges (source_id, target_id, relation) VALUES (?, ?, 'superseded_by')", (sid, node_id))
            # Mark old as superseded
            conn.execute("UPDATE nodes SET status='superseded' WHERE id=?", (sid,))

    conn.commit()

    # Embed + enqueue for auto-edge generation
    embed_text = f"{args.target} {summary}"
    _try_embed(conn, node_id, embed_text)
    _enqueue_for_edges(conn, node_id)
    conn.commit()

    # ── EVO-016: DB is source of truth; .md export happens at post_task end ──
    queue_size = conn.execute("SELECT COUNT(*) FROM pending_edge_queue").fetchone()[0]
    result = {
        "ok": True, "id": node_id,
        "db": str(DB_PATH.relative_to(ROOT)),
        "hint_md": "Run `python shared/tools/kb.py export decisions` to refresh .md export.",
    }
    if queue_size >= 5:
        result["hint"] = f"edge_queue={queue_size}，建議執行 kb.py build-edges 自動補齊關聯邊"
    print(json.dumps(result))
    conn.close()


def cmd_add_learning(args):
    """Write learning note to DB (source of truth) + append to .md (export)."""
    conn = _get_conn()
    _ensure_schema(conn)

    node_id = args.id

    content_lines = [
        f"- 觀察：{args.content}",
        f"- 信心度：{args.confidence}",
    ]
    if args.project:
        content_lines.append(f"- 相關專案：{args.project}")
    if args.related_decision:
        content_lines.append(f"- 相關決策：{args.related_decision}")
    content_body = '\n'.join(content_lines)

    # ── Write to DB ──
    conn.execute("""
        INSERT OR REPLACE INTO nodes
        (id, node_type, project, status, target, summary, content, meta_json, created_date, last_synced)
        VALUES (?, 'learning', ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        node_id, args.project or 'ecr-ecn', args.status or 'active',
        args.title[:80], args.title[:120], content_body,
        json.dumps({"confidence": args.confidence}, ensure_ascii=False),
        args.date, datetime.now().isoformat()
    ))

    # Edges
    if args.related_decision:
        conn.execute("INSERT OR IGNORE INTO edges (source_id, target_id, relation) VALUES (?, ?, 'references')", (node_id, args.related_decision))
    conn.commit()

    _try_embed(conn, node_id, f"{args.title} {content_body[:300]}")
    _enqueue_for_edges(conn, node_id)
    conn.commit()

    # ── EVO-016: DB is source of truth; .md export happens at post_task end ──
    queue_size = conn.execute("SELECT COUNT(*) FROM pending_edge_queue").fetchone()[0]
    result = {
        "ok": True, "id": node_id,
        "db": str(DB_PATH.relative_to(ROOT)),
        "hint_md": "Run `python shared/tools/kb.py export learning` to refresh .md export.",
    }
    if queue_size >= 5:
        result["hint"] = f"edge_queue={queue_size}，建議執行 kb.py build-edges 自動補齊關聯邊"
    print(json.dumps(result))
    conn.close()


# ═══════════════════════════════════════════════════════════
# update
# ═══════════════════════════════════════════════════════════

def cmd_update(args):
    """Update status or fields of an existing entry."""
    conn = _get_conn()
    _ensure_schema(conn)
    row = conn.execute("SELECT * FROM nodes WHERE id = ?", (args.entry_id,)).fetchone()
    if not row:
        print(json.dumps({"ok": False, "error": f"Not found: {args.entry_id}"}))
        sys.exit(1)

    updates = []
    params = []
    if args.status:
        updates.append("status = ?")
        params.append(args.status)
    if args.superseded_by:
        # Mark this entry as superseded by another
        conn.execute("INSERT OR IGNORE INTO edges (source_id, target_id, relation) VALUES (?, ?, 'superseded_by')", (args.entry_id, args.superseded_by))
        conn.execute("INSERT OR IGNORE INTO edges (source_id, target_id, relation) VALUES (?, ?, 'supersedes')", (args.superseded_by, args.entry_id))
        if not args.status:
            updates.append("status = ?")
            params.append('superseded')

    if updates:
        updates.append("last_synced = ?")
        params.append(datetime.now().isoformat())
        params.append(args.entry_id)
        conn.execute(f"UPDATE nodes SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
        print(json.dumps({"ok": True, "id": args.entry_id, "updated": [u.split('=')[0].strip() for u in updates[:-1]]}))
    else:
        print(json.dumps({"ok": False, "error": "Nothing to update"}))
    conn.close()


# ═══════════════════════════════════════════════════════════
# export
# ═══════════════════════════════════════════════════════════

def cmd_export(args):
    """Export DB content back to .md files."""
    conn = _get_conn()
    _ensure_schema(conn)
    target = args.target

    if target in ('decisions', 'all'):
        rows = conn.execute("""
            SELECT id, node_type, project, status, target, summary, content, meta_json, created_date
            FROM nodes WHERE node_type = 'decision'
            ORDER BY id
        """).fetchall()
        lines = ["# 決策日誌 (Decisions Log)\n"]
        lines.append("> 由 `kb.py export decisions` 從 DB 匯出。DB 是 source of truth。\n")
        for r in rows:
            meta = json.loads(r['meta_json']) if r['meta_json'] else {}
            meta_parts = [f"status={r['status']}"]
            if r['target']:
                meta_parts.append(f"target={r['target']}")
            for k in ['supersedes', 'refs_skill', 'refs_db', 'affects', 'review_by']:
                if meta.get(k):
                    meta_parts.append(f"{k}={meta[k]}")
            status_marker = ""
            if r['status'] == 'superseded':
                # Check if superseded_by exists
                sup_by = conn.execute(
                    "SELECT source_id FROM edges WHERE target_id=? AND relation='supersedes'",
                    (r['id'],)
                ).fetchone()
                if sup_by:
                    status_marker = f" **[已修正 → {sup_by['source_id']}]**"

            lines.append(f"\n### {r['id']} -- {r['created_date'] or '?'} -- {r['project'] or '?'}{status_marker}")
            lines.append(f"<!-- kb: {', '.join(meta_parts)} -->")
            if r['content']:
                lines.append(r['content'])
            else:
                lines.append(f"- 決定：{r['summary']}")
            lines.append("")

        out_path = DECISIONS_PATH
        out_path.write_text('\n'.join(lines), encoding='utf-8')
        print(f"Exported {len(rows)} decisions -> {out_path.relative_to(ROOT)}")

    if target in ('learning', 'all'):
        rows = conn.execute("""
            SELECT id, node_type, project, status, target, summary, content, meta_json, created_date
            FROM nodes WHERE node_type = 'learning'
            ORDER BY id
        """).fetchall()
        lines = ["# 學習筆記 (Learning Notes)\n"]
        lines.append("> 由 `kb.py export learning` 從 DB 匯出。DB 是 source of truth。\n")
        for r in rows:
            date_str = f" — {r['created_date']}" if r['created_date'] else ""
            lines.append(f"\n### {r['id']} {r['target']}{date_str}")
            lines.append(f"<!-- status: {r['status']} -->")
            if r['content']:
                lines.append(r['content'])
            else:
                lines.append(f"- 觀察：{r['summary']}")
            lines.append("")

        out_path = LEARNING_PATH
        out_path.write_text('\n'.join(lines), encoding='utf-8')
        print(f"Exported {len(rows)} learning notes -> {out_path.relative_to(ROOT)}")

    conn.close()


# ═══════════════════════════════════════════════════════════
# validate
# ═══════════════════════════════════════════════════════════

def cmd_validate(args):
    """Consistency checks (EVO-016: delegates to KBIndex.validate for full checks)."""
    KBIndex = _get_kb_index()
    kb = KBIndex()
    try:
        code = kb.validate(
            quiet=getattr(args, 'quiet', False),
            strict=getattr(args, 'strict', False),
        )
        sys.exit(code)
    finally:
        kb.close()


# ═══════════════════════════════════════════════════════════
# migrate (one-time .md -> DB)
# ═══════════════════════════════════════════════════════════

def _parse_decision_blocks(path):
    content = path.read_text(encoding='utf-8')
    blocks = re.split(r'(?=^### D-\d+)', content, flags=re.MULTILINE)
    results = []
    for block in blocks:
        m = re.match(r'^### (D-(\d+))\s*--\s*(\d{4}-\d{2}-\d{2})\s*--\s*(.+?)(?:\s*\*\*.*\*\*)?\s*$',
                     block, re.MULTILINE)
        if not m:
            continue
        node_id = m.group(1)
        meta = {}
        meta_match = re.search(r'<!--\s*kb:\s*(.+?)\s*-->', block)
        if meta_match:
            for pair in meta_match.group(1).split(','):
                if '=' in pair:
                    k, v = pair.split('=', 1)
                    meta[k.strip()] = v.strip()
        body_lines = []
        for line in block.strip().split('\n'):
            if line.startswith('### D-') or line.strip().startswith('<!-- kb:'):
                continue
            body_lines.append(line)
        body = '\n'.join(body_lines).strip()
        results.append((node_id, body, json.dumps(meta, ensure_ascii=False) if meta else None))
    return results


def _parse_rule_blocks(path):
    content = path.read_text(encoding='utf-8')
    blocks = re.split(r'(?=^### ECR-R\d+)', content, flags=re.MULTILINE)
    results = []
    for block in blocks:
        m = re.match(r'^### (ECR-R\d+)', block, re.MULTILINE)
        if not m:
            continue
        results.append((m.group(1), block.strip(), None))
    return results


def _parse_learning_blocks(path):
    content = path.read_text(encoding='utf-8')
    blocks = re.split(r'(?=^### )', content, flags=re.MULTILINE)
    results = []
    idx = 0
    for block in blocks:
        m = re.match(r'^### (.+?)(?:\s*—\s*\d{4}-\d{2}-\d{2})?\s*', block, re.MULTILINE)
        if not m:
            continue
        idx += 1
        node_id = f"ECR-L{idx:02d}"
        id_match = re.match(r'^### (ECR-L\d+)', block)
        if id_match:
            node_id = id_match.group(1)
        results.append((node_id, block.strip(), None))
    return results


def _parse_column_sem_blocks(path):
    content = path.read_text(encoding='utf-8')
    blocks = re.split(r'(?=^### )', content, flags=re.MULTILINE)
    results = []
    idx = 0
    for block in blocks:
        m = re.match(r'^### (.+?)(?:\s*\[PROMOTED\])?\s*$', block, re.MULTILINE)
        if not m:
            continue
        idx += 1
        results.append((f"CS-{idx:03d}", block.strip(), None))
    return results


def cmd_migrate(args):
    conn = _get_conn()
    _ensure_schema(conn)

    all_blocks = []
    for parser_fn, path, label in [
        (_parse_decision_blocks, DECISIONS_PATH, 'decisions.md'),
        (_parse_rule_blocks, RULES_PATH, 'ecr_ecn_rules.md'),
        (_parse_learning_blocks, LEARNING_PATH, 'learning_notes.md'),
        (_parse_column_sem_blocks, COLUMN_SEM_PATH, 'column_semantics.md'),
    ]:
        if path.exists():
            before = len(all_blocks)
            all_blocks.extend(parser_fn(path))
            print(f"Parsed {label}: {len(all_blocks) - before} entries")

    existing_ids = {row[0] for row in conn.execute("SELECT id FROM nodes").fetchall()}
    matched = [(nid, c, m) for nid, c, m in all_blocks if nid in existing_ids]
    unmatched = [(nid, c, m) for nid, c, m in all_blocks if nid not in existing_ids]

    print(f"\nTotal parsed: {len(all_blocks)}")
    print(f"Matched: {len(matched)}")
    if unmatched:
        print(f"Unmatched: {len(unmatched)} — {', '.join(u[0] for u in unmatched[:10])}")

    if args.dry_run:
        print("\n[DRY RUN] No changes made.")
        conn.close()
        return

    updated = 0
    for nid, content, meta in matched:
        if meta:
            conn.execute("UPDATE nodes SET content=?, meta_json=? WHERE id=?", (content, meta, nid))
        else:
            conn.execute("UPDATE nodes SET content=? WHERE id=?", (content, nid))
        updated += 1
    conn.commit()

    with_content = conn.execute("SELECT COUNT(*) FROM nodes WHERE content IS NOT NULL AND content != ''").fetchone()[0]
    total = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    print(f"\n[DONE] Updated {updated} nodes. Coverage: {with_content}/{total} ({with_content*100//total}%)")
    conn.close()


# ═══════════════════════════════════════════════════════════
# trace
# ═══════════════════════════════════════════════════════════

def cmd_trace(args):
    """Trace a node's relationships via edges."""
    conn = _get_conn()
    node_id = args.node_id

    node = conn.execute("SELECT id, node_type, status, target, created_date FROM nodes WHERE id=?", (node_id,)).fetchone()
    if not node:
        print(f"[NOT FOUND] {node_id}")
        conn.close()
        return

    print(f"### {node['id']} ({node['node_type']}, {node['status']}) — {node['target'][:60]}")

    out_edges = conn.execute("SELECT target_id, relation FROM edges WHERE source_id=? ORDER BY relation", (node_id,)).fetchall()
    in_edges = conn.execute("SELECT source_id, relation FROM edges WHERE target_id=? ORDER BY relation", (node_id,)).fetchall()

    if out_edges:
        print("  outgoing:")
        for e in out_edges:
            tid = e['target_id']
            # Try to get summary for node targets
            tnode = conn.execute("SELECT target FROM nodes WHERE id=?", (tid,)).fetchone()
            label = tnode['target'][:50] if tnode else ""
            print(f"    → {e['relation']}: {tid} {label}")
    if in_edges:
        print("  incoming:")
        for e in in_edges:
            sid = e['source_id']
            snode = conn.execute("SELECT target FROM nodes WHERE id=?", (sid,)).fetchone()
            label = snode['target'][:50] if snode else ""
            print(f"    ← {e['relation']}: {sid} {label}")

    if not out_edges and not in_edges:
        print("  (no edges)")
    conn.close()


# ═══════════════════════════════════════════════════════════
# impacts
# ═══════════════════════════════════════════════════════════

def cmd_impacts(args):
    """Find nodes that affect a given project or reference a skill."""
    conn = _get_conn()
    conditions = []
    params = []

    if args.skill:
        conditions.append("refs_skill LIKE ?")
        params.append(f"%{args.skill}%")
    if args.project:
        conditions.append("affects_project LIKE ?")
        params.append(f"%{args.project}%")

    if not conditions:
        print("Specify --skill or --project")
        conn.close()
        return

    rows = conn.execute(
        f"SELECT id, node_type, status, target, created_date FROM nodes WHERE ({' OR '.join(conditions)}) AND status='active' ORDER BY id",
        params
    ).fetchall()

    for r in rows:
        print(f"{r['id']:<10} | {r['node_type']:<18} | {r['target'][:60]}")
    print(f"\nTotal: {len(rows)} active nodes")
    conn.close()


# ═══════════════════════════════════════════════════════════
# build-edges
# ═══════════════════════════════════════════════════════════

def cmd_build_edges(args):
    """Materialize JSON reference fields into proper graph edges. Idempotent."""
    conn = _get_conn()
    _ensure_vec_table(conn)
    added = 0
    skipped = 0


    # 1. refs_skill → edges
    rows = conn.execute("SELECT id, refs_skill FROM nodes WHERE refs_skill IS NOT NULL AND refs_skill != '' AND refs_skill != '[]'").fetchall()
    for r in rows:
        try:
            skills = json.loads(r['refs_skill'])
            for s in skills:
                s = s.strip()
                if s:
                    res = conn.execute("INSERT OR IGNORE INTO edges (source_id, target_id, relation) VALUES (?, ?, 'refs_skill')", (r['id'], f"SKILL:{s}"))
                    added += res.rowcount
        except (json.JSONDecodeError, TypeError):
            skipped += 1

    # 2. refs_db → edges
    rows = conn.execute("SELECT id, refs_db FROM nodes WHERE refs_db IS NOT NULL AND refs_db != '' AND refs_db != '[]'").fetchall()
    for r in rows:
        try:
            dbs = json.loads(r['refs_db'])
            for d in dbs:
                d = d.strip()
                if d:
                    res = conn.execute("INSERT OR IGNORE INTO edges (source_id, target_id, relation) VALUES (?, ?, 'refs_db')", (r['id'], f"DB:{d}"))
                    added += res.rowcount
        except (json.JSONDecodeError, TypeError):
            skipped += 1

    # 3. affects_project → edges
    rows = conn.execute("SELECT id, affects_project FROM nodes WHERE affects_project IS NOT NULL AND affects_project != '' AND affects_project != '[]'").fetchall()
    for r in rows:
        try:
            projects = json.loads(r['affects_project'])
            for p in projects:
                p = p.strip()
                if p:
                    res = conn.execute("INSERT OR IGNORE INTO edges (source_id, target_id, relation) VALUES (?, ?, 'affects')", (r['id'], f"PROJECT:{p}"))
                    added += res.rowcount
        except (json.JSONDecodeError, TypeError):
            skipped += 1

    # 4. Scan SKILL.md files for D-NNN references → cited_by_skill edges
    skills_dir = ROOT / '.claude' / 'skills-on-demand'
    if skills_dir.exists():
        valid_ids = {row[0] for row in conn.execute("SELECT id FROM nodes WHERE id LIKE 'D-%'").fetchall()}
        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_name = skill_dir.name
            for md_file in skill_dir.rglob("*.md"):
                try:
                    content = md_file.read_text(encoding='utf-8')
                except (OSError, UnicodeDecodeError):
                    continue
                refs = set(re.findall(r'\bD-(\d{3})\b', content))
                for ref_num in refs:
                    did = f"D-{ref_num}"
                    if did in valid_ids:
                        res = conn.execute("INSERT OR IGNORE INTO edges (source_id, target_id, relation) VALUES (?, ?, 'cited_by_skill')",
                                           (f"SKILL:{skill_name}", did))
                        added += res.rowcount

    conn.commit()

    # Process pending_edge_queue: auto-confirm high-confidence semantic edges
    threshold = getattr(args, 'threshold', 0.85)
    queue_before = conn.execute("SELECT COUNT(DISTINCT source_id) FROM pending_edge_queue").fetchone()[0]
    auto_added, pending_review = _process_edge_queue(conn, threshold=threshold)
    conn.commit()

    # Report
    edge_counts = conn.execute("SELECT relation, COUNT(*) FROM edges GROUP BY relation ORDER BY relation").fetchall()
    total = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
    print(f"Build-edges complete: {added} new edges added ({skipped} parse errors)")
    if queue_before > 0:
        print(f"\nAuto-edge queue: {queue_before} nodes processed, {auto_added} edges auto-written (cosine >= {threshold})")
        if pending_review:
            top_pending = pending_review[:10]
            print(f"Pending review ({len(pending_review)} pairs, showing top 10 — use kb.py add-edge to confirm):")
            print(f"  {'sim':>5}  {'source':<12} {'target':<12} target_text")
            for src, tgt, sim, txt in top_pending:
                print(f"  {sim:.3f}  {src:<12} {tgt:<12} {txt}")
    print(f"\nEdge summary ({total} total):")
    for ec in edge_counts:
        print(f"  {ec[0]:<20} {ec[1]}")
    conn.close()


def _get_related_skills(conn, node_id):
    """Get skill names related to a node via edges."""
    skills = set()
    # Direct: this node refs a skill
    rows = conn.execute("SELECT target_id FROM edges WHERE source_id=? AND relation='refs_skill'", (node_id,)).fetchall()
    for r in rows:
        skills.add(r[0].replace('SKILL:', ''))
    # Reverse: a skill cites this node
    rows = conn.execute("SELECT source_id FROM edges WHERE target_id=? AND relation='cited_by_skill'", (node_id,)).fetchall()
    for r in rows:
        skills.add(r[0].replace('SKILL:', ''))
    return sorted(skills)


# ═══════════════════════════════════════════════════════════
# suggest-edges / add-edge  (Leader-driven edge review)
# ═══════════════════════════════════════════════════════════

def cmd_suggest_edges(args):
    """Print semantic neighbors of a node for Leader to review and classify.

    Leader reads the output, decides relationships, then calls:
        kb.py add-edge <source> <target> <relation>
    """
    conn = _get_conn()
    node = conn.execute(
        "SELECT id, node_type, status, target, summary FROM nodes WHERE id=?",
        (args.node_id,)
    ).fetchone()
    if not node:
        print(f"[ERROR] Node '{args.node_id}' not found")
        return

    print(f"Node: {node['id']} ({node['node_type']}/{node['status']})")
    print(f"Target: {node['target']}")
    print(f"Summary: {(node['summary'] or '')[:120]}")
    print()

    neighbors = _semantic_neighbors(conn, args.node_id, top=args.top)
    if not neighbors:
        print("No semantic neighbors found (no embeddings or all already linked).")
        return

    print(f"Semantic neighbors (top {len(neighbors)}, excluding existing edges):")
    print(f"{'#':<3} {'dist':>6}  {'ID':<12} {'type':<14} {'status':<12} summary")
    print("-" * 90)
    for i, n in enumerate(neighbors, 1):
        dist = n.get('distance', 0)
        summary = (n.get('summary') or '')[:55]
        print(f"{i:<3} {dist:>6.3f}  {n['node_id']:<12} {n['node_type']:<14} {n['status']:<12} {summary}")

    print()
    print("Relations: references | affects | supersedes | (skip = unrelated)")
    print(f"Write edge: kb.py add-edge {args.node_id} <target_id> <relation>")


def cmd_add_edge(args):
    """Write a Leader-reviewed edge to the knowledge graph.

    Sets auto_generated=0 to distinguish from automated detection.
    """
    conn = _get_conn()
    _VALID = {'references', 'affects', 'supersedes'}
    if args.relation not in _VALID:
        print(f"[ERROR] relation must be one of: {', '.join(sorted(_VALID))}")
        return

    # Verify both nodes exist
    src = conn.execute("SELECT id FROM nodes WHERE id=?", (args.source_id,)).fetchone()
    tgt = conn.execute("SELECT id FROM nodes WHERE id=?", (args.target_id,)).fetchone()
    if not src:
        print(f"[ERROR] Source '{args.source_id}' not found")
        return
    if not tgt:
        print(f"[ERROR] Target '{args.target_id}' not found")
        return

    conn.execute(
        "INSERT OR REPLACE INTO edges (source_id, target_id, relation, auto_generated) "
        "VALUES (?, ?, ?, 0)",
        (args.source_id, args.target_id, args.relation)
    )
    conn.commit()
    print(f"[OK] edge: {args.source_id} --[{args.relation}]--> {args.target_id}")


# ═══════════════════════════════════════════════════════════
# session snapshots (FTS5)
# ═══════════════════════════════════════════════════════════

_SNAPSHOT_DATE_RE = re.compile(r'(\d{4}-\d{2}-\d{2})')


def _parse_snapshot(path: Path) -> dict:
    """Parse a snapshot .md file. Returns dict(id, date, title, content, source_file)."""
    stem = path.stem  # e.g. '2026-04-20' or '2026-03-09_evo004'
    m = _SNAPSHOT_DATE_RE.match(stem)
    date = m.group(1) if m else ''
    text = path.read_text(encoding='utf-8', errors='replace')
    # Title: first non-empty H1 line; fallback to stem
    title = stem
    for line in text.splitlines():
        s = line.strip()
        if s.startswith('# '):
            title = s.lstrip('# ').strip() or stem
            break
    return {
        'id': stem,
        'date': date,
        'title': title,
        'content': text,
        'source_file': str(path.relative_to(ROOT)).replace('\\', '/'),
    }


def cmd_import_snapshot(args):
    """Import session snapshot(s) into session_snapshots + FTS index.

    Accepts a single file or a directory. If omitted, imports
    shared/kb/memory/*.md.  Skips README.md. Idempotent — re-import
    updates existing rows.
    """
    conn = _get_conn()
    _ensure_snapshots_schema(conn)

    paths: list[Path] = []
    if args.path:
        target = Path(args.path)
        if not target.is_absolute():
            target = (ROOT / args.path).resolve()
        if not target.exists():
            print(json.dumps({"ok": False, "error": f"not found: {target}"}))
            sys.exit(1)
        if target.is_dir():
            paths = sorted(target.glob('*.md'))
        else:
            paths = [target]
    else:
        mem_dir = KB_ROOT / 'memory'
        if not mem_dir.exists():
            print(json.dumps({"ok": False, "error": f"memory dir missing: {mem_dir}"}))
            sys.exit(1)
        paths = sorted(mem_dir.glob('*.md'))

    now = datetime.now().isoformat()
    imported = 0
    updated = 0
    skipped = 0
    for p in paths:
        if p.name.lower() == 'readme.md':
            skipped += 1
            continue
        # Architecture-review-style docs are also skipped unless explicitly pointed at
        if not _SNAPSHOT_DATE_RE.match(p.stem) and not args.path:
            skipped += 1
            continue
        try:
            snap = _parse_snapshot(p)
        except (OSError, UnicodeDecodeError) as exc:
            print(f"[WARN] skip {p.name}: {exc}", file=sys.stderr)
            skipped += 1
            continue
        existing = conn.execute(
            "SELECT id FROM session_snapshots WHERE id=?", (snap['id'],)
        ).fetchone()
        conn.execute(
            """INSERT OR REPLACE INTO session_snapshots
               (id, date, title, content, source_file, imported_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (snap['id'], snap['date'], snap['title'], snap['content'],
             snap['source_file'], now)
        )
        if existing:
            updated += 1
        else:
            imported += 1
    conn.commit()

    total = conn.execute("SELECT COUNT(*) FROM session_snapshots").fetchone()[0]
    fts_total = conn.execute("SELECT COUNT(*) FROM session_snapshots_fts").fetchone()[0]
    print(json.dumps({
        "ok": True,
        "scanned": len(paths),
        "imported": imported,
        "updated": updated,
        "skipped": skipped,
        "total_snapshots": total,
        "fts_rows": fts_total,
    }, ensure_ascii=False))
    conn.close()


def _search_snapshots_fts(conn, query: str, top: int) -> list:
    """Return list of (snap_id, date, title, snippet, rank)."""
    # Sanitize FTS5 query: escape double quotes, wrap in phrase to allow punctuation
    safe = query.replace('"', '""')
    fts_query = f'"{safe}"'
    try:
        rows = conn.execute("""
            SELECT s.id, s.date, s.title,
                   snippet(session_snapshots_fts, 1, '[', ']', '…', 12) AS snip,
                   bm25(session_snapshots_fts) AS rank
            FROM session_snapshots_fts
            JOIN session_snapshots s ON s.rowid = session_snapshots_fts.rowid
            WHERE session_snapshots_fts MATCH ?
            ORDER BY rank LIMIT ?
        """, (fts_query, top)).fetchall()
    except sqlite3.OperationalError:
        # FTS5 MATCH syntax error → fall back to LIKE
        rows = conn.execute("""
            SELECT id, date, title, substr(content, 1, 120) AS snip, 0 AS rank
            FROM session_snapshots
            WHERE title LIKE ? OR content LIKE ?
            ORDER BY date DESC LIMIT ?
        """, (f"%{query}%", f"%{query}%", top)).fetchall()
    return rows


# ═══════════════════════════════════════════════════════════
# main
# ═══════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════
# tool-graph (Tier-aware Python import dependency graph)
# ═══════════════════════════════════════════════════════════

# Python stdlib module names — anything else is suspect for "internal"
_STDLIB_HINT = {
    'os', 'sys', 're', 'json', 'sqlite3', 'argparse', 'pathlib', 'datetime',
    'time', 'collections', 'itertools', 'functools', 'typing', 'math',
    'subprocess', 'shutil', 'tempfile', 'logging', 'hashlib', 'base64',
    'csv', 'io', 'glob', 'ast', 'random', 'enum', 'dataclasses', 'unittest',
    'asyncio', 'concurrent', 'threading', 'multiprocessing', 'pickle',
    'copy', 'string', 'textwrap', 'urllib', 'http', 'socket', 'struct',
    'warnings', 'inspect', 'traceback', 'contextlib', 'abc', 'types',
    'operator', 'decimal', 'fractions', 'statistics', 'uuid', 'platform',
    'getpass', 'locale', 'codecs', 'gzip', 'zipfile', 'tarfile', 'xml',
    'html', 'email', 'mimetypes', 'queue', 'select', 'signal', 'errno',
    'numbers', 'array', 'bisect', 'heapq', 'weakref', 'gc',
}

# Third-party packages we know are NOT internal ai-office tools
_THIRDPARTY_HINT = {
    'openpyxl', 'pandas', 'numpy', 'requests', 'aiohttp', 'httpx', 'flask',
    'fastapi', 'sqlalchemy', 'pydantic', 'click', 'rich', 'tqdm', 'yaml',
    'toml', 'dotenv', 'chardet', 'lxml', 'bs4', 'PIL', 'cv2', 'torch',
    'transformers', 'sentence_transformers', 'docling', 'pymupdf', 'fitz',
    'pptx', 'docx', 'win32com', 'pywintypes', 'pythoncom', 'ollama',
    'sqlite_vec', 'transitions', 'pytransitions', 'qwen', 'anthropic',
    'tiktoken', 'tenacity', 'jinja2', 'markdown', 'tabulate', 'colorama',
}


def _tg_repo_root() -> Path:
    """Repo root is two levels up from this script (shared/tools/kb.py)."""
    return ROOT


def _tg_iter_py_files(root: Path):
    """Yield all .py files under root, excluding __pycache__ and _template/."""
    for p in root.rglob('*.py'):
        parts = set(p.parts)
        if '__pycache__' in parts:
            continue
        if any(part.startswith('_template') or part == '_template' for part in p.parts):
            continue
        # Skip .git internals if any
        if '.git' in parts:
            continue
        yield p


def _tg_relpath(p: Path, root: Path) -> str:
    """POSIX-style relative path from repo root."""
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return p.as_posix()


def _tg_tier(rel_path: str) -> int:
    """Determine tier from relative path."""
    if rel_path.startswith('shared/tools/'):
        return 1
    name = rel_path.rsplit('/', 1)[-1]
    # Tier 2: utility modules used across scripts in same project
    if name in ('ecr_bom_utils.py',) or name.endswith('_utils.py') and '/workspace/scripts/' in rel_path:
        # _utils.py convention → Tier 2
        return 2
    return 3


def _tg_extract_imports(py_path: Path):
    """Parse a .py file with ast and return set of imported module names (top-level)."""
    try:
        src = py_path.read_text(encoding='utf-8', errors='replace')
    except Exception:
        return set()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return set()
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name:
                    mods.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                mods.add(node.module)
    return mods


def _tg_extract_docstring_first_line(py_path: Path) -> str:
    """Return first line of module docstring, or ''."""
    try:
        src = py_path.read_text(encoding='utf-8', errors='replace')
    except Exception:
        return ''
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return ''
    doc = ast.get_docstring(tree)
    if not doc:
        return ''
    first = doc.strip().splitlines()[0].strip() if doc.strip() else ''
    return first[:200]


def _tg_build_module_index(root: Path):
    """Build maps from importable module names to repo-relative paths.

    Returns (by_dotted, by_basename) where:
      by_dotted: 'shared.tools.bom_parser' -> 'shared/tools/bom_parser.py'
      by_basename: 'bom_parser' -> ['projects/.../bom_parser.py', ...]
    """
    by_dotted = {}
    by_basename = {}
    for p in _tg_iter_py_files(root):
        rel = _tg_relpath(p, root)
        if rel.endswith('/__init__.py'):
            pkg_rel = rel[:-len('/__init__.py')]
            dotted = pkg_rel.replace('/', '.')
            by_dotted[dotted] = rel
            base = pkg_rel.rsplit('/', 1)[-1]
            by_basename.setdefault(base, []).append(rel)
            continue
        if not rel.endswith('.py'):
            continue
        mod_rel = rel[:-3]  # strip .py
        dotted = mod_rel.replace('/', '.')
        by_dotted[dotted] = rel
        base = mod_rel.rsplit('/', 1)[-1]
        by_basename.setdefault(base, []).append(rel)
    return by_dotted, by_basename


def _tg_resolve_import(mod_name: str, importer_rel: str, by_dotted, by_basename):
    """Resolve an imported module name to a repo-relative .py path, or None.

    Strategy:
    1) Skip stdlib / known third-party.
    2) Exact dotted match (e.g. 'shared.tools.bom_parser').
    3) Dotted prefix match (e.g. 'shared.tools.bom_parser.foo' → bom_parser.py).
    4) Single-name basename match preferring same directory as importer.
    """
    if not mod_name:
        return None
    top = mod_name.split('.', 1)[0]
    if top in _STDLIB_HINT or top in _THIRDPARTY_HINT:
        return None

    # 2) exact dotted
    if mod_name in by_dotted:
        return by_dotted[mod_name]

    # 3) dotted prefix match — walk up
    parts = mod_name.split('.')
    while len(parts) > 1:
        parts.pop()
        candidate = '.'.join(parts)
        if candidate in by_dotted:
            return by_dotted[candidate]

    # 4) single-name (no dots) basename match
    if '.' not in mod_name:
        candidates = by_basename.get(mod_name, [])
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]
        # prefer same directory as importer
        importer_dir = importer_rel.rsplit('/', 1)[0] if '/' in importer_rel else ''
        same_dir = [c for c in candidates if c.rsplit('/', 1)[0] == importer_dir]
        if len(same_dir) == 1:
            return same_dir[0]
        # prefer shared/tools/
        shared = [c for c in candidates if c.startswith('shared/tools/')]
        if len(shared) == 1:
            return shared[0]
        return None  # ambiguous — skip rather than mislink

    return None


def _tg_node_id(rel_path: str) -> str:
    return f"TOOL:{rel_path}"


def cmd_tool_graph_scan(args):
    """Scan repo for Python files, extract imports, write tool nodes + import edges."""
    root = _tg_repo_root()
    py_files = list(_tg_iter_py_files(root))
    print(f"Discovered {len(py_files)} .py files under {root}")

    by_dotted, by_basename = _tg_build_module_index(root)

    # Build per-file metadata
    file_meta = {}  # rel_path -> {'docstring': ..., 'tier': ..., 'imports': set(rel_paths)}
    for i, p in enumerate(py_files, 1):
        if i % 50 == 0:
            print(f"  scanned {i}/{len(py_files)}")
        rel = _tg_relpath(p, root)
        imports = _tg_extract_imports(p)
        resolved = set()
        for mod in imports:
            tgt = _tg_resolve_import(mod, rel, by_dotted, by_basename)
            if tgt and tgt != rel:  # don't self-link
                resolved.add(tgt)
        file_meta[rel] = {
            'docstring': _tg_extract_docstring_first_line(p),
            'tier': _tg_tier(rel),
            'imports': resolved,
            'exists': True,
        }

    # Also create stub nodes for any import targets that don't exist as files
    # (shouldn't happen because we built from file scan, but be safe)
    referenced = set()
    for meta in file_meta.values():
        referenced.update(meta['imports'])
    for rel in referenced:
        if rel not in file_meta:
            file_meta[rel] = {
                'docstring': '',
                'tier': _tg_tier(rel),
                'imports': set(),
                'exists': False,
            }

    today = datetime.now().strftime('%Y-%m-%d')
    conn = _get_conn()
    _ensure_schema(conn)

    # Clear previous tool graph (idempotent rebuild)
    conn.execute("DELETE FROM edges WHERE relation='imports' AND auto_generated=1")
    conn.execute("DELETE FROM nodes WHERE node_type='tool'")
    conn.commit()

    node_count = 0
    for rel, meta in file_meta.items():
        node_id = _tg_node_id(rel)
        meta_json = json.dumps({'tier': meta['tier'], 'exists': meta['exists']}, ensure_ascii=False)
        conn.execute(
            """INSERT OR REPLACE INTO nodes
               (id, node_type, project, status, target, summary,
                refs_skill, refs_db, affects_project,
                created_date, last_synced, content, meta_json)
               VALUES (?, 'tool', NULL, 'active', ?, ?, NULL, NULL, NULL, ?, ?, NULL, ?)""",
            (node_id, rel, meta['docstring'], today, today, meta_json)
        )
        node_count += 1

    edge_count = 0
    for rel, meta in file_meta.items():
        importer_id = _tg_node_id(rel)
        for tgt_rel in meta['imports']:
            target_id = _tg_node_id(tgt_rel)
            # Edge convention from spec:
            #   source_id = the tool being imported
            #   target_id = the script doing the import
            conn.execute(
                """INSERT OR REPLACE INTO edges (source_id, target_id, relation, auto_generated)
                   VALUES (?, ?, 'imports', 1)""",
                (target_id, importer_id)
            )
            edge_count += 1

    conn.commit()
    conn.close()
    print(f"Scanned {len(py_files)} files → {node_count} tool nodes, {edge_count} import edges")


def _tg_resolve_tool_arg(conn, query: str):
    """Resolve --tool argument to a TOOL node id. Accepts full ID, path fragment, basename."""
    if query.startswith('TOOL:'):
        row = conn.execute("SELECT id FROM nodes WHERE id=? AND node_type='tool'", (query,)).fetchone()
        if row:
            return row['id']
        return None
    # fuzzy match on target (path) — prefer basename hits
    pat = f"%{query}%"
    rows = conn.execute(
        "SELECT id, target FROM nodes WHERE node_type='tool' AND target LIKE ? ORDER BY length(target)",
        (pat,)
    ).fetchall()
    if not rows:
        return None
    # Prefer exact basename match
    base_matches = [r for r in rows if r['target'].rsplit('/', 1)[-1] in (query, query + '.py')]
    if len(base_matches) == 1:
        return base_matches[0]['id']
    if len(base_matches) > 1:
        print(f"Ambiguous --tool '{query}', candidates:")
        for r in base_matches:
            print(f"  {r['id']}")
        return None
    if len(rows) == 1:
        return rows[0]['id']
    print(f"Ambiguous --tool '{query}', candidates:")
    for r in rows[:10]:
        print(f"  {r['id']}")
    return None


def _tg_meta(row) -> dict:
    try:
        return json.loads(row['meta_json']) if row['meta_json'] else {}
    except Exception:
        return {}


def cmd_tool_graph_show(args):
    """Show direct importers of a tool (one hop)."""
    conn = _get_conn()
    if not args.tool:
        # List all tools grouped by tier
        rows = conn.execute(
            "SELECT id, target, meta_json FROM nodes WHERE node_type='tool' ORDER BY target"
        ).fetchall()
        by_tier = {1: [], 2: [], 3: []}
        for r in rows:
            t = _tg_meta(r).get('tier', 3)
            by_tier.setdefault(t, []).append(r['target'])
        for tier in (1, 2, 3):
            items = by_tier.get(tier, [])
            print(f"\n[Tier {tier}] ({len(items)} tools)")
            for tgt in items[:30]:
                print(f"  {tgt}")
            if len(items) > 30:
                print(f"  ... +{len(items) - 30} more")
        conn.close()
        return

    node_id = _tg_resolve_tool_arg(conn, args.tool)
    if not node_id:
        print(f"[NOT FOUND] tool: {args.tool}")
        conn.close()
        return

    node = conn.execute(
        "SELECT id, target, summary, meta_json FROM nodes WHERE id=?", (node_id,)
    ).fetchone()
    meta = _tg_meta(node)
    tier = meta.get('tier', '?')
    print(f"TOOL: {node['target']}  [Tier {tier}]")
    if node['summary']:
        print(f"  {node['summary']}")

    # incoming edges with relation='imports' → things that import this tool
    importers = conn.execute(
        """SELECT n.id, n.target, n.meta_json FROM edges e
           JOIN nodes n ON n.id = e.target_id
           WHERE e.source_id=? AND e.relation='imports'
           ORDER BY n.target""",
        (node_id,)
    ).fetchall()

    # outgoing: this tool imports others
    imports_out = conn.execute(
        """SELECT n.id, n.target, n.meta_json FROM edges e
           JOIN nodes n ON n.id = e.source_id
           WHERE e.target_id=? AND e.relation='imports'
           ORDER BY n.target""",
        (node_id,)
    ).fetchall()

    if importers:
        print(f"  Used by (imports this): {len(importers)}")
        for r in importers:
            t = _tg_meta(r).get('tier', '?')
            print(f"    → {r['target']}  [Tier {t}]")
    else:
        print("  Used by: (none)")

    if imports_out:
        print(f"  Imports: {len(imports_out)}")
        for r in imports_out:
            t = _tg_meta(r).get('tier', '?')
            print(f"    ← {r['target']}  [Tier {t}]")

    conn.close()


def cmd_tool_graph_impacts(args):
    """Recursively show all scripts impacted if a tool is modified."""
    conn = _get_conn()
    node_id = _tg_resolve_tool_arg(conn, args.tool)
    if not node_id:
        print(f"[NOT FOUND] tool: {args.tool}")
        conn.close()
        return

    root_node = conn.execute(
        "SELECT target, meta_json FROM nodes WHERE id=?", (node_id,)
    ).fetchone()
    print(f"Impact analysis for: {root_node['target']}  [Tier {_tg_meta(root_node).get('tier', '?')}]")

    # BFS along incoming 'imports' edges (source=tool, target=script that imports it)
    visited = {node_id}
    frontier = [(node_id, 0)]
    levels = {}
    while frontier:
        cur, depth = frontier.pop(0)
        rows = conn.execute(
            "SELECT target_id FROM edges WHERE source_id=? AND relation='imports'",
            (cur,)
        ).fetchall()
        for r in rows:
            tid = r['target_id']
            if tid in visited:
                continue
            visited.add(tid)
            levels[tid] = depth + 1
            frontier.append((tid, depth + 1))

    if not levels:
        print("  (no downstream impact)")
        conn.close()
        return

    # Sort by depth then path
    items = sorted(levels.items(), key=lambda kv: (kv[1], kv[0]))
    print(f"  Impacted scripts: {len(items)}")
    for tid, depth in items:
        n = conn.execute("SELECT target, meta_json FROM nodes WHERE id=?", (tid,)).fetchone()
        if not n:
            continue
        t = _tg_meta(n).get('tier', '?')
        indent = "  " + "  " * depth
        print(f"{indent}└─ {n['target']}  [Tier {t}, depth={depth}]")
    conn.close()


def cmd_tool_graph(args):
    """Dispatcher for tool-graph subcommands."""
    action = getattr(args, 'tg_action', None)
    if action == 'scan':
        cmd_tool_graph_scan(args)
    elif action == 'show':
        cmd_tool_graph_show(args)
    elif action == 'impacts':
        cmd_tool_graph_impacts(args)
    else:
        print("Usage: kb.py tool-graph {scan|show|impacts} [--tool ID_OR_PATH]")
        sys.exit(1)


# ═══════════════════════════════════════════════════════════
# EVO-016: absorbed from kb_index.py
# ═══════════════════════════════════════════════════════════

def _get_kb_index():
    """Lazy-load the KBIndex class from kb_index.py (co-located in shared/tools)."""
    sys.path.insert(0, str(SCRIPT_DIR))
    from kb_index import KBIndex
    return KBIndex


def cmd_sync(args):
    """Sync .md files to SQLite index (EVO-016 absorbed from kb_index.py)."""
    KBIndex = _get_kb_index()
    kb = KBIndex()
    try:
        kb.sync(quiet=args.quiet)
        if getattr(args, 'embed', False) or getattr(args, 'embed_force', False):
            kb.sync_embeddings(force=args.embed_force, quiet=args.quiet)
    finally:
        kb.close()


def cmd_generate_summary(args):
    """Generate active_rules_summary.md from DB (EVO-016)."""
    KBIndex = _get_kb_index()
    kb = KBIndex()
    try:
        path, stats = kb.generate_active_summary(
            output_path=getattr(args, 'output', None),
            project=getattr(args, 'project', None),
        )
        print(f"Generated: {path}")
        print(f"  Active decisions: {stats['active_decisions']}")
        print(f"  Superseded: {stats['superseded_decisions']}")
        print(f"  Active rules: {stats['active_rules']}")
        print(f"  Output size: {stats['output_size']} chars")
    finally:
        kb.close()


def cmd_generate_index(args):
    """Generate shared/kb/_index.md (EVO-016)."""
    KBIndex = _get_kb_index()
    kb = KBIndex()
    try:
        path, stats = kb.generate_index(
            output_path=getattr(args, 'output', None),
        )
        print(f"Generated: {path}")
        print(f"  Skills: {stats['skills']}")
        print(f"  Projects: {stats['projects']}")
        print(f"  Tools: {stats['tools']}")
        print(f"  Decisions: {stats['decisions']}")
        print(f"  Output size: {stats['output_size']} chars")
    finally:
        kb.close()


def cmd_check_conflict(args):
    """L2 conflict check for a target text (EVO-016)."""
    KBIndex = _get_kb_index()
    kb = KBIndex()
    try:
        kb.sync(quiet=True)
        conflicts = kb.check_conflict(args.target, threshold=args.threshold)
        if conflicts:
            print(f"POTENTIAL CONFLICTS for target '{args.target}':")
            for did, target, score in conflicts:
                print(f"  {did} | similarity={score} | {target}")
            sys.exit(1)
        else:
            print(f"OK: No conflicts found for target '{args.target}'")
            sys.exit(0)
    finally:
        kb.close()


def main():
    parser = argparse.ArgumentParser(description="Knowledge Base CLI (EVO-012, EVO-016)")
    sub = parser.add_subparsers(dest='command')

    sub.add_parser('catalog', help='Lightweight KB summary')
    sub.add_parser('next-id', help='Next available D-NNN')

    p_search = sub.add_parser('search', help='Search knowledge base')
    p_search.add_argument('query', help='Search query')
    p_search.add_argument('--top', type=int, default=10)
    p_search.add_argument('--keyword', action='store_true')
    p_search.add_argument('--budget', type=int, default=0,
                          help='Max output chars (0=unlimited). Truncate with hint to use kb.py read.')
    p_search.add_argument('--include-snapshots', dest='include_snapshots',
                          action='store_true',
                          help='Also search shared/kb/memory snapshots via FTS5 (use kb.py read SNAP:<id>).')

    # import-snapshot
    p_imp_snap = sub.add_parser('import-snapshot',
                                help='Import session snapshot(s) into FTS5 index')
    p_imp_snap.add_argument('path', nargs='?',
                            help='File or directory (default: shared/kb/memory/)')

    p_read = sub.add_parser('read', help='Read full content')
    p_read.add_argument('ids', nargs='+')

    # add decision
    p_dec = sub.add_parser('add-decision', help='Add decision')
    p_dec.add_argument('--id', required=True)
    p_dec.add_argument('--date', required=True)
    p_dec.add_argument('--project', required=True)
    p_dec.add_argument('--target', required=True)
    p_dec.add_argument('--question', required=True)
    p_dec.add_argument('--decision', required=True)
    p_dec.add_argument('--impact', required=True)
    p_dec.add_argument('--status', default='active')
    p_dec.add_argument('--supersedes')
    p_dec.add_argument('--refs_skill')
    p_dec.add_argument('--refs_db')
    p_dec.add_argument('--affects')
    p_dec.add_argument('--review_by')
    p_dec.add_argument('--source')

    # add learning
    p_learn = sub.add_parser('add-learning', help='Add learning note')
    p_learn.add_argument('--id', required=True)
    p_learn.add_argument('--title', required=True)
    p_learn.add_argument('--date', required=True)
    p_learn.add_argument('--content', required=True)
    p_learn.add_argument('--confidence', required=True, choices=['high', 'medium', 'low'])
    p_learn.add_argument('--status', default='active')
    p_learn.add_argument('--project')
    p_learn.add_argument('--related_decision')

    # update
    p_upd = sub.add_parser('update', help='Update entry status/fields')
    p_upd.add_argument('entry_id')
    p_upd.add_argument('--status', choices=['active', 'superseded', 'deprecated', 'promoted'])
    p_upd.add_argument('--superseded-by', dest='superseded_by')

    # export
    p_exp = sub.add_parser('export', help='Export DB -> .md')
    p_exp.add_argument('target', choices=['decisions', 'learning', 'all'])

    # validate (EVO-016 extended)
    p_val = sub.add_parser('validate', help='Consistency checks')
    p_val.add_argument('--quiet', action='store_true')
    p_val.add_argument('--strict', action='store_true')

    # trace
    p_trace = sub.add_parser('trace', help='Trace node relationships')
    p_trace.add_argument('node_id', help='Node ID to trace (e.g. D-042)')

    # impacts
    p_imp = sub.add_parser('impacts', help='Find nodes affecting a project or skill')
    p_imp.add_argument('--skill', help='Skill name')
    p_imp.add_argument('--project', help='Project name')

    # suggest-edges
    p_sug = sub.add_parser('suggest-edges', help='Show semantic neighbors for Leader edge review')
    p_sug.add_argument('node_id', help='Node to find neighbors for (e.g. D-042)')
    p_sug.add_argument('--top', type=int, default=8, help='Number of candidates (default 8)')

    # add-edge
    p_ae = sub.add_parser('add-edge', help='Write a Leader-reviewed edge')
    p_ae.add_argument('source_id')
    p_ae.add_argument('target_id')
    p_ae.add_argument('relation', choices=['references', 'affects', 'supersedes'])

    # build-edges
    p_be = sub.add_parser('build-edges', help='Materialize JSON refs as graph edges + process auto-edge queue (idempotent)')
    p_be.add_argument('--threshold', type=float, default=0.85,
                      help='Cosine similarity threshold for auto-writing edges (default 0.85)')

    # tool-graph
    p_tg = sub.add_parser('tool-graph', help='Python tool import dependency graph')
    tg_sub = p_tg.add_subparsers(dest='tg_action')
    tg_sub.add_parser('scan', help='Scan repo and rebuild tool nodes + import edges')
    p_tg_show = tg_sub.add_parser('show', help='Show direct importers of a tool')
    p_tg_show.add_argument('--tool', help='Tool ID or path fragment (omit to list all)')
    p_tg_imp = tg_sub.add_parser('impacts', help='Recursively show scripts impacted by modifying a tool')
    p_tg_imp.add_argument('--tool', required=True, help='Tool ID or path fragment')

    # migrate
    p_mig = sub.add_parser('migrate', help='Migrate .md -> DB (one-time)')
    p_mig.add_argument('--dry-run', action='store_true')
    p_mig.add_argument('--execute', action='store_true')

    # EVO-016: absorbed from kb_index.py
    p_sync = sub.add_parser('sync', help='Sync .md files to DB (EVO-016)')
    p_sync.add_argument('--quiet', action='store_true')
    p_sync.add_argument('--embed', action='store_true')
    p_sync.add_argument('--embed-force', action='store_true')

    p_gs = sub.add_parser('generate-summary', help='Generate active_rules_summary.md (EVO-016)')
    p_gs.add_argument('--project', type=str, default=None)
    p_gs.add_argument('--output', type=str, default=None)

    p_gi = sub.add_parser('generate-index', help='Generate shared/kb/_index.md (EVO-016)')
    p_gi.add_argument('--output', type=str, default=None)

    p_cc = sub.add_parser('check-conflict', help='L2 conflict check for a target (EVO-016)')
    p_cc.add_argument('target', type=str)
    p_cc.add_argument('--threshold', type=float, default=0.4)

    args = parser.parse_args()
    cmd_map = {
        'catalog': cmd_catalog,
        'next-id': cmd_next_id,
        'search': cmd_search,
        'read': cmd_read,
        'add-decision': cmd_add_decision,
        'add-learning': cmd_add_learning,
        'update': cmd_update,
        'export': cmd_export,
        'validate': cmd_validate,
        'trace': cmd_trace,
        'impacts': cmd_impacts,
        'suggest-edges': cmd_suggest_edges,
        'add-edge': cmd_add_edge,
        'build-edges': cmd_build_edges,
        'tool-graph': cmd_tool_graph,
        'import-snapshot': cmd_import_snapshot,
        'migrate': lambda a: cmd_migrate(a) if (a.dry_run or a.execute) else print("Specify --dry-run or --execute"),
        # EVO-016: absorbed from kb_index.py
        'sync': cmd_sync,
        'generate-summary': cmd_generate_summary,
        'generate-index': cmd_generate_index,
        'check-conflict': cmd_check_conflict,
    }
    fn = cmd_map.get(args.command)
    if fn:
        fn(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
