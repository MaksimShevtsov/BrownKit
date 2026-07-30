# `/scaffold` — Agent Tooling Generation

**Command**: `speckit.brownkit.scaffold` · **Spec**: [`commands/scaffold.md`](../../commands/scaffold.md)

Turns the locked capability evidence into agent tooling — skills,
subagents, prompts, hooks, and a project brief — and installs it at each
detected client's native path.

## Phases

- **Phase 1** — Preflight and plan: check `phases.generate.status`, note
  degraded mode when `context.json` `tools`/`paths`/`stack` are unresolved,
  detect installed clients locally, confirm the artifact and client plan.
- **Phase 2** — Prior-run reconciliation: read `run-manifest.json`; resume
  an interrupted run, or diff the prior `written` set against the new plan
  and confirm every deletion before making it.
- **Phase 3** — Universal generation into `.agents/` plus staging under
  `evidence/scaffold/`.
- **Phase 4** — Client fan-out driven by `templates/clients.yml`.
- **Phase 5** — Write `run-manifest.json`, update `workflow.json`,
  summarize.

## Ownership model

`written` paths are BrownKit's and may be deleted on a later run, after
confirmation. `merged` paths — `CLAUDE.md`, `AGENTS.md`,
`.claude/settings.json` — are modified but never owned and never deleted.
Files present on disk but absent from any manifest are overwritten when the
plan produces them, never deleted.

## Adding a client

Edit `templates/clients.yml`. An unrecognised client id receives universal
`.agents/skills/` output and a `skipped` entry in the manifest; BrownKit
does not fetch or guess a client's format.

## Gates

6 acceptance gates. Most important: declined artifacts are absent rather
than stubbed; no artifact names a tool command that was `not-collected`;
every `merged` path is flagged not-owned in the manifest.
