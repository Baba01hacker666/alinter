from __future__ import annotations

import pytest

from alinter.utils import ConfigError


def test_structure_valid_json(build_check, source_factory):
    check = build_check({"id": "r", "type": "structure", "format": "json"})
    assert list(check.run(source_factory('{"a": 1}'))) == []
    assert list(check.run(source_factory("{not json")))


def test_structure_require_keys(build_check, source_factory):
    check = build_check(
        {"id": "r", "type": "structure", "format": "json", "require_keys": ["version"]}
    )
    assert list(check.run(source_factory('{"name": "x"}')))
    assert list(check.run(source_factory('{"version": "1"}'))) == []


def test_structure_forbid_keys(build_check, source_factory):
    check = build_check(
        {"id": "r", "type": "structure", "format": "json", "forbid_keys": ["secret"]}
    )
    assert list(check.run(source_factory('{"secret": 1}')))


def test_structure_paths(build_check, source_factory):
    check = build_check(
        {
            "id": "r",
            "type": "structure",
            "format": "json",
            "path_exists": ["a.b"],
            "path_absent": ["a.c"],
        }
    )
    assert list(check.run(source_factory('{"a": {"b": 1}}'))) == []
    assert list(check.run(source_factory('{"a": {"c": 1}}')))


def test_structure_yaml_and_toml(build_check, source_factory):
    yaml_check = build_check({"id": "r", "type": "structure", "format": "yaml"})
    assert list(yaml_check.run(source_factory("a: 1\n"))) == []
    assert list(yaml_check.run(source_factory("a: [1, 2\n")))
    toml_check = build_check({"id": "r", "type": "structure", "format": "toml"})
    assert list(toml_check.run(source_factory("a = 1\n"))) == []
    assert list(toml_check.run(source_factory("a = \n")))


def test_structure_ini_and_xml(build_check, source_factory):
    ini_check = build_check({"id": "r", "type": "structure", "format": "ini"})
    assert list(ini_check.run(source_factory("[s]\nk = v\n"))) == []
    xml_check = build_check({"id": "r", "type": "structure", "format": "xml"})
    assert list(xml_check.run(source_factory("<a><b/></a>"))) == []
    assert list(xml_check.run(source_factory("<a><b></a>")))


def test_structure_unknown_format(build_check):
    with pytest.raises(ConfigError):
        build_check({"id": "r", "type": "structure", "format": "nope"})


def test_command_disabled_by_default(build_check, source_factory):
    check = build_check({"id": "r", "type": "command", "command": "false"})
    assert list(check.run(source_factory("x"))) == []


def test_command_enabled(build_check, source_factory):
    rule = {
        "id": "r",
        "type": "command",
        "command": "true",
        "expect_exit": 0,
        "_allow_commands": True,
    }
    check = build_check(rule)
    assert list(check.run(source_factory("x", rel="f.txt"))) == []


def test_command_failure(build_check, source_factory):
    rule = {
        "id": "r",
        "type": "command",
        "command": "false",
        "expect_exit": 0,
        "_allow_commands": True,
    }
    check = build_check(rule)
    violations = list(check.run(source_factory("x", rel="f.txt")))
    assert len(violations) == 1
