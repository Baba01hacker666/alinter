# How alinter works

alinter is deliberately small. The whole engine is a six-stage pipeline that
turns *paths + config* into *violations (+ fixes)*. Nothing in the pipeline is
language-specific: language knowledge lives in [presets](presets.md) and rule
behaviour lives in [checks](checks.md).

```
            config file(s)                 paths (CLI / API)
                  │                              │
                  ▼                              ▼
   ┌───────────────────────┐        ┌────────────────────────┐
   │ 1. config            │        │ 2. discovery           │
   │    load + merge      │        │    walk, filter,        │
   │    (config.py)       │        │    .gitignore           │
   └──────────┬────────────┘        └───────────┬────────────┘
              │                                 │
              ▼                                 ▼
   ┌───────────────────────────────────────────────────────┐
   │ 3. detect  — extension / filename / shebang → language │
   │ 4. select  — presets + user rules + overrides          │
   └───────────────────────────┬───────────────────────────┘
                               ▼
   ┌───────────────────────────────────────────────────────┐
   │ 5. run     — one Check instance per rule, per file     │
   │    (suppressions, severity filter, error isolation)    │
   └───────────────────────────┬───────────────────────────┘
                               ▼
   ┌───────────────────────┐   ┌───────────────────────────┐
   │ 6. fix   (optional)   │──▶│ 7. report (reporter)       │
   │    apply edits, loop  │   │    text / json / sarif / … │
   └───────────────────────┘   └───────────────────────────┘
```

## Stage 1 — Discovery and loading of configuration

`alinter.config.load_config` finds and merges configuration from (lowest to
highest precedence):

1. built-in defaults;
2. your global user config (`$XDG_CONFIG_HOME/alinter/config.yaml`);
3. the project config found by walking up from the working directory;
4. a file passed with `--config`.

Mappings are deep-merged and certain list keys (`rules`, `extends`,
`exclude`, …) are concatenated. See [configuration.md](configuration.md) for
the details.

## Stage 2 — File discovery

`alinter.discovery.discover` turns the target paths into a deterministic,
sorted list of files:

- Directories are walked with `os.walk` (symlinks not followed by default).
- `include` / `exclude` globs are applied per file and to directories for
  pruning. Globs support `**`, `*`, `?` and `[...]` character classes, and a
  bare name such as `vendor` matches that segment and everything under it.
- `.gitignore` and `.git/info/exclude` are honoured when `use_gitignore` is on
  and the optional `pathspec` dependency is installed.
- A built-in list of excludes skips `.git`, `.venv`, `node_modules`, build
  output, lockfiles, minified assets, and more (see `DEFAULT_EXCLUDES`). Set
  `settings.exclude_defaults: false` to drop that list.
- Missing paths are recorded and surfaced as `result.errors`.

Each accepted file is stored as a `DiscoveredFile` with both its absolute path
and a normalised, root-relative path.

## Stage 3 — Reading and language detection

For each file the engine:

1. skips files whose sniffed bytes contain NUL (binary) and files larger than
   `settings.max_file_size`;
2. decodes the bytes, picking an encoding from `settings.encoding`, then
   `utf-8`, then `utf-16`, then `latin-1` as a last resort (so linting never
   crashes on odd encodings);
3. detects a language via the preset `DetectionIndex`, trying in order:
   **file name** (`Dockerfile`, `Makefile`, …), **extension** (`.py`, `.tf`,
   …), then **shebang** (`#!/usr/bin/env python3`).

The detected language is what ties a file to a *preset*.

## Stage 4 — Rule selection

Rules come from three places, and are combined by `id` (later wins):

1. **preset rules** — from `extends:` plus the auto-detected language preset
   plus every preset marked `always_apply: true` (the `generic` baseline);
2. **your `rules:`** — replace a preset rule of the same `id`;
3. **overrides** — a `rules:` entry with an `id` but no `type` *patches* an
   existing rule (change a parameter, severity, message, scope).

Selection then applies:

- **scope** — a rule runs only for files its `files`/`exclude` globs and
  `languages` allow. Preset rules are scoped to their preset's language
  automatically.
- **`select` / `ignore`** — fnmatch patterns that whitelist or blacklist rule
  ids (from config *and* the CLI; the CLI adds to the config).
- **severity** — rules set to `severity: off` are dropped, as are violations
  below the `--severity` reporting threshold.
- **singletons** — checks that describe a whole-file property (`final-newline`,
  `line-ending`, `no-trailing-whitespace`, `no-tabs`, `encoding`,
  `max-file-size`, `filename`) run at most once per file. When several rules of
  the same type match, the most *specific* one wins:

  | specificity | source |
  | --- | --- |
  | 2 | your own rule |
  | 1 | a language preset |
  | 0 | the `generic` baseline |

  This is how `css/final-newline` cleanly overrides `generic/final-newline`
  without double-reporting.

The result is cached per language for the duration of the run.

## Stage 5 — Running checks

For every selected rule the engine creates **one Check instance** (cached by
rule id) and calls `check.run(source)`. While yielding violations the engine:

- **isolates failures** — an exception from one rule is recorded as an error
  and does not abort the run;
- applies **inline suppressions** parsed from the file text;
- drops violations below the configured reporting severity;
- collects any attached `TextEdit` for the fix stage.

Violations are sorted by `(path, line, column, rule id)` for stable output.

## Stage 6 — Fixing (optional)

With `--fix` (or `--fix-dry-run`) the engine runs a bounded loop
(`settings.max_iterations`, default 10):

1. lint the in-memory sources and collect edits;
2. apply non-overlapping edits (`alinter.fixer.apply_edits`); overlapping edits
   are deferred to the next pass;
3. rewrite each changed file preserving its original encoding and BOM;
4. repeat until no edits remain or the iteration cap is hit.

`--fix-dry-run` reports what *would* change without writing anything.

## Stage 7 — Reporting

A reporter (`alinter/reporters/`) renders the `LintResult`. The CLI maps the
result to an exit code based on `--fail-on` (default: `error`). See
[reporters.md](reporters.md) and [cli.md](cli.md).

## Module map

| Module | Responsibility |
| --- | --- |
| `alinter/cli.py` | argparse CLI, command handlers, exit codes. |
| `alinter/config.py` | Config discovery, merge and `Rule` construction. |
| `alinter/discovery.py` | Walking paths, globs, `.gitignore`. |
| `alinter/engine.py` | The pipeline: selection, running, fixing. |
| `alinter/presets.py` | Preset loading and the detection index. |
| `alinter/registry.py` | Rule `type` → `Check` registry and plugin loading. |
| `alinter/checks/` | Built-in check implementations. |
| `alinter/models.py` | `Rule`, `Violation`, `SourceFile`, `LintResult`, `Severity`. |
| `alinter/ignores.py` | Inline suppression parsing. |
| `alinter/fixer.py` | Applying `TextEdit`s. |
| `alinter/reporters/` | Output formats. |
| `alinter/utils.py` | Globs, parsing, encoding, colours. |

## Design principles

- **Rules are data, not code.** A rule is an `id`, a `type`, and parameters.
- **Language support is a file.** Add `mylang.yaml` and you are done.
- **Never crash on user input.** Bad encodings, binary files, broken plugins
  and failing rules degrade to reported errors.
- **Deterministic and cache-friendly.** Sorted discovery, stable ordering,
  per-language and per-rule caches.
