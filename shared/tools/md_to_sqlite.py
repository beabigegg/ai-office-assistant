#!/usr/bin/env python3
"""
md_to_sqlite.py — Markdown → SQLite doc_sections 通用入庫工具

將 pdf_to_markdown.py 產出的 Markdown 切段後寫入 SQLite doc_sections 表。
按 heading 層級切段，保留 page 對應關係。

用法：
    # 入庫到指定 DB
    python md_to_sqlite.py ingest input.md \\
        --db workspace/db/machine_spec.db \\
        --machine-id HAD300D \\
        --doc-name "HAD300D操作手册"

    # 預覽切段結果（不寫 DB）
    python md_to_sqlite.py preview input.md

    # 清除後重新入庫（冪等）
    python md_to_sqlite.py ingest input.md \\
        --db workspace/db/machine_spec.db \\
        --machine-id HAD300D \\
        --doc-name "HAD300D操作手册" \\
        --replace

作為模組使用：
    from shared.tools.md_to_sqlite import MdToSections, ingest_sections
    sections = MdToSections.from_file("input.md")
    ingest_sections(sections, db_path, machine_id, doc_name)
"""

import argparse
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Section parsing
# ---------------------------------------------------------------------------

@dataclass
class Section:
    """切段結果"""
    section_title: str
    content: str
    page_start: Optional[int]
    page_end: Optional[int]
    word_count: int
    chapter: Optional[str] = None
    content_type: str = 'general'


# Page marker pattern: <!-- page N -->
_PAGE_MARKER = re.compile(r'<!--\s*page\s+(\d+)\s*-->')

# Heading patterns for segmentation
_HEADING = re.compile(
    r'^##\s+(.+?)$',
    re.MULTILINE
)

# Content type classification keywords
_CONTENT_TYPE_MAP = [
    ('safety', re.compile(r'safety|安全|防御|注意事项', re.I)),
    ('specification', re.compile(r'spec|dimension|weight|尺寸|重量|规格|需求', re.I)),
    ('operation', re.compile(r'operat|设定|操作|运行|调节|流程', re.I)),
    ('parameter', re.compile(r'param|设定|参数|设置|配置', re.I)),
    ('maintenance', re.compile(r'maint|calibrat|保养|校正|维修|维护', re.I)),
    ('software_ui', re.compile(r'menu|dialog|界面|软件|菜单|功能介绍', re.I)),
    ('inspection', re.compile(r'inspect|检测|检查|PBI|AXC', re.I)),
    ('programming', re.compile(r'program|编程|PP|process program', re.I)),
    ('troubleshooting', re.compile(r'error|alarm|故障|报警|troubleshoot', re.I)),
    ('overview', re.compile(r'overview|chapter|目录|介绍|简述|产品说明', re.I)),
]


def _classify_content(title: str, content: str) -> str:
    """根據標題和內容分類段落類型"""
    combined = f"{title} {content[:200]}"
    for ctype, pattern in _CONTENT_TYPE_MAP:
        if pattern.search(combined):
            return ctype
    return 'general'


class MdToSections:
    """Markdown → Section 列表"""

    def __init__(self, text: str, min_words: int = 5):
        self.text = text
        self.min_words = min_words

    @classmethod
    def from_file(cls, path: str, min_words: int = 5) -> 'MdToSections':
        text = Path(path).read_text(encoding='utf-8')
        return cls(text, min_words)

    def parse(self) -> list[Section]:
        """切段，回傳 Section 列表"""
        lines = self.text.split('\n')
        sections: list[Section] = []

        current_title = '(untitled)'
        current_lines: list[str] = []
        current_page_start: Optional[int] = None
        current_page_end: Optional[int] = None
        current_chapter: Optional[str] = None

        def flush():
            if not current_lines:
                return
            content = '\n'.join(current_lines).strip()
            wc = len(content.split())
            if wc < self.min_words:
                return
            ctype = _classify_content(current_title, content)
            sections.append(Section(
                section_title=current_title,
                content=content,
                page_start=current_page_start,
                page_end=current_page_end,
                word_count=wc,
                chapter=current_chapter,
                content_type=ctype,
            ))

        for line in lines:
            # Check for page marker
            pm = _PAGE_MARKER.match(line.strip())
            if pm:
                pg = int(pm.group(1))
                if current_page_start is None:
                    current_page_start = pg
                current_page_end = pg
                continue

            # Check for heading
            hm = _HEADING.match(line)
            if hm:
                flush()
                current_title = hm.group(1).strip()
                current_lines = []
                current_page_start = current_page_end  # inherit last seen page
                # Detect chapter
                if re.match(r'Chapter\s+\d+|第[一二三四五六七八九十\d]+章', current_title):
                    current_chapter = current_title
                continue

            current_lines.append(line)

        # Flush last section
        flush()

        return sections


# ---------------------------------------------------------------------------
# DB ingestion
# ---------------------------------------------------------------------------

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS doc_sections (
    section_id INTEGER PRIMARY KEY AUTOINCREMENT,
    machine_id TEXT NOT NULL,
    doc_name TEXT NOT NULL,
    doc_file TEXT,
    chapter TEXT,
    section_title TEXT,
    page_start INTEGER,
    page_end INTEGER,
    content TEXT NOT NULL,
    content_type TEXT,
    word_count INTEGER,
    source_page TEXT,
    FOREIGN KEY (machine_id) REFERENCES machines(machine_id)
)
"""

_INSERT_SQL = """
INSERT INTO doc_sections
    (machine_id, doc_name, doc_file, chapter, section_title,
     page_start, page_end, content, content_type, word_count, source_page)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def ingest_sections(
    sections: list[Section],
    db_path: str,
    machine_id: str,
    doc_name: str,
    doc_file: Optional[str] = None,
    replace: bool = False,
) -> int:
    """寫入 sections 到 SQLite，回傳寫入筆數"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Ensure table exists
    cur.execute(_CREATE_TABLE_SQL)

    if replace:
        cur.execute(
            "DELETE FROM doc_sections WHERE machine_id = ? AND doc_name = ?",
            (machine_id, doc_name),
        )

    count = 0
    for s in sections:
        source_page = None
        if s.page_start and s.page_end:
            source_page = f"p{s.page_start}-{s.page_end}" if s.page_start != s.page_end else f"p{s.page_start}"
        elif s.page_start:
            source_page = f"p{s.page_start}"

        cur.execute(_INSERT_SQL, (
            machine_id,
            doc_name,
            doc_file,
            s.chapter,
            s.section_title,
            s.page_start,
            s.page_end,
            s.content,
            s.content_type,
            s.word_count,
            source_page,
        ))
        count += 1

    conn.commit()
    conn.close()
    return count


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Markdown → SQLite doc_sections ingestion tool'
    )
    sub = parser.add_subparsers(dest='command', required=True)

    # preview
    p_prev = sub.add_parser('preview', help='Preview sections without writing DB')
    p_prev.add_argument('md', help='Markdown file path')

    # ingest
    p_ing = sub.add_parser('ingest', help='Ingest sections into SQLite')
    p_ing.add_argument('md', help='Markdown file path')
    p_ing.add_argument('--db', required=True, help='SQLite DB path')
    p_ing.add_argument('--machine-id', required=True, help='Machine ID')
    p_ing.add_argument('--doc-name', required=True, help='Document name')
    p_ing.add_argument('--doc-file', help='Original filename')
    p_ing.add_argument('--replace', action='store_true',
                       help='Delete existing sections for this machine+doc first')

    args = parser.parse_args()

    if args.command == 'preview':
        parser_obj = MdToSections.from_file(args.md)
        sections = parser_obj.parse()
        print(f"Sections: {len(sections)}")
        print(f"Total words: {sum(s.word_count for s in sections):,}")
        print()
        for i, s in enumerate(sections):
            pg = f"p{s.page_start}" if s.page_start else "?"
            print(f"  [{i+1:3}] {pg:>5} | {s.word_count:5}w | {s.content_type:15} | {s.section_title[:60]}")

    elif args.command == 'ingest':
        parser_obj = MdToSections.from_file(args.md)
        sections = parser_obj.parse()
        count = ingest_sections(
            sections,
            db_path=args.db,
            machine_id=args.machine_id,
            doc_name=args.doc_name,
            doc_file=args.doc_file,
            replace=args.replace,
        )
        print(f"Ingested {count} sections ({sum(s.word_count for s in sections):,} words)")


if __name__ == '__main__':
    main()
