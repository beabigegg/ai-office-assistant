"""
MCP Excel Server — 透過 pywin32 COM 控制本機 Excel
35 個工具：活頁簿生命週期、工作表管理、儲存格讀寫、格式化、表格與篩選、圖表、工具、進階
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
mcp = FastMCP("xlsx", instructions="Excel COM automation server")

# ---------------------------------------------------------------------------
# 全域狀態
# ---------------------------------------------------------------------------
_state = {
    "app": None,
    "wb": None,   # Workbook COM object
    "path": None,
}

# ---------------------------------------------------------------------------
# 輔助函式
# ---------------------------------------------------------------------------

def _ensure_com():
    """確保 COM 已初始化（每次 tool call 開頭呼叫）。"""
    pythoncom.CoInitialize()


def _get_app():
    """取得或建立 Excel Application 實例。Visible=True, DisplayAlerts=False。"""
    _ensure_com()
    if _state["app"] is None:
        app = win32com.client.Dispatch("Excel.Application")
        app.Visible = True
        app.DisplayAlerts = False
        _state["app"] = app
    return _state["app"]


def _get_wb():
    """取得目前的 Workbook 實例。"""
    if _state["wb"] is None:
        raise RuntimeError("No workbook is open. Call create_workbook or open_workbook first.")
    return _state["wb"]


def _hex_to_rgb_int(hex_str: str) -> int:
    """'1F4E79' → Excel RGB int (BGR order for COM)。"""
    hex_str = hex_str.lstrip("#")
    r = int(hex_str[0:2], 16)
    g = int(hex_str[2:4], 16)
    b = int(hex_str[4:6], 16)
    return r + (g << 8) + (b << 16)


def _normalize_value(val):
    """將 COM 回傳值轉為 JSON 可序列化型別。"""
    if val is None:
        return None
    # pywintypes.datetime → ISO string
    import pywintypes
    if isinstance(val, pywintypes.TimeType):
        return str(val)
    # COM currency / Decimal
    if isinstance(val, float):
        return val
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        return val
    if isinstance(val, bool):
        return val
    # fallback
    return str(val)


def _com_result_to_2d(result) -> list[list]:
    """將 COM Range.Value 結果統一轉為 2D list。

    COM 回傳值可能是：
    - 單一值（scalar）→ [[val]]
    - 1D tuple（單列）→ [[v1, v2, ...]]
    - 2D tuple of tuples → 正常轉換
    """
    if result is None:
        return [[None]]
    if not isinstance(result, tuple):
        # 單一值
        return [[_normalize_value(result)]]
    # 是 tuple
    if len(result) == 0:
        return [[]]
    if isinstance(result[0], tuple):
        # 2D tuple of tuples — 正常情況
        return [[_normalize_value(c) for c in row] for row in result]
    else:
        # 1D tuple — 單列
        return [[_normalize_value(c) for c in result]]


# ---------------------------------------------------------------------------
# Excel 常數
# ---------------------------------------------------------------------------

# 水平對齊 (XlHAlign)
XL_HALIGN_MAP = {
    "left": -4131,     # xlHAlignLeft
    "center": -4108,   # xlHAlignCenter
    "right": -4152,    # xlHAlignRight
}

# 垂直對齊 (XlVAlign)
XL_VALIGN_MAP = {
    "top": -4160,      # xlVAlignTop
    "center": -4108,   # xlVAlignCenter
    "bottom": -4107,   # xlVAlignBottom
}

# 框線樣式 (XlLineStyle / XlBorderWeight)
XL_BORDER_WEIGHT_MAP = {
    "hair": 1,         # xlHairline
    "thin": 2,         # xlThin
    "medium": -4138,   # xlMedium
    "thick": 4,        # xlThick
}

# 框線索引 (XlBordersIndex)
XL_BORDER_EDGES = [7, 8, 9, 10, 11, 12]
# xlEdgeLeft=7, xlEdgeTop=8, xlEdgeBottom=9, xlEdgeRight=10,
# xlInsideVertical=11, xlInsideHorizontal=12

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

# 排序方向 (XlSortOrder)
XL_SORT_ORDER_MAP = {
    "asc": 1,               # xlAscending
    "desc": 2,              # xlDescending
}

# 紙張方向
XL_ORIENTATION_MAP = {
    "portrait": 1,          # xlPortrait
    "landscape": 2,         # xlLandscape
}

# 紙張大小
XL_PAPER_SIZE_MAP = {
    "A4": 9,                # xlPaperA4
    "letter": 1,            # xlPaperLetter
    "A3": 8,                # xlPaperA3
    "legal": 5,             # xlPaperLegal
}


# ---------------------------------------------------------------------------
# A. 活頁簿生命週期（5 個）
# ---------------------------------------------------------------------------

@mcp.tool()
def create_workbook(path: str) -> str:
    """建立新的 .xlsx 活頁簿並儲存到指定路徑。"""
    _ensure_com()
    app = _get_app()
    wb = app.Workbooks.Add()
    abs_path = os.path.abspath(path)
    dir_path = os.path.dirname(abs_path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)
    # 51 = xlOpenXMLWorkbook (.xlsx)
    wb.SaveAs(abs_path, 51)
    _state["wb"] = wb
    _state["path"] = abs_path
    return f"Workbook created and saved to {abs_path}"


@mcp.tool()
def open_workbook(path: str, read_only: bool = False) -> str:
    """開啟既有的 .xlsx 活頁簿。"""
    _ensure_com()
    app = _get_app()
    abs_path = os.path.abspath(path)
    if not os.path.exists(abs_path):
        return f"Error: File not found: {abs_path}"
    wb = app.Workbooks.Open(abs_path, ReadOnly=read_only)
    _state["wb"] = wb
    _state["path"] = abs_path
    sheet_count = wb.Worksheets.Count
    sheet_names = [wb.Worksheets(i + 1).Name for i in range(sheet_count)]
    return f"Workbook opened: {abs_path}\nSheets ({sheet_count}): {', '.join(sheet_names)}"


@mcp.tool()
def save_workbook(path: str = "") -> str:
    """儲存活頁簿。若 path 為空則原地儲存，否則另存新檔。"""
    _ensure_com()
    wb = _get_wb()
    if path:
        abs_path = os.path.abspath(path)
        dir_path = os.path.dirname(abs_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        # 51 = xlOpenXMLWorkbook (.xlsx)
        wb.SaveAs(abs_path, 51)
        _state["path"] = abs_path
        return f"Workbook saved to {abs_path}"
    else:
        wb.Save()
        return f"Workbook saved to {_state['path']}"


@mcp.tool()
def close_workbook() -> str:
    """關閉活頁簿並退出 Excel。"""
    _ensure_com()
    try:
        if _state["wb"] is not None:
            _state["wb"].Close(SaveChanges=True)
            _state["wb"] = None
    except Exception:
        _state["wb"] = None
    try:
        if _state["app"] is not None:
            _state["app"].Quit()
            _state["app"] = None
    except Exception:
        _state["app"] = None
    _state["path"] = None
    return "Workbook closed and Excel quit."


@mcp.tool()
def get_workbook_info() -> str:
    """取得活頁簿資訊：工作表清單及各表的使用範圍。"""
    _ensure_com()
    wb = _get_wb()
    sheet_count = wb.Worksheets.Count
    result = [
        f"Workbook info:",
        f"  Path: {_state['path']}",
        f"  Sheets: {sheet_count}",
    ]
    for i in range(1, sheet_count + 1):
        ws = wb.Worksheets(i)
        used = ws.UsedRange
        rows = used.Rows.Count
        cols = used.Columns.Count
        addr = used.Address
        result.append(f"  Sheet '{ws.Name}': {rows} rows x {cols} cols (UsedRange: {addr})")
    return "\n".join(result)


# ---------------------------------------------------------------------------
# B. 工作表管理（4 個）
# ---------------------------------------------------------------------------

@mcp.tool()
def add_sheet(name: str, after: str = "") -> str:
    """新增工作表。若指定 after，則插入在該工作表之後；否則加在最後。"""
    _ensure_com()
    wb = _get_wb()
    if after:
        after_ws = wb.Worksheets(after)
        new_ws = wb.Worksheets.Add(After=after_ws)
    else:
        # 加在最後一張之後
        last_ws = wb.Worksheets(wb.Worksheets.Count)
        new_ws = wb.Worksheets.Add(After=last_ws)
    new_ws.Name = name
    return f"Sheet '{name}' added."


@mcp.tool()
def rename_sheet(old_name: str, new_name: str) -> str:
    """重新命名工作表。"""
    _ensure_com()
    wb = _get_wb()
    wb.Worksheets(old_name).Name = new_name
    return f"Sheet renamed: '{old_name}' -> '{new_name}'"


@mcp.tool()
def delete_sheet(name: str) -> str:
    """刪除工作表。DisplayAlerts 已關閉，不會跳出確認對話框。"""
    _ensure_com()
    wb = _get_wb()
    wb.Worksheets(name).Delete()
    return f"Sheet '{name}' deleted."


@mcp.tool()
def get_sheet_info(sheet: str) -> str:
    """取得工作表資訊：使用範圍位址、列數、欄數。"""
    _ensure_com()
    wb = _get_wb()
    ws = wb.Worksheets(sheet)
    used = ws.UsedRange
    rows = used.Rows.Count
    cols = used.Columns.Count
    addr = used.Address
    first_row = used.Row
    first_col = used.Column
    return (
        f"Sheet '{sheet}' info:\n"
        f"  UsedRange: {addr}\n"
        f"  Rows: {rows} (starting at row {first_row})\n"
        f"  Columns: {cols} (starting at column {first_col})\n"
        f"  Dimensions: {rows} x {cols}"
    )


# ---------------------------------------------------------------------------
# C. 儲存格讀寫（5 個）
# ---------------------------------------------------------------------------

@mcp.tool()
def read_range(sheet: str, range: str) -> str:
    """讀取儲存格範圍的值，回傳 JSON 2D 陣列。最多 500 列。"""
    _ensure_com()
    wb = _get_wb()
    ws = wb.Worksheets(sheet)
    rng = ws.Range(range)
    result = rng.Value

    data = _com_result_to_2d(result)

    # 限制 500 列
    truncated = False
    if len(data) > 500:
        data = data[:500]
        truncated = True

    output = json.dumps(data, ensure_ascii=False, default=str)
    if truncated:
        output += "\n[TRUNCATED: Only first 500 rows shown]"
    return output


@mcp.tool()
def write_range(sheet: str, start_cell: str, data: list[list]) -> str:
    """批次寫入資料。data 為 2D 陣列，從 start_cell 開始填入。"""
    _ensure_com()
    wb = _get_wb()
    ws = wb.Worksheets(sheet)
    rows = len(data)
    cols = max(len(row) for row in data) if data else 0
    if rows == 0 or cols == 0:
        return "Error: data is empty."

    # 補齊每列長度
    padded = []
    for row in data:
        padded_row = list(row) + [None] * (cols - len(row))
        padded.append(tuple(padded_row))
    tuple_data = tuple(padded)

    ws.Range(start_cell).Resize(rows, cols).Value = tuple_data
    return f"Written {rows} rows x {cols} cols starting at {sheet}!{start_cell}"


@mcp.tool()
def write_cell(sheet: str, cell: str, value: str = "", formula: str = "") -> str:
    """寫入單一儲存格。若提供 formula 則設定公式，否則設定值。"""
    _ensure_com()
    wb = _get_wb()
    ws = wb.Worksheets(sheet)
    c = ws.Range(cell)
    if formula:
        c.Formula = formula
        return f"Formula set at {sheet}!{cell}: {formula}"
    else:
        c.Value = value
        return f"Value set at {sheet}!{cell}: {value}"


@mcp.tool()
def clear_range(sheet: str, range: str) -> str:
    """清除儲存格範圍（值 + 格式）。"""
    _ensure_com()
    wb = _get_wb()
    ws = wb.Worksheets(sheet)
    ws.Range(range).Clear()
    return f"Range {sheet}!{range} cleared."


@mcp.tool()
def find_replace(sheet: str, find: str, replace: str, match_case: bool = False) -> str:
    """在工作表中尋找並取代文字。"""
    _ensure_com()
    wb = _get_wb()
    ws = wb.Worksheets(sheet)
    ws.Cells.Replace(What=find, Replacement=replace, MatchCase=match_case)
    return f"Replaced '{find}' with '{replace}' in sheet '{sheet}'."


# ---------------------------------------------------------------------------
# D. 格式化（5 個）
# ---------------------------------------------------------------------------

@mcp.tool()
def format_range(
    sheet: str,
    range: str,
    font_name: str = "",
    font_size: float = 0,
    font_bold: bool = False,
    font_color: str = "",
    bg_color: str = "",
    h_align: str = "",
    v_align: str = "",
    number_format: str = "",
    wrap_text: bool = False,
) -> str:
    """格式化儲存格範圍。只套用非空/非零的參數。
    h_align: left/center/right。v_align: top/center/bottom。
    bg_color/font_color: hex 色碼如 '1F4E79'。number_format: Excel 格式字串如 '#,##0.00'。"""
    _ensure_com()
    wb = _get_wb()
    ws = wb.Worksheets(sheet)
    rng = ws.Range(range)

    if font_name:
        rng.Font.Name = font_name
    if font_size > 0:
        rng.Font.Size = font_size
    if font_bold:
        rng.Font.Bold = True
    if font_color:
        rng.Font.Color = _hex_to_rgb_int(font_color)
    if bg_color:
        rng.Interior.Color = _hex_to_rgb_int(bg_color)
    if h_align and h_align in XL_HALIGN_MAP:
        rng.HorizontalAlignment = XL_HALIGN_MAP[h_align]
    if v_align and v_align in XL_VALIGN_MAP:
        rng.VerticalAlignment = XL_VALIGN_MAP[v_align]
    if number_format:
        rng.NumberFormat = number_format
    if wrap_text:
        rng.WrapText = True

    return f"Format applied to {sheet}!{range}"


@mcp.tool()
def set_column_width(sheet: str, columns: str, width: float) -> str:
    """設定欄寬。columns 可為 'A:C' 或 'B'。"""
    _ensure_com()
    wb = _get_wb()
    ws = wb.Worksheets(sheet)
    ws.Columns(columns).ColumnWidth = width
    return f"Column width set: {sheet}!{columns} = {width}"


@mcp.tool()
def set_row_height(sheet: str, rows: str, height: float) -> str:
    """設定列高。rows 可為 '1:5' 或 '3'。"""
    _ensure_com()
    wb = _get_wb()
    ws = wb.Worksheets(sheet)
    ws.Rows(rows).RowHeight = height
    return f"Row height set: {sheet}!{rows} = {height}"


@mcp.tool()
def merge_cells(sheet: str, range: str) -> str:
    """合併儲存格。"""
    _ensure_com()
    wb = _get_wb()
    ws = wb.Worksheets(sheet)
    ws.Range(range).Merge()
    return f"Cells merged: {sheet}!{range}"


@mcp.tool()
def add_borders(sheet: str, range: str, style: str = "thin", color: str = "000000") -> str:
    """為儲存格範圍加上框線。style: hair/thin/medium/thick。color: hex 色碼。"""
    _ensure_com()
    wb = _get_wb()
    ws = wb.Worksheets(sheet)
    rng = ws.Range(range)

    weight = XL_BORDER_WEIGHT_MAP.get(style, 2)  # 預設 xlThin
    rgb_int = _hex_to_rgb_int(color)

    for edge in XL_BORDER_EDGES:
        try:
            border = rng.Borders(edge)
            border.LineStyle = 1  # xlContinuous
            border.Weight = weight
            border.Color = rgb_int
        except Exception:
            # xlInsideVertical/xlInsideHorizontal 在單一儲存格時可能失敗
            pass

    return f"Borders ({style}) applied to {sheet}!{range}"


# ---------------------------------------------------------------------------
# E. 表格與篩選（3 個）
# ---------------------------------------------------------------------------

@mcp.tool()
def create_table(sheet: str, range: str, name: str, style: str = "TableStyleMedium2") -> str:
    """建立 ListObject 表格（Excel Table）。range 需包含標題列。"""
    _ensure_com()
    wb = _get_wb()
    ws = wb.Worksheets(sheet)
    rng = ws.Range(range)
    # xlSrcRange = 1, xlYes = 1 (has headers)
    lo = ws.ListObjects.Add(1, rng, None, 1)
    lo.Name = name
    lo.TableStyle = style
    return f"Table '{name}' created at {sheet}!{range} with style '{style}'."


@mcp.tool()
def auto_filter(sheet: str, range: str, column: int, criteria: str) -> str:
    """套用自動篩選。column 為篩選的欄位編號（從 1 開始）。"""
    _ensure_com()
    wb = _get_wb()
    ws = wb.Worksheets(sheet)
    ws.Range(range).AutoFilter(Field=column, Criteria1=criteria)
    return f"AutoFilter applied: column {column}, criteria '{criteria}' on {sheet}!{range}"


@mcp.tool()
def sort_range(sheet: str, range: str, key_column: int, order: str = "asc") -> str:
    """排序範圍。key_column 為排序依據的欄位編號（從 1 開始）。order: asc/desc。"""
    _ensure_com()
    wb = _get_wb()
    ws = wb.Worksheets(sheet)
    rng = ws.Range(range)
    order_const = XL_SORT_ORDER_MAP.get(order, 1)

    # 計算 key cell：使用範圍的第一列 + key_column 欄
    key_cell = rng.Cells(1, key_column)

    # 清除舊的排序設定
    ws.Sort.SortFields.Clear()
    # 加入排序欄位
    ws.Sort.SortFields.Add(Key=key_cell, Order=order_const)
    # 設定排序範圍與參數
    ws.Sort.SetRange(rng)
    ws.Sort.Header = 1  # xlYes = 1
    ws.Sort.Apply()

    return f"Range {sheet}!{range} sorted by column {key_column} ({order})."


# ---------------------------------------------------------------------------
# F. 圖表（3 個）
# ---------------------------------------------------------------------------

@mcp.tool()
def add_chart(
    sheet: str,
    chart_type: str,
    data_range: str,
    left: float,
    top: float,
    width: float,
    height: float,
    title: str = "",
) -> str:
    """新增圖表。chart_type: column/column_stacked/bar/pie/line/doughnut/area。
    data_range: 資料來源範圍（如 'A1:D10'）。left/top/width/height 單位為 points。"""
    _ensure_com()
    wb = _get_wb()
    ws = wb.Worksheets(sheet)

    xl_chart_type = CHART_TYPE_MAP.get(chart_type, 51)

    chart_obj = ws.ChartObjects().Add(left, top, width, height)
    chart = chart_obj.Chart
    chart.SetSourceData(ws.Range(data_range))
    chart.ChartType = xl_chart_type

    if title:
        chart.HasTitle = True
        chart.ChartTitle.Text = title
    else:
        chart.HasTitle = False

    return f"Chart '{chart_type}' added on sheet '{sheet}' (data: {data_range})."


@mcp.tool()
def modify_chart(
    sheet: str,
    chart_index: int,
    title: str = "",
    has_legend: bool = True,
    chart_style: int = 0,
) -> str:
    """修改圖表屬性。chart_index 從 1 開始。"""
    _ensure_com()
    wb = _get_wb()
    ws = wb.Worksheets(sheet)
    chart_obj = ws.ChartObjects(chart_index)
    chart = chart_obj.Chart

    if title:
        chart.HasTitle = True
        chart.ChartTitle.Text = title

    chart.HasLegend = has_legend

    if chart_style > 0:
        try:
            chart.ChartStyle = chart_style
        except Exception:
            pass

    return f"Chart {chart_index} modified on sheet '{sheet}'."


@mcp.tool()
def delete_chart(sheet: str, chart_index: int) -> str:
    """刪除圖表。chart_index 從 1 開始。"""
    _ensure_com()
    wb = _get_wb()
    ws = wb.Worksheets(sheet)
    ws.ChartObjects(chart_index).Delete()
    return f"Chart {chart_index} deleted from sheet '{sheet}'."


# ---------------------------------------------------------------------------
# G. 工具（3 個）
# ---------------------------------------------------------------------------

@mcp.tool()
def insert_image(
    sheet: str,
    image_path: str,
    cell: str,
    width: float = 0,
    height: float = 0,
) -> str:
    """插入圖片到指定儲存格位置。若 width/height 為 0 則使用原始尺寸。"""
    _ensure_com()
    wb = _get_wb()
    ws = wb.Worksheets(sheet)
    abs_path = os.path.abspath(image_path)
    if not os.path.exists(abs_path):
        return f"Error: Image file not found: {abs_path}"

    target_cell = ws.Range(cell)
    cell_left = target_cell.Left
    cell_top = target_cell.Top

    # width/height: 0 表示使用原始尺寸（傳 -1 給 COM）
    w = width if width > 0 else -1
    h = height if height > 0 else -1

    ws.Shapes.AddPicture(
        abs_path,
        False,   # LinkToFile
        True,    # SaveWithDocument
        cell_left,
        cell_top,
        w,
        h,
    )
    return f"Image inserted at {sheet}!{cell}"


@mcp.tool()
def freeze_panes(sheet: str, cell: str) -> str:
    """凍結窗格。凍結在指定儲存格的上方與左方。"""
    _ensure_com()
    wb = _get_wb()
    app = _get_app()
    ws = wb.Worksheets(sheet)

    # 必須先啟動工作表
    ws.Activate()
    # 先解除既有凍結
    app.ActiveWindow.FreezePanes = False
    # 選取儲存格
    ws.Range(cell).Select()
    # 凍結
    app.ActiveWindow.FreezePanes = True

    return f"Panes frozen at {sheet}!{cell}"


@mcp.tool()
def page_setup(
    sheet: str,
    orientation: str = "portrait",
    paper_size: str = "A4",
    margins: dict = None,
    print_area: str = "",
    fit_to_page: bool = False,
) -> str:
    """頁面設定。orientation: portrait/landscape。paper_size: A4/letter/A3/legal。
    margins: dict with keys top/bottom/left/right（單位：英吋）。
    print_area: 列印範圍如 'A1:H50'。fit_to_page: 縮放至一頁。"""
    _ensure_com()
    wb = _get_wb()
    ws = wb.Worksheets(sheet)
    ps = ws.PageSetup

    if orientation in XL_ORIENTATION_MAP:
        ps.Orientation = XL_ORIENTATION_MAP[orientation]

    if paper_size in XL_PAPER_SIZE_MAP:
        ps.PaperSize = XL_PAPER_SIZE_MAP[paper_size]

    if margins:
        # 英吋轉 points（*72）
        if "top" in margins:
            ps.TopMargin = float(margins["top"]) * 72
        if "bottom" in margins:
            ps.BottomMargin = float(margins["bottom"]) * 72
        if "left" in margins:
            ps.LeftMargin = float(margins["left"]) * 72
        if "right" in margins:
            ps.RightMargin = float(margins["right"]) * 72

    if print_area:
        ps.PrintArea = print_area

    if fit_to_page:
        ps.Zoom = False
        ps.FitToPagesWide = 1
        ps.FitToPagesTall = 1

    return f"Page setup applied to sheet '{sheet}'."


# ---------------------------------------------------------------------------
# H. 進階工具（7 個）
# ---------------------------------------------------------------------------

@mcp.tool()
def auto_fit_columns(sheet: str, columns: str = "") -> str:
    """自動調整欄寬以適應內容。columns 為空時自動調整所有已用欄。columns 格式如 'A:Z' 或 'B:D'。"""
    _ensure_com()
    wb = _get_wb()
    ws = wb.Worksheets(sheet)
    if columns:
        ws.Columns(columns).AutoFit()
        return f"Columns {columns} auto-fitted on sheet '{sheet}'."
    else:
        ws.UsedRange.Columns.AutoFit()
        return f"All used columns auto-fitted on sheet '{sheet}'."


@mcp.tool()
def auto_fit_rows(sheet: str, rows: str = "") -> str:
    """自動調整列高以適應內容（特別是 wrap_text 的情況）。rows 為空時自動調整所有已用列。rows 格式如 '1:100' 或 '5:10'。"""
    _ensure_com()
    wb = _get_wb()
    ws = wb.Worksheets(sheet)
    if rows:
        ws.Rows(rows).AutoFit()
        return f"Rows {rows} auto-fitted on sheet '{sheet}'."
    else:
        ws.UsedRange.Rows.AutoFit()
        return f"All used rows auto-fitted on sheet '{sheet}'."


@mcp.tool()
def read_cell_format(sheet: str, cell: str) -> str:
    """讀取儲存格的格式資訊（字型、背景色、對齊、邊框、數字格式），回傳 JSON。"""
    _ensure_com()
    wb = _get_wb()
    ws = wb.Worksheets(sheet)
    c = ws.Range(cell)

    def _rgb_int_to_hex(rgb_int):
        """Excel BGR int → hex string."""
        try:
            val = int(rgb_int)
            r = val & 0xFF
            g = (val >> 8) & 0xFF
            b = (val >> 16) & 0xFF
            return f"{r:02X}{g:02X}{b:02X}"
        except (ValueError, TypeError):
            return None

    # 反查對齊常數
    halign_reverse = {v: k for k, v in XL_HALIGN_MAP.items()}
    valign_reverse = {v: k for k, v in XL_VALIGN_MAP.items()}

    info = {
        "font_name": str(c.Font.Name) if c.Font.Name else None,
        "font_size": float(c.Font.Size) if c.Font.Size else None,
        "font_bold": bool(c.Font.Bold) if c.Font.Bold is not None else False,
        "font_italic": bool(c.Font.Italic) if c.Font.Italic is not None else False,
        "font_color": _rgb_int_to_hex(c.Font.Color),
        "bg_color": _rgb_int_to_hex(c.Interior.Color),
        "bg_pattern": int(c.Interior.Pattern) if c.Interior.Pattern else 0,
        "h_align": halign_reverse.get(c.HorizontalAlignment, str(c.HorizontalAlignment)),
        "v_align": valign_reverse.get(c.VerticalAlignment, str(c.VerticalAlignment)),
        "wrap_text": bool(c.WrapText) if c.WrapText is not None else False,
        "number_format": str(c.NumberFormat) if c.NumberFormat else "General",
    }
    return json.dumps(info, ensure_ascii=False)


@mcp.tool()
def copy_worksheet(source_sheet: str, new_name: str, after: str = "") -> str:
    """複製工作表（含所有格式和資料）。after 為目標位置的工作表名稱，為空則複製到最後。"""
    _ensure_com()
    wb = _get_wb()
    src_ws = wb.Worksheets(source_sheet)
    if after:
        after_ws = wb.Worksheets(after)
        src_ws.Copy(After=after_ws)
    else:
        last_ws = wb.Worksheets(wb.Worksheets.Count)
        src_ws.Copy(After=last_ws)
    # 複製後新工作表自動成為 active，重命名
    new_ws = wb.ActiveSheet
    new_ws.Name = new_name
    return f"Sheet '{source_sheet}' copied as '{new_name}'."


@mcp.tool()
def hide_rows_columns(sheet: str, target: str, hidden: bool = True) -> str:
    """隱藏或顯示列/欄。target: 'A:C'（欄）或 '5:10'（列）。hidden=True 隱藏，False 顯示。"""
    _ensure_com()
    wb = _get_wb()
    ws = wb.Worksheets(sheet)
    # 判斷是欄還是列：包含字母 → 欄，純數字 → 列
    parts = target.replace(" ", "").split(":")
    is_column = any(ch.isalpha() for ch in parts[0])
    if is_column:
        ws.Columns(target).Hidden = hidden
    else:
        ws.Rows(target).Hidden = hidden
    action = "Hidden" if hidden else "Shown"
    return f"{action}: {target} on sheet '{sheet}'."


@mcp.tool()
def add_conditional_format(
    sheet: str,
    range: str,
    rule_type: str,
    operator: str = "",
    formula: str = "",
    bg_color: str = "",
    font_color: str = "",
) -> str:
    """新增條件格式。
    rule_type: cell_value / text_contains / duplicate / top_n。
    operator (cell_value 用): greater_than/less_than/between/equal。
    formula: 比較值或公式（cell_value 時為值，text_contains 時為文字）。
    bg_color/font_color: hex 色碼。"""
    _ensure_com()
    wb = _get_wb()
    ws = wb.Worksheets(sheet)
    rng = ws.Range(range)

    # xlFormatConditionType
    # 1 = xlCellValue, 2 = xlExpression
    # xlOperator: 3=xlGreater, 4=xlLess, 1=xlBetween, 3=xlEqual...
    XL_OPERATOR_MAP = {
        "greater_than": 5,  # xlGreater
        "less_than": 6,     # xlLess
        "between": 1,       # xlBetween
        "equal": 3,         # xlEqual
        "not_equal": 4,     # xlNotEqual
        "greater_equal": 7, # xlGreaterEqual
        "less_equal": 8,    # xlLessEqual
    }

    if rule_type == "cell_value":
        op = XL_OPERATOR_MAP.get(operator, 3)
        fc = rng.FormatConditions.Add(Type=1, Operator=op, Formula1=formula)
    elif rule_type == "text_contains":
        # 使用 xlExpression + SEARCH 函式
        first_cell = rng.Cells(1, 1).Address.replace("$", "")
        expr = f'=NOT(ISERROR(SEARCH("{formula}",{first_cell})))'
        fc = rng.FormatConditions.Add(Type=2, Formula1=expr)
    elif rule_type == "duplicate":
        # xlDuplicateValues = 11 (FormatConditions.AddUniqueValues)
        fc = rng.FormatConditions.AddUniqueValues()
        fc.DupeUnique = 1  # xlDuplicate
    elif rule_type == "top_n":
        # xlTop10 = 5
        n = int(formula) if formula else 10
        fc = rng.FormatConditions.AddTop10()
        fc.TopBottom = 1  # xlTop10Top
        fc.Rank = n
    else:
        return f"Error: Unknown rule_type '{rule_type}'. Use: cell_value/text_contains/duplicate/top_n."

    # 套用格式
    if bg_color:
        fc.Interior.Color = _hex_to_rgb_int(bg_color)
    if font_color:
        fc.Font.Color = _hex_to_rgb_int(font_color)

    return f"Conditional format ({rule_type}) applied to {sheet}!{range}."


@mcp.tool()
def apply_style_preset(sheet: str, range: str, preset: str, border: str = "") -> str:
    """套用預設樣式組合。preset: header/subheader/data/data_alt/confirm/warning/error/accent。
    一次套用 bg_color + font + alignment + border。border 可覆蓋預設值（如 'medium'）。"""
    _ensure_com()

    # 讀取共用樣式定義
    import sys, os
    _tools_dir = os.path.dirname(os.path.abspath(__file__))
    if _tools_dir not in sys.path:
        sys.path.insert(0, _tools_dir)
    from excel_styles import PRESETS

    if preset not in PRESETS:
        available = ", ".join(PRESETS.keys())
        return f"Error: Unknown preset '{preset}'. Available: {available}"

    style = PRESETS[preset]
    wb = _get_wb()
    ws = wb.Worksheets(sheet)
    rng = ws.Range(range)

    # 套用字型
    if "font_name" in style:
        rng.Font.Name = style["font_name"]
    if "font_size" in style:
        rng.Font.Size = style["font_size"]
    if style.get("font_bold"):
        rng.Font.Bold = True
    if "font_color" in style:
        rng.Font.Color = _hex_to_rgb_int(style["font_color"])

    # 套用背景色
    if "bg_color" in style:
        rng.Interior.Color = _hex_to_rgb_int(style["bg_color"])

    # 套用對齊
    if "h_align" in style and style["h_align"] in XL_HALIGN_MAP:
        rng.HorizontalAlignment = XL_HALIGN_MAP[style["h_align"]]
    if "v_align" in style and style["v_align"] in XL_VALIGN_MAP:
        rng.VerticalAlignment = XL_VALIGN_MAP[style["v_align"]]
    if style.get("wrap_text"):
        rng.WrapText = True

    # 套用框線
    border_style = border if border else style.get("border", "")
    if border_style:
        weight = XL_BORDER_WEIGHT_MAP.get(border_style, 2)
        for edge in XL_BORDER_EDGES:
            try:
                b = rng.Borders(edge)
                b.LineStyle = 1  # xlContinuous
                b.Weight = weight
            except Exception:
                pass

    return f"Style preset '{preset}' applied to {sheet}!{range}."


# ---------------------------------------------------------------------------
# 啟動
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    mcp.run(transport="stdio")
