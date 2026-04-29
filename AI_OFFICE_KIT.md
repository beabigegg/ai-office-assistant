# AI-OFFICE-kit

This repo is both:

1. a running AI office assistant framework
2. a reusable kit for deploying new AI-office instances

## Kit surfaces

- `AGENTS.md`
  Host-agent operating contract for architecture and repo work.
- `CODEX.md`
  Codex CLI provider entrypoint.
- `init.py`
  Bootstraps directories, environment, KB skeleton, project template, and kit metadata.
- `projects/_template/`
  Base project skeleton for new deployments.
- `.aok/`
  Kit profile and runtime contract metadata for deployed instances.
- `AGENTS.template.md`
  Template seed for generated host-agent guidance.
- `CLAUDE.template.md`
  Template seed for Claude-oriented runtime guidance.
- `CODEX.template.md`
  Template seed for Codex-oriented runtime guidance.

## Mapping from contract-driven-delivery-kit

- `cdd-kit init`
  `ai-office init.py`
- host/provider surfaces (`AGENTS.md`, `.claude/CLAUDE.md`, `CODEX.md`)
  same role here, with templates retained as seeds
- `contracts/` as machine-checkable delivery constraints
  mapped here to workflow definitions + validators + runtime contracts
- `specs/templates/`
  mapped here to `projects/_template/` plus kit metadata under `.aok/`
- context governance manifests
  mapped here to session-start context assembly and project-scoped memory bundle generation

## Runtime contracts

- Session context must be assembled from workflow + KB, not free-form note reading.
- Decisions and learnings are DB-first.
- Open questions are first-class runtime objects.
- Session projections are generated artifacts, not authority.

## Intended evolution path

- Split framework-generic assets from internal overlays.
- Keep provider guidance templated and deployment-oriented.
- Keep one common runtime contract and let Claude/Codex act as host overlays on top.
- Keep startup, writeback, and uncertainty handling machine-verifiable.
