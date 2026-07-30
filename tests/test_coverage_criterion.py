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
