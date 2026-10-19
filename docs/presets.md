# Presets

A **preset** describes one language or file format: how to *detect* it and which
*rules* to apply. Presets are data (YAML/JSON), so adding language support never
requires code changes.

## What a preset looks like

```yaml
name: mylang                 # unique; used in extends/select/explain
language: mylang             # the language label rules are scoped to
description: "Checks for MyLang source files."
always_apply: false          # true = run for every file (baseline)
detect:
  extensions: [".ml", ".mylang"]
  filenames: ["MyBuildfile"]
  shebangs: ["mylang"]
rules:
  - id: mylang/no-goto
    type: literal
    value: "goto"
    mode: forbidden
    severity: warning
  - id: mylang/final-newline
    type: final-newline
    value: require
    severity: error
```

- `name` is required and unique. A later preset with the same name replaces an
  earlier one, which is how user presets override built-ins.
- `language` defaults to `name`.
- Rules are scoped to the preset's `language` automatically (unless the preset
  is `always_apply` or a rule sets its own `languages`).

## Detection

`DetectionIndex` picks a language per file by trying, in order:

1. **filename** — exact name, e.g. `Dockerfile`, `Makefile`, `Cargo.toml`
   (compared case-insensitively as well);
2. **extension** — lowercased, including the dot, e.g. `.py`, `.tf`;
3. **shebang** — the first line if it starts with `#!`. Tokens are taken from
   the basename of each word; `env` and options are skipped, and version
   suffixes are trimmed, so `#!/usr/bin/env python3.12` yields `python3.12`,
   `python3`, `python`.

The first preset that matches wins, so more specific presets should be listed
clearly named. Presets marked `always_apply` are excluded from the index and
always included for every file.

## `always_apply` and the baseline

The bundled `generic` preset is `always_apply: true` and provides the baseline
for every text file: trailing whitespace, final newline, LF line endings, no
BOM, and merge-conflict markers. Language presets layer on top of it.

## Bundled presets

Run `alinter presets` for the live list, or `alinter presets --show NAME` for
detail. Out of the box alinter understands:

c, cpp, csharp, css, dart, dockerfile, elixir, generic, go, haskell, html, ini,
java, javascript, json, kotlin, lua, makefile, markdown, perl, php, powershell,
python, r, ruby, rust, scss, shell, sql, svelte, swift, terraform, toml,
typescript, vue, xml, yaml.

## Adding a language

Drop a YAML file in any preset directory:

```yaml
# ~/.config/alinter/presets/mylang.yaml
name: mylang
language: mylang
detect:
  extensions: [".ml"]
rules:
  - id: mylang/no-goto
    type: literal
    value: "goto"
    mode: forbidden
    severity: warning
```

Preset search order:

1. `preset_paths:` in config,
2. directories in `ALINTER_PRESET_PATH` (`os.pathsep`-separated),
3. `$XDG_CONFIG_HOME/alinter/presets/` (default `~/.config/alinter/presets/`).

User presets are loaded after bundled ones, so reusing a bundled `name` replaces
it. Run `alinter presets --show mylang` to confirm it loaded, or
`alinter validate` to catch mistakes.

## Reusing a preset rule in your config

Force a preset on with `extends:`, then tune its rules by id:

```yaml
extends: [python]
rules:
  - id: python/max-line-length
    length: 88
```

## Sharing a preset

For a group, commit the preset to the repository and point config at it:

```yaml
preset_paths:
  - .alinter/presets
```

Because presets are plain files, they review and diff like any other source.

## Next

- [checks.md](checks.md) — the check types used inside presets.
- [plugins.md](plugins.md) — when a preset rule is not expressive enough.
