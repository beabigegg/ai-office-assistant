"""Validator: check_dynamic_kb_status
M2: Ensures new entries in learning_notes.md have a <!-- status: active --> marker.
Checks only the last 3 entries (most recently added).
"""
import re
from pathlib import Path


def validate(context: dict) -> tuple:
    _default_root = Path(__file__).resolve().parent.parent.parent.parent
    root = Path(context.get('root', _default_root))
    learning_path = root / 'shared' / 'kb' / 'dynamic' / 'learning_notes.md'

    if not learning_path.exists():
        return True, "learning_notes.md not found, skipped"

    content = learning_path.read_text(encoding='utf-8')
    blocks = re.split(r'(?=^### .+)', content, flags=re.MULTILINE)

    # Check last 3 entries for status marker
    entry_blocks = [b for b in blocks if re.match(r'^### ', b)]
    if not entry_blocks:
        return True, "no entries found"

    recent = entry_blocks[-3:]
    missing = []
    for block in recent:
        title_match = re.match(r'^### (.+?)(?:\s*—|\s*$)', block)
        title = title_match.group(1).strip()[:40] if title_match else '?'

        has_explicit_status = bool(re.search(r'<!--\s*status:\s*(active|promoted|obsolete)\s*-->', block))
        has_promoted_tag = '[PROMOTED]' in block

        if not has_explicit_status and not has_promoted_tag:
            missing.append(title)

    if missing:
        return False, (
            f"M2: Recent learning_notes entries missing <!-- status: active --> marker: "
            f"{', '.join(missing)}. Add the marker to each entry header block."
        )

    return True, f"M2: last {len(recent)} entries have status markers"
