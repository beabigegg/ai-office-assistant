#!/usr/bin/env python3
"""Knowledge Base Writer — Append-only tool for decisions.md and learning_notes.md.

Bypasses Claude Code's Edit tool (which requires reading the entire file first)
by directly appending formatted markdown blocks to the end of files.

Usage:
    python kb_writer.py next-id
    python kb_writer.py add-decision --id D-111 --date 2026-03-09 --project ecr-ecn \
        --target "..." --question "..." --decision "..." --impact "..."
    python kb_writer.py add-learning --id ECR-L49 --title "..." --date 2026-03-09 \
        --content "..." --confidence high

Architecture note (EVO-003):
    .md files remain the source of truth. This tool only appends new entries.
    Modifications to existing entries still use Read + Edit (rare, <5% of operations).
    All validators (check_decisions, check_dynamic_kb_status) remain unchanged.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent.parent
KB_ROOT = ROOT / 'shared' / 'kb'
DECISIONS_PATH = KB_ROOT / 'decisions.md'
LEARNING_PATH = KB_ROOT / 'dynamic' / 'learning_notes.md'


def _read_tail(filepath: Path, num_bytes: int = 4096) -> str:
    """Read the last N bytes of a file efficiently (no full read)."""
    size = filepath.stat().st_size
    with open(filepath, 'rb') as f:
        if size > num_bytes:
            f.seek(size - num_bytes)
        raw = f.read()
    text = raw.decode('utf-8', errors='replace')
    # Skip partial first line (may have been cut mid-character)
    nl = text.find('\n')
    if nl >= 0 and size > num_bytes:
        text = text[nl + 1:]
    return text


def _find_last_decision_id(filepath: Path) -> int:
    """Find the highest D-NNN id in decisions.md by scanning the tail."""
    # Read last 8KB - should contain at least the last few decisions
    tail = _read_tail(filepath, 8192)
    ids = [int(m.group(1)) for m in re.finditer(r'### D-(\d+)\s', tail)]
    if ids:
        return max(ids)
    # Fallback: scan more
    tail = _read_tail(filepath, 32768)
    ids = [int(m.group(1)) for m in re.finditer(r'### D-(\d+)\s', tail)]
    return max(ids) if ids else 0


def _find_last_learning_id(filepath: Path) -> str:
    """Find the last ECR-Lxx id in learning_notes.md."""
    tail = _read_tail(filepath, 8192)
    ids = [int(m.group(1)) for m in re.finditer(r'### ECR-L(\d+)', tail)]
    if ids:
        return max(ids)
    tail = _read_tail(filepath, 32768)
    ids = [int(m.group(1)) for m in re.finditer(r'### ECR-L(\d+)', tail)]
    return max(ids) if ids else 0


def cmd_next_id(args):
    """Print the next available D-NNN id."""
    last_id = _find_last_decision_id(DECISIONS_PATH)
    next_id = last_id + 1
    print(json.dumps({"next_id": f"D-{next_id:03d}", "last_id": f"D-{last_id:03d}"}))


def cmd_add_decision(args):
    """Append a new decision block to decisions.md."""
    # Validate ID format
    m = re.match(r'^D-(\d+)$', args.id)
    if not m:
        print(json.dumps({"ok": False, "error": f"Invalid ID format: {args.id}, expected D-NNN"}))
        sys.exit(1)

    new_num = int(m.group(1))
    last_num = _find_last_decision_id(DECISIONS_PATH)

    if new_num != last_num + 1:
        print(json.dumps({
            "ok": False,
            "error": f"ID not sequential: {args.id}, expected D-{last_num + 1:03d} (last is D-{last_num:03d})"
        }))
        sys.exit(1)

    # Build meta line
    meta_parts = [f"status={args.status or 'active'}"]
    meta_parts.append(f"target={args.target}")
    if args.supersedes:
        meta_parts.append(f"supersedes={args.supersedes}")
    if args.refs_skill:
        meta_parts.append(f"refs_skill={args.refs_skill}")
    if args.refs_db:
        meta_parts.append(f"refs_db={args.refs_db}")
    if args.affects:
        meta_parts.append(f"affects={args.affects}")
    if args.review_by:
        meta_parts.append(f"review_by={args.review_by}")
    meta_line = f"<!-- kb: {', '.join(meta_parts)} -->"

    # Build decision block
    lines = [
        "",
        f"### {args.id} -- {args.date} -- {args.project}",
        meta_line,
        f"- 問題：{args.question}",
        f"- 決定：{args.decision}",
        f"- 影響：{args.impact}",
    ]
    if args.source:
        lines.append(f"- 來源：{args.source}")
    lines.append("")  # trailing newline

    block = "\n".join(lines)

    # Ensure file ends with newline before appending
    with open(DECISIONS_PATH, 'rb') as f:
        f.seek(-1, 2)
        last_byte = f.read(1)

    with open(DECISIONS_PATH, 'a', encoding='utf-8') as f:
        if last_byte != b'\n':
            f.write('\n')
        f.write(block)

    print(json.dumps({
        "ok": True,
        "id": args.id,
        "file": str(DECISIONS_PATH.relative_to(ROOT)),
        "lines_added": len(lines),
    }))


def cmd_add_learning(args):
    """Append a new learning note to learning_notes.md."""
    # Build block
    lines = [
        "",
        f"### {args.id} {args.title} — {args.date}",
        f"<!-- status: {args.status or 'active'} -->",
        f"- 觀察：{args.content}",
        f"- 信心度：{args.confidence}",
    ]
    if args.project:
        lines.append(f"- 相關專案：{args.project}")
    if args.related_decision:
        lines.append(f"- 相關決策：{args.related_decision}")
    lines.append("")  # trailing newline

    block = "\n".join(lines)

    # Ensure file ends with newline before appending
    with open(LEARNING_PATH, 'rb') as f:
        f.seek(-1, 2)
        last_byte = f.read(1)

    with open(LEARNING_PATH, 'a', encoding='utf-8') as f:
        if last_byte != b'\n':
            f.write('\n')
        f.write(block)

    print(json.dumps({
        "ok": True,
        "id": args.id,
        "file": str(LEARNING_PATH.relative_to(ROOT)),
        "lines_added": len(lines),
    }))


def main():
    parser = argparse.ArgumentParser(description="Knowledge Base Writer (append-only)")
    sub = parser.add_subparsers(dest='command')

    # next-id
    sub.add_parser('next-id', help='Print next available D-NNN id')

    # add-decision
    p_dec = sub.add_parser('add-decision', help='Append a decision to decisions.md')
    p_dec.add_argument('--id', required=True, help='Decision ID (D-NNN)')
    p_dec.add_argument('--date', required=True, help='Date (YYYY-MM-DD)')
    p_dec.add_argument('--project', required=True, help='Project name')
    p_dec.add_argument('--target', required=True, help='Target/topic of the decision')
    p_dec.add_argument('--question', required=True, help='The question being decided')
    p_dec.add_argument('--decision', required=True, help='The decision made')
    p_dec.add_argument('--impact', required=True, help='Impact of the decision')
    p_dec.add_argument('--status', default='active', help='Status (default: active)')
    p_dec.add_argument('--supersedes', help='ID of superseded decision (D-XXX)')
    p_dec.add_argument('--refs_skill', help='Referenced skill name')
    p_dec.add_argument('--refs_db', help='Referenced db:table')
    p_dec.add_argument('--affects', help='Affected scope')
    p_dec.add_argument('--review_by', help='TTL review date (YYYY-MM-DD)')
    p_dec.add_argument('--source', help='Source of the decision')

    # add-learning
    p_learn = sub.add_parser('add-learning', help='Append a learning note to learning_notes.md')
    p_learn.add_argument('--id', required=True, help='Learning ID (e.g. ECR-L49)')
    p_learn.add_argument('--title', required=True, help='Note title')
    p_learn.add_argument('--date', required=True, help='Date (YYYY-MM-DD)')
    p_learn.add_argument('--content', required=True, help='Observation content')
    p_learn.add_argument('--confidence', required=True, choices=['high', 'medium', 'low'],
                         help='Confidence level')
    p_learn.add_argument('--status', default='active', help='Status (default: active)')
    p_learn.add_argument('--project', help='Related project')
    p_learn.add_argument('--related_decision', help='Related decision ID (D-NNN)')

    args = parser.parse_args()

    if args.command == 'next-id':
        cmd_next_id(args)
    elif args.command == 'add-decision':
        cmd_add_decision(args)
    elif args.command == 'add-learning':
        cmd_add_learning(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
