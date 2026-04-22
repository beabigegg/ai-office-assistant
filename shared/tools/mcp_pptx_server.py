"""
MCP PowerPoint Server v2 — 透過 pywin32 COM 控制本機 PowerPoint
24 個工具：簡報生命週期、投影片操作、文字、表格、圖形、圖表、進階格式
傳輸：stdio（Claude Code 原生支援）
"""

import os
import pythoncom
import win32com.client
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# MCP Server 實例
# ---------------------------------------------------------------------------
mcp = FastMCP("pptx", instructions="PowerPoint COM automation server")

# ---------------------------------------------------------------------------
# 全域狀態
# ---------------------------------------------------------------------------
_state = {
    "app": None,
    "prs": None,  # Presentation COM object
}

# ---------------------------------------------------------------------------
# 輔助函式
# ---------------------------------------------------------------------------

def _ensure_com():
    """確保 COM 已初始化（每次 tool call 開頭呼叫）。"""
    pythoncom.CoInitialize()


def _get_app():
    """取得或建立 PowerPoint Application 實例。"""
    _ensure_com()
    if _state["app"] is None:
        app = win32com.client.Dispatch("PowerPoint.Application")
        app.Visible = True
        _state["app"] = app
    return _state["app"]


def _get_prs():
    """取得目前的 Presentation 實例。"""
    if _state["prs"] is None:
        raise RuntimeError("No presentation is open. Call create_presentation first.")
    return _state["prs"]


def _hex_to_rgb_int(hex_str: str) -> int:
    """'1F4E79' → PowerPoint RGB int (BGR order for COM)。"""
    hex_str = hex_str.lstrip("#")
    r = int(hex_str[0:2], 16)
    g = int(hex_str[2:4], 16)
    b = int(hex_str[4:6], 16)
    return r + (g << 8) + (b << 16)


def _inches_to_points(inches: float) -> float:
    """英吋 → points（PowerPoint COM 使用 points）。"""
    return inches * 72.0


# ---------------------------------------------------------------------------
# PowerPoint 常數
# ---------------------------------------------------------------------------

# 水平對齊
PP_ALIGN_LEFT = 1
PP_ALIGN_CENTER = 2
PP_ALIGN_RIGHT = 3

ALIGN_MAP = {
    "left": PP_ALIGN_LEFT,
    "center": PP_ALIGN_CENTER,
    "right": PP_ALIGN_RIGHT,
}

# 垂直對齊 (msoVerticalAnchor)
VERTICAL_ANCHOR_MAP = {
    "top": 1,      # msoAnchorTop
    "middle": 3,   # msoAnchorMiddle
    "bottom": 4,   # msoAnchorBottom
}

# 形狀類型
SHAPE_TYPE_MAP = {
    "rectangle": 1,         # msoShapeRectangle
    "rounded_rect": 5,      # msoShapeRoundedRectangle
    "oval": 9,              # msoShapeOval
    "arrow_right": 33,      # msoShapeRightArrow
    "arrow_down": 36,       # msoShapeDownArrow
    "triangle": 7,          # msoShapeIsoscelesTriangle
    "diamond": 4,           # msoShapeDiamond
    "hexagon": 10,          # msoShapeHexagon
    "chevron": 52,          # msoShapeChevron
    "pentagon": 51,         # msoShapePentagon
    "star": 92,             # msoShape5pointStar (32-point star = 92? use 12 for 5-point)
    "left_arrow": 34,       # msoShapeLeftArrow
    "up_arrow": 35,         # msoShapeUpArrow
}

# 圖表類型 (XlChartType)
CHART_TYPE_MAP = {
    "column": 51,           # xlColumnClustered
    "column_stacked": 52,   # xlColumnStacked
    "bar": 57,              # xlBarClustered
    "pie": 5,               # xlPie
    "line": 4,              # xlLine
    "doughnut": -4120,      # xlDoughnut
    "area": 1,              # xlArea
}

# 漸層方向 (MsoGradientStyle)
GRADIENT_STYLE_MAP = {
    "horizontal": 1,        # msoGradientHorizontal
    "vertical": 2,          # msoGradientVertical
    "diagonal_up": 3,       # msoGradientDiagonalUp
    "diagonal_down": 4,     # msoGradientDiagonalDown
    "from_center": 7,       # msoGradientFromCenter
}


# ---------------------------------------------------------------------------
# A. 簡報生命週期（4 個）
# ---------------------------------------------------------------------------

@mcp.tool()
def create_presentation(
    title: str,
    subtitle: str = "",
    width_inches: float = 13.333,
    height_inches: float = 7.5,
) -> str:
    """建立新簡報並加入標題投影片。"""
    _ensure_com()
    app = _get_app()
    prs = app.Presentations.Add(WithWindow=True)
    prs.PageSetup.SlideWidth = _inches_to_points(width_inches)
    prs.PageSetup.SlideHeight = _inches_to_points(height_inches)

    # 新增標題投影片（layout index 1 = Title Slide）
    layout = prs.SlideMaster.CustomLayouts(1)
    slide = prs.Slides.AddSlide(1, layout)

    # 設定標題
    if slide.Shapes.HasTitle:
        slide.Shapes.Title.TextFrame.TextRange.Text = title
    # 設定副標題（通常是 placeholder index 2）
    if subtitle:
        try:
            slide.Shapes.Placeholders(2).TextFrame.TextRange.Text = subtitle
        except Exception:
            pass

    _state["prs"] = prs
    return f"Presentation created with title slide. Size: {width_inches}x{height_inches} inches."


@mcp.tool()
def save_presentation(path: str) -> str:
    """儲存簡報為 .pptx 檔案。path 應為完整 Windows 路徑。"""
    _ensure_com()
    prs = _get_prs()
    # 確保目錄存在
    dir_path = os.path.dirname(path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)
    # ppSaveAsOpenXMLPresentation = 24
    prs.SaveAs(os.path.abspath(path), 24)
    return f"Saved to {os.path.abspath(path)}"


@mcp.tool()
def export_to_pdf(output_path: str) -> str:
    """將簡報匯出為 PDF。output_path 應為完整 Windows 路徑（.pdf）。"""
    _ensure_com()
    prs = _get_prs()
    abs_path = os.path.abspath(output_path)
    dir_path = os.path.dirname(abs_path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)
    # ppFixedFormatTypePDF = 2, ppFixedFormatIntentPrint = 2
    prs.ExportAsFixedFormat(
        abs_path,
        2,       # FixedFormatType: ppFixedFormatTypePDF
        Intent=2,
        FrameSlides=False,
        RangeType=1,  # ppPrintAll
    )
    return f"Exported to PDF: {abs_path}"


@mcp.tool()
def close_presentation() -> str:
    """關閉簡報並退出 PowerPoint。"""
    _ensure_com()
    try:
        if _state["prs"] is not None:
            _state["prs"].Close()
            _state["prs"] = None
    except Exception:
        _state["prs"] = None
    try:
        if _state["app"] is not None:
            _state["app"].Quit()
            _state["app"] = None
    except Exception:
        _state["app"] = None
    return "Presentation closed and PowerPoint quit."


@mcp.tool()
def list_slide_layouts() -> str:
    """列出目前簡報可用的投影片版面配置。"""
    _ensure_com()
    prs = _get_prs()
    layouts = prs.SlideMaster.CustomLayouts
    result = []
    for i in range(1, layouts.Count + 1):
        layout = layouts(i)
        result.append(f"  {i}: {layout.Name}")
    return "Available layouts:\n" + "\n".join(result)


# ---------------------------------------------------------------------------
# B. 投影片操作（3 個）
# ---------------------------------------------------------------------------

@mcp.tool()
def add_slide(layout_index: int = 2) -> str:
    """新增投影片。layout_index: 1=標題, 2=標題+內容, 6=空白（依主題而異）。"""
    _ensure_com()
    prs = _get_prs()
    layout = prs.SlideMaster.CustomLayouts(layout_index)
    idx = prs.Slides.Count + 1
    prs.Slides.AddSlide(idx, layout)
    return f"Slide {idx} added (layout {layout_index})."


@mcp.tool()
def duplicate_slide(slide_index: int) -> str:
    """複製指定投影片。slide_index 從 1 開始。"""
    _ensure_com()
    prs = _get_prs()
    prs.Slides(slide_index).Duplicate()
    return f"Slide {slide_index} duplicated. New slide at index {slide_index + 1}."


@mcp.tool()
def set_slide_background(slide_index: int, rgb_hex: str) -> str:
    """設定投影片背景色。rgb_hex 例: '1F4E79'。"""
    _ensure_com()
    prs = _get_prs()
    slide = prs.Slides(slide_index)
    bg = slide.Background
    fill = bg.Fill
    fill.Solid()
    fill.ForeColor.RGB = _hex_to_rgb_int(rgb_hex)
    slide.FollowMasterBackground = False
    return f"Slide {slide_index} background set to #{rgb_hex}."


# ---------------------------------------------------------------------------
# C. 文字內容（4 個：add_textbox, add_rich_textbox, add_bullet_list, set_placeholder_text）
# ---------------------------------------------------------------------------

@mcp.tool()
def add_textbox(
    slide_index: int,
    left: float,
    top: float,
    width: float,
    height: float,
    text: str,
    font_size: int = 18,
    font_color: str = "000000",
    font_bold: bool = False,
    font_name: str = "Microsoft JhengHei",
    alignment: str = "left",
    word_wrap: bool = True,
    vertical_alignment: str = "",
    margin: float = 0,
) -> str:
    """新增文字框。座標單位：英吋。vertical_alignment: top/middle/bottom。margin: 內邊距（英吋）。"""
    _ensure_com()
    prs = _get_prs()
    slide = prs.Slides(slide_index)
    # msoTextOrientationHorizontal = 1
    shape = slide.Shapes.AddTextbox(
        1,  # Orientation
        _inches_to_points(left),
        _inches_to_points(top),
        _inches_to_points(width),
        _inches_to_points(height),
    )
    tf = shape.TextFrame
    tf.WordWrap = -1 if word_wrap else 0  # -1 = True (msoTrue)

    # 垂直對齊
    if vertical_alignment and vertical_alignment in VERTICAL_ANCHOR_MAP:
        tf.VerticalAnchor = VERTICAL_ANCHOR_MAP[vertical_alignment]

    # 內邊距
    if margin > 0:
        margin_pts = _inches_to_points(margin)
        tf.MarginLeft = margin_pts
        tf.MarginRight = margin_pts
        tf.MarginTop = margin_pts
        tf.MarginBottom = margin_pts

    tr = tf.TextRange
    tr.Text = text
    tr.Font.Size = font_size
    tr.Font.Color.RGB = _hex_to_rgb_int(font_color)
    tr.Font.Bold = -1 if font_bold else 0
    tr.Font.Name = font_name
    tr.ParagraphFormat.Alignment = ALIGN_MAP.get(alignment, PP_ALIGN_LEFT)
    return f"Textbox added on slide {slide_index}."


@mcp.tool()
def add_rich_textbox(
    slide_index: int,
    left: float,
    top: float,
    width: float,
    height: float,
    runs: list[dict],
    alignment: str = "left",
    word_wrap: bool = True,
    vertical_alignment: str = "",
    margin: float = 0,
    line_spacing: float = 0,
) -> str:
    """新增混合格式文字框。runs 為 list of dict，每個 dict 包含:
    text (str, 必填), size (int, 預設14), color (str hex, 預設'000000'),
    bold (bool, 預設false), italic (bool, 預設false), name (str, 預設'Microsoft JhengHei'),
    newline (bool, 預設false — 在此 run 前插入換行)。
    座標單位：英吋。"""
    _ensure_com()
    prs = _get_prs()
    slide = prs.Slides(slide_index)

    shape = slide.Shapes.AddTextbox(
        1,
        _inches_to_points(left),
        _inches_to_points(top),
        _inches_to_points(width),
        _inches_to_points(height),
    )
    tf = shape.TextFrame
    tf.WordWrap = -1 if word_wrap else 0

    if vertical_alignment and vertical_alignment in VERTICAL_ANCHOR_MAP:
        tf.VerticalAnchor = VERTICAL_ANCHOR_MAP[vertical_alignment]

    if margin > 0:
        margin_pts = _inches_to_points(margin)
        tf.MarginLeft = margin_pts
        tf.MarginRight = margin_pts
        tf.MarginTop = margin_pts
        tf.MarginBottom = margin_pts

    # 組合全部文字
    full_text = ""
    for run in runs:
        if run.get("newline", False) and full_text:
            full_text += "\r"
        full_text += run.get("text", "")

    tr = tf.TextRange
    tr.Text = full_text
    tr.ParagraphFormat.Alignment = ALIGN_MAP.get(alignment, PP_ALIGN_LEFT)

    if line_spacing > 0:
        for i in range(1, tr.Paragraphs().Count + 1):
            tr.Paragraphs(i).ParagraphFormat.SpaceWithin = line_spacing

    # 逐 run 設定格式（COM 1-based）
    pos = 1
    for run in runs:
        if run.get("newline", False) and pos > 1:
            pos += 1  # 跳過 \r 字元
        text = run.get("text", "")
        length = len(text)
        if length == 0:
            continue
        chars = tr.Characters(pos, length)
        chars.Font.Size = run.get("size", 14)
        chars.Font.Bold = -1 if run.get("bold", False) else 0
        chars.Font.Italic = -1 if run.get("italic", False) else 0
        chars.Font.Color.RGB = _hex_to_rgb_int(run.get("color", "000000"))
        chars.Font.Name = run.get("name", "Microsoft JhengHei")
        pos += length

    return f"Rich textbox ({len(runs)} runs) added on slide {slide_index}."


@mcp.tool()
def add_bullet_list(
    slide_index: int,
    left: float,
    top: float,
    width: float,
    height: float,
    items: list[str],
    font_size: int = 16,
    font_color: str = "333333",
    font_bold: bool = False,
    bullet_type: str = "bullet",
    line_spacing: float = 1.2,
    font_name: str = "Microsoft JhengHei",
    indent_levels: list[int] | None = None,
) -> str:
    """新增條列清單。bullet_type: 'bullet'/'number'/'dash'。
    font_bold: 全部項目粗體。
    indent_levels: 每項的縮排層級 (0=一級, 1=二級, 2=三級)，長度須與 items 一致。"""
    _ensure_com()
    prs = _get_prs()
    slide = prs.Slides(slide_index)

    if bullet_type == "dash":
        formatted_items = ["- " + item for item in items]
        text = "\r".join(formatted_items)
    elif bullet_type == "number":
        formatted_items = [f"{i+1}. {item}" for i, item in enumerate(items)]
        text = "\r".join(formatted_items)
    else:
        text = "\r".join(items)

    shape = slide.Shapes.AddTextbox(
        1,
        _inches_to_points(left),
        _inches_to_points(top),
        _inches_to_points(width),
        _inches_to_points(height),
    )
    tf = shape.TextFrame
    tf.WordWrap = -1
    tr = tf.TextRange
    tr.Text = text
    tr.Font.Size = font_size
    tr.Font.Color.RGB = _hex_to_rgb_int(font_color)
    tr.Font.Name = font_name
    if font_bold:
        tr.Font.Bold = -1

    # 設定行距、項目符號、縮排
    for i in range(1, tr.Paragraphs().Count + 1):
        para = tr.Paragraphs(i)
        para.ParagraphFormat.SpaceWithin = line_spacing
        if bullet_type == "bullet":
            # ppBulletUnnumbered = 1
            para.ParagraphFormat.Bullet.Type = 1
        # 設定縮排層級
        if indent_levels and i - 1 < len(indent_levels):
            level = indent_levels[i - 1]
            para.IndentLevel = level + 1  # COM IndentLevel 從 1 開始

    return f"Bullet list ({len(items)} items) added on slide {slide_index}."


@mcp.tool()
def set_placeholder_text(
    slide_index: int,
    placeholder_index: int,
    text: str,
    font_size: int = 0,
    font_color: str = "",
    font_bold: bool = False,
) -> str:
    """設定版面佔位符文字。placeholder_index 通常 1=標題, 2=副標題/內容。"""
    _ensure_com()
    prs = _get_prs()
    slide = prs.Slides(slide_index)
    ph = slide.Shapes.Placeholders(placeholder_index)
    tr = ph.TextFrame.TextRange
    tr.Text = text
    if font_size > 0:
        tr.Font.Size = font_size
    if font_color:
        tr.Font.Color.RGB = _hex_to_rgb_int(font_color)
    tr.Font.Bold = -1 if font_bold else 0
    return f"Placeholder {placeholder_index} on slide {slide_index} set."


# ---------------------------------------------------------------------------
# D. 表格（3 個：add_table, format_table_cell, merge_table_cells）
# ---------------------------------------------------------------------------

@mcp.tool()
def add_table(
    slide_index: int,
    left: float,
    top: float,
    width: float,
    height: float,
    headers: list[str],
    rows: list[list[str]],
    header_bg_color: str = "1F4E79",
    header_font_color: str = "FFFFFF",
    font_size: int = 12,
    col_widths: list[float] | None = None,
    alt_row_color: str = "",
    cell_vertical_alignment: str = "",
) -> str:
    """新增表格。座標單位：英吋。rows 為二維陣列。
    alt_row_color: 交替行背景色 (hex)，例 'E8EEF4'。
    cell_vertical_alignment: top/middle/bottom — 所有儲存格的垂直對齊。"""
    _ensure_com()
    prs = _get_prs()
    slide = prs.Slides(slide_index)
    num_rows = len(rows) + 1  # +1 for header
    num_cols = len(headers)

    shape = slide.Shapes.AddTable(
        num_rows,
        num_cols,
        _inches_to_points(left),
        _inches_to_points(top),
        _inches_to_points(width),
        _inches_to_points(height),
    )
    table = shape.Table

    # 設定欄寬
    if col_widths and len(col_widths) == num_cols:
        for c in range(num_cols):
            table.Columns(c + 1).Width = _inches_to_points(col_widths[c])

    # 垂直對齊值
    v_anchor = VERTICAL_ANCHOR_MAP.get(cell_vertical_alignment, 0)

    # 填入 header
    for c, h in enumerate(headers):
        cell = table.Cell(1, c + 1)
        cell.Shape.TextFrame.TextRange.Text = h
        cell.Shape.TextFrame.TextRange.Font.Size = font_size
        cell.Shape.TextFrame.TextRange.Font.Bold = -1
        cell.Shape.TextFrame.TextRange.Font.Color.RGB = _hex_to_rgb_int(header_font_color)
        cell.Shape.TextFrame.TextRange.Font.Name = "Microsoft JhengHei"
        # 設定 header 背景色
        cell.Shape.Fill.Solid()
        cell.Shape.Fill.ForeColor.RGB = _hex_to_rgb_int(header_bg_color)
        if v_anchor:
            cell.Shape.TextFrame.VerticalAnchor = v_anchor

    # 填入資料列
    for r, row_data in enumerate(rows):
        for c, val in enumerate(row_data):
            cell = table.Cell(r + 2, c + 1)
            cell.Shape.TextFrame.TextRange.Text = str(val)
            cell.Shape.TextFrame.TextRange.Font.Size = font_size
            cell.Shape.TextFrame.TextRange.Font.Name = "Microsoft JhengHei"
            if v_anchor:
                cell.Shape.TextFrame.VerticalAnchor = v_anchor
        # 交替行色
        if alt_row_color and r % 2 == 1:
            for c in range(num_cols):
                cell = table.Cell(r + 2, c + 1)
                cell.Shape.Fill.Solid()
                cell.Shape.Fill.ForeColor.RGB = _hex_to_rgb_int(alt_row_color)

    return f"Table ({num_rows}x{num_cols}) added on slide {slide_index}."


@mcp.tool()
def format_table_cell(
    slide_index: int,
    table_shape_index: int,
    row: int,
    col: int,
    bg_color: str = "",
    font_color: str = "",
    font_bold: bool = False,
    font_size: int = 0,
) -> str:
    """格式化表格中單一儲存格。row/col 從 1 開始。table_shape_index 為表格在投影片中的 shape 索引。"""
    _ensure_com()
    prs = _get_prs()
    slide = prs.Slides(slide_index)
    shape = slide.Shapes(table_shape_index)
    table = shape.Table
    cell = table.Cell(row, col)
    if bg_color:
        cell.Shape.Fill.Solid()
        cell.Shape.Fill.ForeColor.RGB = _hex_to_rgb_int(bg_color)
    tr = cell.Shape.TextFrame.TextRange
    if font_color:
        tr.Font.Color.RGB = _hex_to_rgb_int(font_color)
    if font_bold:
        tr.Font.Bold = -1
    if font_size > 0:
        tr.Font.Size = font_size
    return f"Cell ({row},{col}) formatted on slide {slide_index}."


@mcp.tool()
def merge_table_cells(
    slide_index: int,
    table_shape_index: int,
    start_row: int,
    start_col: int,
    end_row: int,
    end_col: int,
) -> str:
    """合併表格儲存格。row/col 從 1 開始。將 (start_row, start_col) 到 (end_row, end_col) 的範圍合併。"""
    _ensure_com()
    prs = _get_prs()
    slide = prs.Slides(slide_index)
    shape = slide.Shapes(table_shape_index)
    table = shape.Table
    table.Cell(start_row, start_col).Merge(table.Cell(end_row, end_col))
    return f"Cells ({start_row},{start_col})-({end_row},{end_col}) merged on slide {slide_index}."


# ---------------------------------------------------------------------------
# E. 圖形與圖片（4 個：add_shape, add_image, delete_shape, modify_shape）
# ---------------------------------------------------------------------------

@mcp.tool()
def add_shape(
    slide_index: int,
    shape_type: str,
    left: float,
    top: float,
    width: float,
    height: float,
    fill_color: str = "4472C4",
    line_color: str = "",
    text: str = "",
    font_size: int = 14,
    font_color: str = "FFFFFF",
    vertical_alignment: str = "",
    rotation: float = 0,
    transparency: float = 0,
) -> str:
    """新增形狀。shape_type: rectangle/rounded_rect/oval/arrow_right/arrow_down/
    triangle/diamond/hexagon/chevron/pentagon/star/left_arrow/up_arrow。
    vertical_alignment: top/middle/bottom。rotation: 旋轉角度。transparency: 0-1 填充透明度。"""
    _ensure_com()
    prs = _get_prs()
    slide = prs.Slides(slide_index)
    mso_type = SHAPE_TYPE_MAP.get(shape_type, 1)

    shape = slide.Shapes.AddShape(
        mso_type,
        _inches_to_points(left),
        _inches_to_points(top),
        _inches_to_points(width),
        _inches_to_points(height),
    )

    if fill_color:
        shape.Fill.Solid()
        shape.Fill.ForeColor.RGB = _hex_to_rgb_int(fill_color)
        if transparency > 0:
            shape.Fill.Transparency = max(0, min(1, transparency))

    if line_color:
        shape.Line.ForeColor.RGB = _hex_to_rgb_int(line_color)
    else:
        shape.Line.Visible = False

    if rotation:
        shape.Rotation = rotation

    if text:
        shape.TextFrame.TextRange.Text = text
        shape.TextFrame.TextRange.Font.Size = font_size
        shape.TextFrame.TextRange.Font.Color.RGB = _hex_to_rgb_int(font_color)
        shape.TextFrame.TextRange.Font.Name = "Microsoft JhengHei"
        shape.TextFrame.TextRange.ParagraphFormat.Alignment = PP_ALIGN_CENTER
        shape.TextFrame.WordWrap = -1
        if vertical_alignment and vertical_alignment in VERTICAL_ANCHOR_MAP:
            shape.TextFrame.VerticalAnchor = VERTICAL_ANCHOR_MAP[vertical_alignment]

    return f"Shape '{shape_type}' added on slide {slide_index}."


@mcp.tool()
def add_image(
    slide_index: int,
    image_path: str,
    left: float,
    top: float,
    width: float = 0,
    height: float = 0,
) -> str:
    """插入圖片。若 width/height 為 0，則使用原始尺寸。"""
    _ensure_com()
    prs = _get_prs()
    slide = prs.Slides(slide_index)
    abs_path = os.path.abspath(image_path)
    if not os.path.exists(abs_path):
        return f"Error: Image file not found: {abs_path}"

    if width > 0 and height > 0:
        shape = slide.Shapes.AddPicture(
            abs_path,
            False,  # LinkToFile
            True,   # SaveWithDocument
            _inches_to_points(left),
            _inches_to_points(top),
            _inches_to_points(width),
            _inches_to_points(height),
        )
    else:
        shape = slide.Shapes.AddPicture(
            abs_path,
            False,
            True,
            _inches_to_points(left),
            _inches_to_points(top),
        )
    return f"Image added on slide {slide_index}."


@mcp.tool()
def delete_shape(
    slide_index: int,
    shape_index: int,
) -> str:
    """刪除投影片上指定的 shape。shape_index 從 1 開始（可用 get_slide_info 查詢）。"""
    _ensure_com()
    prs = _get_prs()
    slide = prs.Slides(slide_index)
    if shape_index < 1 or shape_index > slide.Shapes.Count:
        return f"Error: shape_index {shape_index} out of range (1-{slide.Shapes.Count})."
    name = slide.Shapes(shape_index).Name
    slide.Shapes(shape_index).Delete()
    return f"Shape [{shape_index}] '{name}' deleted from slide {slide_index}."


@mcp.tool()
def modify_shape(
    slide_index: int,
    shape_index: int,
    left: float = -1,
    top: float = -1,
    width: float = -1,
    height: float = -1,
    fill_color: str = "",
    text: str = "",
    font_size: int = 0,
    font_color: str = "",
    rotation: float = -1,
) -> str:
    """修改既有 shape 的屬性。只修改有提供的參數（-1 或空字串表示不修改）。
    shape_index 從 1 開始。座標單位：英吋。"""
    _ensure_com()
    prs = _get_prs()
    slide = prs.Slides(slide_index)
    if shape_index < 1 or shape_index > slide.Shapes.Count:
        return f"Error: shape_index {shape_index} out of range (1-{slide.Shapes.Count})."

    shape = slide.Shapes(shape_index)

    if left >= 0:
        shape.Left = _inches_to_points(left)
    if top >= 0:
        shape.Top = _inches_to_points(top)
    if width >= 0:
        shape.Width = _inches_to_points(width)
    if height >= 0:
        shape.Height = _inches_to_points(height)
    if fill_color:
        shape.Fill.Solid()
        shape.Fill.ForeColor.RGB = _hex_to_rgb_int(fill_color)
    if rotation >= 0:
        shape.Rotation = rotation
    if text and shape.HasTextFrame:
        shape.TextFrame.TextRange.Text = text
    if font_size > 0 and shape.HasTextFrame:
        shape.TextFrame.TextRange.Font.Size = font_size
    if font_color and shape.HasTextFrame:
        shape.TextFrame.TextRange.Font.Color.RGB = _hex_to_rgb_int(font_color)

    return f"Shape [{shape_index}] '{shape.Name}' modified on slide {slide_index}."


# ---------------------------------------------------------------------------
# F. 圖表（1 個）
# ---------------------------------------------------------------------------

@mcp.tool()
def add_chart(
    slide_index: int,
    chart_type: str,
    left: float,
    top: float,
    width: float,
    height: float,
    categories: list[str],
    series: list[dict],
    title: str = "",
    has_legend: bool = True,
    chart_style: int = -1,
) -> str:
    """新增圖表。chart_type: column/column_stacked/bar/pie/line/doughnut/area。
    categories: X 軸標籤列表，例 ['Q1','Q2','Q3','Q4']。
    series: list of dict，每個 dict 包含 name (str) 和 values (list[float])。
    例: [{"name": "Revenue", "values": [100,200,150,300]}]。
    chart_style: PowerPoint 圖表樣式編號 (-1 使用預設)。"""
    import time as _time
    _ensure_com()
    prs = _get_prs()
    slide = prs.Slides(slide_index)

    xl_chart_type = CHART_TYPE_MAP.get(chart_type, 51)
    left_pt = _inches_to_points(left)
    top_pt = _inches_to_points(top)
    width_pt = _inches_to_points(width)
    height_pt = _inches_to_points(height)

    num_categories = len(categories)
    num_series = len(series)

    # 建立圖表（AddChart — 相容所有 Office 版本）
    chart_shape = slide.Shapes.AddChart(
        xl_chart_type,
        left_pt, top_pt, width_pt, height_pt,
    )
    chart = chart_shape.Chart

    # 存取內嵌工作表並覆寫資料
    cd = chart.ChartData
    cd.Activate()
    _time.sleep(1.5)  # 充足等待時間確保工作簿完全載入

    wb = cd.Workbook
    ws = wb.Worksheets(1)

    # 先清除整個使用範圍，避免殘留預設資料
    try:
        ws.UsedRange.Clear()
    except Exception:
        pass
    _time.sleep(0.3)

    # A1 保持空格（與預設結構一致）
    ws.Cells(1, 1).Value = " "

    # 寫入 categories（A2 起）
    for i, cat in enumerate(categories):
        ws.Cells(i + 2, 1).Value = cat

    # 寫入 series（B1 起為 header，B2 起為數值）
    for s_idx, s in enumerate(series):
        col = s_idx + 2
        ws.Cells(1, col).Value = s.get("name", f"Series {s_idx + 1}")
        for i, v in enumerate(s.get("values", [])):
            ws.Cells(i + 2, col).Value = v

    _time.sleep(0.3)

    # 關閉工作簿（SaveChanges=True 觸發圖表刷新）
    wb.Close(True)
    _time.sleep(0.5)

    # 刪除多餘的 Series（預設可能有 3 個，只保留需要的數量）
    while chart.SeriesCollection().Count > num_series:
        chart.SeriesCollection(chart.SeriesCollection().Count).Delete()

    # 強制設定分類標籤（wb.Close 後圖表可能快取舊標籤）
    for s_idx in range(1, min(num_series + 1, chart.SeriesCollection().Count + 1)):
        try:
            chart.SeriesCollection(s_idx).XValues = categories
        except Exception:
            pass

    # 圖表標題
    if title:
        chart.HasTitle = True
        chart.ChartTitle.Text = title
    else:
        chart.HasTitle = False

    chart.HasLegend = has_legend

    # 套用圖表樣式
    if chart_style > 0:
        try:
            chart.ChartStyle = chart_style
        except Exception:
            pass

    return f"Chart '{chart_type}' added on slide {slide_index} ({num_categories} categories, {num_series} series)."


# ---------------------------------------------------------------------------
# G. 進階格式（5 個：add_connector, set_gradient_fill, get_slide_info, get_presentation_info, add_presenter_notes）
# ---------------------------------------------------------------------------

@mcp.tool()
def add_connector(
    slide_index: int,
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
    line_color: str = "333333",
    line_width: float = 1.5,
    arrow_end: bool = False,
    arrow_start: bool = False,
) -> str:
    """新增連接線。座標單位：英吋。arrow_start/arrow_end 控制起點/終點箭頭。"""
    _ensure_com()
    prs = _get_prs()
    slide = prs.Slides(slide_index)
    # msoConnectorStraight = 1
    connector = slide.Shapes.AddConnector(
        1,  # msoConnectorStraight
        _inches_to_points(start_x),
        _inches_to_points(start_y),
        _inches_to_points(end_x),
        _inches_to_points(end_y),
    )
    connector.Line.ForeColor.RGB = _hex_to_rgb_int(line_color)
    connector.Line.Weight = line_width
    if arrow_end:
        # msoArrowheadTriangle = 2
        connector.Line.EndArrowheadStyle = 2
    if arrow_start:
        connector.Line.BeginArrowheadStyle = 2
    return f"Connector added on slide {slide_index}."


@mcp.tool()
def set_gradient_fill(
    slide_index: int,
    target: str,
    shape_index: int = 0,
    color1: str = "1F4E79",
    color2: str = "4472C4",
    gradient_style: str = "horizontal",
    variant: int = 1,
) -> str:
    """設定漸層填充。target: 'slide' (投影片背景) 或 'shape' (指定 shape)。
    shape_index: target='shape' 時必填（從 1 開始）。
    gradient_style: horizontal/vertical/diagonal_up/diagonal_down/from_center。
    variant: 漸層變體 1-4。"""
    _ensure_com()
    prs = _get_prs()
    slide = prs.Slides(slide_index)

    style_const = GRADIENT_STYLE_MAP.get(gradient_style, 1)

    if target == "slide":
        fill = slide.Background.Fill
        slide.FollowMasterBackground = False
    elif target == "shape":
        if shape_index < 1 or shape_index > slide.Shapes.Count:
            return f"Error: shape_index {shape_index} out of range."
        fill = slide.Shapes(shape_index).Fill
    else:
        return f"Error: target must be 'slide' or 'shape', got '{target}'."

    fill.TwoColorGradient(style_const, max(1, min(4, variant)))
    fill.ForeColor.RGB = _hex_to_rgb_int(color1)
    fill.BackColor.RGB = _hex_to_rgb_int(color2)

    return f"Gradient fill ({gradient_style}) applied to {target} on slide {slide_index}."


@mcp.tool()
def get_slide_info(slide_index: int) -> str:
    """取得投影片資訊：所有 shapes 的位置/類型/文字。"""
    _ensure_com()
    prs = _get_prs()
    slide = prs.Slides(slide_index)
    result = [f"Slide {slide_index} — {slide.Shapes.Count} shapes:"]
    for i in range(1, slide.Shapes.Count + 1):
        shape = slide.Shapes(i)
        info = f"  [{i}] Type={shape.Type}, Name='{shape.Name}'"
        info += f", Pos=({shape.Left/72:.1f}\", {shape.Top/72:.1f}\")"
        info += f", Size=({shape.Width/72:.1f}\"x{shape.Height/72:.1f}\")"
        if shape.HasTextFrame:
            text = shape.TextFrame.TextRange.Text
            if text:
                preview = text[:80].replace("\r", " | ")
                info += f", Text='{preview}'"
        if shape.HasTable:
            t = shape.Table
            info += f", Table={t.Rows.Count}x{t.Columns.Count}"
        result.append(info)
    return "\n".join(result)


@mcp.tool()
def get_presentation_info() -> str:
    """取得簡報整體資訊：投影片數量、尺寸、每張投影片的 shape 數量。"""
    _ensure_com()
    prs = _get_prs()
    slide_w = prs.PageSetup.SlideWidth / 72
    slide_h = prs.PageSetup.SlideHeight / 72
    count = prs.Slides.Count
    result = [
        f"Presentation info:",
        f"  Slides: {count}",
        f"  Size: {slide_w:.2f}\" x {slide_h:.2f}\"",
    ]
    for i in range(1, count + 1):
        slide = prs.Slides(i)
        shape_count = slide.Shapes.Count
        title_text = ""
        if slide.Shapes.HasTitle:
            try:
                title_text = slide.Shapes.Title.TextFrame.TextRange.Text[:50]
            except Exception:
                pass
        line = f"  Slide {i}: {shape_count} shapes"
        if title_text:
            line += f", Title='{title_text}'"
        result.append(line)
    return "\n".join(result)


@mcp.tool()
def add_presenter_notes(
    slide_index: int,
    notes_text: str,
) -> str:
    """加入或覆寫投影片的備忘稿（Presenter Notes）。"""
    _ensure_com()
    prs = _get_prs()
    slide = prs.Slides(slide_index)
    slide.NotesPage.Shapes.Placeholders(2).TextFrame.TextRange.Text = notes_text
    return f"Presenter notes set on slide {slide_index} ({len(notes_text)} chars)."


# ---------------------------------------------------------------------------
# 啟動
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    mcp.run(transport="stdio")
