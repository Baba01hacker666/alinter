"""Line length checks."""

from __future__ import annotations

import re
from collections.abc import Iterable

from ..models import SourceFile, Violation
from ..utils import as_bool, truncate
from .base import Check

_URL_RE = re.compile(r"https?://\S+")


class MaxLineLengthCheck(Check):
    name = "max-line-length"
    fixable = False
    default_message = "line too long ({length} > {limit})"
    help = "Report lines longer than a configured limit."

    def __init__(self, rule) -> None:
        super().__init__(rule)
        length = self.param("length")
        if length is None:
            raise ValueError(f"{rule.id!r}: 'length' is required")
        try:
            self.length = int(length)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{rule.id!r}: 'length' must be an integer") from exc
        if self.length <= 0:
            raise ValueError(f"{rule.id!r}: 'length' must be positive")
        self.ignore_urls = as_bool(self.param("ignore_urls", False))
        self.tab_width: int | None = self.param("tab_width")
        if self.tab_width is not None:
            self.tab_width = int(self.tab_width)
        ignore_regex = self.param("ignore_regex")
        self.ignore_regex = re.compile(str(ignore_regex)) if ignore_regex else None

    def _measure(self, content: str) -> int:
        if self.tab_width is not None:
            return len(content.expandtabs(self.tab_width))
        return len(content)

    def run(self, file: SourceFile) -> Iterable[Violation]:
        for number, raw in enumerate(file.split_lines_keepends(), 1):
            content = raw.rstrip("\r\n")
            length = self._measure(content)
            if length <= self.length:
                continue
            if self.ignore_urls and _URL_RE.search(content):
                continue
            if self.ignore_regex is not None and self.ignore_regex.search(content):
                continue
            yield self.violation(
                file,
                line=number,
                column=self.length + 1,
                snippet=truncate(content),
                message=self.message(length=length, limit=self.length, line=number),
            )
