# AI-OFFICE Kit Agents

Use these as the reusable agent surface for an AI-OFFICE deployment.

## Core runtime agents

- `architect`: owns structural evolution, governance, and baseline setting.
- `office-report-engine`: generic Office generation and orchestration engine.
- `query-runner`: isolates large SQL result handling.
- `table-reader`: extracts complex table structure from PDFs.
- `ingest-exclusion-engine`: generic exclusion executor for ingestion pipelines.

## Transitional / overlay agents

- `report-builder`: internal reporting overlay, not the generic default.
- `bom-ingest-exclusion-applier`: internal exclusion-policy overlay.
- `ingest-archiver`: ingestion runtime worker.
- `ingest-structure-detector`: ingestion runtime worker.
- `ingest-db-writer`: ingestion runtime worker.
- `ingest-validator`: ingestion runtime worker.

## Governance rule

New agents are architectural assets. Create, split, rename, or retire them only through the `architect` path.
