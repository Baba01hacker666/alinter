# Reporters

A **reporter** turns a `LintResult` into output. Select one with
`--format NAME` (aliases in parentheses). `alinter` prints the reporter's
output to stdout; a process exit code is derived separately from `--fail-on`.

| Format | Purpose |
| --- | --- |
| `text` | Human-readable, colored, grouped by file (default). |
| `json` | Full machine-readable result. |
| `sarif` | SARIF 2.1.0 for code-scanning UIs. |
| `junit` (`xml`) | JUnit XML for CI test reporters. |
| `github` (`gha`) | GitHub Actions workflow annotations. |

## text

```text
a.py
  1:6      info     trailing whitespace  (generic/trailing-whitespace)  [fixable]
      | x = 1
  2:1      warning  print() call found; use logging instead  (python/no-print)
      | print(x)

Found 2 problems  (0 errors, 1 warnings, 1 info)
1 file checked, 13 rules, 0.0029s
```

Color is enabled only on a TTY, or forced with `--color`/`--no-color` (and
honours `NO_COLOR`/`FORCE_COLOR`). `-q/--quiet` drops the per-file detail and
prints only the summary. With `--fix` the summary reports what was fixed; with
`--fix-dry-run` it says what *would* be fixed.

## json

A single object with a `summary`, a `violations` array and any `errors`:

```json
{
  "tool": "alinter",
  "version": "0.1.0",
  "summary": {
    "files": 1, "skipped": 0, "rules": 13, "violations": 2,
    "errors": 0, "warnings": 1, "info": 1, "fixable": 1, "fixed": 0,
    "duration": 0.0027
  },
  "violations": [
    {
      "rule": "generic/trailing-whitespace",
      "message": "trailing whitespace",
      "path": "a.py",
      "severity": "info",
      "type": "no-trailing-whitespace",
      "line": 1, "column": 6,
      "snippet": "x = 1   ",
      "fixable": true
    }
  ],
  "fixed_files": [],
  "errors": []
}
```

Fields are included only when known (`line`, `column`, `end_line`,
`end_column`, `snippet`, `tags`, `type`).

## sarif

SARIF 2.1.0, consumable by GitHub code scanning and most IDEs. Rules are
collected into `runs[0].tool.driver.rules`; results carry
`physicalLocation` with region data, and engine-level problems surface as
`invocations[0].toolExecutionNotifications`.

## junit

JUnit XML. Each file becomes a `testcase` per violation inside a single
`testsuite`; a clean run emits one passing `testcase`. Suitable for
`--junitxml`-style CI consumers.

## github

One workflow command per violation, ready for `::error`/`::warning`/`::notice`
annotations in GitHub Actions:

```text
::notice file=a.py,line=1,col=6,title=generic/trailing-whitespace::trailing whitespace
::warning file=a.py,line=2,col=1,endLine=2,endColumn=7,title=python/no-print::print() call found; use logging instead
```

Messages and properties are percent-escaped, and no color codes are emitted.

## Using a reporter in CI

```yaml
- run: alinter check --format sarif . > alinter.sarif
- uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: alinter.sarif
```

```yaml
- run: alinter --format github .
- run: alinter --format junit . > alinter-junit.xml
```

## Exit codes

Reporter choice does not affect the exit code. Independently, alinter returns:

- `0` — clean (no violations at or above `--fail-on`),
- `1` — violations at or above the threshold,
- `2` — configuration error.

See [cli.md](cli.md).
