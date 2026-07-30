import shutil
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


class MultilineCiExtractionTests(unittest.TestCase):
    """Review found that multi-line CI steps were silently dropped: a GHA
    `run: |` block scalar captured only the literal "|" (no real command,
    no signal anything was missed), and a Jenkins `sh '''...'''` block
    produced zero matches. detect_stack's rule is to emit every candidate
    it found -- seeing nothing is worse than a bad candidate, since /init
    can't ask the user about a command that was never reported."""

    def setUp(self):
        self.tmp = Path(__file__).parent / "_tmp_multiline_ci"
        (self.tmp / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
        self.workflow = self.tmp / ".github" / "workflows" / "ci.yml"
        self.workflow.write_text(
            "jobs:\n"
            "  build:\n"
            "    steps:\n"
            "      - run: |\n"
            "          mvn -B verify\n"
            "          # skip: comment line, not a command\n"
            "          mvn -B jacoco:report\n",
            encoding="utf-8",
        )
        self.jenkinsfile = self.tmp / "Jenkinsfile"
        self.jenkinsfile.write_text(
            "pipeline {\n"
            "  stages {\n"
            "    stage('build') {\n"
            "      steps {\n"
            "        sh '''\n"
            "          mvn -B verify\n"
            "          mvn -B jacoco:report\n"
            "        '''\n"
            "      }\n"
            "    }\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_gha_block_scalar_yields_two_candidates_with_line_numbers(self):
        cmds = ds._ci_commands(self.tmp)
        by_command = {
            c["command"]: c["source"] for c in cmds
            if c["source"].startswith(".github/workflows/ci.yml")
        }
        self.assertEqual(by_command.get("mvn -B verify"),
                          ".github/workflows/ci.yml:5")
        self.assertEqual(by_command.get("mvn -B jacoco:report"),
                          ".github/workflows/ci.yml:7")

    def test_gha_block_scalar_comment_line_is_ignored(self):
        cmds = ds._ci_commands(self.tmp)
        commands = [c["command"] for c in cmds]
        self.assertFalse(any("skip" in c or c.startswith("#") for c in commands))

    def test_jenkins_triple_quoted_sh_yields_two_commands(self):
        cmds = ds._ci_commands(self.tmp)
        by_command = {
            c["command"]: c["source"] for c in cmds
            if c["source"].startswith("Jenkinsfile")
        }
        self.assertEqual(by_command.get("mvn -B verify"), "Jenkinsfile:6")
        self.assertEqual(by_command.get("mvn -B jacoco:report"), "Jenkinsfile:7")

    def test_no_bare_block_indicator_candidate_survives(self):
        """The original defect: a bare "|" captured as a fake command."""
        cmds = ds._ci_commands(self.tmp)
        commands = [c["command"] for c in cmds]
        self.assertNotIn("|", commands)


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


class DatabaseFallbackTests(unittest.TestCase):
    """A DB dependency can be detected generically (e.g. Dapper, a .NET
    micro-ORM matched by DB_DEP_PATTERNS) without matching any vendor
    needle in DATABASE_DEPS. Per the human partner's ruling, the fallback
    candidate must use the term "not-collected" -- BrownKit's existing
    vocabulary for a known-present, unidentified signal -- not invent a
    new word like "unknown", and must explain itself via `source`."""

    def setUp(self):
        self.tmp = Path(__file__).parent / "_tmp_db_fallback"
        self.tmp.mkdir(parents=True, exist_ok=True)
        (self.tmp / "pom.xml").write_text(
            "<project>\n"
            "  <!-- data access via Dapper -->\n"
            "</project>\n",
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_unresolved_vendor_reports_not_collected(self):
        database = ds.detect(self.tmp)["candidates"]["stack"]["database"]
        self.assertEqual(len(database), 1)
        self.assertEqual(database[0]["value"], "not-collected")
        self.assertIn("vendor unresolved", database[0]["source"])


class BackwardCompatTests(unittest.TestCase):
    def test_existing_keys_unchanged(self):
        result = ds.detect(SAMPLE)
        for key in ("schema_version", "root", "project", "adaptations"):
            self.assertIn(key, result)
        self.assertIn("has_frontend", result["project"])


if __name__ == "__main__":
    unittest.main()
