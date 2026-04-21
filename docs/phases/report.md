# `/report` — Audience-Specific Reports

**Command**: `speckit.brownkit.report` · **Spec**: [`commands/report.md`](../../commands/report.md)

Non-blocking and re-runnable. Can follow `/discover` (four reports, security
skipped) or `/assess` (all five).

## Reports

- **Stakeholder** — plain language, business impact, `Strong / Needs
  Attention / At Risk` per capability; modernisation positioning.
- **Architect** — topology, coupling, bounded contexts, decomposition
  options, blueprint gaps; risk overlays when `/assess` ran.
- **Dev** — capability map with file paths, refactor targets, orphan
  hotspots, coverage breakdown, 5–7 ticket-ready Sprint Recommendations.
- **SDET** — always emitted. Coverage map, automation matrix, testability
  hotspots, CI gates, 5–10 Sprint-Ready QA Backlog items, **mandatory
  Not-Collected Summary**.
- **Security** — conditional on `/assess`; risk-ranked findings, compliance
  posture per target, systemic risks, plus side-cars
  (`domain-model-secured.md`, `security-risk-map.json`, `threat-catalog.json`).

## Source linking convention

Every section header carries `*Source: [name](relative-path)*`. Paths are
relative to the report file (which lives in `evidence/reports/`). Security
artifacts link as `../security/...`. Every conclusion is one click from raw
evidence.

## Gates

6 acceptance gates. Most important: no broken source links, SDET report's
Not-Collected Summary is non-empty whenever any QA signal is absent,
sprint-recommendation counts are in range with scope estimates and
acceptance criteria.
