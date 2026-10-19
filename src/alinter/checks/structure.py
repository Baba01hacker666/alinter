"""Structured-data checks: parse validity plus simple key/path assertions."""

from __future__ import annotations

import configparser
import json
import xml.etree.ElementTree as ET
from typing import Any, Iterable, Tuple

from ..models import SourceFile, Violation
from ..utils import as_str_list, have_yaml, parse_data
from .base import Check


def _parse_ini(text: str) -> Any:
    parser = configparser.ConfigParser()
    parser.read_string(text)
    return {section: dict(parser.items(section)) for section in parser.sections()}


def _parse_xml(text: str) -> Any:
    root = ET.fromstring(text)
    return root


def _parse_structure(text: str, fmt: str) -> Any:
    fmt = fmt.lower()
    if fmt == "json":
        return json.loads(text)
    if fmt in ("yaml", "yml"):
        if not have_yaml():
            raise ValueError("PyYAML is required to parse YAML")
        return parse_data(text, "yaml")
    if fmt == "toml":
        return parse_data(text, "toml")
    if fmt == "ini":
        return _parse_ini(text)
    if fmt == "xml":
        return _parse_xml(text)
    raise ValueError(f"unsupported structure format {fmt!r}")


def _lookup(data: Any, path: str) -> Tuple[bool, Any]:
    """Resolve a dotted path; list indices are written as integers (``a.0.b``)."""
    current = data
    for part in path.split("."):
        if isinstance(current, dict):
            if part not in current:
                return False, None
            current = current[part]
        elif isinstance(current, (list, tuple)):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return False, None
        else:
            return False, None
    return True, current


class StructureCheck(Check):
    name = "structure"
    fixable = False
    default_message = "file does not match the expected {format} structure"
    help = "Validate that a file parses, and assert on keys/paths."

    def __init__(self, rule) -> None:
        super().__init__(rule)
        fmt = self.param("format")
        if not fmt:
            raise ValueError(f"{rule.id!r}: 'format' is required")
        self.format = str(fmt).lower()
        if self.format not in ("json", "yaml", "yml", "toml", "ini", "xml"):
            raise ValueError(
                f"{rule.id!r}: unsupported format {self.format!r} "
                "(expected json, yaml, toml, ini or xml)"
            )
        self.require_keys = as_str_list(self.param("require_keys"))
        self.forbid_keys = as_str_list(self.param("forbid_keys"))
        self.path_exists = as_str_list(self.param("path_exists"))
        self.path_absent = as_str_list(self.param("path_absent"))

    def run(self, file: SourceFile) -> Iterable[Violation]:
        try:
            data = _parse_structure(file.text, self.format)
        except Exception as exc:  # noqa: BLE001 - report, never crash
            yield self.violation(
                file,
                line=1,
                column=1,
                message=self.message(error=str(exc), format=self.format),
            )
            return

        if self.require_keys or self.forbid_keys:
            if not isinstance(data, dict):
                yield self.violation(
                    file, line=1, column=1,
                    message=f"expected a mapping at the document root, got {type(data).__name__}",
                )
                return
            for key in self.require_keys:
                if key not in data:
                    yield self.violation(
                        file, line=1, column=1,
                        message=self.message(key=key),
                    )
            for key in self.forbid_keys:
                if key in data:
                    yield self.violation(
                        file, line=1, column=1,
                        message=self.message(key=key),
                    )

        for path in self.path_exists:
            found, _ = _lookup(data, path)
            if not found:
                yield self.violation(
                    file, line=1, column=1,
                    message=self.message(path=path),
                )
        for path in self.path_absent:
            found, _ = _lookup(data, path)
            if found:
                yield self.violation(
                    file, line=1, column=1,
                    message=self.message(path=path),
                )
