"""Configuration discovery, parsing and rule construction.

Configuration may live in a YAML, JSON or TOML file, or under
``[tool.alinter]`` in ``pyproject.toml``. Several layers are merged, from
lowest to highest precedence:

1. bundled presets and your global config (``~/.config/alinter/config.yaml``)
2. the project config found by walking up from the working directory
3. an explicitly passed ``--config`` file

Because rules are plain data (``id`` + ``type`` + parameters), users can add
support for any language or any bespoke check without touching the engine.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .models import RULE_RESERVED_KEYS, Rule, Severity
from .utils import (
    ConfigError,
    as_bool,
    as_str_list,
    deep_merge,
    format_for_path,
    parse_data,
)

CONFIG_FILENAMES = (
    ".alinter.yaml",
    ".alinter.yml",
    "alinter.yaml",
    "alinter.yml",
    ".alinter.toml",
    "alinter.toml",
    ".alinter.json",
    "alinter.json",
)

#: Directories/files skipped by default when walking the tree.
DEFAULT_EXCLUDES: tuple[str, ...] = (
    "**/.git/**",
    "**/.hg/**",
    "**/.svn/**",
    "**/.venv/**",
    "**/venv/**",
    "**/env/**",
    "**/node_modules/**",
    "**/__pycache__/**",
    "**/.mypy_cache/**",
    "**/.ruff_cache/**",
    "**/.pytest_cache/**",
    "**/.tox/**",
    "**/.nox/**",
    "**/dist/**",
    "**/build/**",
    "**/*.egg-info/**",
    "**/target/**",
    "**/.idea/**",
    "**/.vscode/**",
    "**/*.min.js",
    "**/*.min.css",
    "**/package-lock.json",
    "**/yarn.lock",
    "**/poetry.lock",
    "**/uv.lock",
    "**/Pipfile.lock",
    "**/.DS_Store",
)

DEFAULT_SETTINGS: dict[str, Any] = {
    "encoding": "utf-8",
    "max_file_size": 5_000_000,
    "follow_symlinks": False,
    "use_gitignore": True,
    "allow_commands": False,
    "exclude_defaults": True,
}

#: Config keys whose list values are concatenated instead of replaced.
_LIST_KEYS = (
    "rules",
    "extends",
    "presets",
    "include",
    "exclude",
    "ignore",
    "select",
    "plugins",
    "preset_paths",
    "preset_dirs",
)


@dataclass
class Config:
    """A fully resolved alinter configuration."""

    version: int = 1
    path: str | None = None
    root: str = "."
    sources: list[str] = field(default_factory=list)
    auto_detect: bool = True
    extends: tuple[str, ...] = ()
    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    ignore: tuple[str, ...] = ()
    select: tuple[str, ...] = ()
    plugins: tuple[str, ...] = ()
    preset_paths: tuple[str, ...] = ()
    settings: dict[str, Any] = field(default_factory=dict)
    rules: list[Rule] = field(default_factory=list)
    overrides: dict[str, dict[str, Any]] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    # -- convenience ------------------------------------------------------

    def setting(self, name: str, default: Any = None) -> Any:
        if name in self.settings:
            return self.settings[name]
        return DEFAULT_SETTINGS.get(name, default)

    def excludes(self) -> list[str]:
        patterns: list[str] = []
        if as_bool(self.setting("exclude_defaults", True)):
            patterns.extend(DEFAULT_EXCLUDES)
        patterns.extend(self.exclude)
        return patterns

    def rule_ids(self) -> list[str]:
        return [rule.id for rule in self.rules]

    def find_rule(self, rule_id: str) -> Rule | None:
        for rule in self.rules:
            if rule.id == rule_id:
                return rule
        return None


# ---------------------------------------------------------------------------
# Rule construction
# ---------------------------------------------------------------------------

def build_rule(
    entry: Any,
    *,
    source: str | None = None,
    default_severity: Severity = Severity.ERROR,
) -> Rule:
    """Build a :class:`Rule` from a config mapping."""
    if isinstance(entry, str):
        raise ConfigError(
            f"rule {entry!r} must be a mapping with at least 'type' "
            "(e.g. {{id: {0}, type: regex, pattern: ...}})".format(entry)
        )
    if not isinstance(entry, dict):
        raise ConfigError(f"rule entries must be mappings, got {type(entry).__name__}")

    rule_id = entry.get("id")
    if not rule_id:
        raise ConfigError("every rule needs an 'id'")
    rule_id = str(rule_id)

    rule_type = entry.get("type") or entry.get("check")
    if not rule_type:
        raise ConfigError(f"rule {rule_id!r} needs a 'type' (the check to run)")
    rule_type = str(rule_type).strip().lower()

    severity = Severity.coerce(entry.get("severity", entry.get("level", default_severity)))
    params: dict[str, Any] = {
        key: value for key, value in entry.items() if key not in RULE_RESERVED_KEYS
    }
    nested = entry.get("params")
    if isinstance(nested, dict):
        params.update(nested)
    elif nested is not None:
        raise ConfigError(f"rule {rule_id!r}: 'params' must be a mapping")

    return Rule(
        id=rule_id,
        type=rule_type,
        message=entry.get("message"),
        description=entry.get("description"),
        severity=severity,
        files=tuple(as_str_list(entry.get("files"))),
        exclude=tuple(as_str_list(entry.get("exclude"))),
        languages=tuple(as_str_list(entry.get("languages", entry.get("language")))),
        enabled=as_bool(entry.get("enabled", True), True),
        tags=tuple(as_str_list(entry.get("tags"))),
        params=params,
        source=source,
    )


# ---------------------------------------------------------------------------
# File discovery / parsing
# ---------------------------------------------------------------------------

def _has_tool_alinter(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    marker = "[tool.alinter]"
    return marker in text


def find_config_file(start: str) -> Path | None:
    """Walk up from ``start`` looking for a config file."""
    directory = Path(start).resolve()
    if directory.is_file():
        directory = directory.parent
    for parent in (directory, *directory.parents):
        for name in CONFIG_FILENAMES:
            candidate = parent / name
            if candidate.is_file():
                return candidate
        pyproject = parent / "pyproject.toml"
        if pyproject.is_file() and _has_tool_alinter(pyproject):
            return pyproject
    return None


def user_config_path() -> Path | None:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(
        os.path.expanduser("~"), ".config"
    )
    directory = Path(base) / "alinter"
    for name in ("config.yaml", "config.yml", "config.toml", "config.json", "alinter.yaml"):
        candidate = directory / name
        if candidate.is_file():
            return candidate
    return None


def load_config_file(path: Path) -> dict[str, Any]:
    """Parse one config file into a mapping."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"could not read config {path}: {exc}") from exc
    fmt = format_for_path(path)
    data = parse_data(text, fmt, source=str(path))
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"config {path} must contain a mapping at the top level")
    if path.name == "pyproject.toml":
        data = data.get("tool", {}).get("alinter", {}) or {}
    return data


def merge_config_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Merge two config mappings, concatenating list-valued keys."""
    merged: dict[str, Any] = deep_merge(
        {k: v for k, v in base.items() if k not in _LIST_KEYS},
        {k: v for k, v in override.items() if k not in _LIST_KEYS},
    )
    for key in _LIST_KEYS:
        left = base.get(key)
        right = override.get(key)
        if left is None and right is None:
            continue
        combined: list[Any] = []
        for value in (left, right):
            for item in _as_sequence(value):
                if item not in combined:
                    combined.append(item)
        merged[key] = combined
    return merged


def _as_sequence(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_config(
    config_path: str | None = None,
    *,
    cwd: str = ".",
    no_config: bool = False,
    use_user_config: bool = True,
) -> Config:
    """Load and merge configuration into a :class:`Config`."""
    sources: list[str] = []
    merged: dict[str, Any] = {}
    root = "."

    if use_user_config and not no_config:
        user_path = user_config_path()
        if user_path is not None:
            merged = merge_config_dicts(merged, load_config_file(user_path))
            sources.append(str(user_path))

    project_path: Path | None = None
    if config_path:
        project_path = Path(config_path)
        if not project_path.is_file():
            raise ConfigError(f"config file not found: {config_path}")
    elif not no_config:
        project_path = find_config_file(cwd)

    if project_path is not None:
        merged = merge_config_dicts(merged, load_config_file(project_path))
        sources.append(str(project_path))
        root = str(project_path.resolve().parent)

    return _build_config(merged, sources, root)


def _build_config(raw: dict[str, Any], sources: list[str], root: str) -> Config:
    default_severity = Severity.coerce(raw.get("severity", raw.get("default_severity", "error")))

    settings = dict(DEFAULT_SETTINGS)
    user_settings = raw.get("settings")
    if isinstance(user_settings, dict):
        settings.update(user_settings)
    elif user_settings is not None:
        raise ConfigError("'settings' must be a mapping")

    rules: list[Rule] = []
    overrides: dict[str, dict[str, Any]] = {}
    seen: dict[str, int] = {}
    raw_rules = raw.get("rules") or []
    if not isinstance(raw_rules, list):
        raise ConfigError("'rules' must be a list")
    for entry in raw_rules:
        if isinstance(entry, dict) and not (entry.get("type") or entry.get("check")):
            # A rule without a type is an override of an existing rule by id.
            override_id = entry.get("id")
            if not override_id:
                raise ConfigError("every rule entry needs an 'id'")
            overrides[str(override_id)] = {
                key: value for key, value in entry.items() if key != "id"
            }
            continue
        rule = build_rule(entry, source=sources[-1] if sources else None,
                          default_severity=default_severity)
        if rule.id in seen:
            rules[seen[rule.id]] = rule  # later definition wins
        else:
            seen[rule.id] = len(rules)
            rules.append(rule)

    config = Config(
        version=int(raw.get("version", 1) or 1),
        path=sources[-1] if sources else None,
        root=root,
        sources=sources,
        auto_detect=as_bool(raw.get("auto_detect", True), True),
        extends=tuple(as_str_list(raw.get("extends") or raw.get("presets"))),
        include=tuple(as_str_list(raw.get("include"))),
        exclude=tuple(as_str_list(raw.get("exclude"))),
        ignore=tuple(as_str_list(raw.get("ignore"))),
        select=tuple(as_str_list(raw.get("select"))),
        plugins=tuple(as_str_list(raw.get("plugins"))),
        preset_paths=tuple(
            _resolve_paths(as_str_list(raw.get("preset_paths") or raw.get("preset_dirs")), root)
        ),
        settings=settings,
        rules=rules,
        overrides=overrides,
        raw=raw,
    )
    return config


def _resolve_paths(paths: Sequence[str], root: str) -> list[str]:
    resolved: list[str] = []
    for path in paths:
        expanded = os.path.expanduser(str(path))
        if not os.path.isabs(expanded):
            expanded = os.path.normpath(os.path.join(root, expanded))
        resolved.append(expanded)
    return resolved


def default_user_preset_dirs() -> list[str]:
    """Directories searched for extra preset files."""
    dirs: list[str] = []
    env = os.environ.get("ALINTER_PRESET_PATH")
    if env:
        dirs.extend(part for part in env.split(os.pathsep) if part)
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(
        os.path.expanduser("~"), ".config"
    )
    dirs.append(os.path.join(base, "alinter", "presets"))
    return dirs
