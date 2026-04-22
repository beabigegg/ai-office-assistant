# Tool Lineage Registry
<!-- 更新：2026-04-15 | SOT-LD 原則建立後首版 -->
<!-- 查詢方式：cat shared/tools/TOOL_LINEAGE.md 或 kb.py search "tool lineage" -->

## 架構原則（SOT-LD）

```
原始資料 ──→ Tier 1 shared/tools/ ──→ Tier 2 {P}/scripts/ ──→ Tier 3 報告腳本 ──→ Tier 4 輸出
   ↑                  ↑                        ↑                       ↑
 唯一入口          跨專案共用               專案內共用              本報告特有
 不可繞過          無狀態解析              業務邏輯轉換             篩選/聚合
```

**寫新腳本前必查**：
1. 我需要的解析函式 Tier 1 有嗎？→ 查 bom_parser.py
2. 業務邏輯 Tier 2 有嗎？→ 查 {P}_utils.py
3. 有就 import，無就新增到對應層，**禁止橫向複製**

---

## Tier 1 — shared/tools/（跨專案）

### bom_parser.py
| 屬性 | 內容 |
|------|------|
| **職責** | std_bom 原始資料解析（desc 格式、雙層查詢封裝） |
| **Consumes** | `bom.db::std_bom`（唯一原始資料來源） |
| **Produces** | die_size_mil, die_diagonal_mil, thickness_um, compound_code |
| **Key functions** | `parse_die_info()` `parse_die_diagonal()` `parse_compound_code()` `parse_thickness()` |
| **Dual-layer** | `query_waf_rows()` `query_wir_rows()` `query_lef_rows()` `query_com_rows()` `query_glue_rows()` |
| **Used by** | ecr_bom_utils.py, build_bom_material_detail.py, build_unified_families.py（待重構） |
| **規則** | 無業務邏輯（無 FPKC/ECR/ECN 概念）；所有函式無狀態 |

### intake_bom.py
| 屬性 | 內容 |
|------|------|
| **職責** | BOM 原始資料唯一入庫管道 |
| **實際位置** | `projects/BOM資料結構分析/workspace/scripts/intake_bom.py`（非 shared/tools） |
| **Consumes** | 原始 BOM CSV（`merged_output.csv`） |
| **Produces** | `bom.db::std_bom`（Tier 1 事實層） |
| **規則** | 唯一合法寫入 std_bom 的腳本；所有下游腳本禁止繞過 |
| **注意** | 雖歸類為 Tier 1 邏輯（原始入口），但檔案本身在 BOM 專案目錄下，勿誤以為在 shared/tools/ |

---

## Tier 2 — 專案內共用

### projects/ecr-ecn/workspace/scripts/ecr_bom_utils.py
| 屬性 | 內容 |
|------|------|
| **職責** | ECR/ECN 專案 FPKC 組件解析與零件分類 |
| **Consumes** | bom_parser.py (Tier 1), `ecr_ecn.db::master_part_list` |
| **Produces** | da_code, wire_code, lf_code, compound_code, pkg_seg, fpkc, control_code |
| **Key functions** | `resolve_da_code()` `resolve_wire_code_from_field/desc/bop()` `resolve_lf_code_from_desc()` `resolve_compound_code()` `resolve_pkg_segment()` `build_fpkc()` `parse_control_code()` `is_excluded()` |
| **Constants** | `COMPOUND_MAP` `PKG_SEGMENT_MAP` `CSR_PATTERN` `CSR_CUSTOMER_MAP` `EOL_STATUSES` |
| **Used by** | gen_sot23_op456_scope.py, gen_integrated_report_v1.py, build_unified_families.py |

---

## Tier 3 — 報告腳本（各自特有邏輯）

### gen_sot23_op456_scope.py
| 屬性 | 內容 |
|------|------|
| **職責** | SOT-23 OP4/5/6 腳架換料範圍 Excel 報告 |
| **Imports** | ecr_bom_utils.py (Tier 2)；直接查 std_bom（via bom_parser patterns） |
| **Consumes** | `bom.db::std_bom`, `ecr_ecn.db::master_part_list`, `history.sqlite3` |
| **Produces** | `vault/outputs/SOT23_OP456_Change_Scope.xlsx` |
| **Status** | 2026-04-15 重構完成：已移除 bom_material_detail 依賴 |

### gen_integrated_report_v1.py
| 屬性 | 內容 |
|------|------|
| **職責** | O-0003 + O-0004 四變更案整合分析報告（20 sheets） |
| **Imports** | 尚未重構（含自有 COMPOUND_MAP 等，待升級至 Tier 2） |
| **Consumes** | `bom.db::std_bom`, `ecr_ecn.db` |
| **Produces** | `vault/outputs/ECR_ECN_O0003_O0004_整合分析報告_v1_*.xlsx` |
| **Status** | ⚠️ 待重構：含 Tier 2 邏輯應移至 ecr_bom_utils.py |

### build_unified_families.py
| 屬性 | 內容 |
|------|------|
| **職責** | 建立 unified_tech_family 和 unified_family_assignment 表 |
| **Imports** | bom_parser.py (Tier 1), ecr_bom_utils.py (Tier 2) |
| **Consumes** | `bom.db::std_bom`, `ecr_ecn.db` |
| **Produces** | `ecr_ecn.db::unified_tech_family`, `ecr_ecn.db::unified_family_assignment` |
| **Status** | 2026-04-15 重構完成：COMPOUND_MAP / EOL_STATUSES 改 import ecr_bom_utils；_parse_die_info 改 import bom_parser |

---

## 衍生表（非事實來源）

### bom.db::bom_material_detail
| 屬性 | 內容 |
|------|------|
| **性質** | 衍生表（由 build_bom_material_detail.py 建立） |
| **用途** | 輔助探索、快速查詢；**不作為 production 腳本的資料來源** |
| **注意** | 中間表可能過期；分析腳本應直接查 std_bom + bom_parser（D-175） |

---

## 已知重構待辦

（無待辦項目）

## 已完成重構

| 腳本 | 完成日期 | 說明 |
|------|---------|------|
| `gen_sot23_op456_scope.py` | 2026-04-15 | 移除 bom_material_detail 依賴，改直查 std_bom + Tier 2 |
| `build_unified_families.py` | 2026-04-15 | COMPOUND_MAP / EOL_STATUSES / _resolve_compound_code / _parse_die_info 改 import Tier 1/2 |

## 已刪除廢棄腳本

| 腳本 | 刪除日期 | 原因 |
|------|---------|------|
| `derive_compound_code.py` | 2026-04-15 | 舊路徑(D:\AI_test)、無引用、parse_compound_code 重複定義 |
| `complete_pkg_codes.py` | 2026-04-15 | 舊路徑(D:\AI_test)、無引用、自有 COMPOUND_MAP |
| `gen_unified_report_v4.py` | 2026-04-15 | 直查 bom_material_detail；已由 v5/v6 邏輯取代 |
| `build_bom_material_detail.py` | 2026-04-15 | 無現役腳本消費其產出；表 bom_material_detail 同步 DROP |
