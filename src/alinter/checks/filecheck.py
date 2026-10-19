"""Whole-file checks: newline, line endings, size, length and encoding."""

from __future__ import annotations

from collections.abc import Iterable

from ..models import SourceFile, TextEdit, Violation
from ..utils import as_bool
from .base import Check


class FinalNewlineCheck(Check):
    name = "final-newline"
    fixable = True
    singleton = True
    help = "Require (or forbid) a trailing newline at end of file."

    def __init__(self, rule) -> None:
        super().__init__(rule)
        value = str(self.param("value", "require")).strip().lower()
        if value in ("require", "required", "require-one", "yes", "true"):
            self.value = "require"
            self.default_message = "missing final newline"
        elif value in ("forbid", "forbidden", "no", "false", "none"):
            self.value = "forbid"
            self.default_message = "file should not end with a newline"
        else:
            raise ValueError(
                f"{rule.id!r}: 'value' must be 'require' or 'forbid', got {value!r}"
            )
        self.exactly = as_bool(self.param("exactly", False))

    def run(self, file: SourceFile) -> Iterable[Violation]:
        text = file.text
        if text == "":
            return
        end_newlines = len(text) - len(text.rstrip("\r\n"))
        if self.value == "require":
            if end_newlines == 0:
                yield self.violation(
                    file,
                    line=len(file.lines),
                    column=1,
                    fix=TextEdit(len(text), len(text), "\n"),
                    message=self.message(),
                )
            elif self.exactly and end_newlines > 1:
                yield self.violation(
                    file,
                    line=len(file.lines),
                    column=1,
                    fix=TextEdit(len(text) - end_newlines + 1, len(text), ""),
                    message="file must end with exactly one newline",
                )
        else:  # forbid
            if end_newlines > 0:
                yield self.violation(
                    file,
                    line=len(file.lines),
                    column=1,
                    fix=TextEdit(len(text) - end_newlines, len(text), ""),
                    message=self.message(),
                )


class LineEndingCheck(Check):
    name = "line-ending"
    fixable = True
    singleton = True
    help = "Enforce LF or CRLF line endings."

    def __init__(self, rule) -> None:
        super().__init__(rule)
        style = str(self.param("style", "lf")).strip().lower()
        if style in ("lf", "unix", "\n"):
            self.style = "lf"
            self.default_message = "file uses CRLF line endings; expected LF"
        elif style in ("crlf", "windows", "dos", "\r\n"):
            self.style = "crlf"
            self.default_message = "file uses LF line endings; expected CRLF"
        else:
            raise ValueError(f"{rule.id!r}: 'style' must be 'lf' or 'crlf'")
        self._reported = False

    def run(self, file: SourceFile) -> Iterable[Violation]:
        text = file.text
        if self.style == "lf":
            if "\r\n" not in text:
                return
            normalized = text.replace("\r\n", "\n").replace("\r", "\n")
            message = self.message() or "file uses CRLF line endings; expected LF"
        else:
            # Report bare LF that is not part of a CRLF pair.
            stripped = text.replace("\r\n", "")
            if "\n" not in stripped:
                return
            normalized = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")
            message = self.message() or "file uses LF line endings; expected CRLF"
        yield self.violation(
            file,
            line=1,
            column=1,
            fix=TextEdit(0, len(text), normalized),
            message=message,
        )


class MaxLinesCheck(Check):
    name = "max-lines"
    fixable = False
    default_message = "too many lines ({count} > {max})"
    help = "Limit the number of lines, optionally excluding blanks."

    def __init__(self, rule) -> None:
        super().__init__(rule)
        maximum = self.param("max")
        if maximum is None:
            raise ValueError(f"{rule.id!r}: 'max' is required")
        self.maximum = int(maximum)
        self.count_blank = as_bool(self.param("count_blank", True))
        value = self.param("max_blank_lines")
        self.max_blank_lines: int | None = int(value) if value is not None else None

    def run(self, file: SourceFile) -> Iterable[Violation]:
        lines = file.lines
        if self.count_blank:
            counted = len(lines)
            if counted > self.maximum:
                yield self.violation(
                    file,
                    line=self.maximum + 1,
                    column=1,
                    message=self.message(count=counted, limit=self.maximum, max=self.maximum),
                )
        else:
            positions = [i for i, line in enumerate(lines, 1) if line.strip()]
            counted = len(positions)
            if counted > self.maximum:
                line = positions[self.maximum] if len(positions) > self.maximum else len(lines)
                yield self.violation(
                    file,
                    line=line,
                    column=1,
                    message=self.message(count=counted, limit=self.maximum, max=self.maximum),
                )

        if self.max_blank_lines is not None:
            run = 0
            for number, line in enumerate(lines, 1):
                if line.strip() == "":
                    run += 1
                    if run == self.max_blank_lines + 1:
                        yield self.violation(
                            file,
                            line=number,
                            column=1,
                            message=f"more than {self.max_blank_lines} consecutive blank lines",
                        )
                else:
                    run = 0


class MaxFileSizeCheck(Check):
    name = "max-file-size"
    fixable = False
    singleton = True
    default_message = "file is too large ({size} bytes > {max} bytes)"
    help = "Limit file size in bytes."

    def __init__(self, rule) -> None:
        super().__init__(rule)
        maximum = self.param("max")
        if maximum is None:
            raise ValueError(f"{rule.id!r}: 'max' is required (bytes)")
        self.maximum = int(maximum)

    def run(self, file: SourceFile) -> Iterable[Violation]:
        if file.size > self.maximum:
            yield self.violation(
                file,
                message=self.message(size=file.size, max=self.maximum, limit=self.maximum),
            )


def _normalize_encoding(name: str) -> str:
    return name.strip().lower().replace("_", "-")


class EncodingCheck(Check):
    name = "encoding"
    fixable = False
    singleton = True
    default_message = "unexpected file encoding: {actual}"
    help = "Require a specific text encoding and optionally forbid a BOM."

    def __init__(self, rule) -> None:
        super().__init__(rule)
        self.expect = _normalize_encoding(str(self.param("expect", "utf-8")))
        self.forbid_bom = as_bool(self.param("forbid_bom", False))

    def run(self, file: SourceFile) -> Iterable[Violation]:
        actual = _normalize_encoding(file.encoding)
        if self.forbid_bom and file.has_bom:
            yield self.violation(
                file,
                line=1,
                column=1,
                message=self.message(actual=file.encoding),
            )
        expected_actual = actual.replace("-sig", "")
        if self.expect and expected_actual != self.expect.replace("-sig", ""):
            yield self.violation(
                file,
                message=self.message(actual=file.encoding),
            )
