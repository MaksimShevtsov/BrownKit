# Publishing BrownKit to the spec-kit Community Catalog

This guide walks through registering BrownKit in the official
[`github/spec-kit`](https://github.com/github/spec-kit) community catalog so
users can install it with `specify extension install brownkit`.

The steps follow the canonical
[`extensions/EXTENSION-PUBLISHING-GUIDE.md`](https://github.com/github/spec-kit/blob/main/extensions/EXTENSION-PUBLISHING-GUIDE.md)
in the spec-kit repo. Re-read that guide before submitting in case the
process has changed since this document was written.

---

## 0. Pre-flight checklist

Before submitting, verify BrownKit itself is release-ready.

- [ ] `extension.yml` — `version` matches the tag you're about to cut
- [ ] `README.md` — install snippet points at the correct repo URL
- [ ] `CHANGELOG.md` — top entry describes the release
- [ ] `LICENSE` — present (MIT)
- [ ] Command names match `^speckit\.brownkit\.[a-z0-9-]+$`
- [ ] Every command file referenced from `extension.yml` exists
- [ ] Every bash shim in `scripts/bash/` is executable (`chmod +x scripts/bash/*.sh`)
- [ ] `extension.yml` contains only fields documented in the Extension Development
      Guide — no `extension.changelog`, `support`, or other undocumented keys

---

## 1. Cut the release tag and GitHub release

From the BrownKit working tree:

```bash
git add extension.yml CHANGELOG.md
git commit -m "release: vX.Y.Z"
git tag -a vX.Y.Z -m "BrownKit vX.Y.Z"
git push origin main --tags
```

Then create the GitHub release so the archive URL is live:

```bash
gh release create vX.Y.Z \
  --title "vX.Y.Z" \
  --notes "See CHANGELOG.md for details."
```

The download URL that goes in the catalog entry is:

```
https://github.com/MaksimShevtsov/BrownKit/archive/refs/tags/vX.Y.Z.zip
```

Test that the URL resolves before submitting:

```bash
curl -sI https://github.com/MaksimShevtsov/BrownKit/archive/refs/tags/vX.Y.Z.zip \
  | grep -i location
```

---

## 2. Submit via the Extension Submission issue template

> [!IMPORTANT]
> Do **not** open a pull request directly against `extensions/catalog.community.json`.
> All submissions must go through the issue template.

Open the **[Extension Submission](https://github.com/github/spec-kit/issues/new?template=extension_submission.yml)**
template and fill in the fields below.

### Catalog entry values for BrownKit

| Field | Value |
|---|---|
| **id** | `brownkit` |
| **name** | `BrownKit — Brownfield Discovery for Spec-Kit` |
| **description** | `Evidence-driven capability discovery, security and QA risk assessment for existing codebases.` |
| **author** | `Maksim Shautsou` |
| **version** | *(current release, e.g. `1.0.1`)* |
| **download_url** | `https://github.com/MaksimShevtsov/BrownKit/archive/refs/tags/vX.Y.Z.zip` |
| **repository** | `https://github.com/MaksimShevtsov/BrownKit` |
| **homepage** | `https://github.com/MaksimShevtsov/BrownKit/blob/main/README.md` |
| **documentation** | `https://github.com/MaksimShevtsov/BrownKit/blob/main/README.md` |
| **changelog** | `https://github.com/MaksimShevtsov/BrownKit/blob/main/CHANGELOG.md` |
| **license** | `MIT` |
| **requires.speckit_version** | `>=0.1.0` |
| **provides.commands** | `10` |
| **provides.hooks** | `5` |
| **tags** | `brownfield`, `discovery`, `security`, `qa`, `capabilities` |

The full catalog entry JSON (for reference — maintainers write this):

```json
{
  "id": "brownkit",
  "name": "BrownKit — Brownfield Discovery for Spec-Kit",
  "description": "Evidence-driven capability discovery, security and QA risk assessment for existing codebases.",
  "author": "Maksim Shautsou",
  "version": "1.0.1",
  "download_url": "https://github.com/MaksimShevtsov/BrownKit/archive/refs/tags/v1.0.1.zip",
  "repository": "https://github.com/MaksimShevtsov/BrownKit",
  "homepage": "https://github.com/MaksimShevtsov/BrownKit/blob/main/README.md",
  "documentation": "https://github.com/MaksimShevtsov/BrownKit/blob/main/README.md",
  "changelog": "https://github.com/MaksimShevtsov/BrownKit/blob/main/CHANGELOG.md",
  "license": "MIT",
  "requires": {
    "speckit_version": ">=0.1.0"
  },
  "provides": {
    "commands": 10,
    "hooks": 5
  },
  "tags": ["brownfield", "discovery", "security", "qa", "capabilities"]
}
```

---

## 3. After approval

Once a maintainer approves and merges the catalog entry:

1. Announce the release (link the CHANGELOG entry, describe what problem BrownKit solves).
2. Monitor the BrownKit issue tracker for install or compatibility reports.

---

## 4. Releasing future versions

1. Bump `version` in `extension.yml`.
2. Add an entry to `CHANGELOG.md`.
3. Commit, tag, push, and create a GitHub release (Step 1 above).
4. File a new **[Extension Submission](https://github.com/github/spec-kit/issues/new?template=extension_submission.yml)**
   issue with the updated `version` and `download_url`. Mention in the issue
   body that this is an update to an existing entry.

---

## Reference URLs

- Publishing guide: https://github.com/github/spec-kit/blob/main/extensions/EXTENSION-PUBLISHING-GUIDE.md
- Extension Submission template: https://github.com/github/spec-kit/issues/new?template=extension_submission.yml
- Catalog file: https://github.com/github/spec-kit/blob/main/extensions/catalog.community.json
- Community extensions index: https://github.com/github/spec-kit/tree/main/extensions
