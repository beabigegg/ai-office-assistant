"""
MCP Word Server — 透過 pywin32 COM 控制本機 Word
30 個工具：文件生命週期、內容寫入、內容讀取與搜尋、表格、格式化、圖片與形狀、節與頁面、工具
傳輸：stdio（Claude Code 原生支援）
"""

import os
import json
import pythoncom
import win32com.client
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# MCP Server 實例
# ---------------------------------------------------------------------------
mcp = FastMCP("docx", instructions="Word COM automation server")

# ---------------------------------------------------------------------------
# 全域狀態
# ---------------------------------------------------------------------------
_state = {
    "app": None,
    "doc": None,   # Document COM object
    "path": None,  # 目前文件的儲存路徑
}

# ---------------------------------------------------------------------------
# 輔助函式
# ---------------------------------------------------------------------------

def _ensure_com():
    """確保 COM 已初始化（每次 tool call 開頭呼叫）。"""
    pythoncom.CoInitialize()


def _get_app():
    """取得或建立 Word Application 實例。Visible=True, DisplayAlerts=0 (wdAlertsNone)。"""
    _ensure_com()
    if _state["app"] is None:
        app = win32com.client.Dispatch("Word.Application")
        app.Visible = True
        app.DisplayAlerts = 0  # wdAlertsNone
        _state["app"] = app
    return _state["app"]


def _get_doc():
    """取得目前的 Document 實例。"""
    if _state["doc"] is None:
        raise RuntimeError("No document is open. Call create_document or open_document first.")
    return _state["doc"]


def _hex_to_rgb_int(hex_str: str) -> int:
    """'1F4E79' -> Word RGB int (BGR order for COM)。"""
    hex_str = hex_str.lstrip("#")
    r = int(hex_str[0:2], 16)
    g = int(hex_str[2:4], 16)
    b = int(hex_str[4:6], 16)
    return r + (g << 8) + (b << 16)


def _inches_to_points(inches: float) -> float:
    """英吋 -> points（Word COM 使用 points）。"""
    return inches * 72.0


def _cm_to_points(cm: float) -> float:
    """公分 -> points。"""
    return cm * 28.3465


# ---------------------------------------------------------------------------
# Word COM 常數
# ---------------------------------------------------------------------------

# 水平對齊
WD_ALIGN_LEFT = 0
WD_ALIGN_CENTER = 1
WD_ALIGN_RIGHT = 2
WD_ALIGN_JUSTIFY = 3

ALIGN_MAP = {
    "left": WD_ALIGN_LEFT,
    "center": WD_ALIGN_CENTER,
    "right": WD_ALIGN_RIGHT,
    "justify": WD_ALIGN_JUSTIFY,
}

# 節開始類型
SECTION_START_MAP = {
    "new_page": 2,       # wdSectionNewPage
    "continuous": 0,     # wdSectionContinuous
    "even_page": 3,      # wdSectionEvenPage
    "odd_page": 4,       # wdSectionOddPage
}

# 紙張大小
PAPER_SIZE_MAP = {
    "A4": 7,       # wdPaperA4
    "letter": 0,   # wdPaperLetter
    "legal": 5,    # wdPaperLegal
}

# 方向
ORIENTATION_MAP = {
    "portrait": 0,    # wdOrientPortrait
    "landscape": 1,   # wdOrientLandscape
}

# 儲存格式
WD_FORMAT_DOCX = 16  # wdFormatXMLDocument
WD_FORMAT_PDF = 17   # wdFormatPDF

# 標題樣式索引（wdStyleHeading1 = -2, wdStyleHeading2 = -3, ...）
HEADING_STYLE_MAP = {
    1: -2, 2: -3, 3: -4, 4: -5, 5: -6,
    6: -7, 7: -8, 8: -9, 9: -10,
}

# 統計常數
WD_STATISTIC_WORDS = 0
WD_STATISTIC_LINES = 1
WD_STATISTIC_PAGES = 2
WD_STATISTIC_CHARACTERS = 3
WD_STATISTIC_PARAGRAPHS = 4

# 形狀類型
SHAPE_TYPE_MAP = {
    "rectangle": 1,       # msoShapeRectangle
    "rounded_rect": 5,    # msoShapeRoundedRectangle
    "oval": 9,            # msoShapeOval
    "triangle": 7,        # msoShapeIsoscelesTriangle
    "diamond": 4,         # msoShapeDiamond
}


# ---------------------------------------------------------------------------
# A. 文件生命週期（5 個）
# ---------------------------------------------------------------------------

@mcp.tool()
def create_document(path: str, template: str = "") -> str:
    """建立新 Word 文件。path: 儲存路徑（完整 Windows 路徑）。template: 範本路徑（可選）。"""
    _ensure_com()
    app = _get_app()
    abs_path = os.path.abspath(path)

    # 確保目錄存在
    dir_path = os.path.dirname(abs_path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)

    if template:
        abs_template = os.path.abspath(template)
        doc = app.Documents.Add(Template=abs_template)
    else:
        doc = app.Documents.Add()

    # 立即存檔以建立路徑
    doc.SaveAs2(abs_path, FileFormat=WD_FORMAT_DOCX)

    _state["doc"] = doc
    _state["path"] = abs_path
    return f"Document created and saved to {abs_path}."


@mcp.tool()
def open_document(path: str, read_only: bool = False) -> str:
    """開啟既有 Word 文件。回傳頁數與段落數。"""
    _ensure_com()
    app = _get_app()
    abs_path = os.path.abspath(path)
    if not os.path.exists(abs_path):
        return f"Error: File not found: {abs_path}"

    doc = app.Documents.Open(abs_path, ReadOnly=read_only)
    _state["doc"] = doc
    _state["path"] = abs_path

    page_count = doc.ComputeStatistics(WD_STATISTIC_PAGES)
    para_count = doc.Paragraphs.Count
    return f"Document opened: {abs_path}. Pages: {page_count}, Paragraphs: {para_count}."


@mcp.tool()
def save_document(path: str = "") -> str:
    """儲存文件。若提供 path 則另存新檔（.docx），否則覆寫原檔。"""
    _ensure_com()
    doc = _get_doc()
    if path:
        abs_path = os.path.abspath(path)
        dir_path = os.path.dirname(abs_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        doc.SaveAs2(abs_path, FileFormat=WD_FORMAT_DOCX)
        _state["path"] = abs_path
        return f"Document saved to {abs_path}."
    else:
        doc.Save()
        return f"Document saved to {_state['path']}."


@mcp.tool()
def close_document() -> str:
    """關閉文件並退出 Word。"""
    _ensure_com()
    try:
        if _state["doc"] is not None:
            _state["doc"].Close(SaveChanges=-1)  # wdSaveChanges = -1
            _state["doc"] = None
    except Exception:
        _state["doc"] = None
    try:
        if _state["app"] is not None:
            _state["app"].Quit()
            _state["app"] = None
    except Exception:
        _state["app"] = None
    _state["path"] = None
    return "Document closed and Word quit."


@mcp.tool()
def get_document_info() -> str:
    """取得文件資訊：頁數、段落數、節數、字數、表格數。"""
    _ensure_com()
    doc = _get_doc()
    page_count = doc.ComputeStatistics(WD_STATISTIC_PAGES)
    para_count = doc.Paragraphs.Count
    section_count = doc.Sections.Count
    word_count = doc.ComputeStatistics(WD_STATISTIC_WORDS)
    table_count = doc.Tables.Count
    result = [
        "Document info:",
        f"  Pages: {page_count}",
        f"  Paragraphs: {para_count}",
        f"  Sections: {section_count}",
        f"  Words: {word_count}",
        f"  Tables: {table_count}",
        f"  Path: {_state['path']}",
    ]
    return "\n".join(result)


# ---------------------------------------------------------------------------
# B. 內容寫入（5 個）
# ---------------------------------------------------------------------------

@mcp.tool()
def append_paragraph(
    text: str,
    style: str = "",
    font_name: str = "",
    font_size: float = 0,
    bold: bool = False,
    color: str = "",
    alignment: str = "",
    space_after: float = -1,
) -> str:
    """在文件末尾附加段落。alignment: left/center/right/justify。
    space_after: 段後間距（points），-1 表示不設定。"""
    _ensure_com()
    doc = _get_doc()

    # 在文件末尾插入新段落
    doc.Content.InsertParagraphAfter()
    para = doc.Paragraphs(doc.Paragraphs.Count)
    para.Range.Text = text

    # 套用樣式（先設樣式，再覆蓋字型避免樣式覆蓋）
    if style:
        try:
            para.Style = style
        except Exception:
            pass

    # 字型設定
    if font_name:
        para.Range.Font.Name = font_name
    if font_size > 0:
        para.Range.Font.Size = font_size
    if bold:
        para.Range.Font.Bold = True
    if color:
        para.Range.Font.Color = _hex_to_rgb_int(color)

    # 段落格式
    if alignment and alignment in ALIGN_MAP:
        para.Alignment = ALIGN_MAP[alignment]
    if space_after >= 0:
        para.Format.SpaceAfter = space_after

    idx = doc.Paragraphs.Count
    return f"Paragraph appended at index {idx}."


@mcp.tool()
def insert_paragraph(
    after_paragraph_index: int,
    text: str,
    style: str = "",
    font_name: str = "",
    font_size: float = 0,
    bold: bool = False,
    color: str = "",
    alignment: str = "",
) -> str:
    """在指定段落之後插入新段落。after_paragraph_index: 1-based。"""
    _ensure_com()
    doc = _get_doc()

    if after_paragraph_index < 1 or after_paragraph_index > doc.Paragraphs.Count:
        return f"Error: paragraph index {after_paragraph_index} out of range (1-{doc.Paragraphs.Count})."

    # 在指定段落的 Range 末尾插入段落
    target_para = doc.Paragraphs(after_paragraph_index)
    rng = target_para.Range
    rng.Collapse(0)  # wdCollapseEnd = 0
    rng.InsertParagraphAfter()

    # 取得新插入的段落（在 after_paragraph_index 之後）
    new_para = doc.Paragraphs(after_paragraph_index + 1)
    new_para.Range.Text = text

    if style:
        try:
            new_para.Style = style
        except Exception:
            pass
    if font_name:
        new_para.Range.Font.Name = font_name
    if font_size > 0:
        new_para.Range.Font.Size = font_size
    if bold:
        new_para.Range.Font.Bold = True
    if color:
        new_para.Range.Font.Color = _hex_to_rgb_int(color)
    if alignment and alignment in ALIGN_MAP:
        new_para.Alignment = ALIGN_MAP[alignment]

    return f"Paragraph inserted after index {after_paragraph_index}."


@mcp.tool()
def append_heading(text: str, level: int = 1) -> str:
    """在文件末尾附加標題。level: 1-9。"""
    _ensure_com()
    doc = _get_doc()

    if level < 1 or level > 9:
        return f"Error: heading level must be 1-9, got {level}."

    doc.Content.InsertParagraphAfter()
    para = doc.Paragraphs(doc.Paragraphs.Count)
    para.Range.Text = text

    # 使用 wdStyleHeading 常數設定樣式（跨語系相容）
    style_const = HEADING_STYLE_MAP.get(level, -2)
    para.Style = style_const

    idx = doc.Paragraphs.Count
    return f"Heading {level} appended at paragraph index {idx}."


@mcp.tool()
def append_page_break() -> str:
    """在文件末尾插入分頁符。"""
    _ensure_com()
    doc = _get_doc()

    rng = doc.Content
    rng.Collapse(0)  # wdCollapseEnd = 0
    rng.InsertBreak(7)  # wdPageBreak = 7

    return "Page break inserted."


@mcp.tool()
def write_at_bookmark(bookmark_name: str, text: str) -> str:
    """在書籤位置寫入文字。"""
    _ensure_com()
    doc = _get_doc()

    if not doc.Bookmarks.Exists(bookmark_name):
        return f"Error: Bookmark '{bookmark_name}' not found."

    doc.Bookmarks(bookmark_name).Range.Text = text
    return f"Text written at bookmark '{bookmark_name}'."


# ---------------------------------------------------------------------------
# C. 內容讀取與搜尋（4 個）
# ---------------------------------------------------------------------------

@mcp.tool()
def read_paragraphs(start: int = 1, count: int = 50) -> str:
    """讀取段落內容與樣式資訊。start: 起始段落索引（1-based）。count: 讀取數量（上限 50）。"""
    _ensure_com()
    doc = _get_doc()

    total = doc.Paragraphs.Count
    if start < 1:
        start = 1
    if count > 50:
        count = 50

    end_idx = min(start + count - 1, total)
    result = [f"Paragraphs {start}-{end_idx} of {total}:"]

    for i in range(start, end_idx + 1):
        para = doc.Paragraphs(i)
        text = para.Range.Text.rstrip("\r\n")
        preview = text[:200]
        try:
            style_name = para.Style.NameLocal
        except Exception:
            style_name = "Unknown"
        result.append(f"  [{i}] Style='{style_name}', Text='{preview}'")

    return "\n".join(result)


@mcp.tool()
def find_text(text: str, match_case: bool = False) -> str:
    """搜尋文字，回傳所有出現位置。最多回傳 50 筆。"""
    _ensure_com()
    doc = _get_doc()

    rng = doc.Content
    rng.Find.ClearFormatting()
    rng.Find.Text = text
    rng.Find.MatchCase = match_case
    rng.Find.Forward = True
    rng.Find.Wrap = 0  # wdFindStop = 0

    found_list = []
    while rng.Find.Execute() and len(found_list) < 50:
        # 取得所在段落的上下文
        context_start = max(0, rng.Start - 30)
        context_end = min(doc.Content.End, rng.End + 30)
        context_rng = doc.Range(context_start, context_end)
        context_text = context_rng.Text.replace("\r", " ").replace("\n", " ")

        found_list.append({
            "match": rng.Text,
            "start": rng.Start,
            "end": rng.End,
            "context": context_text[:100],
        })
        rng.Collapse(0)  # wdCollapseEnd = 0

    if not found_list:
        return f"No matches found for '{text}'."

    return json.dumps({"count": len(found_list), "matches": found_list}, ensure_ascii=False, indent=2)


@mcp.tool()
def find_replace(
    find: str,
    replace: str,
    match_case: bool = False,
    replace_all: bool = True,
) -> str:
    """尋找並取代文字。COM Range.Find.Execute 可完美處理跨 Run 的文字。"""
    _ensure_com()
    doc = _get_doc()

    rng = doc.Content
    rng.Find.ClearFormatting()
    rng.Find.Replacement.ClearFormatting()
    rng.Find.Text = find
    rng.Find.Replacement.Text = replace
    rng.Find.MatchCase = match_case
    rng.Find.Forward = True
    rng.Find.Wrap = 1  # wdFindContinue = 1

    # wdReplaceAll = 2, wdReplaceOne = 1
    replace_const = 2 if replace_all else 1
    result = rng.Find.Execute(Replace=replace_const)

    mode = "all occurrences" if replace_all else "first occurrence"
    if result:
        return f"Find & replace completed ({mode}): '{find}' -> '{replace}'."
    else:
        return f"No matches found for '{find}'."


@mcp.tool()
def get_bookmarks() -> str:
    """列出文件中所有書籤。"""
    _ensure_com()
    doc = _get_doc()

    count = doc.Bookmarks.Count
    if count == 0:
        return "No bookmarks found."

    result = [f"Bookmarks ({count}):"]
    for i in range(1, count + 1):
        bm = doc.Bookmarks(i)
        text_preview = bm.Range.Text[:80].replace("\r", " ").replace("\n", " ")
        result.append(f"  [{i}] Name='{bm.Name}', Text='{text_preview}'")

    return "\n".join(result)


# ---------------------------------------------------------------------------
# D. 表格（5 個）
# ---------------------------------------------------------------------------

@mcp.tool()
def add_table(
    rows: int,
    cols: int,
    headers: list[str] | None = None,
    data: list[list[str]] | None = None,
    style: str = "",
    auto_fit: bool = True,
) -> str:
    """在文件末尾新增表格。headers: 標頭列（填入第 1 列）。data: 資料列（從第 2 列開始填入）。
    style: Word 表格樣式名稱（如 'Table Grid', 'Light Shading'）。"""
    _ensure_com()
    doc = _get_doc()

    # 在末尾建立表格
    rng = doc.Content
    rng.Collapse(0)  # wdCollapseEnd
    rng.InsertParagraphAfter()
    rng.Collapse(0)

    table = doc.Tables.Add(Range=rng, NumRows=rows, NumColumns=cols)

    # 套用樣式
    if style:
        try:
            table.Style = style
        except Exception:
            pass

    # 填入標頭
    if headers:
        for c, h in enumerate(headers):
            if c < cols:
                table.Cell(1, c + 1).Range.Text = h

    # 填入資料
    if data:
        for r, row_data in enumerate(data):
            for c, val in enumerate(row_data):
                if r + 2 <= rows and c < cols:
                    table.Cell(r + 2, c + 1).Range.Text = str(val)

    # 自動調整欄寬
    if auto_fit:
        table.AutoFitBehavior(1)  # wdAutoFitContent = 1

    idx = doc.Tables.Count
    return f"Table ({rows}x{cols}) added as table index {idx}."


@mcp.tool()
def read_table(table_index: int) -> str:
    """讀取表格內容為 JSON 二維陣列。table_index: 1-based。"""
    _ensure_com()
    doc = _get_doc()

    if table_index < 1 or table_index > doc.Tables.Count:
        return f"Error: table_index {table_index} out of range (1-{doc.Tables.Count})."

    table = doc.Tables(table_index)
    row_count = table.Rows.Count
    col_count = table.Columns.Count

    result = []
    for r in range(1, row_count + 1):
        row_data = []
        for c in range(1, col_count + 1):
            try:
                cell_text = table.Cell(r, c).Range.Text
                # Word 表格儲存格文字末尾有 \r\x07，需移除
                cell_text = cell_text.rstrip("\r\x07")
            except Exception:
                cell_text = ""
            row_data.append(cell_text)
        result.append(row_data)

    return json.dumps(
        {"table_index": table_index, "rows": row_count, "cols": col_count, "data": result},
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def write_table_cell(table_index: int, row: int, col: int, text: str) -> str:
    """寫入表格儲存格。table_index/row/col 皆為 1-based。"""
    _ensure_com()
    doc = _get_doc()

    if table_index < 1 or table_index > doc.Tables.Count:
        return f"Error: table_index {table_index} out of range (1-{doc.Tables.Count})."

    table = doc.Tables(table_index)
    table.Cell(row, col).Range.Text = text
    return f"Table {table_index} cell ({row},{col}) set to '{text[:50]}'."


@mcp.tool()
def format_table_cell(
    table_index: int,
    row: int,
    col: int,
    bg_color: str = "",
    font_bold: bool = False,
    font_size: float = 0,
) -> str:
    """格式化表格儲存格。bg_color: hex 色碼（如 '1F4E79'）。"""
    _ensure_com()
    doc = _get_doc()

    if table_index < 1 or table_index > doc.Tables.Count:
        return f"Error: table_index {table_index} out of range (1-{doc.Tables.Count})."

    table = doc.Tables(table_index)
    cell = table.Cell(row, col)

    if bg_color:
        cell.Shading.BackgroundPatternColor = _hex_to_rgb_int(bg_color)
    if font_bold:
        cell.Range.Font.Bold = True
    if font_size > 0:
        cell.Range.Font.Size = font_size

    return f"Table {table_index} cell ({row},{col}) formatted."


@mcp.tool()
def merge_table_cells(
    table_index: int,
    start_row: int,
    start_col: int,
    end_row: int,
    end_col: int,
) -> str:
    """合併表格儲存格。row/col 從 1 開始。"""
    _ensure_com()
    doc = _get_doc()

    if table_index < 1 or table_index > doc.Tables.Count:
        return f"Error: table_index {table_index} out of range (1-{doc.Tables.Count})."

    table = doc.Tables(table_index)
    cell_start = table.Cell(start_row, start_col)
    cell_end = table.Cell(end_row, end_col)
    cell_start.Merge(cell_end)

    return f"Table {table_index} cells ({start_row},{start_col})-({end_row},{end_col}) merged."


# ---------------------------------------------------------------------------
# E. 格式化（3 個）
# ---------------------------------------------------------------------------

@mcp.tool()
def format_paragraph(
    paragraph_index: int,
    font_name: str = "",
    font_size: float = 0,
    bold: bool = False,
    italic: bool = False,
    color: str = "",
    alignment: str = "",
    line_spacing: float = 0,
) -> str:
    """格式化指定段落。paragraph_index: 1-based。
    alignment: left/center/right/justify。
    line_spacing: 行距倍數（如 1.0, 1.5, 2.0）。"""
    _ensure_com()
    doc = _get_doc()

    if paragraph_index < 1 or paragraph_index > doc.Paragraphs.Count:
        return f"Error: paragraph_index {paragraph_index} out of range (1-{doc.Paragraphs.Count})."

    para = doc.Paragraphs(paragraph_index)

    if font_name:
        para.Range.Font.Name = font_name
    if font_size > 0:
        para.Range.Font.Size = font_size
    if bold:
        para.Range.Font.Bold = True
    if italic:
        para.Range.Font.Italic = True
    if color:
        para.Range.Font.Color = _hex_to_rgb_int(color)
    if alignment and alignment in ALIGN_MAP:
        para.Alignment = ALIGN_MAP[alignment]
    if line_spacing > 0:
        para.Format.LineSpacingRule = 5  # wdLineSpaceMultiple = 5
        para.Format.LineSpacing = line_spacing * 12  # 12 points per line

    return f"Paragraph {paragraph_index} formatted."


@mcp.tool()
def add_style(
    name: str,
    base_style: str = "Normal",
    font_name: str = "",
    font_size: float = 0,
    bold: bool = False,
    color: str = "",
) -> str:
    """建立自訂段落樣式。"""
    _ensure_com()
    doc = _get_doc()

    # wdStyleTypeParagraph = 1
    try:
        new_style = doc.Styles.Add(Name=name, Type=1)
    except Exception as e:
        return f"Error creating style '{name}': {e}"

    try:
        new_style.BaseStyle = base_style
    except Exception:
        pass

    if font_name:
        new_style.Font.Name = font_name
    if font_size > 0:
        new_style.Font.Size = font_size
    if bold:
        new_style.Font.Bold = True
    if color:
        new_style.Font.Color = _hex_to_rgb_int(color)

    return f"Style '{name}' created (base: '{base_style}')."


@mcp.tool()
def apply_style(paragraph_index: int, style_name: str) -> str:
    """套用樣式到指定段落。paragraph_index: 1-based。"""
    _ensure_com()
    doc = _get_doc()

    if paragraph_index < 1 or paragraph_index > doc.Paragraphs.Count:
        return f"Error: paragraph_index {paragraph_index} out of range (1-{doc.Paragraphs.Count})."

    try:
        doc.Paragraphs(paragraph_index).Style = style_name
    except Exception as e:
        return f"Error applying style '{style_name}': {e}"

    return f"Style '{style_name}' applied to paragraph {paragraph_index}."


# ---------------------------------------------------------------------------
# F. 圖片與形狀（3 個）
# ---------------------------------------------------------------------------

@mcp.tool()
def insert_image(
    image_path: str,
    width: float = 0,
    height: float = 0,
    paragraph_index: int = 0,
) -> str:
    """插入圖片。paragraph_index > 0 時在該段落位置插入，否則在末尾插入。
    width/height: 英吋（0 表示使用原始尺寸）。"""
    _ensure_com()
    doc = _get_doc()
    abs_path = os.path.abspath(image_path)

    if not os.path.exists(abs_path):
        return f"Error: Image file not found: {abs_path}"

    if paragraph_index > 0:
        if paragraph_index > doc.Paragraphs.Count:
            return f"Error: paragraph_index {paragraph_index} out of range (1-{doc.Paragraphs.Count})."
        rng = doc.Paragraphs(paragraph_index).Range
    else:
        rng = doc.Content
        rng.Collapse(0)  # wdCollapseEnd

    shape = rng.InlineShapes.AddPicture(
        FileName=abs_path,
        LinkToFile=False,
        SaveWithDocument=True,
    )

    if width > 0:
        shape.Width = _inches_to_points(width)
    if height > 0:
        shape.Height = _inches_to_points(height)

    return f"Image inserted from {abs_path}."


@mcp.tool()
def insert_shape(
    shape_type: str,
    left: float,
    top: float,
    width: float,
    height: float,
    text: str = "",
    fill_color: str = "",
) -> str:
    """新增浮動形狀。shape_type: rectangle/rounded_rect/oval/triangle/diamond。
    座標單位：英吋。"""
    _ensure_com()
    doc = _get_doc()

    mso_type = SHAPE_TYPE_MAP.get(shape_type, 1)

    shape = doc.Shapes.AddShape(
        mso_type,
        _inches_to_points(left),
        _inches_to_points(top),
        _inches_to_points(width),
        _inches_to_points(height),
    )

    if text:
        shape.TextFrame.TextRange.Text = text
    if fill_color:
        shape.Fill.Solid()
        shape.Fill.ForeColor.RGB = _hex_to_rgb_int(fill_color)

    return f"Shape '{shape_type}' added at ({left}\", {top}\")."


@mcp.tool()
def add_text_box(
    left: float,
    top: float,
    width: float,
    height: float,
    text: str,
    font_size: float = 12,
) -> str:
    """新增文字方塊。座標單位：英吋。"""
    _ensure_com()
    doc = _get_doc()

    # msoTextOrientationHorizontal = 1
    shape = doc.Shapes.AddTextbox(
        1,
        _inches_to_points(left),
        _inches_to_points(top),
        _inches_to_points(width),
        _inches_to_points(height),
    )

    shape.TextFrame.TextRange.Text = text
    shape.TextFrame.TextRange.Font.Size = font_size

    return f"Text box added at ({left}\", {top}\") with {len(text)} chars."


# ---------------------------------------------------------------------------
# G. 節與頁面（3 個）
# ---------------------------------------------------------------------------

@mcp.tool()
def page_setup(
    orientation: str = "portrait",
    paper_size: str = "A4",
    margin_top: float = 1.0,
    margin_bottom: float = 1.0,
    margin_left: float = 1.25,
    margin_right: float = 1.25,
) -> str:
    """設定頁面配置。orientation: portrait/landscape。paper_size: A4/letter/legal。
    邊界單位：英吋。"""
    _ensure_com()
    doc = _get_doc()

    ps = doc.PageSetup
    ps.Orientation = ORIENTATION_MAP.get(orientation, 0)
    ps.PaperSize = PAPER_SIZE_MAP.get(paper_size, 7)
    ps.TopMargin = _inches_to_points(margin_top)
    ps.BottomMargin = _inches_to_points(margin_bottom)
    ps.LeftMargin = _inches_to_points(margin_left)
    ps.RightMargin = _inches_to_points(margin_right)

    return f"Page setup: {orientation}, {paper_size}, margins T={margin_top}\" B={margin_bottom}\" L={margin_left}\" R={margin_right}\"."


@mcp.tool()
def add_section(start_type: str = "new_page") -> str:
    """新增節。start_type: new_page/continuous/even_page/odd_page。"""
    _ensure_com()
    doc = _get_doc()

    rng = doc.Content
    rng.Collapse(0)  # wdCollapseEnd
    break_type = SECTION_START_MAP.get(start_type, 2)
    rng.InsertBreak(Type=break_type)

    count = doc.Sections.Count
    return f"Section added ({start_type}). Total sections: {count}."


@mcp.tool()
def add_header_footer(
    section: int = 1,
    header_text: str = "",
    footer_text: str = "",
    page_number: bool = False,
) -> str:
    """設定指定節的頁首/頁尾。page_number: 在頁尾加入頁碼。"""
    _ensure_com()
    doc = _get_doc()

    if section < 1 or section > doc.Sections.Count:
        return f"Error: section {section} out of range (1-{doc.Sections.Count})."

    sec = doc.Sections(section)

    if header_text:
        # wdHeaderFooterPrimary = 1
        sec.Headers(1).Range.Text = header_text
    if footer_text:
        sec.Footers(1).Range.Text = footer_text
    if page_number:
        # 在頁尾加入頁碼
        footer_rng = sec.Footers(1).Range
        footer_rng.Collapse(0)  # wdCollapseEnd
        # wdFieldPage = 33
        footer_rng.Fields.Add(Range=footer_rng, Type=33)

    parts = []
    if header_text:
        parts.append(f"header='{header_text[:30]}'")
    if footer_text:
        parts.append(f"footer='{footer_text[:30]}'")
    if page_number:
        parts.append("page_number=True")

    return f"Section {section} header/footer set: {', '.join(parts)}."


# ---------------------------------------------------------------------------
# H. 工具（2 個）
# ---------------------------------------------------------------------------

@mcp.tool()
def export_to_pdf(output_path: str) -> str:
    """將文件匯出為 PDF。"""
    _ensure_com()
    doc = _get_doc()

    abs_path = os.path.abspath(output_path)
    dir_path = os.path.dirname(abs_path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)

    doc.SaveAs2(abs_path, FileFormat=WD_FORMAT_PDF)
    return f"Exported to PDF: {abs_path}."


@mcp.tool()
def get_statistics() -> str:
    """取得文件統計資訊：字數、行數、頁數、段落數、字元數、表格數、節數。"""
    _ensure_com()
    doc = _get_doc()

    word_count = doc.ComputeStatistics(WD_STATISTIC_WORDS)
    line_count = doc.ComputeStatistics(WD_STATISTIC_LINES)
    page_count = doc.ComputeStatistics(WD_STATISTIC_PAGES)
    char_count = doc.ComputeStatistics(WD_STATISTIC_CHARACTERS)
    para_count = doc.ComputeStatistics(WD_STATISTIC_PARAGRAPHS)
    table_count = doc.Tables.Count
    section_count = doc.Sections.Count

    result = [
        "Document statistics:",
        f"  Words: {word_count}",
        f"  Lines: {line_count}",
        f"  Pages: {page_count}",
        f"  Characters: {char_count}",
        f"  Paragraphs: {para_count}",
        f"  Tables: {table_count}",
        f"  Sections: {section_count}",
    ]
    return "\n".join(result)


# ---------------------------------------------------------------------------
# 啟動
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    mcp.run(transport="stdio")
