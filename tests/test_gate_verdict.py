import contextlib
import io
import json
import re
import shutil
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "python"))

import gate_verdict as gv

TMP = Path(__file__).parent / "_tmp_gate"

DOMAIN_MODEL = """# Domain Model

BC-007: Payments (Domestic)                           3 L2s
------------------------------------------------------------
Processes domestic payment flows.

Security Context:
  Data Sensitivity: PII, financial
  Auth Required: yes - JWT
  Exposure: public
  Criticality: {criticality}

BC-008: Refunds                                       1 L2s
------------------------------------------------------------
Security Context:
  Data Sensitivity: PII
  Auth Required: yes - JWT
  Exposure: internal
  Criticality: low
"""


def write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def build(**overrides):
    """Temporary evidence tree for BC-007; every default spells PASS."""
    shutil.rmtree(TMP, ignore_errors=True)
    (TMP / "risk").mkdir(parents=True)
    (TMP / "security/vulnerabilities").mkdir(parents=True)
    (TMP / "security/controls").mkdir(parents=True)
    (TMP / "security/threats").mkdir(parents=True)
    (TMP / "qa").mkdir(parents=True)
    (TMP / "discovery").mkdir(parents=True)

    write_json(TMP / "workflow.json", {
        "phases": {"assess": {"status": overrides.get("assess", "completed")}},
    })
    write_json(TMP / "risk/unified-risk-map.json", {
        "schema_version": "1.0",
        "capabilities": [{
            "id": "BC-007",
            "name": "Payments (Domestic)",
            "unified": {
                "composite": overrides.get("composite", 0.42),
                "drivers": ["coverage gap on BC-007-03"],
            },
        }],
        "ranking": ["BC-007"],
    })
    write_json(TMP / "security/vulnerabilities/catalog.json",
               {"vulnerabilities": overrides.get("vulns", [])})
    write_json(TMP / "security/threats/BC-007.json",
               overrides.get("threats", {"capability": "BC-007", "categories": []}))
    write_json(TMP / "security/controls/control-map.json",
               overrides.get("controls", []))
    write_json(TMP / "qa/qa-risk-scores.json", {
        "capabilities": [{
            "capability": "BC-007",
            "posture": overrides.get("posture", "release-ready"),
        }],
    })
    write_json(TMP / "qa/qa-gaps.json", overrides.get("qa_gaps", {"gaps": []}))
    (TMP / "discovery/domain-model.md").write_text(
        DOMAIN_MODEL.format(criticality=overrides.get("criticality", "medium")),
        encoding="utf-8")
    return TMP


class HelperTests(unittest.TestCase):
    def tearDown(self):
        shutil.rmtree(TMP, ignore_errors=True)

    def test_composite_tolerates_risk_score_nesting(self):
        self.assertEqual(
            gv.composite_of({"risk_score": {"unified_composite": 0.71}}), 0.71)

    def test_composite_sentinels_and_garbage(self):
        self.assertEqual(
            gv.composite_of({"unified": {"composite": "partial"}}), "partial")
        self.assertEqual(
            gv.composite_of({"unified": {"composite": True}}), "unknown")
        self.assertEqual(gv.composite_of({}), "unknown")
        self.assertEqual(
            gv.composite_of({"unified": {"composite": 93}}), "unknown")

    def test_split_vulnerabilities_review_markers_are_not_open(self):
        catalog = {"vulnerabilities": [
            {"id": "V-1", "classification": "Confirmed", "capability": "BC-007"},
            {"id": "V-2", "classification": "Confirmed", "capability": "BC-007",
             "status": "accepted_risk"},
            {"id": "V-3", "classification": "Probable", "capability": "BC-007"},
            {"id": "V-4", "classification": "Confirmed", "capability": "BC-008"},
            {"id": "V-5", "classification": "Potential", "capability": "BC-007"},
        ]}
        confirmed, probable, reviewed = gv.split_vulnerabilities(catalog, "BC-007")
        self.assertEqual([v["id"] for v in confirmed], ["V-1"])
        self.assertEqual([v["id"] for v in probable], ["V-3"])
        self.assertEqual([v["id"] for v in reviewed], ["V-2"])

    def test_criticality_scoped_to_the_capability_section(self):
        evidence = build()
        self.assertEqual(gv.criticality_of(evidence, "BC-007"), "medium")
        self.assertEqual(gv.criticality_of(evidence, "BC-008"), "low")
        self.assertIsNone(gv.criticality_of(evidence, "BC-999"))

    def test_control_gaps_scoped_by_l2(self):
        controls = [
            {"control_family": "Validation", "capability": "BC-007",
             "present": True, "consistently_applied": False,
             "gaps": [
                 {"l2": "BC-007-03", "operation": "POST /bulk", "issue": "bypass"},
                 {"l2": "BC-007-05", "operation": "GET /stats", "issue": "none"},
             ]},
        ]
        self.assertEqual(len(gv.control_gaps_for(controls, "BC-007", None)), 2)
        self.assertEqual(len(gv.control_gaps_for(controls, "BC-007", {"BC-007-03"})), 1)
        self.assertEqual(len(gv.control_gaps_for(controls, "BC-008", None)), 0)
        self.assertIsNone(gv.control_gaps_for(None, "BC-007", None))

    def test_blocked_testability_unknown_shapes(self):
        self.assertIsNone(gv.blocked_testability_for(None, "BC-007", None))
        self.assertIsNone(gv.blocked_testability_for({"weird": 1}, "BC-007", None))
        gaps = {"gaps": [
            {"capability": "BC-007", "l2": "BC-007-03", "severity": "blocked",
             "finding": "no DI seam", "file": "PaymentGateway.cs:87"},
            {"capability": "BC-007", "l2": "BC-007-04", "severity": "impedes",
             "finding": "slow fixtures"},
        ]}
        blocked = gv.blocked_testability_for(gaps, "BC-007", None)
        self.assertEqual(len(blocked), 1)
        self.assertEqual(
            len(gv.blocked_testability_for(gaps, "BC-007", {"BC-007-04"})), 0)

    def test_high_likelihood_unmitigated(self):
        threats = {"categories": [
            {"category": "Spoofing", "findings": [
                {"id": "T-1", "likelihood_hint": "high", "description": "a"},
                {"id": "T-2", "likelihood_hint": "high", "description": "b"},
                {"id": "T-3", "likelihood_hint": "medium", "description": "c"},
            ]},
        ]}
        controls = [{"control_family": "Authentication", "capability": "BC-007",
                     "present": True, "consistently_applied": True,
                     "mitigates": ["T-1"]}]
        out = gv.high_likelihood_unmitigated(threats, controls)
        self.assertEqual([t["id"] for t in out], ["T-2"])
        self.assertEqual(out[0]["category"], "Spoofing")
        self.assertEqual(out[0]["description"], "b")

    def test_posture_lookup_shapes(self):
        self.assertEqual(
            gv.posture_of({"capabilities": [{"capability": "BC-007",
                                             "posture": "needs-work"}]}, "BC-007"),
            "needs-work")
        self.assertEqual(
            gv.posture_of({"BC-007": {"posture": "high-risk"}}, "BC-007"),
            "high-risk")
        self.assertIsNone(gv.posture_of(None, "BC-007"))

    def test_find_capability(self):
        risk_map = {"capabilities": [{"id": "BC-003"}, {"id": "BC-007"}]}
        self.assertEqual(gv.find_capability(risk_map, "BC-007")["id"], "BC-007")
        self.assertIsNone(gv.find_capability(risk_map, "BC-999"))
        self.assertIsNone(gv.find_capability({"capabilities": "oops"}, "BC-007"))


class VerdictMatrixTests(unittest.TestCase):
    def tearDown(self):
        shutil.rmtree(TMP, ignore_errors=True)

    def test_clean_pass(self):
        payload = gv.evaluate(build(), "BC-007", None)
        self.assertEqual(payload["verdict"], "PASS")
        self.assertEqual(gv.EXIT_CODES[payload["verdict"]], 0)
        self.assertEqual(
            payload["verdict_line"],
            "BROWNKIT-GATE v1 BC-007 PASS composite=0.42 confirmed_open=0 "
            "probable_open=0 blocked_testability=0 control_gaps=0 "
            "qa_posture=release-ready criticality=medium")

    def test_each_block_trigger(self):
        cases = {
            "confirmed": dict(vulns=[{"id": "V-1", "classification": "Confirmed",
                                      "capability": "BC-007"}]),
            "blocked_high": dict(qa_gaps={"gaps": [
                {"capability": "BC-007", "l2": "BC-007-03",
                 "severity": "blocked", "finding": "no DI seam"}]},
                criticality="high"),
            "composite": dict(composite=0.8),
        }
        for name, overrides in cases.items():
            with self.subTest(trigger=name):
                payload = gv.evaluate(build(**overrides), "BC-007", None)
                self.assertEqual(payload["verdict"], "BLOCK")

    def test_each_warn_trigger(self):
        cases = {
            "probable": dict(vulns=[{"id": "V-9", "classification": "Probable",
                                     "capability": "BC-007"}]),
            "posture": dict(posture="high-risk"),
            "composite_band": dict(composite=0.6),
            "control_gap": dict(controls=[
                {"control_family": "Validation", "capability": "BC-007",
                 "present": False,
                 "gaps": [{"l2": "BC-007-03", "operation": "x",
                           "issue": "missing"}]}]),
        }
        for name, overrides in cases.items():
            with self.subTest(trigger=name):
                payload = gv.evaluate(build(**overrides), "BC-007", None)
                self.assertEqual(payload["verdict"], "WARN")

    def test_boundaries(self):
        self.assertEqual(
            gv.evaluate(build(composite=0.799), "BC-007", None)["verdict"],
            "WARN")
        self.assertEqual(
            gv.evaluate(build(composite=0.599), "BC-007", None)["verdict"],
            "PASS")

    def test_sentinel_composites_force_warn(self):
        for sentinel in ("unknown", "partial"):
            with self.subTest(sentinel=sentinel):
                payload = gv.evaluate(build(composite=sentinel), "BC-007", None)
                self.assertEqual(payload["verdict"], "WARN")
                self.assertIn(f"composite={sentinel}", payload["verdict_line"])
                self.assertTrue(payload["degraded"])

    def test_blocked_with_unknown_criticality_downgrades_to_warn(self):
        payload = gv.evaluate(build(
            criticality=None,
            qa_gaps={"gaps": [
                {"capability": "BC-007", "l2": "BC-007-03",
                 "severity": "blocked", "finding": "no DI seam"}]},
        ), "BC-007", None)
        self.assertEqual(payload["verdict"], "WARN")
        self.assertIn("criticality=unknown", payload["verdict_line"])

    def test_qa_gaps_unrecognized_shape_forces_warn(self):
        payload = gv.evaluate(build(qa_gaps={"unexpected": True}), "BC-007", None)
        self.assertEqual(payload["verdict"], "WARN")
        self.assertIn("blocked_testability=unknown", payload["verdict_line"])

    def test_not_assessed_paths(self):
        evidence = build(assess="pending")
        payload = gv.evaluate(evidence, "BC-007", None)
        self.assertEqual(payload["verdict"], "NOT-ASSESSED")
        self.assertIn("reason=assess-not-run", payload["verdict_line"])

        evidence = build()
        (evidence / "workflow.json").unlink()
        self.assertEqual(
            gv.evaluate(evidence, "BC-007", None)["verdict"], "NOT-ASSESSED")

        evidence = build()
        (evidence / "risk/unified-risk-map.json").unlink()
        payload = gv.evaluate(evidence, "BC-007", None)
        self.assertIn("reason=risk-map-missing", payload["verdict_line"])

        payload = gv.evaluate(build(), "BC-999", None)
        self.assertIn("reason=capability-not-in-map", payload["verdict_line"])

        evidence = build()
        (evidence / "security/vulnerabilities/catalog.json").unlink()
        payload = gv.evaluate(evidence, "BC-007", None)
        self.assertIn("reason=catalog-missing", payload["verdict_line"])

    def test_unreadable_risk_map_is_not_assessed_not_a_crash(self):
        evidence = build()
        (evidence / "risk/unified-risk-map.json").write_text("{not json",
                                                             encoding="utf-8")
        payload = gv.evaluate(evidence, "BC-007", None)
        self.assertEqual(payload["verdict"], "NOT-ASSESSED")

    def test_wrong_shape_catalog_is_not_assessed(self):
        for shape in ({}, {"cats": []}, "oops"):
            with self.subTest(shape=shape):
                evidence = build()
                (evidence / "security/vulnerabilities/catalog.json").write_text(
                    json.dumps(shape), encoding="utf-8")
                payload = gv.evaluate(evidence, "BC-007", None)
                self.assertEqual(payload["verdict"], "NOT-ASSESSED")
                self.assertIn("reason=catalog-missing", payload["verdict_line"])

    def test_l2_scope_narrows_control_gaps(self):
        overrides = dict(controls=[
            {"control_family": "Validation", "capability": "BC-007",
             "present": False,
             "gaps": [{"l2": "BC-007-03", "operation": "a", "issue": "x"},
                      {"l2": "BC-007-05", "operation": "b", "issue": "y"}]}])
        unscoped = gv.evaluate(build(**overrides), "BC-007", None)
        self.assertEqual(unscoped["verdict"], "WARN")
        self.assertEqual(len(unscoped["inputs"]["control_gaps"]), 2)
        scoped = gv.evaluate(build(**overrides), "BC-007", {"BC-007-01"})
        self.assertEqual(scoped["verdict"], "PASS")

    def test_reasons_cite_specific_ids(self):
        payload = gv.evaluate(build(vulns=[
            {"id": "V-1", "classification": "Confirmed",
             "capability": "BC-007"}]), "BC-007", None)
        self.assertTrue(any("V-1" in r for r in payload["reasons"]))


if __name__ == "__main__":
    unittest.main()
