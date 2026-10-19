# Development

## Requirements

- Python 3.9+ (CI runs 3.9 through 3.13).
- `pip` and a virtual environment.

## Setup

```bash
git clone https://github.com/Baba01hacker666/alinter
cd alinter
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

The `dev` extra installs `pytest`, `build`, `pyflakes`, `ruff`, `bandit` and
`defusedxml`.

## Repository layout

```
src/alinter/         the package
  cli.py             argparse CLI and command handlers
  config.py          config discovery, merge, Rule construction
  discovery.py       path walking, globs, .gitignore
  engine.py          the lint pipeline
  presets.py         preset loading + detection index
  registry.py        type -> Check registry, plugin loading
  checks/            built-in checks (one module per family)
  reporters/         output formats
  presets/*.yaml     bundled language/formats
tests/               pytest suite (mirrors the modules)
docs/                this documentation
examples/            sample config and plugin
```

## Quality gates

These run in CI and are the definition of "green":

```bash
ruff check src tests examples            # style, imports, bugbear, pyupgrade
bandit -c pyproject.toml -r src/alinter  # security (bandit rules)
pyflakes src/alinter tests examples      # undefined names, unused imports
alinter check src tests examples         # alinter lints itself
python -m pytest -q                      # unit tests
```

Ruff and bandit are configured in `pyproject.toml`; the self-lint uses
`.alinter.yaml`. Every tool is expected to pass with no output.

### Coverage

```bash
python -m pytest --cov=alinter --cov-report=term-missing
```

## Tests

Tests use pytest with fixtures defined in `tests/conftest.py`:

- `project` — a temporary project directory with a `write()`/`config()` helper.
- `lint` — build a config and run the engine, returning a `LintResult`.
- `build_check` — construct a check instance from a rule dict.
- `build_rule_obj` — `build_rule`.
- `source_factory` — fabricate a `SourceFile` from text.

```python
def test_no_foo(project, lint):
    project.write("a.txt", "FOO\n")
    config = "rules:\n  - id: t/no-foo\n    type: literal\n    value: FOO\n"
    result = lint(config=config, paths=["."])
    assert any(v.rule_id == "t/no-foo" for v in result.violations)
```

Write focused tests: one behaviour per test, named after the behaviour,
asserting on observable results.

## Adding a check type

1. Add a module under `src/alinter/checks/` (or extend an existing family).
2. Subclass `Check`, implement `run`, set `name`/`help`/`fixable`/`singleton`.
3. Register it in `src/alinter/checks/__init__.py` (`BUILTIN_CHECKS`).
4. Add tests in `tests/`.
5. Document it in `docs/checks.md` and, if user-facing, `CHANGELOG.md`.

## Adding a language preset

Presets need no code. Add `src/alinter/presets/<lang>.yaml` with `name`,
`language`, `detect` and `rules`, then add a detection test in
`tests/test_presets.py`. See [presets.md](presets.md).

## Pre-commit

A `.pre-commit-config.yaml` runs ruff, bandit, pyflakes and alinter locally:

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

## Continuous integration

`.github/workflows/ci.yml`:

- **test** — matrix over Python 3.9–3.13: install, `ruff check`,
  `bandit`, `pyflakes`, alinter self-lint, `pytest`.
- **build** — `python -m build` and upload the `dist/` artifacts.

## Releasing

1. Bump `version` in `pyproject.toml` and add a `CHANGELOG.md` entry.
2. `python -m build` and check the artifacts
   (`python -m twine check dist/*`).
3. Tag and push:

   ```bash
   git tag -a v0.1.0 -m "v0.1.0"
   git push origin main --tags
   ```

4. Upload to PyPI:

   ```bash
   python -m twine upload dist/*
   ```

   (Or add a tag-triggered workflow using PyPI trusted publishing.)

## Style notes

- Type hints everywhere; `from __future__ import annotations` at the top.
- Prefer `collections.abc` types and PEP 585/604 syntax.
- Every module starts with a docstring explaining *why* it exists.
- Keep dependencies minimal; `pathspec` and `defusedxml` are optional extras.
- Never raise at import time for optional dependencies — degrade gracefully.

## Next

- [how-it-works.md](how-it-works.md) — the pipeline you are extending.
- [AGENTS.md](../AGENTS.md) — quick orientation for automated contributors.
