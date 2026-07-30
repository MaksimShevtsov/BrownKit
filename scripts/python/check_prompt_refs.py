#!/usr/bin/env python3
"""Verify that every `context.json -> path` reference in command prompts
resolves against the context schema.

Repo-maintenance tool, not a pipeline accelerator: no bash or PowerShell shim.

Exit codes:
  0  - every reference resolves.
  1  - at least one reference is unresolved.
  2  - commands directory or schema file missing.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Matches: `context.json -> a.b.c` with the unicode arrow, optional spaces.
REF = re.compile(r"`(context\.json)\s*→\s*([A-Za-z_][\w.]*)`")


def extract_refs(text: str) -> list[tuple[str, str]]:
    return [(m.group(1), m.group(2)) for m in REF.finditer(text)]


def _deref(schema: dict, node: dict) -> dict:
    """Follow a local $ref like '#/$defs/tool'. Non-local refs are left alone."""
    seen = 0
    while isinstance(node, dict) and isinstance(node.get("$ref"), str) and seen < 10:
        ref = node["$ref"]
        if not ref.startswith("#/"):
            return node
        target = schema
        for part in ref[2:].split("/"):
            if not isinstance(target, dict) or part not in target:
                return node
            target = target[part]
        node = target
        seen += 1
    return node


def resolve(schema: dict, dotted_path: str) -> bool:
    node = schema
    for segment in dotted_path.split("."):
        node = _deref(schema, node)
        props = node.get("properties")
        if not isinstance(props, dict) or segment not in props:
            return False
        node = props[segment]
    return True


def check(commands_dir: Path, schema_path: Path) -> list[dict]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    findings: list[dict] = []
    for md in sorted(commands_dir.glob("*.md")):
        for lineno, line in enumerate(md.read_text(encoding="utf-8").splitlines(), 1):
            for _doc, dotted in extract_refs(line):
                if not resolve(schema, dotted):
                    findings.append({
                        "file": str(md).replace("\\", "/"),
                        "line": lineno,
                        "path": dotted,
                    })
    return findings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--commands", default="commands")
    ap.add_argument("--schema", default="docs/schemas/context.schema.json")
    args = ap.parse_args(argv)

    commands_dir = Path(args.commands)
    schema_path = Path(args.schema)
    if not commands_dir.is_dir() or not schema_path.is_file():
        print(json.dumps({"error": "commands dir or schema file not found"}, indent=2))
        return 2

    findings = check(commands_dir, schema_path)
    json.dump({"unresolved": len(findings), "findings": findings}, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
