"""Validator: check_memory
Checks if memory snapshot conditions are met and if snapshot exists.
Also checks MEMORY.md line count against 200-line hard limit.
"""
from pathlib import Path
from datetime import date

MEMORY_MD_LINE_LIMIT = 200
MEMORY_MD_WARN_THRESHOLD = 160


def validate(context: dict) -> tuple:
    _default_root = Path(__file__).resolve().parent.parent.parent.parent
    root = Path(context.get('root', _default_root))
    outputs = context.get('outputs', {})
    memory_dir = root / 'shared' / 'kb' / 'memory'

    warnings = []

    # --- Check 1: MEMORY.md line count ---
    memory_md_path = Path.home() / '.claude' / 'projects' / 'D--ai-office' / 'memory' / 'MEMORY.md'
    if memory_md_path.exists():
        line_count = len(memory_md_path.read_text(encoding='utf-8').splitlines())
        if line_count > MEMORY_MD_LINE_LIMIT:
            return False, (
                f"MEMORY.md has {line_count} lines (limit: {MEMORY_MD_LINE_LIMIT}). "
                f"Must consolidate or remove stale entries before continuing."
            )
        elif line_count > MEMORY_MD_WARN_THRESHOLD:
            warnings.append(
                f"MEMORY.md approaching limit: {line_count}/{MEMORY_MD_LINE_LIMIT} lines"
            )

    # --- Check 2: Memory snapshot ---
    conditions_met = outputs.get('memory_conditions_met', False)
    today_str = date.today().strftime('%Y-%m-%d')
    snapshot_path = memory_dir / f'{today_str}.md'

    if not conditions_met:
        msg = "memory conditions not met, snapshot not required"
        if warnings:
            msg += f" [WARN: {'; '.join(warnings)}]"
        return True, msg

    if snapshot_path.exists():
        msg = f"snapshot written: {snapshot_path.name}"
        if warnings:
            msg += f" [WARN: {'; '.join(warnings)}]"
        return True, msg
    else:
        return False, f"conditions met but no snapshot found at {snapshot_path}"
