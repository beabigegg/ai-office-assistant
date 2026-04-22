#!/usr/bin/env python3
"""Backfill <!-- kb: --> meta lines for decisions.md entries that lack them.

Usage:
    python decision_meta_backfill.py --dry-run     # Preview changes
    python decision_meta_backfill.py --apply        # Apply changes
    python decision_meta_backfill.py --stats        # Show coverage statistics

Strategy:
    - Reads existing decisions.md
    - For entries without meta lines, generates minimal meta from available text
    - Auto-detects: status (from header markers), target (from question line),
      supersedes (from text references), refs_skill, refs_db
    - Inserts meta line after the ### header line
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DECISIONS_PATH = ROOT / 'shared' / 'kb' / 'decisions.md'

# Skills known to exist
KNOWN_SKILLS = [
    'bom-rules', 'process-bom-semantics', 'reliability-testing',
    'package-code', 'mil-std-750', 'pptx-operations',
    'excel-operations', 'word-operations'
]


def parse_blocks(content: str) -> list:
    """Split decisions.md into header + blocks."""
    parts = re.split(r'(?=^### D-\d+)', content, flags=re.MULTILINE)
    return parts


def detect_status(block: str) -> str:
    """Detect decision status from text markers."""
    if re.search(r'\[已修正|已取代|superseded\]', block, re.IGNORECASE):
        return 'superseded'
    if re.search(r'\[deprecated|已廢棄\]', block, re.IGNORECASE):
        return 'deprecated'
    return 'active'


def detect_target(block: str) -> str:
    """Extract target topic from question/issue line."""
    # Try 問題/議題 line
    m = re.search(r'[-]\s*(?:問題|議題)[:：]\s*(.+)', block)
    if m:
        text = m.group(1).strip()
        # Shorten to 80 chars, cut at sentence boundary if possible
        if len(text) > 80:
            cut = text[:77].rfind('，')
            if cut > 40:
                text = text[:cut]
            else:
                text = text[:77] + '...'
        return text
    return ''


def detect_supersedes(block: str, node_id: str) -> list:
    """Detect superseded decisions from text."""
    supersedes = []

    # Pattern: supersedes D-NNN / 取代 D-NNN / 推翻 D-NNN
    matches = re.findall(r'(?:supersedes?|取代|修正|推翻)\s*(?:→\s*)?(D-\d+)', block, re.IGNORECASE)
    for sid in matches:
        if sid != node_id and sid not in supersedes:
            supersedes.append(sid)

    # Pattern: D-NNN 的xxx完全推翻
    ref_matches = re.findall(r'(D-\d+)\s*的.*(?:推翻|修正|取代|superseded)', block, re.IGNORECASE)
    for sid in ref_matches:
        if sid != node_id and sid not in supersedes:
            supersedes.append(sid)

    return supersedes


def detect_refs_skill(block: str) -> list:
    """Detect skill references from text."""
    refs = []
    block_lower = block.lower()
    for skill in KNOWN_SKILLS:
        if skill in block_lower:
            refs.append(skill)
    return refs


def detect_refs_db(block: str) -> list:
    """Detect database references from text."""
    refs = []
    if re.search(r'bom\.db|std_bom|bom_material', block, re.IGNORECASE):
        refs.append('bom.db:std_bom')
    if re.search(r'ecr_ecn\.db|family_assignment|tech_family', block, re.IGNORECASE):
        refs.append('ecr_ecn.db')
    if re.search(r'master_part_list', block, re.IGNORECASE):
        refs.append('ecr_ecn.db:master_part_list')
    return refs


def detect_affects(block: str, project: str) -> list:
    """Detect cross-project impacts."""
    affects = []
    if 'BOM' in block and 'ecr-ecn' in project.lower():
        affects.append('BOM')
    if 'ecr-ecn' in block.lower() and 'bom' in project.lower():
        affects.append('ecr-ecn')
    return affects


def build_meta_line(status, target, supersedes, refs_skill, refs_db, affects) -> str:
    """Build a <!-- kb: ... --> meta line."""
    parts = [f'status={status}']

    if target:
        # Escape commas in target to avoid meta parse issues
        safe_target = target.replace(',', ';')
        parts.append(f'target={safe_target}')

    if supersedes:
        parts.append(f'supersedes={",".join(supersedes)}')

    if refs_skill:
        parts.append(f'refs_skill={"|".join(refs_skill)}')

    if refs_db:
        parts.append(f'refs_db={"|".join(refs_db)}')

    if affects:
        parts.append(f'affects={"|".join(affects)}')

    return f'<!-- kb: {", ".join(parts)} -->'


def process_decisions(dry_run=True):
    """Process decisions.md and backfill meta lines."""
    content = DECISIONS_PATH.read_text(encoding='utf-8')
    blocks = parse_blocks(content)

    stats = {'total': 0, 'has_meta': 0, 'backfilled': 0, 'skipped_header': 0}
    new_blocks = []

    for block in blocks:
        m = re.match(r'^### (D-(\d+))\s*--\s*(\d{4}-\d{2}-\d{2})\s*--\s*(.+?)(?:\s*\*\*.*\*\*)?\s*$',
                     block, re.MULTILINE)
        if not m:
            new_blocks.append(block)
            continue

        node_id = m.group(1)
        project = m.group(4).strip()
        stats['total'] += 1

        # Check if already has meta
        if re.search(r'<!--\s*kb:', block):
            stats['has_meta'] += 1
            new_blocks.append(block)
            continue

        # Detect fields
        status = detect_status(block)
        target = detect_target(block)
        supersedes = detect_supersedes(block, node_id)
        refs_skill = detect_refs_skill(block)
        refs_db = detect_refs_db(block)
        affects = detect_affects(block, project)

        meta_line = build_meta_line(status, target, supersedes, refs_skill, refs_db, affects)

        if dry_run:
            print(f'{node_id}: {meta_line}')
        else:
            # Insert meta line after header
            header_end = block.index('\n') + 1
            block = block[:header_end] + meta_line + '\n' + block[header_end:]

        stats['backfilled'] += 1
        new_blocks.append(block)

    if not dry_run:
        new_content = ''.join(new_blocks)
        DECISIONS_PATH.write_text(new_content, encoding='utf-8')
        print(f'Written {stats["backfilled"]} meta lines to decisions.md')

    return stats


def show_stats():
    """Show meta coverage statistics."""
    content = DECISIONS_PATH.read_text(encoding='utf-8')
    blocks = parse_blocks(content)

    total = 0
    with_meta = 0
    without_meta = []

    for block in blocks:
        m = re.match(r'^### (D-(\d+))', block)
        if not m:
            continue
        total += 1
        node_id = m.group(1)
        if re.search(r'<!--\s*kb:', block):
            with_meta += 1
        else:
            without_meta.append(node_id)

    pct = (with_meta / total * 100) if total else 0
    print(f'Total decisions: {total}')
    print(f'With meta:       {with_meta} ({pct:.1f}%)')
    print(f'Without meta:    {len(without_meta)}')
    if without_meta:
        # Show ranges
        ranges = []
        start = without_meta[0]
        prev = start
        for nid in without_meta[1:]:
            n_cur = int(nid.split('-')[1])
            n_prev = int(prev.split('-')[1])
            if n_cur == n_prev + 1:
                prev = nid
            else:
                if start == prev:
                    ranges.append(start)
                else:
                    ranges.append(f'{start}..{prev}')
                start = nid
                prev = nid
        if start == prev:
            ranges.append(start)
        else:
            ranges.append(f'{start}..{prev}')
        print(f'  Ranges: {", ".join(ranges)}')


def main():
    if sys.platform == 'win32':
        sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', errors='replace', closefd=False)

    if len(sys.argv) < 2:
        print('Usage: decision_meta_backfill.py --dry-run | --apply | --stats')
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == '--dry-run':
        stats = process_decisions(dry_run=True)
        print(f'\n--- Summary ---')
        print(f'Total: {stats["total"]}, Has meta: {stats["has_meta"]}, Would backfill: {stats["backfilled"]}')
    elif cmd == '--apply':
        stats = process_decisions(dry_run=False)
        print(f'Total: {stats["total"]}, Already had meta: {stats["has_meta"]}, Backfilled: {stats["backfilled"]}')
    elif cmd == '--stats':
        show_stats()
    else:
        print(f'Unknown option: {cmd}')
        sys.exit(1)


if __name__ == '__main__':
    main()
