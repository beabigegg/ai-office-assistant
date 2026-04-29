# Publishing Boundaries

This file defines two separate boundaries:

1. what is safe to push to remote git history
2. what is safe to ship inside a future `ai-office-kit` npm package

The two boundaries are related but not identical.

## Push To Remote

### Allowed

- framework code under `shared/tools/`, `shared/workflows/`, `shared/protocols/`
- common/generic agents marked `generic + tracked` in `AGENT_SKILL_GOVERNANCE.md`
  - `architect`
  - `query-runner`
  - `table-reader`
  - `skill-eval-grader`
  - `skill-eval-comparator`
  - `skill-eval-analyzer`
  - `ingest-exclusion-engine`
  - `office-report-engine`
- common/generic skills marked `generic + tracked` in `AGENT_SKILL_GOVERNANCE.md`
  - `automotive-reliability-standards`
  - `batch-refactor`
  - `docx-authoring`
  - `excel-operations`
  - `marp-pptx`
  - `pdf`
  - `pptx-authoring`
  - `pptx-operations`
  - `skill-creator`
  - `sqlite-operations`
  - `word-operations`
  - `xlsx-authoring`
- provider/runtime guidance templates
  - `AGENTS.template.md`
  - `CLAUDE.template.md`
  - `CODEX.template.md`
- reusable repo docs
  - `README.md`
  - `SETUP.md`
  - `AI_OFFICE_KIT.md`
  - `AGENT_SKILL_GOVERNANCE.md`
- deployment/bootstrap files
  - `init.py`
  - `.aok/`
  - `.env.example`
  - `.mcp.json.example`
- reusable project scaffold
  - `projects/_template/`
- tracked generic `.claude/agents/`, `.claude/commands/`, `.claude/skills-on-demand/` assets that are not local-only

### Forbidden

- secrets and machine-local config
  - `.env`
  - `.mcp.json`
  - `MASTER_API_KEY.txt`
- runtime knowledge/state
  - `shared/kb/**`
  - `shared/workflows/state/**`
  - `.claude/agent-memory/**`
- live project data outside `projects/_template/`
- local-only agents/skills/internal overlays that governance marks as non-tracked
  - examples:
    - `.claude/agents/report-builder.md`
    - `.claude/agents/promoter.md`
    - `.claude/agents/questionnaire-response-drafter.md`
    - `.claude/agents/bom-ingest-exclusion-applier.md`
    - `.claude/agents/ingest-archiver.md`
    - `.claude/agents/ingest-structure-detector.md`
    - `.claude/agents/ingest-db-writer.md`
    - `.claude/agents/ingest-validator.md`
    - `.claude/skills-on-demand/bom-rules/`
    - `.claude/skills-on-demand/graph-rag/`
    - `.claude/skills-on-demand/mes-report/`
    - `.claude/skills-on-demand/package-code/`
    - `.claude/skills-on-demand/process-bom-semantics/`
    - `.claude/skills-on-demand/questionnaire-response/`
    - `.claude/skills-on-demand/reliability-testing/`
    - `.claude/skills-on-demand/internal-reliability-practice/`
    - `.claude/skills-on-demand/plm-pdf-ingestion/`
    - `.claude/skills-on-demand/pptx-brand-master/`
- accidental local artifacts and logs

## NPM Package

The npm package boundary should be stricter than git.

### Allowed

- bootstrap and install surfaces
  - `init.py`
  - `README.md`
  - `SETUP.md`
  - `AI_OFFICE_KIT.md`
- common/generic agents marked `generic + tracked`
  - `.claude/agents/architect.md`
  - `.claude/agents/query-runner.md`
  - `.claude/agents/table-reader.md`
  - `.claude/agents/skill-eval-grader.md`
  - `.claude/agents/skill-eval-comparator.md`
  - `.claude/agents/skill-eval-analyzer.md`
  - `.claude/agents/ingest-exclusion-engine.md`
  - `.claude/agents/office-report-engine.md`
- common/generic skills marked `generic + tracked`
  - tracked generic `SKILL.md` / `.skill.yaml` content under `.claude/skills-on-demand/`
  - examples:
    - `automotive-reliability-standards`
    - `batch-refactor`
    - `docx-authoring`
    - `excel-operations`
    - `marp-pptx`
    - `pdf`
    - `pptx-authoring`
    - `pptx-operations`
    - `skill-creator`
    - `sqlite-operations`
    - `word-operations`
    - `xlsx-authoring`
- provider templates
  - `AGENTS.template.md`
  - `CLAUDE.template.md`
  - `CODEX.template.md`
- reusable framework runtime
  - `shared/workflows/**`
  - package-safe generic `shared/tools/**`
- reusable deployment metadata
  - `.aok/**`
- reusable template project
  - `projects/_template/**`

### Forbidden

- current-instance runtime state or memory
  - `shared/kb/**`
  - `shared/workflows/state/**`
  - `.claude/agent-memory/**`
- current-instance local guidance
  - `.claude/CLAUDE.md`
- local-only agents and local-only/internal skills
- internal overlays and company-branded assets
- secrets or machine-local config
  - `.env*`
  - `.mcp.json*`
- live project data outside `_template`
- office outputs, reports, DBs, binary work products
- accidental local artifacts/logs

## Current Local Noise

These are local artifacts and should not be pushed or packaged:

- `err紀錄.txt`
- `ai-officeprojects_templateworkspacebrand_spec.test.json`

## Current Intentional New Assets

These are framework/kit assets and should remain visible for commit review:

- `.aok/kit-profile.md`
- `.aok/runtime-contracts.md`
- `AGENTS.template.md`
- `CLAUDE.template.md`
- `CODEX.template.md`
- `AI_OFFICE_KIT.md`
- `shared/workflows/validators/check_open_questions_loaded.py`
- `shared/workflows/validators/check_session_context_bundle.py`
- `shared/workflows/validators/check_ready_context.py`
- `shared/workflows/validators/check_active_rules_loaded.py`

## Rule Of Thumb

Do not classify by folder name alone.

- `common/generic + tracked` assets are valid for both remote git and npm package
- `internal/local-only` assets must stay out
- when in doubt, the authority is the current governance baseline, not ad-hoc intuition
