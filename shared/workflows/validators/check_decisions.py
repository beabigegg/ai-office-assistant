"""Validator: check_decisions
Verifies decisions.md has sequential D-NNN numbering with no gaps.
"""
import re
from pathlib import Path


def validate(context: dict) -> tuple:
    _default_root = Path(__file__).resolve().parent.parent.parent.parent
    root = Path(context.get('root', _default_root))
    decisions_path = root / 'shared' / 'kb' / 'decisions.md'

    if not decisions_path.exists():
        return True, "decisions.md not found, no entries to validate"

    content = decisions_path.read_text(encoding='utf-8')
    numbers = sorted(set(int(m) for m in re.findall(r'###\s*D-(\d+)', content)))

    if not numbers:
        return True, "no D-NNN entries found"

    # Check for gaps
    expected = list(range(numbers[0], numbers[-1] + 1))
    gaps = sorted(set(expected) - set(numbers))

    if gaps:
        gap_strs = [f"D-{g:03d}" for g in gaps[:5]]
        suffix = f" (and {len(gaps)-5} more)" if len(gaps) > 5 else ""
        return False, f"gaps in numbering: {', '.join(gap_strs)}{suffix}"

    message = f"{len(numbers)} entries, D-{numbers[0]:03d} to D-{numbers[-1]:03d}"

    # Check recent decisions (last 5) for <!-- kb: --> meta line and extract targets
    recent_ids = numbers[-5:]
    blocks = re.split(r'(?=^###\s*D-\d+)', content, flags=re.MULTILINE)
    missing_meta = []
    recent_targets = {}  # {D-NNN: target_text} for conflict check
    for block in blocks:
        m = re.match(r'^###\s*D-(\d+)', block)
        if m and int(m.group(1)) in recent_ids:
            did = f"D-{int(m.group(1)):03d}"
            if not re.search(r'<!--\s*kb:', block):
                missing_meta.append(did)
            # Extract target for L2 conflict check
            target_match = re.search(r'target=([^,>]+)', block)
            if target_match:
                recent_targets[did] = target_match.group(1).strip()
    if missing_meta:
        message += f" | WARN: missing <!-- kb: --> meta: {', '.join(missing_meta)}"

    # Sync, validate, and regenerate active summary (non-blocking warnings)
    try:
        import subprocess, os
        kb_script = str(root / 'shared' / 'tools' / 'kb_index.py')
        env = dict(os.environ, PYTHONIOENCODING='utf-8')
        subprocess.run(
            ['python', kb_script, 'sync', '--quiet'],
            capture_output=True, timeout=10, cwd=str(root), env=env
        )
        val_result = subprocess.run(
            ['python', kb_script, 'validate', '--quiet'],
            capture_output=True, timeout=10, cwd=str(root),
            encoding='utf-8', errors='replace'
        )
        if val_result.returncode == 2:
            # ERROR level issues found — block the flow
            return False, f"KB consistency ERROR (must fix before proceeding): {val_result.stdout.strip()[:300]}"
        elif val_result.returncode == 1 and val_result.stdout.strip():
            message += f" | KB warnings: {val_result.stdout.strip()[:200]}"

        # L2: Proactive conflict check on recent decisions' targets
        for did, target_text in recent_targets.items():
            conflict_result = subprocess.run(
                ['python', kb_script, 'check-conflict', target_text, '--threshold', '0.5'],
                capture_output=True, timeout=10, cwd=str(root),
                encoding='utf-8', errors='replace'
            )
            if conflict_result.returncode == 1 and conflict_result.stdout.strip():
                # Filter out self-match (the decision checking against itself)
                conflict_lines = [
                    line for line in conflict_result.stdout.strip().split('\n')
                    if did not in line and line.strip().startswith(('D-', ' '))
                ]
                if conflict_lines:
                    message += f" | L2-CONFLICT {did}: {'; '.join(l.strip() for l in conflict_lines[:3])}"

        # Regenerate active rules summary (noise-reduced context for AI)
        subprocess.run(
            ['python', kb_script, 'generate-summary'],
            capture_output=True, timeout=15, cwd=str(root), env=env
        )
        message += " | active_rules_summary.md regenerated"

        # Regenerate _index.md (knowledge index, auto-synced)
        subprocess.run(
            ['python', kb_script, 'generate-index'],
            capture_output=True, timeout=15, cwd=str(root), env=env
        )
        message += " | _index.md regenerated"
    except Exception:
        pass  # KB index failure should not block main flow

    return True, message
