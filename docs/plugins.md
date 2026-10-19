# Plugins

When a [preset](presets.md) rule cannot express something, add a **check type**
— a small Python class — and reuse it from any rule. There are two ways to
distribute one: a config `plugins:` target, or the `alinter.checks` entry-point
group.

## The Check API

A check subclasses `alinter.checks.base.Check` and implements `run`, yielding
`Violation`s:

```python
from collections.abc import Iterable

from alinter.checks.base import Check
from alinter.models import SourceFile, Violation


class NoDebuggerCheck(Check):
    name = "no-debugger"                       # the rule `type` this implements
    help = "Forbid leftover debugger statements."
    fixable = False                            # can it emit TextEdits?
    default_message = "debugger statement"     # used when a rule sets no message
    singleton = False                          # whole-file property? (see below)

    def __init__(self, rule) -> None:
        super().__init__(rule)
        self.token = str(self.param("token", "breakpoint()"))

    def run(self, file: SourceFile) -> Iterable[Violation]:
        for number, line in enumerate(file.lines, 1):
            if self.token in line:
                yield self.violation(file, line=number, column=1)
```

### Class attributes

| Attribute | Meaning |
| --- | --- |
| `name` | The rule `type` string (also the default registration key). |
| `help` | One-line description shown by `alinter explain` / `alinter types`. |
| `fixable` | Whether the check may attach a `TextEdit` to a violation. |
| `default_message` | Message used when the rule doesn't set one. |
| `singleton` | `True` for whole-file properties; only the most specific rule of that type runs per file. |

### Helper methods

- `self.param(name, default=None)` — read a rule parameter.
- `self.message(**extra)` — render the rule's `message` template with
  parameters plus extras; unknown placeholders degrade to the raw template.
- `self.violation(file, *, line=None, column=None, end_line=None,
  end_column=None, message=None, snippet=None, fix=None, **extra)` — build a
  `Violation`. If `message` is omitted it is rendered via `self.message`.

`SourceFile` exposes `text`, `lines`, `split_lines_keepends()`, `filename`,
`extension`, `language`, `line_col(offset)`, `line_text(line)` and more.

## Option A — load from config

Expose a `CHECKS` mapping, a `register(registry)` function, or a list of
`CHECK_CLASSES`, then point config at the import target:

```python
# my_package/checks.py
from alinter.checks.base import Check

class MyCheck(Check):
    name = "my-check"

    def run(self, file):
        return []

CHECKS = {"my-check": MyCheck}
```

```yaml
# .alinter.yaml
plugins:
  - my_package.checks            # module with CHECKS / register / CHECK_CLASSES
  - my_package.checks:MyCheck    # or a single Check subclass by attribute
```

A `module:attribute` target registers the object under its `name` attribute (or
the attribute name). A module target calls `register(registry)` if present,
then registers `CHECKS`, then `CHECK_CLASSES`.

Then use it like any built-in type:

```yaml
rules:
  - id: project/no-debugger
    type: no-debugger
    token: "pdb.set_trace()"
    severity: warning
```

See [`examples/plugin_spdx.py`](../examples/plugin_spdx.py) for a complete,
runnable check.

## Option B — publish an entry point

Shipping a package? Advertise the check so it is discovered automatically:

```toml
# pyproject.toml of your plugin package
[project.entry-points."alinter.checks"]
my-check = "my_package.checks:MyCheck"
```

Installing that package makes `type: my-check` available to every project, with
no `plugins:` entry needed. alinter loads entry points once per process.

## Rules for a good plugin

- **Never raise for bad user input.** Validate in `__init__` and raise
  `ValueError`/`TypeError`; the registry converts those into a friendly
  `ConfigError`. Keep `run` robust.
- **Yield, don't collect.** `run` is a generator; yield violations as you find
  them.
- **Be deterministic.** Same input, same violations, same order.
- **Set `singleton`** only for genuine whole-file properties.

## Next

- [checks.md](checks.md) — the built-in checks you can model yours on.
- [python-api.md](python-api.md) — driving the engine directly.
