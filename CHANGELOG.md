# Changelog

All notable changes to BrownKit are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.1] - 2026-05-10

### Fixed
- Removed `extension.changelog` and `support` block from `extension.yml` — neither
  field is in the spec-kit extension schema, making the v1.0.0 manifest non-compliant
  with the Extension Development Guide.

## [1.0.0] - 2026-05-10

### Added
- Initial release of the EDCR brownfield pipeline as a spec-kit extension.
- All ten commands: init, scan, discover, report, assess, generate, finish, enrich, gate, validate.
- Methodology write-up and per-phase docs under `docs/`.
- Helper scripts under `scripts/` — Python core with bash + PowerShell shims:
  `detect-stack`, `list-manifests`, `parse-coverage`, `find-secrets`,
  `git-churn`, `validate-evidence`.
- Five lifecycle hooks: `before_specify`, `before_clarify`, `before_implement`,
  `after_implement`, `before_constitution`.
- `config_schema` for validation of `brownkit-config.yml`.
- `support` and `homepage` metadata for catalog discoverability.
