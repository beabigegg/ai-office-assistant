# Architecture Cost Review

Date: 2026-04-24
Baseline commit: `d15a715` (`Harden ingestion governance contracts`)

## Purpose

This review separates:

- governance complexity: useful for safety, maintainability, and auditability
- runtime complexity: paid every task in time, token, and context budget

The goal is **not** to make the system structurally flatter at all costs.
The goal is to keep governance precise while preventing runtime cost from
growing at the same rate.

## Current Signal Summary

### Heaviest workflow chains

By node count:

- `post_task`: 8 nodes
- `data_ingestion`: 7 nodes
- `session_start`: 7 nodes
- `analysis_report`: 5 nodes
- `knowledge_lifecycle`: 4 nodes

### Longest node instructions

Top runtime-heavy instructions by character length:

- `post_task.record_decisions`: 613
- `post_task.record_knowledge`: 603
- `knowledge_lifecycle.write_to_dynamic`: 558
- `post_task.check_memory_trigger`: 507
- `data_ingestion.post_validation`: 453
- `data_ingestion.confirm_with_user`: 447
- `data_ingestion.ingest_to_db`: 436
- `analysis_report.generate_report`: 426

### Largest prompt surfaces

Top prompt-sized assets by line count:

- `.claude/skills-on-demand/package-code/SKILL.md`: 353
- `.claude/agents/report-builder.md`: 229
- `.claude/agents/skill-eval-analyzer.md`: 227
- `.claude/skills-on-demand/excel-operations/SKILL.md`: 219
- `.claude/skills-on-demand/pptx-operations/SKILL.md`: 201

This means runtime cost is not just in workflows. A small number of large
skills/agents dominate context risk when loaded.

### Heaviest validators

By validator file length:

- `check_checklist.py`: 127
- `check_backlog_health.py`: 112
- `check_decisions.py`: 110
- `check_traceability.py`: 103
- `check_project_state.py`: 94

### Failure hotspots from workflow history

Most frequent failures in `shared/workflows/state/workflow_errors.log`:

- `post_task.record_knowledge` missing `checklist_responses`: 17
- `session_start.read_project_state` missing artifact proof: 8
- `post_task.record_decisions` KB consistency conflict: 4
- `data_ingestion.ingest_to_db` missing DB artifact proof: 2

This is important: the dominant failures are mostly **protocol friction**, not
domain reasoning failures.

## Main Findings

## 1. Runtime cost is being driven more by protocol friction than by domain work

The largest recurring failure class is missing structured outputs such as
`checklist_responses` and artifact proofs. This means users/agents are paying
extra rounds because the system requires exact protocol shape, not because the
underlying task is hard.

Implication:

- validator rigor is useful
- but repeated protocol failures are a runtime tax and a context tax

## 2. `post_task` is currently the biggest execution-cost hotspot

`post_task` is both the longest chain and the top failure source.

Cost drivers:

- 8 nodes
- long instructions
- multiple structured-output checkpoints
- several stateful validations
- frequent user/agent slips on `checklist_responses`

Implication:

- `post_task` should be treated as the highest-value target for runtime slimming
- not because its governance is wrong, but because it is the most expensive path

## 3. `data_ingestion` was structurally mixed, and is now better bounded, but still operationally heavy

Recent fixes improved governance:

- `ingest_to_db` now has a cleaner generic boundary
- `detect_structure` is now DB-agnostic
- canonical downstream fields were normalized to `db_path + operation_id + tables`

Remaining runtime cost:

- 7 nodes
- repeated structured handoffs
- multiple validation points
- confirm/exclude/ingest/validate each carry sizable instructions

Implication:

- governance direction is correct
- but runtime still needs a fast path for simple ingests

## 4. Prompt bloat is concentrated, not uniform

The repo is not generally oversized. The problem is that a small number of
skills/agents are very large. When one of those gets loaded, token and context
cost jump sharply.

This is good news because it means optimization can be focused.

Highest-risk large assets:

- `package-code`
- `report-builder`
- skill-eval agents
- `excel-operations`
- `pptx-operations`

Implication:

- we should optimize selective loading and lazy reference routing
- not broadly shrink every file

## 5. Governance and runtime are still too tightly coupled in some places

The repo has been improving this, but several patterns still show coupling:

- governance boundaries become separate runtime nodes
- audit rules are mirrored as prompt text in multiple places
- structured contracts are enforced, but sometimes via verbose node instructions

Implication:

- some rules belong only in audit/validator layers
- they do not need to be re-explained at runtime every time

## Cost Model

For this repo, runtime cost mainly comes from five things:

1. Node count
2. Instruction length
3. Prompt-size of invoked agent/skill assets
4. Structured-output friction
5. Repeated transfer of the same fields across nodes

This means a change is expensive if it does any of the following:

- adds another node to a high-frequency workflow
- adds another long markdown asset that must be loaded often
- introduces a new required structured output without reducing an old one
- duplicates the same rule in workflow JSON, agent markdown, and validator text

## Recommendations

## A. Keep governance fine-grained, but stop mirroring it 1:1 into runtime

Preferred pattern:

- governance can stay explicit in `AGENT_SKILL_GOVERNANCE.md`
- runtime should only pay for boundaries that isolate real risk

Action:

- before adding a node/agent, ask whether the rule can live in audit instead

## B. Add workflow fast paths for simple cases

Highest-value candidates:

- `data_ingestion`
- `post_task`

Examples:

- simple `data_ingestion`: archive + detect + confirm + ingest + validate
  with exclusion skipped unless explicitly needed
- simple `post_task`: collapse low-risk bookkeeping when no new DB/KB/report work occurred

## C. Compress protocol friction before adding more structure

Priority targets:

- `checklist_responses`
- artifact proof patterns
- repeated required output keys

Action:

- prefer canonical short keys
- keep validators backward-compatible where practical
- remove legacy shapes only after runtime history shows the new shape is stable

## D. Treat large skills as indexed knowledge, not default prompt payload

Especially:

- `package-code`
- `excel-operations`
- `pptx-operations`
- `process-bom-semantics`

Action:

- push more detail into referenced `references/*.md`
- keep top-level `SKILL.md` as routing + hard rules + loading guide
- avoid loading whole large skills unless the trigger is clearly hit

## E. Optimize `post_task` first

This is the strongest system-wide ROI item.

Candidate simplifications:

- merge low-value bookkeeping steps in runtime while keeping separate audit rules
- reduce repeated checklist protocol friction
- convert some reminders into post-run audit instead of per-node runtime burden

## F. Track runtime complexity as a first-class metric

The repo now has governance audits. It should eventually also track cost signals:

- workflow node counts
- top instruction lengths
- largest agent/skill prompts
- most frequent validator failures

This should become a periodic architecture review input, not ad-hoc inspection.

## What Should Happen Next

Recommended order:

1. Slim `post_task` runtime without weakening DB-first / KB-first enforcement
2. Design a `data_ingestion` fast path for non-policy-heavy imports
3. Shorten top-level large skills by pushing detail into lazy references
4. Add a lightweight runtime-cost audit command or report

## Progress Update (2026-04-24)

The first runtime-compression pass has now been applied after this review.

Completed:

- slimmed `post_task` instructions for:
  - `record_decisions`
  - `record_knowledge`
  - `check_memory_trigger`
  - `refresh_kb_exports`
- added compact single-item checklist paths for:
  - `post_task.record_knowledge`
  - `knowledge_lifecycle.classify_knowledge`
  - `data_ingestion.confirm_with_user`
- made `check_decisions` validator side-effect lighter by removing export/index regeneration
- moved KB export/index regeneration back to the canonical `kb.py export all` path
- stabilized `check_memory_trigger` with explicit `snapshot_path` / `snapshot_id`
- stabilized `session_start.read_project_state` with explicit `state_path` and validator enforcement

Not yet changed in this pass:

- `data_ingestion.ingest_to_db` artifact proof contract
- a true `data_ingestion` runtime fast path
- prompt-surface slimming for large skills such as `package-code`, `excel-operations`, `pptx-operations`

## Next Review Trigger

Do not continue speculative slimming immediately.

Instead, wait for several real Claude runs, then re-check:

- `shared/workflows/state/workflow_errors.log`
- `shared/workflows/state/workflow_runtime.jsonl`

The next round should be selected from the new highest-frequency failures, not from
the old pre-compression history.

## Non-Goals

These changes should **not**:

- remove governance boundaries that prevent real regressions
- collapse generic vs overlay distinctions back into mixed assets
- replace validator enforcement with prose-only instructions
- optimize token cost by reintroducing ambiguity

## Bottom Line

The current direction is structurally correct, but the next phase should focus on
**runtime compression**, not more decomposition.

The main problem is no longer "unclear architecture".
The main problem is "too much execution overhead per unit of real work" in a few
high-frequency paths.
