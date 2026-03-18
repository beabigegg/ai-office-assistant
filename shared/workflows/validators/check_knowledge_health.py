"""Validator: check_knowledge_health
Runs kb_index.py sync + validate at session start to surface:
- L3 TTL: expired review_by dates
- M1: supersede inconsistencies
- L2: semantic overlaps among active decisions
Reports issues as warnings (non-blocking) so the user is aware.
"""
import subprocess
from pathlib import Path


def validate(context: dict) -> tuple:
    root = Path(context.get('root', r'D:\AI_test'))
    kb_script = str(root / 'shared' / 'tools' / 'kb_index.py')

    try:
        env = dict(__import__('os').environ, PYTHONIOENCODING='utf-8')

        # Sync first (also triggers M1 auto-supersede)
        subprocess.run(
            ['python', kb_script, 'sync', '--quiet'],
            capture_output=True, timeout=15, cwd=str(root), env=env
        )

        # Validate (checks L2 fuzzy, L3 TTL, M1 consistency)
        result = subprocess.run(
            ['python', kb_script, 'validate', '--quiet'],
            capture_output=True, timeout=15, text=True, cwd=str(root),
            encoding='utf-8', errors='replace'
        )

        output = result.stdout.strip()
        if not output:
            return True, "Knowledge health: OK"

        # Extract only WARN and ERROR lines
        serious = [
            line for line in output.split('\n')
            if line.startswith(('WARN', 'ERROR'))
        ]

        if not serious:
            return True, "Knowledge health: OK"

        # Always pass (session_start should not block), but report issues
        return True, f"Knowledge health issues ({len(serious)}):\n" + '\n'.join(serious[:10])

    except Exception as e:
        return True, f"Knowledge health check skipped: {e}"
