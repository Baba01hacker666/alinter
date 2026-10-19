from __future__ import annotations

import pytest

from alinter.config import (
    build_rule,
    find_config_file,
    load_config,
    merge_config_dicts,
)
from alinter.models import Severity
from alinter.utils import ConfigError


def test_build_rule_extracts_params():
    rule = build_rule(
        {
            "id": "x/rule",
            "type": "regex",
            "pattern": "foo",
            "severity": "warning",
            "files": ["**/*.py"],
            "tags": ["style"],
            "custom": 1,
            "params": {"extra": True},
        }
    )
    assert rule.id == "x/rule"
    assert rule.type == "regex"
    assert rule.severity is Severity.WARNING
    assert rule.files == ("**/*.py",)
    assert rule.tags == ("style",)
    assert rule.params == {"pattern": "foo", "custom": 1, "extra": True}


def test_build_rule_requires_id_and_type():
    with pytest.raises(ConfigError):
        build_rule({"type": "regex"})
    with pytest.raises(ConfigError):
        build_rule({"id": "x"})


def test_build_rule_accepts_string_language_alias():
    rule = build_rule({"id": "x", "type": "regex", "language": "python", "pattern": "a"})
    assert rule.languages == ("python",)


def test_severity_off_disables_rule():
    rule = build_rule({"id": "x", "type": "regex", "pattern": "a", "severity": "off"})
    assert not rule.scoped_to("a.py", "python")


def test_merge_config_dicts_concatenates_lists():
    first = {"rules": [{"id": "a", "type": "regex", "pattern": "a"}]}
    second = {
        "rules": [
            {"id": "a", "type": "regex", "pattern": "a"},
            {"id": "b", "type": "regex", "pattern": "b"},
        ]
    }
    merged = merge_config_dicts(first, second)
    assert [r["id"] for r in merged["rules"]] == ["a", "b"]


def test_load_config_explicit(project):
    path = project.config(
        "version: 1\nsettings:\n  max_file_size: 10\nrules:\n"
        "  - id: x/y\n    type: regex\n    pattern: 'foo'\n    severity: info\n"
    )
    config = load_config(str(path), use_user_config=False)
    assert config.setting("max_file_size") == 10
    assert config.rule_ids() == ["x/y"]


def test_later_rule_with_same_id_wins(project):
    path = project.config(
        "rules:\n"
        "  - id: x/y\n    type: regex\n    pattern: 'a'\n    severity: error\n"
        "  - id: x/y\n    type: regex\n    pattern: 'b'\n    severity: warning\n"
    )
    config = load_config(str(path), use_user_config=False)
    assert len(config.rules) == 1
    assert config.rules[0].params["pattern"] == "b"
    assert config.rules[0].severity is Severity.WARNING


def test_load_config_pyproject(project):
    path = project.config(
        "[tool.alinter]\nauto_detect = false\n[[tool.alinter.rules]]\n"
        "id = 'x/y'\ntype = 'literal'\nvalue = 'nope'\n",
        rel="pyproject.toml",
    )
    config = load_config(str(path), use_user_config=False)
    assert config.auto_detect is False
    assert config.rule_ids() == ["x/y"]


def test_find_config_file_walks_up(project):
    project.config("rules: []")
    nested = project.root / "a" / "b"
    nested.mkdir(parents=True)
    found = find_config_file(str(nested))
    assert found is not None
    assert found.name == ".alinter.yaml"


def test_invalid_config_raises(project):
    path = project.config("rules: not-a-list\n")
    with pytest.raises(ConfigError):
        load_config(str(path), use_user_config=False)


def test_missing_config_raises():
    with pytest.raises(ConfigError):
        load_config("/nonexistent/alinter.yaml", use_user_config=False)


def test_excludes_include_defaults(project):
    path = project.config("exclude: ['**/custom/**']\n")
    config = load_config(str(path), use_user_config=False)
    excludes = config.excludes()
    assert "**/custom/**" in excludes
    assert any("node_modules" in pattern for pattern in excludes)


def test_unknown_settings_type_raises(project):
    path = project.config("settings: nope\n")
    with pytest.raises(ConfigError):
        load_config(str(path), use_user_config=False)


def test_extends_and_plugins_collected(project):
    path = project.config(
        "extends: [python]\nplugins:\n  - my.plugin\npreset_paths: [./presets]\n"
    )
    config = load_config(str(path), use_user_config=False)
    assert config.extends == ("python",)
    assert config.plugins == ("my.plugin",)
    assert config.preset_paths
    assert config.preset_paths[0].endswith("presets")


def test_build_rule_rejects_bad_shapes():
    from alinter.config import build_rule

    with pytest.raises(ConfigError):
        build_rule("just-a-string")
    with pytest.raises(ConfigError):
        build_rule(42)
    with pytest.raises(ConfigError):
        build_rule({"id": "x", "type": "regex", "pattern": "a", "params": 5})


def test_build_rule_check_alias_for_type():
    rule = build_rule({"id": "x", "check": "literal", "value": "a"})
    assert rule.type == "literal"


def test_config_setting_fallbacks():
    config = load_config(None, use_user_config=False, cwd=".")
    assert config.setting("allow_commands") is False
    assert config.setting("unknown-key", "fallback") == "fallback"


def test_find_rule():
    config = load_config(None, use_user_config=False, cwd=".")
    assert config.find_rule("does-not-exist") is None


def test_find_config_file_from_file_path(project):
    path = project.config("rules: []")
    found = find_config_file(str(path))
    assert found is not None
    assert found.name == ".alinter.yaml"


def test_has_tool_alinter_missing_file(tmp_path):
    from alinter.config import _has_tool_alinter

    assert _has_tool_alinter(tmp_path / "nope.toml") is False


def test_load_config_file_missing_raises(tmp_path):
    from alinter.config import load_config_file

    with pytest.raises(ConfigError):
        load_config_file(tmp_path / "nope.yaml")


def test_user_config_path_and_merge(project, monkeypatch, tmp_path):
    from alinter.config import user_config_path

    xdg = tmp_path / "xdg"
    (xdg / "alinter").mkdir(parents=True)
    (xdg / "alinter" / "config.yaml").write_text(
        "auto_detect: false\n", encoding="utf-8"
    )
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    assert user_config_path() is not None
    config = load_config(None, cwd=str(project.root), use_user_config=True)
    assert config.auto_detect is False


def test_override_entry_without_id_raises(project):
    path = project.config("rules:\n  - severity: off\n")
    with pytest.raises(ConfigError):
        load_config(str(path), use_user_config=False)


def test_default_user_preset_dirs_reads_env(monkeypatch, tmp_path):
    from alinter.config import default_user_preset_dirs

    monkeypatch.setenv("ALINTER_PRESET_PATH", f"{tmp_path}/a{__import__('os').pathsep}{tmp_path}/b")
    dirs = default_user_preset_dirs()
    assert str(tmp_path / "a") in dirs
    assert str(tmp_path / "b") in dirs
