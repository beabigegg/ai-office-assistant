"""Validator: check_schema_loaded
Verifies that the AI actually read a SCHEMA file before proceeding to write SQL.

Checks:
1. outputs["schema_file"] must be non-empty
2. The referenced file must exist on disk
3. If outputs["db_path"] provided, SCHEMA filename should correspond to the DB

Part of Harness Engineering R1: Schema-First enforcement.
"""
from pathlib import Path


def validate(context: dict) -> tuple:
    _default_root = Path(__file__).resolve().parent.parent.parent.parent
    root = Path(context.get('root', _default_root))
    outputs = context.get('outputs', {})
    project = context.get('project', '')

    # 1. Check schema_file is provided
    schema_file = outputs.get('schema_file', '')
    if not schema_file:
        return False, (
            "Missing 'schema_file' in outputs. "
            "You must read a SCHEMA_{db}.md file and pass its path: "
            "--outputs '{\"schema_file\": \"path/to/SCHEMA_xxx.md\"}'"
        )

    # 2. Resolve and check file exists
    schema_path = Path(schema_file)
    if not schema_path.is_absolute():
        schema_path = root / schema_file

    if not schema_path.exists():
        return False, (
            f"Schema file does not exist: {schema_file}. "
            "Generate it first: bash shared/tools/conda-python.sh "
            "shared/tools/db_schema.py generate <db_path>"
        )

    # 3. Optional: verify SCHEMA filename matches db_path
    db_path = outputs.get('db_path', '')
    if db_path:
        db_stem = Path(db_path).stem  # e.g. "bom" from "bom.db"
        expected_name = f"SCHEMA_{db_stem}.md"
        if schema_path.name != expected_name:
            return False, (
                f"Schema file '{schema_path.name}' does not match DB '{Path(db_path).name}'. "
                f"Expected: {expected_name}"
            )

    return True, f"Schema loaded: {schema_path.name}"
