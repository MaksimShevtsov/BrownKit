# Splitting `/generate` and Wiring the `context.json` Contract

**Date:** 2026-07-30
**Target release:** v1.1.0
**Status:** approved design, ready for implementation planning

---

## 1. Problem

Two defects in BrownKit v1.0.2 are the same defect seen from two angles.

**`/generate` reads `context.json` fields that nothing writes.** `commands/generate.md`
references `context.json → tools.test_runner` and `tools.build` (lines 567, 586, 591,
769, 793), `context.json → stack` (666, 703, 723), `context.json → paths` and
`paths.src` (703, 725), `context.json → project_name` (720), and
`context.json → security_context.compliance_targets` (630, 734).

None of those exist. `templates/context.json` and `config-template.yml` define
`project / security_scope / qa_scope / weights / inputs / evidence_dir`; `commands/init.md`
writes exactly those; `scripts/python/detect_stack.py` emits `project.*` plus
`adaptations` and detects no test runner, linter, or build command at all. And
`docs/schemas/context.schema.json:8` sets root `additionalProperties: false`, so those
five paths are not merely absent — they are schema violations.

The consequence is not cosmetic. The affected references are load-bearing: the
`allowed-tools` derivation table, the dev-skills condition table keyed on
`backend = express|nestjs|fastapi|spring-boot|gin`, the stack-skills table keyed on
`language = go|python|java|csharp`, `instructions.md` sections 2–4, and the
`session-start` hook string. An agent running the phase must improvise those values,
which is precisely the fabrication the methodology's principle 3 forbids — while
acceptance gate 7 demands "no generic placeholders." The gate is structurally
unsatisfiable from evidence.

**`/generate` outgrew its contract.** At 1026 lines it is 2.5× the next largest command
(`assess.md`, 411). Parts A–C (capability contexts, security prompts, spec seeds) are
evidence packaging under `evidence/`. Parts D, D-bis, and E are a different product:
agent-tooling scaffolding for seven client IDs, plus skills, subagents, prompts, hooks,
an instructions file, a resumability lock file, and a 30-line interactive planning
checklist. That second half writes **outside** `evidence/` — into `.agents/`, `.claude/`,
`.github/`, `.gemini/`, `.opencode/` — and mutates `.claude/settings.json` and
`CLAUDE.md`. Every other phase writes only under `evidence/`; `/finish` is the phase
whose job is packaging outward.

The two are one problem: the seam where `/generate` outgrew its contract is exactly the
seam where its inputs stopped existing. The scaffolding half is the only consumer of the
missing fields.

**A third, independent defect rides along in this release.** `validate_evidence.py:139`
takes the first `\d{1,3}%` match in `coverage.md` as the file-to-capability coverage
figure, while `discover.md:111` instructs the agent to write architectural risks into that
same file using the example phrase "8% orphan rate in `payments/`". A healthy run whose
orphan note lands above the coverage line reports `fail — reported: 8%` on acceptance
criterion 10. It is unrelated to the `/generate` seam but small, self-contained, and
addressed in §6.

---

## 2. Decisions

| # | Decision | Chosen |
|---|---|---|
| 1 | Where the scaffolding half goes | New command `speckit.brownkit.scaffold` in the same extension |
| 2 | Who populates `tools`/`paths`/`stack` | Hybrid: `detect_stack.py` emits candidates, `/init` confirms |
| 3 | Migration for existing users | Additive v1.1.0 — deprecated-but-recognized flags plus a pointer |
| 4 | `/scaffold` shape | Keep the planning dialogue; replace the 14-step lock with a written-paths manifest |
| 5 | Client table | Externalize to `templates/clients.yml`; drop the web-fetch fallback |

Rejected alternatives and why:

- **Fold scaffolding into `/finish`** — `/finish`'s outward packaging is human/team handoff
  bundles, and it already carries 252 lines plus the 14-point validation. Adding ~500 lines
  of client fan-out recreates the same overload one phase later.
- **Separate `brownkit-agents` extension** — the scaffolding reads `domain-model.md`,
  `l1-capabilities.md`, `qa-brief.md`, and `context.json`. Two packages that cannot
  function apart is packaging overhead, not modularity.
- **Auto-delegation (`/generate --with-skills` runs scaffold inline)** — recreates the
  coupling being removed and keeps `/generate` reading fields whose whole purpose is to
  move to `/scaffold`.
- **Drop the run manifest entirely** — without a record of what the prior run wrote, a
  re-run after the user deselects a client silently leaves that client's stale skills in
  place.
- **Keep the `agentskills.io` web-fetch fallback** — it is the one place in BrownKit where
  live web content drives file writes into user-owned directories, with no way to verify
  at spec time that a fetched doc was parsed correctly. Every other unknown in this
  pipeline degrades to `not-collected` with a reason.

---

## 3. Architecture and command boundary

`/generate` keeps **Parts A–C only**: capability-context packages, security-aware prompts,
spec seeds. Writes only under `evidence/generate/`. Drops from ~1026 to ~350 lines and
from nine acceptance gates to six — gates 7–9 (skills, subagents, client fan-out) move out.

`speckit.brownkit.scaffold` takes **Parts D, D-bis, and E**: core skills, capability
skills, dev skills, stack skills, the opt-in business-rules and security-guidelines
skills, subagents, the project agent, project instructions, dev prompts, hooks, and the
client fan-out. It owns a new staging directory `evidence/scaffold/`, which absorbs what
currently sits misfiled under `evidence/generate/`: `instructions.md`, `prompts/`,
`hooks/`, `client-integrations.json`, and the run manifest. All user-directory writes
happen only from this command.

Pipeline:

```
/init → /scan → /discover → [/report] → /assess → /generate → [/scaffold] → /finish
```

`/scaffold` follows `/generate` because it consumes Part A's `capability-contexts/BC-*/`
packages — `attach-context` and every capability-derived skill point at them. It precedes
`/finish` so `manifest.json` can index scaffold artifacts when present.

**Preconditions:** `workflow.json.phases.generate.status == "completed"`.

**Degraded mode:** when `context.json.tools` / `paths` / `stack` are absent — a v1.0.2
evidence tree, or `/init` could not resolve them — `/scaffold` emits universal
`.agents/skills/` output, reduces `allowed-tools` to its base value with no tool-derived
entries, and records an explicit `not-collected` note naming what was skipped. It does
not guess commands.

**Schema constraint.** `docs/schemas/workflow.schema.json:12-19` pins phases with
`required`, `additionalProperties: false`, *and* a `patternProperties` regex listing
exactly seven names. `scaffold` is therefore added to the **pattern only, not to
`required`** — adding it to `required` would invalidate every existing
`evidence/workflow.json` and break the additive promise of decision 3.
`docs/schemas/manifest.schema.json:12-28` repeats the identical structure and takes the
identical treatment. `schema_version` stays `"1.0"` in both, which
`docs/schemas/README.md:43` already permits for additive optional changes.

---

## 4. The `context.json` contract

Three new **top-level, optional** blocks. Optional keeps existing evidence trees valid;
they must still be declared, because root `additionalProperties: false` forbids
undeclared keys.

```json
"stack": {
  "language": "java",
  "backend": "spring-boot",
  "frontend": "react",
  "database": "postgres",
  "package_manager": "maven"
},
"paths": {
  "src": "src/main/java",
  "test": "src/test/java",
  "migrations": "src/main/resources/db/migration"
},
"tools": {
  "test_runner": { "command": "mvn -B verify", "source": "Jenkinsfile:4", "confidence": "HIGH" },
  "build":       { "command": "mvn -DskipTests package", "source": "pom.xml", "confidence": "MEDIUM" },
  "lint":        { "command": null, "source": "not-collected", "confidence": null }
}
```

Any field with no resolved value is `null` for `stack` and `paths`; `tools` entries use
the `not-collected` form shown above. No invented defaults.

### Why `tools` carries provenance and the other two do not

`tools.*.command` is the one field baked into `allowed-tools` — it decides which shell
commands a downstream agent may run **without prompting the user**. A field with that
consequence records where its value came from and how confident the derivation was, and
`not-collected` must be representable as a first-class value rather than an empty string.
`stack` and `paths` are structural and lower-stakes, and their raw evidence already lives
in `project.detected.*`.

### Detection flow

1. `detect_stack.py` gains a `candidates` block and **adjudicates nothing** — it emits
   every command it found, each with its source.
2. `init.md` step 3 asks **only on ambiguity**. Two or more candidates: present them with
   sources and ask which one CI gates on. Exactly one: adopt at `HIGH`, ask nothing. Zero:
   record `not-collected`.
3. New `/init` acceptance gate: every `tools.*` entry is either a command with `source`
   and `confidence`, or explicit `not-collected`.

### Candidate source ranking

**CI config > explicit manifest plugin/script > manifest presence default.**

CI config ranks highest because it is what actually gates merges. This ranking is not
theoretical: `docs/examples/sample-repo/pom.xml` declares no surefire plugin, so
manifest-only detection would emit a generic `mvn test`, while
`docs/examples/sample-repo/Jenkinsfile:4-5` shows the real commands are `mvn -B verify`
and `mvn -B jacoco:report`.

### Ecosystem coverage

| Ecosystem | Candidate sources |
|---|---|
| Node | `package.json` `scripts` keys — `test`, `build`, `lint` |
| Python | presence of `[tool.pytest`, `[tool.ruff`, `[tool.black` in `pyproject.toml`; `setup.cfg` `[tool:pytest]` |
| Java | `pom.xml` surefire plugin; `gradlew` presence; Maven presence default |
| Go | `go.mod` → `go test ./...`; golangci config |
| .NET | `*.csproj` → `dotnet test`, `dotnet build` |
| Cross-cutting | `Makefile` target names matching `test|build|lint|check` |
| Cross-cutting | CI files already located by `_detect_ci` — shell steps invoking the above |

**Python 3.9 constraint.** `scripts/README.md:7` pins stdlib-only at Python ≥ 3.9, and
`tomllib` landed in 3.11. `pyproject.toml` therefore gets a line-prefix scan for
`[tool.pytest`, `[tool.ruff` and siblings — presence detection, not a TOML parse. That is
sufficient to name the runner and preserves the no-dependency promise.

### Fixes folded in

- `generate.md`'s `project_name` → `project.name` (already at `templates/context.json:4`).
- `generate.md`'s `security_context.compliance_targets` → `security_scope.compliance`
  (already at `templates/context.json:17`).
- `context.schema.json:27` — `project.detected.package_manifests` changes from
  `array of string` to the object form `{language, path, pattern}` that
  `detect_stack.py:252` actually emits. The producer's shape is the more useful one.

---

## 5. The `/scaffold` command

Approximately 450 lines, five phases, six acceptance gates.

**Phase 1 — Preflight and plan.** Verify `phases.generate.status`; read `context.json` and
record whether `tools`/`paths`/`stack` resolved (degraded mode if not). Detect installed
clients from `.specify/integrations/*.manifest.json`, then `.specify/integrations.json`,
then directory heuristics — all local sources, all retained from the current Step D-1.
Present the artifact checklist and client selection; confirm the plan before writing
anything.

**Phase 2 — Prior-run reconciliation.** See "Re-run semantics" below.

**Phase 3 — Universal generation.** `.agents/skills/`, `.agents/subagents/`,
`.agents/agent.md`, plus staging into `evidence/scaffold/{instructions.md,prompts/,hooks/}`.

**Phase 4 — Client fan-out**, driven by `templates/clients.yml`.

**Phase 5 — Manifest, `workflow.json` update, summary.**

### Run manifest

`evidence/scaffold/run-manifest.json`:

```json
{
  "schema_version": "1.0",
  "started_at": "2026-07-30T10:00:00Z",
  "completed_at": "2026-07-30T10:04:12Z",
  "degraded": false,
  "plan": {
    "artifacts": ["core-skills", "capability-skills", "dev-skills", "stack-skills",
                  "instructions", "prompts", "subagents", "project-agent"],
    "clients": ["claude", "copilot"],
    "declined": ["hooks", "business-rules"]
  },
  "written": [
    { "path": ".claude/skills/attach-context/SKILL.md", "artifact": "core-skills", "client": "claude" }
  ],
  "merged": [
    { "path": ".claude/settings.json", "key": "hooks", "note": "not owned by brownkit" }
  ],
  "skipped": [
    { "artifact": "security-guidelines", "reason": "assess not run" }
  ]
}
```

The three-way split is the point. **`written`** are files BrownKit created and therefore
owns — deletable on re-run. **`merged`** are files it modified but does not own
(`.claude/settings.json`, `CLAUDE.md`) — never deleted, only re-merged, and reported as
left in place for manual removal. **`skipped`** records every artifact the plan wanted but
the evidence could not support, with the reason.

### Re-run semantics

- Paths in the prior `written` set that the new plan will not produce are deleted — but
  **listed for user confirmation first, never silently**.
- Paths in both sets are overwritten.
- Paths only in the new plan are created.
- `merged` entries are never deleted; they are reported.
- If the prior manifest has `completed_at: null`, the previous run crashed. Offer
  resume-or-restart rather than assuming either.
- **Unmanaged files** — present on disk but absent from any manifest, e.g. left by a
  v1.0.2 `/generate` run — are overwritten when the plan produces the same path, and the
  overwrite is noted in the summary. They are **never deleted**. Cleanup applies only to
  paths BrownKit recorded itself.

### `templates/clients.yml`

Per client: `aliases` (so `claude-code` resolves to `claude`), `skills_path` and
`instructions_path` templates, `instructions_mode` (`prepend-section` or `write`),
`format` (`skill-md` / `agent-md` / `mdc`), `extra_frontmatter` field list, optional
`prompts_path`, and an optional `hooks` target with `hooks_mode: merge`. Seed it with the
seven client IDs currently hardcoded in `generate.md:447-455`: `claude`, `agy`, `copilot`,
`gemini`, `opencode`, `cursor`, `kiro`.

Adding a client becomes a data edit rather than a prompt edit. A client not in the file
receives universal `.agents/` output plus a `skipped` entry naming it — no web fetch, no
web search, no improvised format.

### Acceptance gates

1. Every planned artifact has output; every declined artifact is **absent, not a stub**.
   This carries over the existing `assess_done` conditionality for the
   `security-guidelines` skill, the `security` subagent, and the `review-security` prompt.
2. Every `SKILL.md`: `name` matches its parent directory, `description` is non-empty,
   `metadata.source` is `brownkit`.
3. No generic placeholders. Where a tool name was `not-collected`, the skill body **says
   so** rather than inventing one. This is the gate that was structurally unsatisfiable
   before this change.
4. Every resolved client has output at its `clients.yml` path in the declared format.
5. `run-manifest.json` lists every written path, with `merged` entries flagged not-owned.
6. `workflow.json.phases.scaffold.status == "completed"`.

---

## 6. Coverage-criterion fix

Independent of the `/generate` seam; included here because it is small and self-contained.

**D3 gains a machine-readable sidecar.** `commands/discover.md` D3 writes
`evidence/discovery/coverage-summary.json` alongside the existing narrative
`coverage.md`:

```json
{
  "schema_version": "1.0",
  "actual": 0.873,
  "target": 0.90,
  "mapped": 412,
  "significant": 472,
  "orphans": 38,
  "dead_code": 22
}
```

**The validator prefers the sidecar and falls back to a labeled line.**
`validate_evidence.py` criterion 10 reads `coverage-summary.json` when present. When it is
absent, it looks for an explicitly labeled line — `File-to-capability coverage: 87.3%` —
which D3 is also required to emit into `coverage.md`. Only if neither is found does it
report `needs-review`. The bare positional `re.search` is removed entirely.

The fallback path is load-bearing, not polish: every existing v1.0.2 evidence tree has
`coverage.md` and no sidecar, so a JSON-only validator would regress criterion 10 to
`needs-review` for all of them and break the additive promise of decision 3.

**Second problem fixed in the same place.** `discover.md:114` says explicitly "do not force
to 90% — report the actual percentage and identify the specific gaps that blocked the
target," but criterion 10 could only emit `pass`/`fail` against a bare number, so an
honestly-reported 87% with documented gaps was indistinguishable from a failure. Carrying
`target` and `orphans` lets the validator distinguish them: below target **with** a
non-zero orphan count and a populated gap section reports `needs-review` with the actual
figure, rather than a flat `fail`.

**No JSON schema for the sidecar.** `docs/schemas/` holds the five load-bearing contracts
shared *across* phases. This file has one producer (D3) and one consumer
(`validate_evidence.py`), and six flat numeric fields. Its shape is documented in
`discover.md` D3 instead. Adding a sixth schema would also mean amending
`docs/schemas/README.md:3`, which states "five load-bearing JSON artifacts" — cost without
benefit.

---

## 7. Migration and compatibility

Ships as **v1.1.0**. `extension.yml` gains an eleventh command entry for
`speckit.brownkit.scaffold`.

**Hook wiring is unchanged.** `before_constitution` keeps pointing at `/generate`: its
description ("prepares capability-scoped AI contexts and spec seeds") describes Parts A–C
precisely, so the split does not change what that hook wants. `/scaffold` deliberately
receives **no** lifecycle hook — it is interactive and writes into user-owned
directories, which is the wrong thing to auto-prompt mid-workflow. Users invoke it
explicitly.

**`/generate` deprecation surface.** `--with-skills`, `--no-skills`, `--with-agents`, and
`--no-agents` remain recognized. Passing any one prints a single line — *"moved to
`speckit.brownkit.scaffold` in v1.1.0"* — and changes nothing else. They are deleted in
2.0.0. Plain `/generate` gains a next-step line naming `/scaffold` in its summary; this
closes the silent-drop hazard, where a user running the command exactly as before would
otherwise get no `.agents/`, no `.claude/skills/`, and no explanation.

**Existing v1.0.2 evidence trees remain valid.** Absent `tools`/`paths`/`stack` triggers
degraded mode with an explicit note. A `workflow.json` with seven phases validates,
because `scaffold` went into `patternProperties` only; `/scaffold` adds the key when it
first runs.

---

## 8. Change inventory

**New (4)**

- `commands/scaffold.md`
- `templates/clients.yml`
- `docs/phases/scaffold.md`
- `scripts/python/check_prompt_refs.py` — reference-integrity guard, see §9.3

**Modified (17)**

| File | Change |
|---|---|
| `commands/generate.md` | Delete Parts D / D-bis / E (~680 lines); fix the two misnamed refs; nine gates → six; deprecated flags; next-step line |
| `commands/init.md` | Parse candidates (step 2); ambiguity-only questions (step 3); write `stack`/`paths`/`tools` (step 4); new acceptance gate |
| `commands/discover.md` | D3 writes `coverage-summary.json` and a labeled coverage line in `coverage.md` (§6) |
| `commands/finish.md` | Index the `scaffold` phase in `manifest.json` |
| `scripts/python/detect_stack.py` | Candidate block for six ecosystems plus CI extraction; drop the unused `max_depth` parameter |
| `scripts/python/validate_evidence.py` | Criterion 10 reads the sidecar, falls back to the labeled line; positional regex removed; `needs-review` for honest sub-target coverage (§6) |
| `docs/schemas/context.schema.json` | Declare `stack`/`paths`/`tools` as optional; fix `package_manifests` type |
| `docs/schemas/workflow.schema.json` | Add `scaffold` to `patternProperties` only |
| `docs/schemas/manifest.schema.json` | Add `scaffold` to `patternProperties` only |
| `templates/context.json` | `stack`/`paths`/`tools` skeletons |
| `templates/workflow.json` | `phases.scaffold` entry |
| `extension.yml` | `scaffold` command entry; version `1.1.0` |
| `README.md` | Pipeline diagram, command table, evidence layout, hooks-count fix |
| `CHANGELOG.md` | `[1.1.0]` entry |
| `docs/phases/generate.md` | Trim to Parts A–C |
| `docs/methodology.md` | Phase-to-artifact map row for `/scaffold` |
| `scripts/README.md` | `detect-stack` purpose line — now also emits tool candidates; script-index row for `check-prompt-refs` |

**Untouched:** `commands/{scan,assess,report,gate,validate,enrich}.md`, all scripts other
than `detect_stack.py` and `validate_evidence.py`, all report templates,
`templates/domain-model.md`, `config-template.yml`, `docs/phases/discover.md` (it describes
D3's purpose, not its output files, so the sidecar needs no edit there).

The README hooks-count fix resolves a separate factual error found during analysis:
`README.md:28` says "Three read-only commands" while `extension.yml` registers five hooks.
The statement becomes accurate under this design, since the fifth hook still points at
`/generate`.

---

## 9. Verification

There is no test harness in the repository, so verification is a concrete command list.

1. **Templates against their own schemas.**
   ```bash
   check-jsonschema --schemafile docs/schemas/context.schema.json templates/context.json
   check-jsonschema --schemafile docs/schemas/workflow.schema.json templates/workflow.json
   ```
   Nothing does this today, which is how the `package_manifests` type drift survived.

2. **`detect_stack.py` against the sample fixture.**
   ```bash
   python scripts/python/detect_stack.py --root docs/examples/sample-repo
   ```
   Assert two ranked `test_runner` candidates, with `mvn -B verify` first and sourced to
   `Jenkinsfile`.

3. **Reference-integrity check** — a new `scripts/python/check_prompt_refs.py` that walks
   every `` `context.json → X` `` reference in `commands/*.md` and asserts each path
   resolves against `context.schema.json`, exiting non-zero on any miss.
   ```bash
   python scripts/python/check_prompt_refs.py --commands commands --schema docs/schemas/context.schema.json
   ```
   This is the regression guard for the exact bug class this design fixes; without it, the
   next prose edit can reintroduce it silently. Approximately 30 lines, stdlib only,
   consistent with the existing `scripts/python/` conventions. Unlike the other helpers it
   is a repo-maintenance tool rather than a pipeline accelerator, so it gets no bash or
   PowerShell shim.

4. **Coverage criterion against a regression fixture.** Build a throwaway `coverage.md`
   whose first percentage is an orphan rate — the exact `discover.md:111` phrasing, "8%
   orphan rate in `payments/`" — above a labeled coverage line reading 93%. Assert
   criterion 10 reports `pass` at 93%, not `fail` at 8%. Then assert the sidecar takes
   precedence when both are present, and that a tree with neither reports `needs-review`.

---

## 10. Out of scope

Three findings from the same analysis pass are deliberately **not** addressed here. They
are independent of this seam and each warrants its own change:

- **Only 1 of 10 commands uses spec-kit's `scripts: {sh, ps}` convention.** `init.md`
  declares it; `scan.md` (3 helpers) and `finish.md` (1 helper) hardcode
  `./.specify/scripts/bash/*.sh` in prose, offering no PowerShell path. On Windows those
  four calls fail and the agent silently falls back to reading coverage XML itself,
  losing the determinism the helpers exist to provide.
- **`pyramid_shape` never influences scoring.** It is elicited at `/init`,
  schema-validated, and read only at `report.md:222` as narrative. A trophy-shaped project
  is still scored against classic-shaped coverage defaults (0.7 / 0.3 / 0.1) in
  `assess.md` Phase 3b.
- **CVE lookup is `not-collected` on every run.** `scan.md:277` and `assess.md:128` both
  say "if a source is available," but nothing in `config-template.yml` or `extension.yml`
  lets a user wire one, so dependency vulnerabilities always degrade to "Potential,
  flagged for manual review." Closing it needs a network-capable helper, which conflicts
  with the current stdlib-only, no-network script posture — a design decision in its own
  right.

Also out of scope: `_language_mix` in `detect_stack.py` breaks at a 5000-file cap in
filesystem order, making `primary_languages` non-deterministic run-to-run on large
polyglot repositories. Worth fixing, but it is not a blocker for this work and touching
the sampling logic here would widen the diff without serving the goal.
