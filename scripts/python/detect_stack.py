#!/usr/bin/env python3
"""Read-only project-stack detection for `speckit.brownkit.init`.

Emits a single JSON document on stdout describing languages, package
manifests, build systems, CI platforms, frontend presence, a DB-dependency
hint, coverage-report candidates, and derived adaptation hints for
`workflow.json`.

No analysis. No writes.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Detection catalogs --------------------------------------------------------

MANIFESTS = {
    "java":       ["pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle"],
    "python":     ["pyproject.toml", "requirements.txt", "Pipfile", "setup.cfg", "setup.py"],
    "javascript": ["package.json"],
    "csharp":     ["*.csproj", "*.sln", "*.fsproj"],
    "go":         ["go.mod"],
    "rust":       ["Cargo.toml"],
    "php":        ["composer.json"],
    "ruby":       ["Gemfile"],
    "kotlin":     ["build.gradle.kts"],
    "scala":      ["build.sbt"],
    "swift":      ["Package.swift"],
}

EXT_TO_LANG = {
    ".java": "java", ".kt": "kotlin", ".scala": "scala",
    ".py": "python",
    ".ts": "typescript", ".tsx": "typescript",
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".cs": "csharp", ".fs": "fsharp",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
}

CI_FILES = {
    "github-actions": [".github/workflows"],
    "gitlab-ci":      [".gitlab-ci.yml"],
    "jenkins":        ["Jenkinsfile"],
    "azure-pipelines":["azure-pipelines.yml", "azure-pipelines.yaml"],
    "circleci":       [".circleci/config.yml"],
    "buildkite":      [".buildkite/pipeline.yml"],
    "travis":         [".travis.yml"],
}

FRONTEND_DEPS = {
    "react":   "react",
    "vue":     "vue",
    "angular": "@angular/core",
    "svelte":  "svelte",
    "next":    "next",
    "nuxt":    "nuxt",
    "solid":   "solid-js",
}

DB_DEP_PATTERNS = [
    r"\bjdbc:",
    r"org\.hibernate",
    r"EntityFramework",
    r"Microsoft\.EntityFrameworkCore",
    r"Dapper",
    r"typeorm",
    r"sequelize",
    r"prisma",
    r"mongoose",
    r"SQLAlchemy",
    r"psycopg2",
    r"pymongo",
    r"gorm\.io/gorm",
    r"go\.mongodb\.org",
    r"diesel",
    r"sqlx",
    r"ActiveRecord",
]

COVERAGE_CANDIDATES = [
    "target/site/jacoco/jacoco.xml",
    "build/reports/jacoco/test/jacocoTestReport.xml",
    "coverage/cobertura-coverage.xml",
    "coverage/coverage-final.json",
    "coverage/lcov.info",
    "TestResults/*/coverage.cobertura.xml",
    "coverage.xml",
    "coverage.cobertura.xml",
    "htmlcov/index.html",
]

IGNORED_DIRS = {
    ".git", "node_modules", "dist", "build", "target", "out",
    ".gradle", ".idea", ".vscode", "__pycache__", ".venv", "venv",
    ".mypy_cache", ".pytest_cache", "vendor", "bin", "obj",
}


def _walk(root: Path, max_depth: int = 6):
    root = root.resolve()
    for path in root.rglob("*"):
        if any(part in IGNORED_DIRS for part in path.relative_to(root).parts):
            continue
        yield path


def _glob_first(root: Path, pattern: str) -> Path | None:
    try:
        return next(root.glob(pattern))
    except StopIteration:
        return None


def _find_manifests(root: Path) -> list[dict]:
    seen: list[dict] = []
    for lang, patterns in MANIFESTS.items():
        for pat in patterns:
            for match in root.glob(f"**/{pat}"):
                if any(p in IGNORED_DIRS for p in match.relative_to(root).parts):
                    continue
                seen.append({
                    "language": lang,
                    "path": str(match.relative_to(root)),
                    "pattern": pat,
                })
    seen.sort(key=lambda m: (m["path"].count("/"), m["path"]))
    return seen


def _language_mix(root: Path, sample_cap: int = 5000) -> dict[str, int]:
    counts: dict[str, int] = {}
    seen = 0
    for path in _walk(root):
        if not path.is_file():
            continue
        lang = EXT_TO_LANG.get(path.suffix.lower())
        if not lang:
            continue
        counts[lang] = counts.get(lang, 0) + 1
        seen += 1
        if seen >= sample_cap:
            break
    return counts


def _detect_ci(root: Path) -> list[str]:
    detected = []
    for name, paths in CI_FILES.items():
        for rel in paths:
            candidate = root / rel
            if candidate.exists():
                detected.append(name)
                break
            # glob form for workflows/ dir
            if rel.endswith("/workflows") and (root / rel).is_dir():
                detected.append(name)
                break
    return sorted(set(detected))


def _detect_frontend(root: Path, manifests: list[dict]) -> dict:
    js_pkgs = [m for m in manifests if m["pattern"] == "package.json"]
    for pkg in js_pkgs:
        try:
            data = json.loads((root / pkg["path"]).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        frameworks = [name for name, dep in FRONTEND_DEPS.items() if dep in deps]
        if frameworks:
            return {
                "has_frontend": True,
                "frameworks": frameworks,
                "source_manifest": pkg["path"],
            }
    # heuristic fallback: top-level index.html + src/
    if (root / "index.html").exists() and (root / "src").is_dir():
        return {"has_frontend": True, "frameworks": ["unknown"], "source_manifest": None}
    return {"has_frontend": False, "frameworks": [], "source_manifest": None}


def _detect_db_dependency(root: Path, manifests: list[dict]) -> bool:
    patterns = [re.compile(p, re.IGNORECASE) for p in DB_DEP_PATTERNS]
    for m in manifests:
        try:
            text = (root / m["path"]).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pat in patterns:
            if pat.search(text):
                return True
    return False


def _coverage_candidates(root: Path) -> list[str]:
    hits: list[str] = []
    for pattern in COVERAGE_CANDIDATES:
        for match in root.glob(pattern):
            rel = str(match.relative_to(root))
            if rel not in hits:
                hits.append(rel)
    return hits


def _architecture_hint(root: Path, manifests: list[dict]) -> str:
    top_manifests = [m for m in manifests if m["path"].count("/") == 0]
    service_dirs = [d for d in ("services", "apps", "packages") if (root / d).is_dir()]
    if service_dirs and len(manifests) > 3:
        return "microservices-or-monorepo"
    if len(top_manifests) == 1 and not service_dirs:
        return "monolith"
    return "unknown"


def detect(root: Path) -> dict:
    manifests = _find_manifests(root)
    languages = _language_mix(root)
    ci = _detect_ci(root)
    frontend = _detect_frontend(root, manifests)
    has_db_dep = _detect_db_dependency(root, manifests)
    coverage = _coverage_candidates(root)
    arch = _architecture_hint(root, manifests)

    adaptations = {
        "db_schema_analysis": "auto" if has_db_dep else "skip",
        "frontend_analysis":  "auto" if frontend["has_frontend"] else "skip",
        "coverage_source":    "report" if coverage else "proxy",
    }

    return {
        "schema_version": "1.0",
        "root": str(root),
        "project": {
            "architecture_hint": arch,
            "primary_languages": sorted(languages, key=languages.get, reverse=True),
            "language_file_counts": languages,
            "package_manifests": manifests,
            "frameworks": frontend["frameworks"],
            "has_frontend": frontend["has_frontend"],
            "ci_platforms": ci,
            "coverage_report_candidates": coverage,
            "has_db_dependency": has_db_dep,
        },
        "adaptations": adaptations,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=".", help="Project root (default: current directory).")
    args = ap.parse_args(argv)
    result = detect(Path(args.root).resolve())
    json.dump(result, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
