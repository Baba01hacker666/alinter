# alinter

**A universal, config-driven linter.** alinter does not care what language you
write in — it lints *files*, driven by declarative rules. Point it at your
project and it applies sensible defaults for the languages it recognises;
write a few lines of YAML and it will catch whatever else you care about.

- 🧩 **Language agnostic** — rules are data, not code.
- 📦 **Presets, not rebuilds** — add a language by dropping in a YAML file.
- ✍️ **Your rules, anywhere** — one-off checks for obscure formats are trivial.
- 🔧 **Auto-fix** — whitespace, newline, line-ending and pattern fixes.
- 🚫 **Inline suppression** — `# alinter: disable-next-line=rule`.
- 📊 **Many outputs** — `text`, `json`, `sarif`, `junit`, `github`.
- 🪝 **Plugin system** — contribute custom check types via entry points.

## Install

```bash
pip install alinter
```

alinter needs Python 3.9+ and depends only on PyYAML (plus `tomli` on older
Pythons). Install the optional `xml` extra to harden XML parsing with
[`defusedxml`](https://pypi.org/project/defusedxml/):

```bash
pip install "alinter[xml]"
```

Install the `gitignore` extra for `.gitignore`-aware discovery:

```bash
pip install "alinter[gitignore]"
```

### As a pre-commit hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/Baba01hacker666/alinter
    rev: v0.1.0
    hooks:
      - id: alinter
```

## Quick start

```bash
# Lint the current directory using discovered config + built-in presets
alinter

# Lint specific paths
alinter check src/ tests/ main.py

# Create a starter config
alinter init

# Fix what can be fixed automatically
alinter --fix

# Machine-readable output
alinter --format json
alinter --format sarif > alinter.sarif
```

## How it works

1. **Discover** files under the given paths (respecting `.gitignore` and your
   `exclude` globs).
2. **Detect** each file's language from its extension, name or shebang.
3. **Select** the rules that apply: always-on baseline rules, matching language
   presets, and your own rules.
4. **Run** each rule's check and collect violations.
5. **Report** (and optionally **fix**) the results.

See [`docs/how-it-works.md`](docs/how-it-works.md) for the full pipeline.

## Documentation

The full manual lives in [`docs/`](docs/README.md):

| Document | What it covers |
| --- | --- |
| [how-it-works.md](docs/how-it-works.md) | The linting pipeline and module layout |
| [configuration.md](docs/configuration.md) | Every config key, discovery and merge rules |
| [rules.md](docs/rules.md) | Anatomy of a rule, scopes, severities, overrides |
| [checks.md](docs/checks.md) | Every built-in check type and its parameters |
| [presets.md](docs/presets.md) | Detection and adding a language |
| [suppressions.md](docs/suppressions.md) | Inline `alinter:` comments |
| [plugins.md](docs/plugins.md) | Shipping custom check types |
| [reporters.md](docs/reporters.md) | Output formats |
| [cli.md](docs/cli.md) | Every command and flag |
| [python-api.md](docs/python-api.md) | Using alinter from Python |
| [development.md](docs/development.md) | Setup, quality gates, CI, releasing |
| [faq.md](docs/faq.md) | Common questions and troubleshooting |

Contributors (and AI agents) should also read [`AGENTS.md`](AGENTS.md),
[`CONTRIBUTING.md`](CONTRIBUTING.md), [`SECURITY.md`](SECURITY.md) and the
[`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

## Configuration

alinter looks for a config file named `.alinter.yaml`, `alinter.yaml`,
`.alinter.toml`, `.alinter.json`, or a `[tool.alinter]` section in
`pyproject.toml`, walking up from the working directory. A global config at
`~/.config/alinter/config.yaml` is merged underneath.

```yaml
version: 1
auto_detect: true          # apply presets based on file type

extends: [python, yaml]    # force extra presets on
exclude: ["**/vendor/**"]  # skip these files
ignore: ["generic/line-ending"]  # turn rules off by id (globs ok)
select: []                 # if set, ONLY these rules run

settings:
  encoding: utf-8
  max_file_size: 5000000
  use_gitignore: true
  allow_commands: false    # gate the `command` check type

rules:
  - id: custom/no-todo
    type: regex
    pattern: '\b(TODO|FIXME)\b'
    mode: forbidden
    severity: info
    message: "unresolved {match} marker"
    files: ["**/*"]
```

Everything in a rule that is not a reserved key (`id`, `type`, `severity`,
`message`, `files`, `exclude`, `languages`, `tags`, `enabled`, `description`)
becomes a parameter for the check `type`.

### Overriding preset rules

A rule entry **without** a `type` overrides an existing rule by id, so you can
retune a preset without restating it:

```yaml
rules:
  - id: python/no-print        # tune a bundled rule
    severity: warning
  - id: python/max-line-length # change just the parameter
    length: 88
  - id: generic/line-ending    # turn one off (quote "off" in YAML!)
    severity: "off"
```

Overriding an id that does not exist is reported as an error by
`alinter validate`.

## Built-in check types

Run `alinter types` for the live list.

| type | what it does | key parameters |
| --- | --- | --- |
| `regex` | search for a regular expression | `pattern`, `mode`, `flags`, `fix`, `per_line`, `min`/`max` |
| `literal` | search for a literal substring | `value`, `mode`, `case_sensitive`, `fix` |
| `max-line-length` | limit line length | `length`, `ignore_urls`, `ignore_regex` |
| `no-trailing-whitespace` | flag/strip trailing spaces | — |
| `no-tabs` | flag tab characters | `mode` (`any`/`leading`) |
| `final-newline` | require/forbid a final newline | `value`, `exactly` |
| `line-ending` | enforce LF or CRLF | `style` |
| `max-lines` | limit file length | `max`, `count_blank`, `max_blank_lines` |
| `max-file-size` | limit size in bytes | `max` |
| `encoding` | require an encoding / no BOM | `expect`, `forbid_bom` |
| `filename` | match the base file name | `pattern`, `mode`, `extension` |
| `structure` | validate JSON/YAML/TOML/INI/XML | `format`, `require_keys`, `path_exists`, … |
| `command` | run an external command per file | `command`, `expect_exit` |

`mode` is `forbidden` (default), `required`, or `count` (with `min`/`max`).
`regex`/`literal` also accept `whole_word`, `per_line` and `ignore_fences`
(skip matches inside fenced code blocks).

### Message templates

`message` may reference `{rule}`, `{path}`, `{line}`, `{column}`, `{match}`,
`{count}`, `{limit}`, `{value}` and any of the rule's parameters, e.g.
`"line too long ({length} > {limit})"`.

## Presets

Run `alinter presets` to list them, `alinter presets --show python` for detail.
Bundled presets cover: c, cpp, csharp, css, dart, dockerfile, elixir, generic,
go, haskell, html, ini, java, javascript, json, kotlin, lua, makefile, markdown,
perl, php, powershell, python, r, ruby, rust, scss, shell, sql, svelte, swift,
terraform, toml, typescript, vue, xml, yaml.

Add your own language by writing a preset YAML file — no code required:

```yaml
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

Drop it in `~/.config/alinter/presets/`, set `ALINTER_PRESET_PATH`, or list a
directory under `preset_paths:` in your config.

## Inline suppression

Any comment style works, because alinter just looks for the marker text:

```python
x = 1  # alinter: disable-line=generic/trailing-whitespace
# alinter: disable-next-line=python/no-print
print("hi")
# alinter: disable-file=generic/line-ending
```

Directives: `disable`, `disable-file`, `ignore-file`, `disable-next-line`,
`disable-line`, `enable` (cancels a file-level `disable`). With no rule ids
listed, the directive suppresses **all** rules.

## Plugins

Publish a custom check type via an entry point:

```toml
[project.entry-points."alinter.checks"]
my-check = "my_package.checks:MyCheck"
```

or point alinter at a module from config:

```yaml
plugins:
  - my_package.checks          # module exposing register(registry) or CHECKS
  - my_package.checks:MyCheck  # or a specific Check subclass
```

A check is a small class:

```python
from alinter.checks.base import Check

class MyCheck(Check):
    name = "my-check"
    help = "Whatever this checks."

    def run(self, file):
        for number, line in enumerate(file.lines, 1):
            if "bad thing" in line:
                yield self.violation(file, line=number, column=1)
```

## Python API

```python
from alinter import lint

result = lint(["src/"], config=".alinter.yaml")
for violation in result.violations:
    print(violation.location, violation.message)
```

## CLI reference

```
alinter [check] [PATHS...]   lint files (default command)
alinter init                 write a starter .alinter.yaml
alinter presets              list presets (--show NAME, --json)
alinter rules                list the rules that apply to files
alinter explain RULE_ID      explain one rule
alinter langs                show detected languages per file
alinter validate             validate config and rules
alinter types                list built-in check types
alinter version              print the version
```

Useful flags: `--config`, `--no-config`, `--format`, `--fix`, `--fix-dry-run`,
`--select`, `--ignore`, `--include`, `--exclude`, `--severity`, `--fail-on`,
`--strict`, `--stdin`, `--allow-commands`, `--no-gitignore`, `--no-color`.

Exit codes: `0` clean, `1` violations at or above `--fail-on` (default
`error`), `2` configuration error.

## Development

```bash
git clone https://github.com/Baba01hacker666/alinter
cd alinter
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Quality gates (also run in CI):

```bash
ruff check src tests examples            # formatting, imports, bugbear, pyupgrade
bandit -c pyproject.toml -r src/alinter  # security (bandit rules)
pyflakes src/alinter tests examples      # undefined names / unused imports
alinter check .                          # the linter lints the whole repo, docs included
python -m pytest -q                      # test suite
```

Measure coverage (enforced at 93% in CI):

```bash
python -m pytest --cov=alinter --cov-report=term-missing
```

Ruff and bandit are configured in `pyproject.toml`; alinter's self-lint is
driven by the repository's own [`.alinter.yaml`](.alinter.yaml). A
`.pre-commit-config.yaml` is provided; run `pre-commit install` to enable the
hooks locally. The development guide is
[`docs/development.md`](docs/development.md).

## License

MIT © baba01hacker
