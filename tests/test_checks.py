from __future__ import annotations

from alinter.fixer import apply_edits


def test_trailing_whitespace_and_fix(build_check, source_factory):
    check = build_check({"id": "r", "type": "no-trailing-whitespace"})
    source = source_factory("a  \nb\t\nc\n")
    violations = list(check.run(source))
    assert [v.line for v in violations] == [1, 2]
    new_text, applied = apply_edits(source.text, [v.fix for v in violations])
    assert new_text == "a\nb\nc\n"
    assert applied == 2


def test_no_tabs_any(build_check, source_factory):
    check = build_check({"id": "r", "type": "no-tabs"})
    violations = list(check.run(source_factory("if x:\n\ty = 1\n")))
    assert len(violations) == 1
    assert violations[0].line == 2


def test_no_tabs_leading_only(build_check, source_factory):
    check = build_check({"id": "r", "type": "no-tabs", "mode": "leading"})
    assert list(check.run(source_factory("\tx\n")))
    assert list(check.run(source_factory("a\tb\n"))) == []


def test_max_line_length(build_check, source_factory):
    check = build_check({"id": "r", "type": "max-line-length", "length": 10})
    assert list(check.run(source_factory("short\n" + "x" * 20 + "\n")))
    assert list(check.run(source_factory("short\n"))) == []


def test_max_line_length_ignore_urls(build_check, source_factory):
    check = build_check({"id": "r", "type": "max-line-length", "length": 10, "ignore_urls": True})
    assert list(check.run(source_factory("https://example.com/very/long/path\n"))) == []


def test_max_line_length_ignore_regex(build_check, source_factory):
    check = build_check(
        {"id": "r", "type": "max-line-length", "length": 10, "ignore_regex": "^SKIP"}
    )
    assert list(check.run(source_factory("SKIP" + "x" * 30 + "\n"))) == []


def test_final_newline_require(build_check, source_factory):
    check = build_check({"id": "r", "type": "final-newline", "value": "require"})
    source = source_factory("no newline")
    violations = list(check.run(source))
    assert len(violations) == 1
    assert violations[0].fix.replacement == "\n"


def test_final_newline_present_ok(build_check, source_factory):
    check = build_check({"id": "r", "type": "final-newline", "value": "require"})
    assert list(check.run(source_factory("ok\n"))) == []


def test_final_newline_forbid(build_check, source_factory):
    check = build_check({"id": "r", "type": "final-newline", "value": "forbid"})
    assert list(check.run(source_factory("ok\n")))
    assert list(check.run(source_factory("ok"))) == []


def test_final_newline_exactly(build_check, source_factory):
    check = build_check({"id": "r", "type": "final-newline", "value": "require", "exactly": True})
    assert list(check.run(source_factory("ok\n\n\n")))
    assert list(check.run(source_factory("ok\n"))) == []


def test_line_ending_lf_flags_crlf(build_check, source_factory):
    check = build_check({"id": "r", "type": "line-ending", "style": "lf"})
    source = source_factory("a\r\nb\r\n")
    violations = list(check.run(source))
    assert len(violations) == 1
    new_text, _ = apply_edits(source.text, [violations[0].fix])
    assert new_text == "a\nb\n"


def test_line_ending_crlf_flags_lf(build_check, source_factory):
    check = build_check({"id": "r", "type": "line-ending", "style": "crlf"})
    assert list(check.run(source_factory("a\nb\n")))


def test_max_lines(build_check, source_factory):
    check = build_check({"id": "r", "type": "max-lines", "max": 2})
    assert list(check.run(source_factory("a\nb\nc\n")))
    assert list(check.run(source_factory("a\nb\n"))) == []


def test_max_lines_blank_lines(build_check, source_factory):
    check = build_check({"id": "r", "type": "max-lines", "max": 100, "max_blank_lines": 1})
    assert list(check.run(source_factory("a\n\n\nb\n")))
    assert list(check.run(source_factory("a\n\nb\n"))) == []


def test_max_file_size(build_check, source_factory):
    check = build_check({"id": "r", "type": "max-file-size", "max": 3})
    assert list(check.run(source_factory("abcd")))
    assert list(check.run(source_factory("ab"))) == []


def test_encoding_expect_mismatch(build_check, source_factory):
    check = build_check({"id": "r", "type": "encoding", "expect": "utf-8"})
    assert list(check.run(source_factory("x", encoding="latin-1")))
    assert list(check.run(source_factory("x", encoding="utf-8"))) == []


def test_encoding_forbid_bom(build_check, source_factory):
    check = build_check({"id": "r", "type": "encoding", "expect": "utf-8", "forbid_bom": True})
    assert list(check.run(source_factory("x", encoding="utf-8-sig", has_bom=True)))


def test_filename_pattern(build_check, source_factory):
    check = build_check(
        {"id": "r", "type": "filename", "pattern": r"^[a-z_]+\.py$", "mode": "required"}
    )
    assert list(check.run(source_factory("x\n", rel="Bad.py")))
    assert list(check.run(source_factory("x\n", rel="good_name.py"))) == []


def test_filename_extension(build_check, source_factory):
    check = build_check({"id": "r", "type": "filename", "extension": [".sh"]})
    assert list(check.run(source_factory("x\n", rel="run.bash")))
    assert list(check.run(source_factory("x\n", rel="run.sh"))) == []


def test_message_template_falls_back_on_unknown_placeholder(build_check, source_factory):
    check = build_check(
        {"id": "r", "type": "literal", "value": "x", "message": "hi {nope} there"}
    )
    (violation,) = list(check.run(source_factory("x\n")))
    assert violation.message == "hi {nope} there"


def test_message_uses_default_when_unset(build_check, source_factory):
    check = build_check({"id": "r", "type": "no-trailing-whitespace"})
    (violation,) = list(check.run(source_factory("x  \n")))
    assert violation.message == "trailing whitespace"


def test_max_line_length_requires_length(build_check):
    import pytest

    from alinter.utils import ConfigError

    with pytest.raises(ConfigError):
        build_check({"id": "r", "type": "max-line-length"})


def test_max_line_length_rejects_non_positive(build_check):
    import pytest

    from alinter.utils import ConfigError

    with pytest.raises(ConfigError):
        build_check({"id": "r", "type": "max-line-length", "length": 0})


def test_max_line_length_tab_width(build_check, source_factory):
    check = build_check(
        {"id": "r", "type": "max-line-length", "length": 8, "tab_width": 4}
    )
    # Three tabs expand to 12 columns, over the limit of 8.
    assert list(check.run(source_factory("\t\t\tx\n")))


def test_final_newline_empty_file_is_ok(build_check, source_factory):
    check = build_check({"id": "r", "type": "final-newline"})
    assert list(check.run(source_factory(""))) == []


def test_line_ending_crlf_normalizes_mixed(build_check, source_factory):
    check = build_check({"id": "r", "type": "line-ending", "style": "crlf"})
    (violation,) = list(check.run(source_factory("a\nb\r\n")))
    new_text, _ = apply_edits("a\nb\r\n", [violation.fix])
    assert new_text == "a\r\nb\r\n"


def test_line_ending_invalid_style(build_check):
    import pytest

    from alinter.utils import ConfigError

    with pytest.raises(ConfigError):
        build_check({"id": "r", "type": "line-ending", "style": "sideways"})


def test_max_lines_without_counting_blank(build_check, source_factory):
    check = build_check(
        {"id": "r", "type": "max-lines", "max": 2, "count_blank": False}
    )
    assert list(check.run(source_factory("a\n\n\nb\nc\n")))
    assert list(check.run(source_factory("a\n\n\nb\n"))) == []


def test_no_tabs_invalid_mode(build_check):
    import pytest

    from alinter.utils import ConfigError

    with pytest.raises(ConfigError):
        build_check({"id": "r", "type": "no-tabs", "mode": "middle"})


def test_encoding_no_bom_is_clean(build_check, source_factory):
    check = build_check({"id": "r", "type": "encoding", "expect": "utf-8", "forbid_bom": True})
    assert list(check.run(source_factory("plain", encoding="utf-8", has_bom=False))) == []


def test_filename_forbidden_mode(build_check, source_factory):
    check = build_check(
        {"id": "r", "type": "filename", "pattern": r"^test_", "mode": "forbidden"}
    )
    assert list(check.run(source_factory("x\n", rel="test_thing.py")))
    assert list(check.run(source_factory("x\n", rel="thing.py"))) == []


def test_filename_extension_without_dot(build_check, source_factory):
    check = build_check({"id": "r", "type": "filename", "extension": ["txt"]})
    assert list(check.run(source_factory("x\n", rel="a.md")))
    assert list(check.run(source_factory("x\n", rel="a.txt"))) == []


def test_filename_requires_pattern_or_extension(build_check):
    import pytest

    from alinter.utils import ConfigError

    with pytest.raises(ConfigError):
        build_check({"id": "r", "type": "filename"})
