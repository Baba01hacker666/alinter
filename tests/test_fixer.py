from __future__ import annotations

from alinter.fixer import apply_edits
from alinter.models import TextEdit


def test_apply_single_edit():
    text = "hello world"
    assert apply_edits(text, [TextEdit(6, 11, "there")]) == ("hello there", 1)


def test_apply_multiple_non_overlapping():
    text = "abcabc"
    new_text, applied = apply_edits(text, [TextEdit(0, 3, "X"), TextEdit(3, 6, "Y")])
    assert new_text == "XY"
    assert applied == 2


def test_overlapping_edits_are_skipped():
    text = "abcdef"
    new_text, applied = apply_edits(text, [TextEdit(0, 4, "X"), TextEdit(2, 6, "Y")])
    assert new_text == "Xef"
    assert applied == 1


def test_out_of_range_edits_are_clamped():
    text = "abc"
    new_text, applied = apply_edits(text, [TextEdit(0, 999, "!")])
    assert new_text == "!"
    assert applied == 1


def test_deletion():
    assert apply_edits("abc", [TextEdit(1, 2, "")]) == ("ac", 1)
