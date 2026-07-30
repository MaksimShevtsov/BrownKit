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
