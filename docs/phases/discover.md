# `/discover` — Capability Analysis, Verification & Locking

**Command**: `speckit.brownkit.discover` · **Spec**: [`commands/discover.md`](../../commands/discover.md)

Transforms raw candidates into a locked L1/L2 capability model with
security and QA context, plus a consolidated domain model and industry
blueprint comparison.

## Sub-steps

- **D1** — Cohesion / Coupling / Boundary clarity per candidate.
- **D2** — Action determination: `CONFIRM | SPLIT | MERGE | DE-SCOPE | FLAG`.
  Heuristics: delivery channels and infrastructure are not capabilities;
  deployment boundaries ≠ business boundaries; FLAG over false CONFIRM.
- **D3** — Coverage verification: file-to-capability mapping ≥ 90% target;
  orphan files attached, re-classified as infrastructure, or marked dead code.
- **D4** — Lock L1 with stable `BC-NNN` ids.
- **D5** — L2 decomposition with `OWNS / CREATES / MANAGES / TRACKS / READS`
  entity ownership and explicit conflict handling.
- **D6** — Security context attachment (data sensitivity, auth, exposure,
  criticality) derived from SS signals with documented rules.
- **D6a** — QA context attachment (coverage, automation, testability,
  defect profile, environments, strategy gaps) with first-class
  `not-collected` markers.
- **D7** — Consolidated `domain-model.md` with entity catalog, ownership
  matrix, dependency graph, bounded-context candidates, infrastructure
  classification.
- **D8** — Industry blueprint comparison (BIAN / TM Forum / ACORD / HL7 /
  ARTS / APQC). `MISSING` is context, not validation failure.

## Gates

8 acceptance gates. Most important: every candidate has a recorded D2
action; every entity has exactly one owner (or conflict is surfaced); every
L1/L2 has security + QA context blocks.
