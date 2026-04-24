# Architect Agent Memory

## System Structure Quick Reference (updated 2026-04-01)
- Active agents: query-runner, office-report-engine, report-builder, architect, questionnaire-response-drafter, table-reader
- Skills: legacy note says 4 auto-loaded (bom-rules, process-bom-semantics, reliability-testing, package-code); 2026-04-24 started splitting `reliability-testing` into `automotive-reliability-standards` + internal overlay
- Workflows: 5 (session_start, post_task, data_ingestion, knowledge_lifecycle, analysis_report)
- Validators: 6. Hooks: 3 (Stop, PostToolUse, SubagentStop). MCP: 3 COM + 2 plugin.
- Decisions: 127+, Learning notes: 48+, Projects: 8 (4 active)

## Key Architecture Principles (distilled from EVO-001~010)

- **Agent value = isolation** (large outputs, tool complexity, scan scope), not expertise. Leader has full Skills + Decisions + MEMORY.md for domain judgment.
- **Documents without validators always drift** (EVO-002). No manually-maintained docs unless a validator auto-generates or checks them.
- **Append-only .md files need write tools** (EVO-003): kb_writer.py for decisions/learning saves ~52K tokens/post_task vs Read+Edit.
- **Lazy loading beats preloading** (EVO-004): active_rules_summary.md on-demand, Skills on-demand for <40% usage.
- **Context window RAM is precious** (EVO-010): Global CLAUDE.md cleared, Skills moved to on-demand, SKILL.md details to references/.
- **Schema-First SQL** (EVO-009): db_schema.py generates SCHEMA, CLAUDE.md iron rule, query-runner Step 0.
- **kb_index.py is the knowledge API**: sync, search (semantic+keyword), validate, generate-summary/index. Never bulk-read decisions.md.

## Rejected Proposals (don't revisit)
- YAML per-decision files (grep-unfriendly)
- Agent for data ingestion (Leader needs full domain context)

## Previously Rejected, Now Revisited (EVO-012, 2026-04-01)
- SQLite as source of truth for decisions — previously rejected (migration cost), now user explicitly requests DB-first with phased migration
- Move all 4 core Skills to on-demand — previously rejected (>40% usage), now user wants zero auto-load + DB catalog instead

## Detailed EVO History
See `shared/kb/evolution_log.md` for full EVO-001 through EVO-010 details.

## /promote 2026-03-16
process-bom-semantics R5/R6/R8 strengthened + R14 new. See `promote-2026-03-16.md`.

## Telegram Integration Evaluation v2 (2026-03-23)
Hybrid approach (free local commands + `claude -p` headless AI). See `telegram-evaluation-2026-03-23.md`.

## Hermes-inspired improvements 2026-04-20
Shipped: coordinator `--script` pre-node injection, `scheduled_check.py` SILENT-unless-broken, kb_index.db FTS5 session_snapshots. See `hermes-inspired-improvements-2026-04-20.md`.

## Claude Code convergence 2026-04-23
Shipped: canonical `PROJECT_ID` / `PROJECT_ROOT` split, Windows conda launcher `shared/tools/conda-python.sh`, hardened `coordinator.py` CLI, real `/promote` agent, DB-first `post_task` / `knowledge_lifecycle` / `data_ingestion` contracts, and active-system `{P}` cleanup. Real Claude runs passed for `session_start`, `post_task`, and `knowledge_lifecycle`. See `claude-cli-convergence-2026-04-23.md`.

## Runtime compression pass 2026-04-24
Shipped after governance split stabilized:
- `ARCHITECTURE_COST_REVIEW.md` created to separate governance complexity from runtime complexity
- `post_task` slimmed first, because historical failures were dominated by protocol friction rather than domain reasoning
- `record_knowledge` now accepts compact single-item checklist proof via `summary` / `learning_ids`
- `check_memory_trigger` now uses explicit `snapshot_path` / `snapshot_id` instead of inferring today-local filename
- `record_decisions` validator no longer regenerates KB exports/index as a side effect; those moved back to `refresh_kb_exports`
- `kb.py export all` now also regenerates `active_rules_summary.md` and `shared/kb/_index.md`
- `session_start.read_project_state` now requires explicit `state_path` and validates it against active `{PROJECT_ID}`
- single-item checklist fast paths also added for `knowledge_lifecycle.classify_knowledge` and `data_ingestion.confirm_with_user`

Current intent:
- stop structural changes here and wait for several real Claude runs
- re-check `workflow_errors.log` / `workflow_runtime.jsonl` after new history accumulates
- if the new hotspot shifts, act on the new top failure instead of continuing speculative slimming

Expected next likely hotspot:
- `data_ingestion.ingest_to_db` artifact proof contract

See `runtime-compression-2026-04-24.md`.

## Deferred: Skill source-update governance (2026-04-24)
User explicitly raised a valid gap: skills derived from parsed standards/docs currently lack a full revision/update mechanism when source files change version or interpretation. Current system has fragments (`/promote`, `knowledge_lifecycle`, `.skill.yaml`, external/original file retention) but no complete loop for source mapping, version drift detection, revalidation, or deprecation. This must be revisited after the current skill/agent generic-vs-internal split is stabilized. First concrete case to revisit later: split `reliability-testing` into a generic standards core plus internal company overlay, then add minimal source governance metadata (`source_type`, `source_refs`, `source_version`, `last_verified`, optional `review_due` / `update_trigger`).

## Self-learning skill loop baseline (2026-04-24)
- `post_task` now scans mature learning nodes into `shared/workflows/state/promotion_queue.json`; this scan runs in coordinator Python, not as an auto-completing workflow node.
- New workflow: `skill_self_learning`. It evaluates a queued learning and may emit a proposal JSON, but it must not create or edit `SKILL.md`.
- Governance remains unchanged: actual Skill creation/update still goes through `/promote`, `architect`, and explicit user approval.
- Durable promotion state now lives in `eval_history.json` with suppression states:
  - `in_progress` 24h
  - `proposed` until promoted
  - `below_threshold` / `failed` / `unknown` 30d
  - `overlap` 7d
- Main scanner and validator scanner must stay semantically identical; if one path changes cooldown/overlap rules, the other must change with it.
- Queue/history writes now use per-file advisory locks. Treat `promotion_queue.json` and `eval_history.json` as coordination state, not casual scratch files.
