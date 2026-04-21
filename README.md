# BrownKit

**Evidence-driven brownfield discovery for [spec-kit](https://github.com/github/spec-kit).**

BrownKit packages the EDCR (Evidence → Discovery → Capabilities → Risk)
methodology as a spec-kit extension. It turns an existing codebase into a
locked capability model with security and QA risk overlays — ready for
modernization planning, AI-assisted refactoring, and per-team handoff.

## Pipeline

```
/init → /scan → /discover → [/report] → /assess → /generate → /finish
```

| Command | Purpose |
| --- | --- |
| `speckit.brownkit.init`     | Capture project, security, and QA scope. Create the evidence tree. |
| `speckit.brownkit.scan`     | Extract capability, security, and QA signals from code + external inputs. |
| `speckit.brownkit.discover` | Verify candidates; lock L1/L2 capabilities; build domain model. |
| `speckit.brownkit.report`   | Emit stakeholder / architect / dev / SDET / (conditional) security reports. |
| `speckit.brownkit.assess`   | STRIDE per capability + QA risk analysis + unified scoring. |
| `speckit.brownkit.generate` | Capability-scoped AI contexts, security prompts, spec seeds. |
| `speckit.brownkit.finish`   | Validate acceptance criteria and package per-team handoffs. |

## Install

```bash
specify extension add brownkit
# or from a release archive:
specify extension add brownkit --from https://github.com/Kit-Kroker/BrownKit/archive/refs/tags/v0.1.0.zip
```

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
└── generate/    capability-contexts/, spec-seeds/, handoff/<team>/
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
