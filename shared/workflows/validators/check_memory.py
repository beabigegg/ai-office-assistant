"""Validator: check_memory
Checks if memory snapshot conditions are met and if snapshot exists.
"""
from pathlib import Path
from datetime import date


def validate(context: dict) -> tuple:
    root = Path(context.get('root', r'D:\AI_test'))
    outputs = context.get('outputs', {})
    memory_dir = root / 'shared' / 'kb' / 'memory'

    conditions_met = outputs.get('memory_conditions_met', False)
    today_str = date.today().strftime('%Y-%m-%d')
    snapshot_path = memory_dir / f'{today_str}.md'

    if not conditions_met:
        return True, "memory conditions not met, snapshot not required"

    if snapshot_path.exists():
        return True, f"snapshot written: {snapshot_path.name}"
    else:
        return False, f"conditions met but no snapshot found at {snapshot_path}"
