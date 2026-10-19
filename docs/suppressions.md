# Inline suppressions

Sometimes a violation is correct but not worth fixing — a generated block, a
deliberate `print`, a long line you will not wrap. alinter lets you silence
rules from inside the file, in **any language**, because it simply looks for the
marker text in a comment.

## Directives

| Directive | Effect |
| --- | --- |
| `disable=RULES` | Suppress `RULES` for the rest of the file. |
| `disable-file=RULES` | Alias of `disable`. |
| `ignore-file=RULES` | Alias of `disable`. |
| `disable-line=RULES` | Suppress `RULES` on the same line. |
| `disable-next-line=RULES` | Suppress `RULES` on the following line. |
| `enable=RULES` | Cancel an earlier file-level `disable` for `RULES`. |

`RULES` is a comma- or space-separated list of rule ids. **With no ids, the
directive suppresses all rules.**

The marker is `alinter:` or `alinter-`, so all of these work:

```python
x = 1        # alinter: disable-line=generic/trailing-whitespace
# alinter: disable-next-line=python/no-print
print("hi")
# alinter: disable-file=generic/line-ending
y = 2  # alinter-disable-line=generic/trailing-whitespace
```

```yaml
# alinter: disable-next-line=generic/max-line-length
key: a-very-long-value-that-would-otherwise-exceed-the-limit
```

```js
// alinter: disable-next-line=javascript/no-console
console.log("debug")
```

```html
<!-- alinter: disable-next-line=html/... -->
```

## Suppressing everything

```python
# alinter: disable
...  # nothing in this file is reported
```

## File-level disable then re-enable

```python
# alinter: disable=python/no-bare-except
...generated code...
# alinter: enable=python/no-bare-except
```

## Scoping preference

Inline suppressions are best for **local, justified** cases. For project-wide
rules use config instead:

- `ignore: ["python/no-print"]` — turn a rule off everywhere.
- `select:` — allow-list only the rules you want.

Because alinter is severity-aware, a lighter-weight option is to lower a rule to
`info` and keep the signal visible without failing a build.

## How it works

`alinter.ignores.parse_suppressions` scans every line for the marker and builds
a small state object: a set of file-wide ids and a map of line number to ids.
When a violation is produced, the engine drops it if its rule id (or the wildcard
`*`) is suppressed for that file or that line. No language parser is involved,
so the mechanism is identical for every file type.

## Next

- [rules.md](rules.md) — how rules are named and scoped.
- [configuration.md](configuration.md) — config-level `ignore`/`select`.
