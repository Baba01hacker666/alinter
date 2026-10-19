from __future__ import annotations

import pytest

from alinter.utils import (
    ConfigError,
    as_bool,
    as_list,
    as_str_list,
    deep_merge,
    detect_encoding,
    glob_to_regex,
    is_probably_binary,
    normalize_path,
    parse_data,
    path_matches,
    plural,
    truncate,
)


@pytest.mark.parametrize(
    "path,pattern,expected",
    [
        ("a.py", "**/*.py", True),
        ("src/deep/a.py", "**/*.py", True),
        ("a.js", "**/*.py", False),
        ("src/api/x.py", "src/api/**", True),
        ("src/lib/x.py", "src/api/**", False),
        ("a.py", "*.py", True),
        ("deep/a.py", "*.py", True),
        ("a.py", "a.py", True),
        ("deep/a.py", "a.py", True),
        ("vendor/x/y.js", "vendor", True),
        ("src/vendor/x.js", "vendor", True),
        ("src/keep/x.js", "vendor", False),
        ("node_modules/a.js", "**/node_modules/**", True),
        ("src/node_modules/a.js", "**/node_modules/**", True),
    ],
)
def test_path_matches(path, pattern, expected):
    assert path_matches(path, [pattern]) is expected


def test_glob_trailing_slash_matches_contents():
    assert path_matches("build/out.js", ["build/"])


def test_normalize_path():
    assert normalize_path("./a\\b/./c") == "a/b/c"


def test_deep_merge():
    base = {"a": {"b": 1, "c": 2}, "d": [1]}
    override = {"a": {"c": 3}, "d": [2, 3]}
    assert deep_merge(base, override) == {"a": {"b": 1, "c": 3}, "d": [2, 3]}


def test_parse_data_yaml_and_json():
    assert parse_data("a: 1\n", "yaml") == {"a": 1}
    assert parse_data('{"a": 1}', "json") == {"a": 1}


def test_parse_data_toml():
    assert parse_data('a = 1\n', "toml") == {"a": 1}


def test_parse_data_error():
    with pytest.raises(ConfigError):
        parse_data("{ not json", "json")


def test_detect_encoding_bom_and_fallback():
    encoding, bom = detect_encoding("\ufeffhello".encode("utf-8"))
    assert encoding == "utf-8-sig"
    assert bom is True
    encoding, bom = detect_encoding(b"\xff\xfe\x00a")
    assert encoding in ("utf-16", "latin-1")


def test_is_probably_binary():
    assert is_probably_binary(b"abc\x00def") is True
    assert is_probably_binary(b"plain text") is False


def test_coercions():
    assert as_bool("yes") is True
    assert as_bool(None, True) is True
    assert as_list("x") == ["x"]
    assert as_str_list([1, 2]) == ["1", "2"]


def test_truncate_and_plural():
    assert truncate("a" * 200, 10).endswith("\u2026")
    assert plural(1, "file") == "1 file"
    assert plural(2, "file") == "2 files"


def test_glob_invalid_class_is_escaped():
    # A malformed class should not raise.
    assert glob_to_regex("[abc") is not None


def test_glob_question_mark_and_negated_class():
    assert path_matches("a.py", ["a?py"])
    assert path_matches("a.py", ["a[!x]py"])
    assert not path_matches("axpy", ["a[!x]py"])


def test_glob_leading_dot_slash_is_ignored():
    assert path_matches("src/a.py", ["./src/**"])


def test_path_matches_empty_patterns_is_false():
    assert path_matches("a.py", []) is False


def test_normalize_path_dot_is_empty():
    assert normalize_path(".") == ""


def test_matches_any_name():
    from alinter.utils import matches_any_name

    assert matches_any_name("src/vendor/a.js", ["vendor", "node_modules"])
    assert not matches_any_name("src/app/a.js", ["vendor"])
    assert matches_any_name("a.js", []) is False


def test_deep_merge_non_mapping_override_wins():
    assert deep_merge({"a": 1}, 5) == 5
    assert deep_merge(5, {"a": 1}) == {"a": 1}


def test_format_for_path():
    from alinter.utils import format_for_path

    assert format_for_path("x.yaml") == "yaml"
    assert format_for_path("x.yml") == "yaml"
    assert format_for_path("x.json") == "json"
    assert format_for_path("x.toml") == "toml"
    assert format_for_path("x.unknown") == "yaml"


def test_parse_data_unsupported_format():
    with pytest.raises(ConfigError):
        parse_data("x", "xml")


def test_parse_data_yaml_without_pyyaml(monkeypatch):
    from alinter import utils

    monkeypatch.setattr(utils, "yaml", None)
    assert utils.have_yaml() is False
    with pytest.raises(ConfigError):
        parse_data("a: 1", "yaml")


def test_parse_data_toml_without_tomli(monkeypatch):
    from alinter import utils

    monkeypatch.setattr(utils, "_toml", None)
    with pytest.raises(ConfigError):
        parse_data("a = 1", "toml")


def test_read_text_roundtrip(tmp_path):
    from alinter.utils import read_text

    path = tmp_path / "bom.txt"
    path.write_bytes("\ufeffhello".encode("utf-8"))
    text, encoding, has_bom = read_text(path)
    # utf-8-sig decoding consumes the BOM, and has_bom records that it was there.
    assert text == "hello"
    assert encoding == "utf-8-sig"
    assert has_bom is True


def test_color_disabled_and_enabled():
    from alinter.utils import Color

    assert Color(False).paint("x", "red") == "x"
    assert Color(False)("x", "red") == "x"
    # No styles is a no-op even when enabled.
    assert Color(True).paint("x") == "x"
    painted = Color(True).paint("x", "bold")
    assert painted.startswith("\033[") and painted.endswith("\033[0m")


def test_color_auto_respects_env(monkeypatch):
    from alinter.utils import Color

    monkeypatch.setenv("NO_COLOR", "1")
    assert Color().enabled is False
    monkeypatch.delenv("NO_COLOR")
    monkeypatch.setenv("FORCE_COLOR", "1")
    assert Color().enabled is True


def test_truncate_short_and_plural_custom():
    assert truncate("short", 10) == "short"
    assert truncate("line\r\n", 10) == "line"
    assert plural(2, "child", "children") == "2 children"


def test_as_bool_numeric_and_strings():
    assert as_bool(1) is True
    assert as_bool(0) is False
    assert as_bool("no") is False
    assert as_bool("on") is True


def test_detect_encoding_preferred():
    encoding, bom = detect_encoding(b"caf\xe9", preferred="latin-1")
    assert encoding == "latin-1"
    assert bom is False
