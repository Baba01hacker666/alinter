from __future__ import annotations

import pytest

from alinter.models import (
    LintResult,
    Rule,
    Severity,
    SourceFile,
    TextEdit,
    Violation,
)


def test_severity_coerce_accepts_aliases():
    assert Severity.coerce("error") is Severity.ERROR
    assert Severity.coerce("WARN") is Severity.WARNING
    assert Severity.coerce("note") is Severity.INFO
    assert Severity.coerce("disabled") is Severity.OFF
    assert Severity.coerce(2) is Severity.ERROR
    assert Severity.coerce(Severity.INFO) is Severity.INFO


def test_severity_coerce_bools_from_yaml():
    # YAML parses bare `off`/`no` as False and `on`/`yes` as True.
    assert Severity.coerce(False) is Severity.OFF
    assert Severity.coerce(True) is Severity.ERROR
    assert Severity.coerce(None) is Severity.ERROR


def test_severity_coerce_rejects_unknown():
    with pytest.raises(ValueError):
        Severity.coerce("loud")


def test_severity_rank_and_active():
    assert Severity.ERROR.rank > Severity.WARNING.rank > Severity.INFO.rank > Severity.OFF.rank
    assert Severity.ERROR.is_active is True
    assert Severity.OFF.is_active is False


def test_text_edit_as_dict():
    edit = TextEdit(1, 2, "x")
    assert edit.as_dict() == {"start": 1, "end": 2, "replacement": "x"}


def test_rule_param_and_scope():
    rule = Rule(id="r", type="literal", params={"value": "x"})
    assert rule.param("value") == "x"
    assert rule.param("missing", "fallback") == "fallback"
    assert rule.scoped_to("a.py", "python") is True


def test_rule_scope_respects_files_and_exclude():
    rule = Rule(id="r", type="literal", files=("**/*.py",), exclude=("vendor/**",))
    assert rule.matches_path_language("src/a.py", "python") is True
    assert rule.matches_path_language("src/a.js", "javascript") is False
    assert rule.matches_path_language("vendor/a.py", "python") is False


def test_rule_scope_respects_languages():
    rule = Rule(id="r", type="literal", languages=("python",))
    assert rule.matches_path_language("a.py", "python") is True
    assert rule.matches_path_language("a.txt", None) is False
    assert rule.matches_path_language("a.rb", "ruby") is False


def test_rule_disabled_and_off_are_not_scoped():
    assert Rule(id="r", type="literal", enabled=False).scoped_to("a.py", "python") is False
    assert Rule(id="r", type="literal", severity=Severity.OFF).scoped_to("a.py", "python") is False


def test_rule_as_dict():
    rule = Rule(id="r", type="regex", tags=("style",), params={"pattern": "x"})
    data = rule.as_dict()
    assert data["id"] == "r"
    assert data["tags"] == ["style"]
    assert data["params"] == {"pattern": "x"}


def test_source_file_properties():
    source = SourceFile(path="/tmp/a.py", rel_path="src/a.py", text="one\ntwo\n")
    assert source.filename == "a.py"
    assert source.extension == ".py"
    assert source.lines == ["one", "two"]
    assert source.split_lines_keepends() == ["one\n", "two\n"]


def test_source_file_line_col():
    source = SourceFile(path="a", rel_path="a", text="ab\ncd\n")
    assert source.line_col(0) == (1, 1)
    assert source.line_col(3) == (2, 1)
    # Out-of-range offsets are clamped to the end of the text.
    assert source.line_col(999) == (3, 1)


def test_source_file_line_text():
    source = SourceFile(path="a", rel_path="a", text="first\nsecond\n")
    assert source.line_text(1) == "first"
    assert source.line_text(99) == ""


def test_violation_location_variants():
    assert Violation(rule_id="r", message="m", path="a.py").location == "a.py"
    assert Violation(rule_id="r", message="m", path="a.py", line=2).location == "a.py:2"
    v = Violation(rule_id="r", message="m", path="a.py", line=2, column=3)
    assert v.location == "a.py:2:3"


def test_violation_as_dict_and_sort_key():
    v = Violation(
        rule_id="r",
        message="m",
        path="a.py",
        line=1,
        column=1,
        rule_type="regex",
        tags=("style",),
        fix=TextEdit(0, 1, "x"),
    )
    data = v.as_dict()
    assert data["type"] == "regex"
    assert data["tags"] == ["style"]
    assert data["fixable"] is True
    assert v.fixable is True
    assert v.sort_key() == ("a.py", 1, 1, "r")


def test_lint_result_counts_and_has_errors():
    result = LintResult(
        violations=[
            Violation(rule_id="a", message="m", path="x", severity=Severity.ERROR),
            Violation(rule_id="b", message="m", path="x", severity=Severity.WARNING),
        ]
    )
    assert result.has_errors is True
    counts = result.counts()
    assert counts["error"] == 1
    assert counts["warning"] == 1
    assert counts["info"] == 0
