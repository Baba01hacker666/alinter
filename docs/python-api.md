# Python API

alinter is importable as a library. The public surface is re-exported from the
top-level package.

```python
from alinter import lint

result = lint(["src/"], config=".alinter.yaml")
for violation in result.violations:
    print(violation.location, violation.message)
```

## `lint(paths=None, *, config=None, cwd=".", **options)`

The convenience wrapper: loads configuration and runs the engine.

- `paths` — sequence of files/directories (defaults to `["."]`).
- `config` — a `Config`, a path to a config file, or `None` for discovery.
- `cwd` — working directory used for discovery and relative paths.
- `**options` — any [`Options`](#options) field, e.g. `format="json"`,
  `fix=True`, `severity=Severity.WARNING`, `select=("python/*",)`.

Returns a [`LintResult`](#models).

```python
from alinter import lint
from alinter.models import Severity

result = lint(
    ["."],
    config=None,
    fix=False,
    severity=Severity.WARNING,
    ignore=("generic/*",),
)
print(result.counts(), result.rules_run, result.files_checked)
```

## `Engine`

For repeated runs or fine control, build a `Config` and `Options` yourself.

```python
from alinter import Engine, load_config
from alinter.engine import Options

config = load_config(None, cwd=".", use_user_config=True)
options = Options(paths=["src"], cwd=".", format="json", fail_on="warning")
engine = Engine(config, options)
result = engine.run()
```

`Engine` also exposes `active_rules(include_disabled=False)`, which returns
`rule_id -> {type, severity, source, description, languages, files}` for the
files under the configured paths — this is what `alinter rules` uses.

## `Options`

A dataclass mirroring the CLI flags. The most useful fields:

| Field | Type | Default | Meaning |
| --- | --- | --- | --- |
| `paths` | list[str] | `[]` | Targets to lint. |
| `cwd` | str | `"."` | Working directory. |
| `config` | str \| None | `None` | Explicit config path. |
| `no_config` | bool | `False` | Ignore config files. |
| `fix` / `fix_dry_run` | bool | `False` | Apply / preview fixes. |
| `format` | str | `"text"` | Output format for reporters. |
| `severity` | `Severity` | `INFO` | Minimum reporting severity. |
| `fail_on` | `Severity` | `ERROR` | Failure threshold. |
| `select` / `ignore` | tuple[str, …] | `()` | Rule id patterns. |
| `include` / `exclude` | tuple[str, …] | `()` | File glob patterns. |
| `stdin_text` / `stdin_filename` | str \| None | `None` / `"<stdin>"` | Stdin mode. |
| `allow_commands` | bool \| None | `None` | Gate `command` checks. |
| `use_gitignore` | bool \| None | `None` | Override `.gitignore` handling. |
| `color` | bool \| None | `None` | Force/disable color. |
| `quiet` | bool | `False` | Summary only. |
| `max_iterations` | int | `10` | Fix-loop cap. |

`None` means "fall back to the config setting".

## `Config`

`load_config(path=None, *, cwd=".", no_config=False, use_user_config=True)`
returns a `Config` with fields such as `auto_detect`, `extends`, `include`,
`exclude`, `ignore`, `select`, `plugins`, `preset_paths`, `settings`, `rules`,
`overrides`, `sources`. Helpers: `setting(name, default)`, `excludes()`,
`rule_ids()`, `find_rule(id)`.

## Models

| Type | Purpose |
| --- | --- |
| `Rule` | A configured rule (`id`, `type`, `severity`, `params`, scopes). |
| `Violation` | One finding (`rule_id`, `message`, `path`, `line`, `column`, `fix`, …). |
| `SourceFile` | A file being linted plus offset→line/column helpers. |
| `LintResult` | Run output: `violations`, counters, `errors`, `duration`; `counts()`, `has_errors`. |
| `Severity` | `ERROR`/`WARNING`/`INFO`/`OFF` with `coerce`, `rank`, `is_active`. |

`Violation.location` renders `path:line:column`; `Violation.as_dict()` produces
the JSON-reporter shape. `LintResult.counts()` returns a severity histogram.

## Custom checks in-process

Use the registry directly to register or inspect check types:

```python
from alinter.registry import get_registry

registry = get_registry()
print(list(registry.names()))
registry.register("my-type", MyCheck)   # or use @registry.register("my-type")
```

## Reporting from code

Reporters are plain classes; render to a string or a stream:

```python
from alinter.reporters import get_reporter

reporter = get_reporter("sarif")
text = reporter.render(result, config=config, options=options)
```

## Next

- [plugins.md](plugins.md) — custom check types.
- [how-it-works.md](how-it-works.md) — what the engine does internally.
