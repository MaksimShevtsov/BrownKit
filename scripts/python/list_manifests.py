#!/usr/bin/env python3
"""List package-manifest files for SS2 dependency-vulnerability analysis.

Emits JSON on stdout: { manifests: [{ language, path, size_bytes, sha1 }] }.
Uses the same detection catalog as detect_stack.py; duplicates logic in
isolation so this script can be invoked standalone without importing
detect_stack.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

MANIFESTS = [
    ("java",       "pom.xml"),
    ("java",       "build.gradle"),
    ("java",       "build.gradle.kts"),
    ("python",     "pyproject.toml"),
    ("python",     "requirements.txt"),
    ("python",     "requirements-*.txt"),
    ("python",     "Pipfile.lock"),
    ("python",     "poetry.lock"),
    ("javascript", "package.json"),
    ("javascript", "package-lock.json"),
    ("javascript", "yarn.lock"),
    ("javascript", "pnpm-lock.yaml"),
    ("csharp",     "*.csproj"),
    ("csharp",     "packages.lock.json"),
    ("go",         "go.mod"),
    ("go",         "go.sum"),
    ("rust",       "Cargo.toml"),
    ("rust",       "Cargo.lock"),
    ("php",        "composer.json"),
    ("php",        "composer.lock"),
    ("ruby",       "Gemfile"),
    ("ruby",       "Gemfile.lock"),
]

IGNORED_DIRS = {
    ".git", "node_modules", "dist", "build", "target", "out",
    ".gradle", ".idea", ".vscode", "__pycache__", ".venv", "venv",
    "vendor", "bin", "obj",
}


def _sha1(path: Path, max_bytes: int = 4 * 1024 * 1024) -> str:
    h = hashlib.sha1()
    try:
        with path.open("rb") as fh:
            read = 0
            while chunk := fh.read(65536):
                h.update(chunk)
                read += len(chunk)
                if read >= max_bytes:
                    break
    except OSError:
        return ""
    return h.hexdigest()


def list_manifests(root: Path) -> list[dict]:
    root = root.resolve()
    found: list[dict] = []
    seen: set[str] = set()
    for lang, pattern in MANIFESTS:
        for match in root.glob(f"**/{pattern}"):
            rel_parts = match.relative_to(root).parts
            if any(p in IGNORED_DIRS for p in rel_parts):
                continue
            rel = str(match.relative_to(root))
            if rel in seen:
                continue
            seen.add(rel)
            try:
                size = match.stat().st_size
            except OSError:
                size = 0
            found.append({
                "language": lang,
                "path": rel,
                "size_bytes": size,
                "sha1": _sha1(match),
            })
    found.sort(key=lambda m: (m["path"].count("/"), m["path"]))
    return found


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=".", help="Project root (default: current directory).")
    args = ap.parse_args(argv)
    out = {"schema_version": "1.0", "root": str(Path(args.root).resolve()),
           "manifests": list_manifests(Path(args.root))}
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
