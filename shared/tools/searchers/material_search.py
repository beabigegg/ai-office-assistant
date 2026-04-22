"""
原物料資訊搜索工具 v1.0

用途：搜索半導體封裝原物料的規格、特性、供應商資訊
支援：膠材、線材、腳架、晶片等各類原物料

使用方式：
    from material_search import MaterialSearcher

    searcher = MaterialSearcher()
    result = searcher.search("ELER-8-500C", material_type="膠材")
"""

import json
import re
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from enum import Enum


class MaterialType(Enum):
    """原物料類型"""
    ADHESIVE = "膠材"      # 銀膠、成型膠、保護膠
    WIRE = "線材"          # 金線、銅線、銀線
    LEADFRAME = "腳架"     # 銅、A42
    WAFER = "晶片"         # 晶圓/晶片
    SOLDER = "焊料"        # 錫球、錫膏
    PACKAGE = "包裝材料"   # 載帶、蓋帶
    OTHER = "其他"


@dataclass
class MaterialSpec:
    """材料規格"""
    name: str = ""
    value: str = ""
    unit: str = ""
    note: str = ""


@dataclass
class SearchResult:
    """搜索結果"""
    material_id: str = ""
    material_name: str = ""
    material_type: str = ""
    manufacturer: str = ""

    # 基本資訊
    description: str = ""
    applications: List[str] = field(default_factory=list)

    # 規格特性
    specs: List[MaterialSpec] = field(default_factory=list)

    # 供應商資訊
    supplier_url: str = ""
    datasheet_url: str = ""

    # 替代品
    alternatives: List[str] = field(default_factory=list)

    # 搜索來源
    sources: List[str] = field(default_factory=list)

    # 搜索狀態
    status: str = "pending"  # pending, success, partial, failed
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['specs'] = [asdict(s) for s in self.specs]
        return result

    def to_markdown(self) -> str:
        """輸出為 Markdown 格式"""
        lines = []
        lines.append(f"## {self.material_name or self.material_id}")
        lines.append(f"")
        lines.append(f"| 項目 | 內容 |")
        lines.append(f"|------|------|")
        lines.append(f"| 料號 | {self.material_id} |")
        lines.append(f"| 類型 | {self.material_type} |")
        lines.append(f"| 製造商 | {self.manufacturer} |")
        lines.append(f"| 說明 | {self.description} |")

        if self.specs:
            lines.append(f"")
            lines.append(f"### 規格特性")
            lines.append(f"| 特性 | 值 | 單位 | 備註 |")
            lines.append(f"|------|---|------|------|")
            for spec in self.specs:
                lines.append(f"| {spec.name} | {spec.value} | {spec.unit} | {spec.note} |")

        if self.alternatives:
            lines.append(f"")
            lines.append(f"### 可能替代品")
            for alt in self.alternatives:
                lines.append(f"- {alt}")

        if self.sources:
            lines.append(f"")
            lines.append(f"### 資料來源")
            for src in self.sources:
                lines.append(f"- {src}")

        return "\n".join(lines)


class MaterialSearcher:
    """原物料搜索器"""

    # 已知供應商對照
    KNOWN_SUPPLIERS = {
        # 膠材供應商
        "ELER": "長興化學 (Eternal)",
        "EME": "住友電木 (Sumitomo Bakelite)",
        "KJR": "KJR",
        "84-1": "Henkel (Ablestik)",

        # 線材供應商
        "GLF": "賀利氏 (Heraeus)",
        "AgLite": "田中貴金屬 (Tanaka)",

        # 常見膠材型號模式
    }

    # 膠材特性關鍵字
    ADHESIVE_KEYWORDS = {
        "Tg": "玻璃轉移溫度",
        "CTE": "熱膨脹係數",
        "modulus": "模量",
        "viscosity": "黏度",
        "cure": "固化",
        "filler": "填料",
        "thermal conductivity": "熱傳導係數",
    }

    # 線材特性關鍵字
    WIRE_KEYWORDS = {
        "tensile": "抗拉強度",
        "elongation": "延伸率",
        "hardness": "硬度",
        "resistivity": "電阻率",
        "bonding": "接合",
    }

    def __init__(self):
        self.search_history = []

    def identify_material_type(self, material_id: str, desc: str = "") -> MaterialType:
        """識別物料類型"""
        material_id_upper = material_id.upper()
        desc_upper = desc.upper()

        # 根據料號前綴判斷
        if material_id_upper.startswith("COM") or any(k in desc_upper for k in ["膠", "ADHESIVE", "EMC", "EPOXY"]):
            return MaterialType.ADHESIVE
        elif material_id_upper.startswith("WIR") or any(k in desc_upper for k in ["WIRE", "線"]):
            return MaterialType.WIRE
        elif material_id_upper.startswith("LEF") or any(k in desc_upper for k in ["腳架", "LEADFRAME"]):
            return MaterialType.LEADFRAME
        elif material_id_upper.startswith("WAF") or any(k in desc_upper for k in ["晶片", "WAFER", "DIE"]):
            return MaterialType.WAFER
        elif material_id_upper.startswith("RAW") or any(k in desc_upper for k in ["錫球", "SOLDER"]):
            return MaterialType.SOLDER
        elif material_id_upper.startswith("PAC") or any(k in desc_upper for k in ["TAPE", "載帶", "圓盤"]):
            return MaterialType.PACKAGE
        else:
            return MaterialType.OTHER

    def identify_supplier(self, material_name: str) -> str:
        """識別供應商"""
        for prefix, supplier in self.KNOWN_SUPPLIERS.items():
            if prefix.upper() in material_name.upper():
                return supplier
        return ""

    def build_search_queries(self, material_name: str, material_type: MaterialType) -> List[str]:
        """建立搜索關鍵字組合"""
        queries = []

        # 基本搜索
        queries.append(f"{material_name} datasheet")
        queries.append(f"{material_name} specifications")

        # 根據類型添加特定關鍵字
        if material_type == MaterialType.ADHESIVE:
            queries.append(f"{material_name} die attach adhesive")
            queries.append(f"{material_name} molding compound EMC")
            queries.append(f"{material_name} TDS technical data sheet")
        elif material_type == MaterialType.WIRE:
            queries.append(f"{material_name} bonding wire")
            queries.append(f"{material_name} gold wire copper wire")
        elif material_type == MaterialType.LEADFRAME:
            queries.append(f"{material_name} leadframe substrate")

        # 供應商特定搜索
        supplier = self.identify_supplier(material_name)
        if supplier:
            queries.append(f"{supplier} {material_name}")

        return queries

    def parse_desc_for_specs(self, desc: str, material_type: MaterialType) -> List[MaterialSpec]:
        """從描述欄位解析規格"""
        specs = []

        if material_type == MaterialType.ADHESIVE:
            # 解析膠材描述：成型膠/ELER-8-500C/φ48/90g/
            parts = desc.split("/")
            if len(parts) >= 2:
                specs.append(MaterialSpec(name="膠類型", value=parts[0]))
                specs.append(MaterialSpec(name="型號", value=parts[1]))
            if len(parts) >= 3 and "φ" in parts[2]:
                specs.append(MaterialSpec(name="直徑", value=parts[2].replace("φ", ""), unit="mm"))
            if len(parts) >= 4 and "g" in parts[3]:
                specs.append(MaterialSpec(name="重量", value=parts[3].replace("g", ""), unit="g"))

        elif material_type == MaterialType.WIRE:
            # 解析線材描述：GOLD WIRE/φ1.0mil/GLF/1000M/
            parts = desc.split("/")
            if len(parts) >= 1:
                specs.append(MaterialSpec(name="線材類型", value=parts[0]))
            if len(parts) >= 2 and "mil" in parts[1]:
                match = re.search(r"(\d+\.?\d*)", parts[1])
                if match:
                    specs.append(MaterialSpec(name="線徑", value=match.group(1), unit="mil"))
            if len(parts) >= 3:
                specs.append(MaterialSpec(name="等級", value=parts[2]))
            if len(parts) >= 4 and "M" in parts[3]:
                specs.append(MaterialSpec(name="長度", value=parts[3].replace("M", ""), unit="M"))

        elif material_type == MaterialType.LEADFRAME:
            # 解析腳架描述：腳架/SOT-363/OPTION 3/REEL/A42
            parts = desc.split("/")
            if len(parts) >= 2:
                specs.append(MaterialSpec(name="封裝", value=parts[1]))
            if len(parts) >= 3:
                specs.append(MaterialSpec(name="選項", value=parts[2]))
            if len(parts) >= 4:
                specs.append(MaterialSpec(name="形式", value=parts[3]))
            if len(parts) >= 5:
                specs.append(MaterialSpec(name="材質", value=parts[4]))

        return specs

    def search(self,
               material_id: str,
               material_name: str = "",
               material_type: str = "",
               desc: str = "",
               search_web: bool = False) -> SearchResult:
        """
        搜索原物料資訊

        Args:
            material_id: 料號 (如 COM000138)
            material_name: 材料名稱 (如 ELER-8-500C)
            material_type: 物料類型 (膠材/線材/腳架/晶片)
            desc: 描述欄位
            search_web: 是否進行網路搜索 (需配合 Claude 的 WebSearch)

        Returns:
            SearchResult 物件
        """
        result = SearchResult(material_id=material_id)

        # 識別物料類型
        if material_type:
            m_type = MaterialType(material_type) if material_type in [e.value for e in MaterialType] else MaterialType.OTHER
        else:
            m_type = self.identify_material_type(material_id, desc)
        result.material_type = m_type.value

        # 設定材料名稱
        if material_name:
            result.material_name = material_name
        elif desc:
            # 從描述中提取型號
            parts = desc.split("/")
            if len(parts) >= 2:
                result.material_name = parts[1] if parts[0] in ["成型膠", "銀膠", "保護膠", "腳架"] else parts[0]

        # 識別供應商
        result.manufacturer = self.identify_supplier(result.material_name or material_id)

        # 從描述解析規格
        if desc:
            result.description = desc
            result.specs = self.parse_desc_for_specs(desc, m_type)

        # 建立搜索查詢（供後續網路搜索使用）
        if search_web:
            result.sources = self.build_search_queries(result.material_name or material_id, m_type)
            result.status = "pending_web_search"
        else:
            result.status = "success"

        self.search_history.append(result)
        return result

    def compare(self, results: List[SearchResult]) -> str:
        """比較多個材料"""
        if not results:
            return "無資料可比較"

        lines = []
        lines.append("## 材料比較")
        lines.append("")

        # 表頭
        headers = ["特性"] + [r.material_name or r.material_id for r in results]
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("|" + "|".join(["------"] * len(headers)) + "|")

        # 基本資訊
        lines.append("| 類型 | " + " | ".join([r.material_type for r in results]) + " |")
        lines.append("| 製造商 | " + " | ".join([r.manufacturer or "-" for r in results]) + " |")

        # 收集所有規格名稱
        all_spec_names = set()
        for r in results:
            for spec in r.specs:
                all_spec_names.add(spec.name)

        # 輸出規格比較
        for spec_name in sorted(all_spec_names):
            row = [spec_name]
            for r in results:
                spec_val = next((f"{s.value} {s.unit}".strip() for s in r.specs if s.name == spec_name), "-")
                row.append(spec_val)
            lines.append("| " + " | ".join(row) + " |")

        return "\n".join(lines)


# 便捷函數
def search_material(material_id: str, desc: str = "", search_web: bool = False) -> SearchResult:
    """快速搜索單一材料"""
    searcher = MaterialSearcher()
    return searcher.search(material_id, desc=desc, search_web=search_web)


def compare_materials(materials: List[Dict[str, str]]) -> str:
    """
    比較多個材料

    Args:
        materials: [{"id": "COM000138", "desc": "成型膠/ELER-8-500C/φ48/90g/"}, ...]
    """
    searcher = MaterialSearcher()
    results = []
    for m in materials:
        result = searcher.search(m.get("id", ""), desc=m.get("desc", ""))
        results.append(result)
    return searcher.compare(results)


if __name__ == "__main__":
    # 測試
    print("=== 測試膠材搜索 ===")
    result = search_material("COM000138", desc="成型膠/ELER-8-500C/φ48/90g/")
    print(result.to_markdown())

    print("\n=== 測試線材搜索 ===")
    result = search_material("WIR000030", desc="GOLD WIRE/φ1.0mil/GLF/1000M/")
    print(result.to_markdown())

    print("\n=== 測試腳架搜索 ===")
    result = search_material("LEF000044", desc="腳架/SOT-363/OPTION 3/REEL/A42")
    print(result.to_markdown())

    print("\n=== 測試材料比較 ===")
    comparison = compare_materials([
        {"id": "COM000138", "desc": "成型膠/ELER-8-500C/φ48/90g/"},
        {"id": "COM000175", "desc": "成型膠/EME-G600FL/φ13/4.5g/"},
    ])
    print(comparison)
