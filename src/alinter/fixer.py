"""Apply text edits produced by fixable checks."""

from __future__ import annotations

from collections.abc import Iterable

from .models import TextEdit


def apply_edits(text: str, edits: Iterable[TextEdit]) -> tuple[str, int]:
    """Apply ``edits`` to ``text``, skipping overlapping ones.

    Returns ``(new_text, applied_count)``. Edits are applied left to right;
    an edit that starts before the previous edit finished is dropped (the fix
    loop will pick it up on the next pass).
    """
    ordered: list[TextEdit] = sorted(edits, key=lambda edit: (edit.start, edit.end))
    pieces: list[str] = []
    position = 0
    applied = 0
    length = len(text)
    for edit in ordered:
        start = max(0, min(edit.start, length))
        end = max(start, min(edit.end, length))
        if start < position:
            continue
        pieces.append(text[position:start])
        pieces.append(edit.replacement)
        position = end
        applied += 1
    pieces.append(text[position:])
    return "".join(pieces), applied
