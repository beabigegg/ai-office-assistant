#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

try:
    import yaml  # type: ignore
except ImportError:
    print("[ERROR] PyYAML is required.")
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent.parent
CLAUDE_DIR = ROOT / ".claude"
AGENTS_DIR = CLAUDE_DIR / "agents"
COMMANDS_DIR = CLAUDE_DIR / "commands"
SKILLS_DIR = CLAUDE_DIR / "skills-on-demand"
WORKFLOWS_DIR = ROOT / "shared" / "workflows" / "definitions"

TRACKED_GENERIC_SKILLS = {
    "excel-operations",
    "word-operations",
    "pptx-operations",
    "sqlite-operations",
    "marp-pptx",
    "xlsx-authoring",
    "docx-authoring",
    "pdf",
    "skill-creator",
    "pptx-authoring",
    "batch-refactor",
    "automotive-reliability-standards",
}

VALID_SCOPES = {"generic", "internal"}
VALID_TRACKING = {"tracked", "local-only"}

sys.path.insert(0, str((ROOT / "shared" / "tools").resolve()))
import sync_agent_rules  # type: ignore  # noqa: E402


def load_agent_names() -> Set[str]:
    names: Set[str] = set()
    for path in sorted(AGENTS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        match = re.search(r"^name:\s*([A-Za-z0-9_-]+)\s*$", text, re.MULTILINE)
        names.add(match.group(1) if match else path.stem)
    return names


def load_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        return {}
    try:
        return yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}


def load_workflow_delegate_refs() -> List[Tuple[str, str, str]]:
    refs: List[Tuple[str, str, str]] = []
    for path in sorted(WORKFLOWS_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for node in data.get("nodes", []):
            delegate_to = node.get("delegate_to")
            if delegate_to:
                refs.append((path.name, node.get("id", "<unknown>"), delegate_to))
    return refs


def scan_command_agent_refs() -> List[Tuple[str, int, str]]:
    refs: List[Tuple[str, int, str]] = []
    patterns = [
        re.compile(r"`([a-z0-9-]+)` agent"),
        re.compile(r"use ([a-z0-9-]+) agent", re.IGNORECASE),
        re.compile(r"使用 `([a-z0-9-]+)` agent"),
    ]
    for path in sorted(COMMANDS_DIR.glob("*.md")):
        for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            for pattern in patterns:
                for match in pattern.finditer(line):
                    refs.append((path.name, idx, match.group(1)))
    return refs


def audit_skills() -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warns: List[str] = []
    for skill_dir in sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir()):
        if skill_dir.name.startswith("_"):
            continue
        skill_md = skill_dir / "SKILL.md"
        skill_yaml = skill_dir / ".skill.yaml"
        if not skill_md.exists():
            errors.append(f"skill missing SKILL.md: {skill_dir.name}")
        md_meta = load_frontmatter(skill_md) if skill_md.exists() else {}
        scope = md_meta.get("scope")
        tracking = md_meta.get("tracking")
        if not skill_yaml.exists() and skill_dir.name in TRACKED_GENERIC_SKILLS:
            errors.append(f"skill missing .skill.yaml: {skill_dir.name}")
            continue
        if not skill_yaml.exists():
            if scope != "internal" or tracking != "local-only":
                warns.append(
                    f"skill metadata local-only or missing by policy: {skill_dir.name}"
                )
            continue
        try:
            meta = yaml.safe_load(skill_yaml.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            errors.append(f"invalid .skill.yaml: {skill_dir.name}: {exc}")
            continue
        yaml_name = meta.get("name")
        if yaml_name and yaml_name != skill_dir.name:
            errors.append(
                f"skill name mismatch: dir={skill_dir.name} yaml_name={yaml_name}"
            )
        if "triggers" not in meta:
            warns.append(f"skill missing triggers metadata: {skill_dir.name}")
        if scope not in VALID_SCOPES:
            errors.append(f"skill missing or invalid scope in SKILL.md: {skill_dir.name}")
        if tracking not in VALID_TRACKING:
            errors.append(f"skill missing or invalid tracking in SKILL.md: {skill_dir.name}")
        if skill_dir.name in TRACKED_GENERIC_SKILLS and (scope != "generic" or tracking != "tracked"):
            errors.append(f"tracked generic skill has inconsistent metadata: {skill_dir.name}")
    return errors, warns


def audit_agents() -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warns: List[str] = []
    for path in sorted(AGENTS_DIR.glob("*.md")):
        meta = load_frontmatter(path)
        scope = meta.get("scope")
        tracking = meta.get("tracking")
        if scope not in VALID_SCOPES:
            errors.append(f"agent missing or invalid scope: {path.name}")
        if tracking not in VALID_TRACKING:
            errors.append(f"agent missing or invalid tracking: {path.name}")
        if scope == "generic" and tracking != "tracked":
            warns.append(f"generic agent not marked tracked: {path.name}")
    return errors, warns


def audit_sync_state() -> List[str]:
    issues: List[str] = []
    rules_index = sync_agent_rules.collect_skill_rules()
    scope_keys = set(rules_index.keys())
    for key in sync_agent_rules.NODE_AGENT_MAP:
        scope_keys.add(key)
    for key in sorted(scope_keys):
        workflow, node_id = key
        contributions = rules_index.get(key, [])
        agent_basename = sync_agent_rules.NODE_AGENT_MAP.get(key) or f"{workflow}-{node_id}"
        agent_path = sync_agent_rules.AGENTS_DIR / f"{agent_basename}.md"
        rendered = sync_agent_rules.render_rules_block(workflow, node_id, contributions)
        changed, summary = sync_agent_rules.patch_agent_file(agent_path, rendered, apply=False)
        if "[MISSING]" in summary:
            issues.append(f"missing synced agent file: {agent_path.name} for {workflow}/{node_id}")
        elif changed:
            issues.append(f"agent embedded rules out of sync: {agent_path.name} for {workflow}/{node_id}")
    return issues


def main() -> int:
    errors: List[str] = []
    warns: List[str] = []

    agent_names = load_agent_names()

    for workflow_name, node_id, agent_name in load_workflow_delegate_refs():
        if agent_name not in agent_names:
            errors.append(
                f"workflow delegate target missing: {workflow_name}:{node_id} -> {agent_name}"
            )

    for command_name, line_no, agent_name in scan_command_agent_refs():
        if agent_name not in agent_names:
            errors.append(
                f"command agent reference missing: {command_name}:{line_no} -> {agent_name}"
            )

    skill_errors, skill_warns = audit_skills()
    errors.extend(skill_errors)
    warns.extend(skill_warns)
    agent_errors, agent_warns = audit_agents()
    errors.extend(agent_errors)
    warns.extend(agent_warns)

    warns.extend(audit_sync_state())

    print("== Agent Office Audit ==")
    print(f"agents: {len(agent_names)}")
    print(f"skills: {len([p for p in SKILLS_DIR.iterdir() if p.is_dir() and not p.name.startswith('_')])}")
    print(f"errors: {len(errors)}")
    print(f"warnings: {len(warns)}")

    if errors:
        print("\n[ERROR]")
        for item in errors:
            print(f"- {item}")

    if warns:
        print("\n[WARN]")
        for item in warns:
            print(f"- {item}")

    if not errors and not warns:
        print("\n[OK] No agent/skill/workflow consistency issues detected.")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
