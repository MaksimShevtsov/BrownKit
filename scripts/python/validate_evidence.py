#!/usr/bin/env python3
"""Mechanical portion of the `/finish` 14-point acceptance check.

Verifies what can be verified without LLM judgment: artifact presence, JSON
well-formedness, BC-NNN reference integrity, driver-count bounds, file
existence in handoff bundles. Items that require interpretation (e.g., "are
drivers specific and non-generic?") are reported as `needs-review`.

Exit codes:
  0  — all mechanical checks pass or `needs-review`.
  1  — any mechanical check fails AND `--strict` was set.
  2  — evidence directory missing or unreadable.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

BC_ID = re.compile(r"\bBC-\d{3}(?:-\d{2})?\b")


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return {"__error__": str(e)}


def check(evidence: Path) -> list[dict]:
    results: list[dict] = []

    def add(num: int, title: str, status: str, detail: str = "") -> None:
        results.append({"id": num, "title": title, "status": status, "detail": detail})

    # Criterion 1–2: security + QA context
    domain_model = evidence / "discovery/domain-model.md"
    qa_context = evidence / "qa/qa-context.json"
    if not domain_model.exists():
        add(1, "Security context per capability", "fail", "domain-model.md missing")
        add(2, "QA context per capability", "fail", "domain-model.md missing")
    else:
        text = domain_model.read_text(encoding="utf-8", errors="ignore")
        sec_blocks = text.count("Security Context")
        qa_blocks = text.count("QA Context")
        add(1, "Security context per capability",
            "needs-review" if sec_blocks else "fail",
            f"Security Context sections: {sec_blocks}")
        add(2, "QA context per capability",
            "pass" if qa_context.exists() else "fail",
            f"qa-context.json {'present' if qa_context.exists() else 'missing'}; "
            f"QA Context sections in domain-model: {qa_blocks}")

    # Criterion 3: STRIDE files
    threats_dir = evidence / "security/threats"
    threat_files = sorted(threats_dir.glob("BC-*.json")) if threats_dir.exists() else []
    add(3, "STRIDE threat model per capability",
        "pass" if threat_files else "fail",
        f"{len(threat_files)} threat file(s) in {threats_dir}")

    # Criterion 4: vulnerabilities mapped
    vuln_path = evidence / "security/vulnerabilities/catalog.json"
    if vuln_path.exists():
        data = _load_json(vuln_path)
        if "__error__" in data:
            add(4, "Vulnerabilities mapped to code and capability", "fail", data["__error__"])
        else:
            items = data if isinstance(data, list) else data.get("vulnerabilities", [])
            bad = [v for v in items
                   if not (v.get("location", {}).get("file") and v.get("capability"))]
            add(4, "Vulnerabilities mapped to code and capability",
                "pass" if not bad else "fail",
                f"{len(items)} total; {len(bad)} missing location or capability")
    else:
        add(4, "Vulnerabilities mapped to code and capability", "n/a",
            "catalog.json absent (run /assess)")

    # Criterion 5: security risk scores cover every L1
    risk = evidence / "security/risk-scores.json"
    l1 = evidence / "discovery/l1-capabilities.md"
    if risk.exists() and l1.exists():
        ids_in_l1 = set(BC_ID.findall(l1.read_text(encoding="utf-8")))
        l1_only = {x for x in ids_in_l1 if x.count("-") == 1}
        scored = set()
        data = _load_json(risk)
        if "__error__" not in data:
            entries = data if isinstance(data, list) else data.get("capabilities", [])
            for e in entries:
                if e.get("id"):
                    scored.add(e["id"])
        missing = l1_only - scored
        add(5, "Security risk scoring for all L1 capabilities",
            "pass" if not missing else "fail",
            f"missing: {sorted(missing)}" if missing else f"{len(scored)} scored")
    else:
        add(5, "Security risk scoring for all L1 capabilities", "n/a", "risk-scores.json or l1-capabilities.md absent")

    # Criterion 6: QA risk scoring (unknown allowed)
    qa_risk = evidence / "qa/qa-risk-scores.json"
    add(6, "QA risk scoring complete or explicitly unknown",
        "pass" if qa_risk.exists() else "n/a",
        "qa-risk-scores.json present" if qa_risk.exists() else "absent (run /assess)")

    # Criterion 7: unified composite drivers 1..3
    unified = evidence / "risk/unified-risk-map.json"
    if unified.exists():
        data = _load_json(unified)
        bad = []
        caps = data.get("capabilities", []) if isinstance(data, dict) else []
        for cap in caps:
            drivers = (cap.get("unified") or {}).get("drivers") \
                   or (cap.get("risk_score") or {}).get("drivers") \
                   or cap.get("drivers") or []
            if not (1 <= len(drivers) <= 3):
                bad.append((cap.get("id"), len(drivers)))
        add(7, "Unified composite has 1-3 drivers per capability",
            "pass" if not bad else "fail",
            f"out-of-range: {bad}" if bad else f"{len(caps)} capabilities validated")
    else:
        add(7, "Unified composite has 1-3 drivers per capability", "n/a", "unified-risk-map.json absent")

    # Criterion 8: requires human review (specificity of evidence)
    add(8, "Findings traceable with confidence levels", "needs-review",
        "sample-check that findings include file/line + confidence")

    # Criterion 9: cross-capability file
    xcap = evidence / "security/cross-capability-risks.json"
    add(9, "Cross-capability risks identified",
        "pass" if xcap.exists() else "n/a",
        "cross-capability-risks.json present" if xcap.exists() else "absent (run /assess)")

    # Criterion 10: file-to-capability coverage (extract %)
    coverage = evidence / "discovery/coverage.md"
    if coverage.exists():
        text = coverage.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"(\d{1,3}(?:\.\d+)?)\s*%", text)
        if m:
            pct = float(m.group(1))
            add(10, "File-to-capability coverage >= 90%",
                "pass" if pct >= 90 else "fail",
                f"reported: {pct}%")
        else:
            add(10, "File-to-capability coverage >= 90%", "needs-review",
                "coverage.md present but no percentage detected")
    else:
        add(10, "File-to-capability coverage >= 90%", "fail", "coverage.md missing")

    # Criterion 11: blueprint
    blueprint = evidence / "discovery/blueprint-comparison.md"
    add(11, "Industry blueprint comparison",
        "pass" if blueprint.exists() else "n/a",
        "blueprint-comparison.md present" if blueprint.exists() else "absent (skipped or not run)")

    # Criterion 12: domain model with code traceability
    if domain_model.exists():
        text = domain_model.read_text(encoding="utf-8", errors="ignore")
        bc_refs = len(set(BC_ID.findall(text)))
        add(12, "Domain model with code traceability",
            "pass" if bc_refs >= 1 else "fail",
            f"distinct BC refs: {bc_refs}")
    else:
        add(12, "Domain model with code traceability", "fail", "domain-model.md missing")

    # Criterion 13: reports + SDET Not-Collected Summary
    reports_dir = evidence / "reports"
    required = ["stakeholder-report.md", "architect-report.md", "dev-report.md", "sdet-report.md"]
    missing = [r for r in required if not (reports_dir / r).exists()]
    sdet = reports_dir / "sdet-report.md"
    has_not_collected = False
    if sdet.exists():
        has_not_collected = "Not-Collected Summary" in sdet.read_text(encoding="utf-8", errors="ignore")
    add(13, "All five reports emitted; SDET has Not-Collected Summary",
        "pass" if not missing and has_not_collected else "fail" if missing else "needs-review",
        f"missing reports: {missing}; SDET Not-Collected Summary: {has_not_collected}")

    # Criterion 14: cross-references (cheap check: every *Source: (path) exists)
    broken: list[str] = []
    for md in reports_dir.glob("*.md") if reports_dir.exists() else []:
        text = md.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", text):
            target = m.group(1)
            if target.startswith("http"):
                continue
            resolved = (md.parent / target).resolve()
            if not resolved.exists():
                broken.append(f"{md.name} -> {target}")
    add(14, "Evidence preserved with cross-references",
        "pass" if not broken else "fail",
        f"{len(broken)} broken link(s)" + (f": {broken[:5]}..." if broken else ""))

    return results


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--evidence-dir", default="evidence")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args(argv)

    evidence = Path(args.evidence_dir)
    if not evidence.exists():
        print(json.dumps({"error": f"evidence dir not found: {evidence}"}, indent=2))
        return 2

    results = check(evidence)
    summary = {
        "schema_version": "1.0",
        "evidence_dir": str(evidence),
        "total": len(results),
        "passed":       sum(1 for r in results if r["status"] == "pass"),
        "failed":       sum(1 for r in results if r["status"] == "fail"),
        "needs_review": sum(1 for r in results if r["status"] == "needs-review"),
        "not_applicable": sum(1 for r in results if r["status"] == "n/a"),
        "results": results,
    }
    json.dump(summary, sys.stdout, indent=2)
    sys.stdout.write("\n")

    if args.strict and summary["failed"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
