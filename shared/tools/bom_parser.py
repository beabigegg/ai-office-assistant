# -*- coding: utf-8 -*-
"""
shared/tools/bom_parser.py — Tier 1 BOM Parsing Utilities
==========================================================
Cross-project shared functions for parsing std_bom data.

SOT-LD Tier: 1 (shared/tools, cross-project)
Consumes: std_bom table in bom.db
Produces: structured material info (die dimensions, compound code, ...)
Used by:  ecr_bom_utils.py, build_bom_material_detail.py, build_unified_families.py

Rules:
  - All functions are stateless and reentrant (no global state mutations)
  - No business logic (no FPKC, no ECR/ECN domain concepts)
  - Only raw parsing: desc → value, dual-layer query wrapping
  - See TOOL_LINEAGE.md for dependency graph

Lineage:
  std_bom (intake_bom.py) → bom_parser.py → ecr_bom_utils.py → report scripts
"""

import re
import math
import sqlite3

# ─── Regex patterns ───────────────────────────────────────────────────────────

# WAF desc: ".../W/*Lmil/..." e.g. "43.3/*31.1mil"
_DESC_WL_RE = re.compile(r'/(\d+\.?\d*)/\*(\d+\.?\d*)\s*mil', re.IGNORECASE)
# WAF desc single mil: "/*10mil/" or "/10mil/"
_DESC_SINGLE_MIL_RE = re.compile(r'/\*?(\d+\.?\d+)\s*mil/', re.IGNORECASE)
# die_size_raw W×L: "12.5*22" or "210x210"
_RAW_WL_RE = re.compile(r'^(\d+\.?\d*)\s*[x×X*]\s*(\d+\.?\d*)$')
# die_size_raw single: "33.5"
_RAW_SINGLE_RE = re.compile(r'^(\d+\.?\d*)$')
# thickness: "178um" or "178"
_THICKNESS_RE = re.compile(r'(\d+\.?\d*)')


# ─── Public helpers ────────────────────────────────────────────────────────────

def safe_float(val):
    """Convert val to float, return None on failure."""
    if val is None:
        return None
    try:
        return float(str(val).strip())
    except (ValueError, TypeError):
        return None


def parse_die_info(desc, die_size_raw=None, thickness=None):
    """Parse die dimensions from WAF desc and/or die_size_raw field.

    Returns (width_mil, length_mil, diagonal_mil, thickness_um):
      - width_mil: W dimension (larger or only dimension)
      - length_mil: L dimension (may equal W for square die)
      - diagonal_mil: sqrt(W²+L²)
      - thickness_um: die thickness in µm (float or None)

    Fallback order:
      1. desc W/*Lmil pattern  (e.g. "43.3/*31.1mil")
      2. die_size_raw W×L      (e.g. "12.5*22")
      3. die_size_raw single   (square die assumed)
      4. desc single mil       (square die assumed)

    Note: R8 (bom-rules SKILL) — square assumption (W×sqrt(2)) is WRONG for
    rectangular dies. Always prefer W/*Lmil from desc when available.
    """
    w, l = None, None

    # 1. desc W/*Lmil (most reliable)
    if desc:
        m = _DESC_WL_RE.search(desc)
        if m:
            w, l = float(m.group(1)), float(m.group(2))

    # 2. die_size_raw W×L
    if w is None and die_size_raw:
        m = _RAW_WL_RE.match(str(die_size_raw).strip())
        if m:
            w, l = float(m.group(1)), float(m.group(2))

    # 3. die_size_raw single value → square
    if w is None and die_size_raw:
        m = _RAW_SINGLE_RE.match(str(die_size_raw).strip())
        if m:
            w = l = float(m.group(1))

    # 4. desc single mil → square
    if w is None and desc:
        m = _DESC_SINGLE_MIL_RE.search(desc)
        if m:
            w = l = float(m.group(1))

    if w is None:
        return None, None, None, _parse_thickness(thickness)

    l = l if l is not None else w
    diag = round(math.sqrt(w ** 2 + l ** 2), 4)
    return round(w, 4), round(l, 4), diag, _parse_thickness(thickness)


def parse_die_diagonal(desc, die_size_raw_fallback=None):
    """Convenience wrapper: returns (die_size_mil, die_diagonal_mil).

    die_size_mil = W (width dimension).
    die_diagonal_mil = sqrt(W²+L²).

    Compatible with the interface used in build_bom_material_detail.py.
    """
    w, l, diag, _ = parse_die_info(desc, die_size_raw_fallback)
    return w, diag


def parse_compound_code(desc):
    """Extract compound code from COM item desc.

    Recognises: 500C, G600, G660, G590, G630, 100H, 130P, 9240, EL2K, A631.
    Returns 4-char code string or None.
    """
    if not desc:
        return None
    d = desc.upper()
    # Order: longer/more specific first to avoid partial false-matches
    PATTERNS = [
        ('EL2K', ('EL2K', 'ELL-2K')),
        ('500C', ('500C',)),
        ('G600', ('G600',)),
        ('G660', ('G660', '660B')),
        ('G590', ('G590',)),
        ('G630', ('G630', 'A631')),
        ('G631', ('G631',)),
        ('100H', ('100HF', '100H')),
        ('130P', ('130PJ', '130P')),
        ('9240', ('9240',)),
    ]
    for code, needles in PATTERNS:
        for needle in needles:
            if needle in d:
                return code
    return None


def parse_thickness(thickness_raw):
    """Parse thickness field (e.g. '178um', '178', '230 um') → float µm or None."""
    return _parse_thickness(thickness_raw)


def _parse_thickness(val):
    if not val:
        return None
    m = _THICKNESS_RE.search(str(val))
    return float(m.group(1)) if m else None


# ─── Dual-layer query helpers ──────────────────────────────────────────────────
# R7 (bom-rules SKILL): std_bom has TWO entry points for raw materials.
# Type A: sub_com_item_no LIKE 'WAF/WIR/LEF/COM%'  (_parser_used = wafer/wire/lef/glue)
# Type B: _parser_used = 'com_wafer/com_wire/com_leadframe/com_glue'  (no sub_com)
# ALWAYS query both types — omitting Type B silently misses ~4,500 parts.

def query_waf_rows(conn, ass_item_no, bop=None):
    """Query WAF (wafer) rows from std_bom, dual-layer.

    Returns list of sqlite3.Row with keys:
      item_no, desc, die_size_raw, thickness, back_metal, bop, _parser_used
    """
    return _query_material_rows(
        conn, ass_item_no, bop,
        sub_prefix='WAF%',
        type_b_parser='com_wafer',
    )


def query_wir_rows(conn, ass_item_no, bop=None):
    """Query WIR (wire) rows from std_bom, dual-layer."""
    return _query_material_rows(
        conn, ass_item_no, bop,
        sub_prefix='WIR%',
        type_b_parser='com_wire',
    )


def query_lef_rows(conn, ass_item_no, bop=None):
    """Query LEF (leadframe) rows from std_bom, dual-layer."""
    return _query_material_rows(
        conn, ass_item_no, bop,
        sub_prefix='LEF%',
        type_b_parser='com_leadframe',
    )


def query_com_rows(conn, ass_item_no, bop=None):
    """Query COM (compound/glue) rows from std_bom, dual-layer."""
    return _query_material_rows(
        conn, ass_item_no, bop,
        sub_prefix='COM%',
        type_b_parser='com_glue',
    )


def query_glue_rows(conn, ass_item_no, bop=None):
    """Query molding compound rows via glue_type='成型膠' (simpler path for compound only)."""
    params = [ass_item_no]
    bop_clause = ''
    if bop:
        bop_clause = 'AND bop = ?'
        params.append(bop)
    sql = f"""
        SELECT sub_com_item_no AS item_no,
               sub_com_item_desc AS desc,
               bop,
               _parser_used
        FROM std_bom
        WHERE ass_item_no = ? {bop_clause}
          AND glue_type = '成型膠'
    """
    rows = conn.execute(sql, params).fetchall()
    # Ensure dict-like access even if not using row_factory
    return rows


def _query_material_rows(conn, ass_item_no, bop, sub_prefix, type_b_parser):
    """Internal: dual-layer query for one material type.

    Type A: sub_com_item_no LIKE prefix
    Type B: _parser_used = type_b_parser (com_item_no is the material)
    """
    params_a = [ass_item_no, sub_prefix]
    params_b = [ass_item_no, type_b_parser]
    bop_clause = ''
    if bop:
        bop_clause = 'AND bop = ?'
        params_a.insert(1, bop)  # after ass_item_no
        params_b.insert(1, bop)

    # Reorder: ass_item_no first, then bop (if any), then prefix/parser
    params_a = [ass_item_no] + ([bop] if bop else []) + [sub_prefix]
    params_b = [ass_item_no] + ([bop] if bop else []) + [type_b_parser]

    sql_a = f"""
        SELECT sub_com_item_no AS item_no,
               COALESCE(sub_com_item_desc, com_item_desc) AS desc,
               die_size_raw, thickness, metal AS back_metal,
               bop, _parser_used, sub_com_qty AS qty
        FROM std_bom
        WHERE ass_item_no = ? {bop_clause}
          AND sub_com_item_no LIKE ?
    """
    sql_b = f"""
        SELECT com_item_no AS item_no,
               com_item_desc AS desc,
               die_size_raw, thickness, metal AS back_metal,
               bop, _parser_used, sub_com_qty AS qty
        FROM std_bom
        WHERE ass_item_no = ? {bop_clause}
          AND _parser_used = ?
    """
    rows_a = conn.execute(sql_a, params_a).fetchall()
    rows_b = conn.execute(sql_b, params_b).fetchall()
    return list(rows_a) + list(rows_b)
