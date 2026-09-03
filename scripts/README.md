# BrownKit Helper Scripts

Deterministic accelerators for the LLM-driven commands. They exist so
coverage percentages, git churn numbers, and acceptance verdicts come from
parsers — not from a model guessing.

- **Real logic** lives in `python/*.py` (stdlib only — Python ≥ 3.9).
- **Wrappers** in `bash/*.sh` and `powershell/*.ps1` are thin shims that
  `exec python3 <...>.py "$@"`. Commands reference one or the other per
  spec-kit's `scripts: { sh, ps }` convention.

All scripts emit **JSON on stdout** and write **nothing** to disk, so they
compose cleanly into shell pipelines and into command prompts.

## Script index

| Script | Used by | Purpose |
|---|---|---|
| `detect-stack` | `/init` | Read-only stack detection: languages, manifests, CI, frontend, DB dep, coverage-report candidates, adaptation hints, plus ranked tool / path / stack candidates for `/init` to resolve. |
| `list-manifests` | `/scan` (SS2) | Enumerate every dependency manifest with size + sha1. |
| `parse-coverage` | `/scan` (QS2) | JaCoCo / Cobertura (incl. coverlet) / Istanbul / Go cover → uniform per-package JSON. |
| `find-secrets` | `/scan` (SS1) | Regex scan for hard-coded credentials; emits redacted snippets with HIGH/MEDIUM/LOW confidence. |
| `git-churn` | `/discover` (D6a) / `/assess` | Per-file commits over a window, normalized to repo median, tiered `high/medium/low`. |
| `validate-evidence` | `/finish` | Mechanical portion of the 14-point acceptance check. |
| `gate-verdict` | `/gate` (hook) | Deterministic `PASS / WARN / BLOCK / NOT-ASSESSED` verdict for one capability from the `/assess` evidence tree; emits the canonical `BROWNKIT-GATE v1` verdict line the hook quotes verbatim. |
| `check-prompt-refs` | repo maintenance | Verify every `context.json → path` reference in `commands/*.md` resolves against `context.schema.json`. Python only — no shims. |

## Invocation examples

```bash
scripts/bash/detect-stack.sh --root ./
scripts/bash/list-manifests.sh --root ./
scripts/bash/parse-coverage.sh --report target/site/jacoco/jacoco.xml
scripts/bash/parse-coverage.sh --report coverage/coverage-final.json --format istanbul
scripts/bash/find-secrets.sh --root ./
scripts/bash/git-churn.sh --root ./ --months 6
scripts/bash/validate-evidence.sh --evidence-dir evidence --strict
scripts/bash/gate-verdict.sh --capability BC-007 --l2 BC-007-03,BC-007-05
python scripts/python/check_prompt_refs.py
```

```powershell
scripts/powershell/detect-stack.ps1 --root .
# ...same interface as bash.
```

## Dependencies

- Python 3.9+ (stdlib only; no pip install needed).
- `git` in PATH for `git-churn`.

No other tools required. `parse-coverage` supports the four formats listed
above; add new formats by extending `scripts/python/parse_coverage.py`
`PARSERS` registry.

## Contract — graceful degradation

Every script handles its own "not-collected" path:

- `parse-coverage` exits 2 with `{ "source": "not-collected", "reason": ... }`
  when the report is missing.
- `git-churn` returns an empty `files: []` with a note when the repo has no
  commits in the window.
- `detect-stack` reports empty arrays rather than failing when a category
  has no matches.
- `validate-evidence` returns `n/a` for criteria whose inputs are absent
  (e.g., `/assess` hasn't run); only `--strict` escalates `fail` to a
  non-zero exit.
- `gate-verdict` exits 0/1/2/3 for PASS/BLOCK/NOT-ASSESSED/WARN.
  NOT-ASSESSED is fail-closed: `assess-not-run`, a missing risk map or
  vulnerability catalog, or a capability absent from the map can never
  render as PASS. Missing secondary inputs (control map, qa-gaps) surface
  as `unknown` counts in the verdict line plus a `degraded[]` entry —
  absence is a signal.

Scripts never fabricate defaults to "stay numeric". Absence is a signal.
