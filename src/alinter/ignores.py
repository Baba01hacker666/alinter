"""Inline suppression directives.

alinter understands suppression comments in *any* language, because it just
looks for the marker text. Put a marker in a comment:

.. code-block:: python

    x = 1  # alinter: disable-line=generic/trailing-whitespace
    # alinter: disable-next-line=python/no-print
    print("hi")
    # alinter: disable-file=generic/line-ending

Supported directives (``alinter:`` or ``alinter-`` prefix):

``disable`` / ``disable-file`` / ``ignore-file``
    suppress the listed rules (or all rules when none listed) for the file.
``disable-next-line``
    suppress the listed rules on the following line.
``disable-line``
    suppress the listed rules on the same line.
``enable``
    cancel an earlier file-level ``disable``.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field

DIRECTIVE_RE = re.compile(
    r"\balinter[-:]\s*"
    r"(disable-file|ignore-file|disable-next-line|disable-line|disable|enable)\b"
    r"[ \t]*(?:[=:]?[ \t]*)(?P<ids>[A-Za-z0-9_\-/,\. \t]*)?",
    re.IGNORECASE,
)

ALL = "*"


def _parse_ids(raw: str | None) -> set[str]:
    if not raw:
        return {ALL}
    ids = {token for token in re.split(r"[,\s]+", raw.strip()) if token}
    return ids or {ALL}


@dataclass
class Suppressions:
    """Per-file suppression state."""

    file_ids: set[str] = field(default_factory=set)
    lines: dict[int, set[str]] = field(default_factory=dict)
    directives: int = 0

    def add_file(self, ids: Iterable[str]) -> None:
        self.file_ids.update(ids)
        self.directives += 1

    def remove_file(self, ids: Iterable[str]) -> None:
        for rule_id in ids:
            self.file_ids.discard(rule_id)

    def add_line(self, line: int, ids: Iterable[str]) -> None:
        self.lines.setdefault(line, set()).update(ids)
        self.directives += 1

    def is_suppressed(self, rule_id: str, line: int | None) -> bool:
        if ALL in self.file_ids or rule_id in self.file_ids:
            return True
        if line is not None:
            ids = self.lines.get(line)
            if ids and (ALL in ids or rule_id in ids):
                return True
        return False


def parse_suppressions(text: str) -> Suppressions:
    """Extract suppression directives from source text."""
    state = Suppressions()
    for number, raw in enumerate(text.splitlines(), 1):
        for match in DIRECTIVE_RE.finditer(raw):
            directive = match.group(1).lower()
            ids = _parse_ids(match.group("ids"))
            if directive == "disable-line":
                state.add_line(number, ids)
            elif directive == "disable-next-line":
                state.add_line(number + 1, ids)
            elif directive in ("disable", "disable-file", "ignore-file"):
                state.add_file(ids)
            elif directive == "enable":
                state.remove_file(ids)
    return state
