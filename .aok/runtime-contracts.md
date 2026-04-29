# Runtime Contracts

## Session Start

- Must restore project context from `projects/<PROJECT_ID>/workspace/project_state.md`
- Must load project-scoped active decisions
- Must surface unresolved questions explicitly
- Must generate `.session_context_bundle.md`

## Knowledge Writeback

- Durable decisions/learnings go to `shared/kb/knowledge_graph/kb_index.db`
- Markdown under `shared/kb/` is export / read surface, not authority
- `post_task` must refresh exports when new KB entries were written

## Uncertainty Handling

- Unknown / unresolved / blocked items must be surfaced in project state or workflow outputs
- Session ready status cannot hide open questions behind a clear state
