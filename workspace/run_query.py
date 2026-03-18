import sqlite3
import json

DB_PATH = r'D:\AI_test\projects\ecr-ecn\workspace\db\ecr_ecn.db'
OUT_PATH = r'D:\AI_test\projects\ecr-ecn\workspace\query_grouping_analysis.txt'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Q1
cur.execute('PRAGMA table_info(unified_tech_family_v2)')
q1 = cur.fetchall()

# Q2 schema + sample
cur.execute('PRAGMA table_info(unified_family_assignment_v2)')
q2_schema = cur.fetchall()
cur.execute('SELECT * FROM unified_family_assignment_v2 LIMIT 5')
q2_sample = cur.fetchall()

# Q3: O-0003 families - LF, DA
cur.execute("""
SELECT family_id, full_pkg_code, lf_code, da_code
FROM unified_tech_family_v2
WHERE change_ids LIKE '%O-0003%'
ORDER BY family_id
""")
q3_rows = cur.fetchall()

cur.execute("""
SELECT COUNT(DISTINCT da_code || '|' || lf_code) as cnt
FROM unified_tech_family_v2
WHERE change_ids LIKE '%O-0003%'
""")
q3_distinct = cur.fetchone()[0]

cur.execute("""
SELECT da_code, lf_code, COUNT(*) as cnt
FROM unified_tech_family_v2
WHERE change_ids LIKE '%O-0003%'
GROUP BY da_code, lf_code
ORDER BY da_code, lf_code
""")
q3_groups = cur.fetchall()

# Q4: O-0004 families - DA, Wire, Compound
cur.execute("""
SELECT family_id, full_pkg_code, da_code, wires_code, compound_code
FROM unified_tech_family_v2
WHERE change_ids LIKE '%O-0004%'
ORDER BY family_id
""")
q4_rows = cur.fetchall()

cur.execute("""
SELECT COUNT(DISTINCT da_code || '|' || wires_code || '|' || compound_code) as cnt
FROM unified_tech_family_v2
WHERE change_ids LIKE '%O-0004%'
""")
q4_distinct = cur.fetchone()[0]

cur.execute("""
SELECT da_code, wires_code, compound_code, COUNT(*) as cnt
FROM unified_tech_family_v2
WHERE change_ids LIKE '%O-0004%'
GROUP BY da_code, wires_code, compound_code
ORDER BY da_code, wires_code, compound_code
""")
q4_groups = cur.fetchall()

# Q5: O-0003 all families - full_pkg_code parsed segs
cur.execute("""
SELECT family_id, full_pkg_code, lf_code, da_code
FROM unified_tech_family_v2
WHERE change_ids LIKE '%O-0003%'
ORDER BY family_id
""")
q5_raw = cur.fetchall()

q5_rows = []
for row in q5_raw:
    fpkc = row['full_pkg_code'] or ''
    segs = fpkc.split('-')
    q5_rows.append({
        'family_id': row['family_id'],
        'full_pkg_code': fpkc,
        'lf_code': row['lf_code'],
        'da_code': row['da_code'],
        'seg2_LF': segs[1] if len(segs) > 1 else '',
        'seg3_DA': segs[2] if len(segs) > 2 else '',
    })

# Q6: O-0004 all families - full_pkg_code parsed segs
cur.execute("""
SELECT family_id, full_pkg_code, da_code, wires_code, compound_code
FROM unified_tech_family_v2
WHERE change_ids LIKE '%O-0004%'
ORDER BY family_id
""")
q6_raw = cur.fetchall()

q6_rows = []
for row in q6_raw:
    fpkc = row['full_pkg_code'] or ''
    segs = fpkc.split('-')
    q6_rows.append({
        'family_id': row['family_id'],
        'full_pkg_code': fpkc,
        'da_code': row['da_code'],
        'wires_code': row['wires_code'],
        'compound_code': row['compound_code'],
        'seg3_DA': segs[2] if len(segs) > 2 else '',
        'seg4_Wire': segs[3] if len(segs) > 3 else '',
        'seg5_Compound': segs[4] if len(segs) > 4 else '',
    })

conn.close()

# ========== Write output ==========
with open(OUT_PATH, 'w', encoding='utf-8') as f:
    f.write('=== 查詢結果：ECR/ECN Family 分組分析 ===\n')
    f.write('生成時間：2026-03-12\n')
    f.write('資料庫：projects/ecr-ecn/workspace/db/ecr_ecn.db\n\n')

    # Q1
    f.write('--- Query 1: unified_tech_family_v2 欄位清單 ---\n')
    for col in q1:
        f.write(f'  cid={col[0]}, name={col[1]}, type={col[2]}\n')
    f.write(f'共 {len(q1)} 個欄位\n\n')

    # Q2
    f.write('--- Query 2: unified_family_assignment_v2 欄位清單 + 前5筆樣本 ---\n')
    f.write('[欄位]\n')
    for col in q2_schema:
        f.write(f'  cid={col[0]}, name={col[1]}, type={col[2]}\n')
    f.write(f'共 {len(q2_schema)} 個欄位\n\n')
    f.write('[前5筆樣本]\n')
    for i, row in enumerate(q2_sample):
        f.write(f'  Row {i+1}:\n')
        for key in row.keys():
            f.write(f'    {key}: {row[key]}\n')
    f.write('\n')

    # Q3
    f.write('--- Query 3: O-0003 涉及的 family (LF, DA 分析) ---\n')
    f.write(f'family 總數: {len(q3_rows)}\n')
    f.write(f'DISTINCT (da_code, lf_code) 組合數: {q3_distinct}\n\n')
    header = f'{"family_id":<20} {"full_pkg_code":<45} {"lf_code":<12} {"da_code":<12}'
    f.write(header + '\n')
    f.write('-' * 92 + '\n')
    for row in q3_rows:
        f.write(f'{str(row["family_id"]):<20} {str(row["full_pkg_code"]):<45} {str(row["lf_code"]):<12} {str(row["da_code"]):<12}\n')
    f.write('\n')
    f.write('[DISTINCT (da_code, lf_code) 組合明細]\n')
    f.write(f'{"da_code":<12} {"lf_code":<12} {"family數":<8}\n')
    f.write('-' * 35 + '\n')
    for row in q3_groups:
        f.write(f'{str(row["da_code"]):<12} {str(row["lf_code"]):<12} {row["cnt"]:<8}\n')
    f.write('\n')

    # Q4
    f.write('--- Query 4: O-0004 涉及的 family (DA, Wire, Compound 分析) ---\n')
    f.write(f'family 總數: {len(q4_rows)}\n')
    f.write(f'DISTINCT (da_code, wire_code, compound_code) 組合數: {q4_distinct}\n\n')
    header = f'{"family_id":<20} {"full_pkg_code":<45} {"da_code":<10} {"wires_code":<12} {"compound_code":<14}'
    f.write(header + '\n')
    f.write('-' * 105 + '\n')
    for row in q4_rows:
        f.write(f'{str(row["family_id"]):<20} {str(row["full_pkg_code"]):<45} {str(row["da_code"]):<10} {str(row["wires_code"]):<12} {str(row["compound_code"]):<14}\n')
    f.write('\n')
    f.write('[DISTINCT (da_code, wire_code, compound_code) 組合明細]\n')
    f.write(f'{"da_code":<10} {"wire_code":<12} {"compound_code":<14} {"family數":<8}\n')
    f.write('-' * 48 + '\n')
    for row in q4_groups:
        f.write(f'{str(row["da_code"]):<10} {str(row["wires_code"]):<12} {str(row["compound_code"]):<14} {row["cnt"]:<8}\n')
    f.write('\n')

    # Q5
    f.write('--- Query 5: O-0003 全部 family 的 full_pkg_code + seg2(LF), seg3(DA) 解析 ---\n')
    header = f'{"family_id":<20} {"full_pkg_code":<45} {"lf_code(DB)":<14} {"da_code(DB)":<14} {"seg2_LF":<10} {"seg3_DA":<10}'
    f.write(header + '\n')
    f.write('-' * 118 + '\n')
    for row in q5_rows:
        f.write(f'{str(row["family_id"]):<20} {str(row["full_pkg_code"]):<45} {str(row["lf_code"]):<14} {str(row["da_code"]):<14} {str(row["seg2_LF"]):<10} {str(row["seg3_DA"]):<10}\n')
    f.write('\n')

    # Q6
    f.write('--- Query 6: O-0004 全部 family 的 full_pkg_code + seg3(DA), seg4(Wire), seg5(Compound) 解析 ---\n')
    header = f'{"family_id":<20} {"full_pkg_code":<45} {"da_code(DB)":<12} {"wire(DB)":<10} {"comp(DB)":<12} {"seg3_DA":<10} {"seg4_Wire":<12} {"seg5_Comp":<12}'
    f.write(header + '\n')
    f.write('-' * 138 + '\n')
    for row in q6_rows:
        f.write(f'{str(row["family_id"]):<20} {str(row["full_pkg_code"]):<45} {str(row["da_code"]):<12} {str(row["wires_code"]):<10} {str(row["compound_code"]):<12} {str(row["seg3_DA"]):<10} {str(row["seg4_Wire"]):<12} {str(row["seg5_Compound"]):<12}\n')
    f.write('\n')

print('Done.')
print(f'Q1: {len(q1)} columns')
print(f'Q2: {len(q2_schema)} columns, {len(q2_sample)} sample rows')
print(f'Q3: {len(q3_rows)} families, distinct(da,lf)={q3_distinct}')
print(f'Q4: {len(q4_rows)} families, distinct(da,wire,compound)={q4_distinct}')
print(f'Q5: {len(q5_rows)} rows')
print(f'Q6: {len(q6_rows)} rows')
print()
print('Q3 groups (da_code, lf_code, count):')
for row in q3_groups:
    print(f'  da={row["da_code"]}, lf={row["lf_code"]}, cnt={row["cnt"]}')
print()
print('Q4 groups (da_code, wires_code, compound_code, count):')
for row in q4_groups:
    print(f'  da={row["da_code"]}, wire={row["wires_code"]}, compound={row["compound_code"]}, cnt={row["cnt"]}')
