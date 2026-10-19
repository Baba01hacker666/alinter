# Check types

A rule's `type` selects a **check** — the code that inspects a file. alinter
ships 13 check types; `alinter types` prints the live list and
`alinter explain RULE_ID` shows one rule's parameters.

Anything in a rule that is not a [reserved key](rules.md#reserved-keys-vs-parameters)
is passed to the check as a parameter.

## Quick reference

| Type | Fixable | Signature parameters |
| --- | --- | --- |
| [`regex`](#regex) | yes | `pattern`, `mode`, `flags`, `whole_word`, `per_line`, `ignore_fences`, `fix`, `min`/`max` |
| [`literal`](#literal) | yes | `value`, `mode`, `case_sensitive`, `whole_word`, `ignore_fences`, `fix`, `min`/`max` |
| [`max-line-length`](#max-line-length) | no | `length`, `ignore_urls`, `ignore_regex`, `tab_width` |
| [`no-trailing-whitespace`](#no-trailing-whitespace) | yes | — |
| [`no-tabs`](#no-tabs) | no | `mode` (`any`/`leading`) |
| [`final-newline`](#final-newline) | yes | `value` (`require`/`forbid`), `exactly` |
| [`line-ending`](#line-ending) | yes | `style` (`lf`/`crlf`) |
| [`max-lines`](#max-lines) | no | `max`, `count_blank`, `max_blank_lines` |
| [`max-file-size`](#max-file-size) | no | `max` (bytes) |
| [`encoding`](#encoding) | no | `expect`, `forbid_bom` |
| [`filename`](#filename) | no | `pattern`, `extension`, `mode` |
| [`structure`](#structure) | no | `format`, `require_keys`, `forbid_keys`, `path_exists`, `path_absent` |
| [`command`](#command) | no | `command`, `expect_exit`, `shell`, `timeout` |

Checks marked **singleton** (below) describe a whole-file property; when several
rules of that type match a file, only the most specific one runs. See
[how-it-works.md](how-it-works.md#stage-4--rule-selection).

### Aliases

For convenience several friendly names map to the same check:
`pattern`, `forbidden-pattern`, `required-pattern` → `regex`;
`contains`, `substring`, `forbidden-text`, `required-text` → `literal`;
`line-length`, `max-line` → `max-line-length`;
`trailing-whitespace` → `no-trailing-whitespace`; `tabs` → `no-tabs`;
`eof-newline`, `final-newline-check` → `final-newline`;
`file-size` → `max-file-size`; `file-name` → `filename`.

## Pattern checks

The `regex` and `literal` checks share one engine. They search a file and act
according to `mode`:

- **`forbidden`** (default) — report every match.
- **`required`** — report once if there are no matches.
- **`count`** — report once if the match count is outside `min`/`max`.

By default patterns are compiled with `re.MULTILINE`, so `^`/`$` mean line
start/end. Pass an explicit `flags: []` to opt out.

### regex

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `pattern` | str | — (required) | The regular expression. |
| `mode` | str | `forbidden` | `forbidden`, `required`, `count`. |
| `flags` | list | `[MULTILINE]` | Any of `IGNORECASE`, `MULTILINE`, `DOTALL`, `VERBOSE`, `ASCII`, `UNICODE`. |
| `whole_word` | bool | `false` | Wrap the pattern in `\b(?:…)\b`. |
| `per_line` | bool | `false` | Report at most one match per line. |
| `ignore_fences` | bool | `false` | Ignore matches inside fenced code blocks (Markdown-aware). |
| `fix` | str | — | Replacement template (`\1`, `\g<name>` work). |
| `min` / `max` | int | — | Bounds for `count` mode. |

Violation placeholders: `{match}`, `{count}` and any parameter.

```yaml
- id: python/no-print
  type: regex
  pattern: '^\s*print\s*\('
  mode: forbidden
  severity: warning
  message: "print() call"
```

### literal

Like `regex` but the `value` is matched literally (`re.escape`d).

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `value` | str | — (required) | The substring to search for. |
| `mode` | str | `forbidden` | `forbidden`, `required`, `count`. |
| `case_sensitive` | bool | `true` | Case-sensitive matching. |
| `whole_word` | bool | `false` | Require word boundaries. |
| `ignore_fences` | bool | `false` | Ignore fenced code blocks. |
| `fix` | str | — | Replacement text. |
| `min` / `max` | int | — | Bounds for `count` mode. |

```yaml
- id: generic/no-wip
  type: literal
  value: "WIP"
  mode: forbidden
  severity: info
```

## Line and whitespace checks

### max-line-length

Checks `length` must be a positive integer. Not a singleton.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `length` | int | — (required) | Maximum line length. |
| `ignore_urls` | bool | `false` | Skip lines containing a URL. |
| `ignore_regex` | str | — | Skip lines matching this regex (e.g. `^\s*\|` for tables). |
| `tab_width` | int | — | Expand tabs to this width before measuring. |

Placeholders: `{length}` (actual), `{limit}`, `{line}`.

### no-trailing-whitespace

Singleton, fixable. Reports (and can strip) spaces/tabs at end of line. No
parameters.

### no-tabs

Singleton. Not fixable.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `mode` | str | `any` | `any` (tab anywhere) or `leading` (indentation only). |

### final-newline

Singleton, fixable.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `value` | str | `require` | `require` or `forbid`. |
| `exactly` | bool | `false` | With `require`, allow exactly one trailing newline. |

### line-ending

Singleton, fixable.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `style` | str | `lf` | `lf` (unix) or `crlf` (windows). |

## File-level checks

### max-lines

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `max` | int | — (required) | Maximum number of lines. |
| `count_blank` | bool | `true` | Count blank lines toward the total. |
| `max_blank_lines` | int | — | Also limit consecutive blank lines. |

### max-file-size

Singleton.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `max` | int | — (required) | Maximum size in bytes. |

### encoding

Singleton.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `expect` | str | `utf-8` | Required encoding (aliases normalised). |
| `forbid_bom` | bool | `false` | Flag a leading byte-order mark. |

### filename

Singleton.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `pattern` | str | — | Regex matched against the base name. |
| `extension` | str/list | — | Allowed extension(s). |
| `mode` | str | `forbidden` | `forbidden` (fail if found) or `required` (fail if not). |

At least one of `pattern` / `extension` is required.

## Data checks

### structure

Validates that a file parses, then optionally asserts on keys/paths.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `format` | str | — (required) | `json`, `yaml`/`yml`, `toml`, `ini` or `xml`. |
| `require_keys` | list | `[]` | Top-level keys that must exist (mapping root). |
| `forbid_keys` | list | `[]` | Top-level keys that must not exist. |
| `path_exists` | list | `[]` | Dotted paths that must exist (`a.b.0.c`). |
| `path_absent` | list | `[]` | Dotted paths that must not exist. |

XML parsing prefers [`defusedxml`](../README.md#install) when installed
(`pip install "alinter[xml]"`) and only falls back to the standard library for
the user's own project files.

```yaml
- id: package/require-version
  type: structure
  format: json
  require_keys: [name, version]
  path_exists: [scripts.test]
  files: ["package.json"]
```

## Command checks

### command

Runs an external command once per file and fails on an unexpected exit code.
This is powerful, so it is **opt-in**: enable it with `--allow-commands` or
`settings.allow_commands: true`.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `command` | str | — (required) | Command template. |
| `expect_exit` | int | `0` | Acceptable exit code. |
| `shell` | bool | `true` | Run through the shell (enables pipes/redirection). |
| `timeout` | float | `30` | Seconds before the command is killed. |

The template can reference `{path}`, `{rel_path}`, `{filename}`,
`{extension}` and `{language}`:

```yaml
rules:
  - id: python/compile
    type: command
    command: "python -m py_compile {path}"
    severity: error
```

## Next

- [presets.md](presets.md) — bundle rules into a language.
- [plugins.md](plugins.md) — add your own check type.
