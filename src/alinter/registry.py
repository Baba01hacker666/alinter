"""Check registry and plugin loading.

Custom check types can be contributed in two ways:

* **Entry points** - a package publishes an ``alinter.checks`` entry point
  pointing at a :class:`~alinter.checks.base.Check` subclass::

      [project.entry-points."alinter.checks"]
      my-check = "my_package.checks:MyCheck"

* **Config** - list import targets under ``plugins:`` in the config::

      plugins:
        - my_package.checks
        - my_package.checks:register

  A module target may define ``register(registry)`` or a ``CHECKS`` mapping.
"""

from __future__ import annotations

import importlib
import importlib.metadata as md
import inspect
from collections.abc import Iterable
from typing import Any

from .checks.base import Check
from .utils import ConfigError, as_str_list


class CheckRegistry:
    """Holds the mapping of rule type name -> :class:`Check` subclass."""

    def __init__(self, checks: dict[str, type[Check]] | None = None) -> None:
        self._checks: dict[str, type[Check]] = dict(checks or {})

    # -- registration -----------------------------------------------------

    def register(self, name: str, cls: type[Check] | None = None) -> Any:
        """Register ``cls`` under ``name``; usable as a decorator."""
        if cls is None:
            def decorator(klass: type[Check]) -> type[Check]:
                self._checks[name] = klass
                return klass

            return decorator
        self._checks[name] = cls
        return cls

    def register_object(self, name: str, obj: Any) -> None:
        if inspect.isclass(obj) and issubclass(obj, Check):
            self._checks[name] = obj
        elif callable(obj):
            obj(self)  # plugin callable receives the registry
        else:  # pragma: no cover - defensive
            raise ConfigError(f"cannot register plugin {name!r}: {obj!r}")

    # -- lookup -----------------------------------------------------------

    def get(self, name: str) -> type[Check] | None:
        return self._checks.get(name)

    def names(self) -> Iterable[str]:
        return sorted(self._checks)

    def create(self, rule) -> Check:
        cls = self.get(rule.type)
        if cls is None:
            available = ", ".join(self.names())
            raise ConfigError(
                f"rule {rule.id!r}: unknown check type {rule.type!r}. "
                f"Available types: {available}"
            )
        try:
            return cls(rule)
        except ConfigError:
            raise
        except (ValueError, TypeError) as exc:
            raise ConfigError(f"rule {rule.id!r} ({rule.type}): {exc}") from exc

    # -- plugin loading ---------------------------------------------------

    def load_entry_points(self, group: str = "alinter.checks") -> None:
        try:
            entry_points = md.entry_points(group=group)
        except TypeError:  # Python 3.9 fallback
            entry_points = md.entry_points().get(group, [])  # type: ignore[union-attr]
        for entry_point in entry_points:
            # A broken third-party plugin must never abort the whole run.
            try:
                obj = entry_point.load()
            except Exception:  # noqa: BLE001  # nosec B112
                continue
            try:
                self.register_object(entry_point.name, obj)
            except ConfigError:
                continue

    def load_target(self, target: str) -> None:
        """Load a plugin from a ``module`` or ``module:attribute`` string."""
        module_name, _, attr = target.partition(":")
        try:
            module = importlib.import_module(module_name)
        except ImportError as exc:
            raise ConfigError(f"could not import plugin {target!r}: {exc}") from exc

        if attr:
            try:
                obj = getattr(module, attr)
            except AttributeError as exc:
                raise ConfigError(
                    f"plugin {target!r}: module has no attribute {attr!r}"
                ) from exc
            name = getattr(obj, "name", None) or attr
            self.register_object(name, obj)
            return

        if hasattr(module, "register") and callable(module.register):
            module.register(self)
        if hasattr(module, "CHECKS"):
            for name, cls in dict(module.CHECKS).items():
                self.register(name, cls)
        for name in getattr(module, "CHECK_CLASSES", []):
            if inspect.isclass(name) and issubclass(name, Check):
                self.register(name.name, name)

    def load_targets(self, targets: Iterable[str]) -> None:
        for target in as_str_list(targets):
            self.load_target(target)


_REGISTRY: CheckRegistry | None = None


def get_registry() -> CheckRegistry:
    """Return the process-wide registry, loading built-ins and entry points."""
    global _REGISTRY
    if _REGISTRY is None:
        from .checks import BUILTIN_CHECKS

        _REGISTRY = CheckRegistry(BUILTIN_CHECKS)
        _REGISTRY.load_entry_points()
    return _REGISTRY


def reset_registry() -> None:
    """Forget the cached registry (mainly for tests)."""
    global _REGISTRY
    _REGISTRY = None
