"""Small, dependency-light helpers shared across alinter."""

from __future__ import annotations

import json
import os
import posixpath
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:  # PyYAML is a hard dependency, but keep the import defensive.
    import yaml
except Exception:  # pragma: no cover - only if the environment is broken
    yaml = None  # type: ignore[assignment]

if sys.version_info >= (3, 11):
    import tomllib as _toml
else:  # pragma: no cover - exercised on <3.11
    try:
        import tomli as _toml  # type: ignore[no-redef]
    except Exception:
        _toml = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Data parsing
# ---------------------------------------------------------------------------

class ConfigError(Exception):
    """Raised when a configuration file cannot be read or parsed."""


def have_yaml() -> bool:
    return yaml is not None


def parse_data(text: str, fmt: str, source: str = "<string>") -> Any:
    """Parse ``text`` as ``yaml``, ``json`` or ``toml``.

    Returns the parsed object (usually a mapping). Raises :class:`ConfigError`
    with a helpful message on failure.
    """
    fmt = fmt.lower().lstrip(".")
    try:
        if fmt in ("yaml", "yml"):
            if yaml is None:
                raise ConfigError(
                    "PyYAML is required to read YAML files. Install it with "
                    "`pip install PyYAML`."
                )
            return yaml.safe_load(text)
        if fmt == "json":
            return json.loads(text)
        if fmt == "toml":
            if _toml is None:
                raise ConfigError(
                    "Reading TOML requires Python 3.11+ or the `tomli` package."
                )
            return _toml.loads(text)
    except ConfigError:
        raise
    except Exception as exc:  # noqa: BLE001 - re-raised with context
        raise ConfigError(f"could not parse {source} as {fmt}: {exc}") from exc
    raise ConfigError(f"unsupported format {fmt!r} for {source}")


def format_for_path(path: Any) -> str:
    """Return the config format implied by a file name."""
    name = Path(str(path)).name.lower()
    if name.endswith((".yaml", ".yml")):
        return "yaml"
    if name.endswith(".json"):
        return "json"
    if name.endswith(".toml"):
        return "toml"
    # Unknown extension: try YAML, since it is a superset of JSON.
    return "yaml"


def deep_merge(base: Any, override: Any) -> Any:
    """Recursively merge ``override`` onto ``base`` (override wins).

    Lists and scalars are replaced wholesale. Mappings are merged key by key.
    Both inputs are treated as immutable.
    """
    if isinstance(base, dict) and isinstance(override, dict):
        merged: Dict[Any, Any] = dict(base)
        for key, value in override.items():
            if key in merged:
                merged[key] = deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged
    return override


# ---------------------------------------------------------------------------
# Glob / path matching
# ---------------------------------------------------------------------------

_GLOB_CACHE: Dict[str, "re.Pattern[str]"] = {}


def _is_plain_name(pattern: str) -> bool:
    return "/" not in pattern and not any(ch in pattern for ch in "*?[")


def glob_to_regex(pattern: str) -> "re.Pattern[str]":
    """Compile a shell-style glob (with ``**`` support) to a regex.

    Matching is done against POSIX-style, root-relative paths. A pattern
    without a slash (``*.py``) matches anywhere in the tree, and a bare name
    (``vendor``) matches that path segment and everything beneath it.
    """
    cached = _GLOB_CACHE.get(pattern)
    if cached is not None:
        return cached

    original = pattern
    pattern = pattern.replace("\\", "/").strip()
    while pattern.startswith("./"):
        pattern = pattern[2:]
    pattern = pattern.lstrip("/")
    if pattern.endswith("/"):
        pattern += "**"

    if _is_plain_name(pattern):
        # A bare name matches that path segment and everything beneath it.
        compiled = re.compile(r"^(?:.*/)?" + re.escape(pattern) + r"(?:/.*)?$")
        _GLOB_CACHE[original] = compiled
        return compiled

    if "/" not in pattern:
        # A pattern without a slash matches anywhere in the tree.
        pattern = "**/" + pattern

    out: List[str] = ["^"]
    i = 0
    n = len(pattern)
    while i < n:
        ch = pattern[i]
        if ch == "*":
            if i + 1 < n and pattern[i + 1] == "*":
                # ``**`` -> any number of path segments
                if i + 2 < n and pattern[i + 2] == "/":
                    out.append("(?:[^/]+/)*")
                    i += 3
                else:
                    out.append(".*")
                    i += 2
            else:
                out.append("[^/]*")
                i += 1
        elif ch == "?":
            out.append("[^/]")
            i += 1
        elif ch == "[":
            j = i + 1
            if j < n and pattern[j] in "!^":
                j += 1
            if j < n and pattern[j] == "]":
                j += 1
            while j < n and pattern[j] != "]":
                j += 1
            if j >= n:
                out.append(re.escape(ch))
                i += 1
            else:
                cls = pattern[i + 1 : j]
                if cls.startswith("!"):
                    cls = "^" + cls[1:]
                out.append("[" + cls.replace("\\", "\\\\") + "]")
                i = j + 1
        else:
            out.append(re.escape(ch))
            i += 1
    out.append("$")
    compiled = re.compile("".join(out))
    _GLOB_CACHE[original] = compiled
    return compiled


def normalize_path(path: str) -> str:
    """Normalize a path to forward slashes without ``./`` or redundant parts."""
    path = str(path).replace("\\", "/")
    normalized = posixpath.normpath(path)
    if normalized == ".":
        return ""
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def path_matches(path: str, patterns: Sequence[str]) -> bool:
    """True if ``path`` matches any of the glob ``patterns``."""
    if not patterns:
        return False
    normalized = normalize_path(path)
    for pattern in patterns:
        if glob_to_regex(pattern).match(normalized):
            return True
    return False


def matches_any_name(path: str, names: Iterable[str]) -> bool:
    """True if any path segment equals one of ``names``."""
    wanted = set(names)
    if not wanted:
        return False
    return any(part in wanted for part in normalize_path(path).split("/"))


# ---------------------------------------------------------------------------
# File reading
# ---------------------------------------------------------------------------

BINARY_SNIFF = 8192


def is_probably_binary(data: bytes) -> bool:
    if b"\x00" in data[:BINARY_SNIFF]:
        return True
    return False


def detect_encoding(data: bytes, preferred: str = "utf-8") -> Tuple[str, bool]:
    """Return ``(encoding, has_bom)`` for ``data``.

    Tries the preferred encoding, then ``utf-8-sig``, then common fallbacks.
    Never fails: the last resort is ``latin-1`` which decodes anything.
    """
    if data.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig", True
    for candidate in (preferred, "utf-8", "utf-16"):
        try:
            data.decode(candidate)
            return candidate, False
        except (UnicodeDecodeError, LookupError):
            continue
    return "latin-1", False


def read_text(path: Path, preferred: str = "utf-8") -> Tuple[str, str, bool]:
    """Read ``path`` returning ``(text, encoding, has_bom)``.

    Bytes are decoded leniently so linting never crashes on odd encodings.
    """
    data = path.read_bytes()
    encoding, has_bom = detect_encoding(data, preferred)
    return data.decode(encoding, errors="replace"), encoding, has_bom


# ---------------------------------------------------------------------------
# Text / display helpers
# ---------------------------------------------------------------------------

class Color:
    """Tiny ANSI colorizer that disables itself when appropriate."""

    CODES = {
        "reset": "\033[0m",
        "bold": "\033[1m",
        "dim": "\033[2m",
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
        "white": "\033[37m",
        "bright_red": "\033[91m",
        "bright_yellow": "\033[93m",
        "bright_blue": "\033[94m",
    }

    def __init__(self, enabled: Optional[bool] = None) -> None:
        if enabled is None:
            enabled = self._auto_enabled()
        self.enabled = enabled

    @staticmethod
    def _auto_enabled() -> bool:
        if os.environ.get("NO_COLOR") is not None:
            return False
        if os.environ.get("FORCE_COLOR") is not None:
            return True
        try:
            return sys.stdout.isatty()
        except Exception:  # pragma: no cover
            return False

    def paint(self, text: str, *styles: str) -> str:
        if not self.enabled or not styles:
            return text
        prefix = "".join(self.CODES.get(style, "") for style in styles)
        return f"{prefix}{text}{self.CODES['reset']}"

    def __call__(self, text: str, *styles: str) -> str:
        return self.paint(text, *styles)


def truncate(text: str, limit: int = 120) -> str:
    text = text.rstrip("\r\n")
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)] + "\u2026"


def plural(count: int, singular: str, plural_form: Optional[str] = None) -> str:
    if count == 1:
        return f"{count} {singular}"
    return f"{count} {plural_form or singular + 's'}"


def as_list(value: Any) -> List[Any]:
    """Coerce a scalar/mapping/list into a list."""
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def as_str_list(value: Any) -> List[str]:
    return [str(item) for item in as_list(value)]


def as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in ("1", "true", "yes", "on", "y")
