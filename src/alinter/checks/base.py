"""Base class and helpers for lint checks.

A *check* is the implementation of a rule ``type``. Checks receive a
:class:`~alinter.models.Rule` (carrying the user's parameters) and a
:class:`~alinter.models.SourceFile`, and yield :class:`Violation` objects.

Adding a new built-in check means subclassing :class:`Check` and registering
the class in :mod:`alinter.checks`. Third-party packages can do the same via
the ``alinter.checks`` entry-point group (see :mod:`alinter.registry`).
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from ..models import Rule, SourceFile, TextEdit, Violation


class Check:
    """Base class for all checks."""

    #: The rule ``type`` this class implements (e.g. ``"regex"``).
    name: str = ""
    #: Whether this check can emit auto-fixes.
    fixable: bool = False
    #: One-line human description, used by ``alinter explain``.
    help: str = ""
    #: Fallback message used when a rule does not set ``message``.
    default_message: str = ""
    #: Singleton checks describe a single whole-file property (final newline,
    #: line endings, ...). Only the most specific rule of a singleton type is
    #: run per file, so a language preset overrides the generic baseline.
    singleton: bool = False

    def __init__(self, rule: Rule) -> None:
        self.rule = rule
        self.params: Dict[str, Any] = rule.params

    # -- helpers ----------------------------------------------------------

    def param(self, name: str, default: Any = None) -> Any:
        return self.params.get(name, default)

    def message(self, **extra: Any) -> str:
        """Render the rule message with ``{placeholder}`` substitution.

        Placeholders may reference any rule parameter plus the extras passed
        here. Unknown placeholders degrade gracefully to the raw template.
        """
        template = self.rule.message or self.default_message or self.name
        data: Dict[str, Any] = {"rule": self.rule.id}
        data.update(self.params)
        data.update(extra)
        try:
            return template.format(**data)
        except (KeyError, IndexError, ValueError):
            return template

    def violation(
        self,
        file: SourceFile,
        *,
        line: Optional[int] = None,
        column: Optional[int] = None,
        end_line: Optional[int] = None,
        end_column: Optional[int] = None,
        message: Optional[str] = None,
        snippet: Optional[str] = None,
        fix: Optional[TextEdit] = None,
        **extra: Any,
    ) -> Violation:
        return Violation(
            rule_id=self.rule.id,
            message=message if message is not None else self.message(**extra),
            path=file.rel_path,
            severity=self.rule.severity,
            line=line,
            column=column,
            end_line=end_line,
            end_column=end_column,
            snippet=snippet,
            fix=fix,
            tags=self.rule.tags,
            rule_type=self.rule.type,
        )

    # -- to implement -----------------------------------------------------

    def run(self, file: SourceFile) -> Iterable[Violation]:  # pragma: no cover
        raise NotImplementedError


def location_of(file: SourceFile, start: int, end: Optional[int] = None):
    """Return ``(line, column, end_line, end_column)`` for a span."""
    line, column = file.line_col(start)
    if end is None:
        return line, column, None, None
    end_line, end_column = file.line_col(end)
    return line, column, end_line, end_column
