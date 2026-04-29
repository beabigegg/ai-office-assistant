# CLAUDE.md

This repository is an AI-OFFICE-kit deployment.

## Runtime priorities

- Treat `shared/kb/knowledge_graph/kb_index.db` as the memory source of truth.
- Treat `shared/workflows/definitions/` as the enforced operating model.
- Treat `projects/<PROJECT_ID>/workspace/project_state.md` as the hot project surface.
- Treat `shared/kb/memory/*.md` as retrieval surfaces, not authority.

## Session start contract

- Read project state.
- Load project-scoped active decisions.
- Surface open questions explicitly.
- Generate and read `.session_context_bundle.md`.

## Feedback contract

- Durable decisions and learnings must be written via `shared/tools/kb.py`.
- `post_task` must update project state and refresh exports when KB changed.
- Do not hide uncertainty. If something is unresolved, leave an explicit trace in workflow outputs or project state.
