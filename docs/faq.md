# FAQ & troubleshooting

## Is this meant to replace pylint / ruff / eslint?

No. alinter is **complementary**. Use your language's specialist linter for
deep analysis, and alinter to (a) enforce project-wide, cross-language
conventions with one tool and one config, and (b) catch the long tail of
project-specific rules without writing a plugin.

## How do I add support for a new language?

Write a preset file — no code. See [presets.md](presets.md). Detection works by
filename, extension or shebang, so most formats "just work".

## My rule never fires. Why?

Work through the stages in [how-it-works.md](how-it-works.md):

1. **Is the file discovered?** Check `alinter langs` and your `exclude`/gitignore
   settings. Binary files and files over `settings.max_file_size` are skipped.
2. **Is the language detected?** `alinter langs` shows the language per file. A
   file with no extension needs a `filenames` entry or a shebang.
3. **Is the rule selected?** `alinter rules` lists the rules that apply. Check
   `select`/`ignore` and the rule's own `files`/`exclude`/`languages`.
4. **Is the severity visible?** `severity: off` disables a rule; and anything
   below `--severity` (default `info`) is not reported.
5. **Does the pattern match?** Patterns are `MULTILINE` by default; pass
   `flags: []` to change that. Try `alinter explain RULE_ID` to see the final
   parameters.

## Why does `severity: off` not work in YAML?

YAML parses a bare `off` (and `no`) as boolean `false`. alinter handles that,
but quote it to be explicit and portable: `severity: "off"`.

## How do I silence one rule everywhere?

```yaml
ignore: ["python/no-print", "generic/*"]
```

Or allow-list with `select: ["python/*"]`. For a single line or file, use an
[inline suppression](suppressions.md).

## I only want to run my own rules.

Disable auto-detection and don't extend anything:

```yaml
auto_detect: false
extends: []
rules:
  - id: mine/no-todo
    type: literal
    value: TODO
```

Note the `generic` preset is `always_apply`; add `ignore: ["generic/*"]` to drop
the baseline too.

## How do I catch something unusual — a naming scheme, a header, a raw SQL call?

Combine the built-in checks:

- **text/shape** → `regex` or `literal` (with `mode`, `min`/`max`, `fix`).
- **line/file limits** → `max-line-length`, `max-lines`, `max-file-size`.
- **data files** → `structure` (require/forbid keys, assert dotted paths).
- **run your own tool** → `command` (opt-in).
- **anything else** → a small [plugin](plugins.md).

## Why am I not seeing duplicate final-newline / line-ending reports?

Those checks are **singletons**: only the most specific rule of the type runs
per file. A language preset overrides the `generic` baseline, and your own rule
overrides both. See [how-it-works.md](how-it-works.md#stage-4--rule-selection).

## How do I lint a file from stdin?

```bash
cat file.py | alinter --stdin --stdin-filename file.py
```

The filename drives language detection.

## How do I skip a directory?

```yaml
exclude:
  - "**/vendor/**"
```

Bare names work too (`vendor` matches that segment and everything under it).
Common build/VCS directories are excluded by default; set
`settings.exclude_defaults: false` to start from nothing.

## Is it fast? Does it run in parallel?

Discovery is single-process and deterministic, and results are cached per
language and per rule. `--jobs` is accepted but currently a no-op (reserved for
a future parallel runner). For very large trees, narrow the paths or exclude
generated content.

## How do I use it in CI?

```yaml
- run: pip install alinter
- run: alinter check --format github .
```

GitHub annotations appear inline; `--strict` fails the build on warnings, and
`--fail-on none` never fails. See [reporters.md](reporters.md).

## Can rules differ per directory?

alinter runs from the working directory against one resolved config. For
per-directory behaviour use a rule's `files`/`exclude` globs, or run alinter
once per directory with different `--config` files.

## Something is wrong with the tool itself.

Please [open an issue](https://github.com/Baba01hacker666/alinter/issues) with
your alinter version (`alinter version`), the config, and a minimal file that
reproduces it. See [SECURITY.md](../SECURITY.md) for vulnerabilities.
