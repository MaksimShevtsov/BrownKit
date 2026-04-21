# `/assess` — Security & QA Risk Assessment

**Command**: `speckit.brownkit.assess` · **Spec**: [`commands/assess.md`](../../commands/assess.md)

## Phases

- **Phase 1 — STRIDE** per capability (Spoofing / Tampering / Repudiation /
  Information Disclosure / DoS / Elevation of Privilege). Absent categories
  get an explicit rationale, not omission.
- **Phase 2 — Vulnerability detection**, classified `Confirmed | Probable |
  Potential` with `file:line` + linked threats.
- **Phase 3 — Control mapping** across 5 families (AuthN / AuthZ /
  Validation / Monitoring / Encryption); records consistent application
  across L2s.
- **Phase 3b — QA risk analysis**: coverage gap, testability risk,
  defect density, change velocity, environment coverage. `null` when
  absent; posture classified as `release-ready | needs-work | high-risk |
  unknown`.
- **Phase 4 — Unified risk scoring** with composites and mandatory
  1–3 **specific** drivers. `unknown` / `partial` are first-class; never
  faked to stay numeric.
- **Phase 5 — Cross-capability analysis**: shared vulns, cascading failure
  paths, weak trust boundaries, privilege-escalation chains.
- **Phase 6 — Gap analysis** with a dedicated section per compliance
  target in `security_scope.compliance`.

## False positive management

Findings can be marked `false_positive | mitigated_elsewhere |
accepted_risk`, each with rationale. `--fp-review <path>` applies
pre-recorded decisions on re-run.

## Gates

8 acceptance gates. Most important: every score has 1–3 specific drivers
(no generic labels); `unknown` / `partial` are allowed and carry reasons;
every compliance target gets a dedicated gap section.
