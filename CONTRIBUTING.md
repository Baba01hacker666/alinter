# Contributing to alinter

Thanks for helping improve alinter! This document explains how to set up a
development environment, the conventions we follow, and what makes a pull
request mergeable.

## Getting started

```bash
git clone https://github.com/Baba01hacker666/alinter
cd alinter
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Run the quality gates (they must all pass):

```bash
ruff check src tests examples
bandit -c pyproject.toml -r src/alinter
pyflakes src/alinter tests examples
alinter check src tests examples
python -m pytest -q
```

Optional: install the local git hooks with `pip install pre-commit && pre-commit install`.

## Ways to contribute

- **Add a language/format preset** — a single YAML file, no code required. See
  [`docs/presets.md`](docs/presets.md).
- **Add a rule** — most needs are met by existing check types; see
  [`docs/checks.md`](docs/checks.md).
- **Add a check type** — when a rule can't express it; see
  [`docs/plugins.md`](docs/plugins.md) and the recipe in
  [`AGENTS.md`](AGENTS.md).
- **Fix a bug** — please include a test that would have caught it.
- **Improve docs** — `docs/`, the README, and docstrings.

## Pull request checklist

- [ ] The golden commands above pass cleanly.
- [ ] Tests cover the new behaviour (and existing tests still pass).
- [ ] Documentation updated (`docs/` and `README.md` where relevant).
- [ ] `CHANGELOG.md` has an entry under the unreleased/next version.
- [ ] Commits are focused; the diff is easy to review.

## Conventions

- Python 3.9+ syntax only; `from __future__ import annotations` everywhere.
- Type-annotate public functions and use PEP 585/604 types.
- Keep dependencies minimal. Optional features go behind extras
  (`gitignore`, `xml`) and degrade gracefully when absent.
- Never crash on user input: record an error instead of raising.
- Rules are data — resist adding language-specific branches to the engine.

## Commit messages

A short imperative subject, optionally a body explaining *why*:

```
feat(checks): add ignore_fences to pattern checks

Markdown '#' lines inside fenced code were counted as headings.
```

Common prefixes: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`.

## Reporting issues

Open an issue with:

- `alinter version`,
- your OS and Python version,
- the config (or a minimal version of it),
- the smallest file that reproduces the problem,
- the exact command and observed vs. expected output.

For security reports, follow [`SECURITY.md`](SECURITY.md) instead.

## Code of conduct

Be kind and constructive. Assume good faith, critique the code and not the
person, and help newcomers. See [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) for
the full policy and how to report problems.

## License

By contributing you agree that your contributions are licensed under the
MIT License (see [`LICENSE`](LICENSE)).
