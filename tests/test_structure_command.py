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


def test_structure_requires_format(build_check):
    with pytest.raises(ConfigError):
        build_check({"id": "r", "type": "structure"})


def test_structure_require_keys_on_non_mapping(build_check, source_factory):
    check = build_check(
        {"id": "r", "type": "structure", "format": "json", "require_keys": ["a"]}
    )
    violations = list(check.run(source_factory("[1, 2, 3]")))
    assert len(violations) == 1
    assert "mapping" in violations[0].message


def test_structure_path_absent_when_present(build_check, source_factory):
    check = build_check(
        {"id": "r", "type": "structure", "format": "json", "path_absent": ["a.b"]}
    )
    assert list(check.run(source_factory('{"a": {"b": 1}}')))
    assert list(check.run(source_factory('{"a": {}}'))) == []


def test_structure_list_index_paths(build_check, source_factory):
    check = build_check(
        {"id": "r", "type": "structure", "format": "json", "path_exists": ["a.0.b"]}
    )
    assert list(check.run(source_factory('{"a": [{"b": 1}]}'))) == []
    assert list(check.run(source_factory('{"a": []}')))


def test_structure_xml_rejects_entity_expansion(build_check, source_factory):
    pytest.importorskip("defusedxml")
    check = build_check({"id": "r", "type": "structure", "format": "xml"})
    bomb = (
        '<?xml version="1.0"?>'
        '<!DOCTYPE lolz [<!ENTITY lol "lol"><!ENTITY lol2 "&lol;&lol;">]>'
        "<lolz>&lol2;</lolz>"
    )
    assert list(check.run(source_factory(bomb)))


def test_command_timeout(build_check, source_factory):
    check = build_check(
        {
            "id": "r",
            "type": "command",
            "command": "sleep 5",
            "timeout": 0.2,
            "_allow_commands": True,
        }
    )
    violations = list(check.run(source_factory("x", rel="f.txt")))
    assert len(violations) == 1
    assert "timeout" in violations[0].message


def test_command_oserror_is_reported(build_check, source_factory):
    check = build_check(
        {
            "id": "r",
            "type": "command",
            "command": "definitely-not-a-real-binary-xyz",
            "shell": False,
            "_allow_commands": True,
        }
    )
    violations = list(check.run(source_factory("x", rel="f.txt")))
    assert len(violations) == 1


def test_command_expect_exit_match(build_check, source_factory):
    check = build_check(
        {
            "id": "r",
            "type": "command",
            "command": "exit 3",
            "expect_exit": 3,
            "_allow_commands": True,
        }
    )
    assert list(check.run(source_factory("x", rel="f.txt"))) == []


def test_command_renders_path_placeholders(build_check, source_factory):
    check = build_check(
        {
            "id": "r",
            "type": "command",
            "command": "test -n '{rel_path}'",
            "_allow_commands": True,
        }
    )
    assert list(check.run(source_factory("x", rel="f.txt"))) == []


def test_command_reports_oserror_for_bad_workdir(build_check, source_factory):
    check = build_check(
        {
            "id": "r",
            "type": "command",
            "command": "true",
            "_allow_commands": True,
        }
    )
    # A path in a non-existent directory makes the working directory invalid.
    assert list(check.run(source_factory("x", rel="ghost/dir/f.txt")))
