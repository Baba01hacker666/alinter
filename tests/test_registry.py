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


def test_register_decorator():
    registry = CheckRegistry({})

    @registry.register("deco")
    class DecoCheck(Check):
        name = "deco"

        def run(self, file):
            return []

    assert registry.get("deco") is DecoCheck


def test_register_object_callable_receives_registry():
    registry = CheckRegistry({})
    seen = {}

    def plugin(reg):
        seen["registry"] = reg

    registry.register_object("plugin", plugin)
    assert seen["registry"] is registry


def test_register_object_rejects_non_callable():
    registry = CheckRegistry({})
    with pytest.raises(ConfigError):
        registry.register_object("bad", object())


def test_create_wraps_unexpected_type_errors():
    registry = CheckRegistry({})

    class Boom(Check):
        name = "boom"

        def __init__(self, rule):
            raise TypeError("nope")

        def run(self, file):  # pragma: no cover
            return []

    from alinter.config import build_rule

    registry.register("boom", Boom)
    with pytest.raises(ConfigError):
        registry.create(build_rule({"id": "x", "type": "boom"}))


def test_load_target_missing_attribute(tmp_path, monkeypatch):
    (tmp_path / "attr_missing.py").write_text("x = 1\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    registry = CheckRegistry({})
    with pytest.raises(ConfigError):
        registry.load_target("attr_missing:Nope")


def test_load_target_module_register_function(tmp_path, monkeypatch):
    module = tmp_path / "reg_plugin.py"
    module.write_text(
        textwrap.dedent(
            """
            from alinter.checks.base import Check

            class RegCheck(Check):
                name = "reg"
                def run(self, file):
                    return []

            def register(registry):
                registry.register("reg", RegCheck)
            """
        ),
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    registry = CheckRegistry({})
    registry.load_target("reg_plugin")
    assert registry.get("reg") is not None


def test_load_target_module_check_classes(tmp_path, monkeypatch):
    module = tmp_path / "classes_plugin.py"
    module.write_text(
        textwrap.dedent(
            """
            from alinter.checks.base import Check

            class ClassyCheck(Check):
                name = "classy"
                def run(self, file):
                    return []

            CHECK_CLASSES = [ClassyCheck]
            """
        ),
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    registry = CheckRegistry({})
    registry.load_target("classes_plugin")
    assert registry.get("classy") is not None


def test_load_targets_iterates():
    registry = CheckRegistry({})
    with pytest.raises(ConfigError):
        registry.load_targets(["no_such_module_abc"])


def test_load_entry_points_skips_broken_plugin(monkeypatch):
    from alinter import registry as registry_module

    class FakeEntryPoint:
        name = "broken"

        def load(self):
            raise RuntimeError("plugin exploded")

    monkeypatch.setattr(
        registry_module.md, "entry_points", lambda **kwargs: [FakeEntryPoint()]
    )
    registry = CheckRegistry({})
    registry.load_entry_points()  # must not raise
    assert registry.get("broken") is None


def test_reset_registry_reloads_builtins():
    from alinter.registry import reset_registry

    reset_registry()
    assert get_registry().get("regex") is not None
