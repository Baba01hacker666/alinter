from __future__ import annotations

from alinter.ignores import parse_suppressions


def test_disable_line():
    state = parse_suppressions("x = 1  # alinter: disable-line=some/rule\n")
    assert state.is_suppressed("some/rule", 1)
    assert not state.is_suppressed("other/rule", 1)


def test_disable_next_line():
    text = "# alinter: disable-next-line=a/b\ncode\nmore\n"
    state = parse_suppressions(text)
    assert state.is_suppressed("a/b", 2)
    assert not state.is_suppressed("a/b", 3)


def test_disable_file_and_enable():
    text = "# alinter: disable-file=a/b\ncode\n# alinter: enable=a/b\nmore\n"
    state = parse_suppressions(text)
    assert not state.is_suppressed("a/b", 4)


def test_disable_all_rules():
    state = parse_suppressions("// alinter: disable-file\n")
    assert state.is_suppressed("anything", None)
    assert state.is_suppressed("anything", 10)


def test_bare_disable_is_file_level():
    state = parse_suppressions("# alinter: disable\ncode\n")
    assert state.is_suppressed("a/b", 2)


def test_ignore_file_alias():
    state = parse_suppressions("# alinter: ignore-file=x/y\n")
    assert state.is_suppressed("x/y", 5)


def test_dash_prefix_and_case_insensitive():
    state = parse_suppressions("# ALINTER-disable-line=x/y\n")
    assert state.is_suppressed("x/y", 1)
