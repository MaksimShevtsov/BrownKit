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
