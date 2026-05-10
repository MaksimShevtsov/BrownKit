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
- **Project instructions** — a grounded AI project brief (`evidence/generate/instructions.md`)
  covering stack, paths, workflow commands, capability index, entity ownership,
  and conventions. Placed at each client's native instructions path (e.g.,
  `.github/copilot-instructions.md`, prepended to `CLAUDE.md`).
- **Skills** — [agentskills.io](https://agentskills.io)-compliant `SKILL.md`
  files under `.agents/skills/` in four tiers: core (attach-context,
  review-capability, fix-bug, add-test), capability-derived (one per
  HIGH/MEDIUM L1), dev skills (add-endpoint, add-component, etc. — adding new
  code to existing layers), and stack skills (implement-feature, write-docs,
  modernize-\<lang\>-module — improving existing code). Opt-in: business-rules
  and security-guidelines. Client copies written to each selected client's
  native skill path with correct frontmatter extensions (Claude Code gets
  `allowed-tools` and `argument-hint`; Copilot gets `agent-md` + `prompt.md`;
  Gemini and OpenCode get `SKILL.md` at their native paths).
- **Prompts** — task-scoped prompts (implement-feature, fix-bug, write-tests,
  review-changes, and opt-in review-security) grounded in actual capability IDs
  and file paths. Placed at each client's native prompt path.
- **Hooks** — opt-in automation hooks (session-start project summary,
  pre-tool-use guard, post-tool-use lint/test) placed at each client's native
  hook location.
- **Subagents and project agent** — role-focused `SUBAGENT.md` files under
  `.agents/subagents/` (dev, qa, and security if `/assess` ran) and a
  project entry-point agent at `.agents/agent.md`, all grounded in the
  capability evidence.

## Interactive planning

Before writing any files, `/generate` asks two questions: which artifact
types to produce (skills by tier, opt-in business-rules and
security-guidelines skills, subagents, project agent, context packages,
prompts, spec seeds), and which installed clients to generate copies for.
For any client not in the built-in table, it asks for a documentation URL
or searches for it via `https://agentskills.io/clients` and a web search,
confirms the result with the user, and records the source in
`client-integrations.json`.

## Gates

8 acceptance gates. Most important: every `files.txt` contains only
existing paths (no generated / vendored code); every prompt cites at least
one specific evidence id; spec seeds never fabricate requirements; every
`SKILL.md` body references actual evidence paths, not generic placeholders.
