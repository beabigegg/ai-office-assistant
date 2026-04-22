"""
Desc 欄位解析器

根據 shared/kb/dynamic/column_semantics.md 定義的規則，解析 BOM 資料中的 Desc 欄位。
獨立欄位（Die Length, Wire Mil 等）空白率達 90~95%，而 Desc 欄位空白率僅 0~3%，
因此應優先從 Desc 欄位解析資料。

作者：Toolsmith
建造日期：2026-02-04
"""

import re
from typing import Optional, Dict, Any, Union


# =============================================================================
# 晶片 Desc 解析
# =============================================================================

def parse_wafer_desc(desc: str) -> Optional[Dict[str, str]]:
    """
    解析晶片 Desc 欄位

    格式：{Wafer Function}/{Wafer Size}/{Wafer Type}/{Die Size}/{Die Size2}/{Thickness}/{Metal}/

    Args:
        desc: Sub Com Item Desc 字串（物料類型為「晶片」）

    Returns:
        dict 包含以下欄位，或 None（解析失敗）：
        - wafer_function: 晶片功能（SWI, ZEN, MOS, SKY, TVS, TRA 等）
        - wafer_size: 晶圓尺寸（5", 6", 8"）
        - wafer_type: 晶圓型號（如 5DS02MH-K）
        - die_size: 晶粒大小（如 10, 35）
        - die_size2: 晶粒大小含單位（如 *10mil, *35mil）
        - thickness: 厚度（如 230um）
        - metal: 金屬層（如 ALAU, AGAG, ALSN）

    Example:
        >>> parse_wafer_desc("SWI/5\"/5DS02MH-K/10/*10mil/230um/ALAU/")
        {'wafer_function': 'SWI', 'wafer_size': '5"', 'wafer_type': '5DS02MH-K',
         'die_size': '10', 'die_size2': '*10mil', 'thickness': '230um', 'metal': 'ALAU'}
    """
    if not desc or not isinstance(desc, str):
        return None

    desc = desc.strip()
    if not desc:
        return None

    parts = desc.split('/')

    # 晶片格式至少需要 7 個部分（最後一個可能是空的尾部）
    if len(parts) < 7:
        return None

    # 驗證第一部分看起來像 Wafer Function（通常 3 碼大寫）
    wafer_function = parts[0].strip()
    if not wafer_function:
        return None

    # 驗證第二部分看起來像晶圓尺寸（含有數字和引號）
    # 晶粒格式允許 'CHIP' 作為有效值（裸晶無晶圓尺寸）
    wafer_size = parts[1].strip()
    if wafer_size and wafer_size != 'CHIP' and not re.search(r'\d', wafer_size):
        # 可能不是正確的晶片格式
        return None

    return {
        'wafer_function': wafer_function,
        'wafer_size': wafer_size,
        'wafer_type': parts[2].strip() if len(parts) > 2 else '',
        'die_size': parts[3].strip() if len(parts) > 3 else '',
        'die_size2': parts[4].strip() if len(parts) > 4 else '',
        'thickness': parts[5].strip() if len(parts) > 5 else '',
        'metal': parts[6].strip() if len(parts) > 6 else ''
    }


# =============================================================================
# 腳架 Desc 解析
# =============================================================================

def parse_leadframe_desc(desc: str) -> Optional[Dict[str, str]]:
    """
    解析腳架 Desc 欄位

    格式：腳架/{Package}/{Option}/{Form}/{Material}/[{Extra}]

    Args:
        desc: Sub Com Item Desc 字串（物料類型為「腳架」）

    Returns:
        dict 包含以下欄位，或 None（解析失敗）：
        - package: 封裝類型（SOT-23, SOD-123FL 等）
        - option: Layout 選項（OPTION 1, BASE, HD 等）
        - form: 形式（REEL 捲狀, STRIP 片狀）
        - material: 材質（Cu 銅, A42 合金42）
        - extra: 額外資訊（如有）

    Example:
        >>> parse_leadframe_desc("腳架/SOT-23/OPTION 4/REEL/Cu")
        {'package': 'SOT-23', 'option': 'OPTION 4', 'form': 'REEL',
         'material': 'Cu', 'extra': ''}
    """
    if not desc or not isinstance(desc, str):
        return None

    desc = desc.strip()
    if not desc:
        return None

    # 腳架格式必須以「腳架」開頭
    if not desc.startswith('腳架'):
        return None

    parts = desc.split('/')

    # 至少需要 5 個部分：腳架/Package/Option/Form/Material
    if len(parts) < 5:
        return None

    # HD 腳架為 6 欄位格式：腳架/{Package}/HD/{DetailOption}/{Form}/{Material}/
    # 標準格式為 5 欄位：腳架/{Package}/{Option}/{Form}/{Material}/
    opt = parts[2].strip() if len(parts) > 2 else ''
    if opt == 'HD' and len(parts) >= 6:
        detail_opt = parts[3].strip() if len(parts) > 3 else ''
        return {
            'package': parts[1].strip(),
            'option': f"HD {detail_opt}" if detail_opt else 'HD',
            'form': parts[4].strip() if len(parts) > 4 else '',
            'material': parts[5].strip() if len(parts) > 5 else '',
            'extra': parts[6].strip() if len(parts) > 6 else ''
        }

    return {
        'package': parts[1].strip() if len(parts) > 1 else '',
        'option': opt,
        'form': parts[3].strip() if len(parts) > 3 else '',
        'material': parts[4].strip() if len(parts) > 4 else '',
        'extra': parts[5].strip() if len(parts) > 5 else ''
    }


# =============================================================================
# 線材 Desc 解析
# =============================================================================

def parse_wire_desc(desc: str) -> Optional[Dict[str, Any]]:
    """
    解析線材 Desc 欄位

    標準格式：{Wire Type}/phi{Mil}/{Grade}/{Length}/
    跳線格式：跳線/{Package}/{Option}/{Grade}/

    Args:
        desc: Sub Com Item Desc 字串（物料類型為「線材」）

    Returns:
        dict 包含以下欄位，或 None（解析失敗）：

        標準線材：
        - wire_type: 線材類型（GOLD WIRE, CU WIRE, AG WIRE）
        - wire_mil: 線徑（如 1.0）
        - wire_mil_raw: 原始線徑字串（如 phi1.0mil）
        - grade: 等級（Normal, GLF, AgLite）
        - length: 長度（如 1000M）
        - is_clip: False

        跳線/CLIP：
        - wire_type: 'CLIP'
        - package: 封裝類型
        - option: 選項
        - grade: 等級
        - is_clip: True

    Example:
        >>> parse_wire_desc("GOLD WIRE/phi1.0mil/GLF/1000M/")
        {'wire_type': 'GOLD WIRE', 'wire_mil': '1.0', 'wire_mil_raw': 'phi1.0mil',
         'grade': 'GLF', 'length': '1000M', 'is_clip': False}

        >>> parse_wire_desc("跳線/SMAF/C(C)/HD A/")
        {'wire_type': 'CLIP', 'package': 'SMAF', 'option': 'C(C)',
         'grade': 'HD A', 'is_clip': True}
    """
    if not desc or not isinstance(desc, str):
        return None

    desc = desc.strip()
    if not desc:
        return None

    parts = desc.split('/')

    # 處理跳線/CLIP 格式
    if desc.startswith('跳線'):
        if len(parts) < 4:
            return None
        return {
            'wire_type': 'CLIP',
            'package': parts[1].strip() if len(parts) > 1 else '',
            'option': parts[2].strip() if len(parts) > 2 else '',
            'grade': parts[3].strip() if len(parts) > 3 else '',
            'is_clip': True
        }

    # 標準線材格式
    if len(parts) < 4:
        return None

    wire_type = parts[0].strip()
    wire_mil_raw = parts[1].strip() if len(parts) > 1 else ''

    # 提取線徑數值（支援多種格式：phi1.0mil, 1.0mil, phi1.0 等）
    wire_mil = ''
    if wire_mil_raw:
        # 嘗試匹配 phi{數字}mil 或 {數字}mil
        mil_match = re.search(r'[φφ]?([\d.]+)\s*mil', wire_mil_raw, re.IGNORECASE)
        if mil_match:
            wire_mil = mil_match.group(1)
        else:
            # 嘗試提取純數字
            num_match = re.search(r'[\d.]+', wire_mil_raw)
            if num_match:
                wire_mil = num_match.group(0)

    return {
        'wire_type': wire_type,
        'wire_mil': wire_mil,
        'wire_mil_raw': wire_mil_raw,
        'grade': parts[2].strip() if len(parts) > 2 else '',
        'length': parts[3].strip() if len(parts) > 3 else '',
        'is_clip': False
    }


# =============================================================================
# 膠 Desc 解析
# =============================================================================

def parse_glue_desc(desc: str) -> Optional[Dict[str, str]]:
    """
    解析膠 Desc 欄位

    格式：{Glue Type}/{Model}/{Size}/{Weight}/[{Extra}]

    Args:
        desc: Sub Com Item Desc 字串（物料類型為「膠」）

    Returns:
        dict 包含以下欄位，或 None（解析失敗）：
        - glue_type: 膠類型（銀膠, 錫膏, 成型膠, 絕緣膠）
        - model: 型號（如 84-1LMISR4）
        - size: 規格（如 5cc）
        - weight: 重量（如 18g）
        - extra: 額外資訊

    Example:
        >>> parse_glue_desc("銀膠/84-1LMISR4/5cc/18g//")
        {'glue_type': '銀膠', 'model': '84-1LMISR4', 'size': '5cc',
         'weight': '18g', 'extra': ''}
    """
    if not desc or not isinstance(desc, str):
        return None

    desc = desc.strip()
    if not desc:
        return None

    parts = desc.split('/')

    # 至少需要 4 個部分
    if len(parts) < 4:
        return None

    glue_type = parts[0].strip()

    # 驗證是否為已知的膠類型
    known_glue_types = ['銀膠', '錫膏', '成型膠', '絕緣膠', '保護膠', '導電膠', '封裝膠']
    # 也允許非中文開頭（某些膠可能用英文名）

    return {
        'glue_type': glue_type,
        'model': parts[1].strip() if len(parts) > 1 else '',
        'size': parts[2].strip() if len(parts) > 2 else '',
        'weight': parts[3].strip() if len(parts) > 3 else '',
        'extra': '/'.join(parts[4:]).strip() if len(parts) > 4 else ''
    }


# =============================================================================
# 包裝材料 Desc 解析
# =============================================================================

def parse_packing_desc(desc: str) -> Optional[Dict[str, str]]:
    """
    解析包裝材料 Desc 欄位

    格式不固定，常見有：
    - 錫球：錫球//{規格}/
    - COVER TAPE：COVER TAPE/{型號}/{規格}/{長度}/{寬度}/
    - 載帶：載帶/{規格}/...
    - 圓盤：圓盤/{規格}/...

    Args:
        desc: Sub Com Item Desc 字串（物料類型為「包裝材料」）

    Returns:
        dict 包含以下欄位，或 None（解析失敗）：
        - packing_type: 包裝類型（錫球, COVER TAPE, 載帶, 圓盤 等）
        - spec1, spec2, spec3, spec4: 各段規格資訊
        - full_spec: 完整規格字串（去除類型後）

    Example:
        >>> parse_packing_desc("COVER TAPE/MODEL-X/8mm/1000M/16mm/")
        {'packing_type': 'COVER TAPE', 'spec1': 'MODEL-X', 'spec2': '8mm',
         'spec3': '1000M', 'spec4': '16mm', 'full_spec': 'MODEL-X/8mm/1000M/16mm'}
    """
    if not desc or not isinstance(desc, str):
        return None

    desc = desc.strip()
    if not desc:
        return None

    parts = desc.split('/')

    if len(parts) < 2:
        return None

    packing_type = parts[0].strip()

    return {
        'packing_type': packing_type,
        'spec1': parts[1].strip() if len(parts) > 1 else '',
        'spec2': parts[2].strip() if len(parts) > 2 else '',
        'spec3': parts[3].strip() if len(parts) > 3 else '',
        'spec4': parts[4].strip() if len(parts) > 4 else '',
        'full_spec': '/'.join(p.strip() for p in parts[1:] if p.strip())
    }


# =============================================================================
# Com Item Desc 解析（依站別）
# =============================================================================

def parse_com_item_desc(desc: str, operation_seq: Union[int, str] = None) -> Optional[Dict[str, Any]]:
    """
    解析 Com Item Desc（配方/站別製程描述）

    通用格式：{Process Type}/{Package}/{Process Detail}/{Material}/{Option}/.../for Chip size {Range}/{Loss}

    依站別有不同結構：
    - 站別 15（焊接 DB）：焊接(DB)/{Package}/{Process}/{Material}/{Option}/.../for Chip size {Range}/{Loss}
    - 站別 23（打線 WB）：焊接/{Package}/...//{Wire Type}/{WireSpec}/for Chip size {Range}/{Loss}
    - 站別 28（成型）：成型/{Package}/{EMC Type}/.../
    - 站別 60/63（電鍍）：電鍍/{Package}/.../(PJ)/{Loss}
    - 站別 90（包裝）：包裝/{Package}/{Packing Type}/.../

    Args:
        desc: Com Item Desc 字串
        operation_seq: 站別序號（可選，用於更精確的解析）

    Returns:
        dict 包含以下欄位，或 None（解析失敗）：
        - process_type: 製程類型（焊接(DB), 焊接(WB), 焊接(DWB), 成型, 電鍍, 包裝）
        - package: 封裝類型
        - 其他欄位依製程類型而定

    Example:
        >>> parse_com_item_desc("焊接(DB)/SOT-23/Eutectic/Cu/OP5////0%")
        {'process_type': '焊接(DB)', 'package': 'SOT-23', 'process': 'Eutectic',
         'material': 'Cu', 'option': 'OP5', 'loss_rate': '0%'}
    """
    if not desc or not isinstance(desc, str):
        return None

    desc = desc.strip()
    if not desc:
        return None

    parts = desc.split('/')
    if len(parts) < 2:
        return None

    process_type = parts[0].strip()
    package = parts[1].strip() if len(parts) > 1 else ''

    result = {
        'process_type': process_type,
        'package': package,
        'raw_parts': parts
    }

    # 提取 for Chip size 資訊
    chip_size_match = re.search(r'for Chip size\s*([\d~.]+(?:mil)?)', desc, re.IGNORECASE)
    if chip_size_match:
        result['chip_size_range'] = chip_size_match.group(1)

    # 提取 Loss Rate（通常在最後，格式為 X% 或 X.X%）
    loss_match = re.search(r'([\d.]+%)\s*$', desc)
    if loss_match:
        result['loss_rate'] = loss_match.group(1)

    # 依製程類型細化解析
    if process_type.startswith('焊接(DB)') or process_type == '焊接(DB)':
        # 站別 15 格式
        result['process'] = parts[2].strip() if len(parts) > 2 else ''
        result['material'] = parts[3].strip() if len(parts) > 3 else ''
        result['option'] = parts[4].strip() if len(parts) > 4 else ''

    elif process_type.startswith('焊接(WB)') or process_type.startswith('焊接(DWB)'):
        # 站別 23 格式（打線）
        # 嘗試找 Wire Type 和 WireSpec
        for i, part in enumerate(parts):
            if 'WIRE' in part.upper():
                result['wire_type'] = part.strip()
                if i + 1 < len(parts):
                    result['wire_spec'] = parts[i + 1].strip()
                break
        result['process'] = parts[2].strip() if len(parts) > 2 else ''
        result['material'] = parts[3].strip() if len(parts) > 3 else ''

    elif process_type == '焊接':
        # 一般焊接（可能是 WB）
        result['process'] = parts[2].strip() if len(parts) > 2 else ''
        result['material'] = parts[3].strip() if len(parts) > 3 else ''
        # 嘗試找線材資訊
        for i, part in enumerate(parts):
            if 'WIRE' in part.upper():
                result['wire_type'] = part.strip()
                if i + 1 < len(parts):
                    result['wire_spec'] = parts[i + 1].strip()
                break

    elif process_type == '成型':
        # 站別 28
        result['emc_type'] = parts[2].strip() if len(parts) > 2 else ''

    elif process_type == '電鍍':
        # 站別 60/63
        # 檢查是否有 (PJ) 標記
        if '(PJ)' in desc:
            result['is_pj'] = True

    elif process_type == '包裝':
        # 站別 90
        result['packing_type'] = parts[2].strip() if len(parts) > 2 else ''

    return result


# =============================================================================
# 自動判斷物料類型並解析
# =============================================================================

def auto_parse_sub_com_desc(desc: str, m_type: str) -> Optional[Dict[str, Any]]:
    """
    根據 Sub Com Item M Type 自動選擇正確的解析器

    Args:
        desc: Sub Com Item Desc 字串
        m_type: Sub Com Item M Type（晶片, 腳架, 線材, 膠, 包裝材料, 其他）

    Returns:
        dict 包含解析結果和元資料，或 None（解析失敗）：
        - _parser: 使用的解析器名稱
        - _m_type: 物料類型
        - _success: 是否成功解析
        - ...其他欄位依解析器而定

    Example:
        >>> auto_parse_sub_com_desc("SWI/5\"/5DS02MH-K/10/*10mil/230um/ALAU/", "晶片")
        {'_parser': 'wafer', '_m_type': '晶片', '_success': True,
         'wafer_function': 'SWI', ...}
    """
    if not desc or not isinstance(desc, str):
        return {'_parser': None, '_m_type': m_type, '_success': False, '_error': 'Empty desc'}

    if not m_type or not isinstance(m_type, str):
        return {'_parser': None, '_m_type': m_type, '_success': False, '_error': 'Empty m_type'}

    m_type = m_type.strip()
    result = None
    parser_name = None

    if m_type in ('晶片', '晶粒'):
        result = parse_wafer_desc(desc)
        parser_name = 'wafer'

    elif m_type == '腳架':
        result = parse_leadframe_desc(desc)
        parser_name = 'leadframe'

    elif m_type == '線材':
        result = parse_wire_desc(desc)
        parser_name = 'wire'

    elif m_type == '膠':
        result = parse_glue_desc(desc)
        parser_name = 'glue'

    elif m_type == '包裝材料':
        result = parse_packing_desc(desc)
        parser_name = 'packing'

    elif m_type == '其他':
        # 嘗試通用解析
        result = parse_packing_desc(desc)  # 用 packing 格式作為 fallback
        parser_name = 'generic'

    else:
        # 未知類型，嘗試自動偵測
        if desc.startswith('腳架'):
            result = parse_leadframe_desc(desc)
            parser_name = 'leadframe'
        elif desc.startswith('跳線') or 'WIRE' in desc.upper():
            result = parse_wire_desc(desc)
            parser_name = 'wire'
        elif any(g in desc for g in ['銀膠', '錫膏', '成型膠', '絕緣膠']):
            result = parse_glue_desc(desc)
            parser_name = 'glue'
        else:
            # 嘗試晶片格式
            result = parse_wafer_desc(desc)
            if result:
                parser_name = 'wafer'
            else:
                result = parse_packing_desc(desc)
                parser_name = 'generic'

    if result:
        result['_parser'] = parser_name
        result['_m_type'] = m_type
        result['_success'] = True
        return result
    else:
        return {
            '_parser': parser_name,
            '_m_type': m_type,
            '_success': False,
            '_error': 'Parse failed',
            '_raw_desc': desc
        }


# =============================================================================
# 工具函數
# =============================================================================

def extract_numeric_value(text: str, unit: str = None) -> Optional[float]:
    """
    從文字中提取數值

    Args:
        text: 包含數值的文字（如 "230um", "1.0mil", "18g"）
        unit: 預期的單位（可選，用於驗證）

    Returns:
        float 數值，或 None

    Example:
        >>> extract_numeric_value("230um")
        230.0
        >>> extract_numeric_value("1.0mil", "mil")
        1.0
    """
    if not text:
        return None

    # 提取數字部分（包括小數點）
    match = re.search(r'([\d.]+)', text)
    if match:
        try:
            value = float(match.group(1))
            # 如果指定了單位，驗證是否匹配
            if unit and unit.lower() not in text.lower():
                return None
            return value
        except ValueError:
            return None
    return None


def normalize_wire_type(wire_type: str) -> str:
    """
    標準化線材類型名稱

    Args:
        wire_type: 原始線材類型（如 "GOLD WIRE", "Cu WIRE"）

    Returns:
        標準化後的類型（GOLD, CU, AG）
    """
    if not wire_type:
        return ''

    wire_type = wire_type.upper()

    if 'GOLD' in wire_type or 'AU' in wire_type:
        return 'GOLD'
    elif 'CU' in wire_type or 'COPPER' in wire_type:
        return 'CU'
    elif 'AG' in wire_type or 'SILVER' in wire_type:
        return 'AG'
    elif 'CLIP' in wire_type or '跳線' in wire_type:
        return 'CLIP'
    else:
        return wire_type.replace(' WIRE', '').strip()


def normalize_material(material: str) -> str:
    """
    標準化材質名稱

    Args:
        material: 原始材質（如 "Cu", "Copper", "A42", "ALLOY42"）

    Returns:
        標準化後的材質（CU, A42）
    """
    if not material:
        return ''

    material = material.upper().strip()

    if material in ('CU', 'COPPER', '銅'):
        return 'CU'
    elif material in ('A42', 'ALLOY42', 'ALLOY 42', '合金42'):
        return 'A42'
    else:
        return material


# =============================================================================
# 測試區塊
# =============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("Desc Parser 測試")
    print("=" * 60)

    # 測試晶片解析
    print("\n--- 晶片 ---")
    wafer_samples = [
        "SWI/5\"/5DS02MH-K/10/*10mil/230um/ALAU/",
        "ZEN/6\"/6ZE01MH-L/35/*35mil/200um/AGAG/",
        "MOS/8\"/8MS03-K/20/*20mil/150um/ALSN/",
    ]
    for s in wafer_samples:
        result = parse_wafer_desc(s)
        print(f"  Input: {s}")
        print(f"  Output: {result}")
        print()

    # 測試腳架解析
    print("\n--- 腳架 ---")
    lef_samples = [
        "腳架/SOT-23/OPTION 4/REEL/Cu",
        "腳架/SOD-123FL/BASE/STRIP/A42",
        "腳架/SMAF/HD/REEL/Cu/",
    ]
    for s in lef_samples:
        result = parse_leadframe_desc(s)
        print(f"  Input: {s}")
        print(f"  Output: {result}")
        print()

    # 測試線材解析
    print("\n--- 線材 ---")
    wire_samples = [
        "GOLD WIRE/φ1.0mil/GLF/1000M/",
        "CU WIRE/φ0.8mil/Normal/1000M/",
        "跳線/SMAF/C(C)/HD A/",
        "AG WIRE/φ1.2mil/AgLite/500M/",
    ]
    for s in wire_samples:
        result = parse_wire_desc(s)
        print(f"  Input: {s}")
        print(f"  Output: {result}")
        print()

    # 測試膠解析
    print("\n--- 膠 ---")
    glue_samples = [
        "銀膠/84-1LMISR4/5cc/18g//",
        "錫膏/SAC305/10cc/25g/",
        "成型膠/EMC-7320/10kg//",
    ]
    for s in glue_samples:
        result = parse_glue_desc(s)
        print(f"  Input: {s}")
        print(f"  Output: {result}")
        print()

    # 測試 Com Item Desc 解析
    print("\n--- Com Item Desc ---")
    com_samples = [
        "焊接(DB)/SOT-23/Eutectic/Cu/OP5////0%",
        "焊接/SOT-23////Cu WIRE/10WX1/for Chip size8~19mil/0.0%",
        "成型/SOT-23/Green EMC//////0.0%",
        "電鍍/SOT-23//////(PJ)/0.0%",
        "包裝/SOD-123/R7//////0.00%",
    ]
    for s in com_samples:
        result = parse_com_item_desc(s)
        print(f"  Input: {s}")
        print(f"  Output: {result}")
        print()

    # 測試自動解析
    print("\n--- 自動解析 ---")
    auto_samples = [
        ("SWI/5\"/5DS02MH-K/10/*10mil/230um/ALAU/", "晶片"),
        ("腳架/SOT-23/OPTION 4/REEL/Cu", "腳架"),
        ("GOLD WIRE/φ1.0mil/GLF/1000M/", "線材"),
        ("銀膠/84-1LMISR4/5cc/18g//", "膠"),
    ]
    for desc, m_type in auto_samples:
        result = auto_parse_sub_com_desc(desc, m_type)
        print(f"  Input: ({m_type}) {desc}")
        print(f"  Output: {result}")
        print()

    print("=" * 60)
    print("測試完成")
    print("=" * 60)
