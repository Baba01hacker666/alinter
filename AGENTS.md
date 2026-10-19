# AGENTS.md

Orientation for AI coding agents (and humans) working in this repository.
Read this first; it tells you where things live, what "done" means, and the
conventions to follow.

## What this project is

`alinter` is a **universal, config-driven linter** for Python 3.9+. Rules are
plain data (`id` + `type` + parameters); language support ships as preset
files, so new languages never require code changes. It is packaged on PyPI
(author: `baba01hacker`) under the `alinter` distribution name.

- Package source: `src/alinter/`
- Docs: `docs/` (start at [`docs/README.md`](docs/README.md))
- Tests: `tests/`
- Bundled presets: `src/alinter/presets/*.yaml`

## Golden commands

Run these before considering any change complete. All four must pass cleanly:

```bash
pip install -e ".[dev]"

ruff check src tests examples            # style, imports, bugbear, pyupgrade
bandit -c pyproject.toml -r src/alinter  # security
pyflakes src/alinter tests examples      # undefined names / unused imports
alinter check src tests examples         # alinter lints itself
python -m pytest -q                      # unit tests
```

Useful extras:

```bash
python -m pytest --cov=alinter --cov-report=term-missing
alinter presets && alinter types && alinter rules .
python -m build                          # wheel + sdist
```

## Non-negotiable invariants

1. **Rules are data.** Never hard-code a language check in the engine; add or
   edit a preset, or a check type.
2. **Optional dependencies degrade gracefully.** `pathspec` (gitignore) and
   `defusedxml` (XML hardening) may be absent; import them in `try/except
   ImportError` and fall back.
3. **Never crash on user input.** Bad encodings, binary files, broken plugins
   and failing checks must produce recorded errors, not tracebacks.
4. **Determinism.** Discovery is sorted; violation ordering is stable; caches
   are per-run.
5. **Config errors exit 2; lint failures exit 1; success exits 0.**
6. **`from __future__ import annotations`** at the top of every module, and
   PEP 585/604 type syntax (`list[str]`, `X | None`).

## Where to change what

| Task | Touch |
| --- | --- |
| Add a check type | `src/alinter/checks/<family>.py`, register in `checks/__init__.py`, test in `tests/` |
| Add a language/format | `src/alinter/presets/<name>.yaml` (see `docs/presets.md`) |
| Change CLI flags | `src/alinter/cli.py` (+ `docs/cli.md`) |
| Change config keys | `src/alinter/config.py` (+ `docs/configuration.md`) |
| Change selection/pipeline | `src/alinter/engine.py` |
| Add an output format | `src/alinter/reporters/` |
| Fix parsing/matching | `src/alinter/utils.py` |

## Adding a check type (recipe)

```python
# src/alinter/checks/example.py
from __future__ import annotations

from collections.abc import Iterable

from ..models import SourceFile, Violation
from .base import Check


class ExampleCheck(Check):
    name = "example"
    fixable = False
    default_message = "example problem"
    help = "One-line description shown by `alinter types`."

    def __init__(self, rule) -> None:
        super().__init__(rule)
        # validate parameters here; raise ValueError on bad input

    def run(self, file: SourceFile) -> Iterable[Violation]:
        yield self.violation(file, line=1, column=1)
```

Then add it to `BUILTIN_CHECKS` in `src/alinter/checks/__init__.py`, add a
`tests/test_*.py` case, and document it in `docs/checks.md`. The registry
converts `ValueError`/`TypeError` from `__init__` into a friendly `ConfigError`.

Set `singleton = True` only for whole-file properties (final newline, encoding,
…). Only the most specific singleton rule runs per file.

## Adding a preset

Create `src/alinter/presets/<name>.yaml`:

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

Add a detection assertion in `tests/test_presets.py`; the suite already asserts
every preset rule constructs. Avoid embedding code comments at column 0 in
Markdown examples unless the rule sets `ignore_fences: true`.

## Testing conventions

- Fixtures live in `tests/conftest.py`: `project`, `lint`, `build_check`,
  `build_rule_obj`, `source_factory`.
- One behaviour per test; name it after the behaviour.
- Prefer asserting on `LintResult` / `Violation` objects over internal calls.
- Keep tests hermetic (use `tmp_path` and `monkeypatch.chdir`).

## Style

- Ruff with `E,W,F,I,UP,B,C4,SIM,RUF,PIE,PERF,BLE`; line length 100 (`E501`
  deferred to alinter's own `python/max-line-length`). See `pyproject.toml`.
- Bandit with justified inline `# nosec` markers — never a blanket skip.
- Module docstrings explain *why*; keep comments meaningful, not decorative.
- Update `CHANGELOG.md` for user-visible changes and the relevant `docs/` page.

## Definition of done

- [ ] The golden commands above all pass cleanly.
- [ ] New behaviour is covered by tests.
- [ ] User-facing changes documented in `docs/` and `CHANGELOG.md`.
- [ ] No new required dependencies without justification (prefer an extra).
- [ ] `alinter check src tests examples` still reports "All clear".

## Links

- Architecture: [`docs/how-it-works.md`](docs/how-it-works.md)
- Contributing: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- Security policy: [`SECURITY.md`](SECURITY.md)
