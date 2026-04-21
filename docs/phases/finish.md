# `/finish` — Validation, Persistence & Handoff

**Command**: `speckit.brownkit.finish` · **Spec**: [`commands/finish.md`](../../commands/finish.md)

Closes the pipeline. Validates the 14 acceptance criteria, repairs broken
cross-references, and packages **per-team handoff bundles** sliced by
bounded-context ownership.

## Parts

- **A. Acceptance validation** — 14 criteria, each `pass | fail | n/a` with
  shortest-path-to-fix. Strict mode fails the phase on any miss; default
  mode reports and asks.
- **B. Cross-reference audit** — every `*Source: ...*` line resolves;
  every `BC-NNN`, threat id, vulnerability id, testability id exists.
  Broken refs are failure modes, not warnings — fix or remove the claim.
- **C. Handoff bundles** — one directory per team (from
  `--teams <path>` or derived from bounded-context candidates). Each bundle
  has its own README, per-capability context, filtered dev/SDET/security
  slices, spec seeds, and an open-questions file. Unassigned capabilities
  go to a synthetic `unassigned` team with a prominent warning.
- **D. Finalization** — emits `evidence/README.md` and
  `evidence/manifest.json` — a single machine-readable index for dashboards
  and CI.

## Gates

6 acceptance gates. Most important: `acceptance-check.md` lists all 14
criteria with a verdict; `manifest.json` lists every artifact; strict mode
enforces `pass` or documented `n/a`.
