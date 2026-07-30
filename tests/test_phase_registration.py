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
