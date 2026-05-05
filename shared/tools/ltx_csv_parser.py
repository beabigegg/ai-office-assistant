#!/usr/bin/env python3
"""
LTX CSV Parser — 可重用的 LTX 測試機 raw data 提取工具

功能：
  1. 解析 LTX 測試機輸出的 CSV 檔案（標頭元數據 + 欄位定義 + 量測數據）
  2. 自動偵測不同 TYPE 的測試參數（欄位數不同）
  3. 自動合併 _1, _2... 接續檔
  4. 提取規格上下限 (USL/LSL)
  5. 輸出到 SQLite（含元數據表 + 量測數據表 + 規格表）

使用方式：
  # 作為模組
  from ltx_csv_parser import LtxParser
  parser = LtxParser()
  result = parser.parse_file('path/to/LTX_xxx.csv')
  parser.parse_directory('path/to/data/', 'output.db')

  # 作為命令列工具
  python ltx_csv_parser.py --input <dir_or_file> --output <db_path> [--dry-run]

作者：Leader (auto-generated)
建立：2026-02-25
"""

import os
import re
import csv
import sqlite3
import argparse
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ─── 常數 ───────────────────────────────────────────────

META_COL_COUNT = 4            # 數據區前 4 欄: unit#, bin, category_no, category_name
BATCH_SIZE = 5000             # DB 寫入批次大小

# 用於動態搜索的關鍵字（col 3 的值）
KEY_STD_ITEM = 'Std. Item'
KEY_USER_ITEM = 'User Item'
KEY_UPPER = 'Upper'
KEY_LOWER = 'Lower'
KEY_TIME = 'Time'
KEY_MIN = 'Min.'
KEY_MAX = 'Max.'
KEY_AVE = 'Ave.'
KEY_CATEGORY = 'Category Name'  # 數據區標頭行的 col 3


@dataclass
class FileMetadata:
    """單一 CSV 檔案的元數據"""
    test_file_path: str = ''
    polarity: str = ''
    device_name: str = ''
    comment: str = ''
    lot_name: str = ''
    comment_lot: str = ''
    unit_station: str = ''
    day_time: str = ''
    source_file: str = ''

    # 從檔名解析的欄位
    device_type: str = ''      # e.g. BAS70SW-AU_R1_000A1-A
    tx_batch: str = ''         # e.g. TXS-16167
    ga_order: str = ''         # e.g. GA25092280
    ga_sub: str = ''           # e.g. A00-001
    test_datetime: str = ''    # e.g. 20251009054850


@dataclass
class ColumnSpec:
    """單一測試參數的規格定義"""
    index: int                 # 欄位在 CSV 中的位置 (0-based, 從 META_COL_COUNT 起)
    std_item: str = ''         # 標準項目名（含單位）
    user_item: str = ''        # 使用者定義的參數名
    upper: Optional[float] = None
    lower: Optional[float] = None
    conditions: list = field(default_factory=list)  # Condition 1-5
    time: Optional[float] = None


@dataclass
class ParseResult:
    """單一 lot 的解析結果"""
    metadata: FileMetadata = field(default_factory=FileMetadata)
    columns: list = field(default_factory=list)     # list[ColumnSpec]
    stats: dict = field(default_factory=dict)        # {min/max/ave: [values]}
    data_rows: list = field(default_factory=list)    # [{unit, bin, cat_no, cat_name, param1, ...}]
    total_units: int = 0
    source_files: list = field(default_factory=list)


class LtxParser:
    """LTX CSV 測試數據解析器"""

    # ─── 檔名解析 ──────────────────────────────────────

    @staticmethod
    def parse_filename(filepath: str) -> dict:
        """從 LTX 檔名解析元數據
        格式: LTX_{TYPE}_TXS-{batch}_{GA}-{sub}_{datetime}[_N].csv
        """
        fname = os.path.basename(filepath)
        info = {'is_continuation': False, 'continuation_index': 0}

        # 檢查是否為接續檔 (_1, _2, ...)
        # 接續檔後綴為 1-2 位數字，不是 14 位 timestamp
        m_cont = re.match(r'(.+)_(\d{1,2})\.csv$', fname)
        if m_cont:
            info['is_continuation'] = True
            info['continuation_index'] = int(m_cont.group(2))
            fname_base = m_cont.group(1)
        else:
            fname_base = fname.rsplit('.', 1)[0]

        # 解析主要欄位
        # LTX_BAS70SW-AU_R1_000A1-A_TXS-16167_GA25092280-A00-001_20251009054850        (TXS-: 晶片批號)
        # LTX_BAS70WS-AU_R1_000A1-A_TXS-16321_GA25112287-A00-003-01_20251203100513
        # LTX_BCP56-16-AU_R2_007A1-1_TXTS-0553_GA26032188-A00-001_20260403212228       (TXTS-: 測試批，BCP56 TRA 系列)
        m = re.match(r'LTX_(.+?)_(TXT?S-\d+)_(GA\d+)-([\w-]+)_(\d{10,})', fname_base)
        if m:
            info['device_type'] = m.group(1)
            info['tx_batch'] = m.group(2)
            info['ga_order'] = m.group(3)
            info['ga_sub'] = m.group(4)
            info['test_datetime'] = m.group(5)
        else:
            logger.warning(f'無法解析檔名: {fname}')
            info['device_type'] = fname_base

        return info

    # ─── 單檔解析 ──────────────────────────────────────

    @staticmethod
    def _safe_float(val: str) -> Optional[float]:
        """安全轉換浮點數"""
        if val is None:
            return None
        val = val.strip()
        if val == '' or val == '-':
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    def _find_row(self, all_rows: list, col3_key: str, start: int = 0) -> int:
        """在 all_rows 中搜索 col[3] == key 的行，返回 0-based index，找不到返回 -1"""
        for i in range(start, len(all_rows)):
            row = all_rows[i]
            if len(row) > 3 and row[3].strip() == col3_key:
                return i
        return -1

    def parse_file(self, filepath: str, encoding: str = None) -> ParseResult:
        """解析單一 LTX CSV 檔案，返回 ParseResult

        動態搜索關鍵行（Std. Item, User Item, Upper, Lower 等），
        不依賴固定行號偏移，適應 Comment 多行等變體。
        """
        result = ParseResult()
        result.source_files.append(os.path.basename(filepath))

        # 偵測編碼
        if encoding is None:
            encoding = self._detect_encoding(filepath)

        with open(filepath, 'r', encoding=encoding, errors='replace') as f:
            reader = csv.reader(f)
            all_rows = list(reader)

        if len(all_rows) < 20:
            logger.warning(f'檔案行數不足: {filepath} ({len(all_rows)} rows)')
            return result

        # ── 解析標頭元數據（搜索到 Std. Item 之前的所有行）──
        meta = FileMetadata(source_file=os.path.basename(filepath))
        header_map = {
            'Test File Path': 'test_file_path',
            'Polarity': 'polarity',
            'Device Name': 'device_name',
            'Comment': 'comment',
            'Lot Name': 'lot_name',
            'Comment(Lot)': 'comment_lot',
            'Unit/Station': 'unit_station',
            'Day/Time': 'day_time',
        }

        # 找 Std. Item 行作為標頭結束的標記
        std_idx = self._find_row(all_rows, KEY_STD_ITEM)
        if std_idx < 0:
            logger.warning(f'找不到 Std. Item 行: {filepath}')
            return result

        # 掃描標頭行（Std. Item 之前）
        for i in range(std_idx):
            row = all_rows[i]
            if row and row[0].strip() in header_map:
                attr = header_map[row[0].strip()]
                vals = [c.strip() for c in row[2:] if c.strip()]
                setattr(meta, attr, ' '.join(vals) if vals else '')

        # 從檔名補充
        finfo = self.parse_filename(filepath)
        meta.device_type = finfo.get('device_type', '')
        meta.tx_batch = finfo.get('tx_batch', '')
        meta.ga_order = finfo.get('ga_order', '')
        meta.ga_sub = finfo.get('ga_sub', '')
        meta.test_datetime = finfo.get('test_datetime', '')
        result.metadata = meta

        # ── 動態定位關鍵行 ──
        user_idx = self._find_row(all_rows, KEY_USER_ITEM, std_idx)
        upper_idx = self._find_row(all_rows, KEY_UPPER, std_idx)
        lower_idx = self._find_row(all_rows, KEY_LOWER, std_idx)
        time_idx = self._find_row(all_rows, KEY_TIME, std_idx)
        min_idx = self._find_row(all_rows, KEY_MIN, std_idx)
        max_idx = self._find_row(all_rows, KEY_MAX, std_idx)
        ave_idx = self._find_row(all_rows, KEY_AVE, std_idx)
        cat_idx = self._find_row(all_rows, KEY_CATEGORY, std_idx)

        # Condition 行在 Lower 和 Time 之間
        cond_indices = []
        if lower_idx >= 0 and time_idx >= 0:
            for i in range(lower_idx + 1, time_idx):
                row = all_rows[i]
                if len(row) > 3 and row[3].strip().startswith('Condition'):
                    cond_indices.append(i)

        std_row = all_rows[std_idx] if std_idx >= 0 else []
        user_row = all_rows[user_idx] if user_idx >= 0 else []
        upper_row = all_rows[upper_idx] if upper_idx >= 0 else []
        lower_row = all_rows[lower_idx] if lower_idx >= 0 else []

        # 確定參數欄位數量 (從 col 4 開始)
        param_count = max(len(std_row), len(user_row)) - META_COL_COUNT
        if param_count <= 0:
            logger.warning(f'無測試參數: {filepath}')
            return result

        columns = []
        for i in range(param_count):
            col_idx = META_COL_COUNT + i
            spec = ColumnSpec(index=i)
            spec.std_item = std_row[col_idx].strip() if col_idx < len(std_row) else ''
            spec.user_item = user_row[col_idx].strip() if col_idx < len(user_row) else ''
            spec.upper = self._safe_float(upper_row[col_idx] if col_idx < len(upper_row) else '')
            spec.lower = self._safe_float(lower_row[col_idx] if col_idx < len(lower_row) else '')

            # Conditions
            conds = []
            for cr in cond_indices:
                cond_row = all_rows[cr]
                conds.append(cond_row[col_idx].strip() if col_idx < len(cond_row) else '')
            # 補齊到 5 個
            while len(conds) < 5:
                conds.append('')
            spec.conditions = conds

            # Time
            if time_idx >= 0:
                t_row = all_rows[time_idx]
                spec.time = self._safe_float(t_row[col_idx] if col_idx < len(t_row) else '')

            # 跳過完全空白的欄位
            if spec.user_item or spec.std_item:
                columns.append(spec)

        result.columns = columns

        # ── 解析統計行 ──
        for stat_name, row_idx in [('min', min_idx), ('max', max_idx), ('ave', ave_idx)]:
            if row_idx >= 0 and row_idx < len(all_rows):
                srow = all_rows[row_idx]
                vals = []
                for col in columns:
                    col_idx = META_COL_COUNT + col.index
                    vals.append(self._safe_float(srow[col_idx] if col_idx < len(srow) else ''))
                result.stats[stat_name] = vals

        # ── 解析量測數據（從 Category Name 標頭行之後開始）──
        data_start = (cat_idx + 1) if cat_idx >= 0 else (ave_idx + 2 if ave_idx >= 0 else std_idx + 15)

        data_rows = []
        for row_idx in range(data_start, len(all_rows)):
            row = all_rows[row_idx]
            if not row or not row[0].strip():
                continue

            unit_no = row[0].strip()
            try:
                int(unit_no)
            except ValueError:
                continue

            record = {
                'unit': int(unit_no),
                'bin_no': row[1].strip() if len(row) > 1 else '',
                'category_no': row[2].strip() if len(row) > 2 else '',
                'category_name': row[3].strip() if len(row) > 3 else '',
            }

            for col_spec in columns:
                col_idx = META_COL_COUNT + col_spec.index
                val = self._safe_float(row[col_idx] if col_idx < len(row) else '')
                record[col_spec.user_item] = val

            data_rows.append(record)

        result.data_rows = data_rows
        result.total_units = len(data_rows)
        return result

    @staticmethod
    def _detect_encoding(filepath: str) -> str:
        """偵測檔案編碼"""
        try:
            import chardet
            with open(filepath, 'rb') as f:
                raw = f.read(10000)
            det = chardet.detect(raw)
            enc = det.get('encoding', 'utf-8')
            # chardet 有時回傳 ascii, 但檔案可能有 Big5
            if enc and enc.lower() in ('ascii', 'iso-8859-1'):
                enc = 'utf-8'
            return enc or 'utf-8'
        except ImportError:
            return 'utf-8'

    # ─── 目錄掃描與合併 ──────────────────────────────────

    def scan_directory(self, dir_path: str) -> dict:
        """掃描目錄，將 LTX 檔案按 lot 分組（主檔 + 接續檔合併）

        Returns:
            {lot_key: [filepath1, filepath2_1, ...]}  按接續順序排列
        """
        groups = {}  # {base_key: [(cont_index, filepath)]}

        for root, dirs, files in os.walk(dir_path):
            for fname in sorted(files):
                if not fname.startswith('LTX_') or not fname.endswith('.csv'):
                    continue
                fpath = os.path.join(root, fname)
                finfo = self.parse_filename(fpath)

                # 建立 base key（不含接續編號）
                base_name = fname
                if finfo['is_continuation']:
                    # 移除 _N 後綴
                    base_name = re.sub(r'_\d+\.csv$', '.csv', fname)

                # 用 (folder, base_name) 作為 key
                folder = os.path.basename(root)
                lot_key = f"{folder}/{base_name}"

                if lot_key not in groups:
                    groups[lot_key] = []
                groups[lot_key].append((finfo['continuation_index'], fpath))

        # 排序每組內的檔案
        for key in groups:
            groups[key].sort(key=lambda x: x[0])
            groups[key] = [fp for _, fp in groups[key]]

        return groups

    def parse_lot(self, file_list: list) -> ParseResult:
        """解析一個 lot（可能由多個檔案組成）"""
        if not file_list:
            return ParseResult()

        # 解析主檔
        result = self.parse_file(file_list[0])

        # 合併接續檔
        for cont_file in file_list[1:]:
            cont_result = self.parse_file(cont_file)
            result.data_rows.extend(cont_result.data_rows)
            result.source_files.append(os.path.basename(cont_file))
            # 更新統計（取合併後的 min/max/avg）
            if cont_result.stats.get('min'):
                for i, v in enumerate(cont_result.stats['min']):
                    if v is not None and i < len(result.stats.get('min', [])):
                        orig = result.stats['min'][i]
                        if orig is None or v < orig:
                            result.stats['min'][i] = v
            if cont_result.stats.get('max'):
                for i, v in enumerate(cont_result.stats['max']):
                    if v is not None and i < len(result.stats.get('max', [])):
                        orig = result.stats['max'][i]
                        if orig is None or v > orig:
                            result.stats['max'][i] = v

        result.total_units = len(result.data_rows)
        return result

    # ─── SQLite 輸出 ────────────────────────────────────

    def to_sqlite(self, dir_path: str, db_path: str, dry_run: bool = False) -> dict:
        """掃描目錄 → 解析所有檔案 → 寫入 SQLite

        Tables:
          - lots: 每個 lot 的元數據
          - spec_limits: 每個 device_type 的規格定義
          - measurements: 所有量測數據（長格式）
          - measurements_wide: 所有量測數據（寬格式，每個參數一欄）

        Returns:
            統計摘要 dict
        """
        groups = self.scan_directory(dir_path)
        logger.info(f'找到 {len(groups)} 個 lot（{sum(len(v) for v in groups.values())} 個檔案）')

        if dry_run:
            for key, files in sorted(groups.items()):
                logger.info(f'  {key}: {len(files)} file(s)')
            return {'lots': len(groups), 'files': sum(len(v) for v in groups.values())}

        # 建立 DB
        os.makedirs(os.path.dirname(db_path) or '.', exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=NORMAL')

        try:
            self._create_tables(conn)

            stats = {'lots': 0, 'files': 0, 'units': 0, 'measurements': 0}

            for lot_key, file_list in sorted(groups.items()):
                logger.info(f'解析: {lot_key} ({len(file_list)} file(s))...')
                result = self.parse_lot(file_list)

                if not result.data_rows:
                    logger.warning(f'  無數據: {lot_key}')
                    continue

                lot_id = self._insert_lot(conn, result)
                self._insert_specs(conn, result, lot_id)
                n_meas = self._insert_measurements(conn, result, lot_id)

                stats['lots'] += 1
                stats['files'] += len(file_list)
                stats['units'] += result.total_units
                stats['measurements'] += n_meas

                logger.info(f'  → {result.total_units} units, '
                            f'{len(result.columns)} params, '
                            f'{n_meas} measurements')

            conn.commit()
            logger.info(f'完成! {stats}')
            return stats

        finally:
            conn.close()

    def _create_tables(self, conn: sqlite3.Connection):
        """建立資料表"""
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS lots (
                lot_id          INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_name        TEXT NOT NULL,
                device_type     TEXT,
                tx_batch        TEXT,
                ga_order        TEXT,
                ga_sub          TEXT,
                test_datetime   TEXT,
                polarity        TEXT,
                unit_station    TEXT,
                day_time        TEXT,
                test_file_path  TEXT,
                source_files    TEXT,
                total_units     INTEGER,
                param_count     INTEGER,
                _source_dir     TEXT,
                UNIQUE(lot_name)
            );

            CREATE TABLE IF NOT EXISTS spec_limits (
                spec_id         INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_id          INTEGER NOT NULL,
                device_type     TEXT,
                param_index     INTEGER,
                std_item        TEXT,
                user_item       TEXT NOT NULL,
                upper_limit     REAL,
                lower_limit     REAL,
                condition_1     TEXT,
                condition_2     TEXT,
                condition_3     TEXT,
                condition_4     TEXT,
                condition_5     TEXT,
                time_setting    REAL,
                FOREIGN KEY (lot_id) REFERENCES lots(lot_id)
            );

            CREATE TABLE IF NOT EXISTS measurements (
                meas_id         INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_id          INTEGER NOT NULL,
                unit            INTEGER NOT NULL,
                bin_no          TEXT,
                category_no     TEXT,
                category_name   TEXT,
                user_item       TEXT NOT NULL,
                value           REAL,
                FOREIGN KEY (lot_id) REFERENCES lots(lot_id)
            );

            CREATE INDEX IF NOT EXISTS idx_meas_lot ON measurements(lot_id);
            CREATE INDEX IF NOT EXISTS idx_meas_lot_item ON measurements(lot_id, user_item);
            CREATE INDEX IF NOT EXISTS idx_meas_item ON measurements(user_item);
            CREATE INDEX IF NOT EXISTS idx_lots_type ON lots(device_type);
            CREATE INDEX IF NOT EXISTS idx_lots_ga ON lots(ga_order);
            CREATE INDEX IF NOT EXISTS idx_lots_tx ON lots(tx_batch);
        """)

    def _insert_lot(self, conn: sqlite3.Connection, result: ParseResult) -> int:
        """插入 lot 元數據，返回 lot_id"""
        m = result.metadata
        cursor = conn.execute("""
            INSERT OR REPLACE INTO lots
            (lot_name, device_type, tx_batch, ga_order, ga_sub, test_datetime,
             polarity, unit_station, day_time, test_file_path, source_files,
             total_units, param_count, _source_dir)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            m.lot_name, m.device_type, m.tx_batch, m.ga_order, m.ga_sub,
            m.test_datetime, m.polarity, m.unit_station, m.day_time,
            m.test_file_path, '|'.join(result.source_files),
            result.total_units, len(result.columns), ''
        ))
        return cursor.lastrowid

    def _insert_specs(self, conn: sqlite3.Connection, result: ParseResult, lot_id: int):
        """插入規格定義"""
        rows = []
        for col in result.columns:
            conds = col.conditions + [''] * 5  # 確保長度 ≥ 5
            rows.append((
                lot_id, result.metadata.device_type, col.index,
                col.std_item, col.user_item,
                col.upper, col.lower,
                conds[0], conds[1], conds[2], conds[3], conds[4],
                col.time
            ))
        conn.executemany("""
            INSERT INTO spec_limits
            (lot_id, device_type, param_index, std_item, user_item,
             upper_limit, lower_limit,
             condition_1, condition_2, condition_3, condition_4, condition_5,
             time_setting)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)

    def _insert_measurements(self, conn: sqlite3.Connection, result: ParseResult, lot_id: int) -> int:
        """插入量測數據（長格式），返回寫入筆數"""
        param_names = [col.user_item for col in result.columns]
        batch = []
        total = 0

        for rec in result.data_rows:
            unit = rec['unit']
            bin_no = rec['bin_no']
            cat_no = rec['category_no']
            cat_name = rec['category_name']

            for pname in param_names:
                val = rec.get(pname)
                if val is not None:
                    batch.append((lot_id, unit, bin_no, cat_no, cat_name, pname, val))

                    if len(batch) >= BATCH_SIZE:
                        conn.executemany("""
                            INSERT INTO measurements
                            (lot_id, unit, bin_no, category_no, category_name, user_item, value)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, batch)
                        total += len(batch)
                        batch = []

        if batch:
            conn.executemany("""
                INSERT INTO measurements
                (lot_id, unit, bin_no, category_no, category_name, user_item, value)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, batch)
            total += len(batch)

        return total


# ─── CLI ────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description='LTX CSV Parser — 解析 LTX 測試機 raw data 到 SQLite')
    ap.add_argument('--input', '-i', required=True,
                    help='輸入目錄或單一 CSV 檔案')
    ap.add_argument('--output', '-o', required=True,
                    help='輸出 SQLite 資料庫路徑')
    ap.add_argument('--dry-run', action='store_true',
                    help='僅掃描檔案結構，不實際寫入')
    ap.add_argument('--encoding', default=None,
                    help='強制指定編碼（預設自動偵測）')
    args = ap.parse_args()

    parser = LtxParser()

    if os.path.isfile(args.input):
        # 單檔模式
        result = parser.parse_file(args.input, encoding=args.encoding)
        print(f'Lot: {result.metadata.lot_name}')
        print(f'Type: {result.metadata.device_type}')
        print(f'Units: {result.total_units}')
        print(f'Params: {len(result.columns)}')
        print(f'Columns:')
        for col in result.columns:
            print(f'  [{col.index}] {col.user_item} '
                  f'(std: {col.std_item}) '
                  f'USL={col.upper} LSL={col.lower}')
        if not args.dry_run:
            # 單檔也寫入 DB
            os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
            conn = sqlite3.connect(args.output)
            parser._create_tables(conn)
            lot_id = parser._insert_lot(conn, result)
            parser._insert_specs(conn, result, lot_id)
            n = parser._insert_measurements(conn, result, lot_id)
            conn.commit()
            conn.close()
            print(f'Written to {args.output}: lot_id={lot_id}, {n} measurements')
    else:
        # 目錄模式
        stats = parser.to_sqlite(args.input, args.output, dry_run=args.dry_run)
        print(f'\nResult: {stats}')


if __name__ == '__main__':
    main()
