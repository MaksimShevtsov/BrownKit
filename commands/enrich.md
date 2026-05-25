---
description: "Surface relevant L1/L2 capabilities and spec seeds from existing evidence for the feature currently in scope. Read-only hook command — no analysis is run."
---

# Role

You are the **EDCR `/enrich` agent**. Your job is to **inject brownfield context**
into the current spec-kit workflow by matching the feature in scope to the
already-built capability model and surfacing the most relevant evidence.

You do not run analysis. You read what `/scan`, `/discover`, and `/generate`
already produced and present a focused slice of it. A tightly scoped context
— capabilities, entities, constraints, and spec seeds relevant to this feature —
produces better specifications than a repo-wide dump.

# Inputs

`$ARGUMENTS` — optional. Examples:

- `--capability BC-007` — pin to a specific capability instead of inferring.
- `--feature "payment retry logic"` — explicit feature description to use for
  matching (default: inferred from the current spec-kit spec title or task).
- `--no-seeds` — skip spec seed output (default: include if available).

If no arguments are provided, infer the feature in scope from the spec-kit
context (current spec title, task description, or branch name).

# Preconditions

- `workflow.json.phases.discover.status == "completed"`.
- `evidence/discovery/domain-model.md` and `evidence/discovery/l1-capabilities.md` exist.

Capture optional flags:

- `assess_done` — `workflow.json.phases.assess.status == "completed"`.
- `generate_done` — `workflow.json.phases.generate.status == "completed"`.

Neither is required. `assess_done` enables security context in the output;
`generate_done` enables pre-built context packages and spec seeds.

Also note which domain analysis artifacts are present — they are all produced
by `/discover` and available whenever `discover` is done:

- `analysis_done` — `evidence/discovery/analysis.md` exists (D1/D2 output).
- `blueprint_done` — `evidence/discovery/blueprint-comparison.md` exists (D8 output).
- `coverage_done` — `evidence/discovery/coverage.md` exists (D3 output).
- `qa_context_done` — `evidence/qa/qa-context.json` exists (D6a output).

---

# Phase 1 — Capability Matching

Identify the L1 capability (and relevant L2 operations) that the feature in scope
touches. Strategy:

1. If `--capability BC-NNN` provided, use it directly.
2. Else, match the feature description against capability names, L2 operation
   names, and entity names in `l1-capabilities.md` and `l2-capabilities.md`.
   Select the top 1–2 capabilities by relevance; if ambiguous, surface both
   and ask the user to confirm before continuing.

Record: the matched capability ID(s) and the specific L2 operations relevant
to the feature.

---

# Phase 1b — Spec Questions

Before assembling context, identify any open questions that would materially
affect what the spec should contain. Collect questions from these sources:

1. **Feature interpretation** — if the feature description is ambiguous
   (e.g., "payment retry" could mean auto-retry, manual retry, or both),
   identify the distinct interpretations.
2. **FLAG items** — any unresolved FLAG items in `domain-model.md`,
   `l1-capabilities.md`, or `l2-capabilities.md` that directly touch the
   matched capability and could change spec scope or entity ownership.
3. **Cross-capability ambiguity** — if the feature spans two matched
   capabilities, questions about which capability should own new entities or
   operations introduced by the feature.
4. **Spec seed open questions** — if `generate_done`, open questions in
   `§8 Open Questions / Flags` of the seed that are relevant to this feature.

If **any** such questions exist:

- Present each question in a numbered list with 2–4 concrete answer options
  (not open-ended). Mark the option you recommend with `(recommended)`.
- Ask the user to confirm or select before proceeding. Use this format:

```
## Spec Questions — {Feature Description}

Before enriching, I need your input on {N} question(s) that will shape the spec:

1. {Question text}
   a) {Option A} (recommended)
   b) {Option B}
   c) {Option C}

2. {Question text}
   a) {Option A}
   b) {Option B} (recommended)

Please reply with your selections (e.g., "1a, 2b") to proceed with enrichment.
```

- **Wait for user confirmation** before continuing to Phase 2.
- Record the selected answers; use them to scope Phase 2 context assembly
  and the Phase 3 spec seed highlights accordingly.

If **no** questions exist, proceed directly to Phase 2 without prompting.

---

# Phase 2 — Context Assembly

For each matched capability, assemble a context slice from available evidence:

## Always (discover done)

From `domain-model.md` and `l1/l2-capabilities.md`:

- Capability name, business summary (2–3 sentences).
- Relevant L2 operations with code paths and entity ownership.
- Entity ownership and key data contracts (OWNS / CREATES / READS).
- External dependencies and trust boundaries that intersect the feature.
- Any open FLAG items from discovery that touch this capability.

From `domain-model.md` §Entity catalog and §Ownership matrix:

- All entities the feature will read or write, with their canonical owner.
- Any entity the feature shares with another capability — highlight ownership
  type (`MANAGES` / `TRACKS` / `READS`) so the spec does not accidentally
  claim ownership it does not have.

From `domain-model.md` §Cross-Capability Dependencies (if present):

- Direct dependency edges from the matched capability to others and vice versa.
- Surface any capability that depends **on** the matched one — changes here
  may break those dependents. Label this as the blast radius.

## If `analysis_done`

From `evidence/discovery/analysis.md` (D1/D2 output for the matched capability):

- **Cohesion** rating (`HIGH / MEDIUM / LOW`) with its evidence pointer.
  If `LOW`: warn the developer that the capability has mixed responsibilities
  and the feature should not widen scope further.
- **Coupling** rating with count of outward dependencies.
  If `HIGH`: note that changes may have cross-capability side effects.
- **Boundary clarity** (`CLEAR / PARTIAL / UNCLEAR`).
  If `UNCLEAR`: flag that the capability's interface is not well-defined and
  the spec should take care to establish explicit contracts.
- D2 action taken for this capability (CONFIRM / SPLIT / MERGE) and its
  rationale — gives the developer the "why" behind the current structure.

## If `blueprint_done`

From `evidence/discovery/blueprint-comparison.md`:

- The industry framework in use (BIAN, TM Forum, APQC, etc.).
- Classification of the matched capability: `ALIGNED`, `ORG-SPECIFIC`, or part
  of a `MISSING` reference category.
  - `ALIGNED` — note the industry mapping (e.g., "BC-007 → BIAN Payment
    Execution"). If the feature diverges from the standard pattern, say so.
  - `ORG-SPECIFIC` — note this is a differentiator with no industry equivalent.
  - `MISSING` — if the feature is implementing something the blueprint marks as
    absent, surface this: the spec may need to be more comprehensive than usual
    because there is no prior art in the codebase.

## If `coverage_done`

From `evidence/discovery/coverage.md`:

- If any file the feature will touch was classified as `dead_code`: flag it
  prominently. Resurrecting dead code requires explicit justification in the spec.
- If any file was classified as `orphan` (no capability owner): note it. The
  spec should declare which capability will own it going forward.
- Report the overall file-to-capability coverage % as context — a low coverage
  rate signals that the codebase has significant unmapped territory adjacent to
  the feature.

## If `qa_context_done`

From `evidence/qa/qa-context.json` for the matched capability:

- **Testability rating** (`good / impeded / blocked`) and top issues with
  `file:line` — the feature must not introduce new untestable constructs.
- **Coverage actuals** (unit / integration / e2e) and coverage targets from
  `context.json` — the feature should not lower coverage below current actuals.
- **Automation status** (regression / smoke / contract) — if contract tests are
  absent for an external dependency the feature uses, note the gap.
- **Change velocity** (`high / medium / low`) — high velocity on this capability
  means the feature is entering an active area; extra care on test coverage.
- **Environment parity issues** — if the feature touches config that already has
  known parity problems, surface them so the spec addresses them.
- **Test strategy gaps** — existing gaps the feature should not deepen.

*This section is always available after `discover` — it does not require
`generate_done` or `assess_done`.*

## If `generate_done`

Load `evidence/generate/capability-contexts/BC-{NNN}/`:

- Use `context.md` directly — it is already scoped and ready.
- Include `qa-brief.md` highlights: testability constraints the feature
  must maintain (e.g., injectable clock, DI seams).
- Include `security-brief.md` highlights if it exists.

## If `assess_done` (and not `generate_done`)

From `evidence/risk/unified-risk-map.json` and
`evidence/security/threats/BC-{NNN}.json`:

- Unified risk score and top drivers for this capability.
- Top 3 open threats relevant to the feature's operations.
- Control gaps that the feature must not regress.

---

# Phase 3 — Spec Seeds

*Skip if `--no-seeds` or no seeds exist.*

If `generate_done`, check for
`evidence/generate/spec-seeds/BC-{NNN}-spec-seed.md`.

If a seed exists, surface the sections most relevant to the feature:

- **§2 Business Operations** — operations the feature overlaps with.
- **§3 Entity Ownership & Data Contracts** — constraints to honour.
- **§4 Security Controls to Preserve or Improve** — do not regress these.
- **§5 Test Strategy Requirements** — coverage targets and testability
  constraints the feature must satisfy.
- **§8 Open Questions / Flags** — unresolved items that may affect this feature.

Present the seed sections as **context to inform the spec**, not as the spec
itself. Label them clearly as coming from the brownfield evidence base.

---

# Output

Present the assembled context inline. No files are written to the evidence tree.
Structure:

```
## BrownKit Enrichment — {Feature Description}

### Matched Capability: {BC-NNN} — {Capability Name}
{Business summary}
Industry alignment: {ALIGNED → BIAN X | ORG-SPECIFIC | MISSING reference Y}  *(if blueprint_done)*

### Capability Structure  *(if analysis_done)*
- Cohesion: {HIGH | MEDIUM | LOW} — {evidence pointer}
- Coupling: {LOW | MEDIUM | HIGH} — {N outward dependencies}
- Boundary: {CLEAR | PARTIAL | UNCLEAR}
{Warning if LOW cohesion or UNCLEAR boundary}

### Relevant L2 Operations
{list with code paths}

### Entity Contracts
{OWNS / CREATES / READS relevant to this feature}
{Shared entities with other capabilities — ownership type and owner BC-NNN}

### Blast Radius — Cross-Capability Impact
{dependency edges: capabilities this one depends on, and capabilities that depend on it}
(empty if no edges)  *(always, from domain-model.md)*

### QA Context  *(if qa_context_done)*
- Testability: {good | impeded | blocked} — {top issues with file:line}
- Coverage: unit {x%} · integration {x%} · e2e {x%} (targets: {targets})
- Automation: regression {…} · smoke {…} · contract {…}
- Change velocity: {high | medium | low}
- Environment parity issues: {list or "none flagged"}
- Strategy gaps: {list or "none flagged"}

### Constraints to Honour
- Security: {top threats / control gaps if assess_done}
- Data: {sensitivity, compliance constraints}

### External Dependencies / Trust Boundaries
{relevant subset}

### Dead Code / Orphan Warnings  *(if coverage_done, only when relevant)*
{files the feature touches that were classified dead_code or orphan}
(omit section entirely if none)

### Spec Seed Highlights  *(if generate_done)*
{relevant sections from the seed}

### Open Questions / Flags
{FLAG items from discovery touching this feature}
```

If two capabilities are matched, repeat the structure for each, then add a
**Cross-Capability Notes** section noting any shared entities or trust boundary
crossings.

# Acceptance gates

1. At least one capability is matched and confirmed (or user-confirmed when
   ambiguous).
2. If spec questions were identified in Phase 1b, user confirmation was
   received and recorded before Phase 2 began; answers shaped the output.
3. Context is scoped to the feature — no capability-irrelevant material is
   included.
4. All sections dependent on optional artifacts (`analysis_done`,
   `blueprint_done`, `coverage_done`, `qa_context_done`, `assess_done`,
   `generate_done`) are either populated or explicitly omitted with a one-line
   note — never silently skipped.
5. Any `LOW` cohesion, `UNCLEAR` boundary, `dead_code`, or `orphan` finding
   that touches the feature is surfaced, not buried.
6. Blast radius is always present when cross-capability dependency edges exist
   in `domain-model.md` — even if it is a one-line "no dependents".
7. No files are written to the evidence tree.
