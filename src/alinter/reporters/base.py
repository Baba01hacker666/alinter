"""Reporter base class and shared helpers."""

from __future__ import annotations

import sys
from typing import Any, Dict, List, Optional, Sequence, TextIO

from ..models import LintResult, Severity, Violation

SEVERITY_ORDER = (Severity.ERROR, Severity.WARNING, Severity.INFO)


class Reporter:
    """Base class for output formats."""

    name = "base"
    binary_output = False

    def render(
        self,
        result: LintResult,
        *,
        config: Any = None,
        options: Any = None,
        out: Optional[TextIO] = None,
    ) -> str:
        raise NotImplementedError

    # -- helpers ----------------------------------------------------------

    @staticmethod
    def group_by_file(violations: Sequence[Violation]) -> "Dict[str, List[Violation]]":
        grouped: Dict[str, List[Violation]] = {}
        for violation in violations:
            grouped.setdefault(violation.path, []).append(violation)
        return grouped

    @staticmethod
    def write(text: str, out: Optional[TextIO]) -> str:
        stream = out if out is not None else sys.stdout
        stream.write(text)
        if text and not text.endswith("\n"):
            stream.write("\n")
        return text


def summarize(result: LintResult) -> Dict[str, Any]:
    counts = result.counts()
    return {
        "files": result.files_checked,
        "skipped": result.files_skipped,
        "rules": result.rules_run,
        "violations": len(result.violations),
        "errors": counts.get("error", 0),
        "warnings": counts.get("warning", 0),
        "info": counts.get("info", 0),
        "fixable": sum(1 for v in result.violations if v.fixable),
        "fixed": result.fixed_count,
        "duration": round(result.duration, 4),
    }
