# CODEX.md

This repository uses the AI-OFFICE-kit runtime model for Codex CLI.

## Load Order

Read these surfaces in order:

1. `AGENTS.md`
2. `.aok/runtime-contracts.md`
3. `shared/workflows/definitions/`
4. provider-specific details in this file

## Required Behavior

- Restore project context through the session-start workflow before non-trivial project work.
- Treat `shared/kb/knowledge_graph/kb_index.db` as the memory authority.
- Treat `projects/<PROJECT_ID>/workspace/project_state.md` as the hot project surface.
- Treat `.active_rules_summary.md` and `.session_context_bundle.md` as generated startup projections, not authority.
- Surface open questions explicitly instead of proceeding as if the context were complete.

## Provider Notes

- Prefer the same runtime model as Claude Code CLI, not a parallel Codex-only operating model.
- Put shared behavior into common contracts first; use `CODEX.md` only for Codex-host specifics.
