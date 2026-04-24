# Agent / Skill Governance

## Purpose

This file defines the governance model for all Agent Office agents and skills.
It is the authority for:

- `generic` vs `internal` classification
- `tracked` vs `local-only` tracking policy
- `keep` / `overlay` / `compat` / `candidate_future_generic` / `template_only` lifecycle status
- creation rules for new agents and skills

Future agent/skill additions must follow this document. New agent/skill creation
is not an ad-hoc authoring task; it is an architectural decision owned by the
`architect` agent once trigger conditions are met.

## Core Model

### Scope

- `generic`
  Reusable across companies or repos. No company-specific workflow, template,
  policy, interpretation layer, or proprietary rulebook embedded.

- `internal`
  Any asset that contains company-specific process, reporting style, document
  interpretation, project heuristics, customer-facing conventions, or internal
  rule overlays.

### Tracking

- `tracked`
  Safe to keep under version control in this repo.

- `local-only`
  Must remain local and stay out of tracked repo history.

### Lifecycle Status

- `keep`
  Stable asset. Keep as-is.

- `overlay`
  Internal overlay that must sit on top of a generic engine/core.

- `compat`
  Transitional alias kept only to preserve backward compatibility. No new direct
  dependencies should be added.

- `candidate_future_generic`
  Currently internal, but structurally looks general enough that a future
  generic split may be justified.

- `template_only`
  Scaffolding/template asset, not a runtime skill/agent.

## Creation Authority

Only the `architect` agent may create, split, rename, merge, or retire agents
and skills.

Leader or other agents may:

- propose a new agent/skill
- identify repeated pain or drift
- collect examples

But they must hand the structural change to `architect`.

## Trigger Conditions

### New Agent

Create a new agent only when **all** are true:

1. A repeated task/delegation pattern has appeared `3+` times
2. Existing agents cannot absorb the work without becoming misleading
3. The task benefits from tool isolation, output isolation, or a dedicated role
4. The agent boundary can be described clearly in one sentence

Typical valid triggers:

- a workflow node has become a stable delegation point
- a repeated high-volume task keeps polluting leader context
- a reusable execution engine can be separated from an internal overlay

### New Skill

Create a new skill only when **all** are true:

1. A stable rule set or procedure has appeared `3+` times
2. Existing skills cannot absorb it cleanly
3. The content is durable enough to justify maintenance
4. Clear triggers and "NOT" boundaries can be written

If the content is only:

- an execution detail of one agent
- a one-off project workaround
- a tiny extension of an existing generic skill

then do **not** create a new skill.

## Preferred Resolution Order

Before creating anything new, the `architect` agent must evaluate in this order:

1. Can the behavior be absorbed into an existing generic skill?
2. Can it be handled inside an existing generic agent?
3. Should it be an internal overlay on top of an existing generic asset?
4. Only then consider creating a new agent or skill

## Required Follow-up When Renaming / Splitting

Whenever an agent or skill is renamed, split, or reclassified, `architect` must
update all affected references, including where applicable:

- `.claude/CLAUDE.md`
- `shared/workflows/definitions/*.json`
- `shared/tools/sync_agent_rules.py`
- `shared/tools/system_audit.py`
- related `SKILL.md` / `.skill.yaml`
- related agent markdown
- governance tables in this file
- architect memory if the change establishes a new baseline

## Current Governance Table

### Agents

| Name | Scope | Tracking | Status | Notes |
|------|-------|----------|--------|-------|
| `architect` | generic | tracked | keep | structural authority |
| `query-runner` | generic | tracked | keep | large-result SQL isolation |
| `table-reader` | generic | tracked | keep | complex PDF table extraction |
| `skill-eval-grader` | generic | tracked | keep | skill evaluation pipeline |
| `skill-eval-comparator` | generic | tracked | keep | skill evaluation pipeline |
| `skill-eval-analyzer` | generic | tracked | keep | skill evaluation pipeline |
| `ingest-exclusion-engine` | generic | tracked | keep | generic apply_exclusions executor |
| `office-report-engine` | generic | tracked | keep | generic Office report orchestrator |
| `bom-ingest-exclusion-applier` | internal | local-only | overlay | BOM/ECR exclusion-policy overlay |
| `report-builder` | internal | local-only | overlay | company reporting/template overlay |
| `questionnaire-response-drafter` | internal | local-only | keep | customer/internal drafting |
| `promoter` | internal | local-only | keep | local KB/skill promotion policy |
| `ingest-archiver` | internal | local-only | candidate_future_generic | pure copy+sha256; graduate when embedded-rule sync removes internal coupling |
| `ingest-structure-detector` | internal | local-only | candidate_future_generic | structure probe; graduate once detector drops internal format heuristics |
| `ingest-db-writer` | internal | local-only | candidate_future_generic | idempotent writer; graduate once write contract is fully schema-driven |
| `ingest-validator` | internal | local-only | candidate_future_generic | post-ingest checks; graduate once validators are externalised to handoff schemas |

Graduation criterion for the four ingest agents above: they keep `internal +
candidate_future_generic` until their **sole remaining internal surface is the
embedded-rule block injected by `sync_agent_rules.py`**. Once an agent's body
contains no company-specific format heuristics, file-path conventions, or DB
naming assumptions, `architect` splits it into a generic engine + internal
overlay (same pattern as `ingest-exclusion-engine` + `bom-ingest-exclusion-applier`).

### Skills

| Name | Scope | Tracking | Status | Notes |
|------|-------|----------|--------|-------|
| `automotive-reliability-standards` | generic | tracked | keep | generic standards core |
| `batch-refactor` | generic | tracked | keep | reusable refactor patterns |
| `docx-authoring` | generic | tracked | keep | new Word generation |
| `excel-operations` | generic | tracked | keep | existing Excel incremental editing |
| `marp-pptx` | generic | tracked | keep | fast PPT/PDF route |
| `pdf` | generic | tracked | keep | PDF operations |
| `pptx-authoring` | generic | tracked | keep | new PPT generation |
| `pptx-operations` | generic | tracked | keep | existing PPT editing |
| `skill-creator` | generic | tracked | keep | skill authoring system |
| `sqlite-operations` | generic | tracked | keep | SQLite/Windows execution rules |
| `word-operations` | generic | tracked | keep | existing Word editing |
| `xlsx-authoring` | generic | tracked | keep | new Excel generation |
| `bom-rules` | internal | local-only | keep | company BOM rulebook |
| `graph-rag` | internal | local-only | keep | internal KG workflow |
| `internal-reliability-practice` | internal | local-only | overlay | company reliability overlay |
| `mes-report` | internal | local-only | keep | internal reporting system |
| `mil-std-750` | internal | local-only | keep | internalized standards usage |
| `package-code` | internal | local-only | keep | company package-code semantics |
| `plm-pdf-ingestion` | internal | local-only | keep | internal PLM ingestion practices |
| `pptx-template` | internal | local-only | overlay | company PPT template route |
| `process-bom-semantics` | internal | local-only | keep | company BOM/process semantics |
| `questionnaire-response` | internal | local-only | keep | customer/internal response workflow |
| `reliability-testing` | internal | local-only | compat | no new direct dependencies |
| `_skill_template` | n/a | n/a | template_only | not a runtime skill |

## Immediate Rules

- No new direct dependency should target `reliability-testing`
- No workflow should use `report-builder` as the generic Office default
- No workflow should use `bom-ingest-exclusion-applier` as the generic executor
- New generic Office work should prefer `office-report-engine`
- New generic exclusion execution should prefer `ingest-exclusion-engine`

## Data Ingestion Transitional Contracts

The following four agents remain `candidate_future_generic`, but their boundaries
must stay explicit so future splits do not drift:

### `ingest-archiver`

- Generic core: copy into `vault/originals/`, collision-safe naming, SHA-256, size
- Must remain a pure file operation; no parsing, no interpretation, no project policy
- Split blocker today: still implemented as a local runtime agent instead of a tracked generic engine

### `ingest-structure-detector`

- Generic core: file-format detection, sheet/column/type/row-count/merged-cell reporting
- Must report structural facts only; domain semantics and final target-table choice stay outside this node
- Heuristic table-name suggestions are allowed, but DB existence/alignment checks do not belong in the detector
- Split blocker today: coverage and runtime contract are still local-only even though the behavior is mostly generic

### `ingest-db-writer`

- Canonical downstream contract is `db_path` + `operation_id` + `tables`
- Detailed per-table write stats may exist, but only as supplemental output
- Generic core: SQLite write path, tracking columns, transactionality, idempotency
- Split blocker today: internal BOM/process rules are still embedded in the local agent, so the write-engine boundary is not yet clean

### `ingest-validator`

- Canonical downstream contract is `db_path` + `operation_id` + `tables` + `checklist_responses`
- Preferred `checklist_responses` shape is list-of-dict; validators may keep backward compatibility for legacy dict outputs
- Generic core: batch-scoped read-only validation, evidence capture, structured checklist output
- Split blocker today: checklist policy and thresholds are still carried as local workflow assets rather than a tracked generic validation engine

## Review Policy

`architect` should re-run this governance review whenever:

- a new agent/skill is proposed
- a split/rename is requested
- a workflow starts depending on an internal asset directly
- a local-only asset begins to look reusable across domains
