#!/usr/bin/env python3
"""Knowledge Base Writer — LEGACY WRAPPER.

EVO-012: This tool is superseded by kb.py. All commands are forwarded.
Kept for backward compatibility with existing validators and workflows.

Usage (deprecated — use kb.py instead):
    python kb_writer.py next-id          → python kb.py next-id
    python kb_writer.py add-decision ... → python kb.py add-decision ...
    python kb_writer.py add-learning ... → python kb.py add-learning ...
"""
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
KB_PY = SCRIPT_DIR / 'kb.py'

def main():
    args = sys.argv[1:]
    result = subprocess.run(
        [sys.executable, str(KB_PY)] + args,
        capture_output=False
    )
    sys.exit(result.returncode)

if __name__ == '__main__':
    main()
