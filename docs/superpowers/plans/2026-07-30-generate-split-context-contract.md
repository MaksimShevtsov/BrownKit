# BrownKit v1.1.0 — `/generate` Split & `context.json` Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the 1026-line `/generate` command into evidence packaging plus a new `speckit.brownkit.scaffold` command, define the `context.json` `stack`/`paths`/`tools` contract that the scaffolding half reads, and fix the coverage-criterion false-fail.

**Architecture:** BrownKit is a spec-kit extension: markdown command prompts under `commands/`, stdlib-only Python helpers under `scripts/python/` with bash and PowerShell shims, JSON Schema contracts under `docs/schemas/`, and skeleton templates under `templates/`. There is no runtime — the "code" is prompts plus deterministic helper scripts. This work adds one command prompt, one data template, two helper capabilities, and three schema amendments.

**Tech Stack:** Markdown prompt files, Python 3.9+ (stdlib only), JSON Schema draft 2020-12, YAML manifests. Test harness: stdlib `unittest`. Schema validation: `check-jsonschema` (pip, dev-only).

**Spec:** [`docs/superpowers/specs/2026-07-30-generate-split-context-contract-design.md`](../specs/2026-07-30-generate-split-context-contract-design.md)

**Branch:** `design/generate-split-context-contract`

## Pre-flight amendments

Three rulings made before execution, after a scan for places where the plan mandated something a review rubric would flag:

1. **Tasks 7 and 8 merged into one task** (now Task 7, 20 steps). Splitting them meant Task 7's review would see ~450 lines duplicating `generate.md` and flag it correctly, since the removal was in a task it could not see. As one task the diff reads as the move it is. Task count is now **10**; former Tasks 9/10/11 are now 8/9/10.
2. **Stated test counts are informational** — see Global Constraints below.
3. **Task 10's docs assertion narrowed** from the bare word `"client"` to specific markers (`.agents/skills`, `subagent`, `clients.yml`, `client-integrations`), which tests the real requirement without failing on legitimate prose.

## Global Constraints

Every task's requirements implicitly include this section.

- **Python ≥ 3.9, stdlib only** for everything under `scripts/python/`. No third-party imports. `tomllib` is unavailable (3.11+) — use line-prefix scanning for TOML.
- **`schema_version` stays `"1.0"`** in every schema and template. No version bumps.
- **New schema fields are optional.** Never add a name to a `required` array; never add a phase to a `required` array. Additive-only, so existing v1.0.2 evidence trees stay valid.
- **`not-collected` is a first-class value.** Never substitute `0`, `""`, `"none"`, or omit a field to keep output well-formed. Absent signals are `null` with a stated reason.
- **Helper scripts emit JSON on stdout and write nothing to disk.** Exit non-zero only per each script's documented contract.
- **Every finding carries a source.** File path, and line number where meaningful.
- **Two files are append-only for version metadata:** bump `extension.yml` `version` and add a `CHANGELOG.md` entry only in the final docs task.
- **Stated test counts are informational, not assertions.** A green suite is the gate. Adding a legitimate test case that raises the count above the stated number is fine and welcome — report the actual count, do not delete coverage to match the plan, and do not treat a higher count as a failure. A count *below* the stated number means tests were skipped or lost: investigate that.

## Testing approach

This repo has no test harness today. Two kinds of verification, used per task type:

1. **Python helper changes** (`detect_stack.py`, `validate_evidence.py`, `check_prompt_refs.py`) get real unit tests in `tests/` using stdlib `unittest`. Run with `python -m unittest discover -s tests -v`.
2. **Markdown prompt and schema changes** cannot be unit-tested. Their verification is an *executable check*: the reference-integrity guard built in Task 1, `check-jsonschema` against the templates, or a `grep` assertion with an exact expected count. Every such step states the command and its expected output.

On Windows use `python`; the repo's shims use `python3`. Both are noted where it matters.

---

### Task 1: Reference-integrity guard (proves the core bug)

Build the tool that detects the defect this release fixes. It must **fail** against the current repo, which is the evidence that finding #1 is real.

**Files:**
- Create: `scripts/python/check_prompt_refs.py`
- Create: `tests/__init__.py` (empty)
- Create: `tests/test_check_prompt_refs.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces:
  - `extract_refs(text: str) -> list[tuple[str, str]]` — returns `(document, dotted_path)` pairs parsed from `` `context.json → a.b` `` spans. `document` is always `"context.json"` for now.
  - `resolve(schema: dict, dotted_path: str) -> bool` — walks `properties` nesting, following local `$ref` pointers into `$defs`; `True` when every segment resolves. `$ref` support is required: Task 2 declares `tools.test_runner` as `{"$ref": "#/$defs/tool"}`, and Task 7 references `tools.test_runner.command`.
  - `check(commands_dir: Path, schema_path: Path) -> list[dict]` — returns one `{"file", "line", "path"}` dict per unresolved reference.

- [ ] **Step 1: Write the failing test**

Create `tests/__init__.py` as an empty file, then `tests/test_check_prompt_refs.py`:

```python
import json
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "python"))

import check_prompt_refs as m

SCHEMA = {
    "properties": {
        "project": {"properties": {"name": {"type": "string"}}},
        "tools": {"properties": {"test_runner": {"$ref": "#/$defs/tool"}}},
    },
    "$defs": {
        "tool": {"properties": {"command": {"type": ["string", "null"]}}},
    },
}


class ExtractRefsTests(unittest.TestCase):
    def test_extracts_arrow_reference(self):
        text = "read `context.json → tools.test_runner` now"
        self.assertEqual(m.extract_refs(text), [("context.json", "tools.test_runner")])

    def test_extracts_bare_dotted_reference(self):
        text = "from `context.json → stack`"
        self.assertEqual(m.extract_refs(text), [("context.json", "stack")])

    def test_ignores_unrelated_backticks(self):
        self.assertEqual(m.extract_refs("`qa-context.json` is fine"), [])


class ResolveTests(unittest.TestCase):
    def test_resolves_nested_path(self):
        self.assertTrue(m.resolve(SCHEMA, "project.name"))

    def test_rejects_missing_top_level(self):
        self.assertFalse(m.resolve(SCHEMA, "paths"))

    def test_rejects_missing_leaf(self):
        self.assertFalse(m.resolve(SCHEMA, "project.codebase_path"))

    def test_follows_local_ref_into_defs(self):
        """Task 2 declares tools.test_runner as {"$ref": "#/$defs/tool"} and
        Task 7 references tools.test_runner.command, so $ref must be walked."""
        self.assertTrue(m.resolve(SCHEMA, "tools.test_runner.command"))

    def test_rejects_missing_leaf_behind_a_ref(self):
        self.assertFalse(m.resolve(SCHEMA, "tools.test_runner.bogus"))


class CheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(__file__).parent / "_tmp_refs"
        (self.tmp / "commands").mkdir(parents=True, exist_ok=True)
        self.schema_path = self.tmp / "schema.json"
        self.schema_path.write_text(json.dumps(SCHEMA), encoding="utf-8")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_reports_unresolved_with_line_number(self):
        cmd = self.tmp / "commands" / "demo.md"
        cmd.write_text(
            "line one\nuses `context.json → paths.src` here\n",
            encoding="utf-8",
        )
        findings = m.check(self.tmp / "commands", self.schema_path)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["path"], "paths.src")
        self.assertEqual(findings[0]["line"], 2)

    def test_silent_when_all_resolve(self):
        cmd = self.tmp / "commands" / "ok.md"
        cmd.write_text("uses `context.json → project.name`\n", encoding="utf-8")
        self.assertEqual(m.check(self.tmp / "commands", self.schema_path), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s tests -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'check_prompt_refs'`

- [ ] **Step 3: Write the implementation**

Create `scripts/python/check_prompt_refs.py`:

```python
#!/usr/bin/env python3
"""Verify that every `context.json -> path` reference in command prompts
resolves against the context schema.

Repo-maintenance tool, not a pipeline accelerator: no bash or PowerShell shim.

Exit codes:
  0  - every reference resolves.
  1  - at least one reference is unresolved.
  2  - commands directory or schema file missing.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Matches: `context.json -> a.b.c` with the unicode arrow, optional spaces.
REF = re.compile(r"`(context\.json)\s*→\s*([A-Za-z_][\w.]*)`")


def extract_refs(text: str) -> list[tuple[str, str]]:
    return [(m.group(1), m.group(2)) for m in REF.finditer(text)]


def _deref(schema: dict, node: dict) -> dict:
    """Follow a local $ref like '#/$defs/tool'. Non-local refs are left alone."""
    seen = 0
    while isinstance(node, dict) and isinstance(node.get("$ref"), str) and seen < 10:
        ref = node["$ref"]
        if not ref.startswith("#/"):
            return node
        target = schema
        for part in ref[2:].split("/"):
            if not isinstance(target, dict) or part not in target:
                return node
            target = target[part]
        node = target
        seen += 1
    return node


def resolve(schema: dict, dotted_path: str) -> bool:
    node = schema
    for segment in dotted_path.split("."):
        node = _deref(schema, node)
        props = node.get("properties")
        if not isinstance(props, dict) or segment not in props:
            return False
        node = props[segment]
    return True


def check(commands_dir: Path, schema_path: Path) -> list[dict]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    findings: list[dict] = []
    for md in sorted(commands_dir.glob("*.md")):
        for lineno, line in enumerate(md.read_text(encoding="utf-8").splitlines(), 1):
            for _doc, dotted in extract_refs(line):
                if not resolve(schema, dotted):
                    findings.append({
                        "file": str(md).replace("\\", "/"),
                        "line": lineno,
                        "path": dotted,
                    })
    return findings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--commands", default="commands")
    ap.add_argument("--schema", default="docs/schemas/context.schema.json")
    args = ap.parse_args(argv)

    commands_dir = Path(args.commands)
    schema_path = Path(args.schema)
    if not commands_dir.is_dir() or not schema_path.is_file():
        print(json.dumps({"error": "commands dir or schema file not found"}, indent=2))
        return 2

    findings = check(commands_dir, schema_path)
    json.dump({"unresolved": len(findings), "findings": findings}, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s tests -v`
Expected: PASS — 10 tests

- [ ] **Step 5: Run the guard against the real repo to prove the bug**

Run: `python scripts/python/check_prompt_refs.py`
Expected: exit code 1, `unresolved: 16`. All sixteen are in `commands/generate.md`:

| Lines | Reference | Fixed by |
|---|---|---|
| 567 (×2), 586, 591, 769 | `tools.test_runner`, `tools.build` | Task 2 |
| 727, 767, 768, 793 | `tools` | Task 2 |
| 666, 703, 723 | `stack` | Task 2 |
| 725 | `paths` | Task 2 |
| 630 | `security_context.compliance_targets` | Task 3 |
| 720 | `project_name` | Task 3 |
| 734 | `security_context` | Task 3 |

Record the exact number. Task 2 drives it to 3, Task 3 to 0.

- [ ] **Step 6: Commit**

```bash
git add scripts/python/check_prompt_refs.py tests/__init__.py tests/test_check_prompt_refs.py
git commit -m "test: add context.json reference-integrity guard

Fails against the current repo with 16 unresolved references in
generate.md, which is the defect v1.1.0 fixes."
```

---

### Task 2: `context.json` contract — schema and template

**Files:**
- Modify: `docs/schemas/context.schema.json` (add `stack`, `paths`, `tools`; fix `package_manifests` at line 27)
- Modify: `templates/context.json` (add the three blocks)
- Create: `tests/test_context_schema.py`

**Interfaces:**
- Consumes: nothing from Task 1 (the guard is a separate binary).
- Produces: the `stack` / `paths` / `tools` JSON shapes that Tasks 4, 5, 7, and 8 read. Exact field names:
  - `stack`: `language`, `backend`, `frontend`, `database`, `package_manager` — all `["string","null"]`.
  - `paths`: `src`, `test`, `migrations` — all `["string","null"]`.
  - `tools`: `test_runner`, `build`, `lint` — each an object `{command: ["string","null"], source: "string", confidence: ["string","null"] enum HIGH|MEDIUM|LOW|null}`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_context_schema.py`:

```python
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "docs/schemas/context.schema.json").read_text(encoding="utf-8"))
TEMPLATE = json.loads((ROOT / "templates/context.json").read_text(encoding="utf-8"))


class SchemaDeclaresNewBlocks(unittest.TestCase):
    def test_declares_stack_paths_tools(self):
        for name in ("stack", "paths", "tools"):
            self.assertIn(name, SCHEMA["properties"], f"{name} not declared")

    def test_new_blocks_are_not_required(self):
        for name in ("stack", "paths", "tools"):
            self.assertNotIn(name, SCHEMA["required"],
                             f"{name} must stay optional so v1.0.2 trees validate")

    def test_tools_entries_carry_provenance(self):
        """test_runner is declared as a $ref, so deref before inspecting."""
        entry = SCHEMA["properties"]["tools"]["properties"]["test_runner"]
        self.assertEqual(entry["$ref"], "#/$defs/tool")
        tool = SCHEMA["$defs"]["tool"]
        for field in ("command", "source", "confidence"):
            self.assertIn(field, tool["properties"])

    def test_all_three_tools_share_the_tool_definition(self):
        tools = SCHEMA["properties"]["tools"]["properties"]
        for name in ("test_runner", "build", "lint"):
            self.assertEqual(tools[name]["$ref"], "#/$defs/tool")

    def test_package_manifests_is_object_form(self):
        pm = SCHEMA["properties"]["project"]["properties"]["detected"]["properties"]["package_manifests"]
        self.assertEqual(pm["items"]["type"], "object")
        for field in ("language", "path", "pattern"):
            self.assertIn(field, pm["items"]["properties"])

    def test_schema_version_unchanged(self):
        self.assertEqual(SCHEMA["properties"]["schema_version"]["const"], "1.0")


class TemplateMatchesSchema(unittest.TestCase):
    def test_template_has_new_blocks(self):
        for name in ("stack", "paths", "tools"):
            self.assertIn(name, TEMPLATE)

    def test_template_tools_use_not_collected_form(self):
        lint = TEMPLATE["tools"]["lint"]
        self.assertIsNone(lint["command"])
        self.assertEqual(lint["source"], "not-collected")
        self.assertIsNone(lint["confidence"])

    def test_template_stack_fields_are_null_not_empty_string(self):
        for value in TEMPLATE["stack"].values():
            self.assertIsNone(value, "unresolved stack fields are null, never \"\"")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_context_schema -v`
Expected: FAIL — `AssertionError: stack not declared`

- [ ] **Step 3: Add the three blocks to the schema**

In `docs/schemas/context.schema.json`, insert after the `weights` block's closing brace and before `"inputs"`:

```json
    "stack": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "language":        { "type": ["string", "null"] },
        "backend":         { "type": ["string", "null"] },
        "frontend":        { "type": ["string", "null"] },
        "database":        { "type": ["string", "null"] },
        "package_manager": { "type": ["string", "null"] }
      }
    },
    "paths": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "src":        { "type": ["string", "null"] },
        "test":       { "type": ["string", "null"] },
        "migrations": { "type": ["string", "null"] }
      }
    },
    "tools": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "test_runner": { "$ref": "#/$defs/tool" },
        "build":       { "$ref": "#/$defs/tool" },
        "lint":        { "$ref": "#/$defs/tool" }
      }
    },
```

Then add a `$defs` block as a sibling of `properties`, immediately before the closing brace of the document:

```json
  "$defs": {
    "tool": {
      "type": "object",
      "required": ["command", "source", "confidence"],
      "additionalProperties": false,
      "properties": {
        "command":    { "type": ["string", "null"] },
        "source":     { "type": "string" },
        "confidence": { "enum": ["HIGH", "MEDIUM", "LOW", null] }
      }
    }
  }
```

Do **not** add `stack`, `paths`, or `tools` to the root `required` array.

- [ ] **Step 4: Fix the `package_manifests` type**

In the same file, replace line 27:

```json
            "package_manifests":  { "type": "array", "items": { "type": "string" } },
```

with:

```json
            "package_manifests":  {
              "type": "array",
              "items": {
                "type": "object",
                "required": ["language", "path", "pattern"],
                "properties": {
                  "language": { "type": "string" },
                  "path":     { "type": "string" },
                  "pattern":  { "type": "string" }
                }
              }
            },
```

This matches what `scripts/python/detect_stack.py:252` actually emits.

- [ ] **Step 5: Add the blocks to the template**

In `templates/context.json`, insert after the `weights` block and before `"inputs"`:

```json
  "stack": {
    "language": null,
    "backend": null,
    "frontend": null,
    "database": null,
    "package_manager": null
  },
  "paths": {
    "src": null,
    "test": null,
    "migrations": null
  },
  "tools": {
    "test_runner": { "command": null, "source": "not-collected", "confidence": null },
    "build":       { "command": null, "source": "not-collected", "confidence": null },
    "lint":        { "command": null, "source": "not-collected", "confidence": null }
  },
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m unittest tests.test_context_schema -v`
Expected: PASS — 9 tests

- [ ] **Step 7: Validate the template against its own schema**

```bash
pip install check-jsonschema
check-jsonschema --schemafile docs/schemas/context.schema.json templates/context.json
```

Expected: `ok -- validation done`. Nothing in the repo did this before, which is how the `package_manifests` drift survived.

- [ ] **Step 8: Confirm the guard improved**

Run: `python scripts/python/check_prompt_refs.py`
Expected: `unresolved` dropped from 16 to **3** — `security_context.compliance_targets` at line 630, `project_name` at 720, and `security_context` at 734. All thirteen `tools` / `paths` / `stack` references now resolve, including `tools.test_runner` through the `$defs/tool` `$ref`.

- [ ] **Step 9: Commit**

```bash
git add docs/schemas/context.schema.json templates/context.json tests/test_context_schema.py
git commit -m "feat: declare context.json stack/paths/tools contract

Optional top-level blocks, so existing v1.0.2 evidence trees stay valid.
tools entries carry command/source/confidence because tools.*.command
feeds allowed-tools. Also fixes package_manifests to the object form
detect_stack.py actually emits."
```

---

### Task 3: Fix the two misnamed references in `generate.md`

**Files:**
- Modify: `commands/generate.md` (lines 630, 720, 734)

**Interfaces:**
- Consumes: `project.name` and `security_scope.compliance` — both already present in `templates/context.json` at lines 4 and 17, and declared in the schema.
- Produces: nothing new.

- [ ] **Step 1: Confirm the guard reports exactly 3**

Run: `python scripts/python/check_prompt_refs.py`
Expected: `unresolved: 3` — `security_context.compliance_targets` (line 630), `project_name` (720), `security_context` (734). All three are backtick spans, so the guard catches every one; fixing them is what drives it to zero.

- [ ] **Step 2: Fix the compliance references**

In `commands/generate.md` line 630, replace:

```
   `context.json → security_context.compliance_targets`.
```

with:

```
   `context.json → security_scope.compliance`.
```

In line 734, replace:

```
   (from `context.json → security_context`); emit only if non-empty.
```

with:

```
   (from `context.json → security_scope.compliance`); emit only if non-empty.
```

- [ ] **Step 3: Fix the project-name reference**

Replace:

```
1. **Project name and domain** (from `context.json → project_name` /
```

with:

```
1. **Project name and domain** (from `context.json → project.name` /
```

- [ ] **Step 4: Verify the guard is clean**

Run: `python scripts/python/check_prompt_refs.py`
Expected: exit code 0, `{"unresolved": 0, "findings": []}`

- [ ] **Step 5: Verify no stale names remain**

Run: `grep -rn "project_name\|compliance_targets" commands/`
Expected: no output. These two names are unambiguously wrong wherever they appear.

**Do not grep for bare `security_context`.** It is also the legitimate name of a per-capability *evidence-artifact* block produced by `/discover` D6, and correct uses exist that must not be touched:

| Location | Use | Verdict |
|---|---|---|
| `generate.md:91` | `{from security_context; compliance targets that apply}` | legitimate — the D6 block feeding a capability's `context.md` |
| `assess.md:196` | `security_context.criticality` | legitimate — D6 field |
| `validate.md:70` | `security_context.data_sensitivity` | legitimate — D6 field |

Only the backticked `` `context.json → security_context…` `` spans were wrong, and the guard is what proves those are gone: it matches `context.json →` spans specifically and ignores bare prose mentions.

- [ ] **Step 6: Commit**

```bash
git add commands/generate.md
git commit -m "fix: point generate.md at the context.json fields that exist

project_name -> project.name and security_context.compliance_targets ->
security_scope.compliance. Both targets were already in the template.
Reference guard now reports zero unresolved."
```

---

### Task 4: `detect_stack.py` candidate detection

The largest code task. Adds a `candidates` block that reports every tool command, path, and stack value found — and **adjudicates nothing**.

**Files:**
- Modify: `scripts/python/detect_stack.py`
- Create: `tests/test_detect_stack.py`

**Interfaces:**
- Consumes: the field names defined in Task 2.
- Produces, appended to `detect()`'s return dict under a new `"candidates"` key:
  - `candidates.tools.{test_runner,build,lint}` — each a list of `{"command": str, "source": str, "rank": str}`, sorted best-first. `rank` is one of `"ci"`, `"manifest-explicit"`, `"manifest-default"`.
  - `candidates.paths.{src,test,migrations}` — each a list of `{"path": str, "source": str}`.
  - `candidates.stack.{language,backend,frontend,database,package_manager}` — each a list of `{"value": str, "source": str}`.
  - New helpers: `_ci_files(root) -> list[Path]`, `_ci_commands(root) -> list[dict]`, `_classify_command(cmd) -> str | None`, `_tool_candidates(root, manifests) -> dict`, `_path_candidates(root, manifests) -> dict`, `_stack_candidates(root, manifests, frontend, has_db) -> dict`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_detect_stack.py`:

```python
import unittest
from pathlib import Path

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "python"))

import detect_stack as ds

SAMPLE = ROOT / "docs" / "examples" / "sample-repo"


class ClassifyCommandTests(unittest.TestCase):
    def test_verify_is_a_test_command(self):
        self.assertEqual(ds._classify_command("mvn -B verify"), "test_runner")

    def test_package_is_a_build_command(self):
        self.assertEqual(ds._classify_command("mvn -DskipTests package"), "build")

    def test_ruff_is_a_lint_command(self):
        self.assertEqual(ds._classify_command("ruff check ."), "lint")

    def test_unrecognised_command_is_none(self):
        self.assertIsNone(ds._classify_command("mvn -B jacoco:report"))

    def test_skiptests_flag_does_not_make_it_a_test_command(self):
        """'-DskipTests' contains 'test' as a substring; it is not a test run."""
        self.assertEqual(ds._classify_command("mvn -DskipTests package"), "build")

    def test_build_property_flag_does_not_make_it_a_build(self):
        """'-Dbuild.profile' contains 'build'; the command still runs tests."""
        self.assertEqual(
            ds._classify_command("mvn verify -Dbuild.profile=ci"), "test_runner"
        )


class CiExtractionTests(unittest.TestCase):
    def test_finds_jenkinsfile(self):
        names = [p.name for p in ds._ci_files(SAMPLE)]
        self.assertIn("Jenkinsfile", names)

    def test_extracts_sh_step_with_line_number(self):
        cmds = ds._ci_commands(SAMPLE)
        found = [c for c in cmds if c["command"] == "mvn -B verify"]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["source"], "Jenkinsfile:4")


class ToolCandidateRankingTests(unittest.TestCase):
    """The sample repo has no surefire plugin in pom.xml but its Jenkinsfile
    runs `mvn -B verify` - so CI must outrank the manifest default."""

    def setUp(self):
        self.cands = ds.detect(SAMPLE)["candidates"]["tools"]

    def test_ci_command_ranks_first(self):
        first = self.cands["test_runner"][0]
        self.assertEqual(first["command"], "mvn -B verify")
        self.assertEqual(first["source"], "Jenkinsfile:4")
        self.assertEqual(first["rank"], "ci")

    def test_manifest_default_also_offered(self):
        commands = [c["command"] for c in self.cands["test_runner"]]
        self.assertIn("mvn test", commands)

    def test_ambiguity_is_preserved_not_resolved(self):
        self.assertGreaterEqual(len(self.cands["test_runner"]), 2,
                                "detect must not pick a winner")

    def test_absent_category_is_empty_list(self):
        self.assertEqual(self.cands["lint"], [])


class StackAndPathCandidateTests(unittest.TestCase):
    def setUp(self):
        self.c = ds.detect(SAMPLE)["candidates"]

    def test_language_candidate_is_java(self):
        self.assertIn("java", [x["value"] for x in self.c["stack"]["language"]])

    def test_database_candidate_from_manifest(self):
        self.assertIn("postgres", [x["value"] for x in self.c["stack"]["database"]])

    def test_maven_src_layout_detected(self):
        self.assertIn("src/main/java", [x["path"] for x in self.c["paths"]["src"]])

    def test_maven_test_layout_detected(self):
        self.assertIn("src/test/java", [x["path"] for x in self.c["paths"]["test"]])


class BackwardCompatTests(unittest.TestCase):
    def test_existing_keys_unchanged(self):
        result = ds.detect(SAMPLE)
        for key in ("schema_version", "root", "project", "adaptations"):
            self.assertIn(key, result)
        self.assertIn("has_frontend", result["project"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_detect_stack -v`
Expected: FAIL — `AttributeError: module 'detect_stack' has no attribute '_classify_command'`

- [ ] **Step 3: Add the classification catalogs**

In `scripts/python/detect_stack.py`, add after the `COVERAGE_CANDIDATES` list:

```python
# Command classification -----------------------------------------------------

TEST_TOKENS  = ("verify", "test", "pytest", "jest", "vitest", "check")
BUILD_TOKENS = ("package", "build", "compile", "assemble", "publish")
LINT_TOKENS  = ("lint", "ruff", "black", "flake8", "eslint", "checkstyle",
                "golangci", "format", "fmt")

# Files whose shell steps are the authoritative source for tool commands.
CI_FILE_NAMES = ("Jenkinsfile", ".gitlab-ci.yml", "azure-pipelines.yml",
                 "azure-pipelines.yaml", ".travis.yml")
CI_FILE_GLOBS = (".github/workflows/*.yml", ".github/workflows/*.yaml",
                 ".circleci/config.yml", ".buildkite/pipeline.yml")

# Shell invocations inside CI configs: `sh 'cmd'`, `run: cmd`, `- cmd`.
CI_STEP = re.compile(
    r"""(?:sh\s+['"](?P<sh>[^'"]+)['"]"""
    r"""|run:\s*(?P<run>[^\n#]+)"""
    r"""|^\s*-\s+(?P<bare>(?:mvn|gradle|\./gradlew|npm|yarn|pnpm|pytest|go|dotnet|make|ruff|eslint)\s[^\n#]+))""",
    re.MULTILINE,
)

# Maven/Gradle/npm defaults used only when nothing more specific is found.
MANIFEST_DEFAULTS = {
    "pom.xml":       {"test_runner": "mvn test", "build": "mvn -DskipTests package"},
    "build.gradle":  {"test_runner": "./gradlew test", "build": "./gradlew assemble"},
    "go.mod":        {"test_runner": "go test ./...", "build": "go build ./..."},
}

# Conventional source / test / migration layouts per ecosystem marker.
PATH_LAYOUTS = {
    "pom.xml": {"src": "src/main/java", "test": "src/test/java",
                "migrations": "src/main/resources/db/migration"},
    "go.mod":  {"src": ".", "test": ".", "migrations": "migrations"},
}
GENERIC_LAYOUTS = {
    "src":        ("src", "app", "lib"),
    "test":       ("tests", "test", "spec", "__tests__"),
    "migrations": ("migrations", "db/migrate", "alembic/versions", "prisma/migrations"),
}

BACKEND_DEPS = {
    "spring-boot": "spring-boot-starter", "quarkus": "quarkus",
    "express": "\"express\"", "fastify": "\"fastify\"", "nestjs": "@nestjs/core",
    "fastapi": "fastapi", "flask": "Flask", "django": "Django",
    "gin": "gin-gonic/gin", "echo": "labstack/echo", "chi": "go-chi/chi",
}
DATABASE_DEPS = {
    "postgres": ("postgresql", "psycopg2", "\"pg\"", "lib/pq"),
    "mysql":    ("mysql-connector", "mysql2", "mariadb"),
    "mongodb":  ("mongodb", "mongoose", "pymongo"),
    "sqlite":   ("sqlite3", "sqlite"),
}
```

- [ ] **Step 4: Add the candidate-detection functions**

Add these before `def detect(`:

```python
def _classify_command(cmd: str) -> str | None:
    """Bucket a shell command into a tool category, or None if unrecognised.

    Matches whole segments, not substrings. Bare substring matching gets this
    wrong in both directions: "-DskipTests" contains "test" (so
    "mvn -DskipTests package" reads as a test command) and "-Dbuild.profile"
    contains "build" (so "mvn verify -Dbuild.profile=ci" reads as a build).
    Splitting on non-alphanumerics makes both read correctly, because the
    flag becomes "dskiptests" / "dbuild" rather than "test" / "build".
    """
    words = set(re.split(r"[^a-z0-9]+", cmd.lower()))
    for token in LINT_TOKENS:          # lint before test: "ruff check" is lint
        if token in words:
            return "lint"
    for token in TEST_TOKENS:
        if token in words:
            return "test_runner"
    for token in BUILD_TOKENS:
        if token in words:
            return "build"
    return None


def _ci_files(root: Path) -> list[Path]:
    found: list[Path] = []
    for name in CI_FILE_NAMES:
        candidate = root / name
        if candidate.is_file():
            found.append(candidate)
    for pattern in CI_FILE_GLOBS:
        found.extend(p for p in root.glob(pattern) if p.is_file())
    return found


def _ci_commands(root: Path) -> list[dict]:
    """Every shell command found in CI configs, with file:line provenance."""
    out: list[dict] = []
    for path in _ci_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel = str(path.relative_to(root)).replace("\\", "/")
        for match in CI_STEP.finditer(text):
            raw = match.group("sh") or match.group("run") or match.group("bare") or ""
            cmd = raw.strip()
            if not cmd:
                continue
            line = text[:match.start()].count("\n") + 1
            out.append({"command": cmd, "source": f"{rel}:{line}"})
    return out


def _tool_candidates(root: Path, manifests: list[dict]) -> dict:
    buckets: dict[str, list[dict]] = {"test_runner": [], "build": [], "lint": []}
    seen: set[tuple[str, str]] = set()

    def add(category: str, command: str, source: str, rank: str) -> None:
        key = (category, command)
        if key in seen:
            return
        seen.add(key)
        buckets[category].append({"command": command, "source": source, "rank": rank})

    # Rank 1 - CI config: what actually gates merges.
    for entry in _ci_commands(root):
        category = _classify_command(entry["command"])
        if category:
            add(category, entry["command"], entry["source"], "ci")

    # Rank 2 - explicit manifest scripts.
    for m in manifests:
        path = root / m["path"]
        if m["pattern"] == "package.json":
            try:
                scripts = json.loads(path.read_text(encoding="utf-8")).get("scripts", {})
            except (OSError, json.JSONDecodeError):
                continue
            for name, body in scripts.items():
                category = _classify_command(name) or _classify_command(str(body))
                if category:
                    add(category, f"npm run {name}", f"{m['path']} -> scripts.{name}",
                        "manifest-explicit")
        elif m["pattern"] == "pom.xml":
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if "maven-surefire-plugin" in text:
                add("test_runner", "mvn test", f"{m['path']} -> surefire",
                    "manifest-explicit")
        elif m["pattern"] in ("pyproject.toml", "setup.cfg"):
            try:
                lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
            except OSError:
                continue
            # Line-prefix scan, not a TOML parse: tomllib is 3.11+.
            for raw in lines:
                stripped = raw.strip()
                if stripped.startswith(("[tool.pytest", "[tool:pytest")):
                    add("test_runner", "pytest", f"{m['path']} -> {stripped}",
                        "manifest-explicit")
                elif stripped.startswith(("[tool.ruff", "[tool.black", "[flake8]")):
                    tool = stripped.strip("[]").split(".")[-1].split("]")[0]
                    add("lint", f"{tool} .", f"{m['path']} -> {stripped}",
                        "manifest-explicit")
        elif m["pattern"] in ("*.csproj", "*.sln", "*.fsproj"):
            add("test_runner", "dotnet test", m["path"], "manifest-explicit")
            add("build", "dotnet build", m["path"], "manifest-explicit")

    makefile = root / "Makefile"
    if makefile.is_file():
        try:
            for lineno, raw in enumerate(
                makefile.read_text(encoding="utf-8", errors="ignore").splitlines(), 1
            ):
                if ":" not in raw or raw.startswith(("\t", " ", "#", ".")):
                    continue
                target = raw.split(":", 1)[0].strip()
                category = _classify_command(target)
                if category:
                    add(category, f"make {target}", f"Makefile:{lineno}",
                        "manifest-explicit")
        except OSError:
            pass

    # Rank 3 - manifest presence defaults.
    for m in manifests:
        for marker, defaults in MANIFEST_DEFAULTS.items():
            if m["pattern"] == marker or m["path"].endswith(marker):
                for category, command in defaults.items():
                    add(category, command, f"{m['path']} (default)", "manifest-default")

    order = {"ci": 0, "manifest-explicit": 1, "manifest-default": 2}
    for category in buckets:
        buckets[category].sort(key=lambda c: order[c["rank"]])
    return buckets


def _path_candidates(root: Path, manifests: list[dict]) -> dict:
    out: dict[str, list[dict]] = {"src": [], "test": [], "migrations": []}
    seen: set[tuple[str, str]] = set()

    def add(kind: str, rel: str, source: str) -> None:
        if (kind, rel) in seen or not (root / rel).exists():
            return
        seen.add((kind, rel))
        out[kind].append({"path": rel, "source": source})

    for m in manifests:
        layout = PATH_LAYOUTS.get(m["pattern"])
        if layout:
            base = Path(m["path"]).parent
            for kind, rel in layout.items():
                joined = str(base / rel).replace("\\", "/").lstrip("./")
                add(kind, joined, f"{m['path']} (convention)")

    for kind, names in GENERIC_LAYOUTS.items():
        for name in names:
            add(kind, name, "directory scan")
    return out


def _stack_candidates(root: Path, manifests: list[dict],
                      frontend: dict, has_db: bool) -> dict:
    out: dict[str, list[dict]] = {
        "language": [], "backend": [], "frontend": [],
        "database": [], "package_manager": [],
    }
    seen: set[tuple[str, str]] = set()

    def add(kind: str, value: str, source: str) -> None:
        if (kind, value) in seen:
            return
        seen.add((kind, value))
        out[kind].append({"value": value, "source": source})

    for m in manifests:
        add("language", m["language"], m["path"])
        pm = {"pom.xml": "maven", "package.json": "npm", "go.mod": "go-modules",
              "Cargo.toml": "cargo", "composer.json": "composer",
              "Gemfile": "bundler"}.get(m["pattern"])
        if pm is None and m["pattern"].startswith("build.gradle"):
            pm = "gradle"
        if pm is None and m["pattern"] in ("pyproject.toml", "requirements.txt"):
            pm = "pip"
        if pm:
            add("package_manager", pm, m["path"])

    for name in frontend.get("frameworks", []):
        add("frontend", name, frontend.get("source_manifest") or "directory scan")

    for m in manifests:
        try:
            text = (root / m["path"]).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for name, needle in BACKEND_DEPS.items():
            if needle in text:
                add("backend", name, m["path"])
        for name, needles in DATABASE_DEPS.items():
            if any(n in text for n in needles):
                add("database", name, m["path"])

    if has_db and not out["database"]:
        add("database", "unknown", "DB dependency detected, vendor unresolved")
    return out
```

- [ ] **Step 5: Wire the candidates into `detect()` and drop the dead parameter**

In `detect()`, add before the `return`:

```python
    candidates = {
        "tools": _tool_candidates(root, manifests),
        "paths": _path_candidates(root, manifests),
        "stack": _stack_candidates(root, manifests, frontend, has_db_dep),
    }
```

and add `"candidates": candidates,` to the returned dict as a sibling of `"adaptations"`.

Separately, fix the unused parameter at line 113 — change:

```python
def _walk(root: Path, max_depth: int = 6):
```

to:

```python
def _walk(root: Path):
```

`max_depth` was never referenced; `rglob` walks unbounded either way. Verify no caller passes it: `grep -n "_walk(" scripts/python/detect_stack.py` must show only the definition and the single call in `_language_mix`.

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m unittest tests.test_detect_stack -v`
Expected: PASS — 15 tests

- [ ] **Step 7: Inspect real output against the fixture**

Run: `python scripts/python/detect_stack.py --root docs/examples/sample-repo`
Expected: a `candidates.tools.test_runner` array whose first entry is `{"command": "mvn -B verify", "source": "Jenkinsfile:4", "rank": "ci"}`, with `mvn test` present at `manifest-default`. Confirm `candidates.tools.lint` is `[]` — an empty list, not a fabricated command.

- [ ] **Step 8: Confirm the full suite is green**

Run: `python -m unittest discover -s tests -v`
Expected: PASS — 34 tests

- [ ] **Step 9: Commit**

```bash
git add scripts/python/detect_stack.py tests/test_detect_stack.py
git commit -m "feat: detect tool/path/stack candidates in detect-stack

Emits every candidate found with file:line provenance, ranked
ci > manifest-explicit > manifest-default, and adjudicates nothing --
/init resolves ambiguity with the user. The sample fixture proves the
ranking matters: its pom.xml has no surefire plugin, but its Jenkinsfile
runs 'mvn -B verify'.

Also drops the unused max_depth parameter from _walk."
```

---

### Task 5: `/init` resolves candidates into `context.json`

**Files:**
- Modify: `commands/init.md` (step 2 at lines 48–61, step 3 at lines 81–113, step 4 at lines 115–133, acceptance gates at lines 194–205)

**Interfaces:**
- Consumes: `candidates.tools`, `candidates.paths`, `candidates.stack` from Task 4; the `stack`/`paths`/`tools` shapes from Task 2.
- Produces: a `context.json` whose `tools.*` entries every downstream task can rely on being either a real command with provenance or explicit `not-collected`.

- [ ] **Step 1: Extend step 2 to parse the candidates block**

In `commands/init.md`, after the paragraph ending "derived adaptation hints (`db_schema_analysis`, `frontend_analysis`, `coverage_source`)." (line 61), insert:

```markdown
The helper also returns a `candidates` block — every tool command, source
path, and stack value it found, each with its provenance. It deliberately
does **not** choose between them. Resolving those candidates is step 3.

Only **tool** candidates carry a `rank` of `ci`, `manifest-explicit`, or
`manifest-default`; path and stack candidates carry a `source` only.

Candidate ranking is meaningful: `ci` outranks the others because CI config
is what actually gates merges. A repo whose `pom.xml` declares no surefire
plugin may still run `mvn -B verify` in its Jenkinsfile — that is the real
test command.
```

- [ ] **Step 2: Add candidate resolution to step 3**

In step 3, after the "**External inputs** (all optional)" list (ending line 110), insert:

```markdown
**Stack, paths, and tools** — resolve from the helper's `candidates` block.
Ask **only where the evidence is ambiguous**:

- **Exactly one candidate** → adopt it, recording its source. Ask nothing.
- **Two or more candidates** → present them with their sources (and ranks,
  for tools) and ask which one to record. For `tools.test_runner`, ask
  specifically which command CI gates on.
- **Zero candidates** → record `{ "command": null, "source": "not-collected",
  "confidence": null }`. Offer the user the chance to supply the command, but
  **do not invent one** and do not guess from the language.

**Confidence tracks evidence strength, not whether a question was asked.**
Derive `tools.*.confidence` from the adopted candidate's rank:

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
```

- [ ] **Step 3: Extend step 4 to write the blocks**

In step 4's "Include:" list (after the `inputs.*` bullet at line 124), add:

```markdown
- `stack.*` — resolved language, backend, frontend, database, package
  manager. `null` for anything unresolved.
- `paths.*` — resolved src, test, migrations roots. `null` for anything
  unresolved.
- `tools.*` — `test_runner`, `build`, `lint`, each
  `{ command, source, confidence }`. `tools.*.command` is what downstream
  tooling turns into `allowed-tools` entries, so an unresolved command must
  be `null` with `source: "not-collected"` — never a plausible guess.
```

In the same step's validation list (after line 131), add:

```markdown
- Every `tools.*` entry has all three of `command`, `source`, `confidence`.
- Every `tools.*.confidence` is `HIGH`, `MEDIUM`, `LOW`, or `null`; `null`
  only when `command` is `null`.
- Every non-null `paths.*` value exists on disk.
```

- [ ] **Step 4: Add the acceptance gate**

In the "# Acceptance gates" list, insert after gate 4:

```markdown
5. Every `tools.*` entry is either a command with a `source` and a
   `confidence`, or an explicit `{ "command": null, "source":
   "not-collected", "confidence": null }`. No fabricated commands.
```

Renumber the existing gates 5 and 6 to 6 and 7.

- [ ] **Step 5: Verify the prompt references only real fields**

Run: `python scripts/python/check_prompt_refs.py`
Expected: exit 0, `unresolved: 0`. The new prose uses `tools.*` / `paths.*` / `stack.*` which Task 2 declared.

- [ ] **Step 6: Verify the gate renumbering has no duplicates**

Run: `grep -n "^[0-9]\+\." commands/init.md | tail -8`
Expected: a contiguous `1.` through `7.` with no repeats and no gaps.

- [ ] **Step 7: Commit**

```bash
git add commands/init.md
git commit -m "feat: resolve stack/paths/tools candidates in /init

Asks only where evidence is ambiguous: one candidate is adopted silently,
several are presented with sources and ranks, zero becomes explicit
not-collected. New acceptance gate forbids fabricated tool commands."
```

---

### Task 6: Register the `scaffold` phase in the workflow and manifest schemas

Pattern-only, never `required` — the constraint that keeps existing evidence trees valid.

**Files:**
- Modify: `docs/schemas/workflow.schema.json:14-18`
- Modify: `docs/schemas/manifest.schema.json:14-16`
- Modify: `templates/workflow.json`
- Create: `tests/test_phase_registration.py`

**Interfaces:**
- Consumes: nothing.
- Produces: a validated `phases.scaffold` key that Tasks 7 and 9 write to.

- [ ] **Step 1: Write the failing test**

Create `tests/test_phase_registration.py`:

```python
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_SCHEMA = json.loads((ROOT / "docs/schemas/workflow.schema.json").read_text(encoding="utf-8"))
MANIFEST_SCHEMA = json.loads((ROOT / "docs/schemas/manifest.schema.json").read_text(encoding="utf-8"))
WORKFLOW_TEMPLATE = json.loads((ROOT / "templates/workflow.json").read_text(encoding="utf-8"))

SEVEN = ["init", "scan", "discover", "report", "assess", "generate", "finish"]


class ScaffoldIsPatternOnly(unittest.TestCase):
    def _pattern(self, schema):
        return next(iter(schema["properties"]["phases"]["patternProperties"]))

    def test_workflow_pattern_accepts_scaffold(self):
        self.assertRegex("scaffold", self._pattern(WORKFLOW_SCHEMA))

    def test_manifest_pattern_accepts_scaffold(self):
        self.assertRegex("scaffold", self._pattern(MANIFEST_SCHEMA))

    def test_workflow_still_accepts_all_seven(self):
        pattern = self._pattern(WORKFLOW_SCHEMA)
        for name in SEVEN:
            self.assertRegex(name, pattern)

    def test_workflow_pattern_rejects_unknown_phase(self):
        self.assertIsNone(re.fullmatch(self._pattern(WORKFLOW_SCHEMA), "bogus"))

    def test_scaffold_not_required_in_workflow(self):
        self.assertNotIn("scaffold", WORKFLOW_SCHEMA["properties"]["phases"]["required"],
                         "requiring scaffold invalidates every v1.0.2 workflow.json")

    def test_scaffold_not_required_in_manifest(self):
        self.assertNotIn("scaffold", MANIFEST_SCHEMA["properties"]["phases"]["required"])


class TemplateHasScaffoldPhase(unittest.TestCase):
    def test_template_declares_scaffold(self):
        self.assertIn("scaffold", WORKFLOW_TEMPLATE["phases"])

    def test_scaffold_phase_has_full_shape(self):
        phase = WORKFLOW_TEMPLATE["phases"]["scaffold"]
        self.assertEqual(
            set(phase), {"status", "started_at", "completed_at", "artifacts"}
        )
        self.assertEqual(phase["status"], "pending")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_phase_registration -v`
Expected: FAIL — `AssertionError: Regex didn't match` for `scaffold`

- [ ] **Step 3: Extend the workflow schema pattern**

In `docs/schemas/workflow.schema.json`, replace line 17:

```json
        "^(init|scan|discover|report|assess|generate|finish)$": { "$ref": "#/$defs/phase" }
```

with:

```json
        "^(init|scan|discover|report|assess|generate|scaffold|finish)$": { "$ref": "#/$defs/phase" }
```

Leave the `required` array on line 14 **unchanged**.

- [ ] **Step 4: Extend the manifest schema pattern**

In `docs/schemas/manifest.schema.json`, replace line 16:

```json
        "^(init|scan|discover|report|assess|generate|finish)$": {
```

with:

```json
        "^(init|scan|discover|report|assess|generate|scaffold|finish)$": {
```

Leave the `required` array on line 14 **unchanged**.

- [ ] **Step 5: Add the phase to the workflow template**

In `templates/workflow.json`, insert between the `generate` and `finish` lines:

```json
    "scaffold": { "status": "pending", "started_at": null, "completed_at": null, "artifacts": [] },
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m unittest tests.test_phase_registration -v`
Expected: PASS — 8 tests

- [ ] **Step 7: Validate the template and prove backward compatibility**

```bash
check-jsonschema --schemafile docs/schemas/workflow.schema.json templates/workflow.json
```

Expected: `ok -- validation done`.

Then prove a seven-phase document still validates — this is the additive promise:

```bash
python -c "import json,pathlib; d=json.loads(pathlib.Path('templates/workflow.json').read_text()); d['phases'].pop('scaffold'); pathlib.Path('legacy-workflow.json').write_text(json.dumps(d))"
check-jsonschema --schemafile docs/schemas/workflow.schema.json legacy-workflow.json
rm legacy-workflow.json
```

Expected: `ok -- validation done` for the seven-phase file too.

- [ ] **Step 8: Commit**

```bash
git add docs/schemas/workflow.schema.json docs/schemas/manifest.schema.json templates/workflow.json tests/test_phase_registration.py
git commit -m "feat: register scaffold phase, pattern-only

Added to patternProperties in both workflow and manifest schemas but not
to required, so existing seven-phase evidence trees keep validating.
Test asserts the omission so a later edit cannot regress it."
```

---

### Task 7: Extract scaffolding into `/scaffold` and trim `/generate`

**This is one move, not a copy plus a delete.** Create `commands/scaffold.md` with the content that currently lives in `commands/generate.md` Parts D / D-bis / E, and delete it from `generate.md` **in the same task**, so the diff reads as a refactor rather than as duplication. Both halves land in one commit sequence and one review.

Content described as "move" must be copied **verbatim** from the stated `generate.md` lines — not paraphrased, not regenerated. The point of the verbatim rule is that a move is reviewable: a reader can confirm nothing was lost or silently reworded. Where the plan calls for a change to moved text, it says so explicitly and gives the replacement.

**Files:**
- Create: `commands/scaffold.md`
- Create: `templates/clients.yml`
- Modify: `commands/generate.md` (delete lines 287–924; rewrite final-steps, outputs, and gates; add the deprecation notice)
- Modify: `extension.yml` (add the command entry only; the version bump is the final docs task)
- Create: `tests/test_clients_template.py`
- Create: `tests/test_generate_trimmed.py`

**Interfaces:**
- Consumes: `phases.scaffold` (Task 6); `context.json.tools.*.command`, `paths.*`, `stack.*` (Tasks 2, 5); `evidence/generate/capability-contexts/BC-*/` from `/generate` Part A.
- Produces: `evidence/scaffold/run-manifest.json` with the `plan` / `written` / `merged` / `skipped` shape that Task 8 indexes; a `/generate` whose outputs are confined to `evidence/generate/`.

**Commit structure:** two commits are expected and preferred — one adding `scaffold.md` + `clients.yml` + the `extension.yml` entry, one trimming `generate.md`. Both are part of this single task and are reviewed together.

- [ ] **Step 1: Write the failing test for the client table**

Create `tests/test_clients_template.py`. It parses the YAML with a minimal line reader rather than importing `yaml`, keeping the stdlib-only constraint:

```python
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLIENTS = ROOT / "templates" / "clients.yml"

EXPECTED = ["claude", "agy", "copilot", "gemini", "opencode", "cursor", "kiro"]


def client_ids(text: str) -> list[str]:
    """Top-level keys nested one level under `clients:` (2-space indent)."""
    ids, inside = [], False
    for raw in text.splitlines():
        if raw.startswith("clients:"):
            inside = True
            continue
        if inside:
            if raw and not raw.startswith(" "):
                break
            if raw.startswith("  ") and not raw.startswith("    ") and raw.rstrip().endswith(":"):
                ids.append(raw.strip().rstrip(":"))
    return ids


class ClientTableTests(unittest.TestCase):
    def setUp(self):
        self.text = CLIENTS.read_text(encoding="utf-8")

    def test_file_exists(self):
        self.assertTrue(CLIENTS.is_file())

    def test_all_seven_clients_present(self):
        self.assertEqual(sorted(client_ids(self.text)), sorted(EXPECTED))

    def test_claude_code_is_an_alias_not_a_duplicate_entry(self):
        self.assertNotIn("claude-code", client_ids(self.text))
        self.assertIn("claude-code", self.text)

    def test_every_client_declares_a_format(self):
        self.assertEqual(self.text.count("format:"), len(EXPECTED))

    def test_no_web_fallback_remains(self):
        for banned in ("agentskills.io/clients", "instructionsUrl", "web search"):
            self.assertNotIn(banned, self.text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_clients_template -v`
Expected: FAIL — `FileNotFoundError: templates/clients.yml`

- [ ] **Step 3: Create `templates/clients.yml`**

```yaml
# BrownKit client integration table.
# Consumed by speckit.brownkit.scaffold to fan universal .agents/ output out
# to each client's native location. Adding a client is a data edit here --
# never a prompt edit, and never a web lookup.
#
# Fields:
#   aliases            other ids that resolve to this entry
#   skills_path        {name} is substituted with the skill directory name
#   prompts_path       omit when the client has no separate prompt location
#   instructions_path  where the project AI brief goes
#   instructions_mode  write | prepend-section
#   format             skill-md | agent-md | mdc
#   extra_frontmatter  fields added on top of the agentskills.io standard set
#   hooks              target file and key, omit when unsupported
#   hooks_mode         merge (never overwrite a user-owned settings file)

clients:
  claude:
    aliases: ["claude-code"]
    skills_path: ".claude/skills/{name}/SKILL.md"
    prompts_path: ".claude/skills/{name}/SKILL.md"
    instructions_path: ".claude/CLAUDE.md"
    instructions_mode: prepend-section
    format: skill-md
    extra_frontmatter:
      - when_to_use
      - argument-hint
      - arguments
      - allowed-tools
      - disable-model-invocation
      - user-invocable
      - context
      - paths
    hooks: ".claude/settings.json#hooks"
    hooks_mode: merge

  agy:
    aliases: []
    skills_path: ".agents/skills/{name}/SKILL.md"
    instructions_path: ".agents/AGENTS.md"
    instructions_mode: write
    format: skill-md
    extra_frontmatter: []

  copilot:
    aliases: []
    skills_path: ".github/agents/brownkit.{name}.agent.md"
    prompts_path: ".github/prompts/brownkit.{name}.prompt.md"
    instructions_path: ".github/copilot-instructions.md"
    instructions_mode: write
    format: agent-md
    extra_frontmatter: []
    no_metadata_block: true

  gemini:
    aliases: []
    skills_path: ".gemini/skills/{name}/SKILL.md"
    instructions_path: ".gemini/GEMINI.md"
    instructions_mode: write
    format: skill-md
    extra_frontmatter: []
    hooks: ".gemini/settings.json#hooks"
    hooks_mode: merge

  opencode:
    aliases: []
    skills_path: ".opencode/skills/{name}/SKILL.md"
    instructions_path: "AGENTS.md"
    instructions_mode: prepend-section
    format: skill-md
    extra_frontmatter:
      - compatibility

  cursor:
    aliases: []
    skills_path: ".cursor/rules/{name}.mdc"
    instructions_path: ".cursor/rules/project.mdc"
    instructions_mode: write
    format: mdc
    extra_frontmatter:
      - globs
      - alwaysApply

  kiro:
    aliases: []
    skills_path: ".kiro/skills/{name}/SKILL.md"
    instructions_path: ".kiro/AGENTS.md"
    instructions_mode: write
    format: skill-md
    extra_frontmatter: []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_clients_template -v`
Expected: PASS — 5 tests

- [ ] **Step 5: Create `commands/scaffold.md`**

Build the file in this order. Everything described as "move" is a verbatim copy from `commands/generate.md` at the stated lines — do not paraphrase. Leave `generate.md` untouched until Step 9's commit lands; Steps 10–20 remove the moved content from it.

1. **Frontmatter:**

```markdown
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
```

2. **Phase 1 — Preflight and plan.** Move the interactive planning dialogue from `generate.md:296-380` verbatim (both the Q1 artifact checklist and the Q2 client question), and the local client-detection procedure from `generate.md:423-436` (the `.specify/integrations/` → `.specify/integrations.json` → directory-heuristics ladder). Then **delete** the paragraph at `generate.md:370-378` — the `agentskills.io` fetch and web-search fallback — and replace it with:

```markdown
For any client id not present in `templates/clients.yml`, do **not** search
for its format. Write universal `.agents/skills/` output, add a `skipped`
entry to the run manifest naming the client, and tell the user which file
to extend. Guessing a client's native path from documentation the agent
cannot verify risks writing malformed files into a user-owned directory.
```

3. **Phase 2 — Prior-run reconciliation.** New content:

```markdown
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
```

4. **Phase 3 — Universal generation.** Move, verbatim: the skill output format and rules from `generate.md:511-536`; core skills from `579-593`; capability-derived skills from `595-610`; business-rules from `612-635`; security-guidelines from `637-659`; dev skills from `661-682`; stack skills from `684-704`; project instructions from `710-748`; dev prompts from `750-780`; hooks from `782-804`; and all of Part E, `generate.md:808-922`.

Retarget every staging path from `evidence/generate/` to `evidence/scaffold/`: `instructions.md`, `prompts/`, `hooks/`, `client-integrations.json`.

5. **Phase 4 — Client fan-out.** Replace the hardcoded table at `generate.md:447-455` and the per-client generator table at `489-500` with:

```markdown
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
```

Then move the `allowed-tools` base table from `generate.md:555-565` and the tool-derived append table from `567-578` verbatim, changing every `context.json → tools.test_runner` reference to `context.json → tools.test_runner.command` and `context.json → tools.build` to `context.json → tools.build.command`, to match the object shape from Task 2. Add after the append table:

```markdown
When `tools.test_runner.command` is `null`, append nothing and note the
omission in the manifest's `skipped` list. An `allowed-tools` value decides
which commands an agent may run without prompting the user — a guessed
entry there is a real hazard, not a cosmetic defect.
```

6. **Phase 5 — Manifest, workflow, summary.** New content:

```markdown
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
```

- [ ] **Step 6: Register the command in `extension.yml`**

In the `provides.commands` list, insert after the `speckit.brownkit.generate` entry:

```yaml
    - name: "speckit.brownkit.scaffold"
      file: "commands/scaffold.md"
      description: "Generate client-agnostic skills, subagents, prompts, hooks, and project instructions from locked evidence; install them at each client's native path."
```

Do **not** touch the `version` field — that is Task 10.

- [ ] **Step 7: Verify structural integrity**

```bash
grep -c "^# Phase" commands/scaffold.md
grep -c "^[0-9]\." commands/scaffold.md
python scripts/python/check_prompt_refs.py
grep -rn "agentskills.io/clients\|instructionsUrl" commands/scaffold.md
```

Expected: 5 phases; 6 acceptance gates; guard exits 0 with `unresolved: 0` (every `tools.*.command` reference resolves against the Task 2 schema); and **no output** from the last grep — the web fallback is gone.

- [ ] **Step 8: Verify the command is registered exactly once**

Run: `grep -c "speckit.brownkit.scaffold" extension.yml`
Expected: `1`

- [ ] **Step 9: Commit**

```bash
git add commands/scaffold.md templates/clients.yml extension.yml tests/test_clients_template.py
git commit -m "feat: add speckit.brownkit.scaffold

Takes over agent-tooling generation from /generate Parts D/D-bis/E. Client
paths move to templates/clients.yml so adding a client is a data edit. The
agentskills.io web-fetch fallback is dropped: an unknown client now gets
universal output plus a skipped entry, rather than a format guessed from
documentation the agent cannot verify.

Additive -- /generate is trimmed in the next commit."
```

#### Second half — trim `/generate`

The remaining steps remove from `generate.md` exactly what the steps above added to `scaffold.md`. Do not start them until Step 9's commit exists.

- [ ] **Step 10: Write the failing test**

Create `tests/test_generate_trimmed.py`:

```python
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATE = ROOT / "commands" / "generate.md"


class GenerateIsTrimmed(unittest.TestCase):
    def setUp(self):
        self.text = GENERATE.read_text(encoding="utf-8")
        self.lines = self.text.splitlines()

    def test_scaffolding_parts_are_gone(self):
        for heading in ("# Part D", "# Part D-bis", "# Part E"):
            self.assertNotIn(heading, self.text)

    def test_parts_a_through_c_remain(self):
        for heading in ("# Part A", "# Part B", "# Part C"):
            self.assertIn(heading, self.text)

    def test_no_user_directory_writes_remain(self):
        for path in (".agents/", ".claude/", ".github/", ".gemini/", ".opencode/"):
            self.assertNotIn(path, self.text,
                             f"{path} write belongs to /scaffold now")

    def test_deprecated_flags_still_documented(self):
        for flag in ("--with-skills", "--no-skills", "--with-agents", "--no-agents"):
            self.assertIn(flag, self.text)

    def test_deprecation_points_at_scaffold(self):
        self.assertIn("speckit.brownkit.scaffold", self.text)

    def test_pipeline_lock_is_gone(self):
        self.assertNotIn("pipeline.lock.json", self.text)

    def test_six_acceptance_gates(self):
        tail = self.text.split("# Acceptance gates")[-1]
        numbered = [l for l in tail.splitlines() if l[:2] in ("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.")]
        self.assertEqual(len(numbered), 6)

    def test_file_is_substantially_shorter(self):
        self.assertLess(len(self.lines), 420,
                        "expected ~350 lines after removing Parts D/D-bis/E")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 11: Run test to verify it fails**

Run: `python -m unittest tests.test_generate_trimmed -v`
Expected: FAIL — `AssertionError: '# Part D' unexpectedly found`

- [ ] **Step 12: Delete the scaffolding parts**

Delete `commands/generate.md` lines **287–924** inclusive. That range starts at the blank line after the `---` separator following Part C (line 286) and ends at the `---` separator preceding `# Final steps` (line 924).

After deleting, the file must read: Part C's closing paragraph, a blank line, `---`, a blank line, `# Final steps`. Verify with:

```bash
grep -n -A4 "to evidence or be marked as an open question" commands/generate.md
```

Expected: the paragraph, blank, `---`, blank, `# Final steps`.

- [ ] **Step 13: Replace the four scaffolding flags with a deprecation notice**

In the `$ARGUMENTS` section, replace these two bullets (originally lines 29–32):

```markdown
- `--with-skills` / `--no-skills` — toggle client-agnostic skill generation
  under `.agents/skills/` (default: with).
- `--with-agents` / `--no-agents` — toggle subagent and project-agent
  generation under `.agents/` (default: with).
```

with:

```markdown
- `--with-skills` / `--no-skills` / `--with-agents` / `--no-agents` —
  **deprecated in v1.1.0.** Skill, subagent, prompt, and hook generation
  moved to `speckit.brownkit.scaffold`. When any of these is passed, print
  exactly one line — *"moved to `speckit.brownkit.scaffold` in v1.1.0"* —
  and otherwise proceed unchanged. Removed in 2.0.0.
```

- [ ] **Step 14: Rewrite the outputs section**

Replace the entire `# Outputs` list with:

```markdown
# Outputs

- `evidence/generate/capability-contexts/BC-{NNN}/context.md`
- `evidence/generate/capability-contexts/BC-{NNN}/files.txt`
- `evidence/generate/capability-contexts/BC-{NNN}/qa-brief.md`
- `evidence/generate/capability-contexts/BC-{NNN}/security-brief.md`  (if `assess_done`)
- `evidence/generate/capability-contexts/BC-{NNN}/risks.json`
- `evidence/generate/security-prompts.md`  (unless `--no-prompts`)
- `evidence/generate/spec-seeds/BC-{NNN}-spec-seed.md`  (per selection policy)
```

- [ ] **Step 15: Rewrite the acceptance gates**

Replace the entire `# Acceptance gates` section with:

```markdown
# Acceptance gates

1. Every capability in scope has a `capability-contexts/BC-{NNN}/` directory
   with `context.md`, `files.txt`, `qa-brief.md`, `risks.json`.
2. Every `files.txt` contains only existing paths (validate each) and does
   not include generated code or vendored dependencies.
3. Every prompt in `security-prompts.md` references at least one specific
   evidence id (threat / vulnerability / testability finding) and a file
   list. No generic prompts.
4. Every spec seed has all 8 sections; unresolved items are in **§8**, not
   silently omitted.
5. `security-brief.md` is emitted iff `assess_done`; the file is absent
   (not a stub) otherwise.
6. `workflow.json.phases.generate.status == "completed"`.

Every output is under `evidence/generate/`. This phase writes nothing to
`.agents/`, `.claude/`, or any other client directory — that is
`speckit.brownkit.scaffold`.

If any gate fails, fix before returning control.
```

- [ ] **Step 16: Add the next-step line to the summary**

In `## Summarize to the user`, delete every bullet describing skills, subagents, client copies, instructions, hooks, and web-resolved clients — from "Count of skills generated under `.agents/skills/`" through "confirm the source that was used". Keep the `files.txt` over-300 warning. Then replace the final `Next command` bullet with:

```markdown
- **Skills, subagents, prompts, and hooks are no longer produced here.** Run
  `speckit.brownkit.scaffold` next to generate them, then
  `speckit.brownkit.finish`.
```

This line is the fix for the silent-drop hazard: a user running `/generate` with no flags, exactly as in v1.0.2, is told where the missing output went.

- [ ] **Step 17: Run tests to verify they pass**

Run: `python -m unittest tests.test_generate_trimmed -v`
Expected: PASS — 8 tests

- [ ] **Step 18: Verify the reference guard and line count**

```bash
python scripts/python/check_prompt_refs.py
python -c "print(sum(1 for _ in open('commands/generate.md', encoding='utf-8')))"
```

Expected: guard exits 0 with `unresolved: 0`; line count between 330 and 400.

- [ ] **Step 19: Run the full suite**

Run: `python -m unittest discover -s tests -v`
Expected: PASS — 55 tests

- [ ] **Step 20: Commit**

```bash
git add commands/generate.md tests/test_generate_trimmed.py
git commit -m "refactor: trim /generate to evidence packaging

Deletes Parts D/D-bis/E (~640 lines) now that /scaffold owns them. The
four scaffolding flags stay recognized as deprecated no-ops through 2.0.0,
and the summary now names /scaffold as the next command -- so a user
running /generate exactly as before learns where the output went instead
of silently getting none."
```

---

### Task 8: `/finish` indexes the scaffold phase

**Files:**
- Modify: `commands/finish.md` (preconditions around line 30, Part D manifest sketch around line 190, summary around line 220)

**Interfaces:**
- Consumes: `phases.scaffold` (Task 6); `evidence/scaffold/run-manifest.json` (Task 7).
- Produces: a `manifest.json` containing a `phases.scaffold` entry when the phase ran.

- [ ] **Step 1: Add the optional-phase flag**

In `commands/finish.md`, in the "Capture optional-phase flags" list, add after the `generate_done` bullet:

```markdown
- `scaffold_done` — `workflow.json.phases.scaffold.status == "completed"`.
```

And extend the sentence that follows to read:

```markdown
Neither `/assess`, `/report`, `/generate`, nor `/scaffold` is strictly
required — but each unchecked phase downgrades the handoff bundle. Report
exactly which phases were skipped.
```

- [ ] **Step 2: Add scaffold to the manifest sketch**

In Part D's `manifest.json` example, add after the `"generate"` line:

```json
      "scaffold": { "status": "completed | skipped", ... },
```

Then add below the JSON block:

```markdown
Include the `scaffold` key only when `scaffold_done`. It is absent from the
schema's `required` list precisely so a manifest from a run that skipped
scaffolding stays valid.

When `scaffold_done`, read `evidence/scaffold/run-manifest.json` and use its
`written` list as the phase's `artifacts[]`. Do not re-walk `.agents/` or any
client directory — the manifest is the record of what BrownKit owns, and
files it does not own must not appear in the evidence manifest.
```

- [ ] **Step 3: Extend the summary**

In `## Summarize to the user`, add after the "Skipped phases" bullet:

```markdown
- **Agent tooling** — when `scaffold_done`, the count of skills, subagents,
  and client integrations from `evidence/scaffold/run-manifest.json`, plus
  any `skipped` artifacts with their reasons. When not, one line: "agent
  tooling not generated — run `speckit.brownkit.scaffold`".
```

- [ ] **Step 4: Verify**

```bash
grep -c "scaffold" commands/finish.md
python scripts/python/check_prompt_refs.py
```

Expected: at least 6 occurrences of `scaffold`; guard exits 0.

- [ ] **Step 5: Commit**

```bash
git add commands/finish.md
git commit -m "feat: index the scaffold phase in /finish

manifest.json gains a scaffold entry when the phase ran, sourced from the
run manifest's written list rather than by walking client directories --
files BrownKit does not own must not appear in the evidence manifest."
```

---

### Task 9: Coverage-criterion fix

**Files:**
- Modify: `commands/discover.md` (D3 output section around lines 110–116)
- Modify: `scripts/python/validate_evidence.py` (criterion 10 at lines 135–149)
- Create: `tests/test_coverage_criterion.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `evidence/discovery/coverage-summary.json` — `{schema_version, actual, target, mapped, significant, orphans, dead_code}` where `actual` and `target` are fractions in `[0,1]`.
  - `_coverage_figure(evidence: Path) -> tuple[float | None, float | None, int | None, str | None]` returning `(percent, target_percent, orphans, source)`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_coverage_criterion.py`:

```python
import json
import shutil
import unittest
from pathlib import Path

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "python"))

import validate_evidence as ve

TMP = Path(__file__).parent / "_tmp_coverage"

# The exact phrasing discover.md:111 tells the agent to write. Before this
# fix, criterion 10 read the 8% and reported fail on a healthy run.
ORPHAN_FIRST = """# Coverage

Architectural risks: 8% orphan rate in `payments/` suggests a hidden
capability or an abandoned experiment.

File-to-capability coverage: 93.4%
"""


def build(coverage_md=None, summary=None):
    shutil.rmtree(TMP, ignore_errors=True)
    (TMP / "discovery").mkdir(parents=True)
    (TMP / "reports").mkdir(parents=True)
    if coverage_md is not None:
        (TMP / "discovery/coverage.md").write_text(coverage_md, encoding="utf-8")
    if summary is not None:
        (TMP / "discovery/coverage-summary.json").write_text(
            json.dumps(summary), encoding="utf-8")
    return TMP


def criterion10(evidence):
    return next(r for r in ve.check(evidence) if r["id"] == 10)


class RegressionTests(unittest.TestCase):
    def tearDown(self):
        shutil.rmtree(TMP, ignore_errors=True)

    def test_orphan_rate_no_longer_hijacks_the_figure(self):
        result = criterion10(build(coverage_md=ORPHAN_FIRST))
        self.assertEqual(result["status"], "pass")
        self.assertIn("93.4", result["detail"])
        self.assertNotIn("8%", result["detail"])

    def test_sidecar_takes_precedence_over_labeled_line(self):
        result = criterion10(build(
            coverage_md=ORPHAN_FIRST,
            summary={"schema_version": "1.0", "actual": 0.42, "target": 0.90,
                     "mapped": 42, "significant": 100, "orphans": 0, "dead_code": 0},
        ))
        self.assertIn("42", result["detail"])
        self.assertEqual(result["status"], "fail")

    def test_neither_source_is_needs_review_not_fail(self):
        result = criterion10(build(coverage_md="# Coverage\n\nno figure here\n"))
        self.assertEqual(result["status"], "needs-review")

    def test_missing_file_still_fails(self):
        result = criterion10(build())
        self.assertEqual(result["status"], "fail")


class HonestSubTargetTests(unittest.TestCase):
    def tearDown(self):
        shutil.rmtree(TMP, ignore_errors=True)

    def test_sub_target_with_orphans_is_needs_review(self):
        """discover.md:114 says report the actual with its gaps rather than
        forcing 90%. With orphan context, that is not a flat failure."""
        result = criterion10(build(summary={
            "schema_version": "1.0", "actual": 0.873, "target": 0.90,
            "mapped": 412, "significant": 472, "orphans": 38, "dead_code": 22,
        }))
        self.assertEqual(result["status"], "needs-review")
        self.assertIn("87.3", result["detail"])

    def test_sub_target_without_orphans_is_fail(self):
        result = criterion10(build(summary={
            "schema_version": "1.0", "actual": 0.40, "target": 0.90,
            "mapped": 40, "significant": 100, "orphans": 0, "dead_code": 0,
        }))
        self.assertEqual(result["status"], "fail")

    def test_at_target_is_pass(self):
        result = criterion10(build(summary={
            "schema_version": "1.0", "actual": 0.91, "target": 0.90,
            "mapped": 91, "significant": 100, "orphans": 4, "dead_code": 0,
        }))
        self.assertEqual(result["status"], "pass")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_coverage_criterion -v`
Expected: FAIL — `test_orphan_rate_no_longer_hijacks_the_figure` reports `fail` with `8.0%`, which is exactly the bug.

- [ ] **Step 3: Add the figure resolver**

In `scripts/python/validate_evidence.py`, add after the `_load_json` function:

```python
COVERAGE_LABEL = re.compile(
    r"File-to-capability coverage:\s*(\d{1,3}(?:\.\d+)?)\s*%", re.IGNORECASE
)


def _coverage_figure(evidence: Path):
    """Resolve file-to-capability coverage.

    Prefers the machine-readable sidecar, falls back to an explicitly
    labeled line. Never scans for a bare percentage: coverage.md also
    carries orphan rates, and a positional match reads the wrong number.

    Returns (percent, target_percent, orphans, source).
    """
    summary = evidence / "discovery/coverage-summary.json"
    if summary.exists():
        data = _load_json(summary)
        actual = data.get("actual") if isinstance(data, dict) else None
        if isinstance(actual, (int, float)):
            target = data.get("target")
            return (
                actual * 100,
                target * 100 if isinstance(target, (int, float)) else None,
                data.get("orphans"),
                "coverage-summary.json",
            )

    coverage_md = evidence / "discovery/coverage.md"
    if coverage_md.exists():
        match = COVERAGE_LABEL.search(
            coverage_md.read_text(encoding="utf-8", errors="ignore")
        )
        if match:
            return float(match.group(1)), None, None, "coverage.md labeled line"

    return None, None, None, None
```

- [ ] **Step 4: Replace criterion 10**

Replace lines 135–149 (the `# Criterion 10` block) with:

```python
    # Criterion 10: file-to-capability coverage
    pct, target_pct, orphans, source = _coverage_figure(evidence)
    threshold = target_pct if target_pct is not None else 90.0
    if pct is None:
        if not (evidence / "discovery/coverage.md").exists():
            add(10, "File-to-capability coverage >= target", "fail",
                "coverage.md missing")
        else:
            add(10, "File-to-capability coverage >= target", "needs-review",
                "no coverage-summary.json and no labeled "
                "'File-to-capability coverage: N%' line in coverage.md")
    elif pct >= threshold:
        add(10, "File-to-capability coverage >= target", "pass",
            f"reported: {pct:.1f}% (target {threshold:.0f}%) [{source}]")
    elif orphans:
        # discover.md:114 - report the actual figure with the gaps that
        # blocked the target rather than forcing it. Not a flat failure.
        add(10, "File-to-capability coverage >= target", "needs-review",
            f"reported: {pct:.1f}% below target {threshold:.0f}% with "
            f"{orphans} orphan(s) documented [{source}]")
    else:
        add(10, "File-to-capability coverage >= target", "fail",
            f"reported: {pct:.1f}% below target {threshold:.0f}% [{source}]")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m unittest tests.test_coverage_criterion -v`
Expected: PASS — 7 tests

- [ ] **Step 6: Confirm the positional regex is gone**

Run: `grep -n 'search(r"(\\d{1,3}' scripts/python/validate_evidence.py`
Expected: no output.

- [ ] **Step 7: Specify the sidecar in `discover.md` D3**

In `commands/discover.md`, replace the D3 output paragraph (lines 110–112):

```markdown
Output: `evidence/discovery/coverage.md` — file-to-capability mapping,
orphan resolutions, and architectural risks (e.g., "8% orphan rate in
`payments/`" suggests hidden capability or abandoned experiment).
```

with:

```markdown
Outputs — **both** are required:

1. `evidence/discovery/coverage.md` — file-to-capability mapping, orphan
   resolutions, and architectural risks (e.g., "8% orphan rate in
   `payments/`" suggests hidden capability or abandoned experiment). It must
   contain a line in exactly this form, so acceptance validation can find
   the figure among the other percentages in the document:

   ```
   File-to-capability coverage: 93.4%
   ```

2. `evidence/discovery/coverage-summary.json` — the same figures, machine
   readable:

   ```json
   {
     "schema_version": "1.0",
     "actual": 0.934,
     "target": 0.90,
     "mapped": 441,
     "significant": 472,
     "orphans": 24,
     "dead_code": 7
   }
   ```

   `actual` and `target` are fractions in `[0,1]`. `/finish` acceptance
   validation prefers this file and falls back to the labeled line above.
   Reporting `orphans` is what lets validation distinguish an honestly
   reported sub-target coverage from an unexplained failure.
```

- [ ] **Step 8: Add the sidecar to D3's outputs and gates**

In `commands/discover.md`, add to the `# Outputs` list after the `coverage.md` entry:

```markdown
- `evidence/discovery/coverage-summary.json`
```

And amend acceptance gate 4 to read:

```markdown
4. File-to-capability coverage ≥ 90% — or the actual percentage is reported
   with the specific gaps preventing it. Both `coverage.md` (with its
   labeled `File-to-capability coverage: N%` line) and
   `coverage-summary.json` exist.
```

- [ ] **Step 9: Run the full suite**

Run: `python -m unittest discover -s tests -v`
Expected: PASS — 62 tests

- [ ] **Step 10: Commit**

```bash
git add commands/discover.md scripts/python/validate_evidence.py tests/test_coverage_criterion.py
git commit -m "fix: stop criterion 10 reading the orphan rate as coverage

validate_evidence grabbed the first percentage in coverage.md, and
discover.md tells the agent to write '8% orphan rate' into that same
file -- so a healthy run could report fail at 8%. D3 now also emits
coverage-summary.json, and the validator prefers it with a labeled-line
fallback so existing evidence trees do not regress.

Carrying target and orphans also lets criterion 10 distinguish an
honestly reported sub-target figure (needs-review) from an unexplained
one (fail), which discover.md:114 asks for but a bare number could not
express."
```

---

### Task 10: Docs, version bump, and release notes

**Files:**
- Modify: `README.md` (pipeline diagram line 13, command table lines 16–24, hooks paragraph line 28, evidence layout lines 67–76, install line 43)
- Modify: `extension.yml` (`version` field only)
- Modify: `CHANGELOG.md`
- Modify: `docs/methodology.md` (pipeline line 14, phase-to-artifact map lines 40–48)
- Modify: `docs/phases/generate.md`
- Create: `docs/phases/scaffold.md`
- Modify: `scripts/README.md` (script index, invocation examples)
- Create: `tests/test_docs_consistency.py`

**Interfaces:**
- Consumes: every prior task.
- Produces: nothing consumed downstream.

- [ ] **Step 1: Write the failing test**

Create `tests/test_docs_consistency.py`:

```python
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


class VersionConsistency(unittest.TestCase):
    def test_extension_version_is_1_1_0(self):
        self.assertRegex(read("extension.yml"), r'version:\s*"1\.1\.0"')

    def test_changelog_has_1_1_0_section(self):
        self.assertIn("## [1.1.0]", read("CHANGELOG.md"))

    def test_readme_install_pins_1_1_0(self):
        self.assertIn("v1.1.0.zip", read("README.md"))


class CommandRegistration(unittest.TestCase):
    def test_extension_declares_eleven_commands(self):
        self.assertEqual(read("extension.yml").count("- name: \"speckit.brownkit."), 11)

    def test_every_declared_command_file_exists(self):
        for name in re.findall(r'file:\s*"(commands/[^"]+)"', read("extension.yml")):
            self.assertTrue((ROOT / name).is_file(), f"{name} missing")


class ReadmeAccuracy(unittest.TestCase):
    def setUp(self):
        self.readme = read("README.md")

    def test_pipeline_includes_scaffold(self):
        self.assertIn("scaffold", self.readme.split("## Pipeline")[1][:400])

    def test_hook_count_claim_matches_manifest(self):
        declared = read("extension.yml").count("optional: true")
        self.assertEqual(declared, 5)
        self.assertNotIn("Three read-only commands", self.readme)

    def test_evidence_layout_lists_scaffold(self):
        self.assertIn("scaffold/", self.readme)


class PhaseDocs(unittest.TestCase):
    def test_scaffold_phase_doc_exists(self):
        self.assertTrue((ROOT / "docs/phases/scaffold.md").is_file())

    def test_generate_phase_doc_no_longer_claims_skills(self):
        """Specific markers, not the bare word 'client' -- the phase doc may
        legitimately mention downstream AI tooling."""
        text = read("docs/phases/generate.md").lower()
        for banned in (".agents/skills", "subagent.md", "subagent", "clients.yml",
                       "client-integrations"):
            self.assertNotIn(banned, text)

    def test_methodology_map_has_scaffold_row(self):
        self.assertIn("/scaffold", read("docs/methodology.md"))


class ScriptsDoc(unittest.TestCase):
    def test_index_lists_check_prompt_refs(self):
        self.assertIn("check-prompt-refs", read("scripts/README.md"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_docs_consistency -v`
Expected: FAIL — `AssertionError: Regex didn't match 'version: "1.1.0"'`

- [ ] **Step 3: Bump the version and install line**

In `extension.yml`, change `version: "1.0.2"` to `version: "1.1.0"`.

In `README.md` line 43, change `v1.0.2.zip` to `v1.1.0.zip`, and in line 54's example change `v1.1.0` to `v1.2.0` so the placeholder still reads as a *future* version.

- [ ] **Step 4: Update the README pipeline, table, and hooks paragraph**

Replace the pipeline block:

```
/init → /scan → /discover → [/report] → /assess → /generate → /finish
```

with:

```
/init → /scan → /discover → [/report] → /assess → /generate → [/scaffold] → /finish
```

Change the `generate` row's description to `Capability-scoped AI contexts and spec seeds.` and add after it:

```markdown
| `speckit.brownkit.scaffold`  | Skills, subagents, prompts, hooks, and project instructions, installed per client. |
```

Replace the hooks paragraph at line 28:

```markdown
Three read-only commands plug into the spec-kit workflow without re-running
analysis. They read existing evidence and surface the relevant slice.
```

with:

```markdown
Five hooks plug into the spec-kit workflow. Three of them — `enrich`,
`gate`, and `validate` — are read-only: they surface a slice of existing
evidence without re-running analysis. The other two invoke `/generate`,
which writes under `evidence/`. All five are optional and prompt before
running.
```

Add `scaffold/` to the evidence-layout tree after the `generate/` line:

```
└── scaffold/   run-manifest, client-integrations, instructions, prompts/, hooks/
```

- [ ] **Step 5: Update `docs/methodology.md`**

Change the pipeline line to match the README's, and add to the phase-to-artifact map after the `/generate` row:

```markdown
| `/scaffold` | `.agents/skills/`, `.agents/subagents/`, `.agents/agent.md`, `scaffold/run-manifest.json`, per-client copies |
```

Change the `/generate` row's "Writes" cell to:

```markdown
| `/generate` | `capability-contexts/BC-*/`, `security-prompts.md`, `spec-seeds/BC-*.md` |
```

(unchanged content — confirm it does not mention skills).

- [ ] **Step 6: Trim `docs/phases/generate.md` and create `docs/phases/scaffold.md`**

Remove any sub-step bullet in `docs/phases/generate.md` that mentions skills, subagents, clients, or hooks, leaving Parts A–C only.

Create `docs/phases/scaffold.md`:

```markdown
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
```

- [ ] **Step 7: Update `scripts/README.md`**

Add to the script index table:

```markdown
| `check-prompt-refs` | repo maintenance | Verify every `context.json → path` reference in `commands/*.md` resolves against `context.schema.json`. Python only — no shims. |
```

Change the `detect-stack` row's purpose to:

```markdown
| `detect-stack` | `/init` | Read-only stack detection: languages, manifests, CI, frontend, DB dep, coverage-report candidates, adaptation hints, plus ranked tool / path / stack candidates for `/init` to resolve. |
```

Add to the invocation examples:

```bash
python scripts/python/check_prompt_refs.py
```

- [ ] **Step 8: Write the changelog entry**

In `CHANGELOG.md`, replace `## [Unreleased]` with:

```markdown
## [Unreleased]

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
```

- [ ] **Step 9: Run tests to verify they pass**

Run: `python -m unittest tests.test_docs_consistency -v`
Expected: PASS — 12 tests

- [ ] **Step 10: Full verification sweep**

```bash
python -m unittest discover -s tests -v
python scripts/python/check_prompt_refs.py
check-jsonschema --schemafile docs/schemas/context.schema.json templates/context.json
check-jsonschema --schemafile docs/schemas/workflow.schema.json templates/workflow.json
python scripts/python/detect_stack.py --root docs/examples/sample-repo
```

Expected: 74 tests pass; guard exits 0; both schema validations report `ok`; `detect-stack` shows `mvn -B verify` first in `candidates.tools.test_runner`.

- [ ] **Step 11: Commit**

```bash
git add README.md CHANGELOG.md extension.yml docs/methodology.md docs/phases/generate.md docs/phases/scaffold.md scripts/README.md tests/test_docs_consistency.py
git commit -m "release: v1.1.0 -- /generate split, context contract, coverage fix

Docs, version bump, and changelog. Also corrects the README's claim of
three read-only hook commands against five registered hooks."
```

---

## Self-review

**Spec coverage:** every section maps to a task.

| Spec section | Task |
|---|---|
| §3 Architecture — `/generate` trim | 7 (Steps 10–20) |
| §3 Architecture — `/scaffold` creation, staging dir, preconditions, degraded mode | 7 (Steps 1–9) |
| §3 Architecture — pattern-only phase registration (workflow + manifest) | 6 |
| §4 `stack`/`paths`/`tools` schema and template | 2 |
| §4 `tools` provenance asymmetry | 2 |
| §4 Detection flow, ambiguity-only questioning, new `/init` gate | 5 |
| §4 Candidate source ranking (CI first) | 4 |
| §4 Ecosystem coverage, Python 3.9 TOML constraint | 4 |
| §4 Two misnamed refs, `package_manifests` type | 3, 2 |
| §5 Five phases, run manifest, re-run semantics, `clients.yml`, 6 gates | 7 |
| §6 Coverage sidecar, validator fallback, `needs-review` for honest sub-target | 9 |
| §7 Migration — deprecated flags, next-step line, hooks unchanged | 7, 10 |
| §8 Change inventory — all 4 new and 17 modified files | 1–10 |
| §9.1 Templates vs schemas | 2, 6 |
| §9.2 `detect_stack` against the fixture | 4 |
| §9.3 Reference-integrity guard | 1 |
| §9.4 Coverage regression fixture | 9 |

`docs/phases/discover.md` is correctly absent — §8 lists it as untouched.

**Placeholder scan:** no `TBD`, `TODO`, "implement later", "add error handling", or "similar to Task N". Every code step carries runnable code; every prompt step carries verbatim replacement text with exact line anchors; every verification step states its command and expected output.

**Type consistency:** `_classify_command` returns the same three category strings (`test_runner`, `build`, `lint`) used as `candidates.tools` keys in Task 4, as `context.json.tools` keys in Task 2, and as `tools.*.command` references in Task 7. `rank` values (`ci`, `manifest-explicit`, `manifest-default`) are identical between Task 4's implementation and Task 5's prose. The run manifest's four keys (`plan`, `written`, `merged`, `skipped`) match across Tasks 7, 9, and 11. `_coverage_figure` returns a 4-tuple consumed positionally in exactly one place. `check`/`extract_refs`/`resolve` signatures match between Task 1's test and implementation.

**Cumulative test counts** by task (informational — see Global Constraints): 10 → 19 → 19 → 34 → 34 → 42 → 55 → 55 → 62 → 74. Per module: `check_prompt_refs` 10, `context_schema` 9, `detect_stack` 15, `phase_registration` 8, `clients_template` 5, `generate_trimmed` 8, `coverage_criterion` 7, `docs_consistency` 12.

**Corrections applied during review:** the guard's initial count is 16, not 11 — verified by running the regex over `generate.md`. `project_name` at line 720 *is* a backtick span, so the guard catches it and Task 3 fixes all three of its references under guard coverage. And `resolve()` gained `$ref` support, without which Task 7's `tools.test_runner.command` references would have failed against Task 2's `$defs/tool` indirection.
