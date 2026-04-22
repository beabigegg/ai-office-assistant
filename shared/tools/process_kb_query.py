#!/usr/bin/env python3
"""Process Analysis Knowledge Base Query Tool

統一查詢 process_analysis.db 的工具，封裝所有表的 schema 知識，
避免每次查詢時猜測欄位名稱導致錯誤。

用法:
    python shared/tools/process_kb_query.py <command> [options]

Commands:
    search   --keyword <kw> [--station <id>] [--tables <t1,t2,...>]
             全文搜索指定關鍵字，跨多表返回結果

    schema   [--table <name>]
             顯示表結構（不指定則顯示全部）

    stats    [--station <id>]
             統計各表筆數

    fmea     --keyword <kw> [--station <id>]
             搜索 FMEA 失效模式/原因/預防/偵測

    cp       --keyword <kw> [--station <id>]
             搜索 CP 管制項

    oi       --keyword <kw> [--station <id>]
             搜索 OI 段落

    oi-ctrl  --keyword <kw> [--station <id>]
             搜索 OI 管制項目

    pa       --keyword <kw> [--category <cat>]
             搜索 PA 參數

    kg       --keyword <kw> [--station <id>] [--entity-type <type>]
             搜索 Knowledge Graph entities + relations

    qa       --keyword <kw>
             搜索歷史問卷回覆

Output: UTF-8 text to stdout, structured for AI consumption.
"""

import argparse
import json
import os
import sqlite3
import sys

# Force UTF-8 output (Windows compatibility)
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', buffering=1)

DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..',
                       'projects', 'process-analysis', 'workspace', 'db', 'process_analysis.db')

# ── Schema Reference (embedded so we never guess) ─────────────────────────

TABLE_COLUMNS = {
    'stations': ['station_id', 'station_name_zh', 'station_name_en', 'process_type',
                 'applicable_packages', 'equipment', 'notes'],
    'fmea_items': ['fmea_id', 'station_id', 'doc_number', 'doc_rev',
                   'process_step_zh', 'process_step_en', 'work_element_zh', 'work_element_en',
                   'four_m_type', 'function_zh', 'function_en',
                   'failure_effect_zh', 'failure_effect_en', 'severity',
                   'failure_mode_zh', 'failure_mode_en',
                   'failure_cause_zh', 'failure_cause_en',
                   'prevention_control_zh', 'prevention_control_en', 'occurrence',
                   'detection_control_zh', 'detection_control_en', 'detection',
                   'action_priority', 'source_page'],
    'cp_items': ['cp_id', 'station_id', 'doc_number', 'doc_rev', 'cp_type', 'item_no',
                 'process_name_zh', 'process_name_en', 'machine',
                 'char_product_zh', 'char_product_en',
                 'char_process_zh', 'char_process_en',
                 'special_char_class', 'spec_tolerance', 'measurement_tool',
                 'sample_size', 'sample_freq', 'control_method',
                 'reaction_plan', 'ref_oi_section', 'source_page'],
    'oi_paragraphs': ['para_id', 'station_id', 'doc_number', 'page_num',
                      'section', 'content'],  # embedding excluded
    'oi_control_items': ['oi_ctrl_id', 'station_id', 'doc_number', 'doc_rev',
                         'item_no', 'item_name_zh', 'item_name_en',
                         'checker', 'measurement_tool', 'check_frequency',
                         'sample_size', 'record_form', 'check_criterion',
                         'criterion_ref', 'source_page'],
    'oi_specs': ['spec_id', 'station_id', 'doc_number', 'spec_category',
                 'spec_key', 'spec_value', 'spec_unit', 'condition',
                 'source_section', 'source_page'],
    'oi_materials': ['material_id', 'station_id', 'doc_number', 'part_number',
                     'description', 'material_type'],
    'pa_documents': ['pa_doc_id', 'station_type', 'machine_model', 'process_type',
                     'doc_rev', 'total_pages', 'notes'],
    'pa_parameters': ['param_id', 'pa_doc_id', 'category', 'subcategory', 'parameter',
                      'condition_lf_material', 'condition_back_metal', 'condition_die_size',
                      'condition_wire_type', 'condition_wire_dia', 'condition_package',
                      'condition_grade', 'condition_other',
                      'value_text', 'value_min', 'value_max', 'value_nominal',
                      'value_tolerance', 'unit', 'part_number', 'usage_life',
                      'source_page', 'notes'],
    'kg_entities': ['entity_id', 'station_id', 'entity_type', 'name',
                    'name_normalized', 'attributes'],
    'kg_relations': ['relation_id', 'station_id', 'source_entity_id',
                     'target_entity_id', 'relation_type', 'description'],
    'kg_entity_sources': ['id', 'entity_id', 'source_type', 'source_id', 'station_id'],
    'qa_pairs': ['qa_id', 'customer', 'source_file', 'station', 'topic',
                 'question_text', 'response_text', 'response_strategy',
                 'doc_citations', 'confidence'],
    'complaint_cases': ['id', 'case_id', 'case_number', 'year', 'month',
                        'customer', 'product', 'failure_mode', 'failure_mode_raw',
                        'engineer', 'folder_name'],
    'complaint_8d_texts': ['id', 'case_id', 'customer', 'product', 'failure_mode',
                           'doc_type', 'doc_name', 'full_text', 'text_length',
                           'd1_team', 'd2_problem_description', 'd3_containment',
                           'd4_root_cause', 'd5_corrective_action'],
}

# ── Helpers ────────────────────────────────────────────────────────────────

def get_conn():
    path = os.path.abspath(DB_PATH)
    if not os.path.exists(path):
        print(f"ERROR: DB not found at {path}", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def like_clauses(columns, keywords):
    """Build OR-connected LIKE clauses for multiple columns × keywords."""
    clauses = []
    params = []
    for col in columns:
        for kw in keywords:
            clauses.append(f"{col} LIKE ?")
            params.append(f"%{kw}%")
    return " OR ".join(clauses), params


def station_filter(station_id):
    if station_id:
        return "AND station_id = ?", [station_id]
    return "", []


def print_rows(rows, max_per_table=50):
    """Print rows as structured text."""
    for i, r in enumerate(rows):
        if i >= max_per_table:
            print(f"  ... ({len(rows) - max_per_table} more rows omitted)")
            break
        d = {k: r[k] for k in r.keys() if r[k] is not None and k != 'embedding'}
        # Truncate long text fields
        for k, v in d.items():
            if isinstance(v, str) and len(v) > 300:
                d[k] = v[:300] + "..."
        print(f"  {json.dumps(d, ensure_ascii=False)}")


# ── Commands ───────────────────────────────────────────────────────────────

def cmd_schema(args):
    """Show table schema."""
    if args.table:
        tables = [args.table]
    else:
        tables = sorted(TABLE_COLUMNS.keys())

    conn = get_conn()
    for t in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"=== {t} ({count} rows) ===")
        if t in TABLE_COLUMNS:
            for col in TABLE_COLUMNS[t]:
                print(f"  {col}")
        print()
    conn.close()


def cmd_stats(args):
    """Show row counts, optionally filtered by station."""
    conn = get_conn()
    station_tables = ['fmea_items', 'cp_items', 'oi_paragraphs', 'oi_control_items',
                      'oi_specs', 'oi_materials', 'kg_entities', 'kg_relations']

    if args.station:
        print(f"=== Station {args.station} ===")
        for t in station_tables:
            count = conn.execute(f"SELECT COUNT(*) FROM {t} WHERE station_id = ?",
                                 [args.station]).fetchone()[0]
            print(f"  {t:25s} {count:>6d}")
    else:
        # All tables
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence' ORDER BY name"
        ).fetchall()]
        for t in tables:
            count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"  {t:25s} {count:>6d}")
    conn.close()


def cmd_fmea(args):
    """Search FMEA items."""
    conn = get_conn()
    keywords = args.keyword
    search_cols = ['failure_mode_zh', 'failure_mode_en',
                   'failure_cause_zh', 'failure_cause_en',
                   'prevention_control_zh', 'prevention_control_en',
                   'detection_control_zh', 'detection_control_en',
                   'process_step_zh', 'process_step_en',
                   'failure_effect_zh', 'failure_effect_en']
    where, params = like_clauses(search_cols, keywords)
    sf, sp = station_filter(args.station)

    sql = f"""SELECT station_id, doc_number, process_step_zh, process_step_en,
              failure_mode_zh, failure_mode_en, failure_cause_zh, failure_cause_en,
              prevention_control_zh, prevention_control_en,
              detection_control_zh, detection_control_en,
              severity, occurrence, detection, action_priority
       FROM fmea_items WHERE ({where}) {sf}
       ORDER BY station_id, fmea_id"""
    rows = conn.execute(sql, params + sp).fetchall()
    print(f"=== FMEA Results: {len(rows)} rows ===")
    print_rows(rows)
    conn.close()


def cmd_cp(args):
    """Search CP items."""
    conn = get_conn()
    keywords = args.keyword
    search_cols = ['char_process_zh', 'char_process_en',
                   'char_product_zh', 'char_product_en',
                   'spec_tolerance', 'control_method', 'reaction_plan',
                   'process_name_zh', 'process_name_en', 'measurement_tool']
    where, params = like_clauses(search_cols, keywords)
    sf, sp = station_filter(args.station)

    sql = f"""SELECT station_id, doc_number, cp_type, item_no,
              process_name_zh, process_name_en,
              char_process_zh, char_process_en,
              special_char_class, spec_tolerance, measurement_tool,
              sample_size, sample_freq, control_method, reaction_plan
       FROM cp_items WHERE ({where}) {sf}
       ORDER BY station_id, cp_id"""
    rows = conn.execute(sql, params + sp).fetchall()
    print(f"=== CP Results: {len(rows)} rows ===")
    print_rows(rows)
    conn.close()


def cmd_oi(args):
    """Search OI paragraphs."""
    conn = get_conn()
    keywords = args.keyword
    where, params = like_clauses(['content', 'section'], keywords)
    sf, sp = station_filter(args.station)

    sql = f"""SELECT para_id, station_id, doc_number, section, content
       FROM oi_paragraphs WHERE ({where}) {sf}
       ORDER BY station_id, para_id"""
    rows = conn.execute(sql, params + sp).fetchall()
    print(f"=== OI Paragraph Results: {len(rows)} rows ===")
    print_rows(rows)
    conn.close()


def cmd_oi_ctrl(args):
    """Search OI control items."""
    conn = get_conn()
    keywords = args.keyword
    search_cols = ['item_name_zh', 'item_name_en', 'check_criterion',
                   'measurement_tool', 'check_frequency', 'record_form']
    where, params = like_clauses(search_cols, keywords)
    sf, sp = station_filter(args.station)

    sql = f"""SELECT oi_ctrl_id, station_id, doc_number, item_no,
              item_name_zh, item_name_en, checker, measurement_tool,
              check_frequency, sample_size, record_form, check_criterion, criterion_ref
       FROM oi_control_items WHERE ({where}) {sf}
       ORDER BY station_id, item_no"""
    rows = conn.execute(sql, params + sp).fetchall()
    print(f"=== OI Control Items Results: {len(rows)} rows ===")
    print_rows(rows)
    conn.close()


def cmd_pa(args):
    """Search PA parameters."""
    conn = get_conn()
    keywords = args.keyword
    search_cols = ['p.category', 'p.subcategory', 'p.parameter', 'p.value_text', 'p.notes',
                   'p.condition_wire_type', 'p.condition_package']
    where, params = like_clauses(search_cols, keywords)

    cat_filter = ""
    cat_params = []
    if args.category:
        cat_filter = "AND category LIKE ?"
        cat_params = [f"%{args.category}%"]

    sql = f"""SELECT p.param_id, p.pa_doc_id, d.machine_model, d.station_type,
              p.category, p.subcategory, p.parameter,
              p.condition_wire_type, p.condition_wire_dia, p.condition_package,
              p.condition_other,
              p.value_text, p.value_min, p.value_max, p.unit, p.notes AS param_notes
       FROM pa_parameters p
       JOIN pa_documents d ON p.pa_doc_id = d.pa_doc_id
       WHERE ({where}) {cat_filter}
       ORDER BY p.pa_doc_id, p.param_id"""
    rows = conn.execute(sql, params + cat_params).fetchall()
    print(f"=== PA Parameter Results: {len(rows)} rows ===")
    print_rows(rows, max_per_table=80)
    conn.close()


def cmd_kg(args):
    """Search Knowledge Graph."""
    conn = get_conn()
    keywords = args.keyword

    # Search entities
    where_e, params_e = like_clauses(['name', 'attributes'], keywords)
    sf, sp = station_filter(args.station)

    type_filter = ""
    type_params = []
    if args.entity_type:
        type_filter = "AND entity_type = ?"
        type_params = [args.entity_type]

    sql = f"""SELECT entity_id, station_id, entity_type, name, attributes
       FROM kg_entities WHERE ({where_e}) {sf} {type_filter}
       ORDER BY station_id, entity_type
       LIMIT 50"""
    rows = conn.execute(sql, params_e + sp + type_params).fetchall()
    print(f"=== KG Entities: {len(rows)} rows ===")
    print_rows(rows)

    # Search relations involving matched entities
    if rows:
        entity_ids = [r['entity_id'] for r in rows]
        placeholders = ','.join('?' * len(entity_ids))
        sf2, sp2 = station_filter(args.station)
        sql_r = f"""SELECT e1.name as src, r.relation_type, e2.name as tgt,
                    r.description, r.station_id
             FROM kg_relations r
             JOIN kg_entities e1 ON r.source_entity_id = e1.entity_id AND r.station_id = e1.station_id
             JOIN kg_entities e2 ON r.target_entity_id = e2.entity_id AND r.station_id = e2.station_id
             WHERE (r.source_entity_id IN ({placeholders}) OR r.target_entity_id IN ({placeholders})) {sf2}
             LIMIT 50"""
        rows_r = conn.execute(sql_r, entity_ids + entity_ids + sp2).fetchall()
        print(f"\n=== KG Relations: {len(rows_r)} rows ===")
        print_rows(rows_r)

    conn.close()


def cmd_qa(args):
    """Search historical QA pairs."""
    conn = get_conn()
    keywords = args.keyword
    search_cols = ['question_text', 'response_text', 'topic', 'station']
    where, params = like_clauses(search_cols, keywords)

    sql = f"""SELECT qa_id, customer, station, topic, question_text, response_text,
              response_strategy, doc_citations, confidence
       FROM qa_pairs WHERE ({where})
       ORDER BY qa_id"""
    rows = conn.execute(sql, params).fetchall()
    print(f"=== QA Pairs Results: {len(rows)} rows ===")
    print_rows(rows)
    conn.close()


def cmd_search(args):
    """Cross-table keyword search."""
    keywords = args.keyword
    tables_to_search = args.tables.split(',') if args.tables else [
        'fmea_items', 'cp_items', 'oi_paragraphs', 'oi_control_items', 'pa_parameters', 'kg_entities'
    ]

    # Define searchable columns per table
    search_map = {
        'fmea_items': ['failure_mode_zh', 'failure_mode_en', 'failure_cause_zh', 'failure_cause_en',
                       'prevention_control_zh', 'prevention_control_en',
                       'detection_control_zh', 'detection_control_en'],
        'cp_items': ['char_process_zh', 'char_process_en', 'spec_tolerance',
                     'control_method', 'reaction_plan'],
        'oi_paragraphs': ['content', 'section'],
        'oi_control_items': ['item_name_zh', 'item_name_en', 'check_criterion',
                             'measurement_tool'],
        'pa_parameters': ['category', 'parameter', 'value_text'],
        'kg_entities': ['name', 'attributes'],
        'qa_pairs': ['question_text', 'response_text', 'topic'],
    }

    conn = get_conn()
    sf, sp = station_filter(args.station)

    for table in tables_to_search:
        if table not in search_map:
            print(f"SKIP: {table} (no search config)")
            continue

        cols = search_map[table]
        where, params = like_clauses(cols, keywords)

        # Select meaningful columns (skip blobs)
        select_cols = [c for c in TABLE_COLUMNS.get(table, []) if c != 'embedding']
        select_str = ', '.join(select_cols[:15])  # Limit columns for readability

        has_station = 'station_id' in TABLE_COLUMNS.get(table, [])
        sf_use = sf if has_station else ""
        sp_use = sp if has_station else []

        sql = f"SELECT {select_str} FROM {table} WHERE ({where}) {sf_use} LIMIT 30"
        rows = conn.execute(sql, params + sp_use).fetchall()

        if rows:
            print(f"\n=== {table}: {len(rows)} matches ===")
            print_rows(rows, max_per_table=30)

    conn.close()


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Process Analysis KB Query Tool')
    sub = parser.add_subparsers(dest='command', required=True)

    # schema
    p = sub.add_parser('schema', help='Show table schema')
    p.add_argument('--table', '-t', help='Specific table name')

    # stats
    p = sub.add_parser('stats', help='Show row counts')
    p.add_argument('--station', '-s', help='Filter by station_id')

    # fmea
    p = sub.add_parser('fmea', help='Search FMEA items')
    p.add_argument('--keyword', '-k', nargs='+', required=True, help='Keywords to search')
    p.add_argument('--station', '-s', help='Filter by station_id')

    # cp
    p = sub.add_parser('cp', help='Search CP items')
    p.add_argument('--keyword', '-k', nargs='+', required=True)
    p.add_argument('--station', '-s')

    # oi
    p = sub.add_parser('oi', help='Search OI paragraphs')
    p.add_argument('--keyword', '-k', nargs='+', required=True)
    p.add_argument('--station', '-s')

    # oi-ctrl
    p = sub.add_parser('oi-ctrl', help='Search OI control items')
    p.add_argument('--keyword', '-k', nargs='+', required=True)
    p.add_argument('--station', '-s')

    # pa
    p = sub.add_parser('pa', help='Search PA parameters')
    p.add_argument('--keyword', '-k', nargs='+', required=True)
    p.add_argument('--category', '-c', help='Filter by category')

    # kg
    p = sub.add_parser('kg', help='Search Knowledge Graph')
    p.add_argument('--keyword', '-k', nargs='+', required=True)
    p.add_argument('--station', '-s')
    p.add_argument('--entity-type', '-e', help='Filter by entity_type')

    # qa
    p = sub.add_parser('qa', help='Search QA pairs')
    p.add_argument('--keyword', '-k', nargs='+', required=True)

    # search (cross-table)
    p = sub.add_parser('search', help='Cross-table keyword search')
    p.add_argument('--keyword', '-k', nargs='+', required=True)
    p.add_argument('--station', '-s')
    p.add_argument('--tables', help='Comma-separated table list')

    args = parser.parse_args()

    cmd_map = {
        'schema': cmd_schema,
        'stats': cmd_stats,
        'fmea': cmd_fmea,
        'cp': cmd_cp,
        'oi': cmd_oi,
        'oi-ctrl': cmd_oi_ctrl,
        'pa': cmd_pa,
        'kg': cmd_kg,
        'qa': cmd_qa,
        'search': cmd_search,
    }

    cmd_map[args.command](args)


if __name__ == '__main__':
    main()
