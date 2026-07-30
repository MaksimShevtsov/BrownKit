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
