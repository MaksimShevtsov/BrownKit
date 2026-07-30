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


class OutOfRangeSidecarTests(unittest.TestCase):
    """`actual`/`target` must be fractions in [0,1] per discover.md:137. A
    sidecar reporting a percentage where a fraction belongs (or vice versa)
    must not be trusted at face value -- that is exactly the failure class
    this release exists to remove."""

    def tearDown(self):
        shutil.rmtree(TMP, ignore_errors=True)

    def test_actual_out_of_range_falls_back_to_labeled_line(self):
        # actual: 0.93 correct fraction, but here we simulate the reverse
        # mistake -- actual reported as a percentage (93) instead of 0.93.
        # An out-of-range actual must fall through to the coverage.md
        # labeled line rather than being scaled into a bogus 9300%.
        result = criterion10(build(
            coverage_md=ORPHAN_FIRST,
            summary={"schema_version": "1.0", "actual": 93, "target": 0.90,
                     "mapped": 93, "significant": 100, "orphans": 0, "dead_code": 0},
        ))
        self.assertEqual(result["status"], "pass")
        self.assertIn("93.4", result["detail"])
        self.assertIn("coverage.md labeled line", result["detail"])

    def test_target_out_of_range_falls_back_to_90_default(self):
        # target: 90 (a percentage) instead of 0.90 (a fraction) must not
        # become a 9000% threshold -- it must fall back to the 90.0 default.
        result = criterion10(build(summary={
            "schema_version": "1.0", "actual": 0.93, "target": 90,
            "mapped": 93, "significant": 100, "orphans": 0, "dead_code": 0,
        }))
        self.assertEqual(result["status"], "pass")
        self.assertIn("target 90%", result["detail"])

    def test_boolean_actual_is_rejected(self):
        # bool is a subclass of int in Python; isinstance(True, (int, float))
        # is True, so this must be explicitly excluded.
        result = criterion10(build(
            coverage_md=ORPHAN_FIRST,
            summary={"schema_version": "1.0", "actual": True, "target": 0.90,
                     "mapped": 1, "significant": 1, "orphans": 0, "dead_code": 0},
        ))
        self.assertEqual(result["status"], "pass")
        self.assertIn("coverage.md labeled line", result["detail"])

    def test_boolean_target_is_rejected(self):
        result = criterion10(build(summary={
            "schema_version": "1.0", "actual": 0.93, "target": True,
            "mapped": 93, "significant": 100, "orphans": 0, "dead_code": 0,
        }))
        self.assertEqual(result["status"], "pass")
        self.assertIn("target 90%", result["detail"])


if __name__ == "__main__":
    unittest.main()
