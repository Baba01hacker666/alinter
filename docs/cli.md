# CLI reference

```
alinter [check] [PATHS...]   lint files (the default command)
alinter init                 write a starter .alinter.yaml
alinter presets              list presets (--show NAME, --json)
alinter rules                list the rules that apply to files
alinter explain RULE_ID      explain one rule
alinter langs                show detected languages per file
alinter validate             validate config and rules
alinter types                list built-in check types
alinter version              print the version
```

The first argument is treated as a command; if it is not one, `check` is
assumed, so `alinter src/` and `alinter check src/` are equivalent.
`check` also answers to `lint` and `run`.

## check

Lint files and report violations.

| Flag | Meaning |
| --- | --- |
| `-c, --config FILE` | Use this config instead of discovering one. |
| `-f, --format NAME` | `text` (default), `json`, `sarif`, `junit`/`xml`, `github`/`gha`. |
| `--fix` | Apply available fixes in place. |
| `--fix-dry-run`, `--diff` | Show what would be fixed without writing. |
| `--select RULE` | Only run matching rule ids (fnmatch); repeatable. |
| `--ignore RULE` | Skip matching rule ids (fnmatch); repeatable. |
| `--include GLOB` | Only lint files matching this glob; repeatable. |
| `--exclude GLOB` | Skip files matching this glob; repeatable. |
| `--preset NAME` | Force a preset on; repeatable. |
| `--severity LEVEL` | Minimum severity to *report*: `info` (default), `warning`, `error`. |
| `--fail-on LEVEL` | Exit non-zero at this severity or worse: `info`, `warning`, `error` (default), `none`. |
| `--strict` | Shorthand for `--fail-on warning`. |
| `--stdin` | Read one file from standard input. |
| `--stdin-filename NAME` | Name to assume for `--stdin` (drives detection). |
| `--allow-commands` | Permit `command` checks to run external programs. |
| `--no-gitignore` | Do not honour `.gitignore`. |
| `--jobs N`, `-j N` | Accepted but reserved; currently ignored. |
| `--color` / `--no-color` | Force or disable ANSI color. |
| `-q, --quiet` | Print only the summary. |
| `-v, --verbose` | Increase verbosity (repeatable). |
| `--no-config` | Ignore all config files. |
| `--no-user-config` | Ignore only the global user config. |

Examples:

```bash
alinter                          # lint the current directory (discovered config)
alinter check src tests          # lint specific paths
alinter --fix                    # fix what can be fixed
alinter --diff                   # show what --fix would change
alinter --format sarif > out.sarif
alinter --strict                 # fail on warnings too
alinter --fail-on none           # always exit 0 (report only)
alinter --select 'python/*'      # only python preset rules
alinter --ignore 'generic/*'
echo 'print(1)' | alinter --stdin --stdin-filename x.py
```

## init

Write a starter `.alinter.yaml` into a directory.

```bash
alinter init                 # into the current directory
alinter init myproject       # into myproject/
alinter init --preset python --preset yaml
alinter init --force         # overwrite an existing file
```

## presets

List bundled and user presets; `--show NAME` prints one in detail and
`--json` emits machine-readable data.

```bash
alinter presets
alinter presets --show python
alinter presets --json
```

## rules

List the rules that apply to the given paths (after detection, scoping and
overrides). `--all` includes disabled rules; `--json` emits structured data.

```bash
alinter rules src/
alinter rules --all
alinter rules --json
```

## explain

Describe a single rule by id — its type, severity, scope, parameters and the
check's help text. Works for preset and user rules.

```bash
alinter explain python/no-print
alinter explain generic/final-newline
```

## langs

Show which language each file is detected as — handy when a preset is not
firing. `--json` emits a mapping of language to files.

```bash
alinter langs
alinter langs src/ --json
```

## validate

Check the config: that preset names exist, rule `type`s are registered, and
overrides point at real rules. Exits `1` and lists problems when invalid,
`0` otherwise.

```bash
alinter validate
alinter validate --config ci.yaml
```

## types

List the built-in check types, whether each is fixable, and a one-line
description.

```bash
alinter types
```

## version

```bash
alinter version      # -> alinter 0.1.0
alinter --version
```

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Clean, or nothing at/above the `--fail-on` threshold. |
| `1` | Violations at or above the threshold. |
| `2` | Configuration error (bad file, unknown preset, bad rule). |
| `130` | Interrupted (Ctrl-C). |

## Environment

| Variable | Effect |
| --- | --- |
| `ALINTER_PRESET_PATH` | Extra preset directories (`os.pathsep`-separated). |
| `XDG_CONFIG_HOME` | Base for the user config and preset directory. |
| `NO_COLOR` / `FORCE_COLOR` | Disable / enable color regardless of TTY. |

## Next

- [reporters.md](reporters.md) — output formats in detail.
- [configuration.md](configuration.md) — the config these commands read.
