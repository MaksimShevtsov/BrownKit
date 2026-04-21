#!/usr/bin/env python3
"""Parse a coverage report into a uniform JSON shape for QS2.

Supports JaCoCo XML, Cobertura XML (including coverlet output), Istanbul
coverage-final.json, and Go `cover` text profiles. Auto-detects by filename
and root element; `--format` forces a specific parser.

Output schema:
{
  "schema_version": "1.0",
  "source": "jacoco|cobertura|istanbul|gocover",
  "confidence": "HIGH",
  "report_path": "...",
  "totals": { "line_rate": 0.0-1.0, "branch_rate": 0.0-1.0 | null },
  "packages": [
    {
      "name": "com.example.payments",
      "line_rate": ..., "branch_rate": ...|null,
      "files": [
        { "path": "...", "line_rate": ..., "branch_rate": ...|null,
          "lines_covered": int, "lines_total": int,
          "missed_line_ranges": ["12-18", "42"] }
      ]
    }
  ]
}
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def _detect_format(path: Path) -> str:
    name = path.name.lower()
    if name.endswith(".json"):
        return "istanbul"
    if name == "jacoco.xml" or "jacoco" in name:
        return "jacoco"
    if "cobertura" in name:
        return "cobertura"
    if name.endswith(".out") or name.startswith("cover"):
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as fh:
                first = fh.readline().strip()
            if first.startswith("mode:"):
                return "gocover"
        except OSError:
            pass
    if name.endswith(".xml"):
        try:
            root = ET.parse(path).getroot()
            tag = root.tag.lower()
            if "coverage" in tag and "jacoco" not in tag:
                return "cobertura"
            if tag.endswith("report") or "jacoco" in tag:
                return "jacoco"
        except ET.ParseError:
            pass
    raise ValueError(f"Cannot auto-detect coverage format for {path}")


def _safe_rate(num: float, denom: float) -> float | None:
    if denom <= 0:
        return None
    return round(num / denom, 4)


def _collapse_ranges(nums: list[int]) -> list[str]:
    if not nums:
        return []
    nums = sorted(set(nums))
    out: list[str] = []
    start = prev = nums[0]
    for n in nums[1:]:
        if n == prev + 1:
            prev = n
            continue
        out.append(f"{start}-{prev}" if prev != start else str(start))
        start = prev = n
    out.append(f"{start}-{prev}" if prev != start else str(start))
    return out


# -- JaCoCo -----------------------------------------------------------------

def _parse_jacoco(path: Path) -> dict:
    root = ET.parse(path).getroot()
    packages = []
    tot_line_covered = tot_line_total = 0
    tot_br_covered = tot_br_total = 0

    for pkg in root.findall("package"):
        pkg_files = []
        pkg_line_c = pkg_line_t = 0
        pkg_br_c = pkg_br_t = 0

        for sf in pkg.findall("sourcefile"):
            line_c = line_t = br_c = br_t = 0
            missed_lines: list[int] = []
            for ctr in sf.findall("counter"):
                kind = ctr.get("type")
                missed = int(ctr.get("missed", 0))
                covered = int(ctr.get("covered", 0))
                if kind == "LINE":
                    line_c += covered
                    line_t += covered + missed
                elif kind == "BRANCH":
                    br_c += covered
                    br_t += covered + missed
            for line in sf.findall("line"):
                if int(line.get("mi", 0)) > 0:
                    missed_lines.append(int(line.get("nr", 0)))
            path_attr = f"{pkg.get('name','')}/{sf.get('name','')}".lstrip("/")
            pkg_files.append({
                "path": path_attr,
                "line_rate": _safe_rate(line_c, line_t),
                "branch_rate": _safe_rate(br_c, br_t),
                "lines_covered": line_c,
                "lines_total": line_t,
                "missed_line_ranges": _collapse_ranges(missed_lines),
            })
            pkg_line_c += line_c; pkg_line_t += line_t
            pkg_br_c += br_c; pkg_br_t += br_t

        packages.append({
            "name": pkg.get("name", "").replace("/", "."),
            "line_rate": _safe_rate(pkg_line_c, pkg_line_t),
            "branch_rate": _safe_rate(pkg_br_c, pkg_br_t),
            "files": pkg_files,
        })
        tot_line_covered += pkg_line_c; tot_line_total += pkg_line_t
        tot_br_covered += pkg_br_c; tot_br_total += pkg_br_t

    return {
        "source": "jacoco",
        "totals": {
            "line_rate": _safe_rate(tot_line_covered, tot_line_total),
            "branch_rate": _safe_rate(tot_br_covered, tot_br_total),
        },
        "packages": packages,
    }


# -- Cobertura / coverlet ---------------------------------------------------

def _parse_cobertura(path: Path) -> dict:
    root = ET.parse(path).getroot()
    packages = []
    for pkg in root.iter("package"):
        pkg_files = []
        for cls in pkg.iter("class"):
            file_path = cls.get("filename", cls.get("name", ""))
            line_c = line_t = br_c = br_t = 0
            missed: list[int] = []
            for ln in cls.iter("line"):
                line_t += 1
                hits = int(ln.get("hits", 0))
                if hits > 0:
                    line_c += 1
                else:
                    try:
                        missed.append(int(ln.get("number", 0)))
                    except ValueError:
                        pass
                if ln.get("branch") == "true":
                    ccov = ln.get("condition-coverage", "")
                    m = re.match(r"(\d+)%\s*\((\d+)/(\d+)\)", ccov)
                    if m:
                        _, covered, total = map(int, m.groups())
                        br_c += covered; br_t += total
            pkg_files.append({
                "path": file_path,
                "line_rate": _safe_rate(line_c, line_t),
                "branch_rate": _safe_rate(br_c, br_t),
                "lines_covered": line_c,
                "lines_total": line_t,
                "missed_line_ranges": _collapse_ranges(missed),
            })
        pkg_line_c = sum(f["lines_covered"] for f in pkg_files)
        pkg_line_t = sum(f["lines_total"] for f in pkg_files)
        packages.append({
            "name": pkg.get("name", ""),
            "line_rate": _safe_rate(pkg_line_c, pkg_line_t),
            "branch_rate": None,
            "files": pkg_files,
        })
    tot_line_c = sum(f["lines_covered"] for p in packages for f in p["files"])
    tot_line_t = sum(f["lines_total"] for p in packages for f in p["files"])
    return {
        "source": "cobertura",
        "totals": {
            "line_rate": _safe_rate(tot_line_c, tot_line_t),
            "branch_rate": None,
        },
        "packages": packages,
    }


# -- Istanbul coverage-final.json ------------------------------------------

def _parse_istanbul(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    files = []
    tot_line_c = tot_line_t = tot_br_c = tot_br_t = 0
    for file_path, rec in data.items():
        stmt_map = rec.get("statementMap", {})
        s = rec.get("s", {})
        line_total = len(s)
        line_covered = sum(1 for v in s.values() if v > 0)
        missed: list[int] = []
        for sid, hits in s.items():
            if hits == 0 and sid in stmt_map:
                line = stmt_map[sid].get("start", {}).get("line")
                if line:
                    missed.append(line)
        branches = rec.get("b", {})
        br_total = sum(len(v) for v in branches.values())
        br_covered = sum(1 for v in branches.values() for b in v if b > 0)
        files.append({
            "path": file_path,
            "line_rate": _safe_rate(line_covered, line_total),
            "branch_rate": _safe_rate(br_covered, br_total),
            "lines_covered": line_covered,
            "lines_total": line_total,
            "missed_line_ranges": _collapse_ranges(missed),
        })
        tot_line_c += line_covered; tot_line_t += line_total
        tot_br_c += br_covered; tot_br_t += br_total
    # Package = directory
    pkgs: dict[str, list[dict]] = {}
    for f in files:
        pkg_name = str(Path(f["path"]).parent)
        pkgs.setdefault(pkg_name, []).append(f)
    packages = []
    for name, pkg_files in sorted(pkgs.items()):
        line_c = sum(f["lines_covered"] for f in pkg_files)
        line_t = sum(f["lines_total"] for f in pkg_files)
        packages.append({
            "name": name,
            "line_rate": _safe_rate(line_c, line_t),
            "branch_rate": None,
            "files": pkg_files,
        })
    return {
        "source": "istanbul",
        "totals": {
            "line_rate": _safe_rate(tot_line_c, tot_line_t),
            "branch_rate": _safe_rate(tot_br_c, tot_br_t),
        },
        "packages": packages,
    }


# -- Go cover profile -------------------------------------------------------

def _parse_gocover(path: Path) -> dict:
    files: dict[str, dict] = {}
    with path.open("r", encoding="utf-8") as fh:
        header = fh.readline()
        if not header.startswith("mode:"):
            raise ValueError("Not a Go cover profile (missing 'mode:' header)")
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            m = re.match(r"(.+?):(\d+)\.(\d+),(\d+)\.(\d+)\s+(\d+)\s+(\d+)", line)
            if not m:
                continue
            path_, ls, _, le, _, stmts, count = m.groups()
            stmts = int(stmts); count = int(count)
            rec = files.setdefault(path_, {"covered": 0, "total": 0, "missed_lines": []})
            rec["total"] += stmts
            if count > 0:
                rec["covered"] += stmts
            else:
                rec["missed_lines"].extend(range(int(ls), int(le) + 1))
    packages: dict[str, list[dict]] = {}
    for path_, rec in files.items():
        entry = {
            "path": path_,
            "line_rate": _safe_rate(rec["covered"], rec["total"]),
            "branch_rate": None,
            "lines_covered": rec["covered"],
            "lines_total": rec["total"],
            "missed_line_ranges": _collapse_ranges(rec["missed_lines"]),
        }
        pkg = str(Path(path_).parent)
        packages.setdefault(pkg, []).append(entry)
    out_packages = []
    for pkg, pkg_files in sorted(packages.items()):
        line_c = sum(f["lines_covered"] for f in pkg_files)
        line_t = sum(f["lines_total"] for f in pkg_files)
        out_packages.append({
            "name": pkg,
            "line_rate": _safe_rate(line_c, line_t),
            "branch_rate": None,
            "files": pkg_files,
        })
    tot_c = sum(r["covered"] for r in files.values())
    tot_t = sum(r["total"] for r in files.values())
    return {
        "source": "gocover",
        "totals": {"line_rate": _safe_rate(tot_c, tot_t), "branch_rate": None},
        "packages": out_packages,
    }


PARSERS = {
    "jacoco": _parse_jacoco,
    "cobertura": _parse_cobertura,
    "istanbul": _parse_istanbul,
    "gocover": _parse_gocover,
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--report", required=True, help="Path to the coverage report.")
    ap.add_argument("--format", choices=list(PARSERS) + ["auto"], default="auto")
    args = ap.parse_args(argv)

    report = Path(args.report)
    if not report.exists():
        print(json.dumps({
            "source": "not-collected",
            "confidence": "LOW",
            "reason": f"report not found: {report}",
        }, indent=2))
        return 2

    fmt = args.format if args.format != "auto" else _detect_format(report)
    result = PARSERS[fmt](report)
    result.update({
        "schema_version": "1.0",
        "report_path": str(report),
        "confidence": "HIGH",
    })
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
