# BrownKit Methodology (EDCR)

**EDCR** = *Evidence → Discovery → Capabilities → Risk.*

BrownKit treats an existing codebase as **evidence to be extracted**, not as
a blank slate to impose architecture onto. Every capability, every control,
every test claim is tied to a specific file, line, or artifact. When a
signal cannot be collected, that absence is recorded as `not-collected` —
never fabricated as a default.

## Pipeline

```
/init → /scan → /discover → [/report] → /assess → /generate → /finish
```

Each stage has a dedicated command (`speckit.brownkit.<phase>`) and a
per-phase spec in [`phases/`](phases/).

## Design principles

1. **Evidence first, interpretation second.** `/scan` extracts raw signals
   from independent sources before `/discover` fuses them into a locked
   capability model. High confidence comes from cross-source corroboration.
2. **Explicit uncertainty.** When code alone cannot decide, **FLAG** — do
   not guess. Every FLAG carries the specific question a human must answer.
3. **`not-collected` is a first-class value.** Missing coverage, missing
   defect exports, missing flaky history — all recorded with a reason.
   Downstream scoring treats absent signals as `null`, not `0`.
4. **Stable IDs across runs.** `BC-001` means the same capability across
   discovery re-runs. Reports and prompts can safely reference IDs.
5. **Capability-aware risk.** Security and QA are evaluated *per
   capability*, because criticality, exposure, data sensitivity, and test
   posture differ. Generic scanning flattens what matters.
6. **Every conclusion is one click from raw evidence.** Reports carry
   source links; prompts and spec seeds cite finding ids.

## Phase-to-artifact map

| Phase | Writes |
|---|---|
| `/init`     | `context.json`, `workflow.json`, empty `evidence/` tree |
| `/scan`     | `candidates.md`, signal files under `discovery/signals/`, `security/*`, `qa/*` |
| `/discover` | `l1-capabilities.md`, `l2-capabilities.md`, `domain-model.md`, `coverage.md`, `blueprint-comparison.md`, `qa-context.json` |
| `/report`   | 4 always-emitted reports, 1 conditional (security), 3 side-cars when `/assess` has run |
| `/assess`   | STRIDE threat files, `vulnerabilities/catalog.json`, `control-map.json`, `risk-scores.json`, `qa-risk-scores.json`, `unified-risk-map.json`, `cross-capability-risks.json`, `gaps.json` |
| `/generate` | `capability-contexts/BC-*/`, `security-prompts.md`, `spec-seeds/BC-*.md` |
| `/finish`   | `acceptance-check.md`, `manifest.json`, per-team handoff bundles |

## Brownfield vs. greenfield

| Dimension | Brownfield (EDCR) | Greenfield |
|---|---|---|
| Starting point | Working code; signals extracted | Blank slate; architecture imposed |
| Discovery | Evidence-driven, multi-source | Architects' decisions, ADRs |
| Validation | Code-level proof required; `not-collected` explicit | Assumptions gated by review |
| Security | Embedded in `/discover` (D6) + `/assess` (per capability) | Added post-design via review |
| QA | Attached in `/discover` (D6a); measured per capability | Defined in delivery planning |
| Adaptation | Pipeline adjusts to available inputs | Model inflexible; deviations re-reviewed |
| Handoff | Domain + security + QA profile per team; scoped AI contexts | Architecture doc + team assignments |

## Acceptance criteria (14)

A complete run satisfies every item in the checklist enforced by `/finish`:

1. Every capability has a security context.
2. Every capability has a QA context with `not-collected` markers.
3. STRIDE threat model per capability.
4. Every vulnerability mapped to code and capability.
5. Security risk scoring complete for all capabilities.
6. QA risk scoring complete, or explicitly `unknown`.
7. Unified composite per capability with 1–3 **specific** drivers.
8. All findings traceable with confidence levels.
9. Cross-capability systemic risks identified.
10. File-to-capability coverage ≥ 90% (or actual reported with gaps).
11. Industry blueprint comparison complete.
12. Domain model with full code traceability.
13. All five reports generated; SDET report includes Not-Collected Summary.
14. All evidence preserved with full cross-referencing.
