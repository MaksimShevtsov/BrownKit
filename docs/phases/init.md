# `/init` — Initialization & Context Setup

**Command**: `speckit.brownkit.init` · **Spec**: [`commands/init.md`](../../commands/init.md)

Establishes project identity, security scope, QA scope, and the evidence
store. No analysis — only elicitation, detection, and recording.

## Inputs (all optional)

- `brownkit-config.yml` in project root (from `config-template.yml`).
- `$ARGUMENTS` overrides (e.g., `--compliance PCI-DSS --coverage-report ...`).
- Pre-generated anchors: nDepend export, DB schema export, coverage report,
  flaky-test history, defect export, entry-point list. Each is optional;
  absent inputs are marked `not-collected` with a reason.

## Detected automatically (read-only)

Languages, build systems, package manifests, frontend presence, architecture
hint, CI platforms, common coverage-report paths.

## Written artifacts

- `evidence/context.json` — project + security_scope + qa_scope + weights + inputs.
- `evidence/workflow.json` — pipeline state tracker with `adaptations.*`:
  - `db_schema_analysis`: `skip` if no DB dependency detected and no export.
  - `frontend_analysis`: `skip` if `has_frontend=false`.
  - `coverage_source`: `report` if registered, else `proxy`.
- Empty evidence tree with `.gitkeep`.

## Gates

6 acceptance gates. Most important: every `inputs.*` is either an existing
path or `null` with a matching `notes[]` entry; no business-domain
assumptions are written (that's reserved for `/scan` and `/discover`).
