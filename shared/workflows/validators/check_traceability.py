"""Validator: check_traceability
Verifies that ingested tables contain traceability columns.

Required columns: _operation_id, _source_file, _source_version, _source_row
These columns ensure every record can be traced back to its origin.

Part of Harness Engineering R3: Data traceability enforcement.
"""
import sqlite3
from pathlib import Path
import sys

WORKFLOWS_DIR = Path(__file__).resolve().parents[1]
if str(WORKFLOWS_DIR) not in sys.path:
    sys.path.insert(0, str(WORKFLOWS_DIR))

from project_ref import normalize_project_id, project_db_dir

REQUIRED_COLUMNS = ['_operation_id', '_source_file', '_source_version', '_source_row']


def _normalize_tables(outputs: dict) -> list[str]:
    target_tables = outputs.get('tables', [])
    if not target_tables:
        legacy = outputs.get('tables_written', [])
        if isinstance(legacy, list) and legacy and isinstance(legacy[0], dict):
            target_tables = [item.get('table_name', '') for item in legacy]
        else:
            target_tables = legacy

    if isinstance(target_tables, str):
        target_tables = [target_tables]

    return [table for table in target_tables if table]


def _find_db(root: Path, project: str, outputs: dict) -> Path | None:
    """Find the project database, same pattern as check_exclusion.py."""
    # Explicit db_path in outputs takes priority
    explicit = outputs.get('db_path', '')
    if explicit:
        p = Path(explicit)
        if not p.is_absolute():
            p = root / explicit
        if p.exists():
            return p

    if project:
        db_candidates = [project_db_dir(root, project)]
    else:
        db_candidates = list(root.glob('projects/*/workspace/db'))

    for d in db_candidates:
        if d.is_dir():
            dbs = list(d.glob('*.db')) + list(d.glob('*.sqlite'))
            if dbs:
                return dbs[0]
    return None


def validate(context: dict) -> tuple:
    _default_root = Path(__file__).resolve().parent.parent.parent.parent
    root = Path(context.get('root', _default_root))
    project = normalize_project_id(context.get('project', ''))
    outputs = context.get('outputs', {})
    params = context.get('params', {})

    required_cols = params.get('required_columns', REQUIRED_COLUMNS)

    db_path = _find_db(root, project, outputs)
    if db_path is None:
        return True, "no database found, skipping traceability check"

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Get tables to check
    target_tables = _normalize_tables(outputs)

    if not target_tables:
        # Check all non-system tables
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        target_tables = [r[0] for r in cursor.fetchall()]

    if not target_tables:
        conn.close()
        return True, "no tables found in database"

    missing_cols = []  # tables missing required columns entirely
    warnings = []

    for table in target_tables:
        cursor.execute(f"PRAGMA table_info([{table}])")
        columns = {r[1] for r in cursor.fetchall()}

        absent = [c for c in required_cols if c not in columns]
        if absent:
            missing_cols.append(f"{table}: missing {', '.join(absent)}")
            continue

        # Columns exist — check for NULL values in current batch
        operation_id = outputs.get('operation_id', '')
        for col in required_cols:
            if operation_id:
                cursor.execute(
                    f"SELECT COUNT(*) FROM [{table}] WHERE [{col}] IS NULL AND [_operation_id] = ?",
                    (operation_id,)
                )
            else:
                cursor.execute(
                    f"SELECT COUNT(*) FROM [{table}] WHERE [{col}] IS NULL"
                )
            null_count = cursor.fetchone()[0]
            if null_count > 0:
                scope = f" (batch: {operation_id})" if operation_id else ""
                warnings.append(f"{table}.{col}: {null_count} NULL values{scope}")

    conn.close()

    if missing_cols:
        return False, (
            f"Traceability columns missing: {'; '.join(missing_cols)}. "
            f"Required: {', '.join(required_cols)}"
        )

    msg = f"traceability check passed for {len(target_tables)} table(s)"
    if warnings:
        msg += f" | WARN: {'; '.join(warnings)}"
    return True, msg
