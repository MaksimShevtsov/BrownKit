# `/generate` — AI-Ready Context Generation

**Command**: `speckit.brownkit.generate` · **Spec**: [`commands/generate.md`](../../commands/generate.md)

Packages the evidence into **capability-scoped contexts** so downstream AI
tooling (Cursor, Copilot, Claude Code, custom agents) works within
bounded scope. Scope first, then analyze.

## Outputs

- **Capability contexts** — one directory per capability with `context.md`,
  `files.txt` (hard boundary for tool scope), `qa-brief.md`, `risks.json`,
  and (when `/assess` has run) `security-brief.md`.
- **Security-aware prompts** — one catalog per category:
  vulnerability review, input validation hardening, least-privilege
  refactoring, testability seam introduction, integration/contract test
  drafting, environment parity fixes. Every prompt names specific
  capabilities, files, and finding ids — no generic instructions.
- **Functional specification seeds** — structured starting points for
  Refactor / Replace candidates (selection policy adapts to which earlier
  phases ran). 8-section template; unresolved items land in `§8 Open
  Questions`, never silently omitted.

## Gates

6 acceptance gates. Most important: every `files.txt` contains only
existing paths (no generated / vendored code); every prompt cites at least
one specific evidence id; spec seeds never fabricate requirements.
