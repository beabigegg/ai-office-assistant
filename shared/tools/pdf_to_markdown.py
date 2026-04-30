#!/usr/bin/env python3
"""
pdf_to_markdown.py — PDF → Markdown 通用轉換工具

混合方案：PyMuPDF 文字提取 + RapidOCR 截圖頁辨識 + Docling 表格增強。
適用於文字型 PDF（K&S 等英文手冊）和截圖型 PDF（Szhech 等中文手冊）。

用法：
    # 基本轉換
    python pdf_to_markdown.py convert input.pdf -o output.md

    # 預設啟用 Docling 表格增強（偵測表格頁 → Docling 提取跨頁表格）
    python pdf_to_markdown.py convert input.pdf -o output.md

    # 明確停用 Docling 表格增強
    python pdf_to_markdown.py convert input.pdf -o output.md --no-docling-tables

    # 僅分析（不轉換，顯示頁面統計 + 表格偵測）
    python pdf_to_markdown.py analyze input.pdf

    # 其他選項
    python pdf_to_markdown.py convert input.pdf -o output.md --ocr-dpi 200
    python pdf_to_markdown.py convert input.pdf -o output.md --pages 1-50
    python pdf_to_markdown.py convert input.pdf -o output.md --no-ocr

作為模組使用：
    from shared.tools.pdf_to_markdown import PdfToMarkdown
    converter = PdfToMarkdown(ocr_dpi=150, min_words_for_text=20)
    result = converter.convert("input.pdf")
    result.save("output.md")

    # 預設啟用 Docling 表格增強（跨頁表格自動偵測 + 分群處理）
    converter = PdfToMarkdown()
    result = converter.convert("input.pdf")
"""

import argparse
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PageResult:
    """單頁轉換結果"""
    page_num: int           # 1-based
    method: str             # 'text' | 'ocr' | 'text+ocr' | 'empty'
    text: str
    word_count: int
    ocr_lines: int = 0
    heading: Optional[str] = None   # 偵測到的標題（如 "3.2.1 xxx"）


@dataclass
class ConvertResult:
    """整份 PDF 轉換結果"""
    source: str
    total_pages: int
    pages: list[PageResult] = field(default_factory=list)
    elapsed_sec: float = 0.0

    @property
    def text_pages(self) -> int:
        return sum(1 for p in self.pages if p.method == 'text')

    @property
    def ocr_pages(self) -> int:
        return sum(1 for p in self.pages if 'ocr' in p.method)

    @property
    def docling_pages(self) -> int:
        return sum(1 for p in self.pages if p.method == 'docling')

    @property
    def empty_pages(self) -> int:
        return sum(1 for p in self.pages if p.method == 'empty')

    @property
    def total_words(self) -> int:
        return sum(p.word_count for p in self.pages)

    def to_markdown(self, include_page_markers: bool = True) -> str:
        """產出完整 Markdown 文件"""
        parts = []
        for p in self.pages:
            if not p.text.strip():
                continue
            if include_page_markers:
                parts.append(f'\n<!-- page {p.page_num} -->\n')
            if p.heading:
                parts.append(f'\n## {p.heading}\n')
            parts.append(p.text)
        return '\n'.join(parts)

    def save(self, path: str, include_page_markers: bool = True) -> Path:
        """儲存 Markdown 到檔案"""
        out = Path(path)
        out.write_text(self.to_markdown(include_page_markers), encoding='utf-8')
        return out

    def summary(self) -> str:
        """產出摘要統計"""
        method_parts = [f"{self.text_pages} text"]
        if self.ocr_pages:
            method_parts.append(f"{self.ocr_pages} ocr")
        if self.docling_pages:
            method_parts.append(f"{self.docling_pages} docling")
        if self.empty_pages:
            method_parts.append(f"{self.empty_pages} empty")
        lines = [
            f"Source: {self.source}",
            f"Pages:  {self.total_pages} total, {', '.join(method_parts)}",
            f"Words:  {self.total_words:,}",
            f"Time:   {self.elapsed_sec:.1f}s",
        ]
        return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Heading detection patterns
# ---------------------------------------------------------------------------

# N.N.N Title (English technical manuals)
_HEADING_EN = re.compile(
    r'^(\d+\.\d+(?:\.\d+)*)\s+([A-Z][A-Za-z\s\-/&,()]+)', re.MULTILINE
)
# Chapter N: Title
_HEADING_CHAPTER = re.compile(
    r'^(Chapter\s+\d+):\s*(.+)', re.MULTILINE
)
# 中文標題：N.N.N 中文（Szhech 手冊）
_HEADING_CN = re.compile(
    r'^(\d+\.\d+(?:\.\d+)*)\s*([\u4e00-\u9fff].+)', re.MULTILINE
)
# 第N章 中文
_HEADING_CN_CHAPTER = re.compile(
    r'^(第[一二三四五六七八九十\d]+章)\s*(.*)', re.MULTILINE
)


def _detect_heading(text: str) -> Optional[str]:
    """偵測頁面中最早出現的標題"""
    for pattern in [_HEADING_CHAPTER, _HEADING_EN, _HEADING_CN_CHAPTER, _HEADING_CN]:
        m = pattern.search(text[:500])  # 只看前 500 字元
        if m:
            return m.group(0).strip()
    return None


# ---------------------------------------------------------------------------
# Page header stripping
# ---------------------------------------------------------------------------

# K&S ConnX ELITE header pattern
_HEADER_KS = re.compile(
    r'^.{0,80}\n'
    r'98895-\S+\n'
    r'Revision [A-Z]\n'
    r'ConnX.*\n'
    r'(?:Operator|Reference|Programmer|Maintenance).*(?:Guide|Manual).*\n'
    r'Page [\w-]+\n',
    re.MULTILINE
)

# Szhech HOSON header
_HEADER_HOSON = re.compile(
    r'^HOSON\n.*?操作手册\n',
    re.MULTILINE
)

# Generic page number line at top/bottom
_PAGE_NUM = re.compile(r'^\s*-?\s*\d+\s*-?\s*$', re.MULTILINE)


def _strip_headers(text: str) -> str:
    """移除頁首/頁尾模板文字"""
    text = _HEADER_KS.sub('', text)
    text = _HEADER_HOSON.sub('', text)
    # Remove isolated page numbers (but not in middle of content)
    lines = text.split('\n')
    if lines and _PAGE_NUM.match(lines[0]):
        lines = lines[1:]
    if lines and _PAGE_NUM.match(lines[-1]):
        lines = lines[:-1]
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Main converter
# ---------------------------------------------------------------------------

class PdfToMarkdown:
    """PDF → Markdown 轉換器

    Args:
        ocr_dpi: OCR 渲染解析度（預設 150，越高越精確但越慢）
        min_words_for_text: 低於此字數的頁面觸發 OCR（預設 20）
        use_ocr: 是否啟用 OCR（預設 True）
        use_docling_tables: 啟用 Docling 表格增強（預設 True）
            偵測含表格的頁面，將連續表格頁分群後用 Docling 處理，
            保留跨頁表格的完整結構。需安裝 docling 套件。
        docling_max_batch: Docling 單批最大頁數（預設 15，避開記憶體 bug）
    """

    def __init__(
        self,
        ocr_dpi: int = 150,
        min_words_for_text: int = 20,
        use_ocr: bool = True,
        use_docling_tables: bool = True,
        docling_max_batch: int = 15,
    ):
        self.ocr_dpi = ocr_dpi
        self.min_words = min_words_for_text
        self.use_ocr = use_ocr
        self.use_docling_tables = use_docling_tables
        self.docling_max_batch = docling_max_batch
        self._ocr_engine = None

    def _get_ocr(self):
        """Lazy-load RapidOCR (auto-detect GPU)"""
        if self._ocr_engine is None:
            import logging
            logging.getLogger('RapidOCR').setLevel(logging.WARNING)
            from rapidocr import RapidOCR
            # Enable CUDA if onnxruntime-gpu is available
            params = {}
            try:
                import onnxruntime as ort
                if 'CUDAExecutionProvider' in ort.get_available_providers():
                    params = {"EngineConfig.onnxruntime.use_cuda": True}
            except ImportError:
                pass
            self._ocr_engine = RapidOCR(params=params)
        return self._ocr_engine

    def _ocr_page(self, page) -> str:
        """對單頁做 OCR，回傳辨識文字"""
        import numpy as np

        ocr = self._get_ocr()
        scale = self.ocr_dpi / 72.0
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, pix.n
        )
        # RGB only (drop alpha if present)
        if pix.n == 4:
            img = img[:, :, :3]

        result = ocr(img)
        if result.txts:
            return '\n'.join(result.txts)
        return ''

    # -------------------------------------------------------------------
    # Docling table enhancement
    # -------------------------------------------------------------------

    @staticmethod
    def detect_table_groups(
        pdf_path: str,
        page_range: Optional[tuple[int, int]] = None,
        min_rows: int = 3,
        min_cols: int = 2,
        max_group_size: int = 15,
    ) -> list[list[int]]:
        """用 PyMuPDF find_tables() 偵測表格頁並分群。

        連續的表格頁合併為一組（跨頁表格），超過 max_group_size 則拆分。
        回傳 [[page_num, ...], ...] (1-based)。
        """
        doc = fitz.open(str(pdf_path))
        total = len(doc)
        start = page_range[0] if page_range else 1
        end = page_range[1] if page_range else total

        table_pages = []
        for i in range(max(0, start - 1), min(total, end)):
            page = doc[i]
            tables = page.find_tables()
            real = [t for t in tables.tables
                    if t.row_count >= min_rows and t.col_count >= min_cols]
            if real:
                table_pages.append(i + 1)
        doc.close()

        if not table_pages:
            return []

        # Group consecutive pages
        groups: list[list[int]] = []
        cur = [table_pages[0]]
        for pg in table_pages[1:]:
            if pg == cur[-1] + 1:
                cur.append(pg)
            else:
                groups.append(cur)
                cur = [pg]
        groups.append(cur)

        # Split oversized groups
        final: list[list[int]] = []
        for g in groups:
            while len(g) > max_group_size:
                final.append(g[:max_group_size])
                g = g[max_group_size:]
            if g:
                final.append(g)
        return final

    def _docling_convert_pages(
        self, pdf_path: str, page_start: int, page_end: int,
    ) -> dict[int, str]:
        """用 Docling 處理指定頁面範圍，回傳 {page_num: markdown_text}。

        每次建立新的 DocumentConverter 避開 docling-parse 記憶體累積 bug
        (docling-project/docling-parse#227)。
        """
        import gc
        import os
        import shutil

        # Windows symlink workaround for HuggingFace cache
        _orig = os.symlink
        def _safe(src, dst, *a, **kw):
            try:
                _orig(src, dst, *a, **kw)
            except OSError:
                if os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
        os.symlink = _safe

        try:
            from docling.document_converter import DocumentConverter, PdfFormatOption
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            from docling.datamodel.document import InputFormat
        except ImportError:
            print("WARNING: docling not installed, skipping table enhancement",
                  file=sys.stderr)
            return {}

        pipeline_opts = PdfPipelineOptions()
        pipeline_opts.do_ocr = self.use_ocr
        pipeline_opts.do_table_structure = True

        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_opts)
            }
        )

        result_map: dict[int, str] = {}
        try:
            result = converter.convert(
                str(pdf_path), page_range=(page_start, page_end)
            )
            md = result.document.export_to_markdown()
            # Store as a single block keyed by the start page
            # (Docling merges cross-page content, which is the whole point)
            result_map[page_start] = md
        except Exception as e:
            print(f"WARNING: Docling failed on pages {page_start}-{page_end}: "
                  f"{type(e).__name__}: {e}", file=sys.stderr)
        finally:
            os.symlink = _orig
            del converter
            gc.collect()

        return result_map

    def convert(
        self,
        pdf_path: str,
        page_range: Optional[tuple[int, int]] = None,
    ) -> ConvertResult:
        """轉換 PDF 為結構化結果

        Args:
            pdf_path: PDF 檔案路徑
            page_range: (start, end) 1-based inclusive，None 表示全部
        """
        t0 = time.time()
        doc = fitz.open(str(pdf_path))
        total = len(doc)

        if page_range:
            start, end = page_range
            start = max(1, start)
            end = min(total, end)
        else:
            start, end = 1, total

        result = ConvertResult(
            source=str(Path(pdf_path).name),
            total_pages=total,
        )

        # Step 0: Docling table enhancement — detect and process table groups
        docling_pages: dict[int, str] = {}  # page_num → docling markdown
        docling_covered: set[int] = set()   # pages handled by Docling
        if self.use_docling_tables:
            groups = self.detect_table_groups(
                pdf_path, page_range=(start, end),
                max_group_size=self.docling_max_batch,
            )
            if groups:
                n_table_pages = sum(len(g) for g in groups)
                print(f"Docling: {n_table_pages} table pages in "
                      f"{len(groups)} groups", file=sys.stderr)
                for gi, group in enumerate(groups):
                    g_start, g_end = group[0], group[-1]
                    print(f"  Group {gi+1}/{len(groups)}: "
                          f"pages {g_start}-{g_end} ({len(group)} pages)",
                          file=sys.stderr)
                    dm = self._docling_convert_pages(pdf_path, g_start, g_end)
                    docling_pages.update(dm)
                    docling_covered.update(range(g_start, g_end + 1))

        for i in range(start - 1, end):
            page = doc[i]
            page_num = i + 1

            # If this page is covered by Docling, use Docling output
            if page_num in docling_covered:
                # Only emit Docling content for the first page of each group
                if page_num in docling_pages:
                    dl_text = docling_pages[page_num]
                    wc = len(dl_text.split())
                    heading = _detect_heading(dl_text)
                    result.pages.append(PageResult(
                        page_num=page_num,
                        method='docling',
                        text=dl_text,
                        word_count=wc,
                        heading=heading,
                    ))
                # Skip non-first pages in the group (content merged by Docling)
                continue

            # Step 1: PyMuPDF text extraction
            raw_text = page.get_text().strip()
            clean_text = _strip_headers(raw_text)
            word_count = len(clean_text.split())

            # Step 2: Decide if OCR needed
            method = 'text'
            ocr_lines = 0
            final_text = clean_text

            if word_count < self.min_words and self.use_ocr:
                try:
                    ocr_text = self._ocr_page(page)
                    ocr_lines = len(ocr_text.split('\n')) if ocr_text else 0
                    if ocr_text:
                        ocr_text = _strip_headers(ocr_text)
                        if word_count > 0:
                            final_text = ocr_text
                            method = 'text+ocr'
                        else:
                            final_text = ocr_text
                            method = 'ocr'
                        word_count = len(final_text.split())
                except Exception:
                    pass

            if word_count == 0:
                method = 'empty'

            # Step 3: Detect heading
            heading = _detect_heading(final_text)

            result.pages.append(PageResult(
                page_num=page_num,
                method=method,
                text=final_text,
                word_count=word_count,
                ocr_lines=ocr_lines,
                heading=heading,
            ))

        doc.close()
        result.elapsed_sec = time.time() - t0
        return result

    def analyze(self, pdf_path: str) -> dict:
        """分析 PDF 頁面特性（不做 OCR），回傳統計"""
        doc = fitz.open(str(pdf_path))
        total = len(doc)
        stats = {
            'total_pages': total,
            'text_rich': 0,     # >min_words
            'low_text': 0,      # <=min_words but >0
            'no_text': 0,       # 0 words
            'has_images': 0,    # pages with embedded images
            'total_words': 0,
            'page_details': [],
        }

        for i in range(total):
            page = doc[i]
            text = page.get_text().strip()
            wc = len(text.split())
            imgs = len(page.get_images())
            stats['total_words'] += wc

            if wc > self.min_words:
                stats['text_rich'] += 1
                cat = 'text'
            elif wc > 0:
                stats['low_text'] += 1
                cat = 'low_text'
            else:
                stats['no_text'] += 1
                cat = 'no_text'

            if imgs > 0:
                stats['has_images'] += 1

            stats['page_details'].append({
                'page': i + 1,
                'words': wc,
                'images': imgs,
                'category': cat,
            })

        doc.close()
        return stats


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_pages(s: str) -> tuple[int, int]:
    """Parse '10-50' or '10' to (start, end) tuple"""
    if '-' in s:
        parts = s.split('-', 1)
        return int(parts[0]), int(parts[1])
    n = int(s)
    return n, n


def main():
    parser = argparse.ArgumentParser(
        description='PDF → Markdown converter (PyMuPDF + RapidOCR)'
    )
    sub = parser.add_subparsers(dest='command', required=True)

    # convert
    p_conv = sub.add_parser('convert', help='Convert PDF to Markdown')
    p_conv.add_argument('pdf', help='PDF file path')
    p_conv.add_argument('-o', '--output', required=True, help='Output .md path')
    p_conv.add_argument('--ocr-dpi', type=int, default=150, help='OCR DPI (default 150)')
    p_conv.add_argument('--pages', help='Page range, e.g. 1-50')
    p_conv.add_argument('--no-ocr', action='store_true', help='Disable OCR')
    p_conv.add_argument('--no-page-markers', action='store_true', help='Omit <!-- page N --> markers')
    p_conv.add_argument(
        '--docling-tables',
        dest='docling_tables',
        action='store_true',
        default=True,
        help='Enable Docling for detected table-heavy pages (default: enabled)',
    )
    p_conv.add_argument(
        '--no-docling-tables',
        dest='docling_tables',
        action='store_false',
        help='Disable Docling table enhancement and use PyMuPDF/OCR only',
    )

    # analyze
    p_ana = sub.add_parser('analyze', help='Analyze PDF without converting')
    p_ana.add_argument('pdf', help='PDF file path')

    args = parser.parse_args()

    if args.command == 'analyze':
        converter = PdfToMarkdown()
        stats = converter.analyze(args.pdf)
        print(f"File: {Path(args.pdf).name}")
        print(f"Total pages: {stats['total_pages']}")
        print(f"  Text-rich (>{converter.min_words}w): {stats['text_rich']}")
        print(f"  Low text:  {stats['low_text']}")
        print(f"  No text:   {stats['no_text']}")
        print(f"  Has images: {stats['has_images']}")
        print(f"Total words: {stats['total_words']:,}")
        pct_ocr = (stats['low_text'] + stats['no_text']) / stats['total_pages'] * 100
        print(f"OCR needed:  {pct_ocr:.0f}% of pages")
        # Table group analysis
        groups = PdfToMarkdown.detect_table_groups(args.pdf)
        n_table_pages = sum(len(g) for g in groups)
        print(f"Table pages: {n_table_pages} in {len(groups)} groups")
        for i, g in enumerate(groups[:10]):
            rng = f"{g[0]}-{g[-1]}" if len(g) > 1 else str(g[0])
            print(f"  Group {i+1}: pages {rng} ({len(g)} pages)")
        if len(groups) > 10:
            print(f"  ... and {len(groups)-10} more groups")

    elif args.command == 'convert':
        page_range = _parse_pages(args.pages) if args.pages else None
        converter = PdfToMarkdown(
            ocr_dpi=args.ocr_dpi,
            use_ocr=not args.no_ocr,
            use_docling_tables=args.docling_tables,
        )
        result = converter.convert(args.pdf, page_range=page_range)
        result.save(args.output, include_page_markers=not args.no_page_markers)
        print(result.summary())


if __name__ == '__main__':
    main()
