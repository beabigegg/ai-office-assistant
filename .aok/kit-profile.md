# AI-OFFICE Kit Profile

- kit_name: ai-office-kit
- runtime_role: agent-first office assistant
- source_of_truth:
  - shared/kb/knowledge_graph/kb_index.db
  - shared/workflows/definitions/
- startup_contract:
  - read project_state.md
  - load active_rules_summary
  - load open questions
  - generate session_context_bundle
- feedback_contract:
  - post_task updates project_state.md
  - durable decisions/learnings write to DB via kb.py
  - snapshots are retrieval surfaces, not authority
- provider_guidance:
  - AGENTS.md
  - .claude/CLAUDE.md
  - CODEX.md
