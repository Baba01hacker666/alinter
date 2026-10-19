"""Human-readable, colored text reporter."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TextIO

from ..models import LintResult, Severity, Violation
from ..utils import Color, plural
from .base import Reporter, summarize

_SEVERITY_LABEL = {
    Severity.ERROR: ("error", "bright_red"),
    Severity.WARNING: ("warning", "yellow"),
    Severity.INFO: ("info", "bright_blue"),
}


class TextReporter(Reporter):
    name = "text"

    def render(
        self,
        result: LintResult,
        *,
        config: Any = None,
        options: Any = None,
        out: Optional[TextIO] = None,
    ) -> str:
        enabled = getattr(options, "color", None)
        color = Color(enabled)
        lines: List[str] = []

        grouped = self.group_by_file(result.violations)
        quiet = getattr(options, "quiet", False)
        if not quiet:
            for path in sorted(grouped):
                lines.append(color.paint(path, "bold", "cyan"))
                for violation in grouped[path]:
                    lines.append("  " + self._format_violation(violation, color))
                lines.append("")

        if result.fixed_files and not getattr(options, "fix_dry_run", False):
            lines.append(
                color.paint(
                    f"Fixed {plural(result.fixed_count, 'issue')} in "
                    f"{plural(len(result.fixed_files), 'file')}.",
                    "green",
                )
            )
        elif getattr(options, "fix_dry_run", False) and result.fixed_count:
            lines.append(
                color.paint(
                    f"Would fix {plural(result.fixed_count, 'issue')} in "
                    f"{plural(len(result.fixed_files), 'file')}.",
                    "yellow",
                )
            )

        stats = summarize(result)
        lines.append(self._summary(stats, color))
        text = "\n".join(lines)
        return self.write(text + "\n", out)

    def _format_violation(self, violation: Violation, color: Color) -> str:
        label, style = _SEVERITY_LABEL.get(violation.severity, ("info", "white"))
        location = ""
        if violation.line is not None:
            location = f"{violation.line}:{violation.column or 1}"
        parts = [
            color.paint(location.ljust(7), "dim"),
            color.paint(label.ljust(7), style, "bold"),
            violation.message,
            color.paint(f"({violation.rule_id})", "dim"),
        ]
        if violation.fixable:
            parts.append(color.paint("[fixable]", "green"))
        rendered = "  ".join(part for part in parts if part)
        if violation.snippet:
            rendered += "\n" + color.paint(f"      | {violation.snippet}", "dim")
        return rendered

    def _summary(self, stats: Dict[str, Any], color: Color) -> str:
        total = stats["violations"]
        if total == 0:
            head = color.paint("All clear", "green", "bold")
        else:
            tone = "bright_red" if stats["errors"] else "yellow"
            head = color.paint(f"Found {plural(total, 'problem')}", tone, "bold")
            head += "  " + color.paint(
                f"({stats['errors']} errors, {stats['warnings']} warnings, {stats['info']} info)",
                "dim",
            )
        tail = color.paint(
            f"{plural(stats['files'], 'file')} checked, "
            f"{plural(stats['rules'], 'rule')}, {stats['duration']}s",
            "dim",
        )
        return f"{head}\n{tail}"
