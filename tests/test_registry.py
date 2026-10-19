from __future__ import annotations

import textwrap

import pytest

from alinter.checks.base import Check
from alinter.registry import CheckRegistry, get_registry
from alinter.utils import ConfigError


def test_builtin_registry_has_types():
    registry = get_registry()
    assert registry.get("regex") is not None
    assert registry.get("literal") is not None
    assert "no-trailing-whitespace" in list(registry.names())


def test_create_unknown_type():
    registry = get_registry()
    from alinter.config import build_rule

    rule = build_rule({"id": "x", "type": "does-not-exist"})
    with pytest.raises(ConfigError):
        registry.create(rule)


def test_create_wraps_parameter_errors():
    registry = get_registry()
    from alinter.config import build_rule

    rule = build_rule({"id": "x", "type": "max-line-length"})  # missing 'length'
    with pytest.raises(ConfigError):
        registry.create(rule)


def test_register_custom_check():
    registry = CheckRegistry({})
    from alinter.config import build_rule

    class MyCheck(Check):
        name = "my-check"

        def run(self, file):
            return []

    registry.register("my-check", MyCheck)
    rule = build_rule({"id": "x", "type": "my-check"})
    assert isinstance(registry.create(rule), MyCheck)


def test_load_plugin_from_module(tmp_path, monkeypatch):
    module = tmp_path / "my_plugin.py"
    module.write_text(
        textwrap.dedent(
            """
            from alinter.checks.base import Check

            class MarkerCheck(Check):
                name = "marker"

                def run(self, file):
                    return []

            register = None
            CHECKS = {"marker": MarkerCheck}
            """
        ),
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    registry = CheckRegistry({})
    registry.load_target("my_plugin")
    registered = registry.get("marker")
    assert registered is not None
    assert registered.name == "marker"


def test_load_plugin_attribute_target(tmp_path, monkeypatch):
    module = tmp_path / "attr_plugin.py"
    module.write_text(
        textwrap.dedent(
            """
            from alinter.checks.base import Check

            class ThingCheck(Check):
                name = "thing"

                def run(self, file):
                    return []
            """
        ),
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    registry = CheckRegistry({})
    registry.load_target("attr_plugin:ThingCheck")
    registered = registry.get("thing")
    assert registered is not None
    assert registered.name == "thing"


def test_load_plugin_missing_module():
    registry = CheckRegistry({})
    with pytest.raises(ConfigError):
        registry.load_target("definitely_not_a_module_xyz")
