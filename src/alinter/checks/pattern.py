"""Pattern based checks: ``regex`` and ``literal``.

Both share the same engine: search a file for matches, then act according to
``mode`` (``forbidden``, ``required`` or ``count``). Optional ``fix`` values
produce auto-fixes.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from ..models import SourceFile, TextEdit, Violation
from ..utils import as_bool, as_list, truncate
from .base import Check

FLAG_NAMES: dict[str, int] = {
    "IGNORECASE": re.IGNORECASE, "I": re.IGNORECASE, "i": re.IGNORECASE,
    "MULTILINE": re.MULTILINE, "M": re.MULTILINE, "m": re.MULTILINE,
    "DOTALL": re.DOTALL, "S": re.DOTALL, "s": re.DOTALL,
    "VERBOSE": re.VERBOSE, "X": re.VERBOSE, "x": re.VERBOSE,
    "ASCII": re.ASCII, "A": re.ASCII, "a": re.ASCII,
    "UNICODE": re.UNICODE, "U": re.UNICODE, "u": re.UNICODE,
}


def compile_flags(values: Any) -> int:
    flags = 0
    for name in as_list(values):
        key = str(name).strip()
        if key in FLAG_NAMES:
            flags |= FLAG_NAMES[key]
        else:
            raise ValueError(
                f"unknown regex flag {name!r}; "
                f"expected one of {', '.join(sorted(set(FLAG_NAMES)))}"
            )
    return flags


class PatternCheck(Check):
    """Common implementation for regex/literal rules."""

    fixable = True
    kind = "pattern"

    def __init__(self, rule) -> None:
        super().__init__(rule)
        self.mode = str(self.param("mode", "forbidden")).strip().lower()
        if self.mode not in ("forbidden", "required", "count"):
            raise ValueError(
                f"{self.name} rule {rule.id!r}: invalid mode {self.mode!r} "
                "(expected forbidden, required or count)"
            )
        self.per_line = as_bool(self.param("per_line", False))
        self.fix_template = self.param("fix")
        self.min_count = self.param("min")
        self.max_count = self.param("max")
        self.display = self.param("pattern") or self.param("value") or ""
        self.regex = self._compile()

    # -- configuration hooks ---------------------------------------------

    def _compile(self) -> re.Pattern[str]:  # pragma: no cover - overridden
        raise NotImplementedError

    def _base_flags(self) -> int:
        """Compile flags for the pattern.

        Linters think line-by-line, so ``^``/``$`` mean start/end of *line* by
        default. Pass an explicit ``flags`` list (even ``[]``) to opt out.
        """
        if "flags" not in self.params:
            return re.MULTILINE
        return compile_flags(self.param("flags"))

    # -- execution -------------------------------------------------------

    def _default_message(self, **extra: Any) -> str:
        if self.mode == "required":
            return f"missing required {self.kind}: {self.display!r}"
        if self.mode == "count":
            expected = _range_text(self.min_count, self.max_count)
            return f"expected {expected} {self.kind} matches, found {extra.get('count', 0)}"
        return f"forbidden {self.kind} found: {self.display!r}"

    def run(self, file: SourceFile) -> Iterable[Violation]:
        matches = list(self.regex.finditer(file.text))

        if self.mode == "required":
            if not matches:
                yield self.violation(
                    file, line=1, column=1,
                    message=self._message(file, count=0),
                )
            return

        if self.mode == "count":
            count = len(matches)
            too_few = self.min_count is not None and count < int(self.min_count)
            too_many = self.max_count is not None and count > int(self.max_count)
            if too_few or too_many:
                line, column = (file.line_col(matches[0].start()) if matches else (1, 1))
                yield self.violation(
                    file, line=line, column=column,
                    message=self._message(file, count=count),
                )
            return

        # forbidden
        seen_lines = set()
        for match in matches:
            line, column = file.line_col(match.start())
            if self.per_line and line in seen_lines:
                continue
            seen_lines.add(line)
            end_line, end_column = file.line_col(match.end())
            fix = None
            if self.fix_template is not None:
                fix = TextEdit(
                    match.start(), match.end(), match.expand(str(self.fix_template))
                )
            yield self.violation(
                file,
                line=line,
                column=column,
                end_line=end_line,
                end_column=end_column,
                snippet=truncate(file.line_text(line)),
                fix=fix,
                match=match.group(0),
                message=self._message(file, match=match.group(0)),
            )

    def _message(self, file: SourceFile, **extra: Any) -> str:
        if self.rule.message:
            return self.message(**extra)
        return self._default_message(**extra)


class RegexCheck(PatternCheck):
    name = "regex"
    kind = "pattern"
    help = "Search a file for a regular expression (forbidden/required/count)."

    def _compile(self) -> re.Pattern[str]:
        pattern = self.param("pattern")
        if pattern is None or pattern == "":
            raise ValueError(f"regex rule {self.rule.id!r} requires a 'pattern'")
        pattern = str(pattern)
        if as_bool(self.param("whole_word", False)):
            pattern = rf"\b(?:{pattern})\b"
        try:
            return re.compile(pattern, self._base_flags())
        except re.error as exc:
            raise ValueError(f"regex rule {self.rule.id!r}: {exc}") from exc

    def _default_message(self, **extra: Any) -> str:
        base = super()._default_message(**extra)
        return base


class LiteralCheck(PatternCheck):
    name = "literal"
    kind = "value"
    help = "Search a file for a literal substring (forbidden/required/count)."

    def _compile(self) -> re.Pattern[str]:
        value = self.param("value")
        if value is None or value == "":
            raise ValueError(f"literal rule {self.rule.id!r} requires a 'value'")
        pattern = re.escape(str(value))
        if as_bool(self.param("whole_word", False)):
            pattern = rf"\b(?:{pattern})\b"
        flags = 0 if as_bool(self.param("case_sensitive", True)) else re.IGNORECASE
        flags |= self._base_flags()
        return re.compile(pattern, flags)


def _range_text(minimum: Any, maximum: Any) -> str:
    if minimum is not None and maximum is not None:
        return f"{minimum}-{maximum}"
    if minimum is not None:
        return f"at least {minimum}"
    if maximum is not None:
        return f"at most {maximum}"
    return "a specific number of"
