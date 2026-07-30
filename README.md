# BrownKit

**Evidence-driven brownfield discovery for [spec-kit](https://github.com/github/spec-kit).**

BrownKit packages the EDCR (Evidence → Discovery → Capabilities → Risk)
methodology as a spec-kit extension. It turns an existing codebase into a
locked capability model with security and QA risk overlays — ready for
modernization planning, AI-assisted refactoring, and per-team handoff.

## Pipeline

```
/init → /scan → /discover → [/report] → /assess → /generate → [/scaffold] → /finish
```

| Command | Purpose |
| --- | --- |
| `speckit.brownkit.init`     | Capture project, security, and QA scope. Create the evidence tree. |
| `speckit.brownkit.scan`     | Extract capability, security, and QA signals from code + external inputs. |
| `speckit.brownkit.discover` | Verify candidates; lock L1/L2 capabilities; build domain model. |
| `speckit.brownkit.report`   | Emit stakeholder / architect / dev / SDET / (conditional) security reports. |
| `speckit.brownkit.assess`   | STRIDE per capability + QA risk analysis + unified scoring. |
| `speckit.brownkit.generate` | Capability-scoped AI contexts and spec seeds. |
| `speckit.brownkit.scaffold`  | Skills, subagents, prompts, hooks, and project instructions, installed per client. |
| `speckit.brownkit.finish`   | Validate acceptance criteria and package per-team handoffs. |

## Hooks

Five hooks plug into the spec-kit workflow. Four of them — `enrich`
(fired both before specify and before clarify), `gate`, and `validate` —
are read-only: they surface a slice of existing evidence without
re-running analysis. The remaining hook invokes `/generate`, which writes
under `evidence/`. All five are optional and prompt before running.

| Command | Fires | Purpose |
| --- | --- | --- |
| `speckit.brownkit.enrich`   | before specify / clarify | Surface matching L1/L2 capabilities and spec seeds for the feature in scope. |
| `speckit.brownkit.gate`     | before implement         | Check open STRIDE threats and QA risk score; warn or block if risks are unaccepted. |
| `speckit.brownkit.validate` | after implement          | Verify the delivered implementation against spec seed commitments, security constraints, and QA targets. |
| `speckit.brownkit.generate` | before constitution      | Prepare capability-scoped AI contexts and spec seeds before a constitution update. Writes under `evidence/`. |

Pass `--strict` to `gate` or `validate` to treat unresolved findings as a
hard stop.

## Install

```bash
specify extension add brownkit --from https://github.com/MaksimShevtsov/BrownKit/archive/refs/tags/v1.1.0.zip
```

## Update

The `specify extension update` command does not support external URLs, so updating requires a remove + re-add:

```bash
specify extension remove brownkit && specify extension add brownkit --from https://github.com/MaksimShevtsov/BrownKit/archive/refs/tags/v<NEW_VERSION>.zip
```

Replace `<NEW_VERSION>` with the target version (e.g. `v1.2.0`). Check [`CHANGELOG.md`](CHANGELOG.md) for what changed between versions before updating.

## Configure

Copy `config-template.yml` to `brownkit-config.yml` in your project root and
adjust scope. All fields are optional — the pipeline adapts to available
signals and marks absent inputs as `not-collected` rather than fabricating
defaults.

## Evidence layout

After a full run:

```
evidence/
├── context.json, workflow.json
├── discovery/   candidates, l1/l2, domain-model, blueprint, coverage
├── security/    signals, threats/, vulnerabilities/, controls/, risk-scores
├── qa/          test-inventory, coverage-map, testability, environments, qa-context
├── risk/        unified-risk-map
├── reports/     stakeholder, architect, dev, sdet, (security)
├── generate/    capability-contexts/, spec-seeds/, handoff/<team>/
└── scaffold/    run-manifest, instructions, prompts/, hooks/
```

## Methodology

Full write-up in [`docs/methodology.md`](docs/methodology.md). Per-phase
specs live in [`docs/phases/`](docs/phases/).

## Helper scripts

Deterministic accelerators (coverage parsers, git churn, secret scan,
acceptance validator) live under [`scripts/`](scripts/README.md). Python
core with bash and PowerShell shims. Stdlib only; Python ≥ 3.9.

## License

[MIT](LICENSE).
