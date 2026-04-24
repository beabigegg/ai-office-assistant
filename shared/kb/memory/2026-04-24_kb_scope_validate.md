# 2026-04-24 KB Scope And Validate Hardening

## Summary

- Enforced explicit KB scope on new learning writes.
- Added project-scoped KB search so system and project memories do not mix by default.
- Reduced `kb.py validate` false positives for architecturally related decisions.

## Changes

- `shared/tools/kb.py`
  - Normalize KB project labels before write/search.
  - Require `--project` for `add-learning`.
  - Add `search --project` filtering for keyword and vector retrieval.

- `shared/tools/kb_index.py`
  - Suppress L2 semantic-overlap warnings when a direct semantic edge already exists.
  - Ignore low-signal path/file tokens during target-overlap tokenization.

- `shared/workflows/definitions/knowledge_lifecycle.json`
  - Document that KB writes must pass explicit project/system scope.

- `shared/workflows/definitions/post_task.json`
  - Document that reusable learnings must be recorded with explicit scope.

## Rationale

- System architecture learnings and project learnings were both stored in the same KB, but write-time scope discipline was incomplete.
- `add-learning` previously allowed missing scope and silently defaulted to `ecr-ecn`, which polluted project memory with system-level knowledge.
- `validate` previously judged target overlap from text similarity alone, so adding graph edges did not suppress known-related decision pairs.

## Outcome

- New learning writes must declare intended scope.
- KB retrieval can now stay within `system`, `ai-office`, `shared`, or a project id.
- Known-related architectural decisions no longer raise overlap warnings solely because they share path-like tokens.
