# `/scan` — Multi-Source Signal Extraction

**Command**: `speckit.brownkit.scan` · **Spec**: [`commands/scan.md`](../../commands/scan.md)

Extracts raw signals independently from **five** sources before any
interpretation. Confidence comes from cross-source corroboration, not
single-source depth.

## Part A — Capabilities (target 15–25 candidates)

- **S1 — Package structure**: domain-suggestive names vs generic vs
  layer/framework names.
- **S2 — Database schema** (skippable): table clusters, FK graph, stored
  procs by domain.
- **S3 — Backend entry points**: HTTP, jobs, consumers, CLI, RPC, webhooks.
  **Grouped by business operation, not technical type.**
- **S4 — Frontend entry points** (skippable): routes, navigation, feature
  folders.
- **S5 — Signal merge**: HIGH (3+ sources), MEDIUM (2), LOW (1). Duplicates
  flagged for `/discover`, not pre-merged.

## Part B — Security

- **SS1 — Static patterns**: auth/authz, credential storage (regex for
  hardcoded tokens), TLS enforcement, input validation presence/absence.
- **SS2 — Dependency manifests**: every manifest parsed; CVE lookup if a
  source is available, else `not-collected`.
- **SS3 — Configuration & infrastructure**: env divergence, exposed ports,
  CORS, ingress, DB security, logging config.
- **SS4 — Data sensitivity**: entities classified (PII / financial /
  authentication / health / regulatory).

## Part C — QA

- **QS1 — Test inventory**: every test classified by level
  (unit / integration / contract / e2e / performance / manual); mapped to
  files under test.
- **QS2 — Coverage**: parse the registered report (JaCoCo / Cobertura /
  Istanbul / coverlet / Go cover / coverage.py), else proxy
  `min(1.0, tested_files / significant_files)` per package — proxy is
  `confidence: LOW`.
- **QS3 — Testability**: `blocks / impedes / smell` with file:line +
  recommended seam.
- **QS4 — Environment & CI**: pipeline parse, flaky history if registered,
  declared-vs-covered env drift.

## Output roll-ups

- `evidence/discovery/candidates.md`
- `evidence/security/security-signals.json`, `security-dependencies.json`
- `evidence/qa/qa-signals.json`, `test-inventory.json`, `coverage/*`,
  `testability/*`, `environments/*`

## Gates

6 acceptance gates. Most important: candidate count in range, every
candidate traceable with confidence, every skipped sub-step recorded as
`not-collected` with reason, every coverage record carries `source` and
`confidence`.
