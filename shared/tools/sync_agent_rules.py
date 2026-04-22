#!/usr/bin/env python3
"""sync_agent_rules.py — keep node-agent embedded rules in sync with Skills.

Source of truth: each Skill's `.skill.yaml` (or SKILL.md frontmatter) may declare:

    applies_to_nodes:
      - workflow: data_ingestion
        nodes: [apply_exclusions, ingest_to_db]
        rules:
          - "Rule bullet 1"
          - "Rule bullet 2"

For each (workflow, node) combination, this tool aggregates the contributing
rules across all Skills and rewrites the `## 內嵌規則` section of the matching
node-agent markdown at:

    .claude/agents/ingest-<suffix>.md                 (default mapping)
    .claude/agents/<workflow>-<node_id>.md            (fallback)

The agent->node mapping is configurable via NODE_AGENT_MAP below.

Usage:
    python shared/tools/sync_agent_rules.py --dry-run
    python shared/tools/sync_agent_rules.py --apply
    python shared/tools/sync_agent_rules.py --workflow data_ingestion --apply

Design notes:
- The delimited section `## 內嵌規則` ... (up to next `## ` heading or EOF)
  is the only region rewritten. Everything else in the agent .md is preserved.
- If a target agent file is missing, we print a warning and skip (no creation).
- Exit code: 0 on success, 1 if any agent file is missing when --apply.
"""
from __future__ import annotations

import argparse
import difflib
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

try:
    import yaml  # type: ignore
except ImportError:
    print("[ERROR] PyYAML is required. `conda run -n ai-office pip install pyyaml`")
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent.parent
SKILLS_DIR = ROOT / ".claude" / "skills-on-demand"
AGENTS_DIR = ROOT / ".claude" / "agents"

# Default mapping: workflow + node_id -> agent filename (without .md)
NODE_AGENT_MAP: Dict[Tuple[str, str], str] = {
    ("data_ingestion", "archive_original"): "ingest-archiver",
    ("data_ingestion", "detect_structure"): "ingest-structure-detector",
    ("data_ingestion", "apply_exclusions"): "ingest-exclusion-applier",
    ("data_ingestion", "ingest_to_db"): "ingest-db-writer",
    ("data_ingestion", "post_validation"): "ingest-validator",
}

EMBEDDED_HEADING = "## 內嵌規則"
GENERATED_BEGIN = "<!-- AUTO-GENERATED:embedded_rules BEGIN -->"
GENERATED_END = "<!-- AUTO-GENERATED:embedded_rules END -->"


# ─── Skill discovery ────────────────────────────────────────────────

def _load_skill_yaml(skill_dir: Path) -> dict:
    """Load .skill.yaml if present. Fall back to SKILL.md frontmatter."""
    yaml_path = skill_dir / ".skill.yaml"
    if yaml_path.exists():
        try:
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
            return data
        except yaml.YAMLError as exc:
            print(f"[WARN] Skipping {yaml_path}: YAML parse error — {exc}")
            return {}

    # Fallback: try SKILL.md frontmatter
    md_path = skill_dir / "SKILL.md"
    if not md_path.exists():
        return {}
    text = md_path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return {}
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as exc:
        print(f"[WARN] Skipping {md_path}: frontmatter parse error — {exc}")
        return {}


def collect_skill_rules(workflow_filter: str | None = None
                        ) -> Dict[Tuple[str, str], List[Tuple[str, List[str]]]]:
    """Return {(workflow, node): [(skill_name, [rule1, rule2, ...]), ...]}."""
    out: Dict[Tuple[str, str], List[Tuple[str, List[str]]]] = defaultdict(list)

    if not SKILLS_DIR.is_dir():
        print(f"[ERROR] Skills directory not found: {SKILLS_DIR}")
        return out

    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        meta = _load_skill_yaml(skill_dir)
        if not meta:
            continue
        applies = meta.get("applies_to_nodes") or []
        if not isinstance(applies, list):
            continue
        skill_name = meta.get("name") or skill_dir.name

        for entry in applies:
            if not isinstance(entry, dict):
                continue
            wf = entry.get("workflow")
            nodes = entry.get("nodes") or []
            rules = entry.get("rules") or []
            if not wf or not nodes or not rules:
                continue
            if workflow_filter and wf != workflow_filter:
                continue
            if not isinstance(nodes, list):
                nodes = [nodes]
            for node_id in nodes:
                out[(wf, node_id)].append((skill_name, list(rules)))

    return out


# ─── Rule rendering ─────────────────────────────────────────────────

def render_rules_block(workflow: str, node_id: str,
                       contributions: List[Tuple[str, List[str]]]) -> str:
    """Render a markdown block for the embedded rules of a single node."""
    lines: List[str] = []
    lines.append(GENERATED_BEGIN)
    lines.append(f"<!-- synced from .claude/skills-on-demand/*/.skill.yaml "
                 f"applies_to_nodes[workflow={workflow}, node={node_id}] -->")
    lines.append(f"<!-- DO NOT EDIT BY HAND. Run: "
                 f"python shared/tools/sync_agent_rules.py --apply -->")
    lines.append("")

    if not contributions:
        lines.append("_(no skill contributions for this node yet — "
                     "add `applies_to_nodes` to a Skill's .skill.yaml)_")
        lines.append("")
    else:
        for skill_name, rules in sorted(contributions):
            lines.append(f"### From Skill: `{skill_name}`")
            lines.append("")
            for rule in rules:
                # Collapse internal newlines so a multi-line YAML literal becomes
                # a single Markdown bullet instead of one bullet per source line.
                flat = " ".join(s.strip() for s in rule.strip().splitlines() if s.strip())
                lines.append(f"- {flat}")
            lines.append("")

    lines.append(GENERATED_END)
    return "\n".join(lines)


# ─── Agent file patching ────────────────────────────────────────────

_SECTION_RE = re.compile(
    r"(^|\n)(##\s*內嵌規則\s*\n)(.*?)(?=\n##\s|\Z)",
    re.DOTALL,
)
_GEN_BLOCK_RE = re.compile(
    re.escape(GENERATED_BEGIN) + r".*?" + re.escape(GENERATED_END),
    re.DOTALL,
)


def patch_agent_file(agent_path: Path, rendered_block: str,
                     apply: bool) -> Tuple[bool, str]:
    """Rewrite the `## 內嵌規則` section. Returns (changed, diff_summary)."""
    if not agent_path.exists():
        return False, f"[MISSING] {agent_path} (skipping)"

    text = agent_path.read_text(encoding="utf-8")
    original = text

    if EMBEDDED_HEADING not in text:
        # Append the section at EOF
        new_text = text.rstrip() + "\n\n" + EMBEDDED_HEADING + "\n\n" + rendered_block + "\n"
    else:
        # Replace everything between the `## 內嵌規則` heading and the next
        # `## ` heading (or EOF) with the freshly rendered block.
        # Canonical form: heading line, one blank line, rendered block, trailing newline.
        def _replace(match: re.Match) -> str:
            prefix = match.group(1) or ""
            heading = match.group(2).rstrip("\n") + "\n"
            return prefix + heading + "\n" + rendered_block + "\n"

        new_text = _SECTION_RE.sub(_replace, text, count=1)

    if new_text == original:
        return False, f"[OK] {agent_path.name} — already in sync"

    diff = list(difflib.unified_diff(
        original.splitlines(keepends=True),
        new_text.splitlines(keepends=True),
        fromfile=str(agent_path) + " (current)",
        tofile=str(agent_path) + " (synced)",
        n=2,
    ))
    diff_summary = "".join(diff)

    if apply:
        agent_path.write_text(new_text, encoding="utf-8")
        return True, f"[WRITE] {agent_path.name}\n{diff_summary}"
    return True, f"[DIFF] {agent_path.name}\n{diff_summary}"


# ─── Main ───────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true",
                    help="Preview changes without writing (default).")
    ap.add_argument("--apply", action="store_true",
                    help="Write changes to agent files.")
    ap.add_argument("--workflow", default=None,
                    help="Restrict sync to a single workflow (e.g. data_ingestion).")
    args = ap.parse_args()

    if args.apply and args.dry_run:
        print("[ERROR] --apply and --dry-run are mutually exclusive.")
        return 2
    apply = bool(args.apply)

    rules_index = collect_skill_rules(workflow_filter=args.workflow)

    if not rules_index:
        print("[INFO] No skills declare `applies_to_nodes` for the requested scope.")
        return 0

    # Ensure every mapped node appears in output, even if no skill contributes
    scope_keys = set(rules_index.keys())
    for (wf, node) in NODE_AGENT_MAP:
        if args.workflow and wf != args.workflow:
            continue
        scope_keys.add((wf, node))

    missing_agents: List[str] = []
    any_changed = False

    for key in sorted(scope_keys):
        workflow, node_id = key
        contributions = rules_index.get(key, [])
        agent_basename = NODE_AGENT_MAP.get(key) or f"{workflow}-{node_id}"
        agent_path = AGENTS_DIR / f"{agent_basename}.md"

        block = render_rules_block(workflow, node_id, contributions)
        changed, summary = patch_agent_file(agent_path, block, apply=apply)
        print(f"\n=== {workflow} :: {node_id} → {agent_path.name} ===")
        if contributions:
            skill_tags = ", ".join(sorted({s for s, _ in contributions}))
            print(f"  skills: {skill_tags}")
            total = sum(len(r) for _, r in contributions)
            print(f"  rules: {total}")
        else:
            print("  skills: (none)")
        print(summary)

        if not agent_path.exists():
            missing_agents.append(str(agent_path))
        if changed:
            any_changed = True

    print("\n" + "=" * 60)
    if missing_agents:
        print(f"[WARN] {len(missing_agents)} agent file(s) missing:")
        for m in missing_agents:
            print(f"  - {m}")
        if apply:
            print("[HINT] Create the agent files first, then re-run --apply.")
            return 1

    if apply:
        print(f"[DONE] {'updated' if any_changed else 'nothing to update'}.")
    else:
        print("[DRY-RUN] No files written. Re-run with --apply to persist.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
