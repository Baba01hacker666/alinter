from __future__ import annotations

import pytest

from alinter.utils import (
    ConfigError,
    as_bool,
    as_list,
    as_str_list,
    detect_encoding,
    deep_merge,
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
