from __future__ import annotations

import pytest

from alinter.presets import PresetRepository
from alinter.registry import get_registry


@pytest.fixture(scope="module")
def repository():
    return PresetRepository([])


def test_all_builtin_presets_load(repository):
    assert repository.errors == []
    assert len(repository.names()) >= 30


def test_every_preset_rule_is_valid(repository):
    registry = get_registry()
    for name in repository.names():
        preset = repository.presets[name]
        rules = preset.build_rules()
        assert rules, f"{name} has no rules"
        seen = set()
        for rule in rules:
            assert rule.id not in seen, f"duplicate id {rule.id} in {name}"
            seen.add(rule.id)
            assert registry.get(rule.type) is not None, f"{name}: unknown type {rule.type}"
            # Constructing the check validates every parameter.
            registry.create(rule)


def test_generic_preset_always_applies(repository):
    assert repository.presets["generic"].always_apply is True
    assert repository.presets["generic"].build_rules()[0].languages == ()


def test_detection_by_extension(repository):
    index = repository.index
    assert index.detect("a.py", ".py") == "python"
    assert index.detect("a.go", ".go") == "go"
    assert index.detect("a.ts", ".ts") == "typescript"
    assert index.detect("a.rs", ".rs") == "rust"
    assert index.detect("a.json", ".json") == "json"


def test_detection_by_filename(repository):
    index = repository.index
    assert index.detect("Dockerfile", "") == "dockerfile"
    assert index.detect("Makefile", "") == "makefile"


def test_detection_by_shebang(repository):
    index = repository.index
    assert index.detect("runme", "", "#!/usr/bin/env bash") == "shell"
    assert index.detect("runme", "", "#!/usr/bin/python3") == "python"


def test_unknown_extension(repository):
    assert repository.index.detect("a.qqq", ".qqq") is None


def test_require_unknown_preset(repository):
    from alinter.utils import ConfigError

    with pytest.raises(ConfigError):
        repository.require("nope-not-real")


def test_require_returns_preset(repository):
    assert repository.require("python").language == "python"


def test_preset_from_data_rejects_bad_shapes():
    from alinter.presets import _preset_from_data
    from alinter.utils import ConfigError

    with pytest.raises(ConfigError):
        _preset_from_data([], None, "<test>")  # not a mapping
    with pytest.raises(ConfigError):
        _preset_from_data({}, None, "<test>")  # missing name
    with pytest.raises(ConfigError):
        _preset_from_data({"name": "x", "detect": 5}, "x", "<test>")
    with pytest.raises(ConfigError):
        _preset_from_data({"name": "x", "rules": 1}, "x", "<test>")


def test_build_rules_scope_to_language(repository):
    from alinter.presets import Preset

    preset = Preset(
        name="mylang",
        language="mylang",
        raw_rules=[{"id": "mylang/r", "type": "literal", "value": "x"}],
    )
    (rule,) = preset.build_rules()
    assert rule.languages == ("mylang",)


def test_always_apply_rules_are_not_language_scoped(repository):
    from alinter.presets import Preset

    preset = Preset(
        name="base",
        language="generic",
        always_apply=True,
        raw_rules=[{"id": "base/r", "type": "literal", "value": "x"}],
    )
    (rule,) = preset.build_rules()
    assert rule.languages == ()


def test_preset_rule_keeps_explicit_languages():
    from alinter.presets import Preset

    preset = Preset(
        name="mylang",
        language="mylang",
        raw_rules=[
            {"id": "mylang/r", "type": "literal", "value": "x", "languages": ["other"]}
        ],
    )
    (rule,) = preset.build_rules()
    assert rule.languages == ("other",)


def test_load_dir_reports_bad_presets(tmp_path):
    from alinter.presets import PresetRepository

    (tmp_path / "good.yaml").write_text(
        "name: good\nlanguage: good\nrules:\n  - id: good/r\n    type: literal\n    value: x\n",
        encoding="utf-8",
    )
    (tmp_path / "broken.yaml").write_text("rules: 1\n", encoding="utf-8")
    (tmp_path / "ignored.txt").write_text("not a preset", encoding="utf-8")
    repo = PresetRepository([str(tmp_path)])
    assert repo.get("good") is not None
    assert repo.errors  # the broken preset was reported, not raised


def test_load_dir_ignores_missing_directory(tmp_path):
    from alinter.presets import PresetRepository

    repo = PresetRepository([str(tmp_path / "nope")])
    assert repo.errors == []


def test_detection_is_case_insensitive():
    from alinter.presets import PresetRepository

    repo = PresetRepository([])
    index = repo.index
    assert index.detect("dockerfile", "") == "dockerfile"
    assert index.detect("A.PY", ".PY") == "python"


def test_shebang_tokens_strip_versions_and_env():
    from alinter.presets import _shebang_tokens

    tokens = _shebang_tokens("#!/usr/bin/env python3.12")
    assert "python3.12" in tokens
    assert "python3" in tokens
    assert "python" in tokens
