# alinter documentation

`alinter` is a **universal, config-driven linter**. Instead of hard-coding a
linter per language, it lints *files* using rules that are plain data; language
support is shipped as presets, and you can write new rules (or whole new
languages) without touching any code.

This directory is the long-form documentation. `README.md` in the repository
root is the short overview; start here when you want the details.

## Contents

| Document | What it covers |
| --- | --- |
| [how-it-works.md](how-it-works.md) | The linting pipeline and the module layout. |
| [configuration.md](configuration.md) | Config discovery, every key, and merge rules. |
| [rules.md](rules.md) | Anatomy of a rule, scopes, severities, overrides. |
| [checks.md](checks.md) | Every built-in check type and its parameters. |
| [presets.md](presets.md) | Detection, `always_apply`, and adding a language. |
| [suppressions.md](suppressions.md) | Inline `alinter:` suppression comments. |
| [plugins.md](plugins.md) | Shipping custom check types. |
| [reporters.md](reporters.md) | `text`, `json`, `sarif`, `junit`, `github`. |
| [cli.md](cli.md) | Every command and flag. |
| [python-api.md](python-api.md) | Using alinter from Python. |
| [development.md](development.md) | Setup, quality gates, CI, releasing. |
| [faq.md](faq.md) | Common questions and troubleshooting. |

## In one paragraph

alinter **discovers** the files you point it at, **reads** and **detects** each
file's language, **selects** the rules that apply (always-on baseline rules,
matching language presets, and your own rules), **runs** each rule's check, and
**reports** the violations — optionally applying **auto-fixes**. Everything in
the middle is driven by configuration, so the same engine lints Python, YAML,
Terraform, Markdown, or a bespoke DSL you invented this morning.

## See also

- [AGENTS.md](../AGENTS.md) — orientation for AI coding agents and new contributors.
- [CONTRIBUTING.md](../CONTRIBUTING.md) — how to propose changes.
- [CHANGELOG.md](../CHANGELOG.md) — release history.
