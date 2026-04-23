# AGENTS

## Purpose

This repository extends Claude Code CLI into an office assistant. Future agent work must preserve Claude Code's native operating model instead of layering ad-hoc rules that fight it.

## Runtime Rules

- `context.project` in workflow commands must be the canonical `PROJECT_ID` only, never `projects/<name>` and never `projects/`.
- Use `PROJECT_ROOT = projects/<PROJECT_ID>/` only for file paths.
- Use `bash shared/tools/conda-python.sh ...` for repo Python commands so Windows + conda + UTF-8 behavior stays stable.
- `shared/workflows/state/current.json` is the only live workflow state file.
- `shared/kb/knowledge_graph/kb_index.db` is the source of truth. Markdown under `shared/kb/` is export/read surface, not authority.

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
