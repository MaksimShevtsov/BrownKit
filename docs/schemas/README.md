# BrownKit JSON Schemas

Draft-2020-12 schemas for the five load-bearing JSON artifacts. These are
the stable contracts between phases — commands and downstream tools read
and write against them.

| Schema | Written by | Consumed by |
|---|---|---|
| [`context.schema.json`](context.schema.json) | `/init` | every phase |
| [`workflow.schema.json`](workflow.schema.json) | all phases | `/finish`, reports |
| [`qa-context.schema.json`](qa-context.schema.json) | `/discover` (D6a) | `/assess`, `/report`, `/generate` |
| [`unified-risk-map.schema.json`](unified-risk-map.schema.json) | `/assess` (Phase 4–6) | `/report`, `/generate`, `/finish`, dashboards |
| [`manifest.schema.json`](manifest.schema.json) | `/finish` | external consumers (CI, dashboards) |

## Validating manually

```bash
pip install check-jsonschema
check-jsonschema --schemafile docs/schemas/qa-context.schema.json evidence/qa/qa-context.json
```

Or with `ajv` in JS projects:

```bash
npx ajv-cli validate -s docs/schemas/unified-risk-map.schema.json -d evidence/risk/unified-risk-map.json
```

## First-class "not-collected"

The QA-context and unified-risk-map schemas intentionally allow `null` for
absent measurements and `"unknown"` / `"partial"` for composites with
missing inputs. These are **not** validation failures — they are signals.

Phases that substitute `0` or `"none"` to keep a field numeric violate the
methodology and will be flagged by `/finish` acceptance validation.

## Versioning

- `schema_version` in each document is a `const` string (currently `"1.0"`).
- Breaking changes bump the major version and introduce a new schema file
  (`qa-context-v2.schema.json`, etc.). Old runs remain valid against their
  original schema.
- Additive changes (new optional fields) are allowed in-place.
