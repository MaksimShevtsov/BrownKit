# Changelog

All notable changes to BrownKit are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.2.0] - 2026-09-03

### Added
- `gate-verdict` helper script — deterministic `PASS / WARN / BLOCK /
  NOT-ASSESSED` verdict for the `/gate` hook, computed from `/assess`
  evidence. Emits a canonical `BROWNKIT-GATE v1 ...` verdict line the hook
  must quote verbatim; exit codes 0/1/2/3 mirror the verdict.

### Changed
- `/gate` no longer classifies risk itself: the LLM matches the capability,
  runs `gate-verdict`, and quotes its verdict line. Missing `/assess`
  evidence surfaces as an explicit `NOT-ASSESSED` verdict instead of a
  free-text warning; sentinel composites (`unknown`/`partial`) can no
  longer drift into a PASS.
- `/assess` pins two field names consumed by `gate-verdict`: the
  vulnerability `status` review marker and the QA `posture` key.

## [1.1.0] - 2026-07-30

### Added
- `speckit.brownkit.scaffold` — new command owning skills, subagents,
  prompts, hooks, and project instructions, previously Parts D/D-bis/E of
  `/generate`. Writes a `run-manifest.json` recording every path it wrote,
  which makes re-runs safe: it deletes only what it owns, and only after
  confirmation.
- `context.json` gains optional `stack`, `paths`, and `tools` blocks.
  `tools.*` entries carry `command` / `source` / `confidence`, because
  `tools.*.command` becomes an `allowed-tools` entry and a guessed value
  there decides which commands an agent may run unprompted.
- `detect-stack` emits ranked tool / path / stack candidates with
  `file:line` provenance. CI config outranks manifest defaults — a repo
  whose `pom.xml` declares no surefire plugin may still run `mvn -B verify`
  in CI.
- `templates/clients.yml` — client paths and formats as data, so adding a
  client no longer means editing a prompt.
- `evidence/discovery/coverage-summary.json`, written by `/discover` D3.
- `scripts/python/check_prompt_refs.py` and a `tests/` suite on stdlib
  `unittest`.

### Changed
- `/generate` is evidence packaging only (Parts A–C) and writes nothing
  outside `evidence/generate/`. Its summary now names `/scaffold` as the
  next command, so a user running it exactly as before learns where the
  skills went.
- `/finish` indexes the `scaffold` phase in `manifest.json` when it ran.
- `scaffold` is registered in the workflow and manifest schemas via
  `patternProperties` only, never `required`, so existing seven-phase
  evidence trees keep validating.
- Acceptance criterion 10 reads `coverage-summary.json`, falling back to a
  labeled `File-to-capability coverage: N%` line. It can now report
  `needs-review` for an honestly documented sub-target figure instead of a
  flat `fail`.

### Deprecated
- `/generate` flags `--with-skills`, `--no-skills`, `--with-agents`, and
  `--no-agents` are recognized no-ops that print a pointer to `/scaffold`.
  Removed in 2.0.0.

### Fixed
- Acceptance criterion 10 read the first percentage in `coverage.md`, which
  `discover.md` instructs the agent to populate with an orphan rate — so a
  healthy run could report `fail` at 8%.
- `/generate` referenced `context.json → project_name` and
  `security_context.compliance_targets`; the real fields are `project.name`
  and `security_scope.compliance`.
- `context.schema.json` declared `project.detected.package_manifests` as an
  array of strings while `detect-stack` emitted objects.
- Removed the unused `max_depth` parameter from `detect_stack._walk`.
- `README.md` claimed three read-only hook commands against five registered
  hooks.

## [1.0.2] - 2026-05-25

### Changed
- `/enrich` command now surfaces open questions about the specification before
  assembling context (Phase 1b). When ambiguities exist — feature interpretation,
  unresolved FLAG items, cross-capability ownership, or spec seed open questions —
  the agent presents numbered options with a recommended choice and waits for user
  confirmation before proceeding to Phase 2.

## [1.0.1] - 2026-05-10

### Fixed
- Removed `extension.changelog` and `support` block from `extension.yml` — neither
  field is in the spec-kit extension schema, making the v1.0.0 manifest non-compliant
  with the Extension Development Guide.

## [1.0.0] - 2026-05-10

### Added
- Initial release of the EDCR brownfield pipeline as a spec-kit extension.
- All ten commands: init, scan, discover, report, assess, generate, finish, enrich, gate, validate.
- Methodology write-up and per-phase docs under `docs/`.
- Helper scripts under `scripts/` — Python core with bash + PowerShell shims:
  `detect-stack`, `list-manifests`, `parse-coverage`, `find-secrets`,
  `git-churn`, `validate-evidence`.
- Five lifecycle hooks: `before_specify`, `before_clarify`, `before_implement`,
  `after_implement`, `before_constitution`.
- `config_schema` for validation of `brownkit-config.yml`.
- `support` and `homepage` metadata for catalog discoverability.
