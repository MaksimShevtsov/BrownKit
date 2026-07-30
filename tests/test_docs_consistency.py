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
