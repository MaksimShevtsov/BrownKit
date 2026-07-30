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
