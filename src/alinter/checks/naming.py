"""File-name checks."""

from __future__ import annotations

import re
from typing import Iterable

from ..models import SourceFile, Violation
from ..utils import as_str_list
from .base import Check


class FilenameCheck(Check):
    name = "filename"
    fixable = False
    singleton = True
    default_message = "file name does not match the rule: {name}"
    help = "Match the base file name against a pattern and/or allowed extensions."

    def __init__(self, rule) -> None:
        super().__init__(rule)
        pattern = self.param("pattern")
        self.pattern = re.compile(str(pattern)) if pattern else None
        self.mode = str(self.param("mode", "forbidden")).strip().lower()
        if self.mode not in ("forbidden", "required"):
            raise ValueError(f"{rule.id!r}: 'mode' must be 'forbidden' or 'required'")
        if self.pattern is None and not self.param("extension"):
            raise ValueError(f"{rule.id!r}: 'pattern' or 'extension' is required")
        self.extensions = [
            ext.lower() if ext.startswith(".") else "." + ext.lower()
            for ext in as_str_list(self.param("extension"))
        ]

    def run(self, file: SourceFile) -> Iterable[Violation]:
        if self.pattern is not None:
            found = self.pattern.search(file.filename) is not None
            if self.mode == "forbidden" and found:
                yield self.violation(
                    file, line=1, column=1,
                    message=self.message(name=file.filename),
                )
            elif self.mode == "required" and not found:
                yield self.violation(
                    file, line=1, column=1,
                    message=self.message(name=file.filename),
                )
        if self.extensions and file.extension not in self.extensions:
            yield self.violation(
                file, line=1, column=1,
                message=self.message(name=file.filename, extension=file.extension),
            )
