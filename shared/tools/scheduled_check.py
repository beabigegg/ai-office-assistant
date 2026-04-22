#!/usr/bin/env python3
"""Scheduled knowledge-base health check.

Runs ``kb.py validate`` and ``kb.py catalog`` and stays silent when everything is OK.

Convention
----------
Only speak when there is a problem. Silence = healthy. This keeps scheduled
runs (cron, Task Scheduler, pre-session hook) noise-free and trains operators
to take any output at all as a signal that attention is needed.

Output modes
------------
- No issues:     ``[SILENT] kb health OK at YYYY-MM-DD HH:MM`` (single line)
- Issues found:  full timestamped report to stdout (validate output + catalog)
- ``--force``:   full report regardless of state (useful for smoke tests)
- ``--catalog-on-clean`` attaches the catalog summary even when silent

Exit codes
----------
0  — healthy (or forced)
1  — validate reported WARN/INFO (degraded but not blocking)
2  — validate reported ERROR or the script itself failed
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent.parent
KB_PY = SCRIPT_DIR / 'kb.py'


def _python_executable() -> str:
    """Prefer CONDA_PYTHON_EXE (matches CLAUDE.md requirement); fall back to current."""
    return os.environ.get('CONDA_PYTHON_EXE') or sys.executable


def _run(args: list[str], timeout: int = 60) -> tuple[int, str, str]:
    """Run kb.py subcommand. Returns (returncode, stdout, stderr)."""
    env = os.environ.copy()
    env.setdefault('PYTHONUTF8', '1')
    env.setdefault('PYTHONIOENCODING', 'utf-8')
    cmd = [_python_executable(), str(KB_PY), *args]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=timeout,
            env=env,
            cwd=str(ROOT),
        )
        return proc.returncode, proc.stdout or '', proc.stderr or ''
    except subprocess.TimeoutExpired:
        return 124, '', f'timeout after {timeout}s'
    except Exception as exc:  # noqa: BLE001
        return 99, '', f'{type(exc).__name__}: {exc}'


def _classify(validate_stdout: str, validate_rc: int) -> tuple[str, int, int, int]:
    """Return (severity, errors, warns, infos). severity in {OK, INFO, WARN, ERROR}."""
    errors = warns = infos = 0
    for line in validate_stdout.splitlines():
        line = line.strip()
        if line.startswith('ERROR'):
            errors += 1
        elif line.startswith('WARN'):
            warns += 1
        elif line.startswith('INFO'):
            infos += 1

    if validate_rc >= 2 or errors:
        return 'ERROR', errors, warns, infos
    if warns:
        return 'WARN', errors, warns, infos
    if infos:
        return 'INFO', errors, warns, infos
    return 'OK', errors, warns, infos


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Scheduled KB health check. Silent when healthy.'
    )
    parser.add_argument('--force', action='store_true',
                        help='Always print full report, even when healthy.')
    parser.add_argument('--catalog-on-clean', action='store_true',
                        help='Include catalog summary in SILENT line (still one-pass).')
    parser.add_argument('--timeout', type=int, default=60)
    args = parser.parse_args()

    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    validate_rc, validate_out, validate_err = _run(['validate'], timeout=args.timeout)
    severity, errors, warns, infos = _classify(validate_out, validate_rc)

    # Catalog is cheap and useful when we need to speak
    catalog_rc, catalog_out, catalog_err = _run(['catalog'], timeout=args.timeout)

    silent_line = f"[SILENT] kb health OK at {now}"
    if args.catalog_on_clean and severity == 'OK':
        # Append a compact catalog fingerprint so cron logs have one-line evidence
        cat_tail = ' | '.join(
            ln.strip() for ln in catalog_out.splitlines()
            if ln.startswith(('Content in DB', 'Embeddings', 'Projects', 'Recent'))
        )
        if cat_tail:
            silent_line += f" — {cat_tail}"

    if severity == 'OK' and not args.force:
        print(silent_line)
        return 0

    # Loud mode: full report
    banner = '=' * 60
    print(banner)
    print(f"[KB HEALTH CHECK] {now}  severity={severity}  "
          f"(ERR={errors} WARN={warns} INFO={infos})")
    print(banner)

    print("\n--- kb.py validate ---")
    if validate_out.strip():
        print(validate_out.rstrip())
    else:
        print('(no output)')
    if validate_err.strip():
        print(f"stderr: {validate_err.rstrip()}")
    print(f"validate exit code: {validate_rc}")

    print("\n--- kb.py catalog ---")
    if catalog_out.strip():
        print(catalog_out.rstrip())
    else:
        print('(no output)')
    if catalog_err.strip():
        print(f"stderr: {catalog_err.rstrip()}")

    print(banner)
    if severity == 'ERROR':
        return 2
    if severity in ('WARN', 'INFO'):
        return 1
    return 0  # forced but clean


if __name__ == '__main__':
    sys.exit(main())
