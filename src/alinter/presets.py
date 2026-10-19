"""Language/format presets and file-type detection.

A *preset* is a YAML (or JSON) document describing one language or file
format: how to detect it, and a list of rules to apply. Bundled presets live
in ``alinter/presets/``; users can drop their own into
``~/.config/alinter/presets/`` or a directory named by ``preset_paths``.

Adding language support therefore never requires code changes: write a
preset file and it is picked up automatically.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .config import build_rule
from .models import Rule, Severity
from .utils import ConfigError, as_bool, as_str_list, format_for_path, parse_data

try:  # pragma: no cover - importlib.resources always present on 3.9+
    from importlib import resources as _resources
except Exception:  # pragma: no cover
    _resources = None  # type: ignore[assignment]


@dataclass
class Preset:
    """A language or format definition."""

    name: str
    language: str
    description: str = ""
    always_apply: bool = False
    detect: Dict[str, List[str]] = field(default_factory=dict)
    raw_rules: List[Dict[str, Any]] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)
    source: str = "<builtin>"

    @property
    def extensions(self) -> List[str]:
        return [str(ext).lower() for ext in self.detect.get("extensions", [])]

    @property
    def filenames(self) -> List[str]:
        return [str(name) for name in self.detect.get("filenames", [])]

    @property
    def shebangs(self) -> List[str]:
        return [str(token).lower() for token in self.detect.get("shebangs", [])]

    def build_rules(self) -> List[Rule]:
        """Build rules, scoping them to this preset's language.

        Preset rules are matched by *detected language* rather than by file
        glob, so detection via extension, file name or shebang all work. A
        rule may still set its own ``files``/``languages`` to narrow further.
        """
        rules: List[Rule] = []
        for entry in self.raw_rules:
            rule = build_rule(
                entry, source=self.source, default_severity=Severity.WARNING
            )
            if not self.always_apply and not rule.languages and self.language:
                rule.languages = (self.language,)
            rules.append(rule)
        return rules


def _preset_from_data(data: Any, name: Optional[str], source: str) -> Preset:
    if not isinstance(data, dict):
        raise ConfigError(f"preset {source} must contain a mapping")
    preset_name = str(data.get("name") or name or "").strip()
    if not preset_name:
        raise ConfigError(f"preset {source} needs a 'name'")
    detect = data.get("detect") or {}
    if not isinstance(detect, dict):
        raise ConfigError(f"preset {source}: 'detect' must be a mapping")
    rules = data.get("rules") or []
    if not isinstance(rules, list):
        raise ConfigError(f"preset {source}: 'rules' must be a list")
    return Preset(
        name=preset_name,
        language=str(data.get("language") or preset_name),
        description=str(data.get("description") or ""),
        always_apply=as_bool(data.get("always_apply", False)),
        detect={
            "extensions": as_str_list(detect.get("extensions")),
            "filenames": as_str_list(detect.get("filenames")),
            "shebangs": as_str_list(detect.get("shebangs")),
        },
        raw_rules=rules,
        raw=data,
        source=source,
    )


# ---------------------------------------------------------------------------
# Detection index
# ---------------------------------------------------------------------------

@dataclass
class DetectionIndex:
    extensions: Dict[str, List[str]] = field(default_factory=dict)
    filenames: Dict[str, List[str]] = field(default_factory=dict)
    shebangs: Dict[str, List[str]] = field(default_factory=dict)

    def detect(
        self,
        filename: str,
        extension: str,
        first_line: Optional[str] = None,
    ) -> Optional[str]:
        for candidate in (filename, filename.lower()):
            if candidate in self.filenames:
                return self.filenames[candidate][0]
        if extension and extension.lower() in self.extensions:
            return self.extensions[extension.lower()][0]
        if first_line and first_line.startswith("#!"):
            lowered = first_line.lower()
            for token in _shebang_tokens(lowered):
                if token in self.shebangs:
                    return self.shebangs[token][0]
        return None


def _shebang_tokens(line: str) -> List[str]:
    tokens: List[str] = []
    for word in line[2:].replace("\t", " ").split():
        word = word.strip()
        if not word:
            continue
        base = os.path.basename(word)
        if base.startswith("-") or "=" in base:
            if base.startswith("env"):
                continue
            continue
        tokens.append(base)
        tokens.append(base.split(".")[0])
        stripped = base.rstrip("0123456789.")
        if stripped and stripped not in tokens:
            tokens.append(stripped)
    return tokens


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------

class PresetRepository:
    """Loads every preset from bundled resources and user directories."""

    def __init__(self, extra_dirs: Sequence[str] = ()) -> None:
        self.presets: Dict[str, Preset] = {}
        self.errors: List[str] = []
        self._load_builtin()
        for directory in extra_dirs:
            self.load_dir(directory)
        self.index = self._build_index()

    # -- loading ----------------------------------------------------------

    def _load_builtin(self) -> None:
        if _resources is None:  # pragma: no cover
            return
        try:
            root = _resources.files("alinter").joinpath("presets")
        except (ModuleNotFoundError, FileNotFoundError):  # pragma: no cover
            return
        if not root.is_dir():  # pragma: no cover
            return
        for entry in sorted(root.iterdir(), key=lambda item: item.name):
            if entry.name.lower().endswith((".yaml", ".yml", ".json")):
                try:
                    self._add(entry.read_text(encoding="utf-8"), entry.name,
                              f"builtin:{entry.name}")
                except (OSError, ConfigError) as exc:  # pragma: no cover
                    self.errors.append(str(exc))

    def load_dir(self, directory: str) -> None:
        path = Path(directory)
        if not path.is_dir():
            return
        for file in sorted(path.iterdir()):
            if file.suffix.lower() not in (".yaml", ".yml", ".json"):
                continue
            try:
                self._add(file.read_text(encoding="utf-8"), file.stem, str(file))
            except (OSError, ConfigError) as exc:
                self.errors.append(str(exc))

    def _add(self, text: str, name: str, source: str) -> None:
        data = parse_data(text, format_for_path(name), source=source)
        preset = _preset_from_data(data, name, source)
        self.presets[preset.name] = preset

    # -- access -----------------------------------------------------------

    def get(self, name: str) -> Optional[Preset]:
        return self.presets.get(name)

    def require(self, name: str) -> Preset:
        preset = self.presets.get(name)
        if preset is None:
            available = ", ".join(self.names())
            raise ConfigError(f"unknown preset {name!r}. Available: {available}")
        return preset

    def names(self) -> List[str]:
        return sorted(self.presets)

    def _build_index(self) -> DetectionIndex:
        index = DetectionIndex()
        for name in self.names():
            preset = self.presets[name]
            if preset.always_apply:
                continue
            for ext in preset.extensions:
                index.extensions.setdefault(ext, []).append(preset.name)
            for filename in preset.filenames:
                index.filenames.setdefault(filename, []).append(preset.name)
                index.filenames.setdefault(filename.lower(), []).append(preset.name)
            for token in preset.shebangs:
                index.shebangs.setdefault(token.lower(), []).append(preset.name)
        return index
