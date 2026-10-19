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
