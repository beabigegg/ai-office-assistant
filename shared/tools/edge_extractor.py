#!/usr/bin/env python3
"""LLM-assisted edge extraction for KB Phase 4 T4.2.

Iterates active decision/learning nodes, fetches BM25 neighbors,
asks gpt-oss to classify the relation, writes proposals to edge_proposals.

Resumable: skips source_id already processed by this extractor version.

Usage:
    python edge_extractor.py --batch-size 10 [--project ecr-ecn] [--dry-run]
"""
import json
import sqlite3
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / 'shared' / 'kb' / 'knowledge_graph' / 'kb_index.db'
EXTRACTOR_VERSION = 'gpt-oss-v1'
DELAY_SEC = 3
DEFAULT_TOP_N = 5

import os
_env_path = REPO_ROOT / '.env'
if _env_path.exists():
    for _line in _env_path.read_text(encoding='utf-8').splitlines():
        if '=' in _line and not _line.startswith('#'):
            _k, _, _v = _line.partition('=')
            os.environ.setdefault(_k.strip(), _v.strip())

GPT_OSS_URL = os.environ.get('GPT_OSS_URL', 'http://localhost:11434/api/generate')
GPT_OSS_MODEL = os.environ.get('GPT_OSS_MODEL', 'gpt-oss:20b')
GPT_OSS_API_KEY = os.environ.get('GPT_OSS_API_KEY', '')

# Build RELATION_PROMPT without embedded single/double quote conflicts
_PROMPT_PARTS = [
    'You are a knowledge graph analyst. Analyze the relationship between SOURCE and CANDIDATE.\n\n',
    'SOURCE [{src_id}] ({src_type}):\n{src_text}\n\n',
    'CANDIDATE [{tgt_id}] ({tgt_type}):\n{tgt_text}\n\n',
    'Choose the ONE best relation, or "none" if no meaningful relationship exists:\n',
    '- refines: SOURCE narrows, clarifies, or corrects CANDIDATE\n',
    '- contradicts: SOURCE opposes or invalidates CANDIDATE\n',
    '- extends: SOURCE builds upon or generalizes CANDIDATE\n',
    '- depends_on: SOURCE requires CANDIDATE to be in effect\n',
    '- references: SOURCE mentions or loosely refers to CANDIDATE\n',
    '- none: no meaningful relationship\n\n',
    # Double braces escape literal { } in .format() calls
    'Output ONLY valid JSON: {{"relation": "<relation>", "confidence": <0.0-1.0>, "reasoning": "<one sentence>"}}\n',
]
RELATION_PROMPT = ''.join(_PROMPT_PARTS)


def _call_gpt_oss(prompt: str, timeout: int = 60) -> dict:
    """Call gpt-oss API (Ollama-compatible or OpenAI-compatible)."""
    payload = json.dumps({
        'model': GPT_OSS_MODEL,
        'prompt': prompt,
        'stream': False,
        'format': 'json',
        'options': {'temperature': 0.1}
    }).encode('utf-8')

    headers = {'Content-Type': 'application/json'}
    if GPT_OSS_API_KEY:
        headers['Authorization'] = 'Bearer ' + GPT_OSS_API_KEY

    req = urllib.request.Request(GPT_OSS_URL, data=payload, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode('utf-8')
            data = json.loads(raw)
            # Ollama format: {"response": "...json..."}
            # OpenAI format: {"choices": [{"message": {"content": "..."}}]}
            if 'response' in data:
                return json.loads(data['response'])
            elif 'choices' in data:
                return json.loads(data['choices'][0]['message']['content'])
            return data
    except (urllib.error.URLError, json.JSONDecodeError, KeyError, TimeoutError) as e:
        raise RuntimeError('gpt-oss call failed: ' + str(e)) from e


def _sanitize_fts_query(text: str) -> str:
    """Extract ASCII word tokens for FTS5 MATCH query.

    CJK text uses the trigram tokenizer and works best when individual
    trigrams are matched; however arbitrary CJK punctuation causes FTS5
    syntax errors.  We extract only ASCII word characters (letters, digits,
    underscores) which are safe as bare-word terms, then collapse whitespace.
    """
    import re as _re
    # Keep only ASCII word chars (\w in ASCII mode = [a-zA-Z0-9_])
    cleaned = _re.sub(r'[^\w\s]', ' ', text, flags=_re.ASCII)
    cleaned = _re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned[:200]


def _bm25_neighbors(conn, node_id: str, node_text: str, top_n: int) -> list:
    """Use FTS5 BM25 to find candidate neighbors for a node."""
    safe = _sanitize_fts_query(node_text)
    if not safe.strip():
        return []
    try:
        rows = conn.execute(
            'SELECT node_id FROM node_fts WHERE node_fts MATCH ? AND node_id != ? '
            'ORDER BY bm25(node_fts) LIMIT ?',
            (safe, node_id, top_n)
        ).fetchall()
        return [r[0] for r in rows]
    except Exception:
        return []


def run(db_path=None, batch_size=None, project=None, dry_run=False):
    """Main extraction loop. Returns (processed_count, proposals_written_count)."""
    db_path = db_path or str(DB_PATH)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    sys.path.insert(0, str(REPO_ROOT / 'shared' / 'tools'))
    from kb import _ensure_schema
    _ensure_schema(conn)

    # Load already-processed source_ids for this extractor version (resumable)
    done = {
        r[0] for r in conn.execute(
            'SELECT DISTINCT source_id FROM edge_proposals WHERE extractor=?',
            (EXTRACTOR_VERSION,)
        )
    }

    sql = (
        'SELECT id, node_type, target, summary, full_text FROM nodes '
        "WHERE status='active' AND node_type IN ('decision', 'learning')"
    )
    params = []
    if project:
        sql += ' AND (project=? OR affects_project LIKE ?)'
        params.extend([project, '%' + project + '%'])
    sql += ' ORDER BY id'
    nodes = conn.execute(sql, params).fetchall()

    processed = 0
    proposals_written = 0

    for n in nodes:
        node_id = n['id']
        if node_id in done:
            continue

        node_text = ' '.join(filter(None, [n['target'], n['summary']]))
        neighbors = _bm25_neighbors(conn, node_id, node_text, DEFAULT_TOP_N)

        for nb_id in neighbors:
            nb = conn.execute(
                'SELECT id, node_type, target, summary FROM nodes WHERE id=?', (nb_id,)
            ).fetchone()
            if not nb:
                continue

            src_text = (n['target'] or '') + ' | ' + (n['summary'] or '')
            tgt_text = (nb['target'] or '') + ' | ' + (nb['summary'] or '')
            prompt = RELATION_PROMPT.format(
                src_id=node_id, src_type=n['node_type'],
                src_text=src_text[:400],
                tgt_id=nb_id, tgt_type=nb['node_type'],
                tgt_text=tgt_text[:300],
            )

            if dry_run:
                print('[DRY-RUN] ' + node_id + ' -> ' + nb_id + ' (would call gpt-oss)')
                continue

            try:
                result = _call_gpt_oss(prompt)
                relation = result.get('relation', 'none')
                confidence = float(result.get('confidence', 0.5))
                reasoning = str(result.get('reasoning', ''))[:300]

                if relation == 'none':
                    continue

                conn.execute(
                    'INSERT OR IGNORE INTO edge_proposals '
                    '(source_id, target_id, relation, confidence, extractor, reasoning, status, proposed_at) '
                    "VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)",
                    (node_id, nb_id, relation, confidence, EXTRACTOR_VERSION,
                     reasoning, datetime.now().isoformat())
                )
                proposals_written += 1

            except RuntimeError as e:
                print('[WARN] ' + node_id + ' -> ' + nb_id + ': ' + str(e), file=sys.stderr)

            if not dry_run:
                time.sleep(DELAY_SEC)

        conn.commit()
        processed += 1

        if batch_size and processed >= batch_size:
            print('Batch limit reached (' + str(batch_size) + ' nodes).')
            break

    conn.close()
    print('Processed: ' + str(processed) + ' source nodes | Proposals written: ' + str(proposals_written))
    return processed, proposals_written


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch-size', type=int, default=None)
    parser.add_argument('--project', type=str, default=None)
    parser.add_argument('--dry-run', action='store_true',
                        help='Print actions without calling gpt-oss')
    args = parser.parse_args()
    run(batch_size=args.batch_size, project=args.project, dry_run=args.dry_run)


if __name__ == '__main__':
    main()