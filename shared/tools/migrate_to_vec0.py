#!/usr/bin/env python3
"""
一次性遷移腳本：把 node_embeddings 的 BLOB 灌入 node_vec（sqlite-vec vec0 virtual table）。

執行：
    PYTHONUTF8=1 python shared/tools/migrate_to_vec0.py
"""
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = ROOT / 'shared' / 'kb' / 'knowledge_graph' / 'kb_index.db'

def main():
    # 1. 連線並載入 sqlite-vec
    try:
        import sqlite_vec
    except ImportError:
        print("ERROR: sqlite-vec not installed. Run: pip install sqlite-vec")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    print("sqlite-vec loaded OK")

    # 2. 建立 vec0 virtual table（若不存在）
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS node_vec USING vec0(
            node_id TEXT PRIMARY KEY,
            embedding FLOAT[2560]
        )
    """)
    conn.commit()
    print("node_vec table ready")

    # 3. 讀取所有 node_embeddings
    rows = conn.execute(
        "SELECT node_id, embedding FROM node_embeddings"
    ).fetchall()
    print(f"Found {len(rows)} embeddings in node_embeddings")

    # 4. 批次寫入 node_vec
    ok = 0
    fail = 0
    for row in rows:
        try:
            conn.execute(
                "INSERT OR REPLACE INTO node_vec (node_id, embedding) VALUES (?, ?)",
                (row['node_id'], row['embedding'])
            )
            ok += 1
        except Exception as e:
            print(f"  FAIL {row['node_id']}: {e}")
            fail += 1

    conn.commit()
    print(f"Migrated: {ok} OK, {fail} failed")

    # 5. 驗證數量一致
    vec_count = conn.execute("SELECT count(*) FROM node_vec").fetchone()[0]
    emb_count = conn.execute("SELECT count(*) FROM node_embeddings").fetchone()[0]
    print(f"\nValidation: node_vec={vec_count}, node_embeddings={emb_count}")
    if vec_count == emb_count:
        print("✓ Count match — migration complete")
    else:
        print(f"✗ Count mismatch! Diff = {emb_count - vec_count}")
        sys.exit(1)

    # 6. 快速搜尋測試
    print("\nQuick search test (k=3):")
    test_rows = conn.execute("SELECT node_id, embedding FROM node_embeddings LIMIT 1").fetchall()
    if test_rows:
        sample_blob = test_rows[0]['embedding']
        results = conn.execute("""
            SELECT node_id, distance FROM node_vec
            WHERE embedding MATCH ? AND k = 3
            ORDER BY distance
        """, (sample_blob,)).fetchall()
        for r in results:
            print(f"  {r['node_id']}: distance={r['distance']:.4f}")
    else:
        print("  (no embeddings to test)")

    conn.close()
    print("\nDone.")


if __name__ == '__main__':
    main()
