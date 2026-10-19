# Security Policy

## Supported versions

alinter is pre-1.0. Security fixes are applied to the latest release on the
`main` branch.

| Version | Supported |
| --- | --- |
| 0.1.x | ✅ |

## Reporting a vulnerability

Please **do not** open a public issue for a security problem. Instead, use
GitHub's private reporting:

1. Go to the [Security tab](https://github.com/Baba01hacker666/alinter/security)
   of the repository.
2. Click **Report a vulnerability**.
3. Describe the issue, the impact, and a minimal reproduction if possible.

We aim to acknowledge reports within a few days and will credit reporters who
wish to be named once a fix is released.

## Threat model and design notes

alinter reads the files you point it at and runs the rules you configure. It is
a developer tool, not a sandbox, and the following are intentional behaviours
worth understanding:

- **`command` checks execute programs.** This is the most powerful check type,
  so it is **off by default**: it only runs when you pass `--allow-commands` or
  set `settings.allow_commands: true`. Commands come from your own config; do
  not run a `.alinter.yaml` you do not trust. The few places the codebase
  imports `subprocess` are marked with a justified `# nosec` comment.
- **XML parsing uses `defusedxml` when available.** Install `alinter[xml]` to
  harden the `structure` check against entity-expansion ("billion laughs")
  attacks. Without it, parsing falls back to the standard library and is only
  intended for your own trusted project files.
- **`.gitignore` handling uses the optional `pathspec` package** (`alinter[gitignore]`).
- **Plugins run in-process.** Code loaded via the `alinter.checks` entry point
  or the `plugins:` config is arbitrary Python with the same privileges as
  alinter itself. Only load plugins you trust.
- **No network access.** The engine never phones home; it only reads local
  files (and runs `command` checks if you enable them).

## Hardening checklist

- Run `pip install "alinter[xml]"` if you lint XML.
- Keep `allow_commands` off unless you need it, and review configs before use.
- Pin alinter and its extras in CI for reproducible scans.
- Run the bundled quality gates (`ruff`, `bandit`, `pyflakes`, `pytest`) when
  building from source; CI does this on every change.

## Dependency vulnerabilities

Runtime dependencies are `PyYAML` (plus `tomli` on Python < 3.11), with
`pathspec` and `defusedxml` as optional extras. If a dependency advisory
affects alinter, we will bump the constraint and note it in `CHANGELOG.md`.
