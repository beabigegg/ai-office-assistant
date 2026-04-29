#!/usr/bin/env python3
"""Knowledge Base Index — SQLite-backed index for decisions, rules, and semantics.

NOTE: EVO-012 Phase 3 complete. DB (kb_index.db) is now source of truth.
Primary CLI is kb.py. This tool is retained for sync/impacts/generate-index/embedding.

Usage:
    python kb_index.py sync
    python kb_index.py active [--project X] [--fmt line|ids|full]
    python kb_index.py trace <ID> [--fmt line|ids|full]
    python kb_index.py related --target X / --skill X / --db X [--fmt line|ids|full]
    python kb_index.py validate [--quiet]
    python kb_index.py impacts --project X / --skill X [--fmt line|ids|full]
"""
import argparse
import json
import os
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Embedding support (lazy import to avoid startup cost)
_embedding_utils = None

def _get_embedding_utils():
    """Lazy import embedding_utils to avoid cost when not needed."""
    global _embedding_utils
    if _embedding_utils is None:
        try:
            from embedding_utils import (
                get_embedding, embedding_to_blob, blob_to_embedding,
                cosine_similarity, is_ollama_available,
            )
            _embedding_utils = {
                'get_embedding': get_embedding,
                'embedding_to_blob': embedding_to_blob,
                'blob_to_embedding': blob_to_embedding,
                'cosine_similarity': cosine_similarity,
                'is_ollama_available': is_ollama_available,
            }
        except ImportError:
            _embedding_utils = {}
    return _embedding_utils

# Resolve paths
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent.parent  # repo root
KB_ROOT = ROOT / 'shared' / 'kb'
KG_DIR = KB_ROOT / 'knowledge_graph'
DB_PATH = KG_DIR / 'kb_index.db'
SCHEMA_PATH = KG_DIR / 'kb_schema.sql'

DECISIONS_PATH = KB_ROOT / 'decisions.md'
RULES_PATH = KB_ROOT / 'dynamic' / 'ecr_ecn_rules.md'
COLUMN_SEM_PATH = KB_ROOT / 'dynamic' / 'column_semantics.md'
LEARNING_PATH = KB_ROOT / 'dynamic' / 'learning_notes.md'

SEMANTIC_OVERLAP_SUPPRESS_RELATIONS = {
    'references',
    'related_to',
    'duplicate_of',
    'same_topic',
    'supersedes',
    'superseded_by',
}
SEMANTIC_TOKEN_STOPWORDS = {
    'shared',
    'tools',
    'tool',
    'workspace',
    'projects',
    'project',
    'scripts',
    'python',
    'py',
    'md',
    'json',
    'db',
}


# ── Static templates for generate-index (stable content, rarely changes) ──

_RULES_DETAIL_TEMPLATE = """### 規則明細（共 51 條）

#### bom-rules (6)
| ID | 名稱 | 關鍵詞 |
|----|------|--------|
| R1 | BOM-FLAT-PROCESS | 扁平結構, 非樹狀 |
| R2 | BOM-ALT-DESIGNATOR | alt_bom_designator, 製程變體 |
| R3 | BOM-VENDOR-FLATTEN | 不適用 |
| R4 | SUBSTITUTE-PATTERNS | 替代材料, sub_com_remarks |
| R5 | ASS-ITEM-NO-CODING | 組裝品料號, 5碼控制碼 |
| R6 | UNIVERSAL-EXCLUSION | RD-, PE-, EOL, GD, MBU3 |

#### process-bom-semantics (12)
| ID | 名稱 | 關鍵詞 |
|----|------|--------|
| R1 | OPERATION-SEQ-NUM | 站別, Op 10/15/23/28, -DW |
| R2 | COM-QTY-RULE | com_qty, 主料, 備用料 |
| R3 | ALT-BOM-DESIGNATOR | 替代結構, 製程變體→bop |
| R4 | BOP-CODING | Bop編碼, U/E/P, 線徑 |
| R5 | WAF-LIFECYCLE | WAF0, WAF9, _CP, 入庫 |
| R6 | DESC-PRIORITY | Desc解析, 空白率 |
| R7 | BOM-NAME-JOIN | bom_name, 跨物料, CLIP無線材 |
| R8 | DUAL-LAYER-QUERY | 雙層結構, Com/SubCom, 2nd Source |
| R9 | PACKAGE-DIE-SIZE | Die Size範圍, 封裝分類 |
| R10 | LEADFRAME-MATERIAL | A42, Cu腳架, CLIP |
| R11 | METAL-CODING | AGAG, AUAU, ALAU, ALSN, 背金/背銀 |
| R12 | BACKMETAL-DA | Sn→Eutectic, Ag→Epoxy, 搭配限制 |

#### reliability-testing / automotive-reliability-standards
| ID | 名稱 | 關鍵詞 |
|----|------|--------|
| - | Q101-OVERVIEW | Test Group A~E, 測試概覽 |
| - | Q006-SUMMARY | 銅線驗證, Option 1/2, Family |
| - | GRADE-TEMP | Grade 0~3, 溫度範圍 |
| - | TABLE3-MATRIX | 變更測試矩陣, 15 子分類 |
| - | FAQ | TS, TCDT, H3TRB vs HAST, Schottky |
| VR1 | Q006-SUPPLEMENT | Q006是Q101補充 |
| VR2 | HTSL-VS-HTRB | HTSL無偏壓, HTRB有偏壓, 不可互替 |
| VR3 | PDAUCU-NO-NOTE2 | PdAuCu不豁免, BSOB必須做TCT |
| VR4 | WIRE-CHANGE-ESD-DPA | 線材變更需ESD+DPA qualification |
| VR5 | WBP-THRESHOLD | M2037 2.5gf vs Q101 3gf |
| VR6 | C6-PTH-ONLY | Terminal Strength僅PTH, DO-218AB=SMT |
| VR7 | BACKMETAL-IS-DA | 背面金屬變更=Die Attach, 非Die Overcoat |

#### package-code (10)
| ID | 名稱 | 關鍵詞 |
|----|------|--------|
| R1 | FULL-PKG-CODE-STRUCTURE | 六段結構 |
| R2 | PKG-CODE-MODES | SOT/SOD, DFN, SMA, TO/DO 四模式 |
| R3 | LF-CODE | 腳架材質代碼 C/A/P/B/G/H |
| R4 | DA-CODE | D/A代碼 EP/EU/SS/SP/SF |
| R5 | WIRES-CODE | 線材代碼 CU/AU/AG/PC/CJ |
| R6 | COMPOUND-CODE | 成型膠 33組, 7組覆蓋95.5% |
| R7 | VENDOR-CODE | 供應商 2023新制 5/6/7 |
| R8 | CODE-MAPPING | NEW vs OLD 對照 |
| R9 | ECR-CROSS-REF | ECR交叉關聯 |
| R10 | BOP-DERIVATION | BOP→PKG CODE推導, pj_package映射 |

#### mil-std-750 (8)
| ID | 名稱 | 關鍵詞 |
|----|------|--------|
| - | STANDARD-STRUCTURE | Part 1~5, 750 vs 883 |
| - | Q101-CROSS-REF | AEC-Q101引用對照 |
| - | M2017 | Die Shear, 2.5Kg |
| - | M2037 | Bond Pull, 2.5/3.0 gf |
| - | M2076 | Die Attach Void, X-ray |
| - | M2036 | Terminal Strength, PTH only |
| - | M1038/1039/1040/1042 | Burn-in 各元件類型 |
| - | M1051 | Temperature Cycling |"""

_EXTERNAL_STANDARDS_TEMPLATE = """## 外部標準（shared/kb/external/standards/）

| 標準體系 | 檔案 | 公司適用 |
|---------|------|---------|
| AEC-Q101 Rev E | aec-q/ | **主要** |
| AEC-Q006 Rev B | aec-q/ | **銅線必須** |
| AEC-Q100 Rev J | aec-q/ | 參考 |
| MIL-STD-883 Rev L | mil-std/ | 測試方法 |
| JESD22 Series | jedec/ | 環境/壽命測試 |
| J-STD Series | ipc-jedec/ | MSL 分類 |"""

_UPGRADE_HISTORY_TEMPLATE = """## 升級歷程摘要

| 日期 | 動作 | 數量 |
|------|------|------|
| 2026-02-05 | 初建 bom-rules, process-bom-semantics, reliability-testing | 3 Skills |
| 2026-04-24 | reliability-testing 開始拆分為 automotive-reliability-standards + internal overlay | 1 Skill split |
| 2026-02-06 | 初建 package-code | 1 Skill |
| 2026-02-09 | 初建 mil-std-750 | 1 Skill |
| 2026-02-22 | 全量反例驗證 + R10~R12 新增 | process-bom-semantics 大修 |
| 2026-02-22 | R10 BOP推導 + pj_package映射 | package-code 擴充 |
| 2026-02-25 | /promote: VR1~VR7 + R12 升級 | 9 條知識升級 |
| 2026-02-25 | v3.1 架構升級: triggers 自動路由 + 記憶自動化 | 系統改進 |
| 2026-03-04 | 新建 excel-operations, word-operations, sqlite-operations | 3 Skills |"""


class KBIndex:
    def __init__(self, db_path=None, kb_root=None):
        self.db_path = Path(db_path or DB_PATH)
        self.kb_root = Path(kb_root or KB_ROOT)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        schema_path = self.db_path.parent / 'kb_schema.sql'
        if schema_path.exists():
            self.conn.executescript(schema_path.read_text(encoding='utf-8'))
        else:
            # Inline minimal schema
            self.conn.executescript("""
                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY, node_type TEXT NOT NULL, project TEXT,
                    status TEXT DEFAULT 'active', target TEXT, summary TEXT,
                    refs_skill TEXT, refs_db TEXT, affects_project TEXT,
                    created_date TEXT, last_synced TEXT
                );
                CREATE TABLE IF NOT EXISTS edges (
                    source_id TEXT NOT NULL, target_id TEXT NOT NULL, relation TEXT NOT NULL,
                    PRIMARY KEY (source_id, target_id, relation)
                );
                CREATE TABLE IF NOT EXISTS sync_log (
                    source_file TEXT PRIMARY KEY, synced_at TEXT NOT NULL,
                    source_mtime REAL, nodes_synced INTEGER DEFAULT 0
                );
            """)

    def close(self):
        self.conn.close()

    def _has_semantic_overlap_suppress_edge(self, left_id: str, right_id: str) -> bool:
        row = self.conn.execute(
            """
            SELECT 1
            FROM edges
            WHERE relation IN ({})
              AND (
                    (source_id=? AND target_id=?)
                 OR (source_id=? AND target_id=?)
              )
            LIMIT 1
            """.format(",".join("?" for _ in SEMANTIC_OVERLAP_SUPPRESS_RELATIONS)),
            [*SEMANTIC_OVERLAP_SUPPRESS_RELATIONS, left_id, right_id, right_id, left_id],
        ).fetchone()
        return row is not None

    # ── Sync ──────────────────────────────────────────────────────────

    def sync(self, quiet=False, auto_supersede=True):
        """Parse .md files and sync to SQLite.

        Args:
            quiet: Suppress info output
            auto_supersede: When a supersedes edge is found, automatically
                            update the old decision's status in the .md file
        """
        total_nodes = 0
        total_edges = 0

        for src_path, parser in [
            (DECISIONS_PATH, self._parse_decisions),
            (RULES_PATH, self._parse_rules),
            (COLUMN_SEM_PATH, self._parse_column_semantics),
            (LEARNING_PATH, self._parse_learning),
        ]:
            if not src_path.exists():
                continue
            mtime = src_path.stat().st_mtime
            nodes, edges = parser(src_path)
            now = datetime.now().isoformat()

            # Upsert nodes
            for n in nodes:
                self.conn.execute("""
                    INSERT INTO nodes (id, node_type, project, status, target, summary,
                                       refs_skill, refs_db, affects_project, created_date, last_synced)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        node_type=excluded.node_type, project=excluded.project,
                        status=excluded.status, target=excluded.target, summary=excluded.summary,
                        refs_skill=excluded.refs_skill, refs_db=excluded.refs_db,
                        affects_project=excluded.affects_project, created_date=excluded.created_date,
                        last_synced=excluded.last_synced
                """, (
                    n['id'], n['node_type'], n.get('project'), n.get('status', 'active'),
                    n.get('target'), n.get('summary'),
                    json.dumps(n['refs_skill']) if n.get('refs_skill') else None,
                    json.dumps(n['refs_db']) if n.get('refs_db') else None,
                    json.dumps(n['affects_project']) if n.get('affects_project') else None,
                    n.get('created_date'), now
                ))

            # Upsert edges
            for e in edges:
                self.conn.execute("""
                    INSERT OR IGNORE INTO edges (source_id, target_id, relation)
                    VALUES (?, ?, ?)
                """, (e['source'], e['target'], e['relation']))

            # Update sync log
            self.conn.execute("""
                INSERT INTO sync_log (source_file, synced_at, source_mtime, nodes_synced)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(source_file) DO UPDATE SET
                    synced_at=excluded.synced_at, source_mtime=excluded.source_mtime,
                    nodes_synced=excluded.nodes_synced
            """, (str(src_path.name), now, mtime, len(nodes)))

            total_nodes += len(nodes)
            total_edges += len(edges)

        self.conn.commit()

        # M1: Auto-supersede — update .md source of truth
        if auto_supersede:
            fixed = self._auto_supersede_in_md()
            if fixed and not quiet:
                print(f"auto-superseded {len(fixed)} decisions in decisions.md: {', '.join(fixed)}")

        if not quiet:
            print(f"synced: {total_nodes} nodes, {total_edges} edges")
        return total_nodes, total_edges

    def _auto_supersede_in_md(self):
        """M1: When a supersedes edge exists, ensure the old decision's
        meta line in decisions.md has status=superseded.

        Uses block-by-block processing (not full-text regex) to avoid
        cross-block matching bugs.

        Returns list of decision IDs that were updated."""
        if not DECISIONS_PATH.exists():
            return []

        edges = self.conn.execute(
            "SELECT source_id, target_id FROM edges WHERE relation='supersedes'"
        ).fetchall()
        if not edges:
            return []

        # Collect IDs that should be superseded
        should_be_superseded = set()
        for e in edges:
            should_be_superseded.add(e['target_id'])

        content = DECISIONS_PATH.read_text(encoding='utf-8')
        # Split into blocks by D-NNN headers
        blocks = re.split(r'(?=^### D-\d+)', content, flags=re.MULTILINE)

        fixed = []
        new_blocks = []
        for block in blocks:
            m = re.match(r'^### (D-\d+)', block)
            if m and m.group(1) in should_be_superseded:
                did = m.group(1)
                # Only change if meta line exists and says active
                new_block = re.sub(
                    r'(<!--\s*kb:\s*)status=active\b',
                    r'\1status=superseded',
                    block,
                    count=1
                )
                if new_block != block:
                    fixed.append(did)
                    block = new_block
            new_blocks.append(block)

        if fixed:
            new_content = ''.join(new_blocks)
            DECISIONS_PATH.write_text(new_content, encoding='utf-8')
            # Re-parse after modification to keep index consistent
            nodes, edges_new = self._parse_decisions(DECISIONS_PATH)
            now = datetime.now().isoformat()
            for n in nodes:
                self.conn.execute("""
                    INSERT INTO nodes (id, node_type, project, status, target, summary,
                                       refs_skill, refs_db, affects_project, created_date, last_synced)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        status=excluded.status, last_synced=excluded.last_synced
                """, (
                    n['id'], n['node_type'], n.get('project'), n.get('status', 'active'),
                    n.get('target'), n.get('summary'),
                    json.dumps(n['refs_skill']) if n.get('refs_skill') else None,
                    json.dumps(n['refs_db']) if n.get('refs_db') else None,
                    json.dumps(n['affects_project']) if n.get('affects_project') else None,
                    n.get('created_date'), now
                ))
            self.conn.commit()

        return fixed

    def _parse_decisions(self, path):
        """Parse decisions.md into nodes and edges."""
        content = path.read_text(encoding='utf-8')
        nodes = []
        edges = []

        # Split by ### D-NNN headers
        blocks = re.split(r'(?=^### D-\d+)', content, flags=re.MULTILINE)
        for block in blocks:
            m = re.match(r'^### (D-(\d+))\s*--\s*(\d{4}-\d{2}-\d{2})\s*--\s*(.+?)(?:\s*\*\*.*\*\*)?\s*$',
                         block, re.MULTILINE)
            if not m:
                continue

            node_id = m.group(1)
            date = m.group(3)
            project = m.group(4).strip()

            # Check for <!-- kb: ... --> meta line
            meta = {}
            meta_match = re.search(r'<!--\s*kb:\s*(.+?)\s*-->', block)
            if meta_match:
                meta = self._parse_meta(meta_match.group(1))

            # Extract status
            status = meta.get('status', 'active')
            # Auto-detect superseded from header
            if re.search(r'\[(?:已修正|已取代|superseded)', block, re.IGNORECASE):
                status = 'superseded'

            # Extract target
            target = meta.get('target', '')
            if not target:
                # Try to extract from 問題/議題 line
                q_match = re.search(r'[-]\s*(?:問題|議題)[:：]\s*(.+)', block)
                if q_match:
                    target = q_match.group(1).strip()[:80]

            # Extract summary
            summary = meta.get('summary', '')
            if not summary:
                d_match = re.search(r'[-]\s*決定[:：]\s*(.+)', block)
                if d_match:
                    summary = d_match.group(1).strip()[:120]

            # Extract refs (ensure always list)
            _IGNORE_VALUES = {'n/a', 'na', 'none', '', '-'}

            def _ensure_list(val):
                if val is None:
                    return []
                if isinstance(val, str):
                    return [v.strip() for v in val.split('|')
                            if v.strip() and v.strip().lower() not in _IGNORE_VALUES]
                return [v for v in val if str(v).lower() not in _IGNORE_VALUES]

            refs_skill = _ensure_list(meta.get('refs_skill'))
            refs_db = _ensure_list(meta.get('refs_db'))
            affects = _ensure_list(meta.get('affects'))

            # Auto-detect cross-references in text
            # Skill references
            for skill_name in ['bom-rules', 'process-bom-semantics', 'reliability-testing',
                               'automotive-reliability-standards',
                               'package-code', 'mil-std-750', 'pptx-operations']:
                if skill_name in block.lower() and skill_name not in refs_skill:
                    refs_skill.append(skill_name)

            # DB references
            if re.search(r'bom\.db|std_bom', block, re.IGNORECASE) and 'bom.db' not in str(refs_db):
                refs_db.append('bom.db:std_bom')
            if re.search(r'ecr_ecn\.db', block, re.IGNORECASE) and 'ecr_ecn.db' not in str(refs_db):
                refs_db.append('ecr_ecn.db')

            # Cross-project detection
            if 'BOM' in project and 'ecr-ecn' not in str(affects):
                affects.append('ecr-ecn')
            if 'ecr-ecn' in project and 'BOM' in block and 'BOM' not in str(affects):
                affects.append('BOM')

            # Normalize project name
            proj_normalized = project.split('+')[0].strip() if '+' in project else project

            node = {
                'id': node_id,
                'node_type': 'decision',
                'project': proj_normalized,
                'status': status,
                'target': target,
                'summary': summary,
                'refs_skill': refs_skill if refs_skill else None,
                'refs_db': refs_db if refs_db else None,
                'affects_project': affects if affects else None,
                'created_date': date,
            }
            nodes.append(node)

            # Build edges from supersedes
            supersedes_list = meta.get('supersedes', [])
            if isinstance(supersedes_list, str):
                supersedes_list = [s.strip() for s in supersedes_list.split(',')]

            # Auto-detect supersedes from text
            sup_matches = re.findall(r'(?:supersedes?|取代|修正|推翻)\s*(?:→\s*)?(D-\d+)', block, re.IGNORECASE)
            for sid in sup_matches:
                if sid not in supersedes_list and sid != node_id:
                    supersedes_list.append(sid)
            # Also detect "D-031 的xxx完全推翻" pattern
            ref_matches = re.findall(r'(D-\d+)\s*的.*(?:推翻|修正|取代|superseded)', block, re.IGNORECASE)
            for sid in ref_matches:
                if sid not in supersedes_list and sid != node_id:
                    supersedes_list.append(sid)
            # Detect from header: [已修正 → D-032] means THIS node is superseded BY the target
            header_sup_target = None
            header_sup = re.search(r'\[已修正\s*→\s*(D-\d+)\]', block)
            if header_sup:
                header_sup_target = header_sup.group(1)
                edges.append({'source': node_id, 'target': header_sup_target, 'relation': 'superseded_by'})
                edges.append({'source': header_sup_target, 'target': node_id, 'relation': 'supersedes'})

            # Remove header_sup_target from supersedes_list (it's the opposite direction)
            if header_sup_target and header_sup_target in supersedes_list:
                supersedes_list.remove(header_sup_target)

            for sid in supersedes_list:
                edges.append({'source': node_id, 'target': sid, 'relation': 'supersedes'})
                edges.append({'source': sid, 'target': node_id, 'relation': 'superseded_by'})

            # Cross-references to other decisions
            other_refs = re.findall(r'(D-\d+)', block)
            for ref_id in set(other_refs):
                if ref_id != node_id and ref_id not in supersedes_list:
                    edges.append({'source': node_id, 'target': ref_id, 'relation': 'references'})

            # References to rules
            rule_refs = re.findall(r'(ECR-R\d+)', block)
            for rule_id in set(rule_refs):
                edges.append({'source': node_id, 'target': rule_id, 'relation': 'references'})

        return nodes, edges

    def _parse_rules(self, path):
        """Parse ecr_ecn_rules.md into nodes and edges."""
        content = path.read_text(encoding='utf-8')
        nodes = []
        edges = []

        blocks = re.split(r'(?=^### ECR-R\d+)', content, flags=re.MULTILINE)
        for block in blocks:
            m = re.match(r'^### (ECR-R(\d+))[:：]?\s*(.+?)$', block, re.MULTILINE)
            if not m:
                continue

            node_id = m.group(1)
            title = m.group(3).strip()

            # Extract confidence
            conf_match = re.search(r'信心度[:：]\s*(high|medium|low)', block, re.IGNORECASE)
            confidence = conf_match.group(1) if conf_match else 'medium'

            # Extract verification status
            promoted = '[PROMOTED]' in block

            node = {
                'id': node_id,
                'node_type': 'rule',
                'project': 'ecr-ecn',
                'status': 'promoted' if promoted else 'active',
                'target': title[:80],
                'summary': f"[{confidence}] {title[:100]}",
                'refs_skill': None,
                'refs_db': None,
                'affects_project': None,
                'created_date': None,
            }
            nodes.append(node)

            # Cross-references to decisions
            d_refs = re.findall(r'(D-\d+)', block)
            for d_id in set(d_refs):
                edges.append({'source': node_id, 'target': d_id, 'relation': 'references'})

        return nodes, edges

    def _parse_column_semantics(self, path):
        """Parse column_semantics.md into nodes."""
        content = path.read_text(encoding='utf-8')
        nodes = []

        blocks = re.split(r'(?=^### .+)', content, flags=re.MULTILINE)
        idx = 0
        for block in blocks:
            m = re.match(r'^### (.+?)(?:\s*\[PROMOTED\])?\s*$', block, re.MULTILINE)
            if not m:
                continue
            idx += 1
            title = m.group(1).strip()
            promoted = '[PROMOTED]' in block

            # Extract confidence
            conf_match = re.search(r'信心度[:：]\s*(high|medium|low)', block, re.IGNORECASE)
            confidence = conf_match.group(1) if conf_match else 'medium'

            # Extract meaning
            meaning_match = re.search(r'含義[:：]\s*(.+)', block)
            meaning = meaning_match.group(1).strip()[:100] if meaning_match else title

            node_id = f"CS-{idx:03d}"
            node = {
                'id': node_id,
                'node_type': 'column_semantic',
                'project': 'ecr-ecn',
                'status': 'promoted' if promoted else 'active',
                'target': title,
                'summary': f"[{confidence}] {meaning}",
                'refs_skill': None,
                'refs_db': None,
                'affects_project': None,
                'created_date': None,
            }
            nodes.append(node)

        return nodes, []

    def _parse_learning(self, path):
        """Parse learning_notes.md into nodes.

        M2: Supports <!-- status: active|promoted|obsolete --> marker.
        Falls back to [PROMOTED] tag detection for backwards compatibility.
        """
        content = path.read_text(encoding='utf-8')
        nodes = []
        edges = []

        blocks = re.split(r'(?=^### .+)', content, flags=re.MULTILINE)
        idx = 0
        for block in blocks:
            m = re.match(r'^### (.+?)(?:\s*—\s*(\d{4}-\d{2}-\d{2}))?\s*(?:\(.+?\))?\s*(?:\[PROMOTED\])?\s*(?:\*\*.+?\*\*)?\s*$',
                         block, re.MULTILINE)
            if not m:
                continue
            idx += 1
            title = m.group(1).strip()
            date = m.group(2)
            promoted = '[PROMOTED]' in block

            # M2: Check explicit status marker first
            status_match = re.search(r'<!--\s*status:\s*(active|promoted|obsolete|superseded|deprecated)\s*-->', block)
            if status_match:
                status = status_match.group(1)
            elif promoted:
                status = 'promoted'
            else:
                status = 'active'

            # Also detect "[部分否定]" as a signal
            if re.search(r'\[部分否定', block):
                # Still active but flagged — keep active, add to summary
                pass

            node_id = f"ECR-L{idx:02d}"
            node = {
                'id': node_id,
                'node_type': 'learning',
                'project': 'ecr-ecn',
                'status': status,
                'target': title[:80],
                'summary': title[:120],
                'refs_skill': None,
                'refs_db': None,
                'affects_project': None,
                'created_date': date,
            }
            nodes.append(node)

            # Cross-references
            d_refs = re.findall(r'(D-\d+)', block)
            for d_id in set(d_refs):
                edges.append({'source': node_id, 'target': d_id, 'relation': 'references'})

        return nodes, edges

    def _parse_meta(self, meta_str):
        """Parse <!-- kb: key=val, key=val --> meta string."""
        result = {}
        # Split by comma, but handle JSON arrays
        parts = re.findall(r'(\w+)\s*=\s*([^,]+(?:\[[^\]]*\])?)', meta_str)
        for key, val in parts:
            val = val.strip()
            if val.startswith('['):
                try:
                    result[key] = json.loads(val)
                except json.JSONDecodeError:
                    result[key] = [v.strip() for v in val.strip('[]').split('|')]
            elif '|' in val:
                result[key] = [v.strip() for v in val.split('|')]
            else:
                result[key] = val
        return result

    # ── Embedding ──────────────────────────────────────────────────────

    def sync_embeddings(self, force=False, quiet=False):
        """Vectorize nodes that don't have embeddings yet.

        Args:
            force: Re-embed all nodes (ignore existing embeddings)
            quiet: Suppress progress output

        Returns:
            (embedded_count, skipped_count, error_count)
        """
        eu = _get_embedding_utils()
        if not eu:
            if not quiet:
                print("WARN: embedding_utils not available, skipping embedding sync")
            return 0, 0, 0

        if not eu['is_ollama_available']():
            if not quiet:
                print("WARN: Ollama service not available, skipping embedding sync")
            return 0, 0, 0

        # Ensure table exists
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS node_embeddings (
                node_id TEXT PRIMARY KEY,
                embedding BLOB,
                embed_text TEXT,
                embed_model TEXT,
                updated_at TEXT,
                FOREIGN KEY (node_id) REFERENCES nodes(id)
            )
        """)

        # Get all active nodes
        nodes = self.conn.execute(
            "SELECT id, target, summary FROM nodes WHERE status='active'"
        ).fetchall()

        embedded = 0
        skipped = 0
        errors = 0
        model_name = 'qwen3-embedding:4b'

        for n in nodes:
            node_id = n['id']
            # Build embed text from target + summary
            parts = []
            if n['target']:
                parts.append(n['target'])
            if n['summary']:
                parts.append(n['summary'])
            embed_text = ' | '.join(parts)
            if not embed_text.strip():
                skipped += 1
                continue

            # Check if already embedded (unless force)
            if not force:
                existing = self.conn.execute(
                    "SELECT embed_text, embed_model FROM node_embeddings WHERE node_id=?",
                    (node_id,)
                ).fetchone()
                if existing and existing['embed_text'] == embed_text and existing['embed_model'] == model_name:
                    skipped += 1
                    continue

            # Get embedding
            try:
                vec = eu['get_embedding'](embed_text)
                blob = eu['embedding_to_blob'](vec)
                now = datetime.now().isoformat()
                self.conn.execute("""
                    INSERT INTO node_embeddings (node_id, embedding, embed_text, embed_model, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(node_id) DO UPDATE SET
                        embedding=excluded.embedding, embed_text=excluded.embed_text,
                        embed_model=excluded.embed_model, updated_at=excluded.updated_at
                """, (node_id, blob, embed_text, model_name, now))
                embedded += 1
                if not quiet and embedded % 20 == 0:
                    print(f"  embedded {embedded} nodes...", file=sys.stderr)
            except (ConnectionError, RuntimeError) as e:
                errors += 1
                if not quiet and errors <= 3:
                    print(f"  WARN: failed to embed {node_id}: {e}", file=sys.stderr)
                if errors >= 5:
                    if not quiet:
                        print(f"  Too many errors ({errors}), stopping embedding sync", file=sys.stderr)
                    break

        self.conn.commit()

        # Clean up embeddings for deleted/superseded nodes
        self.conn.execute("""
            DELETE FROM node_embeddings
            WHERE node_id NOT IN (SELECT id FROM nodes WHERE status='active')
        """)
        self.conn.commit()

        if not quiet:
            print(f"embedding sync: {embedded} embedded, {skipped} skipped, {errors} errors")
        return embedded, skipped, errors

    def related_semantic(self, query_text, top_k=10, threshold=0.3, fmt='line'):
        """Semantic search across all embedded nodes using cosine similarity.

        Args:
            query_text: Natural language query
            top_k: Max results to return
            threshold: Minimum cosine similarity
            fmt: Output format (line/ids/full)

        Returns:
            Formatted results string, or falls back to LIKE-based related()
        """
        eu = _get_embedding_utils()
        if not eu or not eu['is_ollama_available']():
            # Fallback to keyword matching
            return self.related(target=query_text, fmt=fmt) + "\n(fallback: keyword match, Ollama unavailable)"

        # Check if embeddings exist
        count = self.conn.execute("SELECT COUNT(*) as c FROM node_embeddings").fetchone()
        if not count or count['c'] == 0:
            return self.related(target=query_text, fmt=fmt) + "\n(fallback: keyword match, no embeddings)"

        try:
            query_vec = eu['get_embedding'](query_text)
        except (ConnectionError, RuntimeError):
            return self.related(target=query_text, fmt=fmt) + "\n(fallback: keyword match, embedding failed)"

        # Load all embeddings and compute similarity
        rows = self.conn.execute("""
            SELECT ne.node_id, ne.embedding, n.*
            FROM node_embeddings ne
            JOIN nodes n ON ne.node_id = n.id
            WHERE n.status = 'active'
        """).fetchall()

        scored = []
        for row in rows:
            vec = eu['blob_to_embedding'](row['embedding'])
            sim = eu['cosine_similarity'](query_vec, vec)
            if sim >= threshold:
                scored.append((sim, row))

        scored.sort(key=lambda x: x[0], reverse=True)
        scored = scored[:top_k]

        if not scored:
            return f"No semantic matches for '{query_text}' (threshold={threshold})"

        lines = []
        for sim, row in scored:
            if fmt == 'ids':
                lines.append(row['id'])
            elif fmt == 'full':
                lines.append(f"{row['id']} | sim={sim:.3f} | {row['status']} | {row['project']} | {row['target']}")
                lines.append(f"  summary: {row['summary']}")
                if row['refs_skill']:
                    lines.append(f"  refs_skill: {row['refs_skill']}")
            else:  # line
                lines.append(f"{row['id']} | sim={sim:.3f} | {row['target'][:50] if row['target'] else ''} | {row['summary'][:60] if row['summary'] else ''}")

        if fmt == 'ids':
            return ','.join(lines)
        return '\n'.join(lines)

    # ── Queries ───────────────────────────────────────────────────────

    def active(self, project=None, fmt='line'):
        """List active decisions."""
        sql = "SELECT * FROM nodes WHERE status='active' AND node_type='decision'"
        params = []
        if project:
            sql += " AND project LIKE ?"
            params.append(f"%{project}%")
        sql += " ORDER BY id"
        rows = self.conn.execute(sql, params).fetchall()
        return self._format(rows, fmt)

    def trace(self, node_id, fmt='line'):
        """Trace a node's relationships."""
        # Get the node itself
        node = self.conn.execute("SELECT * FROM nodes WHERE id=?", (node_id,)).fetchone()
        if not node:
            return f"Node {node_id} not found"

        # Get edges
        out_edges = self.conn.execute(
            "SELECT e.*, n.summary FROM edges e LEFT JOIN nodes n ON e.target_id=n.id WHERE e.source_id=?",
            (node_id,)
        ).fetchall()
        in_edges = self.conn.execute(
            "SELECT e.*, n.summary FROM edges e LEFT JOIN nodes n ON e.source_id=n.id WHERE e.target_id=?",
            (node_id,)
        ).fetchall()

        lines = [self._format_node(node, fmt)]
        if out_edges:
            lines.append("  outgoing:")
            for e in out_edges:
                lines.append(f"    → {e['relation']}: {e['target_id']} ({e['summary'] or ''})")
        if in_edges:
            lines.append("  incoming:")
            for e in in_edges:
                lines.append(f"    ← {e['relation']}: {e['source_id']} ({e['summary'] or ''})")
        return '\n'.join(lines)

    def related(self, target=None, skill=None, db=None, fmt='line'):
        """Find related nodes by target topic, skill reference, or db reference."""
        conditions = []
        params = []

        if target:
            conditions.append("(target LIKE ? OR summary LIKE ?)")
            params.extend([f"%{target}%", f"%{target}%"])
        if skill:
            conditions.append("refs_skill LIKE ?")
            params.append(f"%{skill}%")
        if db:
            conditions.append("refs_db LIKE ?")
            params.append(f"%{db}%")

        if not conditions:
            return "No filter specified"

        sql = f"SELECT * FROM nodes WHERE {' OR '.join(conditions)} ORDER BY id"
        rows = self.conn.execute(sql, params).fetchall()
        return self._format(rows, fmt)

    def validate(self, quiet=False, strict=False):
        """Check for consistency issues.

        Args:
            quiet: Only show warnings (skip info)
            strict: Also check meta line coverage and lifecycle invariants
        """
        issues = []

        # 1. Supersedes target not marked superseded (ERROR)
        edges = self.conn.execute(
            "SELECT source_id, target_id FROM edges WHERE relation='supersedes'"
        ).fetchall()
        for e in edges:
            target_node = self.conn.execute(
                "SELECT status FROM nodes WHERE id=?", (e['target_id'],)
            ).fetchone()
            if target_node and target_node['status'] != 'superseded':
                issues.append(f"ERROR: {e['source_id']} supersedes {e['target_id']}, but {e['target_id']} status={target_node['status']} (should be superseded)")

        # 2. Multiple active decisions on same target (WARN — upgraded from INFO)
        #    2a: Exact match
        dupes = self.conn.execute("""
            SELECT target, GROUP_CONCAT(id) as ids, COUNT(*) as cnt
            FROM nodes
            WHERE status='active' AND node_type='decision' AND target != '' AND target IS NOT NULL
            GROUP BY target HAVING cnt > 1
        """).fetchall()
        for d in dupes:
            issues.append(f"WARN: Multiple active decisions on target '{d['target']}': {d['ids']}")

        #    2b: L2 — Fuzzy match (different wording, same topic)
        active_decisions = self.conn.execute(
            "SELECT id, target FROM nodes WHERE status='active' AND node_type='decision' AND target IS NOT NULL AND target != ''"
        ).fetchall()
        reported_pairs = set()
        for i, a in enumerate(active_decisions):
            conflicts = self.check_conflict(a['target'], threshold=0.5)
            for did, target, score in conflicts:
                if did != a['id']:
                    pair = tuple(sorted([a['id'], did]))
                    if pair not in reported_pairs:
                        # Skip exact target matches (already reported above)
                        if a['target'] != target:
                            if self._has_semantic_overlap_suppress_edge(a['id'], did):
                                continue
                            reported_pairs.add(pair)
                            issues.append(f"WARN: Possible semantic overlap ({score}): {a['id']}({a['target'][:30]}) <-> {did}({target[:30]})")

        # 3. refs_skill pointing to non-existent skills
        base = self.db_path.parent.parent.parent.parent / '.claude'
        existing_skills = set()
        for skills_dir in [base / 'skills', base / 'skills-on-demand']:
            if skills_dir.exists():
                existing_skills |= {p.name for p in skills_dir.iterdir() if p.is_dir()}

        skill_nodes = self.conn.execute(
            "SELECT id, refs_skill FROM nodes WHERE refs_skill IS NOT NULL"
        ).fetchall()
        for n in skill_nodes:
            try:
                refs = json.loads(n['refs_skill'])
                for s in refs:
                    skill_name = s.split(':')[0]  # handle "process-bom-semantics:R4"
                    if skill_name not in existing_skills:
                        issues.append(f"WARN: {n['id']} references non-existent skill '{skill_name}'")
            except (json.JSONDecodeError, TypeError):
                pass

        # 4. Orphan nodes (no edges)
        orphans = self.conn.execute("""
            SELECT n.id FROM nodes n
            WHERE n.node_type = 'decision'
            AND NOT EXISTS (SELECT 1 FROM edges e WHERE e.source_id = n.id OR e.target_id = n.id)
        """).fetchall()
        if orphans and not quiet:
            orphan_ids = [o['id'] for o in orphans]
            issues.append(f"INFO: {len(orphan_ids)} orphan decisions (no edges): {','.join(orphan_ids[:10])}{'...' if len(orphan_ids) > 10 else ''}")

        # 5. Superseded decisions without a successor (WARN)
        superseded_nodes = self.conn.execute(
            "SELECT id FROM nodes WHERE status='superseded' AND node_type='decision'"
        ).fetchall()
        for n in superseded_nodes:
            successor = self.conn.execute(
                "SELECT source_id FROM edges WHERE target_id=? AND relation='supersedes'",
                (n['id'],)
            ).fetchone()
            if not successor:
                issues.append(f"WARN: {n['id']} is superseded but no successor found (missing supersedes edge)")

        # 6. L3: TTL — decisions with review_by date that have expired
        today = datetime.now().strftime('%Y-%m-%d')
        if DECISIONS_PATH.exists():
            dec_content = DECISIONS_PATH.read_text(encoding='utf-8')
            for block in re.split(r'(?=^### D-\d+)', dec_content, flags=re.MULTILINE):
                id_match = re.match(r'^### (D-\d+)', block)
                if not id_match:
                    continue
                did = id_match.group(1)
                review_match = re.search(r'review_by=(\d{4}-\d{2}-\d{2})', block)
                if review_match:
                    review_date = review_match.group(1)
                    # Check if this decision is still active
                    status_match = re.search(r'status=(active|superseded|deprecated)', block)
                    status = status_match.group(1) if status_match else 'active'
                    if status == 'active' and review_date < today:
                        issues.append(f"WARN: {did} review_by={review_date} has EXPIRED — needs review or update")

        # 7. Meta line coverage check (strict mode or always for recent)
        if strict or not quiet:
            decisions_path = self.kb_root / 'decisions.md'
            if decisions_path.exists():
                content = decisions_path.read_text(encoding='utf-8')
                blocks = re.split(r'(?=^### D-\d+)', content, flags=re.MULTILINE)
                all_ids = []
                missing_meta_ids = []
                for block in blocks:
                    m = re.match(r'^### (D-(\d+))', block)
                    if not m:
                        continue
                    all_ids.append(int(m.group(2)))
                    if not re.search(r'<!--\s*kb:', block):
                        missing_meta_ids.append(int(m.group(2)))

                if all_ids:
                    total = len(all_ids)
                    missing = len(missing_meta_ids)
                    pct = (total - missing) / total * 100

                    # Recent 30 decisions should all have meta
                    recent_threshold = sorted(all_ids)[-30] if len(all_ids) >= 30 else sorted(all_ids)[0]
                    recent_missing = [f"D-{n:03d}" for n in missing_meta_ids if n >= recent_threshold]

                    if recent_missing and strict:
                        issues.append(f"WARN: Recent decisions missing meta: {', '.join(recent_missing[:10])}")

                    if not quiet:
                        issues.append(f"INFO: Meta coverage: {total - missing}/{total} ({pct:.0f}%)")

        if not issues:
            if not quiet:
                print("OK: No issues found")
            return 0

        output = '\n'.join(issues)
        if not quiet:
            print(output)
        else:
            # In quiet mode, only print warnings and errors (not info)
            serious = [i for i in issues if i.startswith(('WARN', 'ERROR'))]
            if serious:
                print('\n'.join(serious))
        return 2 if any(i.startswith('ERROR') for i in issues) else (1 if any(i.startswith('WARN') for i in issues) else 0)

    def impacts(self, project=None, skill=None, fmt='line'):
        """Find nodes that affect a given project or skill."""
        conditions = []
        params = []

        if project:
            conditions.append("affects_project LIKE ?")
            params.append(f"%{project}%")
        if skill:
            conditions.append("refs_skill LIKE ?")
            params.append(f"%{skill}%")

        if not conditions:
            return "No filter specified"

        sql = f"SELECT * FROM nodes WHERE {' OR '.join(conditions)} ORDER BY id"
        rows = self.conn.execute(sql, params).fetchall()
        return self._format(rows, fmt)

    # ── L2: Target Conflict Detection ─────────────────────────────────

    def check_conflict(self, target_text, threshold=0.4):
        """L2: Check if a new decision's target conflicts with existing active decisions.

        Uses keyword overlap (Jaccard similarity on CJK + alphanumeric tokens)
        to find semantically similar targets even with different wording.

        Args:
            target_text: The target text of the proposed new decision
            threshold: Similarity threshold (0.0-1.0). Default 0.4 catches
                       "family_grouping" vs "分組邏輯" if they share tokens.

        Returns:
            List of (decision_id, target, similarity_score) tuples
        """
        # Tokenize: split on non-alphanumeric/non-CJK, keep CJK chars as individual tokens
        def tokenize(text):
            if not text:
                return set()
            # Extract alphanumeric words
            alpha_tokens = {
                tok for tok in re.findall(r'[a-zA-Z0-9_]+', text.lower())
                if tok not in SEMANTIC_TOKEN_STOPWORDS
            }
            # Extract CJK characters individually (each is a "word")
            cjk_tokens = set(re.findall(r'[\u4e00-\u9fff]', text))
            return alpha_tokens | cjk_tokens

        new_tokens = tokenize(target_text)
        if not new_tokens:
            return []

        # Get all active decisions
        rows = self.conn.execute(
            "SELECT id, target, summary FROM nodes WHERE status='active' AND node_type='decision' AND target IS NOT NULL"
        ).fetchall()

        conflicts = []
        for row in rows:
            existing_tokens = tokenize(row['target'])
            if not existing_tokens:
                continue

            # Jaccard similarity
            intersection = new_tokens & existing_tokens
            union = new_tokens | existing_tokens
            similarity = len(intersection) / len(union) if union else 0

            # Also check if new target is substring of existing or vice versa
            target_lower = (row['target'] or '').lower()
            new_lower = target_text.lower()
            if new_lower in target_lower or target_lower in new_lower:
                similarity = max(similarity, 0.6)

            if similarity >= threshold:
                conflicts.append((row['id'], row['target'], round(similarity, 2)))

        # Sort by similarity descending
        conflicts.sort(key=lambda x: x[2], reverse=True)
        return conflicts

    # ── Active Summary Generator ─────────────────────────────────────

    def generate_active_summary(self, output_path=None, project=None):
        """Generate a compact active rules summary for AI consumption.

        Produces a markdown file with only currently active decisions,
        grouped by project and topic, with superseded/deprecated filtered out.
        This is the "noise-reduced" context file that AI should read instead
        of the full decisions.md.

        Returns: (output_path, stats_dict)
        """
        if output_path is None:
            output_path = self.kb_root / 'active_rules_summary.md'
        else:
            output_path = Path(output_path)

        # Fetch active decisions. Project scope must match both locally-owned
        # decisions and cross-project decisions that explicitly affect this project.
        sql = "SELECT * FROM nodes WHERE status='active' AND node_type='decision'"
        params = []
        if project:
            sql += " AND (project = ? OR affects_project LIKE ?)"
            params.extend([project, f"%{project}%"])
        sql += " ORDER BY id"
        decisions = self.conn.execute(sql, params).fetchall()

        # Fetch active rules
        rules = self.conn.execute(
            "SELECT * FROM nodes WHERE status='active' AND node_type='rule' ORDER BY id"
        ).fetchall()

        # Fetch superseded decisions (for cross-reference)
        superseded = self.conn.execute(
            "SELECT id, target FROM nodes WHERE status='superseded' AND node_type='decision' ORDER BY id"
        ).fetchall()

        # Group decisions by project
        by_project = {}
        for d in decisions:
            proj = d['project'] or 'general'
            if proj not in by_project:
                by_project[proj] = []
            by_project[proj].append(d)

        # Build markdown
        lines = [
            '# Active Rules Summary',
            '',
            f'> Auto-generated by kb_index.py on {datetime.now().strftime("%Y-%m-%d %H:%M")}',
            f'> Source: decisions.md ({len(decisions)} active / {len(superseded)} superseded)',
            '> Do NOT edit this file directly. Edit decisions.md and re-run:',
            '>   python shared/tools/kb_index.py generate-summary',
            '',
            '---',
            '',
        ]

        # Superseded summary (compact)
        if superseded:
            lines.append(f'## Superseded ({len(superseded)})')
            lines.append('')
            for s in superseded:
                # Find successor
                succ = self.conn.execute(
                    "SELECT source_id FROM edges WHERE target_id=? AND relation='supersedes'",
                    (s['id'],)
                ).fetchone()
                succ_str = f" -> {succ['source_id']}" if succ else " (no successor)"
                lines.append(f'- ~~{s["id"]}~~{succ_str}: {s["target"][:60] if s["target"] else ""}')
            lines.append('')
            lines.append('---')
            lines.append('')

        # Active decisions by project
        for proj, decs in sorted(by_project.items()):
            lines.append(f'## {proj} ({len(decs)} active)')
            lines.append('')

            for d in decs:
                did = d['id']
                target = d['target'][:70] if d['target'] else ''
                summary = d['summary'][:100] if d['summary'] else ''

                # Get refs
                refs_parts = []
                if d['refs_skill']:
                    try:
                        skills = json.loads(d['refs_skill'])
                        refs_parts.append(f"skill:{','.join(skills)}")
                    except (json.JSONDecodeError, TypeError):
                        pass
                if d['refs_db']:
                    try:
                        dbs = json.loads(d['refs_db'])
                        refs_parts.append(f"db:{','.join(dbs)}")
                    except (json.JSONDecodeError, TypeError):
                        pass

                refs_str = f" [{'; '.join(refs_parts)}]" if refs_parts else ""

                lines.append(f'### {did} -- {target}')
                lines.append(f'{summary}{refs_str}')
                lines.append('')

            lines.append('---')
            lines.append('')

        # Active rules section
        if rules:
            lines.append(f'## ECR Rules ({len(rules)} active)')
            lines.append('')
            for r in rules:
                lines.append(f'- **{r["id"]}**: {r["summary"][:80] if r["summary"] else ""}')
            lines.append('')

        content = '\n'.join(lines)
        output_path.write_text(content, encoding='utf-8')

        stats = {
            'active_decisions': len(decisions),
            'superseded_decisions': len(superseded),
            'active_rules': len(rules),
            'output_path': str(output_path),
            'output_size': len(content),
        }
        return str(output_path), stats

    # ── Index Generation ─────────────────────────────────────────────

    def generate_index(self, output_path=None):
        """Auto-generate shared/kb/_index.md by scanning skills, projects, tools, and KB.

        Returns: (output_path, stats_dict)
        """
        import ast
        try:
            import yaml
        except ImportError:
            yaml = None

        if output_path is None:
            output_path = self.kb_root / '_index.md'
        else:
            output_path = Path(output_path)

        today = datetime.now().strftime('%Y-%m-%d')

        # ── 1. Scan skills (both directories, deduplicated) ──
        skill_rows = []
        seen_skills = set()
        idx = 0
        for skills_dir in [ROOT / '.claude' / 'skills', ROOT / '.claude' / 'skills-on-demand']:
            if not skills_dir.is_dir():
                continue
            for sd in sorted(skills_dir.iterdir()):
                if not sd.is_dir() or sd.name in seen_skills:
                    continue
                seen_skills.add(sd.name)
                idx += 1
                name = sd.name
                rules_count = '-'
                lines = '-'
                triggers_str = ''
                updated = '-'
                yaml_path = sd / '.skill.yaml'
                skill_md = sd / 'SKILL.md'
                if yaml_path.exists() and yaml is not None:
                    try:
                        with open(yaml_path, encoding='utf-8') as f:
                            y = yaml.safe_load(f) or {}
                        rules_count = y.get('rules_count', '-')
                        updated = y.get('last_updated', '-')
                        t = y.get('triggers', {})
                        if isinstance(t, dict):
                            kws = (t.get('keywords') or [])[:5]
                            triggers_str = ', '.join(str(k) for k in kws)
                    except Exception:
                        pass
                if skill_md.exists():
                    try:
                        lines = sum(1 for _ in open(skill_md, encoding='utf-8'))
                    except Exception:
                        pass
                skill_rows.append((idx, name, rules_count, lines, triggers_str, updated))

        # ── 2. Scan dynamic KB ──
        dynamic_dir = self.kb_root / 'dynamic'
        dynamic_rows = []
        file_desc = {
            'column_semantics.md': ('欄位語意字典', '~15'),
            'ecr_ecn_rules.md': ('ECR/ECN 業務規則', '3'),
            'learning_notes.md': ('學習筆記（ECR-L, BOM-L, STD-L）', '10'),
        }
        if dynamic_dir.is_dir():
            for md_file in sorted(dynamic_dir.glob('*.md')):
                try:
                    content = md_file.read_text(encoding='utf-8')
                    count = len(re.findall(r'^###\s', content, re.MULTILINE))
                except Exception:
                    count = 0
                desc, promoted = file_desc.get(md_file.name, (md_file.stem, '-'))
                dynamic_rows.append((md_file.name, count, promoted, desc))
            # Also list directories
            for sub in sorted(dynamic_dir.iterdir()):
                if sub.is_dir() and not sub.name.startswith('_'):
                    items = len(list(sub.glob('*')))
                    desc, promoted = file_desc.get(sub.name + '/', (sub.name, '-'))
                    dynamic_rows.append((sub.name + '/', items, promoted, desc))

        # ── 3. Scan decisions ──
        decisions_path = self.kb_root / 'decisions.md'
        d_range = 'D-001~D-???'
        if decisions_path.exists():
            try:
                dc = decisions_path.read_text(encoding='utf-8')
                nums = sorted(set(int(m) for m in re.findall(r'###\s*D-(\d+)', dc)))
                if nums:
                    d_range = f'D-{nums[0]:03d}~D-{nums[-1]:03d}+'
            except Exception:
                pass

        # ── 4. Scan projects ──
        projects_dir = ROOT / 'projects'
        project_rows = []
        if projects_dir.is_dir():
            for pd in sorted(projects_dir.iterdir()):
                if not pd.is_dir() or pd.name.startswith('_'):
                    continue
                db_name = '-'
                db_dir = pd / 'workspace' / 'db'
                if db_dir.is_dir():
                    dbs = list(db_dir.glob('*.db')) + list(db_dir.glob('*.sqlite'))
                    if dbs:
                        db_name = dbs[0].name
                title = pd.name
                pm = pd / 'project.md'
                if pm.exists():
                    try:
                        for line in open(pm, encoding='utf-8'):
                            if line.startswith('# '):
                                title = line[2:].strip()
                                break
                    except Exception:
                        pass
                project_rows.append((pd.name, f'projects/{pd.name}/', db_name, title))

        # ── 5. Scan tools ──
        tools_dir = ROOT / 'shared' / 'tools'
        tool_rows = []
        if tools_dir.is_dir():
            for py in sorted(tools_dir.rglob('*.py')):
                if '__pycache__' in str(py) or py.name == '__init__.py':
                    continue
                rel = str(py.relative_to(ROOT)).replace('\\', '/')
                try:
                    tree = ast.parse(py.read_text(encoding='utf-8'))
                    doc = ast.get_docstring(tree) or ''
                    desc = doc.split('\n')[0].strip()[:80] if doc else py.stem
                except Exception:
                    desc = py.stem
                # Clean name
                display_name = py.stem
                tool_rows.append((display_name, rel, desc))

        # ── Build markdown ──
        L = []
        L.append(f'# 知識索引 — Agent Office v3.1')
        L.append('')
        L.append(f'> 統一知識路由。所有知識條目一覽。')
        L.append(f'> 最後更新：{today}')
        L.append(f'> 由 `kb_index.py generate-index` 自動產生，請勿手動編輯。')
        L.append('')
        L.append('---')
        L.append('')

        # Skills table
        L.append('## Layer 1：Skills（.claude/skills-on-demand/，全部按需載入）')
        L.append('')
        L.append('每個 SKILL.md frontmatter 含 `triggers` 觸發詞列表，語意搜尋命中後按需 Read。')
        L.append('')
        L.append('| # | Skill | 規則數 | 行數 | 核心觸發詞 | 最後更新 |')
        L.append('|---|-------|--------|------|-----------|---------|')
        for idx, name, rules, lines, triggers, updated in skill_rows:
            L.append(f'| {idx} | **{name}** | {rules} | {lines} | {triggers} | {updated} |')
        L.append('')

        # Static rules detail block
        L.append(_RULES_DETAIL_TEMPLATE.rstrip())
        L.append('')
        L.append('---')
        L.append('')

        # Dynamic KB
        L.append('## Layer 2：動態知識（shared/kb/dynamic/）')
        L.append('')
        L.append('| 文件 | 條目數 | 已升級 | 說明 |')
        L.append('|------|--------|--------|------|')
        for fname, count, promoted, desc in dynamic_rows:
            L.append(f'| {fname} | {count} | {promoted} | {desc} |')
        L.append('')
        L.append('---')
        L.append('')

        # External standards (static)
        L.append(_EXTERNAL_STANDARDS_TEMPLATE.rstrip())
        L.append('')
        L.append('---')
        L.append('')

        # Decisions & memory
        L.append('## 決策與記憶')
        L.append('')
        L.append('| 文件 | 路徑 | 說明 |')
        L.append('|------|------|------|')
        L.append(f'| 決策日誌 | shared/kb/decisions.md | {d_range} |')
        L.append('| 中場記憶 | shared/kb/memory/*.md | 自動快照 |')
        L.append('')
        L.append('---')
        L.append('')

        # Projects
        L.append('## 專案清單')
        L.append('')
        L.append('| 專案 | 路徑 | DB | 說明 |')
        L.append('|------|------|-----|------|')
        for name, path, db, desc in project_rows:
            L.append(f'| {name} | {path} | {db} | {desc} |')
        L.append('')
        L.append('---')
        L.append('')

        # Tools
        L.append('## 共用工具')
        L.append('')
        L.append('| 工具 | 路徑 | 說明 |')
        L.append('|------|------|------|')
        for name, path, desc in tool_rows:
            L.append(f'| {name} | {path} | {desc} |')
        L.append('')
        L.append('---')
        L.append('')

        # Upgrade history (static)
        L.append(_UPGRADE_HISTORY_TEMPLATE.rstrip())
        L.append('')

        content = '\n'.join(L)
        output_path.write_text(content, encoding='utf-8')

        stats = {
            'skills': len(skill_rows),
            'dynamic_entries': sum(r[1] for r in dynamic_rows),
            'projects': len(project_rows),
            'tools': len(tool_rows),
            'decisions': d_range,
            'output_size': len(content),
        }
        return str(output_path), stats

    # ── Formatters ────────────────────────────────────────────────────

    def _format(self, rows, fmt):
        if fmt == 'ids':
            return ','.join(r['id'] for r in rows)
        elif fmt == 'full':
            return '\n\n'.join(self._format_node(r, 'full') for r in rows)
        else:  # line
            return '\n'.join(self._format_node(r, 'line') for r in rows)

    def _format_node(self, row, fmt):
        if fmt == 'ids':
            return row['id']
        elif fmt == 'full':
            parts = [f"{row['id']} | {row['status']} | {row['project']} | {row['target']}"]
            parts.append(f"  summary: {row['summary']}")
            if row['refs_skill']:
                parts.append(f"  refs_skill: {row['refs_skill']}")
            if row['refs_db']:
                parts.append(f"  refs_db: {row['refs_db']}")
            if row['affects_project']:
                parts.append(f"  affects: {row['affects_project']}")
            return '\n'.join(parts)
        else:  # line
            return f"{row['id']} | {row['status']} | {row['target'][:50] if row['target'] else ''} | {row['summary'][:60] if row['summary'] else ''}"


def main():
    """EVO-016 deprecation shim: delegate all CLI usage to kb.py."""
    import subprocess as _subprocess
    # Force UTF-8 on Windows
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, OSError):
            sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', errors='replace', closefd=False)
            sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', errors='replace', closefd=False)

    sys.stderr.write(
        "[DEPRECATED] kb_index.py CLI is replaced by kb.py in EVO-016. "
        "Forwarding to kb.py.\n"
    )

    kb_script = str(Path(__file__).resolve().parent / 'kb.py')
    result = _subprocess.run(
        [sys.executable, kb_script, *sys.argv[1:]],
        cwd=str(Path(__file__).resolve().parent.parent.parent),
    )
    sys.exit(result.returncode)

    # ── Below kept as no-op to keep byte-compat if anything still reaches here ──
    parser = argparse.ArgumentParser(description='Knowledge Base Index (deprecated)')
    sub = parser.add_subparsers(dest='command')

    # sync
    p_sync = sub.add_parser('sync', help='Sync .md files to SQLite index')
    p_sync.add_argument('--quiet', action='store_true')
    p_sync.add_argument('--embed', action='store_true', help='Also sync embeddings (requires Ollama)')
    p_sync.add_argument('--embed-force', action='store_true', help='Force re-embed all nodes')

    # active
    p_active = sub.add_parser('active', help='List active decisions')
    p_active.add_argument('--project', type=str, default=None)
    p_active.add_argument('--fmt', choices=['line', 'ids', 'full'], default='line')

    # trace
    p_trace = sub.add_parser('trace', help='Trace a node relationships')
    p_trace.add_argument('node_id', type=str)
    p_trace.add_argument('--fmt', choices=['line', 'ids', 'full'], default='line')

    # related
    p_related = sub.add_parser('related', help='Find related nodes')
    p_related.add_argument('--target', type=str, default=None)
    p_related.add_argument('--skill', type=str, default=None)
    p_related.add_argument('--db', type=str, default=None)
    p_related.add_argument('--semantic', action='store_true', help='Use embedding semantic search (requires Ollama)')
    p_related.add_argument('--top-k', type=int, default=10, help='Max results for semantic search')
    p_related.add_argument('--threshold', type=float, default=0.3, help='Min similarity for semantic search')
    p_related.add_argument('--fmt', choices=['line', 'ids', 'full'], default='line')

    # validate
    p_val = sub.add_parser('validate', help='Check consistency')
    p_val.add_argument('--quiet', action='store_true')
    p_val.add_argument('--strict', action='store_true', help='Also check meta coverage for recent decisions')

    # impacts
    p_imp = sub.add_parser('impacts', help='Find impacting nodes')
    p_imp.add_argument('--project', type=str, default=None)
    p_imp.add_argument('--skill', type=str, default=None)
    p_imp.add_argument('--fmt', choices=['line', 'ids', 'full'], default='line')

    # check-conflict (L2)
    p_conflict = sub.add_parser('check-conflict', help='Check if a target conflicts with existing active decisions')
    p_conflict.add_argument('target', type=str, help='Target text to check')
    p_conflict.add_argument('--threshold', type=float, default=0.4, help='Similarity threshold (0.0-1.0)')

    # generate-summary
    p_gen = sub.add_parser('generate-summary', help='Generate active rules summary markdown')
    p_gen.add_argument('--project', type=str, default=None, help='Filter by project')
    p_gen.add_argument('--output', type=str, default=None, help='Output file path')

    # generate-index
    p_idx = sub.add_parser('generate-index', help='Auto-generate _index.md by scanning skills, projects, tools, KB')
    p_idx.add_argument('--output', type=str, default=None, help='Output file path')

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    kb = KBIndex()
    try:
        if args.command == 'sync':
            kb.sync(quiet=args.quiet)
            if args.embed or args.embed_force:
                kb.sync_embeddings(force=args.embed_force, quiet=args.quiet)
        elif args.command == 'active':
            print(kb.active(project=args.project, fmt=args.fmt))
        elif args.command == 'trace':
            print(kb.trace(args.node_id, fmt=args.fmt))
        elif args.command == 'related':
            if args.semantic and args.target:
                print(kb.related_semantic(
                    query_text=args.target, top_k=args.top_k,
                    threshold=args.threshold, fmt=args.fmt
                ))
            else:
                print(kb.related(target=args.target, skill=args.skill, db=args.db, fmt=args.fmt))
        elif args.command == 'validate':
            code = kb.validate(quiet=args.quiet, strict=getattr(args, 'strict', False))
            sys.exit(code)
        elif args.command == 'impacts':
            print(kb.impacts(project=args.project, skill=args.skill, fmt=args.fmt))
        elif args.command == 'check-conflict':
            kb.sync(quiet=True)
            conflicts = kb.check_conflict(args.target, threshold=args.threshold)
            if conflicts:
                print(f"POTENTIAL CONFLICTS for target '{args.target}':")
                for did, target, score in conflicts:
                    print(f"  {did} | similarity={score} | {target}")
                sys.exit(1)
            else:
                print(f"OK: No conflicts found for target '{args.target}'")
                sys.exit(0)
        elif args.command == 'generate-summary':
            path, stats = kb.generate_active_summary(
                output_path=getattr(args, 'output', None),
                project=getattr(args, 'project', None)
            )
            print(f"Generated: {path}")
            print(f"  Active decisions: {stats['active_decisions']}")
            print(f"  Superseded: {stats['superseded_decisions']}")
            print(f"  Active rules: {stats['active_rules']}")
            print(f"  Output size: {stats['output_size']} chars")
        elif args.command == 'generate-index':
            path, stats = kb.generate_index(
                output_path=getattr(args, 'output', None)
            )
            print(f"Generated: {path}")
            print(f"  Skills: {stats['skills']}")
            print(f"  Projects: {stats['projects']}")
            print(f"  Tools: {stats['tools']}")
            print(f"  Decisions: {stats['decisions']}")
            print(f"  Output size: {stats['output_size']} chars")
    finally:
        kb.close()


if __name__ == '__main__':
    main()
