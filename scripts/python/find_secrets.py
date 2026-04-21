#!/usr/bin/env python3
"""Scan the repository for hard-coded credential patterns (SS1 support).

Regex-only. Reports file:line + pattern name + a redacted snippet. This is a
starting set — known false-positive-prone patterns like `password=...` are
included at LOW confidence and should be triaged in `/assess`.

Output JSON:
{
  "schema_version": "1.0",
  "root": "...",
  "scanned_files": N,
  "findings": [
    { "pattern": "aws-access-key", "confidence": "HIGH",
      "file": "src/...", "line": 42, "snippet": "AKIA...REDACTED..." }
  ]
}
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PATTERNS = [
    ("aws-access-key",        r"\bAKIA[0-9A-Z]{16}\b",                                   "HIGH"),
    ("aws-secret-key",        r"(?i)aws(.{0,20})?(secret|private)?.{0,20}?[=:]\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?", "MEDIUM"),
    ("github-pat-classic",    r"\bghp_[A-Za-z0-9]{36}\b",                                "HIGH"),
    ("github-pat-fine",       r"\bgithub_pat_[A-Za-z0-9_]{80,}\b",                       "HIGH"),
    ("github-oauth",          r"\bgho_[A-Za-z0-9]{36}\b",                                "HIGH"),
    ("github-server",         r"\bghs_[A-Za-z0-9]{36}\b",                                "HIGH"),
    ("github-refresh",        r"\bghr_[A-Za-z0-9]{36}\b",                                "HIGH"),
    ("slack-token",           r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b",                       "HIGH"),
    ("google-api-key",        r"\bAIza[0-9A-Za-z_\-]{35}\b",                             "HIGH"),
    ("stripe-live-key",       r"\bsk_live_[0-9a-zA-Z]{24,}\b",                           "HIGH"),
    ("stripe-pub-key",        r"\bpk_live_[0-9a-zA-Z]{24,}\b",                           "MEDIUM"),
    ("private-key-pem",       r"-----BEGIN (RSA|EC|OPENSSH|PGP|DSA)? ?PRIVATE KEY-----", "HIGH"),
    ("jdbc-inline-password",  r"jdbc:[^\"'\s]+password=[^\"'\s&]+",                      "MEDIUM"),
    ("generic-password-assign", r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"][^'\"]{6,}['\"]", "LOW"),
    ("generic-secret-assign",   r"(?i)(api[-_]?key|secret|token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]", "LOW"),
    ("basic-auth-url",        r"https?://[^/\s:]+:[^/\s@]+@",                            "HIGH"),
]

COMPILED = [(name, re.compile(pat), conf) for name, pat, conf in PATTERNS]

TEXT_EXTS = {
    ".java", ".kt", ".scala", ".groovy", ".py", ".ts", ".tsx", ".js", ".jsx",
    ".mjs", ".cjs", ".cs", ".fs", ".go", ".rs", ".rb", ".php", ".swift",
    ".yml", ".yaml", ".json", ".toml", ".ini", ".conf", ".config", ".env",
    ".properties", ".xml", ".sh", ".bash", ".ps1", ".tf", ".bicep", ".sql",
}

IGNORED_DIRS = {
    ".git", "node_modules", "dist", "build", "target", "out",
    ".gradle", ".idea", ".vscode", "__pycache__", ".venv", "venv",
    "vendor", "bin", "obj",
}

MAX_FILE_BYTES = 2 * 1024 * 1024


def _redact(snippet: str) -> str:
    # Hide the matched secret itself; keep enough context for triage.
    if len(snippet) > 200:
        snippet = snippet[:197] + "..."
    return re.sub(r"(?<=[A-Za-z0-9_])([A-Za-z0-9/_+=\-]{16,})", "<REDACTED>", snippet)


def _iter_files(root: Path):
    for path in root.rglob("*"):
        parts = path.relative_to(root).parts
        if any(p in IGNORED_DIRS for p in parts):
            continue
        if not path.is_file():
            continue
        if path.suffix.lower() not in TEXT_EXTS and path.name not in {".env", "Dockerfile"}:
            continue
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        yield path


def scan(root: Path) -> dict:
    root = root.resolve()
    findings = []
    scanned = 0
    for path in _iter_files(root):
        scanned += 1
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for name, pat, conf in COMPILED:
                if pat.search(line):
                    findings.append({
                        "pattern": name,
                        "confidence": conf,
                        "file": str(path.relative_to(root)),
                        "line": i,
                        "snippet": _redact(line.strip()),
                    })
    return {
        "schema_version": "1.0",
        "root": str(root),
        "scanned_files": scanned,
        "findings": findings,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=".", help="Project root (default: current directory).")
    args = ap.parse_args(argv)
    json.dump(scan(Path(args.root)), sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
