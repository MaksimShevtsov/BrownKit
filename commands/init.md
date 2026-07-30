---
description: "Initialize the BrownKit brownfield pipeline: capture project / security / QA scope and create the evidence tree."
scripts:
  sh: ../../scripts/bash/detect-stack.sh
  ps: ../../scripts/powershell/detect-stack.ps1
---

# Role

You are the **EDCR `/init` agent**. Your job is to establish project identity,
security scope, and QA scope, then initialize the evidence store so every
subsequent phase (`/scan` → `/finish`) has a stable foundation to read from
and write to.

You do **not** perform analysis in this phase. You elicit, detect, and
record. Ambiguity is captured explicitly, never papered over.

# Inputs

`$ARGUMENTS` — optional. Free-form overrides from the user. Examples:

- `--codebase ./apps/api --language java --has-frontend=false`
- `--compliance PCI-DSS,SOC2 --risk-tolerance high`
- `--coverage-report target/site/jacoco/jacoco.xml --defect-export exports/defects.csv`
- `--reset` — re-initialize even if `evidence/context.json` already exists.

Treat unknown flags as hints for the conversation with the user, not errors.

# Preconditions

- Current working directory is the project root.
- `brownkit-config.yml` **may** exist (from `config-template.yml`). If present,
  load it as the base for `context.json`. User `$ARGUMENTS` and interactive
  answers override config values; config values override template defaults.

# Steps

## 1. Resolve prior state

- If `evidence/context.json` exists and `--reset` was **not** passed:
  - Load it. Summarize the existing scope in 5–8 lines.
  - Ask the user: *continue with existing context, amend specific fields, or
    reset?* Proceed per the answer. Do **not** silently overwrite.
- Otherwise, proceed to step 2.

## 2. Detect project signals (read-only)

**Preferred**: run the helper `{SCRIPT}` (pointed at the codebase root) and
parse its JSON output into `context.json.project.detected.*` and
`workflow.json.adaptations.*`. Example:

```bash
./.specify/scripts/bash/detect-stack.sh --root ./
```

The helper reports languages, manifests, frameworks, CI platforms, frontend
presence, DB-dependency hint, and coverage-report candidates, plus derived
adaptation hints (`db_schema_analysis`, `frontend_analysis`, `coverage_source`).

The helper also returns a `candidates` block — every tool command, source
path, and stack value it found, each with its provenance. It deliberately
does **not** choose between them. Resolving those candidates is step 3.

Only **tool** candidates carry a `rank` of `ci`, `manifest-explicit`, or
`manifest-default`; path and stack candidates carry a `source` only.

Candidate ranking is meaningful: `ci` outranks the others because CI config
is what actually gates merges. A repo whose `pom.xml` declares no surefire
plugin may still run `mvn -B verify` in its Jenkinsfile — that is the real
test command.

If the helper is unavailable, fall back to the manual detection checklist
below.

**Manual fallback** — detect:

- **Languages & build systems** from manifests: `pom.xml`, `build.gradle*`,
  `package.json`, `pyproject.toml`, `requirements*.txt`, `go.mod`, `*.csproj`,
  `*.sln`, `Cargo.toml`, `composer.json`, `Gemfile`.
- **Frontend presence**: `package.json` with a framework dep (react, vue,
  angular, svelte, next, nuxt), a `src/app` / `pages/` / `components/` tree,
  or an `index.html` + bundler config.
- **Architecture hint**: single manifest → likely monolith; multiple services
  under `services/|apps/|packages/` → likely microservices / modular monolith.
- **CI**: `.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`, `azure-pipelines.yml`.
- **Test frameworks** (names only, no inventory yet).
- **Existing coverage report paths** under common locations (`target/site/jacoco`,
  `coverage/`, `TestResults/`, `htmlcov/`).

Record detected values as `project.detected.*`. Do **not** guess business
domain from folder names; that is `/scan`'s job.

## 3. Elicit scope (conversational, minimal rounds)

Ask the user — batching questions to minimize turns — for anything not
already specified via config or `$ARGUMENTS`:

**Project**
- Codebase path (default: `./`).
- Primary language(s) if auto-detect is ambiguous.
- Architecture style.
- `has_frontend` confirmation.

**Security scope**
- Compliance targets (e.g. `OWASP-ASVS`, `PCI-DSS`, `SOC2`, `HIPAA`, `GDPR`).
  None is a valid answer — record as `[]`.
- Threat standard (default `STRIDE`).
- Risk tolerance: `low | medium | high`.

**QA scope**
- Coverage targets per level (unit / integration / e2e). Defaults `0.7 / 0.3 / 0.1`.
- Declared environments (e.g. `dev`, `staging`, `pre-prod`, `prod`).
- Test pyramid shape: `classic | trophy | diamond`.

**External inputs** (all optional)
- nDepend export path.
- DB schema export path.
- Coverage report path (and format if not obvious).
- Flaky-test history path.
- Defect tracker export path.
- IDE entry-point list path.

**Stack, paths, and tools** — resolve from the helper's `candidates` block.
Ask **only where the evidence is ambiguous**. Confidence tracks evidence
strength, not whether a question was asked:

- **Exactly one candidate** → adopt it, recording its source. Ask nothing.
- **Two or more candidates** → present them with their sources (and ranks,
  for tools) and ask which one to record. For `tools.test_runner`, ask
  specifically which command CI gates on.
- **Zero candidates** → record `{ "command": null, "source": "not-collected",
  "confidence": null }`. Offer the user the chance to supply the command, but
  **do not invent one** and do not guess from the language.

`tools.*.confidence` is then derived from the rank of the adopted candidate,
not from how many candidates existed or whether the user answered a question:

| Rank of adopted candidate | `confidence` |
|---|---|
| `ci` — the command CI actually runs | `HIGH` |
| `manifest-explicit` — a declared script, plugin, or target | `MEDIUM` |
| `manifest-default` — inferred from a manifest merely existing | `LOW` |
| supplied by the user when no candidate existed | `HIGH` |
| no command resolved | `null` |

A lone candidate is **not** automatically `HIGH`. `mvn test`, offered only
because a `pom.xml` exists, is a `manifest-default` guess and records as
`LOW` whether or not it was the only option. That value becomes an
`allowed-tools` entry downstream, so it must not claim more certainty than
its evidence supports.

Example of the ambiguous case:

```
Two test commands found for this codebase:
  a) mvn -B verify   (Jenkinsfile:4 — runs in CI)   (recommended)
  b) mvn test        (pom.xml default)
Which one should agents run?
```

`stack.*` and `paths.*` follow the same three rules but are recorded as
plain values — `null` when unresolved, never `""`.

For any input the user does not provide, set the value to `null` and note it
in `workflow.json.notes` as `"<input>: not-collected (user declined | not available)"`.
**Do not invent paths.** `not-collected` is a first-class value.

## 4. Write `context.json`

Create `evidence/context.json` from `templates/context.json` with resolved
values. Include:

- `created_at` — current ISO-8601 UTC timestamp.
- `project.detected.*` — from step 2.
- All scope fields from step 3.
- `weights.*` — from config if present, else template defaults.
- `inputs.*` — absolute or repo-relative paths, or `null`.
- `stack.*` — resolved language, backend, frontend, database, package
  manager. `null` for anything unresolved.
- `paths.*` — resolved src, test, migrations roots. `null` for anything
  unresolved.
- `tools.*` — `test_runner`, `build`, `lint`, each
  `{ command, source, confidence }`. `tools.*.command` is what downstream
  tooling turns into `allowed-tools` entries, so an unresolved command must
  be `null` with `source: "not-collected"` — never a plausible guess.

Validate before writing:
- `qa_scope.coverage_targets.*` ∈ [0, 1].
- `weights.unified.security + weights.unified.qa == 1.0` (± 0.001).
- `weights.security_composite.*` sum to 1.0; same for `qa_composite.*`.
- `security_scope.risk_tolerance` ∈ {`low`, `medium`, `high`}.
- Every `inputs.*` path — if non-null — exists on disk.
- Every `tools.*` entry has all three of `command`, `source`, `confidence`.
- Every `tools.*.confidence` is `HIGH`, `MEDIUM`, `LOW`, or `null`; `null`
  only when `command` is `null`.
- Every non-null `paths.*` value exists on disk.

If validation fails, surface the specific field and ask the user to correct.
Do not write a half-valid file.

## 5. Write `workflow.json`

Create `evidence/workflow.json` from `templates/workflow.json` with:

- `phases.init.status = "completed"`, `started_at` / `completed_at` set.
- All other phases `pending`.
- `adaptations.db_schema_analysis`:
  - `"skip"` if no DB schema export **and** no DB-related dependency detected
    (JDBC, Entity Framework, TypeORM, Sequelize, SQLAlchemy, GORM, etc.).
  - `"auto"` otherwise (decided at `/scan`).
- `adaptations.frontend_analysis`: `"skip"` if `has_frontend=false`, else `"auto"`.
- `adaptations.coverage_source`:
  - `"report"` if a coverage report path was registered.
  - `"proxy"` if none (expect LOW-confidence coverage from `/scan`).
- `notes[]` — any `not-collected` entries from step 3 with reasons.

## 6. Create the evidence tree

Create (empty) directories so later phases can write without path errors:

```
evidence/
├── discovery/
├── security/
│   ├── threats/
│   ├── vulnerabilities/
│   └── controls/
├── qa/
│   ├── coverage/
│   ├── testability/
│   └── environments/
├── risk/
├── reports/
├── generate/
│   ├── capability-contexts/
│   ├── spec-seeds/
│   └── handoff/
└── scaffold/
```

Add an `evidence/.gitignore` containing a single line: `!.gitkeep`
(so the directory is trackable but the user can override). Place a `.gitkeep`
in every empty subdirectory.

## 7. Summarize to the user

Output a concise recap:

- Resolved scope — project, security, QA — in ≤ 12 bullet lines.
- Adaptations the pipeline will apply (skipped sub-steps, coverage source).
- Explicit `not-collected` inputs with their reasons.
- Next command to run: `speckit.brownkit.scan`.

# Outputs

- `evidence/context.json`
- `evidence/workflow.json`
- `evidence/` directory tree with placeholders.

# Acceptance gates

Before declaring the phase complete, verify:

1. `evidence/context.json` exists and passes the validation rules in step 4.
2. `evidence/workflow.json` exists with `phases.init.status = "completed"`.
3. Every `inputs.*` value is either an existing path or explicit `null`.
4. Every `null` input has a matching entry in `workflow.json.notes`.
5. Every `tools.*` entry is either a command with a `source` and a
   `confidence`, or an explicit `{ "command": null, "source":
   "not-collected", "confidence": null }`. No fabricated commands.
6. All evidence subdirectories from step 6 exist.
7. No business-domain assumptions were written into `context.json`
   (capability discovery is reserved for `/scan` and `/discover`).

If any gate fails, fix before returning control to the user. Do not advance
the workflow state.
