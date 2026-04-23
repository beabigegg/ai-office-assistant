"""Validator: check_backlog_health

For session_start: inspects the project's backlog.db and returns a one-line
summary plus (optionally) a short list of items requiring attention.

Contract:
    validate(context) -> (ok: bool, message: str)

Behavior:
- knowledge-type projects (no backlog.db) => pass with "no backlog.db"
- project_management projects with a backlog.db => read counts & stale items
- Always returns ok=True (session_start should not block); callers treat
  presence of `WARN:` in the message as a soft warning.
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

WORKFLOWS_DIR = Path(__file__).resolve().parents[1]
if str(WORKFLOWS_DIR) not in sys.path:
    sys.path.insert(0, str(WORKFLOWS_DIR))

from project_ref import normalize_project_id, project_db_dir


STALE_BLOCKED_DAYS = 3
STALE_IN_PROGRESS_DAYS = 7


def _parse_iso(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _age_days(ts: Optional[str]) -> Optional[float]:
    dt = _parse_iso(ts)
    if dt is None:
        return None
    delta = datetime.now(timezone.utc) - dt
    return delta.total_seconds() / 86400.0


def validate(context: dict) -> tuple:
    _default_root = Path(__file__).resolve().parent.parent.parent.parent
    root = Path(context.get('root', _default_root))
    project = normalize_project_id(context.get('project', ''))

    if not project:
        return True, "no project context, skip backlog health"

    backlog_db = project_db_dir(root, project) / 'backlog.db'
    if not backlog_db.exists():
        return True, "no backlog.db"

    try:
        conn = sqlite3.connect(str(backlog_db))
        conn.row_factory = sqlite3.Row
    except sqlite3.Error as exc:
        return True, f"backlog.db unreadable: {exc}"

    try:
        # Guard against empty / uninitialized DB
        tbl = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='action_items'"
        ).fetchone()
        if tbl is None:
            return True, "backlog.db has no action_items table yet"

        # P0 open
        p0_rows = conn.execute(
            """
            SELECT id, title, status FROM action_items
            WHERE priority = 'P0' AND status IN ('open', 'in_progress')
            ORDER BY id
            """
        ).fetchall()
        p0_open = len(p0_rows)

        # blocked > 3 days
        blocked_stale = []
        for r in conn.execute(
            "SELECT id, title, updated_at FROM action_items "
            "WHERE status = 'blocked' ORDER BY id"
        ).fetchall():
            age = _age_days(r['updated_at'])
            if age is not None and age > STALE_BLOCKED_DAYS:
                blocked_stale.append((r['id'], r['title'], int(age)))

        # in_progress > 7 days
        ip_stale = []
        for r in conn.execute(
            "SELECT id, title, updated_at FROM action_items "
            "WHERE status = 'in_progress' ORDER BY id"
        ).fetchall():
            age = _age_days(r['updated_at'])
            if age is not None and age > STALE_IN_PROGRESS_DAYS:
                ip_stale.append((r['id'], r['title'], int(age)))
    finally:
        conn.close()

    summary = (
        f"Backlog: {p0_open} open P0, "
        f"{len(blocked_stale)} blocked>{STALE_BLOCKED_DAYS}d, "
        f"{len(ip_stale)} stale-in_progress"
    )

    # If any attention-worthy items, append a short list (WARN but non-blocking)
    if p0_open or blocked_stale or ip_stale:
        details: list[str] = []
        for r in p0_rows[:3]:
            title = (r['title'] or '')[:60]
            details.append(f"  [P0/{r['status']}] {r['id']} {title}")
        for aid, title, age in blocked_stale[:3]:
            details.append(
                f"  [blocked-{age}d] {aid} {(title or '')[:60]}"
            )
        for aid, title, age in ip_stale[:3]:
            details.append(
                f"  [in_progress-{age}d] {aid} {(title or '')[:60]}"
            )
        if details:
            return True, f"WARN: {summary}\n" + '\n'.join(details)

    return True, summary
