"""PreToolUse hook (Read): track SKILL.md reads into kb_index.db.

Reads tool_input from stdin (JSON). Always exits 0 — never blocks the Read
tool. All errors are swallowed silently.

Behavior:
- If Read target is `.claude/skills-on-demand/<skill>/SKILL.md` (or nested .md
  under that skill dir), increment usage counters on:
  1. Every node whose id contains `SKILL:<skill>` (skill node itself, if any).
  2. Every `learning` node that has an edge to a SKILL: target whose name
     matches `<skill>`.
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = REPO_ROOT / 'shared' / 'kb' / 'knowledge_graph' / 'kb_index.db'
SKILL_DIR_RE = re.compile(
    r'[\\/]\.claude[\\/]skills-on-demand[\\/]([^\\/]+)[\\/]',
    re.IGNORECASE,
)


def _extract_skill_name(file_path: str) -> str | None:
    if not file_path:
        return None
    # Normalize to look for the skills-on-demand segment
    m = SKILL_DIR_RE.search(file_path.replace('\\', '/').replace('/', '\\') + '\\')
    if not m:
        # retry with POSIX form
        m = re.search(
            r'/\.claude/skills-on-demand/([^/]+)/',
            file_path.replace('\\', '/'),
        )
        if not m:
            return None
    name = m.group(1)
    if not file_path.lower().endswith('.md'):
        return None
    return name


def _bump_meta(conn: sqlite3.Connection, node_id: str, now_iso: str) -> None:
    row = conn.execute(
        "SELECT meta_json FROM nodes WHERE id=?",
        (node_id,),
    ).fetchone()
    if row is None:
        return
    raw = row[0]
    try:
        meta = json.loads(raw) if raw else {}
        if not isinstance(meta, dict):
            meta = {}
    except Exception:
        meta = {}
    meta['usage_count'] = int(meta.get('usage_count', 0) or 0) + 1
    meta['last_skill_read_at'] = now_iso
    conn.execute(
        "UPDATE nodes SET meta_json=? WHERE id=?",
        (json.dumps(meta, ensure_ascii=False), node_id),
    )


def _track(skill_name: str) -> None:
    if not DB_PATH.exists():
        return
    conn = sqlite3.connect(str(DB_PATH), timeout=3.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        now_iso = datetime.now(timezone.utc).isoformat()

        # (1) Skill node itself (if the KB tracks it as a node).
        skill_pattern = f"%SKILL:{skill_name}%"
        for (nid,) in conn.execute(
            "SELECT id FROM nodes WHERE id LIKE ?",
            (skill_pattern,),
        ).fetchall():
            _bump_meta(conn, nid, now_iso)

        # (2) Learning nodes linked to a SKILL: target matching skill_name.
        rows = conn.execute(
            "SELECT DISTINCT source_id FROM edges "
            "WHERE target_id LIKE 'SKILL:%' AND "
            "(target_id = ? OR target_id LIKE ?)",
            (f"SKILL:{skill_name}", f"SKILL:{skill_name}:%"),
        ).fetchall()
        for (src,) in rows:
            # restrict to learning nodes
            t = conn.execute(
                "SELECT node_type FROM nodes WHERE id=?",
                (src,),
            ).fetchone()
            if t and t[0] == 'learning':
                _bump_meta(conn, src, now_iso)

        conn.commit()
    finally:
        try:
            conn.close()
        except Exception:
            pass


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    try:
        tool_input = data.get('tool_input', {}) or {}
        file_path = ''
        if isinstance(tool_input, dict):
            file_path = tool_input.get('file_path', '') or ''
        elif isinstance(tool_input, str):
            file_path = tool_input
        skill = _extract_skill_name(file_path)
        if skill:
            _track(skill)
    except Exception:
        pass

    sys.exit(0)


if __name__ == '__main__':
    main()
