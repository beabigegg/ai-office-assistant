"""
Knowledge Graph Query Tool for Process Analysis.
Provides multi-hop graph traversal, cross-station comparison, and impact analysis.

Usage:
    python graph_query.py trace <entity_name> [--type TYPE] [--depth N] [--station STATION]
    python graph_query.py impact <entity_name> [--station STATION]
    python graph_query.py compare <station1> <station2> [--type TYPE]
    python graph_query.py related <entity_name> [--station STATION]
    python graph_query.py path <entity1> <entity2> [--station STATION]
    python graph_query.py gaps [--station STATION]
    python graph_query.py stats
    python graph_query.py search <keyword> [--type TYPE] [--station STATION]
"""
import sqlite3
import sys
import argparse
import json

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = r'D:\AI_test\projects\process-analysis\workspace\db\process_analysis.db'


def get_conn():
    return sqlite3.connect(DB_PATH)


def cmd_trace(args):
    """Multi-hop trace: follow all relations from an entity."""
    conn = get_conn()
    c = conn.cursor()

    # Find seed entities
    where = "e.name_normalized LIKE ?"
    params = [f'%{args.name}%']
    if args.type:
        where += " AND e.entity_type = ?"
        params.append(args.type)
    if args.station:
        where += " AND e.station_id = ?"
        params.append(args.station)

    c.execute(f'SELECT entity_id, station_id, entity_type, name, attributes FROM kg_entities e WHERE {where}', params)
    seeds = c.fetchall()

    if not seeds:
        print(f'No entity found matching "{args.name}"')
        return

    depth = args.depth or 2
    for eid, sid, etype, ename, attrs in seeds:
        print(f'\n[{sid}] {etype}: {ename}')
        if attrs:
            print(f'  attributes: {attrs}')
        _trace_recursive(c, eid, sid, depth, visited=set(), indent=1)

    conn.close()


def _trace_recursive(cursor, entity_id, station_id, depth, visited, indent):
    """Recursively follow relations."""
    if depth <= 0 or entity_id in visited:
        return
    visited.add(entity_id)

    prefix = '  ' * indent

    # Outgoing relations
    cursor.execute('''
        SELECT r.relation_type, e.entity_id, e.entity_type, e.name
        FROM kg_relations r JOIN kg_entities e ON r.target_entity_id = e.entity_id
        WHERE r.source_entity_id = ? AND r.station_id = ?
    ''', (entity_id, station_id))
    for rtype, tid, ttype, tname in cursor.fetchall():
        print(f'{prefix}──{rtype}──> [{ttype}] {tname}')
        _trace_recursive(cursor, tid, station_id, depth - 1, visited, indent + 1)

    # Incoming relations
    cursor.execute('''
        SELECT r.relation_type, e.entity_id, e.entity_type, e.name
        FROM kg_relations r JOIN kg_entities e ON r.source_entity_id = e.entity_id
        WHERE r.target_entity_id = ? AND r.station_id = ?
    ''', (entity_id, station_id))
    for rtype, sid_ent, stype, sname in cursor.fetchall():
        print(f'{prefix}<──{rtype}── [{stype}] {sname}')
        _trace_recursive(cursor, sid_ent, station_id, depth - 1, visited, indent + 1)


def cmd_impact(args):
    """Impact analysis: what failure modes does this entity affect?"""
    conn = get_conn()
    c = conn.cursor()

    where = "e.name_normalized LIKE ?"
    params = [f'%{args.name}%']
    if args.station:
        where += " AND e.station_id = ?"
        params.append(args.station)

    c.execute(f'SELECT entity_id, station_id, entity_type, name FROM kg_entities e WHERE {where}', params)
    seeds = c.fetchall()

    if not seeds:
        print(f'No entity found matching "{args.name}"')
        return

    for eid, sid, etype, ename in seeds:
        print(f'\n=== Impact of [{etype}] {ename} (Station {sid}) ===')

        # Find connected failure_modes (up to 3 hops)
        failure_modes = set()
        _find_type_recursive(c, eid, sid, 'failure_mode', 3, set(), failure_modes)

        if failure_modes:
            print(f'Related failure modes ({len(failure_modes)}):')
            for fm_id, fm_name in failure_modes:
                # Find prevention and detection for this FM
                c.execute('''
                    SELECT r.relation_type, e.entity_type, e.name
                    FROM kg_relations r JOIN kg_entities e ON r.source_entity_id = e.entity_id
                    WHERE r.target_entity_id = ? AND r.station_id = ?
                    AND e.entity_type IN ('prevention', 'detection')
                ''', (fm_id, sid))
                controls = c.fetchall()
                print(f'  • {fm_name}')
                for rtype, ctype, cname in controls:
                    print(f'    {rtype}: {cname}')
        else:
            print('  No related failure modes found')

    conn.close()


def _find_type_recursive(cursor, entity_id, station_id, target_type, depth, visited, results):
    """Find entities of target_type within N hops."""
    if depth <= 0 or entity_id in visited:
        return
    visited.add(entity_id)

    # Check if current entity matches
    cursor.execute('SELECT entity_type, name FROM kg_entities WHERE entity_id=?', (entity_id,))
    row = cursor.fetchone()
    if row and row[0] == target_type:
        results.add((entity_id, row[1]))

    # Follow all relations
    cursor.execute('''
        SELECT DISTINCT target_entity_id FROM kg_relations
        WHERE source_entity_id = ? AND station_id = ?
        UNION
        SELECT DISTINCT source_entity_id FROM kg_relations
        WHERE target_entity_id = ? AND station_id = ?
    ''', (entity_id, station_id, entity_id, station_id))
    for (next_id,) in cursor.fetchall():
        _find_type_recursive(cursor, next_id, station_id, target_type, depth - 1, visited, results)


def cmd_compare(args):
    """Cross-station comparison of entities by type."""
    conn = get_conn()
    c = conn.cursor()
    s1, s2 = args.station1, args.station2
    etype = args.type or 'failure_mode'

    # Only in s1
    c.execute('''
        SELECT name FROM kg_entities WHERE station_id=? AND entity_type=?
        AND name_normalized NOT IN (SELECT name_normalized FROM kg_entities WHERE station_id=? AND entity_type=?)
        ORDER BY name
    ''', (s1, etype, s2, etype))
    only_s1 = [r[0] for r in c.fetchall()]

    # Only in s2
    c.execute('''
        SELECT name FROM kg_entities WHERE station_id=? AND entity_type=?
        AND name_normalized NOT IN (SELECT name_normalized FROM kg_entities WHERE station_id=? AND entity_type=?)
        ORDER BY name
    ''', (s2, etype, s1, etype))
    only_s2 = [r[0] for r in c.fetchall()]

    # Common
    c.execute('''
        SELECT e1.name FROM kg_entities e1 JOIN kg_entities e2
        ON e1.entity_type = e2.entity_type AND e1.name_normalized = e2.name_normalized
        WHERE e1.station_id=? AND e2.station_id=? AND e1.entity_type=?
        ORDER BY e1.name
    ''', (s1, s2, etype))
    common = [r[0] for r in c.fetchall()]

    print(f'=== {etype} comparison: {s1} vs {s2} ===')
    print(f'\nCommon ({len(common)}):')
    for n in common:
        print(f'  • {n}')
    print(f'\n{s1} only ({len(only_s1)}):')
    for n in only_s1:
        print(f'  • {n}')
    print(f'\n{s2} only ({len(only_s2)}):')
    for n in only_s2:
        print(f'  • {n}')

    conn.close()


def cmd_related(args):
    """Find all entities related to a given entity."""
    conn = get_conn()
    c = conn.cursor()

    where = "e.name_normalized LIKE ?"
    params = [f'%{args.name}%']
    if args.station:
        where += " AND e.station_id = ?"
        params.append(args.station)

    c.execute(f'SELECT entity_id, station_id, entity_type, name FROM kg_entities e WHERE {where}', params)
    seeds = c.fetchall()

    for eid, sid, etype, ename in seeds:
        print(f'\n=== Related to [{etype}] {ename} (Station {sid}) ===')

        c.execute('''
            SELECT r.relation_type, e.entity_type, e.name, 'outgoing'
            FROM kg_relations r JOIN kg_entities e ON r.target_entity_id = e.entity_id
            WHERE r.source_entity_id = ? AND r.station_id = ?
            UNION ALL
            SELECT r.relation_type, e.entity_type, e.name, 'incoming'
            FROM kg_relations r JOIN kg_entities e ON r.source_entity_id = e.entity_id
            WHERE r.target_entity_id = ? AND r.station_id = ?
            ORDER BY 2, 1
        ''', (eid, sid, eid, sid))

        for rtype, retype, rename, direction in c.fetchall():
            arrow = '→' if direction == 'outgoing' else '←'
            print(f'  {arrow} {rtype:12s} [{retype}] {rename}')

    conn.close()


def cmd_path(args):
    """Find shortest path between two entities (BFS)."""
    conn = get_conn()
    c = conn.cursor()

    station = args.station or '1610'

    # Find start entity
    c.execute('SELECT entity_id, name FROM kg_entities WHERE name_normalized LIKE ? AND station_id=? LIMIT 1',
              (f'%{args.entity1}%', station))
    start = c.fetchone()

    # Find end entity
    c.execute('SELECT entity_id, name FROM kg_entities WHERE name_normalized LIKE ? AND station_id=? LIMIT 1',
              (f'%{args.entity2}%', station))
    end = c.fetchone()

    if not start or not end:
        print(f'Entity not found: start={start}, end={end}')
        conn.close()
        return

    print(f'Finding path: [{start[1]}] → [{end[1]}] (Station {station})')

    # BFS
    from collections import deque
    queue = deque([(start[0], [start[0]])])
    visited = {start[0]}
    found = False

    while queue and not found:
        current, path = queue.popleft()
        if len(path) > 6:
            continue

        c.execute('''
            SELECT target_entity_id FROM kg_relations WHERE source_entity_id=? AND station_id=?
            UNION
            SELECT source_entity_id FROM kg_relations WHERE target_entity_id=? AND station_id=?
        ''', (current, station, current, station))

        for (next_id,) in c.fetchall():
            if next_id == end[0]:
                path.append(next_id)
                # Print path
                print(f'Path found ({len(path)-1} hops):')
                for i, nid in enumerate(path):
                    c.execute('SELECT entity_type, name FROM kg_entities WHERE entity_id=?', (nid,))
                    nt, nn = c.fetchone()
                    if i < len(path) - 1:
                        c.execute('''SELECT relation_type FROM kg_relations
                                     WHERE (source_entity_id=? AND target_entity_id=?) OR (source_entity_id=? AND target_entity_id=?)
                                     AND station_id=? LIMIT 1''',
                                  (nid, path[i+1], path[i+1], nid, station))
                        rel = c.fetchone()
                        rname = rel[0] if rel else '?'
                        print(f'  [{nt}] {nn} ──{rname}──>')
                    else:
                        print(f'  [{nt}] {nn}')
                found = True
                break

            if next_id not in visited:
                visited.add(next_id)
                queue.append((next_id, path + [next_id]))

    if not found:
        print('No path found within 6 hops')

    conn.close()


def cmd_gaps(args):
    """Find FMEA failure modes without CP coverage."""
    conn = get_conn()
    c = conn.cursor()
    station = args.station or '1610'

    # FMEA failure modes
    c.execute('''SELECT entity_id, name FROM kg_entities
                 WHERE station_id=? AND entity_type='failure_mode'
                 ORDER BY name''', (station,))
    fmea_fms = c.fetchall()

    # Check which have CP-sourced relations
    print(f'=== Gap Analysis: FMEA without CP coverage (Station {station}) ===\n')
    gaps = []
    covered = []

    for eid, ename in fmea_fms:
        # Check if this entity has source links from CP
        c.execute('''SELECT COUNT(*) FROM kg_entity_sources
                     WHERE entity_id=? AND source_type='cp' ''', (eid,))
        cp_count = c.fetchone()[0]

        # Also check if any related entity (prevention/detection) has CP source
        c.execute('''
            SELECT COUNT(*) FROM kg_relations r
            JOIN kg_entity_sources es ON (r.source_entity_id = es.entity_id OR r.target_entity_id = es.entity_id)
            WHERE (r.source_entity_id = ? OR r.target_entity_id = ?) AND es.source_type = 'cp'
        ''', (eid, eid))
        related_cp = c.fetchone()[0]

        if cp_count == 0 and related_cp == 0:
            gaps.append(ename)
        else:
            covered.append(ename)

    print(f'Covered by CP ({len(covered)}): {len(covered)}/{len(fmea_fms)}')
    print(f'NOT covered ({len(gaps)}):')
    for g in gaps:
        print(f'  ⚠ {g}')

    conn.close()


def cmd_search(args):
    """Search entities by keyword."""
    conn = get_conn()
    c = conn.cursor()

    where = "name_normalized LIKE ?"
    params = [f'%{args.keyword}%']
    if args.type:
        where += " AND entity_type = ?"
        params.append(args.type)
    if args.station:
        where += " AND station_id = ?"
        params.append(args.station)

    c.execute(f'''SELECT entity_id, station_id, entity_type, name,
                  (SELECT COUNT(*) FROM kg_relations WHERE source_entity_id=entity_id OR target_entity_id=entity_id) as rel_count
                  FROM kg_entities WHERE {where} ORDER BY rel_count DESC LIMIT 20''', params)

    results = c.fetchall()
    print(f'Found {len(results)} entities matching "{args.keyword}":')
    for eid, sid, etype, ename, rcnt in results:
        print(f'  [{sid}] {etype:15s} | {ename} ({rcnt} relations)')

    conn.close()


def cmd_stats(args):
    """Show KG statistics."""
    conn = get_conn()
    c = conn.cursor()

    c.execute('SELECT COUNT(*) FROM kg_entities')
    print(f'Entities: {c.fetchone()[0]}')
    c.execute('SELECT COUNT(*) FROM kg_relations')
    print(f'Relations: {c.fetchone()[0]}')
    c.execute('SELECT COUNT(*) FROM kg_entity_sources')
    print(f'Source links: {c.fetchone()[0]}')

    print('\nBy station:')
    c.execute('SELECT station_id, COUNT(*) FROM kg_entities GROUP BY station_id')
    for r in c.fetchall():
        print(f'  {r[0]}: {r[1]} entities')

    print('\nEntity types:')
    c.execute('SELECT entity_type, COUNT(*) FROM kg_entities GROUP BY entity_type ORDER BY COUNT(*) DESC')
    for r in c.fetchall():
        print(f'  {r[0]:20s} {r[1]:>5}')

    print('\nRelation types:')
    c.execute('SELECT relation_type, COUNT(*) FROM kg_relations GROUP BY relation_type ORDER BY COUNT(*) DESC')
    for r in c.fetchall():
        print(f'  {r[0]:20s} {r[1]:>5}')

    conn.close()


def main():
    parser = argparse.ArgumentParser(description='Knowledge Graph Query Tool')
    sub = parser.add_subparsers(dest='command')

    p = sub.add_parser('trace', help='Multi-hop trace from entity')
    p.add_argument('name')
    p.add_argument('--type', '-t')
    p.add_argument('--depth', '-d', type=int)
    p.add_argument('--station', '-s')

    p = sub.add_parser('impact', help='Impact analysis')
    p.add_argument('name')
    p.add_argument('--station', '-s')

    p = sub.add_parser('compare', help='Cross-station comparison')
    p.add_argument('station1')
    p.add_argument('station2')
    p.add_argument('--type', '-t')

    p = sub.add_parser('related', help='Find related entities')
    p.add_argument('name')
    p.add_argument('--station', '-s')

    p = sub.add_parser('path', help='Find path between entities')
    p.add_argument('entity1')
    p.add_argument('entity2')
    p.add_argument('--station', '-s')

    p = sub.add_parser('gaps', help='FMEA-CP gap analysis')
    p.add_argument('--station', '-s')

    p = sub.add_parser('search', help='Search entities')
    p.add_argument('keyword')
    p.add_argument('--type', '-t')
    p.add_argument('--station', '-s')

    p = sub.add_parser('stats', help='KG statistics')

    args = parser.parse_args()

    commands = {
        'trace': cmd_trace, 'impact': cmd_impact, 'compare': cmd_compare,
        'related': cmd_related, 'path': cmd_path, 'gaps': cmd_gaps,
        'search': cmd_search, 'stats': cmd_stats,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
