"""Whitespace checks: trailing whitespace and tab characters."""

from __future__ import annotations

from typing import Iterable

from ..models import SourceFile, TextEdit, Violation
from ..utils import truncate
from .base import Check


class TrailingWhitespaceCheck(Check):
    name = "no-trailing-whitespace"
    fixable = True
    singleton = True
    default_message = "trailing whitespace"
    help = "Report (and optionally strip) whitespace at the end of lines."

    def run(self, file: SourceFile) -> Iterable[Violation]:
        offset = 0
        for number, raw in enumerate(file.split_lines_keepends(), 1):
            content = raw.rstrip("\r\n")
            stripped = content.rstrip(" \t")
            if len(stripped) != len(content):
                start = offset + len(stripped)
                end = offset + len(content)
                yield self.violation(
                    file,
                    line=number,
                    column=len(stripped) + 1,
                    snippet=truncate(content),
                    fix=TextEdit(start, end, ""),
                    message=self.message(),
                )
            offset += len(raw)


class NoTabsCheck(Check):
    name = "no-tabs"
    fixable = False
    singleton = True
    help = "Report tab characters (anywhere, or only as indentation)."

    def __init__(self, rule) -> None:
        super().__init__(rule)
        self.mode = str(self.param("mode", "any")).strip().lower()
        if self.mode not in ("any", "leading"):
            raise ValueError(
                f"{rule.id!r}: invalid mode {self.mode!r} (expected any or leading)"
            )
        self.default_message = (
            "tab used for indentation" if self.mode == "leading" else "tab character found"
        )

    def run(self, file: SourceFile) -> Iterable[Violation]:
        for number, line in enumerate(file.lines, 1):
            if self.mode == "leading":
                stripped = line[: len(line) - len(line.lstrip(" \t"))]
                if "\t" in stripped:
                    yield self.violation(
                        file,
                        line=number,
                        column=1,
                        snippet=truncate(line),
                        message=self.message(line=number),
                    )
            elif "\t" in line:
                column = line.index("\t") + 1
                yield self.violation(
                    file,
                    line=number,
                    column=column,
                    snippet=truncate(line),
                    message=self.message(line=number),
                )
