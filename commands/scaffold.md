---
description: "Generate client-agnostic skills, subagents, prompts, hooks, and project instructions from the locked capability evidence, then fan them out to each detected AI client."
---

# Role

You are the **EDCR `/scaffold` agent**. Your job is to turn the locked
capability evidence into **agent tooling** — skills, subagents, prompts,
hooks, and a project brief — and install it at each client's native path.

You do not analyze. `/generate` packaged the evidence; you shape it into
artifacts an AI client can load. Every artifact you write must reference real
evidence paths, real entity names, and real tool commands. Where a tool
command was not collected, **say so in the artifact** rather than inventing
a plausible one.

# Inputs

`$ARGUMENTS` — optional. Examples:

- `--clients claude,copilot` — skip client detection and use this list.
- `--no-skills` / `--no-agents` / `--no-prompts` / `--no-hooks` — drop a
  whole artifact family without going through the planning dialogue.
- `--resume` — continue an interrupted prior run instead of asking.
- `--dry-run` — print the plan and the paths that would be written; write
  nothing.

# Preconditions

- `workflow.json.phases.generate.status == "completed"`.
- `evidence/generate/capability-contexts/` exists with at least one
  `BC-NNN/` package.

If either fails, instruct the user to run `speckit.brownkit.generate` and
stop.

Load `context.json`. Record whether `stack`, `paths`, and `tools` are
present and resolved.

## Degraded mode

When `context.json.tools`, `paths`, or `stack` are absent — a pre-v1.1.0
evidence tree, or `/init` could not resolve them — run in **degraded mode**:

- Emit universal `.agents/skills/` output only for artifacts that do not
  need tool commands.
- Reduce every `allowed-tools` value to its base entry with **no**
  tool-derived additions.
- Where a skill body would name a test runner, write
  `"test command: not-collected — set context.json.tools.test_runner"`.
- Add a `skipped` entry to the run manifest for every artifact family
  affected, naming the missing field.

Never guess a command in degraded mode.

# Phase 1 — Preflight and plan

## Interactive planning

Before writing any files, run this planning dialogue. Skip it if
`$ARGUMENTS` already contains explicit `--with/--no` flags that fully
resolve all choices.

**Ask the user two questions in a single message:**

**Q1 — Artifact types.** Present a checklist of what can be generated and
ask which items to include:

```
Which artifacts should /generate produce?

Instructions:
  [x] Project instructions   (AI project brief: stack, paths, conventions, workflow)

Skills — dev (adding new code to the existing layers):
  [x] Core skills            (attach-context, review-capability, fix-bug, add-test)
  [x] Capability skills      (one per HIGH/MEDIUM L1 — scoped to capability evidence)
  [x] Dev skills             (add-endpoint, add-component, add-migration, etc. — stack-derived)

Skills — stack (improving existing code in this project's style):
  [x] Stack skills           (implement-feature, write-docs, modernize-<lang>-module, etc.)
  [ ] Business-rules skill   (cross-capability invariants and forbidden patterns)
  [ ] Security-guidelines    (threat/vuln/gap checklist — requires /assess)

Prompts:
  [x] implement-feature      (full-stack feature from capability map)
  [x] fix-bug                (reproduce → locate → fix → test)
  [x] write-tests            (coverage gaps and seam recommendations)
  [x] review-changes         (diff review against capability evidence)
  [ ] review-security        (security-focused review — requires /assess)

Agents:
  [x] dev subagent           (.agents/subagents/dev/)
  [x] qa subagent            (.agents/subagents/qa/)
  [x] security subagent      (.agents/subagents/security/ — requires /assess)
  [x] Project agent          (.agents/agent.md)

Hooks:
  [ ] session-start          (inject project summary into every session)
  [ ] pre-tool-use           (gate dangerous operations)
  [ ] post-tool-use          (run lint/test after file writes)

Evidence packages:
  [x] Capability-context packages  (Part A)
  [x] Security-aware prompts       (Part B — security evidence, not agent prompts)
  [x] Spec seeds                   (Part C)
```

Default selections (shown with `[x]`) are applied if the user confirms
without changes. Items marked `[ ]` are opt-in.

Items that are impossible given the current workflow state are shown but
dimmed with a note (e.g., `security subagent — skipped: /assess not run`).

**Q2 — Clients.** Detect installed clients first (procedure below), then
ask:

```
Installed clients detected: claude, copilot, gemini
Which clients should receive skill copies?
(All three / choose a subset / universal .agents/ only)
```

For any client id not present in `templates/clients.yml`, do **not** search
for its format. Write universal `.agents/skills/` output, add a `skipped`
entry to the run manifest naming the client, and tell the user which file
to extend. Guessing a client's native path from documentation the agent
cannot verify risks writing malformed files into a user-owned directory.

Record all selections in a planning summary and show it to the user before
starting the pipeline. Adjust `--with/--no` flags and the client selection
accordingly.

**1. Detect installed clients — in priority order:**

a. **`.specify/integrations/` directory** (canonical source when spec-kit
   integrations are installed): read every `*.manifest.json` file; use the
   `"integration"` field value as the client ID.
   Example: `{ "integration": "claude", ... }` → client ID `claude`.
b. **`.specify/integrations.json`** — if it exists, object keys are client IDs.
c. **Directory heuristics** (fallback when no manifest found):
   `.claude/` → `claude`, `.cursor/` → `cursor`,
   `.github/agents/` → `copilot`, `.kiro/` → `kiro`,
   `.gemini/` → `gemini`, `.opencode/` → `opencode`.
   The presence of `.agents/skills/` alone does not imply a specific client.

Merge results; deduplicate by client ID.

# Phase 2 — Prior-run reconciliation

Read `evidence/scaffold/run-manifest.json` if it exists.

**No manifest** — this is a first run, or a pre-v1.1.0 `/generate` produced
the files on disk. Treat every existing file as *unmanaged*: overwrite it
when the plan produces the same path, note the overwrite in the summary, and
**never delete it**. Cleanup applies only to paths BrownKit recorded itself.

**Manifest with `completed_at: null`** — the prior run was interrupted.
Present the count of paths already written and ask: resume (skip artifacts
already complete) or restart clean. Do not assume either.

**Manifest with a `completed_at` timestamp** — compute the difference
between the prior `written` set and what the new plan will produce:

| Case | Action |
|---|---|
| In prior `written`, not in new plan | Deletion candidate |
| In both | Overwrite |
| Only in new plan | Create |
| In prior `merged` | Never delete — report as left in place |

List every deletion candidate and **ask for confirmation before deleting
anything**. Deleting files in `.claude/` or `.github/` without confirmation
is not acceptable, even when BrownKit wrote them.

# Phase 3 — Universal generation

## Skill output format

Every skill is a directory containing `SKILL.md` with
[agentskills.io frontmatter](https://agentskills.io/specification):

```markdown
---
name: {skill-name}
description: {what it does and when to use it — specific, ≤ 1024 chars}
metadata:
  source: brownkit
---

# Instructions
...
```

Rules:
- `name` must match the directory name: lowercase letters, digits, hyphens; no
  consecutive hyphens; 1–64 chars.
- `description` must be non-empty and mention both what the skill does and when
  to activate it.
- Body must reference actual evidence paths, entity names, and tool names —
  never generic placeholders.
- Keep each `SKILL.md` under 200 lines; move reference material to a
  `references/` subdirectory if needed.

## Core skills (always)

| Skill name | Description | What it reads |
|---|---|---|
| `attach-context` | Load a capability's evidence package for scoped AI work. Use when starting on a BC-NNN capability. | `evidence/generate/capability-contexts/{id}/context.md`, `files.txt`, `qa-brief.md`, `risks.json`, `security-brief.md` (if present) |
| `review-capability` | Review code changes for a capability against its evidence boundary. Use before committing to a capability. | same context package; `files.txt` as hard file-scope boundary |
| `fix-bug` | Diagnose and fix a bug within a capability boundary. Use when given an error, failing test, or bug description. | capability `context.md`, `files.txt`, `qa-brief.md` |
| `add-test` | Add tests grounded in `qa-brief.md` testability findings. Use when coverage is below target or a seam recommendation needs applying. | `qa-brief.md`, `files.txt`, `context.json → tools.test_runner.command` |

Body of each core skill must:
- Describe the file-scope constraint (`files.txt` as hard boundary — no writes
  outside it without explicit instruction).
- Name the test runner from `context.json → tools.test_runner.command`.
- For `attach-context`: list every file in the context package and what it
  contains, so the agent loads them one by one as needed.

## Capability-derived skills (one per HIGH/MEDIUM L1)

For each capability in `l1-capabilities.md` with confidence HIGH or MEDIUM,
generate `.agents/skills/{slug}/SKILL.md`:

- **Name**: lowercase slug of the capability name
  (e.g., `payments-domestic`, `user-auth`). Spaces and special characters
  become hyphens; consecutive hyphens collapsed.
- **Description**: `"{Capability name} (BC-{NNN}) — {1-sentence description}.
  Use when working on {slug} features, bugs, or tests."`
- **Metadata**: add `capability-id: "BC-{NNN}"`.
- **Body**: capability summary + pointer to
  `evidence/generate/capability-contexts/BC-{NNN}/` + key entity list (from
  `context.md`) + top 5–10 files from `files.txt`.

Skip LOW-confidence capabilities.

## Business-rules skill (opt-in)

*Generate only if selected in interactive planning.*

`.agents/skills/business-rules/SKILL.md`

Synthesises the invariants and constraints that cut across capabilities into
a single reference skill. Use when implementing any feature that touches
core domain logic, to avoid violating cross-capability contracts.

Body must include:

1. **Domain invariants** — rules that must hold across all capabilities,
   derived from entity ownership table in `domain-model.md`
   (e.g., "only BC-NNN may write to `orders.status`").
2. **Cross-capability contracts** — interface rules between capabilities
   (derived from D3 L2 decomposition and any `FLAG` items in `domain-model.md`).
3. **Compliance constraints** — data-sensitivity and regulatory rules from
   `context.json → security_scope.compliance`.
4. **Forbidden patterns** — anti-patterns observed in the codebase (from
   QA and security findings) that must not be introduced in new code.

Keep the body under 150 lines; move detailed entity tables to
`references/domain-invariants.md` if needed.

## Security-guidelines skill (opt-in)

*Generate only if selected in interactive planning AND `assess_done == true`.*

`.agents/skills/security-guidelines/SKILL.md`

A hardening checklist derived from the assess phase, scoped to this
codebase's actual threats and gaps. Use before committing any change to
input-handling, authentication, or data-access code.

Body must include:

1. **Top threats** — top 5 STRIDE threats across all capabilities
   (from threat files), with attack scenario and file-scope hint.
2. **Open vulnerabilities** — all `Confirmed` and `Probable` findings from
   `vulnerabilities/catalog.json` with `file:line` and fix hint; mark each
   as OPEN or FIXED.
3. **Control gaps** — items from `gaps.json` with "where to add" guidance.
4. **Mandatory checks** — a short checklist every code reviewer must run for
   this project (e.g., "validate all SQL params through ORM; never
   concatenate user input into queries").

Omit this skill entirely (not a stub) when `assess_done == false`.

## Dev skills — adding new code (Phase 3)

*Selected by default. Skip if user deselected "Dev skills" in Q1.*

Skills that guide an agent in adding new code to the existing codebase
layers. Derive from `context.json → stack`; generate only for tools
actually present.

| Condition | Skill name | Purpose |
|---|---|---|
| always | `add-feature` | Add a new end-to-end feature across all detected layers → test |
| always | `add-test` | Add unit/integration tests for an existing module or capability |
| always | `fix-bug` | Reproduce → locate → minimal fix → add failing test → verify |
| backend = express / fastify / koa | `add-endpoint` | Route → handler → service → test |
| backend = nestjs | `add-module` | Module → controller → service → dto → test |
| backend = fastapi / flask / django | `add-endpoint` | Route → handler → schema → test |
| backend = spring-boot / quarkus | `add-endpoint` | Controller → service → test |
| backend = gin / echo / fiber / chi | `add-handler` | Handler → route → test |
| db = postgres / mysql / sqlite | `add-migration` | Migration via detected tool (flyway / alembic / prisma migrate / etc.) |
| db = mongodb | `add-model` | Model → schema → indexes → repository |
| frontend present | `add-component` | UI component → props → state → test |
| frontend present | `add-page` | Page / route → layout → data fetch → test |

## Stack skills — improving existing code (Phase 3)

*Selected by default. Skip if user deselected "Stack skills" in Q1.*

Skills that guide an agent in modernising or documenting existing code in
this project's idioms. Every skill must contain imperative instructions
(do X, then Y) — not analysis-only descriptions.

| Condition | Skill name | Purpose |
|---|---|---|
| always | `implement-feature` | Full-stack feature from capability map: read domain model → implement all layers → test → lint |
| always | `write-docs` | Write idiomatic inline docs for a module (godoc / docstrings / JSDoc / Javadoc) — logic unchanged |
| language = go | `modernize-go-module` | Replace legacy `net/http` patterns with detected router; extract thin handler → service; add `context.Context`; table-driven tests |
| language = python | `modernize-python-module` | Add type annotations; replace bare `except`; apply detected formatter; update docstrings |
| language = typescript / javascript | `modernize-js-module` | CJS → ESM; `var` → `const/let`; `.then/.catch` → `async/await`; add TS types; run detected linter |
| language = java | `modernize-java-class` | Constructor injection; replace field injection; apply detected formatter; update unit tests |
| language = csharp | `modernize-csharp-class` | Add nullable annotations; replace `async void`; apply detected formatter; update tests |

Cap stack skills at 5 entries — prioritize by frequency of use in the
detected codebase (infer from `context.json → stack` and `paths.src` file
count per layer).

## Project instructions (Phase 3)

*Selected by default.*

`evidence/scaffold/instructions.md` — a project-level AI brief that
client-specific installers copy to the correct location (e.g.,
`.github/copilot-instructions.md`, prepended to `CLAUDE.md`, etc.).

Must include, all derived from evidence — no invented values:

1. **Project name and domain** (from `context.json → project.name` /
   domain model summary).
2. **Tech stack** — language, backend, frontend, database, package manager
   (from `context.json → stack`).
3. **Key paths** — source root, test root, migration directory
   (from `context.json → paths`).
4. **Development workflow** — test command, lint command, build command
   (from `context.json → tools`).
5. **Capability index** — one line per L1: ID, name, key paths.
6. **Entity ownership** — entity → owning capability → sensitivity tag
   (from `domain-model.md`).
7. **Conventions** — naming patterns observed in the codebase; do not
   invent — derive from existing file and symbol names.
8. **Security constraints** — data-sensitivity tags and compliance targets
   (from `context.json → security_scope.compliance`); emit only if non-empty.

Keep the instructions file under 120 lines. Reference `domain-model.md`
for deeper entity detail rather than repeating it inline.

When writing client copies in Phase 4, the generator for each client
places this file at the correct native path:

| Client | Instructions path |
|---|---|
| `claude` / `claude-code` | Prepend a `# {Project Name}` section to `.claude/CLAUDE.md` (create if absent) |
| `copilot` | `.github/copilot-instructions.md` |
| `gemini` | `.gemini/GEMINI.md` (create if absent) |
| `opencode` | Prepend to `AGENTS.md` or create `.opencode/AGENTS.md` |
| `agy` | `.agents/AGENTS.md` (create if absent) |

## Dev prompts (Phase 3)

*Selected by default (implement-feature, fix-bug, write-tests, review-changes).
review-security is opt-in and requires `assess_done`.*

Prompts are stored at `evidence/scaffold/prompts/{name}.md` and copied to
each selected client's prompt directory during Phase 4.

Each prompt must:
- Reference actual capability IDs, file paths, and tool names from evidence.
- Include a `## Context to read first` section listing the exact files the
  agent should load before starting.
- End with a structured `## Task` section using `${input:...}` variables
  where the user or agent supplies the specific subject.

| Prompt | Purpose | Key context files |
|---|---|---|
| `implement-feature` | Implement a capability from the domain model end-to-end | `l1-capabilities.md`, `domain-model.md`, `context.json → tools` |
| `fix-bug` | Reproduce → locate root cause → minimal fix → failing test | `l2-capabilities.md`, `qa-context.json`, `context.json → tools` |
| `write-tests` | Close coverage gap or apply seam recommendation | `qa-brief.md` for target capability, `context.json → tools.test_runner.command` |
| `review-changes` | Review a diff against the capability evidence boundary | `files.txt` for affected capability, `domain-model.md` |
| `review-security` | Security-focused diff review (opt-in, `assess_done` only) | `security-brief.md`, `vulnerabilities/catalog.json` |

Client-native prompt paths per client type:

| Client | Prompt path |
|---|---|
| `claude` / `claude-code` | `.claude/skills/{name}/SKILL.md` with `disable-model-invocation: true` |
| `copilot` | `.github/prompts/{name}.prompt.md` |
| `gemini` | `.gemini/skills/{name}/SKILL.md` |
| `opencode` | `.opencode/skills/{name}/SKILL.md` |

## Hooks (Phase 3)

*Opt-in. Generate only items selected in Q1.*

Hooks are stored at `evidence/scaffold/hooks/` and copied to each
client's native hook location during Phase 4.

| Hook | Trigger | Purpose | What it emits |
|---|---|---|---|
| `session-start` | Session / conversation start | Inject a one-line project summary so every session starts grounded | `"Project: {name} | Stack: {lang}/{backend} | Tests: {runner} | Lint: {linter}"` — derived from `context.json` |
| `pre-tool-use` | Before destructive Bash commands | Warn before `rm`, `drop table`, force-push, etc. | Warning message asking the agent to confirm |
| `post-tool-use` | After file-write tools (Edit, Write) | Run linter + test runner on changed files | Lint + test command from `context.json → tools` |

Client-native hook paths:

| Client | Hook path |
|---|---|
| `claude` / `claude-code` | `.claude/settings.json → hooks` (merge, do not overwrite) |
| `copilot` / VS Code | `.vscode/settings.json → github.copilot.chat.agent.thinkingTool` / extension hooks |
| `gemini` | `.gemini/settings.json → hooks` (if supported) |

If the client does not support hooks natively, skip that hook for that
client and note it in the summary.

# Part E — Subagents and Project Agent

*Skip if `--no-agents`.*

Generate role-focused subagents at `.agents/subagents/` and a project
entry-point agent at `.agents/agent.md`.

Use the `generate-dev-subagents` skill if available; otherwise execute inline.

## Subagent format

All subagents use `.agents/subagents/{name}/SUBAGENT.md` with the same
agentskills.io frontmatter convention:

```markdown
---
name: {name}
description: {what this subagent does and when to use it}
metadata:
  role: {dev|qa|security}
  source: brownkit
---
```

Body is a full system-prompt-style agent definition grounding the subagent in
this project's evidence.

## `dev` subagent — always

`.agents/subagents/dev/SUBAGENT.md`

Primary development assistant. Body must include:

1. **System overview** — architecture, language, framework, database, frontend,
   test runner, source root (all from `context.json`).
2. **Capability table** — one row per L1: ID, name, 1-line description, key
   paths from `files.txt`.
3. **Entity ownership table** — for each entity in `domain-model.md`:
   `EntityName` · owning capability (BC-NNN) · table name · sensitivity tag.
4. **Available skills** — list every `.agents/skills/` entry with its
   description.
5. **Working rules**:
   - Identify BC-NNN before writing any code.
   - Scope work to `files.txt` for that capability.
   - Never write to an entity owned by a different capability without going
     through its defined interface.
   - Always write tests using the detected test runner.
   - For tasks that span capabilities, resolve the dependency direction first
     and start from the upstream capability.

## `qa` subagent — always

`.agents/subagents/qa/SUBAGENT.md`

QA-focused assistant. Body must include:

1. Testability posture summary across all capabilities (from each
   `qa-brief.md`).
2. Coverage targets per capability.
3. Seam gaps ranked by severity (`blocks` → `high` → `medium`).
4. Test runner and conventions from `context.json`.
5. Rules: always read `qa-brief.md` for the target capability first; never
   claim a seam is addressed without writing the test.

## `security` subagent — only if `assess_done`

`.agents/subagents/security/SUBAGENT.md`

Security-aware code reviewer. Body must include:

1. Threat summary per capability (top 3 threats, from threat files).
2. All Confirmed and Probable vulnerabilities with `file:line` and fix hints.
3. Control gaps from `gaps.json` with "where to add" guidance.
4. Rules: block any change to input-handling code until `security-brief.md`
   has been reviewed for that capability.

**Omit this file entirely (not a stub) when `assess_done == false`.**

## Project agent — `.agents/agent.md`

Entry-point agent — brief, delegates to subagents and skills:

```markdown
---
name: {project name from context.json}
description: {domain} AI assistant — {N} capabilities, {primary language}/{primary framework}. Delegates to specialized subagents for dev, QA{if assess_done: , and security} work.
metadata:
  source: brownkit
---

# {Project Name}

{2-sentence project description derived from context.json and l1-capabilities.md}

## Capabilities ({N})
| ID | Capability | Description |
|----|-----------|-------------|
{L1 rows: ID · name · 1-line description}

## Subagents
- **dev** (`.agents/subagents/dev/`) — development assistant; knows capabilities, entity boundaries, available skills
- **qa** (`.agents/subagents/qa/`) — QA assistant; testability context, coverage targets, seam guidance
{if assess_done:}
- **security** (`.agents/subagents/security/`) — security reviewer; threats, vulnerabilities, control gaps

## Skills
{For each .agents/skills/ entry: **{name}** — {description}}

## Evidence
Context packages at `evidence/generate/capability-contexts/BC-{NNN}/`.
```

# Phase 4 — Client fan-out

Load `templates/clients.yml`. For each selected client, resolve its entry
(following `aliases`), then for every skill written under
`.agents/skills/{name}/`:

1. Substitute `{name}` into the client's `skills_path`.
2. Copy the body unchanged. Never re-derive content per client — the
   universal artifact from Phase 3 is the single source.
3. Add the client's `extra_frontmatter` fields. For `claude`, populate
   `allowed-tools` per the table below; for `opencode`, set
   `compatibility: opencode`; for `cursor`, set `globs` and `alwaysApply`.
4. Record every written path in the run manifest's `written` list, tagged
   with the client id.

For `instructions_mode: prepend-section`, insert a `# {Project Name}`
section at the top of the existing file and record the path in `merged`,
not `written` — BrownKit does not own `CLAUDE.md` or `AGENTS.md`. Same for
any `hooks` target: merge the `hooks` key, never overwrite the file, and
record it in `merged`.

| Skill | `allowed-tools` base value |
|---|---|
| `attach-context` | `Read` |
| `review-capability` | `Read Bash(git status) Bash(git diff *)` |
| `fix-bug` | `Read Write Edit Bash(git status) Bash(git diff *)` |
| `add-test` | `Read Write Edit` |
| `add-endpoint` / `add-module` / `add-handler` | `Read Write Edit` |
| `add-migration` | `Read Write Edit` |
| `add-model` | `Read Write Edit` |
| `add-component` | `Read Write Edit` |
| Capability-derived | `Read Write Edit Bash(git status)` |

After applying the base value, append tool entries derived from
`context.json → tools.test_runner.command` and `context.json → tools.build.command`:

| Detected tool | Append |
|---|---|
| `npm` test runner | `Bash(npm test) Bash(npm run *)` |
| `pytest` | `Bash(pytest *)` |
| `vitest` | `Bash(npx vitest *)` |
| `jest` | `Bash(npx jest *)` |
| `mvn` | `Bash(mvn *)` |
| `gradle` / `gradlew` | `Bash(./gradlew *)` |
| `make` | `Bash(make *)` |

When `tools.test_runner.command` is `null`, append nothing and note the
omission in the manifest's `skipped` list. An `allowed-tools` value decides
which commands an agent may run without prompting the user — a guessed
entry there is a real hazard, not a cosmetic defect.

# Phase 5 — Manifest, workflow, and summary

## Write `evidence/scaffold/run-manifest.json`

```json
{
  "schema_version": "1.0",
  "started_at": "<ISO-8601 UTC>",
  "completed_at": "<ISO-8601 UTC>",
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

`written` is what BrownKit owns and may delete on a later run. `merged` is
what it modified but does not own — never deleted. `skipped` records every
planned artifact the evidence could not support, with the reason.

Set `completed_at` only after every write succeeds. A null `completed_at`
is how Phase 2 detects an interrupted run.

## Update `workflow.json`

- `phases.scaffold.status = "completed"`.
- `phases.scaffold.started_at` / `completed_at` set.
- `phases.scaffold.artifacts[]` — every path from `written`.
- Append to `notes[]` each `skipped` entry with its reason, and a
  `"scaffold ran in degraded mode: <missing fields>"` note when applicable.

## Summarize to the user

- Skill count by tier (core / capability / dev / stack / opt-in).
- Subagents written; whether the security subagent was omitted and why.
- Per client: count of copies written and the path root.
- Files **overwritten** that no manifest owned (pre-v1.1.0 leftovers).
- Files **deleted**, with the confirmation that was given.
- Files **merged** and left in place for manual removal.
- Every `skipped` artifact with its reason.
- Whether the run was degraded, and which `context.json` fields to set.
- Next command — `speckit.brownkit.finish`.

# Outputs

- `evidence/scaffold/run-manifest.json`
- `evidence/scaffold/client-integrations.json`
- `evidence/scaffold/instructions.md`
- `evidence/scaffold/prompts/{name}.md`
- `evidence/scaffold/hooks/{name}.json`
- `.agents/skills/{name}/SKILL.md`
- `.agents/subagents/{dev,qa,security}/SUBAGENT.md`
- `.agents/agent.md`
- Per selected client: paths resolved from `templates/clients.yml`

# Acceptance gates

1. Every artifact in `plan.artifacts` has output; every artifact in
   `plan.declined` is **absent, not a stub**. `security-guidelines`, the
   `security` subagent, and the `review-security` prompt are omitted
   entirely unless `workflow.json.phases.assess.status == "completed"`.
2. Every `SKILL.md` has valid agentskills.io frontmatter: `name` matches its
   parent directory, `description` is non-empty, `metadata.source` is
   `"brownkit"`.
3. No generic placeholders. Every body references real evidence paths,
   entity names, and file paths. Where a tool command was `not-collected`,
   the body says so explicitly rather than naming an invented command.
4. Every client in `client-integrations.json` has output at the path its
   `templates/clients.yml` entry declares, in the declared format.
5. `run-manifest.json` lists every written path; `merged` entries are
   flagged not-owned; `completed_at` is set.
6. `workflow.json.phases.scaffold.status == "completed"`.

If any gate fails, fix before returning control.
