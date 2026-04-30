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
AGENT_MEMORY_DIR = CLAUDE_DIR / "agent-memory"
COMMANDS_DIR = CLAUDE_DIR / "commands"
SKILLS_DIR = CLAUDE_DIR / "skills-on-demand"
WORKFLOWS_DIR = ROOT / "shared" / "workflows" / "definitions"
HANDOFF_SCHEMAS_DIR = ROOT / "shared" / "workflows" / "handoff_schemas" / "data_ingestion"
PROCESS_BOM_SKILL_PATH = CLAUDE_DIR / "skills-on-demand" / "process-bom-semantics" / ".skill.yaml"
DOC_PATHS = [
    ROOT / "README.md",
    ROOT / "LOCAL_INTERNAL_SETUP.md",
    ROOT / "AGENTS.md",
    ROOT / "CODEX.md",
    ROOT / "SETUP.md",
    CLAUDE_DIR / "CLAUDE.md",
]

# Broader scan targets for stale-structure audits (file-path / placeholder /
# execution contract). These are files where residual violations have been
# observed historically; keep this list explicit so false positives stay bounded.
EXTENDED_SCAN_FILES = [
    ROOT / "init.py",
    ROOT / "README.md",
    ROOT / "SETUP.md",
    ROOT / "LOCAL_INTERNAL_SETUP.md",
    ROOT / "AGENTS.md",
    ROOT / "CODEX.md",
    CLAUDE_DIR / "CLAUDE.md",
    ROOT / "shared" / "protocols" / "skill_manifest_spec.md",
    ROOT / "shared" / "tools" / "TOOL_LINEAGE.md",
    ROOT / "shared" / "tools" / "check_sot_ld.py",
    ROOT / "shared" / "tools" / "sync_agent_rules.py",
    ROOT / "projects" / "_template" / "project.md",
    ROOT / "projects" / "_template" / "workspace" / "project_state.md",
]
EXTENDED_SCAN_GLOBS = [
    ("shared/kb/external", "*.json"),
]

# Paths allowed to still mention the legacy '.claude/skills/' directory for
# historic / compat reasons. Keep this set minimal.
LEGACY_SKILLS_PATH_ALLOWED = {
    CLAUDE_DIR / "agent-memory" / "architect" / "MEMORY.md",
}

# Paths allowed to still show bare `python shared/...` or `conda run` as a
# cross-platform installation hint (very narrow exception).
PYTHON_CONTRACT_ALLOWED = {
    ROOT / "README.md",  # README may show both shells for external readers
    ROOT / "environment.yml",
}

# Paths allowed to mention `{P}` / `conda run` in prose ONLY for the purpose of
# telling readers never to use those patterns. These files are prohibition
# documentation, not violations. Keep minimal and review when editing.
META_PROHIBITION_DOCS = {
    ROOT / "AGENTS.md",
    ROOT / "CODEX.md",
    CLAUDE_DIR / "CLAUDE.md",
}

FORBIDDEN_WORKFLOW_DELEGATES = {
    "report-builder": "generic Office work must route through office-report-engine",
    "bom-ingest-exclusion-applier": "generic exclusion execution must route through ingest-exclusion-engine",
}
STALE_ALIASES = {
    "response-drafter": "questionnaire-response-drafter",
    "ingest-exclusion-applier": "ingest-exclusion-engine",
}
RELIABILITY_COMPAT_ALLOWED_PATHS = {
    ROOT / "AGENTS.md",
    ROOT / "CODEX.md",
    ROOT / "LOCAL_INTERNAL_SETUP.md",
    CLAUDE_DIR / "agent-memory" / "architect" / "MEMORY.md",
    CLAUDE_DIR / "skills-on-demand" / "reliability-testing" / "SKILL.md",
    CLAUDE_DIR / "skills-on-demand" / "internal-reliability-practice" / "SKILL.md",
    CLAUDE_DIR / "skills-on-demand" / "automotive-reliability-standards" / "SKILL.md",
    ROOT / "shared" / "tools" / "decision_meta_backfill.py",
    ROOT / "shared" / "tools" / "kb_index.py",
}

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


def iter_text_matches(paths: List[Path], pattern: str) -> List[Tuple[Path, int, str]]:
    hits: List[Tuple[Path, int, str]] = []
    regex = re.compile(pattern)
    for path in paths:
        if not path.exists():
            continue
        for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if regex.search(line):
                hits.append((path, idx, line.strip()))
    return hits


def exact_token_pattern(token: str) -> str:
    escaped = re.escape(token)
    return rf"(?<![A-Za-z0-9_-]){escaped}(?![A-Za-z0-9_-])"


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


def load_text_agent_refs(agent_names: Set[str]) -> Set[str]:
    refs: Set[str] = set()
    scan_paths: List[Path] = [CLAUDE_DIR / "CLAUDE.md"]
    scan_paths.extend(sorted(COMMANDS_DIR.glob("*.md")))
    scan_paths.extend(sorted(SKILLS_DIR.glob("*/SKILL.md")))
    scan_paths.extend(sorted(WORKFLOWS_DIR.glob("*.json")))

    for path in scan_paths:
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for agent_name in agent_names:
            if re.search(exact_token_pattern(agent_name), text):
                refs.add(agent_name)
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


def audit_agent_activation_and_memory() -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warns: List[str] = []
    agent_names = load_agent_names()

    delegated_agents = {
        agent_name for _, _, agent_name in load_workflow_delegate_refs()
    }
    command_agents = {
        agent_name for _, _, agent_name in scan_command_agent_refs()
    }
    text_agents = load_text_agent_refs(agent_names)

    for path in sorted(AGENTS_DIR.glob("*.md")):
        meta = load_frontmatter(path)
        name = meta.get("name") or path.stem
        memory_scope = meta.get("memory")

        if memory_scope in {"project", "user"}:
            memory_dir = AGENT_MEMORY_DIR / name
            if not memory_dir.exists():
                warns.append(
                    f"agent declares memory but has no memory dir: {name} -> .claude/agent-memory/{name}/"
                )

        if name == "architect":
            continue

        if (
            name not in delegated_agents
            and name not in command_agents
            and name not in text_agents
        ):
            warns.append(
                f"agent has no workflow delegate_to, command reference, or documented activation surface: {name}"
            )

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


def audit_governance() -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warns: List[str] = []

    workflow_paths = sorted(WORKFLOWS_DIR.glob("*.json"))
    for workflow_name, node_id, agent_name in load_workflow_delegate_refs():
        reason = FORBIDDEN_WORKFLOW_DELEGATES.get(agent_name)
        if reason:
            errors.append(
                f"forbidden workflow delegate: {workflow_name}:{node_id} -> {agent_name} ({reason})"
            )

    stale_scan_paths = workflow_paths + sorted(COMMANDS_DIR.glob("*.md")) + DOC_PATHS
    for stale_name, replacement in STALE_ALIASES.items():
        for path, line_no, _ in iter_text_matches(stale_scan_paths, exact_token_pattern(stale_name)):
            warns.append(
                f"stale alias: {path.relative_to(ROOT)}:{line_no} uses {stale_name}; prefer {replacement}"
            )

    compat_scan_paths = workflow_paths + sorted(COMMANDS_DIR.glob("*.md")) + DOC_PATHS + [
        ROOT / "shared" / "tools" / "decision_meta_backfill.py",
    ]
    for path, line_no, _ in iter_text_matches(compat_scan_paths, exact_token_pattern("reliability-testing")):
        if path in RELIABILITY_COMPAT_ALLOWED_PATHS:
            continue
        warns.append(
            f"compat skill reference still active: {path.relative_to(ROOT)}:{line_no} uses reliability-testing"
        )

    return errors, warns


def _collect_extended_scan_paths() -> List[Path]:
    paths: List[Path] = [p for p in EXTENDED_SCAN_FILES if p.exists()]
    for rel_dir, pattern in EXTENDED_SCAN_GLOBS:
        base = ROOT / rel_dir
        if not base.exists():
            continue
        paths.extend(sorted(base.rglob(pattern)))
    return paths


def audit_structural_drift() -> Tuple[List[str], List[str]]:
    """Catch residual drift in file paths, placeholders, and execution contract.

    Rules enforced:
      D1 - legacy `.claude/skills/` path (new canonical: `.claude/skills-on-demand/`)
      D2 - bare `{P}` placeholder (must be `{PROJECT_ID}` or `{PROJECT_ROOT}`)
      D3 - `python shared/...` invocation (must be `bash shared/tools/conda-python.sh shared/...`)
      D4 - `conda run` invocation (must route via conda-python.sh)
    """
    errors: List[str] = []
    warns: List[str] = []

    scan_paths = _collect_extended_scan_paths()

    # D1: legacy skills path
    legacy_skills_re = re.compile(r"\.claude/skills/(?!on-demand)")
    for path in scan_paths:
        if path in LEGACY_SKILLS_PATH_ALLOWED:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for idx, line in enumerate(text.splitlines(), start=1):
            if legacy_skills_re.search(line):
                errors.append(
                    f"legacy skills path: {path.relative_to(ROOT)}:{idx} uses .claude/skills/ (expected .claude/skills-on-demand/)"
                )

    # D2: bare {P} placeholder (not {PROJECT_ID} / {PROJECT_ROOT})
    bare_p_re = re.compile(r"\{P\}")
    for path in scan_paths:
        if path in META_PROHIBITION_DOCS:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for idx, line in enumerate(text.splitlines(), start=1):
            if bare_p_re.search(line):
                errors.append(
                    f"legacy placeholder: {path.relative_to(ROOT)}:{idx} uses {{P}} (expected {{PROJECT_ID}} or {{PROJECT_ROOT}})"
                )

    # D3: bare `python shared/...` (should be bash shared/tools/conda-python.sh shared/...)
    python_shared_re = re.compile(r"(?<![./\w-])python\s+shared/")
    for path in scan_paths:
        if path in PYTHON_CONTRACT_ALLOWED:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for idx, line in enumerate(text.splitlines(), start=1):
            if python_shared_re.search(line):
                # conda-python.sh itself is the canonical form, skip it
                if "conda-python.sh" in line:
                    continue
                errors.append(
                    f"execution contract drift: {path.relative_to(ROOT)}:{idx} uses bare `python shared/...` (expected `bash shared/tools/conda-python.sh shared/...`)"
                )

    # D4: `conda run` invocation
    conda_run_re = re.compile(r"\bconda\s+run\b")
    for path in scan_paths:
        if path in PYTHON_CONTRACT_ALLOWED or path in META_PROHIBITION_DOCS:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for idx, line in enumerate(text.splitlines(), start=1):
            if conda_run_re.search(line):
                errors.append(
                    f"execution contract drift: {path.relative_to(ROOT)}:{idx} uses `conda run` (expected `bash shared/tools/conda-python.sh ...`)"
                )

    return errors, warns


def audit_data_ingestion_contracts() -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warns: List[str] = []

    workflow_path = WORKFLOWS_DIR / "data_ingestion.json"
    detect_schema_path = HANDOFF_SCHEMAS_DIR / "detect_structure.json"
    ingest_schema_path = HANDOFF_SCHEMAS_DIR / "ingest_to_db.json"
    post_schema_path = HANDOFF_SCHEMAS_DIR / "post_validation.json"

    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    nodes = {node.get("id"): node for node in workflow.get("nodes", [])}

    ingest_node = nodes.get("ingest_to_db", {})
    ingest_required = {
        item.get("output_key")
        for item in ingest_node.get("required_outputs", [])
        if item.get("output_key")
    }
    if "tables" not in ingest_required:
        errors.append("data_ingestion.ingest_to_db must require canonical output_key 'tables'")

    post_node = nodes.get("post_validation", {})
    post_required = {
        item.get("output_key")
        for item in post_node.get("required_outputs", [])
        if item.get("output_key")
    }
    if "tables" not in post_required:
        errors.append("data_ingestion.post_validation must require canonical output_key 'tables'")

    ingest_schema = json.loads(ingest_schema_path.read_text(encoding="utf-8"))
    ingest_required_schema = set(ingest_schema.get("output_schema", {}).get("required", []))
    if "tables" not in ingest_required_schema:
        errors.append("ingest_to_db handoff schema must require canonical field 'tables'")
    if "tables_written" in ingest_required_schema:
        errors.append("ingest_to_db handoff schema must not require legacy field 'tables_written'")

    post_schema = json.loads(post_schema_path.read_text(encoding="utf-8"))
    post_required_schema = set(post_schema.get("input_schema", {}).get("required", []))
    if "tables" not in post_required_schema:
        errors.append("post_validation handoff schema must require canonical field 'tables'")
    if "tables_written" in post_required_schema:
        errors.append("post_validation handoff schema must not require legacy field 'tables_written'")

    detect_schema = json.loads(detect_schema_path.read_text(encoding="utf-8"))
    proposed_table_props = (
        detect_schema.get("output_schema", {})
        .get("properties", {})
        .get("proposed_tables", {})
        .get("items", {})
        .get("properties", {})
    )
    if "exists_in_db" in proposed_table_props:
        errors.append("detect_structure must not encode DB-existence checks inside proposed_tables; keep detector DB-agnostic")

    if PROCESS_BOM_SKILL_PATH.exists():
        process_bom_meta = yaml.safe_load(PROCESS_BOM_SKILL_PATH.read_text(encoding="utf-8")) or {}
        for entry in process_bom_meta.get("applies_to_nodes", []):
            if not isinstance(entry, dict) or entry.get("workflow") != "data_ingestion":
                continue
            nodes = entry.get("nodes") or []
            if not isinstance(nodes, list):
                nodes = [nodes]
            if "ingest_to_db" in nodes:
                errors.append(
                    "process-bom-semantics must not inject rules into data_ingestion.ingest_to_db; keep BOM semantics before the generic writer boundary"
                )

    return errors, warns


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
    activation_errors, activation_warns = audit_agent_activation_and_memory()
    errors.extend(activation_errors)
    warns.extend(activation_warns)

    warns.extend(audit_sync_state())
    governance_errors, governance_warns = audit_governance()
    errors.extend(governance_errors)
    warns.extend(governance_warns)
    ingestion_errors, ingestion_warns = audit_data_ingestion_contracts()
    errors.extend(ingestion_errors)
    warns.extend(ingestion_warns)
    drift_errors, drift_warns = audit_structural_drift()
    errors.extend(drift_errors)
    warns.extend(drift_warns)

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
