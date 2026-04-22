"""
外部知識庫存取工具 v1.0

用途：存取從網路搜索學習的外部知識（材料規格、產業標準）
位置：shared/kb/external/

使用方式：
    from knowledge_store import KnowledgeStore

    store = KnowledgeStore()
    store.save_material("henkel_84-1lmisr4", data)
    result = store.get_material("henkel_84-1lmisr4")
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any


class KnowledgeStore:
    """外部知識庫存取器"""

    def __init__(self, base_path: str = None):
        if base_path:
            self.base_path = Path(base_path)
        else:
            # 自動偵測路徑
            current = Path(__file__).resolve()
            # 往上找到 shared/ 目錄
            for parent in current.parents:
                if (parent / "kb" / "external").exists():
                    self.base_path = parent / "kb" / "external"
                    break
            else:
                # 預設路徑：從腳本位置相對推導
                self.base_path = Path(__file__).resolve().parent.parent / "kb" / "external"

        self.materials_path = self.base_path / "materials"
        self.standards_path = self.base_path / "standards"

        # 確保目錄存在
        self.materials_path.mkdir(parents=True, exist_ok=True)
        self.standards_path.mkdir(parents=True, exist_ok=True)

    # ==================== 材料相關 ====================

    def save_material(self, material_id: str, data: Dict[str, Any],
                      subtype: str = "general") -> str:
        """
        存入材料資訊

        Args:
            material_id: 材料識別碼（如 "henkel_84-1lmisr4"）
            data: 材料資料字典
            subtype: 子類型目錄（adhesives/wires/leadframes）

        Returns:
            儲存路徑
        """
        # 確保有 meta 資訊
        if "meta" not in data:
            data["meta"] = {}

        data["meta"]["id"] = material_id
        data["meta"]["updated"] = datetime.now().strftime("%Y-%m-%d")
        if "created" not in data["meta"]:
            data["meta"]["created"] = data["meta"]["updated"]

        # 根據類型決定子目錄
        type_dirs = {
            "adhesive": "adhesives",
            "silver_epoxy": "adhesives",
            "molding_compound": "adhesives",
            "wire": "wires",
            "gold_wire": "wires",
            "copper_wire": "wires",
            "leadframe": "leadframes",
        }

        mat_type = data.get("meta", {}).get("subtype", subtype)
        subdir = type_dirs.get(mat_type, "general")

        save_dir = self.materials_path / subdir
        save_dir.mkdir(parents=True, exist_ok=True)

        file_path = save_dir / f"{material_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 更新索引
        self._update_materials_index()

        return str(file_path)

    def get_material(self, material_id: str) -> Optional[Dict[str, Any]]:
        """讀取材料資訊"""
        # 搜索所有子目錄
        for subdir in self.materials_path.iterdir():
            if subdir.is_dir():
                file_path = subdir / f"{material_id}.json"
                if file_path.exists():
                    with open(file_path, "r", encoding="utf-8") as f:
                        return json.load(f)
        return None

    def search_materials(self,
                         type: str = None,
                         manufacturer: str = None,
                         keyword: str = None) -> List[Dict[str, Any]]:
        """
        搜索材料

        Args:
            type: 材料類型（adhesive/wire/leadframe）
            manufacturer: 製造商
            keyword: 關鍵字搜索

        Returns:
            符合條件的材料列表
        """
        results = []

        for subdir in self.materials_path.iterdir():
            if not subdir.is_dir() or subdir.name.startswith("_"):
                continue

            for file_path in subdir.glob("*.json"):
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                meta = data.get("meta", {})

                # 過濾條件
                if type and meta.get("type") != type and meta.get("subtype") != type:
                    continue
                if manufacturer and manufacturer.lower() not in meta.get("manufacturer", "").lower():
                    continue
                if keyword:
                    text = json.dumps(data, ensure_ascii=False).lower()
                    if keyword.lower() not in text:
                        continue

                results.append(data)

        return results

    def list_materials(self) -> List[Dict[str, str]]:
        """列出所有材料（簡要資訊）"""
        materials = []
        for subdir in self.materials_path.iterdir():
            if not subdir.is_dir() or subdir.name.startswith("_"):
                continue
            for file_path in subdir.glob("*.json"):
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                meta = data.get("meta", {})
                materials.append({
                    "id": meta.get("id", file_path.stem),
                    "name": meta.get("name", ""),
                    "manufacturer": meta.get("manufacturer", ""),
                    "type": meta.get("type", subdir.name),
                })
        return materials

    def _update_materials_index(self):
        """更新材料索引"""
        index = {
            "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "materials": self.list_materials()
        }
        index_path = self.materials_path / "_index.json"
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

    # ==================== 標準相關 ====================

    def save_standard(self, standard_id: str, data: Dict[str, Any],
                      category: str = "general") -> str:
        """
        存入標準文件

        Args:
            standard_id: 標準識別碼（如 "aec-q100"）
            data: 標準資料字典
            category: 類別目錄（aec-q/jedec/iec）

        Returns:
            儲存路徑
        """
        if "meta" not in data:
            data["meta"] = {}

        data["meta"]["id"] = standard_id
        data["meta"]["updated"] = datetime.now().strftime("%Y-%m-%d")
        if "created" not in data["meta"]:
            data["meta"]["created"] = data["meta"]["updated"]

        save_dir = self.standards_path / category
        save_dir.mkdir(parents=True, exist_ok=True)

        file_path = save_dir / f"{standard_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self._update_standards_index()
        return str(file_path)

    def get_standard(self, standard_id: str) -> Optional[Dict[str, Any]]:
        """讀取標準文件"""
        for subdir in self.standards_path.iterdir():
            if subdir.is_dir():
                file_path = subdir / f"{standard_id}.json"
                if file_path.exists():
                    with open(file_path, "r", encoding="utf-8") as f:
                        return json.load(f)
        return None

    def get_test_requirements(self, standard_id: str, test_id: str = None) -> Optional[Dict]:
        """
        查詢標準中的測試要求

        Args:
            standard_id: 標準識別碼
            test_id: 測試項目 ID（如 "A2"），若為 None 則返回所有測試
        """
        standard = self.get_standard(standard_id)
        if not standard:
            return None

        test_groups = standard.get("test_groups", [])

        if test_id is None:
            return {"test_groups": test_groups}

        # 搜索特定測試
        for group in test_groups:
            for test in group.get("tests", []):
                if test.get("id") == test_id:
                    return {
                        "group": group.get("name"),
                        "test": test
                    }

        return None

    def list_standards(self) -> List[Dict[str, str]]:
        """列出所有標準（簡要資訊）"""
        standards = []
        for subdir in self.standards_path.iterdir():
            if not subdir.is_dir() or subdir.name.startswith("_"):
                continue
            for file_path in subdir.glob("*.json"):
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                meta = data.get("meta", {})
                standards.append({
                    "id": meta.get("id", file_path.stem),
                    "name": meta.get("name", ""),
                    "version": meta.get("version", ""),
                    "organization": meta.get("organization", ""),
                })
        return standards

    def _update_standards_index(self):
        """更新標準索引"""
        index = {
            "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "standards": self.list_standards()
        }
        index_path = self.standards_path / "_index.json"
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

    # ==================== 匯出 ====================

    def export_material_to_markdown(self, material_id: str) -> str:
        """將材料資訊匯出為 Markdown"""
        data = self.get_material(material_id)
        if not data:
            return f"找不到材料: {material_id}"

        meta = data.get("meta", {})
        lines = []
        lines.append(f"# {meta.get('name', material_id)}")
        lines.append("")
        lines.append("## 基本資訊")
        lines.append(f"| 項目 | 內容 |")
        lines.append(f"|------|------|")
        lines.append(f"| ID | {meta.get('id', '')} |")
        lines.append(f"| 製造商 | {meta.get('manufacturer', '')} |")
        lines.append(f"| 類型 | {meta.get('type', '')} / {meta.get('subtype', '')} |")
        lines.append(f"| 更新日期 | {meta.get('updated', '')} |")

        # 未固化特性
        if "uncured" in data:
            lines.append("")
            lines.append("## 未固化特性")
            lines.append("| 特性 | 值 | 單位 |")
            lines.append("|------|---|------|")
            for key, val in data["uncured"].items():
                if isinstance(val, dict):
                    lines.append(f"| {key} | {val.get('value', '')} | {val.get('unit', '')} |")
                else:
                    lines.append(f"| {key} | {val} | |")

        # 固化後特性
        if "cured" in data:
            lines.append("")
            lines.append("## 固化後特性")
            lines.append("| 特性 | 值 | 單位 |")
            lines.append("|------|---|------|")
            for key, val in data["cured"].items():
                if isinstance(val, dict):
                    lines.append(f"| {key} | {val.get('value', '')} | {val.get('unit', '')} |")
                else:
                    lines.append(f"| {key} | {val} | |")

        # 來源
        if "sources" in meta:
            lines.append("")
            lines.append("## 資料來源")
            for src in meta["sources"]:
                lines.append(f"- {src}")

        return "\n".join(lines)


# 便捷函數
def save_material(material_id: str, data: Dict) -> str:
    return KnowledgeStore().save_material(material_id, data)

def get_material(material_id: str) -> Optional[Dict]:
    return KnowledgeStore().get_material(material_id)

def save_standard(standard_id: str, data: Dict, category: str = "general") -> str:
    return KnowledgeStore().save_standard(standard_id, data, category)

def get_standard(standard_id: str) -> Optional[Dict]:
    return KnowledgeStore().get_standard(standard_id)


if __name__ == "__main__":
    # 測試
    store = KnowledgeStore()
    print(f"Base path: {store.base_path}")
    print(f"Materials: {store.list_materials()}")
    print(f"Standards: {store.list_standards()}")
