#!/usr/bin/env python3
"""
SOT-LD (Single Source of Truth - Layered Dependency) Compliance Checker

Scans the repo for violations of the four-tier SOT-LD architecture:

    Tier 1: shared/tools/bom_parser.py        - cross-project shared parsers
    Tier 2: {P}/workspace/scripts/X_utils.py  - project-internal shared logic
    Tier 3: {P}/workspace/scripts/*.py        - report scripts
    Tier 4: vault/outputs/                    - pure presentation

Violations detected:
    V1 - Tier 1 function redefined (should import from bom_parser.py)
    V2 - Tier 2 function redefined (should import from ecr_bom_utils.py)
    V3 - Querying derived table bom_material_detail directly (forbidden)
    V4 - Hardcoded legacy path D:\\AI_test (warning)

Usage:
    python shared/tools/check_sot_ld.py
    python shared/tools/check_sot_ld.py --project ecr-ecn
    python shared/tools/check_sot_ld.py --strict      # V4 also counts as error

Exit code:
    0 = no V1/V2/V3 violations (V4 warnings allowed unless --strict)
    1 = has V1/V2/V3 violations (or any V4 in --strict mode)

Pure stdlib, no third-party dependencies.
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import Iterable

# ---------------------------------------------------------------------------
# Rule definitions
# ---------------------------------------------------------------------------

TIER1_FUNCTIONS: frozenset[str] = frozenset({
    "parse_compound_code",
    "parse_die_info",
    "parse_die_diagonal",
    "parse_thickness",
    "safe_float",
    "query_waf_rows",
    "query_wir_rows",
    "query_lef_rows",
    "query_com_rows",
    "query_glue_rows",
})

TIER2_FUNCTIONS: frozenset[str] = frozenset({
    "resolve_compound_code",
    "resolve_da_code",
    "resolve_wire_code_from_field",
    "resolve_wire_code_from_desc",
    "resolve_wire_code_from_bop",
    "resolve_lf_code_from_desc",
    "resolve_pkg_segment",
    "build_fpkc",
    "parse_control_code",
    "is_excluded",
})

# Files that are the canonical implementation - exempt from V1/V2 checks.
EXEMPT_RELATIVE_PATHS: frozenset[str] = frozenset({
    "shared/tools/bom_parser.py",
    "projects/ecr-ecn/workspace/scripts/ecr_bom_utils.py",
    # intake_bom.py is the data producer (writes std_bom); it cannot import bom_parser downstream.
    "projects/BOM資料結構分析/workspace/scripts/intake_bom.py",
})

# Path-segment exclusions (apply everywhere)
EXCLUDED_DIR_NAMES: frozenset[str] = frozenset({
    "__pycache__",
    "_template",
    "_deprecated",
    ".git",
    ".venv",
    "venv",
    "node_modules",
})

# V3: forbidden derived-table reference inside SQL strings.
V3_PATTERN = re.compile(
    r"\b(?:FROM|JOIN)\s+bom_material_detail\b",
    re.IGNORECASE,
)

# V4: legacy hardcoded path (matches both backslash and forward slash variants).
V4_PATTERN = re.compile(r"D:[\\/]AI_test", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Repo discovery
# ---------------------------------------------------------------------------


def find_repo_root(start: Path) -> Path:
    """Walk upward from `start` until a directory containing both
    `shared/` and `projects/` is found."""
    for candidate in (start, *start.parents):
        if (candidate / "shared").is_dir() and (candidate / "projects").is_dir():
            return candidate
    raise RuntimeError(
        f"Could not locate repo root (no shared/+projects/ ancestor of {start})"
    )


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------


def iter_python_files(root: Path, project: str | None) -> Iterable[Path]:
    """Yield all .py files under shared/tools and projects/* (or a single project)."""
    scan_roots: list[Path] = []

    if project is None:
        scan_roots.append(root / "shared" / "tools")
        projects_dir = root / "projects"
        if projects_dir.is_dir():
            for child in sorted(projects_dir.iterdir()):
                if child.is_dir() and child.name not in EXCLUDED_DIR_NAMES:
                    scan_roots.append(child)
    else:
        proj_path = root / "projects" / project
        if not proj_path.is_dir():
            raise RuntimeError(f"Project not found: {proj_path}")
        scan_roots.append(proj_path)

    for scan_root in scan_roots:
        if not scan_root.exists():
            continue
        for path in scan_root.rglob("*.py"):
            if not path.is_file():
                continue
            if any(part in EXCLUDED_DIR_NAMES for part in path.parts):
                continue
            name = path.name
            if name.startswith("test_") or name.endswith(".pyc"):
                continue
            yield path


# ---------------------------------------------------------------------------
# Violation record
# ---------------------------------------------------------------------------


class Violation:
    __slots__ = ("kind", "rel_path", "line", "message")

    def __init__(self, kind: str, rel_path: str, line: int, message: str) -> None:
        self.kind = kind
        self.rel_path = rel_path
        self.line = line
        self.message = message

    def format(self) -> str:
        return f"[{self.kind}] {self.rel_path}:{self.line}  {self.message}"


# ---------------------------------------------------------------------------
# Per-file checks
# ---------------------------------------------------------------------------


def read_text(path: Path) -> str | None:
    """Best-effort UTF-8 read. Return None on failure (file skipped)."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None
    except OSError:
        return None


def check_function_defs(
    source: str,
    rel_path: str,
    is_tier1_exempt: bool,
    is_tier2_exempt: bool,
) -> list[Violation]:
    """Walk the AST for top-level / nested FunctionDef nodes that collide with
    Tier 1 or Tier 2 reserved names."""
    violations: list[Violation] = []
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        # Don't fail the run on a single broken file; surface as a soft note.
        violations.append(
            Violation(
                kind="V1",  # parser error reuses V1 lane just for visibility
                rel_path=rel_path,
                line=exc.lineno or 0,
                message=f"SyntaxError while parsing: {exc.msg}",
            )
        )
        return violations

    # Only check module-level definitions; nested functions (e.g. helpers inside
    # another function) share a name by coincidence, not by architecture violation.
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        name = node.name
        if name in TIER1_FUNCTIONS and not is_tier1_exempt:
            violations.append(
                Violation(
                    kind="V1",
                    rel_path=rel_path,
                    line=node.lineno,
                    message=f"def {name} (duplicate of Tier 1 bom_parser.py)",
                )
            )
        elif name in TIER2_FUNCTIONS and not is_tier2_exempt:
            violations.append(
                Violation(
                    kind="V2",
                    rel_path=rel_path,
                    line=node.lineno,
                    message=f"def {name} (duplicate of Tier 2 ecr_bom_utils.py)",
                )
            )
    return violations


def check_v3_derived_table(source: str, rel_path: str) -> list[Violation]:
    violations: list[Violation] = []
    for lineno, line in enumerate(source.splitlines(), start=1):
        match = V3_PATTERN.search(line)
        if match:
            violations.append(
                Violation(
                    kind="V3",
                    rel_path=rel_path,
                    line=lineno,
                    message=f"{match.group(0)} (derived table — query std_bom + Tier 1 helpers instead)",
                )
            )
    return violations


def check_v4_legacy_path(source: str, rel_path: str) -> list[Violation]:
    violations: list[Violation] = []
    for lineno, line in enumerate(source.splitlines(), start=1):
        if V4_PATTERN.search(line):
            violations.append(
                Violation(
                    kind="V4",
                    rel_path=rel_path,
                    line=lineno,
                    message="hardcoded D:\\AI_test path",
                )
            )
    return violations


# ---------------------------------------------------------------------------
# Main scan
# ---------------------------------------------------------------------------


def scan(root: Path, project: str | None) -> list[Violation]:
    all_violations: list[Violation] = []

    for path in iter_python_files(root, project):
        rel_path = path.relative_to(root).as_posix()

        # Skip the checker itself (it intentionally references the rule names).
        if rel_path == "shared/tools/check_sot_ld.py":
            continue

        is_tier1_exempt = rel_path == "shared/tools/bom_parser.py"
        is_tier2_exempt = rel_path == "projects/ecr-ecn/workspace/scripts/ecr_bom_utils.py"
        # Treat both canonical files as fully exempt for both tiers.
        if rel_path in EXEMPT_RELATIVE_PATHS:
            is_tier1_exempt = True
            is_tier2_exempt = True

        source = read_text(path)
        if source is None:
            continue

        all_violations.extend(
            check_function_defs(source, rel_path, is_tier1_exempt, is_tier2_exempt)
        )
        all_violations.extend(check_v3_derived_table(source, rel_path))
        all_violations.extend(check_v4_legacy_path(source, rel_path))

    # Stable ordering: by file then line then kind.
    all_violations.sort(key=lambda v: (v.rel_path, v.line, v.kind))
    return all_violations


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="SOT-LD compliance checker (V1=Tier1 dup, V2=Tier2 dup, "
        "V3=derived-table query, V4=legacy path).",
    )
    parser.add_argument(
        "--project",
        type=str,
        default=None,
        help="Only scan a single project under projects/ (e.g. ecr-ecn).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat V4 warnings as errors (affects exit code).",
    )
    args = parser.parse_args(argv)

    here = Path(__file__).resolve()
    try:
        repo_root = find_repo_root(here.parent)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    try:
        violations = scan(repo_root, args.project)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    hard_violations = [v for v in violations if v.kind in ("V1", "V2", "V3")]
    warnings = [v for v in violations if v.kind == "V4"]

    for v in violations:
        print(v.format())

    if violations:
        print()  # blank line before summary
    print(
        f"Summary: {len(hard_violations)} "
        f"{'violation' if len(hard_violations) == 1 else 'violations'} (V1-V3), "
        f"{len(warnings)} {'warning' if len(warnings) == 1 else 'warnings'} (V4)"
    )

    if hard_violations:
        return 1
    if args.strict and warnings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
