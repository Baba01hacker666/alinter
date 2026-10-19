"""Data models shared by the engine, checks and reporters."""

from __future__ import annotations

import bisect
import posixpath
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(str, Enum):
    """How serious a rule violation is."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    OFF = "off"

    @classmethod
    def coerce(cls, value: Any) -> Severity:
        if isinstance(value, Severity):
            return value
        if value is None:
            return cls.ERROR
        if isinstance(value, bool):
            # YAML 1.1 parses bare `off`/`no` as False and `on`/`yes` as True.
            return cls.ERROR if value else cls.OFF
        text = str(value).strip().lower()
        mapping = {
            "error": cls.ERROR, "err": cls.ERROR, "e": cls.ERROR, "2": cls.ERROR,
            "fatal": cls.ERROR, "critical": cls.ERROR,
            "warning": cls.WARNING, "warn": cls.WARNING, "w": cls.WARNING, "1": cls.WARNING,
            "info": cls.INFO, "information": cls.INFO, "i": cls.INFO,
            "note": cls.INFO, "hint": cls.INFO, "0": cls.INFO, "style": cls.INFO,
            "off": cls.OFF, "none": cls.OFF, "disable": cls.OFF,
            "disabled": cls.OFF, "ignore": cls.OFF, "-1": cls.OFF,
        }
        if text not in mapping:
            raise ValueError(
                f"unknown severity {value!r}; expected one of "
                "error, warning, info, off"
            )
        return mapping[text]

    @property
    def rank(self) -> int:
        return {"off": 0, "info": 1, "warning": 2, "error": 3}[self.value]

    @property
    def is_active(self) -> bool:
        return self is not Severity.OFF


# Reserved rule keys that are not check parameters.
RULE_RESERVED_KEYS = frozenset(
    {
        "id",
        "type",
        "description",
        "message",
        "severity",
        "level",
        "files",
        "exclude",
        "languages",
        "enabled",
        "tags",
        "params",
        "url",
        "source",
        "fixable",
    }
)


@dataclass
class TextEdit:
    """A byte-range replacement within a source file (offsets into ``text``)."""

    start: int
    end: int
    replacement: str

    def as_dict(self) -> dict[str, Any]:
        return {"start": self.start, "end": self.end, "replacement": self.replacement}


@dataclass
class Rule:
    """A single declarative lint rule."""

    id: str
    type: str
    message: str | None = None
    description: str | None = None
    severity: Severity = Severity.ERROR
    files: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    enabled: bool = True
    tags: tuple[str, ...] = ()
    params: dict[str, Any] = field(default_factory=dict)
    source: str | None = None

    def param(self, name: str, default: Any = None) -> Any:
        return self.params.get(name, default)

    def scoped_to(self, rel_path: str, language: str | None) -> bool:
        """Whether this *active* rule applies to a file."""
        if not self.enabled or not self.severity.is_active:
            return False
        return self.matches_path_language(rel_path, language)

    def matches_path_language(self, rel_path: str, language: str | None) -> bool:
        """Whether this rule's file/language scope covers a file (ignoring on/off)."""
        from .utils import path_matches

        if self.files and not path_matches(rel_path, self.files):
            return False
        if self.exclude and path_matches(rel_path, self.exclude):
            return False
        if self.languages:
            if language is None:
                return False
            if language not in self.languages:
                return False
        return True

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "severity": self.severity.value,
            "description": self.description,
            "message": self.message,
            "languages": list(self.languages),
            "files": list(self.files),
            "tags": list(self.tags),
            "source": self.source,
            "params": dict(self.params),
        }


@dataclass
class Violation:
    """A single rule violation found in a file."""

    rule_id: str
    message: str
    path: str
    severity: Severity = Severity.ERROR
    line: int | None = None
    column: int | None = None
    end_line: int | None = None
    end_column: int | None = None
    snippet: str | None = None
    fix: TextEdit | None = None
    tags: tuple[str, ...] = ()
    rule_type: str | None = None

    @property
    def fixable(self) -> bool:
        return self.fix is not None

    @property
    def location(self) -> str:
        if self.line is None:
            return self.path
        if self.column is None:
            return f"{self.path}:{self.line}"
        return f"{self.path}:{self.line}:{self.column}"

    def sort_key(self) -> tuple[str, int, int, str]:
        return (self.path, self.line or 0, self.column or 0, self.rule_id)

    def as_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "rule": self.rule_id,
            "message": self.message,
            "path": self.path,
            "severity": self.severity.value,
        }
        if self.rule_type:
            data["type"] = self.rule_type
        if self.line is not None:
            data["line"] = self.line
        if self.column is not None:
            data["column"] = self.column
        if self.end_line is not None:
            data["end_line"] = self.end_line
        if self.end_column is not None:
            data["end_column"] = self.end_column
        if self.snippet is not None:
            data["snippet"] = self.snippet
        if self.tags:
            data["tags"] = list(self.tags)
        data["fixable"] = self.fixable
        return data


@dataclass
class SourceFile:
    """A file being linted, with an index for offset -> line/column."""

    path: str
    rel_path: str
    text: str
    encoding: str = "utf-8"
    has_bom: bool = False
    language: str | None = None
    size: int = 0

    _line_starts: list[int] | None = field(default=None, repr=False, compare=False)

    @property
    def filename(self) -> str:
        return posixpath.basename(self.rel_path)

    @property
    def extension(self) -> str:
        return posixpath.splitext(self.filename)[1].lower()

    @property
    def lines(self) -> list[str]:
        """Lines *without* their terminators (a final empty line is dropped)."""
        return self.text.splitlines()

    def split_lines_keepends(self) -> list[str]:
        return self.text.splitlines(keepends=True)

    def _ensure_index(self) -> list[int]:
        if self._line_starts is None:
            self._line_starts = [0, *[m.end() for m in _NEWLINE_RE.finditer(self.text)]]
        return self._line_starts

    def line_col(self, offset: int) -> tuple[int, int]:
        """Convert a character offset to 1-based ``(line, column)``."""
        starts = self._ensure_index()
        offset = max(0, min(offset, len(self.text)))
        index = bisect.bisect_right(starts, offset) - 1
        return index + 1, offset - starts[index] + 1

    def line_text(self, line: int) -> str:
        lines = self.split_lines_keepends()
        if 1 <= line <= len(lines):
            return lines[line - 1].rstrip("\r\n")
        return ""


import re as _re  # noqa: E402  (kept at the bottom to avoid clutter above)

_NEWLINE_RE = _re.compile(r"\r\n|\r|\n")


@dataclass
class RuleReport:
    """Aggregate information about a rule after a run."""

    rule_id: str
    severity: Severity
    count: int
    fixable: bool = False


@dataclass
class LintResult:
    """Everything produced by one engine run."""

    violations: list[Violation] = field(default_factory=list)
    files_checked: int = 0
    files_skipped: int = 0
    rules_run: int = 0
    fixed_files: list[str] = field(default_factory=list)
    fixed_count: int = 0
    errors: list[str] = field(default_factory=list)
    duration: float = 0.0

    def counts(self) -> dict[str, int]:
        counts = {"error": 0, "warning": 0, "info": 0}
        for violation in self.violations:
            counts[violation.severity.value] = counts.get(violation.severity.value, 0) + 1
        return counts

    @property
    def has_errors(self) -> bool:
        return any(v.severity is Severity.ERROR for v in self.violations)
