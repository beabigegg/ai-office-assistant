#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
TOOLS_DIR = ROOT / "shared" / "tools"
MANIFEST_PATH = TOOLS_DIR / "tool_manifest.json"
SCAN_SUFFIXES = {".py", ".sh", ".ps1"}
TEXT_SUFFIXES = {
    ".py", ".sh", ".ps1", ".md", ".json", ".yaml", ".yml", ".txt", ".sql"
}


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def iter_tool_files() -> list[Path]:
    files: list[Path] = []
    for path in TOOLS_DIR.rglob("*"):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts:
            continue
        if path.suffix.lower() in SCAN_SUFFIXES:
            files.append(path)
    return sorted(files)


def relpath(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def effective_meta(rel: str, manifest: dict) -> dict:
    if rel in manifest.get("tools", {}):
        return {**manifest["tools"][rel], "source": "tool"}

    policies = []
    for policy in manifest.get("path_policies", []):
        prefix = policy.get("prefix", "")
        if rel.startswith(prefix):
            policies.append((len(prefix), policy))
    if policies:
        _, best = max(policies, key=lambda item: item[0])
        meta = dict(best)
        meta["source"] = "policy"
        return meta

    return {"class": "unclassified", "status": "unclassified", "owner": "", "source": "none"}


def load_text_corpus() -> list[tuple[Path, str]]:
    corpus: list[tuple[Path, str]] = []
    scan_roots = [ROOT / ".claude", ROOT / "shared", ROOT / "README.md", ROOT / "AGENTS.md", ROOT / "CODEX.md"]
    for root in scan_roots:
        paths: list[Path]
        if root.is_file():
            paths = [root]
        else:
            paths = [p for p in root.rglob("*") if p.is_file()]
        for path in paths:
            if "__pycache__" in path.parts:
                continue
            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            corpus.append((path, text))

    # Project scan stays narrow on purpose: runtime scripts and hot state only.
    projects_dir = ROOT / "projects"
    if projects_dir.exists():
        for project_dir in [p for p in projects_dir.iterdir() if p.is_dir()]:
            workspace = project_dir / "workspace"
            if not workspace.exists():
                continue
            candidate_files = [
                workspace / "project_state.md",
                workspace / ".project_state.prev.md",
                workspace / "project_history.md",
            ]
            scripts_dir = workspace / "scripts"
            if scripts_dir.exists():
                candidate_files.extend([p for p in scripts_dir.rglob("*") if p.is_file()])
            for path in candidate_files:
                if not path.exists() or not path.is_file():
                    continue
                if path.suffix.lower() not in TEXT_SUFFIXES:
                    continue
                try:
                    text = path.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                corpus.append((path, text))
    return corpus


def reference_summary(tool_rel: str, corpus: list[tuple[Path, str]]) -> dict:
    tool_name = Path(tool_rel).name
    stem = Path(tool_rel).stem
    refs = []
    stem_pattern = re.compile(rf"(?<![A-Za-z0-9_-]){re.escape(stem)}(?![A-Za-z0-9_-])")
    path_pattern = re.compile(re.escape(tool_rel.replace("/", "\\")), re.IGNORECASE)
    posix_pattern = re.compile(re.escape(tool_rel), re.IGNORECASE)

    for path, text in corpus:
        rel = relpath(path)
        if rel == tool_rel:
            continue
        if tool_name in text or stem_pattern.search(text) or path_pattern.search(text) or posix_pattern.search(text):
            refs.append(rel)

    buckets = {
        "workflow_refs": [
            r for r in refs
            if r.startswith("shared/workflows/") and not r.startswith("shared/workflows/state/")
        ],
        "agent_refs": [r for r in refs if r.startswith(".claude/agents/")],
        "skill_refs": [r for r in refs if "/skills-on-demand/" in r],
        "project_refs": [r for r in refs if r.startswith("projects/")],
        "doc_refs": [r for r in refs if r.startswith("README") or r.startswith("AGENTS") or r.startswith("CODEX") or r.startswith(".claude/commands/") or r.startswith(".claude/CLAUDE.md")],
        "hook_refs": [r for r in refs if r == ".claude/settings.local.json"],
    }
    known = set()
    for values in buckets.values():
        known.update(values)
    buckets["other_refs"] = [r for r in refs if r not in known]
    buckets["total_ref_count"] = len(refs)
    return buckets


def build_rows() -> list[dict]:
    manifest = load_manifest()
    corpus = load_text_corpus()
    rows: list[dict] = []
    for path in iter_tool_files():
        rel = relpath(path)
        meta = effective_meta(rel, manifest)
        refs = reference_summary(rel, corpus)
        rows.append({
            "tool": rel,
            "class": meta.get("class", "unclassified"),
            "status": meta.get("status", "unclassified"),
            "owner": meta.get("owner", ""),
            "source": meta.get("source", "none"),
            "business_logic_level": meta.get("business_logic_level", ""),
            "notes": meta.get("notes", ""),
            "total_ref_count": refs["total_ref_count"],
            "workflow_ref_count": len(refs["workflow_refs"]),
            "agent_ref_count": len(refs["agent_refs"]),
            "skill_ref_count": len(refs["skill_refs"]),
            "project_ref_count": len(refs["project_refs"]),
            "doc_ref_count": len(refs["doc_refs"]),
            "hook_ref_count": len(refs["hook_refs"]),
            "workflow_refs": refs["workflow_refs"],
            "agent_refs": refs["agent_refs"],
            "skill_refs": refs["skill_refs"],
            "project_refs": refs["project_refs"],
            "doc_refs": refs["doc_refs"],
            "hook_refs": refs["hook_refs"],
            "other_refs": refs["other_refs"]
        })
    return rows


def audit_rows(rows: list[dict]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warns: list[str] = []
    for row in rows:
        tool = row["tool"]
        klass = row["class"]
        status = row["status"]
        refs = row["total_ref_count"]

        if klass == "unclassified" or status == "unclassified":
            errors.append(f"unclassified tool: {tool}")
            continue

        if status == "active" and refs == 0:
            warns.append(f"active tool has no repo references: {tool}")

        if klass == "core_shared" and row["workflow_ref_count"] + row["agent_ref_count"] + row["skill_ref_count"] + row["hook_ref_count"] == 0:
            warns.append(f"core_shared tool lacks workflow/agent/skill wiring evidence: {tool}")

        if status == "candidate_review" and refs <= 1:
            warns.append(f"candidate_review tool has weak reuse evidence: {tool}")

        if status == "maintenance_only" and row["workflow_ref_count"] > 0:
            warns.append(f"maintenance-only tool is referenced by workflow contract: {tool}")

        if status == "compat" and refs == 0:
            warns.append(f"compat tool appears unused and may be removable: {tool}")

    return errors, warns


def print_text(rows: list[dict], errors: list[str], warns: list[str]) -> None:
    class_counts = Counter(row["class"] for row in rows)
    status_counts = Counter(row["status"] for row in rows)

    print("== Tool Audit ==")
    print(f"manifest: {MANIFEST_PATH.relative_to(ROOT).as_posix()}")
    print(f"tools_scanned: {len(rows)}")
    print("class_counts:")
    for key, value in sorted(class_counts.items()):
        print(f"  {key}: {value}")
    print("status_counts:")
    for key, value in sorted(status_counts.items()):
        print(f"  {key}: {value}")

    print()
    print(f"{'tool':<48} {'class':<20} {'status':<18} {'refs':>4}")
    print("-" * 96)
    for row in rows:
        print(f"{row['tool']:<48} {row['class']:<20} {row['status']:<18} {row['total_ref_count']:>4}")

    if errors:
        print("\n[ERROR]")
        for item in errors:
            print(f"- {item}")

    if warns:
        print("\n[WARN]")
        for item in warns:
            print(f"- {item}")

    if not errors and not warns:
        print("\n[OK] No tool governance issues detected.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit shared/tools against tool_manifest.json.")
    parser.add_argument("--json", action="store_true", help="Emit rows/errors/warnings as JSON.")
    args = parser.parse_args()

    rows = build_rows()
    errors, warns = audit_rows(rows)

    if args.json:
        print(json.dumps({
            "rows": rows,
            "errors": errors,
            "warnings": warns
        }, ensure_ascii=False, indent=2))
    else:
        print_text(rows, errors, warns)

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
