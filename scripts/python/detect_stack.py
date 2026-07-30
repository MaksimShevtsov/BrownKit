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
    r"org\.postgresql",
    r"mysql-connector", r"mariadb-java-client",
    r"spring-boot-starter-data-",
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
    r"<artifactId>(postgresql|mysql|mariadb|oracle|mongodb|h2|redis|cassandra)(?:-\w+)?</artifactId>",
    r"\"(pg|mysql2|sqlite3|mongodb|ioredis|cassandra-driver)\"\s*:",
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

# Command classification -----------------------------------------------------

TEST_TOKENS  = ("verify", "test", "pytest", "jest", "vitest", "check")
BUILD_TOKENS = ("package", "build", "compile", "assemble", "publish")
LINT_TOKENS  = ("lint", "ruff", "black", "flake8", "eslint", "checkstyle",
                "golangci", "format", "fmt")

# Files whose shell steps are the authoritative source for tool commands.
CI_FILE_NAMES = ("Jenkinsfile", ".gitlab-ci.yml", "azure-pipelines.yml",
                 "azure-pipelines.yaml", ".travis.yml")
CI_FILE_GLOBS = (".github/workflows/*.yml", ".github/workflows/*.yaml",
                 ".circleci/config.yml", ".buildkite/pipeline.yml")

# Shell invocations inside CI configs: `sh 'cmd'`, `run: cmd`, `- cmd`.
CI_STEP = re.compile(
    r"""(?:sh\s+['"](?P<sh>[^'"]+)['"]"""
    r"""|run:\s*(?P<run>[^\n#]+)"""
    r"""|^\s*-\s+(?P<bare>(?:mvn|gradle|\./gradlew|npm|yarn|pnpm|pytest|go|dotnet|make|ruff|eslint)\s[^\n#]+))""",
    re.MULTILINE,
)

# Maven/Gradle/npm defaults used only when nothing more specific is found.
MANIFEST_DEFAULTS = {
    "pom.xml":       {"test_runner": "mvn test", "build": "mvn -DskipTests package"},
    "build.gradle":  {"test_runner": "./gradlew test", "build": "./gradlew assemble"},
    "go.mod":        {"test_runner": "go test ./...", "build": "go build ./..."},
}

# Conventional source / test / migration layouts per ecosystem marker.
PATH_LAYOUTS = {
    "pom.xml": {"src": "src/main/java", "test": "src/test/java",
                "migrations": "src/main/resources/db/migration"},
    "go.mod":  {"src": ".", "test": ".", "migrations": "migrations"},
}
GENERIC_LAYOUTS = {
    "src":        ("src", "app", "lib"),
    "test":       ("tests", "test", "spec", "__tests__"),
    "migrations": ("migrations", "db/migrate", "alembic/versions", "prisma/migrations"),
}

BACKEND_DEPS = {
    "spring-boot": "spring-boot-starter", "quarkus": "quarkus",
    "express": "\"express\"", "fastify": "\"fastify\"", "nestjs": "@nestjs/core",
    "fastapi": "fastapi", "flask": "Flask", "django": "Django",
    "gin": "gin-gonic/gin", "echo": "labstack/echo", "chi": "go-chi/chi",
}
DATABASE_DEPS = {
    "postgres": ("postgresql", "psycopg2", "\"pg\"", "lib/pq"),
    "mysql":    ("mysql-connector", "mysql2", "mariadb"),
    "mongodb":  ("mongodb", "mongoose", "pymongo"),
    "sqlite":   ("sqlite3", "sqlite"),
}


def _walk(root: Path):
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


def _classify_command(cmd: str) -> str | None:
    """Bucket a shell command into a tool category, or None if unrecognised."""
    low = cmd.lower()
    for token in LINT_TOKENS:          # lint before test: "ruff check" is lint
        if token in low:
            return "lint"
    # build before test: a flag like "-DskipTests" would otherwise make the
    # substring "test" win over "package"/"build" in a build command.
    for token in BUILD_TOKENS:
        if token in low:
            return "build"
    for token in TEST_TOKENS:
        if token in low:
            return "test_runner"
    return None


def _ci_files(root: Path) -> list[Path]:
    found: list[Path] = []
    for name in CI_FILE_NAMES:
        candidate = root / name
        if candidate.is_file():
            found.append(candidate)
    for pattern in CI_FILE_GLOBS:
        found.extend(p for p in root.glob(pattern) if p.is_file())
    return found


def _ci_commands(root: Path) -> list[dict]:
    """Every shell command found in CI configs, with file:line provenance."""
    out: list[dict] = []
    for path in _ci_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel = str(path.relative_to(root)).replace("\\", "/")
        for match in CI_STEP.finditer(text):
            raw = match.group("sh") or match.group("run") or match.group("bare") or ""
            cmd = raw.strip()
            if not cmd:
                continue
            line = text[:match.start()].count("\n") + 1
            out.append({"command": cmd, "source": f"{rel}:{line}"})
    return out


def _tool_candidates(root: Path, manifests: list[dict]) -> dict:
    buckets: dict[str, list[dict]] = {"test_runner": [], "build": [], "lint": []}
    seen: set[tuple[str, str]] = set()

    def add(category: str, command: str, source: str, rank: str) -> None:
        key = (category, command)
        if key in seen:
            return
        seen.add(key)
        buckets[category].append({"command": command, "source": source, "rank": rank})

    # Rank 1 - CI config: what actually gates merges.
    for entry in _ci_commands(root):
        category = _classify_command(entry["command"])
        if category:
            add(category, entry["command"], entry["source"], "ci")

    # Rank 2 - explicit manifest scripts.
    for m in manifests:
        path = root / m["path"]
        if m["pattern"] == "package.json":
            try:
                scripts = json.loads(path.read_text(encoding="utf-8")).get("scripts", {})
            except (OSError, json.JSONDecodeError):
                continue
            for name, body in scripts.items():
                category = _classify_command(name) or _classify_command(str(body))
                if category:
                    add(category, f"npm run {name}", f"{m['path']} -> scripts.{name}",
                        "manifest-explicit")
        elif m["pattern"] == "pom.xml":
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if "maven-surefire-plugin" in text:
                add("test_runner", "mvn test", f"{m['path']} -> surefire",
                    "manifest-explicit")
        elif m["pattern"] in ("pyproject.toml", "setup.cfg"):
            try:
                lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
            except OSError:
                continue
            # Line-prefix scan, not a TOML parse: tomllib is 3.11+.
            for raw in lines:
                stripped = raw.strip()
                if stripped.startswith(("[tool.pytest", "[tool:pytest")):
                    add("test_runner", "pytest", f"{m['path']} -> {stripped}",
                        "manifest-explicit")
                elif stripped.startswith(("[tool.ruff", "[tool.black", "[flake8]")):
                    tool = stripped.strip("[]").split(".")[-1].split("]")[0]
                    add("lint", f"{tool} .", f"{m['path']} -> {stripped}",
                        "manifest-explicit")
        elif m["pattern"] in ("*.csproj", "*.sln", "*.fsproj"):
            add("test_runner", "dotnet test", m["path"], "manifest-explicit")
            add("build", "dotnet build", m["path"], "manifest-explicit")

    makefile = root / "Makefile"
    if makefile.is_file():
        try:
            for lineno, raw in enumerate(
                makefile.read_text(encoding="utf-8", errors="ignore").splitlines(), 1
            ):
                if ":" not in raw or raw.startswith(("\t", " ", "#", ".")):
                    continue
                target = raw.split(":", 1)[0].strip()
                category = _classify_command(target)
                if category:
                    add(category, f"make {target}", f"Makefile:{lineno}",
                        "manifest-explicit")
        except OSError:
            pass

    # Rank 3 - manifest presence defaults.
    for m in manifests:
        for marker, defaults in MANIFEST_DEFAULTS.items():
            if m["pattern"] == marker or m["path"].endswith(marker):
                for category, command in defaults.items():
                    add(category, command, f"{m['path']} (default)", "manifest-default")

    order = {"ci": 0, "manifest-explicit": 1, "manifest-default": 2}
    for category in buckets:
        buckets[category].sort(key=lambda c: order[c["rank"]])
    return buckets


def _path_candidates(root: Path, manifests: list[dict]) -> dict:
    out: dict[str, list[dict]] = {"src": [], "test": [], "migrations": []}
    seen: set[tuple[str, str]] = set()

    def add(kind: str, rel: str, source: str) -> None:
        if (kind, rel) in seen or not (root / rel).exists():
            return
        seen.add((kind, rel))
        out[kind].append({"path": rel, "source": source})

    for m in manifests:
        layout = PATH_LAYOUTS.get(m["pattern"])
        if layout:
            base = Path(m["path"]).parent
            for kind, rel in layout.items():
                joined = str(base / rel).replace("\\", "/").lstrip("./")
                add(kind, joined, f"{m['path']} (convention)")

    for kind, names in GENERIC_LAYOUTS.items():
        for name in names:
            add(kind, name, "directory scan")
    return out


def _stack_candidates(root: Path, manifests: list[dict],
                      frontend: dict, has_db: bool) -> dict:
    out: dict[str, list[dict]] = {
        "language": [], "backend": [], "frontend": [],
        "database": [], "package_manager": [],
    }
    seen: set[tuple[str, str]] = set()

    def add(kind: str, value: str, source: str) -> None:
        if (kind, value) in seen:
            return
        seen.add((kind, value))
        out[kind].append({"value": value, "source": source})

    for m in manifests:
        add("language", m["language"], m["path"])
        pm = {"pom.xml": "maven", "package.json": "npm", "go.mod": "go-modules",
              "Cargo.toml": "cargo", "composer.json": "composer",
              "Gemfile": "bundler"}.get(m["pattern"])
        if pm is None and m["pattern"].startswith("build.gradle"):
            pm = "gradle"
        if pm is None and m["pattern"] in ("pyproject.toml", "requirements.txt"):
            pm = "pip"
        if pm:
            add("package_manager", pm, m["path"])

    for name in frontend.get("frameworks", []):
        add("frontend", name, frontend.get("source_manifest") or "directory scan")

    for m in manifests:
        try:
            text = (root / m["path"]).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for name, needle in BACKEND_DEPS.items():
            if needle in text:
                add("backend", name, m["path"])
        for name, needles in DATABASE_DEPS.items():
            if any(n in text for n in needles):
                add("database", name, m["path"])

    if has_db and not out["database"]:
        add("database", "unknown", "DB dependency detected, vendor unresolved")
    return out


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

    candidates = {
        "tools": _tool_candidates(root, manifests),
        "paths": _path_candidates(root, manifests),
        "stack": _stack_candidates(root, manifests, frontend, has_db_dep),
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
        "candidates": candidates,
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
