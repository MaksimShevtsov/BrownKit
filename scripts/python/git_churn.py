#!/usr/bin/env python3
"""Compute per-file commit churn over a window for change-velocity scoring.

Runs `git log --name-only` over the last N months (default 6), counts
commits per path, computes the repo median, and tags each file as
`high | medium | low` relative to the median.

Output JSON on stdout:
{
  "schema_version": "1.0",
  "window_months": 6,
  "since": "2025-10-21",
  "total_commits": 412,
  "repo_median": 3,
  "files": [ { "path": "...", "commits": 17, "normalized": 5.67, "tier": "high" } ]
}

Exits non-zero if not inside a git repo.
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git failed")
    return result.stdout


def compute_churn(root: Path, months: int) -> dict:
    since = (datetime.now(timezone.utc) - timedelta(days=months * 30)).strftime("%Y-%m-%d")
    try:
        raw = _git(root, "log", f"--since={since}", "--name-only", "--pretty=format:__COMMIT__")
    except RuntimeError as e:
        msg = str(e).lower()
        if "does not have any commits" in msg or "unknown revision" in msg:
            return {
                "schema_version": "1.0",
                "window_months": months,
                "since": since,
                "total_commits": 0,
                "repo_median": 0,
                "files": [],
                "note": "no commits in window (or empty repo)",
            }
        raise
    counts: dict[str, int] = {}
    total_commits = 0
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if line == "__COMMIT__":
            total_commits += 1
            continue
        counts[line] = counts.get(line, 0) + 1

    values = list(counts.values())
    median = statistics.median(values) if values else 0
    files = []
    for path, n in counts.items():
        normalized = round(n / median, 3) if median else None
        if normalized is None:
            tier = "unknown"
        elif normalized > 2.0:
            tier = "high"
        elif normalized < 0.5:
            tier = "low"
        else:
            tier = "medium"
        files.append({"path": path, "commits": n, "normalized": normalized, "tier": tier})
    files.sort(key=lambda f: f["commits"], reverse=True)

    return {
        "schema_version": "1.0",
        "window_months": months,
        "since": since,
        "total_commits": total_commits,
        "repo_median": median,
        "files": files,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=".", help="Git repo root (default: current directory).")
    ap.add_argument("--months", type=int, default=6, help="Window in months (default: 6).")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    try:
        _git(root, "rev-parse", "--git-dir")
    except RuntimeError as e:
        print(json.dumps({"error": f"not a git repo at {root}: {e}"}), file=sys.stderr)
        return 2
    result = compute_churn(root, args.months)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
