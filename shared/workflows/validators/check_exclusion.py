"""Validator: check_exclusion
Verifies that excluded records (RD-/PE- prefixes) are not in the database.

Supports scope parameter in validator_params:
  - "full_db": Check entire database (default, backward-compatible)
  - "current_batch": Only check records from the current ingestion batch,
    identified by operation_id. operation_id is resolved from (priority order):
      1. context["outputs"]["operation_id"]  (runtime, via --outputs on complete)
      2. context["params"]["operation_id"]   (static, from validator_params in JSON)
    Falls back to full_db if table lacks _operation_id column or operation_id is None.
"""
import sqlite3
from pathlib import Path


def validate(context: dict) -> tuple:
    root = Path(context.get('root', r'D:\AI_test'))
    project = context.get('project', '')
    params = context.get('params', {})
    outputs = context.get('outputs', {})
    excluded_prefixes = params.get('excluded_prefixes', ['RD-', 'PE-'])
    scope = params.get('scope', 'full_db')
    # operation_id: prefer runtime outputs over static params
    operation_id = outputs.get('operation_id') or params.get('operation_id', None)

    # Find SQLite DB
    if project:
        db_candidates = [
            root / 'projects' / project / 'workspace' / 'db',
            root / project / 'workspace' / 'db',
        ]
    else:
        db_candidates = list(root.glob('projects/*/workspace/db'))

    db_path = None
    for d in db_candidates:
        if d.is_dir():
            dbs = list(d.glob('*.db')) + list(d.glob('*.sqlite'))
            if dbs:
                db_path = dbs[0]
                break

    if db_path is None:
        return True, "no database found, skipping exclusion check"

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cursor.fetchall()]

    use_batch_scope = (scope == 'current_batch' and operation_id is not None)

    violations = []
    for table in tables:
        # Get columns
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [r[1] for r in cursor.fetchall()]

        pn_columns = [c for c in columns if any(
            kw in c.lower() for kw in ['part_number', 'part_no', 'pn', 'item_no', 'item_number']
        )]

        # Check if table supports batch filtering
        has_op_id = '_operation_id' in columns
        filter_batch = use_batch_scope and has_op_id

        for col in pn_columns:
            for prefix in excluded_prefixes:
                if filter_batch:
                    cursor.execute(
                        f"SELECT COUNT(*) FROM [{table}] WHERE [{col}] LIKE ? AND [_operation_id] = ?",
                        (f'{prefix}%', operation_id)
                    )
                else:
                    cursor.execute(
                        f"SELECT COUNT(*) FROM [{table}] WHERE [{col}] LIKE ?",
                        (f'{prefix}%',)
                    )
                count = cursor.fetchone()[0]
                if count > 0:
                    scope_label = f" (batch: {operation_id})" if filter_batch else ""
                    violations.append(f"{table}.{col}: {count} records with '{prefix}' prefix{scope_label}")

    conn.close()

    if violations:
        return False, f"excluded records found: {'; '.join(violations)}"

    scope_msg = f" (scope: {scope})" if scope != 'full_db' else ""
    return True, f"no excluded records found{scope_msg}"
