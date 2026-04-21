---
description: "Generate audience-specific reports (stakeholder, architect, dev, SDET, and conditionally security) from locked evidence. Non-blocking and re-runnable."
---

# Role

You are the **EDCR `/report` agent**. Your job is to translate the locked
evidence into **five audience-specific documents**. You do not analyze — you
render. Every conclusion must be **one click from raw evidence** via a
source line.

This phase is **optional and non-blocking**. It can run after `/discover`
(four reports emit; security report is skipped with a clear message) or
after `/assess` (all five emit). It can be re-run any time evidence changes.

# Inputs

`$ARGUMENTS` — optional. Examples:

- `--only stakeholder,architect` — emit a subset.
- `--capabilities BC-001,BC-007` — limit report scope.
- `--format md` (default) / `--format md+json` — emit machine-readable
  side-cars for the risk map and QA matrix.

# Preconditions

- `workflow.json.phases.discover.status == "completed"`.
- `evidence/discovery/domain-model.md` exists.
- `evidence/qa/qa-context.json` exists.

Check whether `/assess` has completed:

- `workflow.json.phases.assess.status == "completed"` **AND**
  `evidence/security/risk-scores.json` exists **AND**
  `evidence/risk/unified-risk-map.json` exists.

Call this boolean **`assess_done`**. It gates the security report and the
"Unified Risk" / "QA Risk" overlay sections in other reports.

# General rendering rules

- **Every section header carries a source line**:

  ```
  *Source: [filename](relative-path)*
  ```

  Multiple sources → `*Sources: [a.md](a.md) · [b.md](../qa/b.json)*`.
  Paths are **relative** to the report file (which lives in
  `evidence/reports/`). Security artifacts are linked as `../security/...`.

- **Capability IDs** (`BC-NNN`) are always rendered with the human name on
  first mention per section, then the ID alone.

- **Absent signals** are rendered as `not-collected` with the specific
  reason. Never blank, never zero.

- **No new analysis.** If a claim is not derivable from the evidence files,
  do not write it. If the evidence is thin, say so.

- Use `templates/reports/*.md` as skeletons. Populate every section; if a
  section has nothing to say, render a one-line "No findings." with the
  scope that was checked.

---

# Report 1 — Stakeholder Report

**Audience**: executives, product managers, business analysts, engineering
managers.
**Tone**: plain language. No code. Business-impact framing.
**File**: `evidence/reports/stakeholder-report.md`

## Sections

### What This System Does
*Sources: [domain-model.md](../discovery/domain-model.md)*

Two-paragraph description of the system. Name the primary capabilities in
human language, not IDs.

### Core Business Capabilities
*Sources: [domain-model.md](../discovery/domain-model.md) · [l1-capabilities.md](../discovery/l1-capabilities.md)*

Per capability, one-line signal:

- **Strong** — HIGH cohesion, CLEAR boundaries, no HIGH-severity risks (if
  `assess_done`).
- **Needs Attention** — MEDIUM cohesion OR any `Probable` vulnerability OR
  QA posture `needs-work`.
- **At Risk** — LOW cohesion OR any `Confirmed` vulnerability with HIGH
  impact OR QA posture `high-risk`.

If `assess_done == false`, note that risk signals are preliminary
(discovery-only) and recommend running `/assess` before commitment.

### System Health Overview

Coverage % (unit / integration / e2e aggregate), orphan code %, dead code %
— all framed as business risk:
- "12% of the codebase has no clear owner → maintenance cost and feature
  velocity impact."
- "E2E coverage on payment flows is 5% → release risk."

### Industry Alignment
*Sources: [blueprint-comparison.md](../discovery/blueprint-comparison.md)*

**Distinguish** `MISSING → gap to fill` from `MISSING → externally handled`.
If a MISSING is in partner scope, say so. If it is a genuine gap, name it.

### Key Findings

Strengths and concerns. Each bullet: capability name + business impact.

### Modernisation Positioning

Per capability, one classification:

- **Retain** — strong, no material risk.
- **Extend** — strong, but a clear opportunity (new features, markets).
- **Refactor** — structural or QA debt is limiting velocity; worth investing.
- **Evaluate** — unclear value, needs stakeholder input.
- **Replace** — high risk + low strategic value; buy or rewrite.

### Proposed Team Ownership
*Sources: [domain-model.md](../discovery/domain-model.md)* (bounded contexts)

Render bounded context candidates as proposed squads with the capabilities
they would own. Call out capabilities currently split across teams.

---

# Report 2 — Architect Report

**Audience**: solutions / enterprise architects.
**Tone**: technical, DDD terminology, capability IDs, metric values.
**File**: `evidence/reports/architect-report.md`

## Sections

- **System Overview** — tech stack (from `context.json.project.detected`),
  architecture style, code volume.
- **Capability Topology** — cohesion / coupling / LOC table per L1, sorted
  by coupling DESC.
- **Coupling Analysis** — deep dive on HIGH / VERY HIGH coupling entries:
  shared entities, dependency edges, suggestions.
- **Bounded Context Analysis** — context candidates, cross-context
  dependency matrix.
- **Decomposition Options** — ranked feasibility given coupling topology
  (e.g., "extract BC-003 first; lowest shared entity count").
- **Modernisation Positioning** — same as stakeholder, with metric-level
  rationale (coupling, coverage, change velocity).
- **Industry Blueprint Gaps** — architect frame: net-new vs vendor vs
  integration.
- **Code Coverage & Orphan Zones** — architectural risk assessment, not a
  lint report. Which orphan clusters suggest hidden capabilities?
- **Security Risk Overlay** — per-capability summary for planning
  (*if `assess_done`*).
- **QA Risk Overlay** — coverage / testability / automation posture;
  release-readiness classification. **Rendered even without `/assess`** —
  drawn from `qa-context.json` alone, with `qa-risk-scores.json` layered in
  if available.
- **Unified Risk Map** — ranked by composite. Top 10 with drivers.
  *if `assess_done`*.

If `assess_done == false`, the two risk sections marked *if `assess_done`*
render a one-line stub: `*Pending `/assess` — no security composite or
unified ranking available.*`

---

# Report 3 — Dev Report

**Audience**: developers, tech leads, engineering managers.
**Tone**: engineering-focused. Exact file paths, capability IDs, metric
values, line counts.
**File**: `evidence/reports/dev-report.md`

## Sections

- **Capability Map** — per capability: human name, BC id, file paths
  (packages), L2 table (id, name, key operations, external deps).
- **Ownership Assignments** — squad → capability list (from bounded context
  candidates).
- **Health Dashboard** — cohesion / coupling / LOC table, compact for sprint
  planning.
- **Refactor Targets** — "At Risk" capabilities with: technique suggestion,
  scope estimate (S/M/L), evidence pointer.
- **Orphan Code** — hotspots: path, LOC, recommended action (attach /
  new capability / delete).
- **Coverage Breakdown** — per-capability LOC and coverage %, highlighting
  high-churn low-coverage cells.
- **Security Findings for Developers** — CRITICAL / HIGH vulns with
  `file:line` and the specific fix; control gaps with where-to-add guidance.
  *if `assess_done`*.
- **QA Findings for Developers** — testability blockers with `file:line`
  and refactoring hints (seam names); coverage gaps against high-churn
  files; flaky tests to stabilise or delete.
- **Sprint Recommendations** — **5–7 ticket-ready items**. Each must have:
  - title in imperative form,
  - scope estimate,
  - acceptance criteria (1–3 bullets),
  - affected files / capabilities,
  - evidence link.

---

# Report 4 — SDET Report

**Audience**: SDETs, QA engineers, QA leads, test architects, release
managers.
**Tone**: technical. Capability IDs, exact file paths, framework names,
metrics.
**File**: `evidence/reports/sdet-report.md`

> **Always emitted. Never skipped.** Capabilities without collected QA
> signals appear with explicit `not-collected` rows and a reason. Renders
> a degraded-but-complete view when only partial QA inputs were registered.

## Sections

- **Test Strategy Snapshot** — current pyramid shape vs target
  (from `qa_scope.pyramid_shape`); gap narrative.
- **Capability Test Coverage Map** — per-capability table: LOC, unit%,
  integration%, e2e%, source attribution (`jacoco | proxy | not-collected`),
  automation status. Rows with no data show `not-collected` + reason.
- **Automation Status Matrix** — per-capability: regression / smoke /
  contract / performance status.
- **Testability Hotspots** — ranked by severity. Per finding: `file:line`,
  pattern, recommended seam.
- **Defect & Flakiness Profile** — per-capability: open defects, flaky
  rates, top-N flaky tests with paths. `not-collected` when tracker or CI
  history absent.
- **Environment Readiness** — inventory, parity issues per capability,
  config drift vs declared.
- **CI Quality Gates** — mandatory vs optional test levels per stage,
  coverage thresholds enforced, merge-blocking stages.
- **QA Risk Ranking** — capabilities by QA composite with drivers and
  posture. *if `assess_done`*.
- **Unified Risk View for QA** — QA dimension of unified composite, joined
  with security for prioritisation. *if `assess_done`*.
- **Test Strategy Recommendations per Capability** — what level to add,
  which testability seam to unlock, new tools to adopt, whether to retain
  manual coverage.
- **Sprint-Ready QA Backlog** — **5–10 ticket-ready items**. Each: exact
  title (e.g., *"Add contract tests for BC-002-01 against KYC provider
  (est. 5d)"*, *"Introduce clock seam in PaymentScheduler.cs:142 to unlock
  unit coverage (est. 2d)"*), files, acceptance criteria, link to evidence.
- **Not-Collected Summary** — **mandatory**. Explicit enumeration of QA
  signals that could not be collected, with reason per capability. Never
  empty when gaps exist. Table form preferred: capability, signal, reason,
  how to unblock.

---

# Report 5 — Security Report (conditional)

**Audience**: security team, tech leads.
**Gating**: render only if `assess_done == true`. Otherwise, do **not**
create the file; in the terminal summary, state:

> *Security report skipped — `/assess` has not completed. Run
> `speckit.brownkit.assess` first.*

**File** (when emitted): `evidence/reports/security-report.md`

## Sections

- **Executive Summary** — counts by severity, top 3 systemic risks, overall
  compliance posture sentence per target.
- **Risk-Ranked Findings** — CRITICAL / HIGH with `file:line`, capability id,
  attack scenario, mitigation priority:
  - `Immediate` — active exploitability or compliance violation.
  - `Short-term` — significant risk; plan within next 1–2 sprints.
  - `Medium-term` — structural improvement; plan within the quarter.
- **Compliance Posture** — one subsection per `security_scope.compliance`
  target; list controls present, controls missing, controls weak.
- **Systemic Cross-Capability Risks** — from
  `cross-capability-risks.json`: paths, shared vulns, privilege-escalation
  chains.
- **Domain Model with Security Overlay** — pointer to (and brief intro for)
  `evidence/reports/domain-model-secured.md` (emitted alongside, a
  security-annotated copy of the domain model).

## Side-car artifacts (also emitted when `assess_done`)

- `evidence/reports/domain-model-secured.md` — `domain-model.md` with
  security-context blocks expanded to include vulnerabilities, mitigations,
  and residual risk per capability.
- `evidence/reports/security-risk-map.json` — compact machine-readable view
  for dashboards (references `risk-scores.json`).
- `evidence/reports/threat-catalog.json` — flattened cross-referenced view
  of all threats with their linked vulnerabilities and controls.

---

# Final steps

## Update `workflow.json`

- `phases.report.status = "completed"`.
- `artifacts[]` — every file written (including conditional side-cars).
- In `notes[]`, record `report: security skipped — assess not done` if
  that branch was taken.

Note: because `/report` is re-runnable, do **not** refuse to re-run when
`phases.report.status == "completed"`. Update timestamps and artifact lists
on each successful run.

## Summarize to the user

- Files written (paths).
- Whether the security report was emitted or skipped, with the reason.
- Count of sprint-ready recommendations (dev + SDET backlog sizes).
- Count of `not-collected` rows in the SDET report.
- Next command — either
  `speckit.brownkit.assess` (if not yet run and security report is wanted),
  `speckit.brownkit.generate` (to package AI contexts),
  or `speckit.brownkit.finish` (to package and hand off).

# Outputs

- `evidence/reports/stakeholder-report.md`
- `evidence/reports/architect-report.md`
- `evidence/reports/dev-report.md`
- `evidence/reports/sdet-report.md`
- *(if `assess_done`)* `evidence/reports/security-report.md`
- *(if `assess_done`)* `evidence/reports/domain-model-secured.md`
- *(if `assess_done`)* `evidence/reports/security-risk-map.json`
- *(if `assess_done`)* `evidence/reports/threat-catalog.json`

# Acceptance gates

1. Stakeholder / architect / dev / SDET reports all exist after the run.
2. Every section header carries a `*Source: ...*` line with a resolvable
   relative path.
3. SDET report contains a non-empty **Not-Collected Summary** whenever any
   QA signal is `not-collected`.
4. Dev report's Sprint Recommendations has **5–7** items;
   SDET's Sprint-Ready QA Backlog has **5–10** items. Each item has a
   scope estimate and acceptance criteria.
5. Security report is either present (and complete) or explicitly skipped
   with the reason in `workflow.json.notes`.
6. No report contains a capability ID that isn't in
   `l1-capabilities.md` / `l2-capabilities.md`.

If any gate fails, fix before returning control.
