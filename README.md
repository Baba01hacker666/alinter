# alinter

**A universal, config-driven linter.** Rules are data, not code, and language
support ships as presets — so you can lint any language, format, or bespoke DSL
with one tool and one config, without changing the linter.

- 🧩 **Language agnostic** — rules are plain YAML/JSON/TOML.
- 📦 **Presets, not rebuilds** — add a language by dropping in a file.
- ✍️ **Your rules, anywhere** — one-off checks for obscure formats are trivial.
- 🔧 **Auto-fix** — whitespace, newlines, line endings, and patterns.
- 📊 **Many outputs** — `text`, `json`, `sarif`, `junit`, `github`.
- 🪝 **Plugins** — custom check types via entry points.

## Install

```bash
pip install alinter
```

Python 3.9+ and PyYAML (plus `tomli` on older Pythons). Optional extras:
`alinter[gitignore]` for `.gitignore`-aware discovery, `alinter[xml]` to harden
XML parsing with `defusedxml`.

## Quick start

```bash
alinter                  # lint the current directory
alinter check src/       # lint specific paths
alinter init             # write a starter .alinter.yaml
alinter --fix            # apply automatic fixes
alinter --format sarif > alinter.sarif
```

## How it works

Discover files → detect each file's language (extension, name, or shebang) →
select the rules that apply (always-on baseline + matching language presets +
your own) → run each check → report, optionally fixing. See
[`docs/how-it-works.md`](docs/how-it-works.md).

## Configuration

alinter reads `.alinter.yaml`, `alinter.yml`, `.alinter.json`, `.alinter.toml`,
or a `[tool.alinter]` table in `pyproject.toml`, walking up from the working
directory. A global config at `~/.config/alinter/config.yaml` is merged
underneath. A minimal config:

```yaml
version: 1
extends: [python, yaml]          # force extra presets on
exclude: ["**/vendor/**"]
ignore: ["generic/line-ending"]  # turn rules off by id (globs ok)

rules:
  - id: custom/no-todo
    type: regex
    pattern: '\b(TODO|FIXME)\b'
    mode: forbidden
    severity: info
    message: "unresolved {match} marker"
```

A rule entry **without** a `type` overrides an existing rule by id. Full details
are in [`docs/configuration.md`](docs/configuration.md) and
[`docs/rules.md`](docs/rules.md). Run `alinter presets`, `alinter types`, and
`alinter --help` for the live reference.

## Documentation

Everything else lives in [`docs/`](docs/README.md):

- [How it works](docs/how-it-works.md) · [Configuration](docs/configuration.md) · [Rules](docs/rules.md)
- [Checks](docs/checks.md) · [Presets](docs/presets.md) · [Suppressions](docs/suppressions.md)
- [Plugins](docs/plugins.md) · [Reporters](docs/reporters.md) · [CLI](docs/cli.md)
- [Python API](docs/python-api.md) · [Development](docs/development.md) · [FAQ](docs/faq.md)

Contributors should also read [`AGENTS.md`](AGENTS.md),
[`CONTRIBUTING.md`](CONTRIBUTING.md), and [`SECURITY.md`](SECURITY.md).

## License

MIT © baba01hacker
