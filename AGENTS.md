# AGENTS

## Purpose

This repository extends Claude Code CLI into an office assistant. Future agent work must preserve Claude Code's native operating model instead of layering ad-hoc rules that fight it.

## Runtime Rules

- `context.project` in workflow commands must be the canonical `PROJECT_ID` only, never `projects/<name>` and never `projects/`.
- Use `PROJECT_ROOT = projects/<PROJECT_ID>/` only for file paths.
- Use `bash shared/tools/conda-python.sh ...` for repo Python commands so Windows + conda + UTF-8 behavior stays stable.
- `shared/workflows/state/current.json` is the only live workflow state file.
- `shared/kb/knowledge_graph/kb_index.db` is the source of truth. Markdown under `shared/kb/` is export/read surface, not authority.
- Agent / skill governance is defined in `AGENT_SKILL_GOVERNANCE.md`.
- New agents or skills may only be created by `architect` after the trigger conditions in `AGENT_SKILL_GOVERNANCE.md` are met.

## Workflow Contracts

- `session_start` must restore context without preloading large KB markdown files.
- `post_task` must end with DB-consistent KB exports when this round created new decisions or learnings.
- `knowledge_lifecycle.write_to_dynamic` must complete with `kb_entry_ids`.
- `data_ingestion` batch steps must preserve `operation_id`, `db_path`, and `tables` across validators.

## Current Convergence Baseline (2026-04-23)

- Canonical project-id/path split shipped: `PROJECT_ID` vs `PROJECT_ROOT`.
- `coordinator.py` CLI hardened: `help`, `show`, `list`, `--session`, `--artifacts`, explicit `Next:` commands, targeted `force_close --instance`.
- Windows conda launcher standardized via `shared/tools/conda-python.sh`.
- `/promote` now has a real `promoter` agent.
- `kb.py validate --warn-exit-zero` prevents WARN-only checks from looking like hard workflow failure.
- `post_task` now enforces DB-first evidence (`decision_ids`, `learning_ids`) and required `refresh_kb_exports`.
- `knowledge_lifecycle` validates exact `kb_entry_ids` in DB.
- `data_ingestion` now requires batch evidence for exclusion, ingest, schema refresh, and post-validation.

## Governance Baseline (2026-04-24)

- Agent / skill governance is now formalized in `AGENT_SKILL_GOVERNANCE.md`.
- Structural lifecycle authority is now explicitly assigned to `architect`.
- New generic engines were split out from internal overlays:
  - `office-report-engine` from `report-builder`
  - `ingest-exclusion-engine` from `bom-ingest-exclusion-applier`
  - `automotive-reliability-standards` from `reliability-testing`
- Internal assets are classified as `local-only`; generic assets are the tracked framework baseline.

### Current Transitional Items

- `compat`
  - `reliability-testing`
    Keep only as a compatibility shim. No new direct dependencies should point to it.

- `candidate_future_generic`
  - `ingest-archiver`
  - `ingest-structure-detector`
  - `ingest-db-writer`
  - `ingest-validator`
    These are still internal today, but structurally look like possible future generic ingestion pipeline components.

### Current Overlay Items

- `bom-ingest-exclusion-applier`
- `report-builder`
- `internal-reliability-practice`
- `pptx-template`

These are intended overlays, not future generic targets.

## Change Log

- `2026-04-24`
  - Added formal agent/skill governance and lifecycle rules.
  - Split three high-risk mixed assets into generic engine/core plus internal overlay:
    - `reliability-testing`
    - `bom-ingest-exclusion-applier`
    - `report-builder`
  - Added `system_audit.py` and kept runtime consistency green after the split.
  - Added a harness-native self-learning skill loop:
    - `post_task` now scans mature learning candidates into `promotion_queue.json`
    - new `skill_self_learning` workflow evaluates candidates and only writes approval proposals
    - actual Skill creation still stays behind `/promote` + `architect` + explicit user approval
  - Added durable promotion state:
    - `promotion_state.py` manages `promotion_queue.json` and `eval_history.json`
    - `in_progress` / `proposed` / cooldown outcomes prevent indefinite re-enqueueing
    - queue/history read-modify-write paths now use per-file advisory locking
  - Added skill-read usage tracking to feed promotion maturity from real SKILL.md usage.
  - Cleared the remaining architecture drift in framework docs/templates/tools:
    - standardized `.claude/skills-on-demand/` references across setup, templates, and protocol docs
    - standardized repo Python invocation examples to `bash shared/tools/conda-python.sh ...`
    - removed residual `{P}` placeholder usage from active framework guidance
  - Expanded `system_audit.py` from governance-only checks to structural-drift checks:
    - legacy skill path detection
    - legacy placeholder detection
    - Windows execution contract drift detection (bare repo-Python invocations / `conda run`)
    - bounded scan coverage for templates, protocol docs, tool docs, and external JSON references
  - Clarified that the four `data_ingestion` runtime agents remain active `candidate_future_generic` assets until only embedded-rule coupling remains before split graduation.

## Next Optimization Priorities

1. Real-world test `data_ingestion` on an actual new file import.
2. Add a system-wide audit command for workflow/agent/KB consistency.
3. Improve `kb.py` CLI discoverability so Claude stops guessing unsupported flags.
4. Keep shrinking prompt-layer ambiguity; prefer executable workflow hints over descriptive prose.

## Do Not Regress

- Do not reintroduce `{P}` as a mixed project-id/path placeholder.
- Do not make markdown files authoritative again.
- Do not rely on `conda run ...` for workflow execution on Windows.
- Do not add workflow documentation that is not backed by engine enforcement or validator checks.
- Do not create new agents or skills ad-hoc; route all such structural changes through `architect`.
