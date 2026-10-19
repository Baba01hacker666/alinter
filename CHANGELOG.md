# Changelog

All notable changes to **alinter** are documented here.
This project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-10-19

### Added

- Initial release.
- Universal, config-driven lint engine with 13 built-in check types:
  `regex`, `literal`, `max-line-length`, `no-trailing-whitespace`, `no-tabs`,
  `final-newline`, `line-ending`, `max-lines`, `max-file-size`, `encoding`,
  `filename`, `structure`, and `command`.
- Bundled language/format presets with auto-detection by extension, filename,
  and shebang.
- Config file discovery (`.alinter.yaml`, `alinter.yaml`, `.alinter.json`,
  `.alinter.toml`, `pyproject.toml [tool.alinter]`, plus a user-level config).
- Inline suppression comments (`alinter: disable`, `disable-line`,
  `disable-next-line`, `disable-file`, `enable`).
- Auto-fix support (`--fix`, `--fix-dry-run`) for whitespace, newline,
  line-ending and regex/literal replacements.
- Reporters: `text`, `json`, `sarif`, `junit`, and `github`.
- Rule overrides: retune or disable any preset rule by id from your config.
- CLI commands: `check`, `init`, `presets`, `rules`, `explain`, `langs`,
  `validate`, `version` (plus `types`).
- Plugin system via `alinter.checks` entry points and `plugins:` config.
- pre-commit hook definition (`.pre-commit-hooks.yaml`).
