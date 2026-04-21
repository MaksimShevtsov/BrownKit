# Publishing BrownKit to the spec-kit Community Catalog

This guide walks through registering BrownKit in the official
[`github/spec-kit`](https://github.com/github/spec-kit) community catalog so
users can install it with `specify extension install brownkit`.

The steps follow the canonical
[`extensions/EXTENSION-PUBLISHING-GUIDE.md`](https://github.com/github/spec-kit/blob/main/extensions/EXTENSION-PUBLISHING-GUIDE.md)
in the spec-kit repo. Re-read that guide before opening a PR in case the
schema has changed since this document was written.

---

## 0. Pre-flight checklist

Before touching spec-kit, verify BrownKit itself is release-ready.

- [ ] `extension.yml` — `version` matches the tag you're about to cut
- [ ] `README.md` — install snippet points at the correct repo URL
- [ ] `CHANGELOG.md` — top entry describes the release
- [ ] `LICENSE` — present (MIT)
- [ ] Command names match `^speckit\.brownkit\.[a-z0-9-]+$`
- [ ] Every command file referenced from `extension.yml` exists
- [ ] Every `scripts.sh` / `scripts.ps` path referenced from command
      frontmatter exists and is executable (`chmod +x scripts/bash/*.sh`)
- [ ] Helpers produce valid JSON against `docs/schemas/*.schema.json`
- [ ] Example fixture under `docs/examples/sample-repo/` still exercises
      detect-stack, list-manifests, parse-coverage, find-secrets end-to-end

---

## 1. Cut the release tag

From the BrownKit working tree:

```bash
git add -A
git commit -m "release: v0.1.0"
git tag -a v0.1.0 -m "BrownKit v0.1.0 — initial release"
# Push when a remote is configured:
# git push origin main --tags
```

GitHub will surface the tag as a release once the repo has a remote. The
catalog entry pins to a commit SHA, so the tag is primarily for humans.

Record the commit SHA you want the catalog to pin to:

```bash
git rev-parse HEAD
```

---

## 2. Fork and clone spec-kit

```bash
gh repo fork github/spec-kit --clone --remote
cd spec-kit
git checkout -b add-brownkit-extension
```

---

## 3. Register in `catalog.community.json`

Edit `extensions/catalog.community.json`. Add a new entry, keeping the
array sorted alphabetically by `id`:

```json
{
  "id": "brownkit",
  "name": "BrownKit — Brownfield Discovery",
  "description": "Evidence-driven capability discovery, security and QA risk assessment for existing codebases.",
  "repository": "https://github.com/Kit-Kroker/BrownKit",
  "commit": "<full-sha-from-step-1>",
  "version": "0.1.0",
  "author": "Kit-Kroker",
  "license": "MIT",
  "tags": ["brownfield", "discovery", "security", "qa", "capabilities"]
}
```

Replace `<full-sha-from-step-1>` with the 40-char SHA. The catalog never
pins to a branch name or tag — always a commit.

---

## 4. Update the community README

Edit `extensions/README.md` (or whichever file holds the community
extensions table — verify the current path in the publishing guide). Add a
row, alphabetically by name:

```markdown
| [BrownKit](https://github.com/Kit-Kroker/BrownKit) | Evidence-driven capability discovery, security and QA risk assessment for existing codebases. | MIT |
```

---

## 5. Validate locally

spec-kit ships a catalog validator. From the spec-kit repo root:

```bash
# Whatever the guide prescribes — commonly:
npm install
npm run validate:catalog
# or: python -m speckit.tools.validate_catalog extensions/catalog.community.json
```

Fix any schema errors before opening the PR.

---

## 6. Open the PR

```bash
git add extensions/catalog.community.json extensions/README.md
git commit -m "Add BrownKit extension to community catalog"
git push -u origin add-brownkit-extension
gh pr create --title "Add BrownKit extension to community catalog" \
  --body "$(cat <<'EOF'
## Summary
Registers [BrownKit](https://github.com/Kit-Kroker/BrownKit) v0.1.0 in the
community extensions catalog. BrownKit packages an evidence-driven
brownfield discovery methodology (EDCR) as seven `speckit.brownkit.*`
commands.

## Commands provided
- speckit.brownkit.init
- speckit.brownkit.scan
- speckit.brownkit.discover
- speckit.brownkit.report
- speckit.brownkit.assess
- speckit.brownkit.generate
- speckit.brownkit.finish

## Validation
- [x] Catalog schema validator passes locally
- [x] All referenced command files exist at pinned SHA
- [x] Command names match `^speckit\.brownkit\.[a-z0-9-]+$`
- [x] MIT-licensed, repository public
EOF
)"
```

---

## 7. After merge

Once the spec-kit PR lands:

1. Announce the release (CHANGELOG link, a short post describing what
   problem BrownKit solves).
2. Monitor issues on the BrownKit repo for install/compat reports.
3. For future releases: bump `version` in `extension.yml` and
   `CHANGELOG.md`, cut a new tag, then open a follow-up PR against
   `catalog.community.json` updating only the `commit` and `version`
   fields.

---

## Reference URLs

- Publishing guide: https://github.com/github/spec-kit/blob/main/extensions/EXTENSION-PUBLISHING-GUIDE.md
- Catalog file: https://github.com/github/spec-kit/blob/main/extensions/catalog.community.json
- Community extensions index: https://github.com/github/spec-kit/tree/main/extensions
