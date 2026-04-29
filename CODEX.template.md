# CODEX.md

This repository uses the AI-OFFICE-kit runtime model.

## Working model

- `shared/workflows/definitions/` is the enforced workflow layer.
- `shared/kb/knowledge_graph/kb_index.db` is the memory authority.
- `projects/<PROJECT_ID>/workspace/project_state.md` is the hot per-project context.
- `projects/<PROJECT_ID>/workspace/.active_rules_summary.md` and `.session_context_bundle.md` are startup context projections.

## Required behavior

- Before non-trivial project work, restore context through the session-start workflow.
- Prefer `kb.py` over direct markdown reads for durable knowledge.
- Do not treat historical snapshots as current truth without checking active decision state.
- If open questions exist, surface them instead of proceeding as if the context were complete.
