"""Promotion queue and eval-history state manager.

Manages two files in `shared/workflows/state/`:
  - promotion_queue.json  : candidates waiting to be processed by skill_self_learning
  - eval_history.json     : durable outcomes of past evaluations (proposed / in_progress /
                            below_threshold / overlap / ...), consulted by
                            _scan_and_queue_candidates to prevent indefinite re-enqueueing

Queue entry shape:
    {"learning_id": "STD-L041", "meta": {...}, "queued_at": "<iso>"}

Eval-history entry shape:
    "<learning_id>": {"result": "proposed|in_progress|failed|below_threshold|overlap|unknown",
                      "evaluated_at": "<iso>", ...extra kwargs}

All read-modify-write operations hold a per-file advisory lock (O_CREAT|O_EXCL sentinel)
before reading, so concurrent callers (hooks, validators, coordinator completion block)
cannot lose updates. Atomic rename is still used for the write itself to prevent partial
reads of an in-progress write.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _pid_alive(pid: int) -> bool:
    """Return True if the process is still running (cross-platform)."""
    if sys.platform == 'win32':
        import ctypes
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        handle = ctypes.windll.kernel32.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION, False, pid
        )
        if not handle:
            return False
        code = ctypes.c_ulong()
        ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(handle)
        return code.value == STILL_ACTIVE
    else:
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True  # Exists under different user


# ─── Advisory file lock ──────────────────────────────────────────────────────

class _FileLock:
    """Per-file advisory lock using an O_CREAT|O_EXCL sentinel file.

    Stale-lock detection: reads the PID from the sentinel file and calls
    os.kill(pid, 0) to verify the owner is still alive.  Only a confirmed-dead
    owner causes the lock to be stolen.  Time-based fallback (60 s age) applies
    only when the PID cannot be read (empty / corrupt sentinel).
    Lock files are named <target>.lock (e.g. promotion_queue.json.lock).
    """

    def __init__(self, path: Path, timeout: float = 10.0, interval: float = 0.05):
        self._path = path
        self._timeout = timeout
        self._interval = interval

    def _is_stale(self) -> bool:
        """Return True only when the lock owner is confirmed dead."""
        try:
            pid = int(self._path.read_text(encoding='utf-8').strip())
        except (OSError, ValueError):
            # Can't read PID → age-based fallback (generous 60 s)
            try:
                return time.time() - self._path.stat().st_mtime > 60
            except OSError:
                return True
        return not _pid_alive(pid)

    def __enter__(self) -> '_FileLock':
        self._path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + self._timeout
        while True:
            try:
                fd = os.open(
                    str(self._path),
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                )
                os.write(fd, str(os.getpid()).encode())
                os.close(fd)
                return self
            except FileExistsError:
                if self._is_stale():
                    try:
                        self._path.unlink()
                    except OSError:
                        pass
                    continue  # Retry acquisition immediately
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        f"Could not acquire lock within {self._timeout}s: {self._path}"
                    )
                time.sleep(self._interval)

    def __exit__(self, *_: Any) -> None:
        try:
            self._path.unlink()
        except OSError:
            pass


def _lock_for(path: Path) -> _FileLock:
    """Return a _FileLock for the given data file."""
    return _FileLock(path.with_suffix(path.suffix + '.lock'))


# ─── Queue helpers ───────────────────────────────────────────────────────────

def get_queue_path(root: Path | str) -> Path:
    return Path(root) / 'shared' / 'workflows' / 'state' / 'promotion_queue.json'


def load_queue(root: Path | str) -> list[dict[str, Any]]:
    """Read queue JSON without locking (pure read, safe for observers)."""
    path = get_queue_path(root)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def _save_queue(path: Path, queue: list[dict[str, Any]]) -> None:
    """Atomic write via .tmp rename. Caller must hold the lock."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(tmp, path)


def save_queue(root: Path | str, queue: list[dict[str, Any]]) -> None:
    """Atomic write under file lock (public alias for callers that manage the
    full queue themselves, e.g. migration scripts)."""
    path = get_queue_path(Path(root))
    with _lock_for(path):
        _save_queue(path, queue)


def add_candidate(
    root: Path | str,
    learning_id: str,
    meta: dict[str, Any] | None = None,
    suggested_skill: str | None = None,
) -> bool:
    """Idempotent add under file lock. Returns True if added, False if already present.

    suggested_skill: pre-populated skill name derived from refs_skill or
    caller knowledge. If None, select_candidate must derive it at runtime.
    """
    path = get_queue_path(Path(root))
    with _lock_for(path):
        queue = load_queue(root)
        for entry in queue:
            if entry.get('learning_id') == learning_id:
                return False
        entry: dict[str, Any] = {
            'learning_id': learning_id,
            'meta': meta or {},
            'queued_at': datetime.now(timezone.utc).isoformat(),
        }
        if suggested_skill:
            entry['suggested_skill'] = suggested_skill
        queue.append(entry)
        _save_queue(path, queue)
        return True


def remove_candidate(root: Path | str, learning_id: str) -> bool:
    """Remove a candidate by id under file lock. Returns True if removed."""
    path = get_queue_path(Path(root))
    with _lock_for(path):
        queue = load_queue(root)
        new_queue = [e for e in queue if e.get('learning_id') != learning_id]
        if len(new_queue) == len(queue):
            return False
        _save_queue(path, new_queue)
        return True


# ─── Eval-history helpers ────────────────────────────────────────────────────

def _eval_history_path(root: Path | str) -> Path:
    return Path(root) / 'shared' / 'workflows' / 'state' / 'eval_history.json'


def load_eval_history(root: Path | str) -> dict[str, Any]:
    """Read eval_history.json without locking (pure read, safe for observers)."""
    path = _eval_history_path(root)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if isinstance(data, dict):
            return data
        return {}
    except Exception:
        return {}


def _save_eval_history(path: Path, history: dict[str, Any]) -> None:
    """Atomic write via .tmp rename. Caller must hold the lock."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(tmp, path)


def record_eval_result(
    root: Path | str,
    learning_id: str,
    result: str,
    **kwargs: Any,
) -> None:
    """Persist an evaluation outcome under file lock.

    result: 'proposed' | 'in_progress' | 'below_threshold' | 'overlap' | 'unknown'
    Extra kwargs (pass_rate, proposal_path, …) are stored alongside.
    """
    path = _eval_history_path(Path(root))
    with _lock_for(path):
        history = load_eval_history(root)
        history[learning_id] = {
            'result': result,
            'evaluated_at': datetime.now(timezone.utc).isoformat(),
            **kwargs,
        }
        _save_eval_history(path, history)
