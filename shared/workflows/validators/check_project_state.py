"""Validator: check_project_state
Verifies that project_state.md was recently modified (within max_age_seconds).
Also runs Block Memory content quality checks (WARN-level, non-blocking).
Also creates a single-version backup (.project_state.prev.md) before validation.
"""
import re
import shutil
import time
from pathlib import Path


def validate(context: dict) -> tuple:
    _default_root = Path(__file__).resolve().parent.parent.parent.parent
    root = Path(context.get('root', _default_root))
    project = context.get('project', '')
    params = context.get('params', {})
    max_age = params.get('max_age_seconds', 600)

    # Find project_state.md
    if project:
        candidates = [
            root / 'projects' / project / 'workspace' / 'project_state.md',
            root / project / 'workspace' / 'project_state.md',
        ]
    else:
        candidates = list(root.glob('projects/*/workspace/project_state.md'))

    target = None
    for c in candidates:
        if c.exists():
            target = c
            break

    if target is None:
        return False, "project_state.md not found for any project"

    # Auto-backup before validation (single version, overwritten each time)
    backup_path = target.parent / '.project_state.prev.md'
    try:
        shutil.copy2(str(target), str(backup_path))
    except OSError:
        pass  # best-effort backup, don't block on failure

    mtime = target.stat().st_mtime
    age = time.time() - mtime
    age_str = f"{int(age)}s" if age < 60 else f"{int(age/60)}m {int(age%60)}s"

    if age <= max_age:
        # Mtime OK — run Block Memory content quality checks (WARN-level, non-blocking)
        warnings = _check_content_quality(target)
        if warnings:
            warn_str = ' | '.join(warnings)
            return True, f"updated {age_str} ago — ⚠ WARN: {warn_str}"
        return True, f"updated {age_str} ago ({target.name})"
    else:
        return False, f"last modified {age_str} ago (threshold: {max_age}s) — {target}"


def _check_content_quality(target: Path) -> list:
    """Return list of warning strings (empty = clean). All checks are WARN-level."""
    try:
        content = target.read_text(encoding='utf-8')
    except OSError:
        return []
    lines = content.splitlines()
    warnings = []

    # 1. Line count soft limit (project_type-aware)
    project_type = 'project_management' if (
        'project_type: project_management' in content
        or '<!-- type: project_management' in content
    ) else 'knowledge'
    limit = 200 if project_type == 'project_management' else 150
    if len(lines) > limit:
        warnings.append(
            f"TOO LARGE: {len(lines)} lines (soft limit {limit} for {project_type}). "
            "Move history to project_history.md."
        )

    # 2. Required Block Memory sections
    required_sections = ['## 當前階段', '## 下一步行動',
                         '## 資料庫現況', '## 未解問題']
    missing = [s for s in required_sections if s not in content]
    if missing:
        warnings.append(f"MISSING SECTIONS: {missing}")

    # 3. Duplicate headings
    headers = re.findall(r'^#{1,3}\s+(.+)$', content, re.MULTILINE)
    dups = [h for h in set(headers) if headers.count(h) > 1]
    if dups:
        warnings.append(f"DUPLICATE HEADINGS: {dups}")

    # 4. Empty 下一步行動
    na_match = re.search(
        r'## 下一步行動\n(.*?)(?=\n##|\Z)', content, re.DOTALL
    )
    if na_match:
        na_lines = [
            l for l in na_match.group(1).splitlines()
            if l.strip() and not l.strip().startswith(('>', '注意', '（', '('))
        ]
        if not na_lines:
            warnings.append(
                "下一步行動 is empty — add actionable items or link to backlog."
            )

    return warnings
