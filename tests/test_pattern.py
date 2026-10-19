from __future__ import annotations

from alinter.fixer import apply_edits


def test_regex_forbidden_reports_each_match(build_check, source_factory):
    check = build_check({"id": "r", "type": "regex", "pattern": r"\bfoo\b"})
    source = source_factory("foo bar\nbaz foo\n")
    violations = list(check.run(source))
    assert [v.line for v in violations] == [1, 2]
    assert violations[0].column == 1
    assert "foo" in violations[0].message


def test_regex_multiline_is_default(build_check, source_factory):
    check = build_check({"id": "r", "type": "regex", "pattern": "^print"})
    assert list(check.run(source_factory("x\nprint(1)\n")))


def test_regex_explicit_empty_flags_disables_multiline(build_check, source_factory):
    check = build_check({"id": "r", "type": "regex", "pattern": "^print", "flags": []})
    assert list(check.run(source_factory("x\nprint(1)\n"))) == []


def test_regex_required(build_check, source_factory):
    check = build_check({"id": "r", "type": "regex", "pattern": r"license", "mode": "required"})
    assert list(check.run(source_factory("no header here\n")))
    assert list(check.run(source_factory("# license\n"))) == []


def test_regex_count(build_check, source_factory):
    check = build_check(
        {"id": "r", "type": "regex", "pattern": r"^# ", "mode": "count", "max": 1}
    )
    assert list(check.run(source_factory("# one\n# two\n")))
    assert list(check.run(source_factory("# one\n"))) == []


def test_regex_per_line(build_check, source_factory):
    check = build_check({"id": "r", "type": "regex", "pattern": r"x", "per_line": True})
    violations = list(check.run(source_factory("x x x\n")))
    assert len(violations) == 1


def test_regex_whole_word(build_check, source_factory):
    check = build_check({"id": "r", "type": "regex", "pattern": "foo", "whole_word": True})
    assert list(check.run(source_factory("foobar\n"))) == []
    assert list(check.run(source_factory("a foo b\n")))


def test_regex_fix_produces_edit(build_check, source_factory):
    check = build_check({"id": "r", "type": "regex", "pattern": "colour", "fix": "color"})
    source = source_factory("the colour is nice\n")
    violations = list(check.run(source))
    assert violations[0].fix is not None
    new_text, applied = apply_edits(source.text, [v.fix for v in violations])
    assert applied == 1
    assert new_text == "the color is nice\n"


def test_regex_invalid_pattern(build_check):
    import pytest

    from alinter.utils import ConfigError

    with pytest.raises(ConfigError):
        build_check({"id": "r", "type": "regex", "pattern": "("})


def test_literal_case_insensitive(build_check, source_factory):
    check = build_check(
        {"id": "r", "type": "literal", "value": "todo", "case_sensitive": False}
    )
    assert list(check.run(source_factory("TODO: fix\n")))


def test_literal_forbidden_default(build_check, source_factory):
    check = build_check({"id": "r", "type": "literal", "value": "FIXME"})
    assert list(check.run(source_factory("a FIXME b\n")))
    assert list(check.run(source_factory("nothing\n"))) == []
