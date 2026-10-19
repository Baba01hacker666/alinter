# Configuration

alinter is driven by a single declarative config document. It can be YAML,
TOML or JSON, or live under `[tool.alinter]` in `pyproject.toml`.

## Where config is looked up

Walking up from the working directory, alinter uses the first file it finds:

```
.alinter.yaml  .alinter.yml  alinter.yaml  alinter.yml
.alinter.toml  alinter.toml  .alinter.json  alinter.json
pyproject.toml            # only if it contains a [tool.alinter] table
```

A **global** user config is additionally merged *underneath* the project config:

```
$XDG_CONFIG_HOME/alinter/config.yaml     # default: ~/.config/alinter/config.yaml
```

Precedence, lowest to highest:

1. built-in defaults,
2. global user config,
3. project config (or an explicit `--config FILE`).

`--no-config` ignores everything except built-in defaults; `--no-user-config`
ignores just the global file.

## Merge rules

- Mappings are **deep-merged** (nested tables merge key by key).
- These keys have their **list values concatenated** instead of replaced:
  `rules`, `extends`, `presets`, `include`, `exclude`, `ignore`, `select`,
  `plugins`, `preset_paths`, `preset_dirs`.
- A rule defined twice with the same `id` — later definition wins.

## Top-level keys

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `version` | int | `1` | Config schema version. |
| `auto_detect` | bool | `true` | Apply language presets based on detected type. |
| `extends` | list | `[]` | Preset names to force on (alias: `presets`). |
| `include` | list | `[]` | Only lint files matching these globs. |
| `exclude` | list | `[]` | Skip files matching these globs. |
| `ignore` | list | `[]` | Turn rules off by id (fnmatch patterns allowed). |
| `select` | list | `[]` | If set, **only** these rule ids run. |
| `plugins` | list | `[]` | Import targets for custom check types. |
| `preset_paths` | list | `[]` | Extra dirs to load presets from (alias: `preset_dirs`). |
| `severity` | str | `error` | Default severity for rules that omit one. |
| `settings` | mapping | see below | Engine-wide settings. |
| `rules` | list | `[]` | Your rules and rule overrides. |

## `settings`

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `encoding` | str | `utf-8` | Preferred decoding; falls back to `utf-8`, `utf-16`, `latin-1`. |
| `max_file_size` | int | `5000000` | Skip files larger than this many bytes (`0` disables). |
| `use_gitignore` | bool | `true` | Honour `.gitignore` / `.git/info/exclude`. |
| `exclude_defaults` | bool | `true` | Apply the built-in exclude list. |
| `allow_commands` | bool | `false` | Gate the `command` check type. |
| `follow_symlinks` | bool | `false` | Reserved; symlinks are not followed. |

## Example (YAML)

```yaml
version: 1
auto_detect: true

extends: [python, yaml, dockerfile]
exclude:
  - "**/vendor/**"
  - "**/*.generated.py"
ignore:
  - "python/no-print"          # exact id
  - "generic/*"                # fnmatch pattern

settings:
  encoding: utf-8
  max_file_size: 2000000
  use_gitignore: true
  allow_commands: false

rules:
  - id: custom/no-todo
    type: regex
    pattern: '\b(TODO|FIXME)\b'
    mode: forbidden
    severity: info
    message: "unresolved {match} marker"
    files: ["**/*.py", "**/*.md"]

  # Tune a preset rule by id (no `type` = override):
  - id: python/max-line-length
    length: 88
```

## Example (TOML / pyproject.toml)

```toml
[tool.alinter]
version = 1
extends = ["python"]
exclude = ["**/vendor/**"]

[tool.alinter.settings]
allow_commands = false

[[tool.alinter.rules]]
id = "custom/no-debugger"
type = "literal"
value = "breakpoint()"
severity = "warning"
```

## Example (JSON)

```json
{
  "version": 1,
  "extends": ["python"],
  "rules": [
    { "id": "custom/no-todo", "type": "literal", "value": "TODO", "severity": "info" }
  ]
}
```

## Custom preset locations

Extra preset files are loaded from, in order:

1. directories listed in `preset_paths`,
2. directories in the `ALINTER_PRESET_PATH` environment variable
   (`os.pathsep`-separated),
3. `$XDG_CONFIG_HOME/alinter/presets/` (default `~/.config/alinter/presets/`).

See [presets.md](presets.md).

## Validating a config

```bash
alinter validate               # checks presets, rule types and overrides
alinter validate --config x.yaml
```

## Next

- [rules.md](rules.md) — how individual rules are written.
- [checks.md](checks.md) — the check types you can use.
