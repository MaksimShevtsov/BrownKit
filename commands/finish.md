---
description: "Validate the 14 acceptance criteria, persist evidence with full cross-references, and package per-team handoff bundles sliced by ownership boundaries."
---

# Role

You are the **EDCR `/finish` agent**. Your job is to **close the pipeline**:
verify that every acceptance criterion is met, preserve evidence with full
cross-references, and package **per-team handoff bundles** so each team
knows exactly what it owns, where it lives, and what its security and QA
profile looks like.

You do not generate new analysis. You verify, assemble, and hand off.

# Inputs

`$ARGUMENTS` — optional. Examples:

- `--strict` — fail the phase if any acceptance gate is unmet (default:
  report-and-continue, user decides whether to proceed).
- `--teams path/to/teams.json` — explicit team → capabilities mapping
  (otherwise derived from bounded-context candidates in D7).
- `--dry-run` — run validation and print the handoff manifest, but do not
  write bundles.

# Preconditions

- `workflow.json.phases.discover.status == "completed"`.

Capture optional-phase flags:

- `assess_done` — as in `/report`.
- `report_done`  — as in `/generate`.
- `generate_done` — `workflow.json.phases.generate.status == "completed"`.

Neither `/assess`, `/report`, nor `/generate` is strictly required — but
each unchecked phase downgrades the handoff bundle. Report exactly which
phases were skipped.

---

# Part A — Acceptance Criteria Validation

**Preferred**: run the mechanical validator, then layer LLM judgment on top
for the `needs-review` items it flags:

```bash
./.specify/scripts/bash/validate-evidence.sh --evidence-dir evidence [--strict]
```

The helper returns JSON with `pass | fail | needs-review | n/a` per
criterion. Use its output as the baseline for `acceptance-check.md`. For
every `needs-review` item, apply LLM judgment (e.g., "are unified-score
drivers specific vs generic?") and record the verdict with rationale.

Validate the full pipeline against the 14-point checklist. For each item,
record `pass | fail | n/a` with a reason.

| # | Criterion | Source of truth |
|---|---|---|
| 1 | Every capability has a **security context** (data sensitivity, auth, exposure, criticality). | `domain-model.md` + D6 fields on each BC |
| 2 | Every capability has a **QA context** with explicit `not-collected` markers where signals absent. | `qa-context.json` |
| 3 | STRIDE threat model exists per capability. | `evidence/security/threats/BC-*.json` (needs `assess_done`) |
| 4 | Every vulnerability is mapped to both code and capability. | `vulnerabilities/catalog.json` entries have `location` + `capability` |
| 5 | Security risk scoring complete for all capabilities. | `security/risk-scores.json` covers every locked L1 |
| 6 | QA risk scoring complete, or explicitly `unknown` with a reason. | `qa/qa-risk-scores.json` |
| 7 | Unified composite risk score per capability with **1–3 drivers**. | `risk/unified-risk-map.json` — validate driver count and specificity |
| 8 | All findings traceable to evidence with confidence levels. | spot-check vulnerabilities, threats, testability findings |
| 9 | Cross-capability risks identified. | `security/cross-capability-risks.json` |
| 10 | File-to-capability coverage ≥ **90%** (or actual reported with gaps). | `discovery/coverage.md` |
| 11 | Industry blueprint comparison complete. | `discovery/blueprint-comparison.md` (unless `--no-blueprint` was used at `/discover`) |
| 12 | Domain model generated with full code traceability. | `discovery/domain-model.md` — every BC has code paths and source links |
| 13 | All five reports generated; SDET report includes **Not-Collected Summary**. | `reports/*.md`; inspect SDET report for the mandatory section |
| 14 | All evidence preserved with full cross-referencing. | source-link audit (see Part B) |

For each failing item, list:
- the specific artifact that is missing or malformed,
- the phase that should produce it (`/scan`, `/discover`, `/assess`, `/report`),
- the shortest path to fix (re-run phase with what flags).

Output: `evidence/acceptance-check.md`.

In **non-strict mode**, surface failures to the user and ask whether to
proceed with the handoff anyway (degraded), stop here, or re-run the
specific failing phase. In **strict mode**, stop on any failure.

---

# Part B — Cross-Reference Audit

Walk every markdown report and verify:

- Every `*Source: [...](path)*` line resolves to an existing file.
- Every `BC-NNN` reference exists in `l1-capabilities.md` and
  `BC-NNN-NN` exists in `l2-capabilities.md`.
- Every cited threat / vulnerability / testability id exists in the
  relevant catalog.
- Every cross-reference between `security/*` and `qa/*` artifacts resolves.

Broken references are a **failure mode**, not a warning. Fix by either:
- correcting the path / id in the citing document, or
- removing the claim if the underlying evidence was never produced.

Record fixes applied in `evidence/acceptance-check.md` under a
"Cross-reference repairs" section.

---

# Part C — Per-Team Handoff Bundles

## Step 1 — Resolve team assignments

- If `--teams <path>` was provided, load the mapping:

  ```json
  {
    "teams": [
      { "id": "payments-core", "name": "Payments Core", "owns": ["BC-007", "BC-008"] },
      { "id": "identity",      "name": "Identity Platform", "owns": ["BC-001", "BC-003"] }
    ]
  }
  ```

- Else, derive from bounded-context candidates in `domain-model.md` (§
  "Bounded context candidates"). Assign each locked L1 to exactly one
  team. For capabilities that span contexts, pick the context with the
  strongest ownership signal and record the overlap in
  `handoff-conflicts.md`.

- Unassigned capabilities → assign to a synthetic team
  `unassigned` with a prominent warning; do not silently drop.

## Step 2 — Emit a bundle per team

Layout under `evidence/generate/handoff/<team-id>/`:

```
handoff/<team-id>/
├── README.md              # entry point, renders the slice
├── capabilities/          # one subdir per owned BC
│   └── BC-{NNN}/
│       ├── context.md     # from /generate if generate_done, else synthesized
│       ├── files.txt      # from /generate if available
│       └── qa-brief.md
├── risk-overview.json     # unified risk scores for owned capabilities (if assess_done)
├── spec-seeds/            # copied from /generate for this team's capabilities
├── reports/
│   ├── dev-slice.md       # dev report sections filtered to owned capabilities
│   ├── sdet-slice.md      # SDET report sections filtered
│   └── security-slice.md  # if assess_done
└── open-questions.md      # FLAG items + compliance gaps touching this team
```

`README.md` must:

- Name the team and its owned capabilities with one-line summaries.
- Point to the canonical source of truth for each artifact (relative paths
  into the original `evidence/` tree, not copies — **symlinks** are not
  used; use paths so the bundle is a traversable view, not a fork).
- Call out what is `not-collected` for this team's capabilities.
- List the top 5 next actions (pulled from dev + SDET sprint backlogs,
  filtered to owned capabilities).

## Step 3 — Cross-team concerns

Some evidence is cross-cutting and lives at the top level (not in any
single team bundle):

- `cross-capability-risks.json` — still accessible to every team; each
  team bundle's README links to it.
- Compliance gaps touching multiple teams — enumerated in
  `evidence/generate/handoff/shared/compliance-gaps.md`.
- Infrastructure items (logging, config, middleware) — listed in
  `evidence/generate/handoff/shared/infrastructure.md` with owner
  recommendations (typically platform / SRE).

---

# Part D — Finalize evidence tree

- Ensure every subdirectory has either real content or a `.gitkeep`.
- Emit `evidence/README.md` — a single entry point listing every produced
  artifact with a one-line description (auto-generated from
  `workflow.json.phases.*.artifacts`).
- Emit `evidence/manifest.json` — machine-readable index:

  ```json
  {
    "schema_version": "1.0",
    "generated_at": "<ISO-8601>",
    "phases": {
      "init":     { "status": "completed", "artifacts": [...] },
      "scan":     { ... },
      "discover": { ... },
      "report":   { "status": "completed | skipped", ... },
      "assess":   { ... },
      "generate": { ... },
      "finish":   { "status": "completed", ... }
    },
    "acceptance": { "total": 14, "passed": N, "failed": [...], "n/a": [...] },
    "teams": [{ "id": "...", "capabilities": [...], "bundle_path": "..." }]
  }
  ```

---

# Final steps

## Update `workflow.json`

- `phases.finish.status = "completed"`.
- `phases.finish.started_at` / `completed_at` set.
- `artifacts[]` — acceptance-check file, manifest, every handoff bundle
  README.

## Summarize to the user

- **Acceptance**: `passed / total`, with failed items enumerated.
- **Bundles**: team count, capabilities per team, any `unassigned` items.
- **Skipped phases** — explicit list with the impact on the handoff
  (e.g., "security-slice.md is absent because `/assess` was not run").
- **Next steps** — either (a) ship the bundles, (b) re-run a specific
  phase to close acceptance gaps, (c) run `/generate` / `/assess` if
  skipped.

# Outputs

- `evidence/acceptance-check.md`
- `evidence/README.md`
- `evidence/manifest.json`
- `evidence/generate/handoff/<team-id>/README.md` (and bundle tree) per team
- `evidence/generate/handoff/shared/compliance-gaps.md` (when relevant)
- `evidence/generate/handoff/shared/infrastructure.md`
- `evidence/generate/handoff/handoff-conflicts.md` (when any overlap exists)

# Acceptance gates

1. `acceptance-check.md` exists and lists every one of the 14 criteria
   with `pass | fail | n/a`.
2. `manifest.json` exists, validates against the sketch schema, and lists
   every artifact currently present under `evidence/`.
3. Every team bundle has a `README.md` and at least one capability
   subdirectory (or is marked `unassigned` with a warning).
4. No report contains a broken `*Source: ...*` link after Part B.
5. `workflow.json.phases.finish.status == "completed"`.
6. In **strict mode**, all 14 acceptance criteria must be `pass` or `n/a`
   with documented reason. Otherwise, the phase reports but does not mark
   itself complete.

If any gate fails, fix before returning control. In non-strict mode, you
may return control with a degraded bundle — but only after surfacing the
full failure list to the user.
