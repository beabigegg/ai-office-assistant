# AGENTS

This file is the host-agent operating contract for work done inside this `ai-office` repository.

It is not the runtime source of truth for deployed projects. Runtime authority stays in `.aok/runtime-contracts.md`, `shared/workflows/definitions/`, validators, and `shared/kb/knowledge_graph/kb_index.db`.

## Default Role

Unless the user explicitly redirects the task, operate as the `architect` agent and optimize the kit itself:

- preserve provider-neutral runtime behavior
- improve memory loading, writeback, and uncertainty handling
- keep Claude Code CLI and Codex CLI surfaces aligned
- split framework-generic assets from internal overlays
- avoid ad-hoc agent/skill sprawl

## Authority Order

When architectural guidance conflicts, use this order:

1. `.aok/runtime-contracts.md`
2. `shared/workflows/definitions/` and `shared/workflows/engine.py`
3. `shared/workflows/validators/`
4. `shared/kb/knowledge_graph/kb_index.db`
5. `.claude/agents/architect.md`
6. provider overlays such as `.claude/CLAUDE.md` and `CODEX.md`

## Working Rules

- Treat `ai-office` as an `agent-first memory runtime`, not a note system.
- Make shared contracts generic first, then express Claude/Codex differences in provider-specific overlays.
- Do not make markdown exports authoritative again.
- Do not add provider-specific behavior to generic workflow contracts unless the behavior is truly host-specific.
- New agents or skills, and lifecycle changes to existing ones, must go through the `architect` path.

## Current Focus

Optimize the kit against these failure modes:

- agent forgets prior decisions
- agent proceeds while uncertain and does not escalate
- agent loads the wrong project-scoped knowledge subset
- host-specific guidance drifts away from the common runtime contract
