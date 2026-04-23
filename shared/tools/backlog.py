#!/usr/bin/env python3
"""Backlog CLI — Structured action-item tracker for project_management projects.

Each project has its own backlog.db at:
    D:/ai-office/projects/<project>/workspace/db/backlog.db

Usage:
    python shared/tools/backlog.py --project <name> list [--status ...] [--priority ...] [--owner ...]
    python shared/tools/backlog.py --project <name> add --title "..." [options]
    python shared/tools/backlog.py --project <name> update A-NNN [--status ...] [--note ...]
    python shared/tools/backlog.py --project <name> resolve A-NNN --resolution "..." [--decision D-NNN]
    python shared/tools/backlog.py --project <name> discuss --topic "..." --summary "..." [options]
    python shared/tools/backlog.py --project <name> remind
    python shared/tools/backlog.py --project <name> summary
    python shared/tools/backlog.py --project <name> next-id

If --project is omitted, falls back to context.project in
    D:/ai-office/shared/workflows/state/current.json
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent.parent  # D:/ai-office
PROJECTS_DIR = ROOT / 'projects'
STATE_FILE = ROOT / 'shared' / 'workflows' / 'state' / 'current.json'

VALID_STATUSES = ('open', 'in_progress', 'blocked', 'done', 'cancelled')
VALID_PRIORITIES = ('P0', 'P1', 'P2')
VALID_OWNERS = ('leader', 'user')

DEFAULT_LIST_STATUSES = ('open', 'in_progress', 'blocked')

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS action_items (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    priority TEXT NOT NULL DEFAULT 'P1',
    owner TEXT DEFAULT 'leader',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    due_date TEXT,
    related_decision TEXT,
    related_files TEXT,
    blocked_reason TEXT,
    resolution TEXT
);

CREATE TABLE IF NOT EXISTS action_item_updates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_id TEXT NOT NULL,
    ts TEXT NOT NULL,
    status_from TEXT,
    status_to TEXT,
    note TEXT,
    FOREIGN KEY (action_id) REFERENCES action_items(id)
);

CREATE TABLE IF NOT EXISTS discussion_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    topic TEXT NOT NULL,
    summary TEXT NOT NULL,
    outcome TEXT,
    related_actions TEXT,
    related_decision TEXT
);

CREATE INDEX IF NOT EXISTS idx_action_items_status
    ON action_items(status);
CREATE INDEX IF NOT EXISTS idx_action_items_priority
    ON action_items(priority);
CREATE INDEX IF NOT EXISTS idx_action_item_updates_action
    ON action_item_updates(action_id);
"""


# ---------------------------------------------------------------------------
# Project resolution
# ---------------------------------------------------------------------------

def _get_default_project() -> Optional[str]:
    """Read default project from workflow state file."""
    if not STATE_FILE.exists():
        return None
    try:
        state = json.loads(STATE_FILE.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return None

    # Check active instances first
    for inst in state.get('active', {}).values():
        ctx = inst.get('context', {}) or {}
        proj = ctx.get('project')
        if proj:
            return _normalize_project_name(proj)

    # Fall back to most recent history entry
    history = state.get('history') or []
    if history:
        last = history[-1]
        ctx = last.get('context', {}) or {}
        proj = ctx.get('project')
        if proj:
            return _normalize_project_name(proj)

    return None


def _normalize_project_name(raw: str) -> str:
    """Accept either 'ecr-ecn' or 'projects/ecr-ecn' — return bare name."""
    raw = raw.strip().replace('\\', '/')
    if raw.startswith('projects/'):
        raw = raw[len('projects/'):]
    return raw.strip('/')


def _resolve_db_path(project: str) -> Path:
    """Return backlog.db path for a given project."""
    project = _normalize_project_name(project)
    return PROJECTS_DIR / project / 'workspace' / 'db' / 'backlog.db'


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _get_conn(db_path: Path) -> sqlite3.Connection:
    """Open / create backlog.db with schema migration."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _next_action_id(conn: sqlite3.Connection) -> str:
    """Return next available A-NNN id (zero-padded, continues max+1)."""
    row = conn.execute(
        "SELECT id FROM action_items WHERE id LIKE 'A-%' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if row is None:
        return 'A-001'
    last = row['id']
    try:
        n = int(last.split('-', 1)[1])
    except (IndexError, ValueError):
        n = 0
    return f"A-{n + 1:03d}"


def _fail(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _format_list_row(row: sqlite3.Row) -> str:
    status = row['status']
    priority = row['priority']
    title = (row['title'] or '')[:60]
    suffix = ''
    if status == 'blocked' and row['blocked_reason']:
        reason = row['blocked_reason'][:40]
        suffix = f"  blocked: {reason}"
    elif row['due_date']:
        suffix = f"  due: {row['due_date']}"
    return f"{row['id']} [{priority}] [{status:<11}] {title:<60}{suffix}"


def _parse_iso(ts: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return None


def _age_days(ts: str) -> Optional[float]:
    dt = _parse_iso(ts)
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - dt
    return delta.total_seconds() / 86400.0


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_list(args, conn: sqlite3.Connection) -> int:
    if args.status:
        statuses = tuple(s.strip() for s in args.status.split(',') if s.strip())
    else:
        statuses = DEFAULT_LIST_STATUSES

    for s in statuses:
        if s not in VALID_STATUSES:
            _fail(f"invalid status '{s}', expected one of {VALID_STATUSES}")

    where = [f"status IN ({','.join(['?'] * len(statuses))})"]
    params: list = list(statuses)

    if args.priority:
        if args.priority not in VALID_PRIORITIES:
            _fail(f"invalid priority '{args.priority}'")
        where.append("priority = ?")
        params.append(args.priority)

    if args.owner:
        if args.owner not in VALID_OWNERS:
            _fail(f"invalid owner '{args.owner}'")
        where.append("owner = ?")
        params.append(args.owner)

    sql = (
        "SELECT * FROM action_items "
        f"WHERE {' AND '.join(where)} "
        "ORDER BY CASE priority WHEN 'P0' THEN 0 WHEN 'P1' THEN 1 WHEN 'P2' THEN 2 "
        "ELSE 3 END, id"
    )
    rows = conn.execute(sql, params).fetchall()

    if not rows:
        print("(no matching action items)")
        return 0

    for row in rows:
        print(_format_list_row(row))
    print(f"\nTotal: {len(rows)}")
    return 0


def cmd_add(args, conn: sqlite3.Connection) -> int:
    priority = args.priority or 'P1'
    if priority not in VALID_PRIORITIES:
        _fail(f"invalid priority '{priority}'")
    owner = args.owner or 'leader'
    if owner not in VALID_OWNERS:
        _fail(f"invalid owner '{owner}'")
    if args.due:
        # Validate shape YYYY-MM-DD
        try:
            datetime.strptime(args.due, '%Y-%m-%d')
        except ValueError:
            _fail(f"--due must be YYYY-MM-DD, got '{args.due}'")

    now = _utc_now_iso()
    action_id = _next_action_id(conn)

    conn.execute(
        """
        INSERT INTO action_items (
            id, title, description, status, priority, owner,
            created_at, updated_at, due_date, related_decision
        ) VALUES (?, ?, ?, 'open', ?, ?, ?, ?, ?, ?)
        """,
        (
            action_id,
            args.title,
            args.description,
            priority,
            owner,
            now,
            now,
            args.due,
            args.decision,
        ),
    )
    conn.execute(
        """
        INSERT INTO action_item_updates (action_id, ts, status_from, status_to, note)
        VALUES (?, ?, NULL, 'open', ?)
        """,
        (action_id, now, 'created'),
    )
    conn.commit()

    print(f"Created {action_id}: {args.title}")
    return 0


def cmd_update(args, conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT * FROM action_items WHERE id = ?", (args.action_id,)
    ).fetchone()
    if row is None:
        _fail(f"action item '{args.action_id}' not found")

    sets = []
    params: list = []
    status_from = row['status']
    status_to = row['status']

    if args.status:
        if args.status not in VALID_STATUSES:
            _fail(f"invalid status '{args.status}'")
        sets.append("status = ?")
        params.append(args.status)
        status_to = args.status

    if args.blocked_reason is not None:
        sets.append("blocked_reason = ?")
        params.append(args.blocked_reason)
        # If blocked_reason given without status, imply blocked
        if not args.status:
            sets.append("status = ?")
            params.append('blocked')
            status_to = 'blocked'

    if not sets and not args.note:
        _fail("nothing to update (provide --status / --note / --blocked-reason)")

    now = _utc_now_iso()
    sets.append("updated_at = ?")
    params.append(now)
    params.append(args.action_id)

    if sets:
        conn.execute(
            f"UPDATE action_items SET {', '.join(sets)} WHERE id = ?",
            params,
        )

    conn.execute(
        """
        INSERT INTO action_item_updates (action_id, ts, status_from, status_to, note)
        VALUES (?, ?, ?, ?, ?)
        """,
        (args.action_id, now, status_from, status_to, args.note),
    )
    conn.commit()

    changed = f"{status_from} -> {status_to}" if status_from != status_to else status_to
    print(f"Updated {args.action_id} [{changed}]")
    return 0


def cmd_resolve(args, conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT * FROM action_items WHERE id = ?", (args.action_id,)
    ).fetchone()
    if row is None:
        _fail(f"action item '{args.action_id}' not found")

    now = _utc_now_iso()
    status_from = row['status']
    # If a decision ref is provided, keep existing or overwrite
    related_decision = args.decision or row['related_decision']

    conn.execute(
        """
        UPDATE action_items
        SET status = 'done',
            resolution = ?,
            related_decision = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (args.resolution, related_decision, now, args.action_id),
    )
    conn.execute(
        """
        INSERT INTO action_item_updates (action_id, ts, status_from, status_to, note)
        VALUES (?, ?, ?, 'done', ?)
        """,
        (args.action_id, now, status_from, f"resolved: {args.resolution}"),
    )
    conn.commit()

    extra = f" (ref {args.decision})" if args.decision else ''
    print(f"Resolved {args.action_id}{extra}")
    return 0


def cmd_discuss(args, conn: sqlite3.Connection) -> int:
    now = _utc_now_iso()
    related_actions = None
    if args.actions:
        ids = [a.strip() for a in args.actions.split(',') if a.strip()]
        related_actions = json.dumps(ids, ensure_ascii=False)

    conn.execute(
        """
        INSERT INTO discussion_log
            (ts, topic, summary, outcome, related_actions, related_decision)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (now, args.topic, args.summary, args.outcome,
         related_actions, args.decision),
    )
    conn.commit()
    print(f"Recorded discussion: {args.topic}")
    return 0


def cmd_remind(args, conn: sqlite3.Connection) -> int:
    lines: list[str] = []

    # 1. P0 open / in_progress
    p0_rows = conn.execute(
        """
        SELECT * FROM action_items
        WHERE priority = 'P0' AND status IN ('open', 'in_progress')
        ORDER BY id
        """
    ).fetchall()
    for r in p0_rows:
        lines.append(f"[REMIND] {r['id']} [P0/{r['status']}] {r['title']}")

    # 2. blocked > 3 days (no updated_at change)
    blocked_rows = conn.execute(
        "SELECT * FROM action_items WHERE status = 'blocked' ORDER BY id"
    ).fetchall()
    for r in blocked_rows:
        age = _age_days(r['updated_at'])
        if age is not None and age > 3:
            lines.append(
                f"[REMIND] {r['id']} [{r['priority']}/blocked/stale-{int(age)}d] "
                f"{r['title']}"
            )

    # 3. in_progress > 7 days
    ip_rows = conn.execute(
        "SELECT * FROM action_items WHERE status = 'in_progress' ORDER BY id"
    ).fetchall()
    for r in ip_rows:
        age = _age_days(r['updated_at'])
        if age is not None and age > 7:
            lines.append(
                f"[REMIND] {r['id']} [{r['priority']}/in_progress/stale-{int(age)}d] "
                f"{r['title']}"
            )

    if not lines:
        print("(no reminders)")
    else:
        for line in lines:
            print(line)
    return 0


def cmd_summary(args, conn: sqlite3.Connection) -> int:
    p0_open = conn.execute(
        "SELECT COUNT(*) AS c FROM action_items "
        "WHERE priority = 'P0' AND status IN ('open', 'in_progress')"
    ).fetchone()['c']
    p1_open = conn.execute(
        "SELECT COUNT(*) AS c FROM action_items "
        "WHERE priority = 'P1' AND status IN ('open', 'in_progress')"
    ).fetchone()['c']
    blocked = conn.execute(
        "SELECT COUNT(*) AS c FROM action_items WHERE status = 'blocked'"
    ).fetchone()['c']

    # stale in_progress (>7d)
    stale = 0
    for r in conn.execute(
        "SELECT updated_at FROM action_items WHERE status = 'in_progress'"
    ).fetchall():
        age = _age_days(r['updated_at'])
        if age is not None and age > 7:
            stale += 1

    print(
        f"Backlog: {p0_open} open P0, {p1_open} open P1, "
        f"{blocked} blocked, {stale} stale-in_progress"
    )
    return 0


def cmd_next_id(args, conn: sqlite3.Connection) -> int:
    print(_next_action_id(conn))
    return 0


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Backlog CLI — per-project action-item tracker"
    )
    parser.add_argument(
        '--project',
        help=(
            "Project name (e.g. 'ecr-ecn'). "
            "If omitted, read from workflow state current.json."
        ),
    )
    sub = parser.add_subparsers(dest='command', required=True)

    # list
    p_list = sub.add_parser('list', help='List action items')
    p_list.add_argument(
        '--status',
        help=f"Comma-separated statuses (default: "
             f"{','.join(DEFAULT_LIST_STATUSES)})",
    )
    p_list.add_argument('--priority', choices=VALID_PRIORITIES)
    p_list.add_argument('--owner', choices=VALID_OWNERS)

    # add
    p_add = sub.add_parser('add', help='Add a new action item')
    p_add.add_argument('--title', required=True)
    p_add.add_argument('--priority', choices=VALID_PRIORITIES, default='P1')
    p_add.add_argument('--description')
    p_add.add_argument('--due', help='YYYY-MM-DD')
    p_add.add_argument('--owner', choices=VALID_OWNERS, default='leader')
    p_add.add_argument('--decision', help='Related decision ID (D-NNN)')

    # update
    p_upd = sub.add_parser('update', help='Update action item status/note')
    p_upd.add_argument('action_id', help='A-NNN')
    p_upd.add_argument('--status', choices=VALID_STATUSES)
    p_upd.add_argument('--note')
    p_upd.add_argument(
        '--blocked-reason',
        dest='blocked_reason',
        help='Reason (implies status=blocked if --status not provided)',
    )

    # resolve
    p_res = sub.add_parser('resolve', help='Mark action as done')
    p_res.add_argument('action_id', help='A-NNN')
    p_res.add_argument('--resolution', required=True)
    p_res.add_argument('--decision', help='Related decision ID (D-NNN)')

    # discuss
    p_dis = sub.add_parser('discuss', help='Log a discussion entry')
    p_dis.add_argument('--topic', required=True)
    p_dis.add_argument('--summary', required=True)
    p_dis.add_argument('--outcome')
    p_dis.add_argument(
        '--actions',
        help='Comma-separated A-NNN ids',
    )
    p_dis.add_argument('--decision', help='Related decision D-NNN')

    # remind / summary / next-id
    sub.add_parser('remind', help='Show reminders (P0 / stale / blocked)')
    sub.add_parser('summary', help='One-line backlog summary')
    sub.add_parser('next-id', help='Print next available A-NNN')

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    # Force UTF-8 stdout/stderr (Windows default is cp950)
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, OSError):
        pass

    parser = _build_parser()
    args = parser.parse_args(argv)

    project = args.project or _get_default_project()
    if not project:
        _fail(
            "no project specified; pass --project <name> or run inside an "
            "active workflow (current.json with context.project)."
        )
    project = _normalize_project_name(project)

    project_root = PROJECTS_DIR / project
    if not project_root.exists():
        _fail(f"project directory not found: {project_root}")

    db_path = _resolve_db_path(project)
    conn = _get_conn(db_path)

    try:
        if args.command == 'list':
            return cmd_list(args, conn)
        if args.command == 'add':
            return cmd_add(args, conn)
        if args.command == 'update':
            return cmd_update(args, conn)
        if args.command == 'resolve':
            return cmd_resolve(args, conn)
        if args.command == 'discuss':
            return cmd_discuss(args, conn)
        if args.command == 'remind':
            return cmd_remind(args, conn)
        if args.command == 'summary':
            return cmd_summary(args, conn)
        if args.command == 'next-id':
            return cmd_next_id(args, conn)
        _fail(f"unknown command '{args.command}'")
        return 1
    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())
