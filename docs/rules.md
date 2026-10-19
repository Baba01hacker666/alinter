# Rules

A **rule** is the unit of configuration: it says *what to check* and *where*.
Rules are plain data — an `id`, a `type`, and parameters — so the same shape
works whether you are reusing a bundled preset rule or inventing a new one.

## Anatomy

```yaml
- id: custom/no-todo          # required, unique
  type: regex                 # required; a check type (see checks.md)
  description: "No TODO markers"   # human description (shown by `alinter explain`)
  message: "unresolved {match} marker"  # violation text template
  severity: warning           # error | warning | info | off
  files: ["**/*.py"]          # globs the rule applies to
  exclude: ["**/vendor/**"]   # globs the rule never applies to
  languages: [python]         # only for these detected languages
  tags: [style]               # free-form labels
  enabled: true               # hard on/off toggle
  # everything else is a parameter for the check `type`:
  pattern: '\b(TODO|FIXME)\b'
  mode: forbidden
```

### Reserved keys vs parameters

These keys are understood by the engine and are **not** passed to the check:

`id`, `type`, `description`, `message`, `severity`, `level`, `files`,
`exclude`, `languages`, `enabled`, `tags`, `params`, `url`, `source`,
`fixable`.

**Every other key becomes a parameter** for the check. You may also nest them
under `params:` if you prefer:

```yaml
- id: custom/line
  type: max-line-length
  params:
    length: 100
```

## `id`

- Must be unique within a config.
- Convention: `namespace/short-name`, e.g. `python/no-print`,
  `generic/final-newline`. It is only a label; the namespace is not special
  except that it makes integer select/ignore patterns readable.
- Used in `select`, `ignore` and [inline suppressions](suppressions.md).

## `severity`

One of `error`, `warning`, `info`, `off`. `off` disables the rule. Aliases such
as `warn`, `w`, `fatal`, `note`, `none` are accepted, and the numeric levels
`0`/`1`/`2`. Because YAML parses a bare `off`/`no` as boolean `false`, quote it:
`severity: "off"`.

Rules without a severity inherit the config-level `severity` (default `error`);
preset rules default to `warning`.

## `message`

A template rendered per violation. Placeholders may reference any rule
parameter and the values the check provides (`{match}`, `{count}`, `{limit}`,
`{line}`, `{length}`, `{value}`, `{name}`, …). Unknown placeholders make the
template render literally rather than raise.

```yaml
message: "line too long ({length} > {limit})"
```

## Scoping: `files`, `exclude`, `languages`

- `files`: list of globs; empty means "any file".
- `exclude`: list of globs to subtract.
- `languages`: only run when the detected language matches. Preset rules are
  automatically scoped to their preset's language.

Globs match root-relative, POSIX-style paths and support `**`, `*`, `?` and
`[...]`. A bare name matches that path segment and anything beneath it.

## Overriding and disabling

A `rules:` entry with an `id` but **no `type`** patches the existing rule of
that id; you do not restate the whole rule:

```yaml
rules:
  - id: python/no-print        # tighten a preset rule
    severity: error
  - id: python/max-line-length # change a single parameter
    length: 88
  - id: generic/line-ending    # turn one off
    severity: "off"
  - id: python/no-print        # or via `ignore`/`select`
    enabled: false
```

To disable in bulk, use `ignore: ["python/*"]`; to allow-list, use
`select: ["python/*"]`. Overriding an id that does not exist is reported by
`alinter validate` (and surfaces as a run error).

## Adding your own rules

Anything the built-in checks cannot express can be a rule too: combine a
`regex`/`literal` rule with `files`, `mode`, `min`/`max`, `fix` and a `message`
to catch project-specific mistakes.

```yaml
rules:
  - id: myapi/no-raw-select
    type: regex
    pattern: 'db\.execute\(\s*["'']SELECT'
    flags: [IGNORECASE]
    mode: forbidden
    severity: error
    message: "use the query builder instead of raw SELECT"
    files: ["src/**/*.py"]
```

If no check type fits, write it once as a [plugin](plugins.md).

## Next

- [checks.md](checks.md) — the parameters each `type` understands.
- [suppressions.md](suppressions.md) — silencing a rule on one line.
