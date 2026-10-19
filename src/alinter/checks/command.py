"""Run an external command per file and check its exit status.

This is powerful and therefore *opt-in*: it only runs when the user passes
``--allow-commands`` (or sets ``settings.allow_commands: true``). The engine
injects a ``_allow_commands`` parameter into the rule.
"""

from __future__ import annotations

import os
import subprocess
from typing import Iterable

from ..models import SourceFile, Violation
from ..utils import as_bool, truncate
from .base import Check


class CommandCheck(Check):
    name = "command"
    fixable = False
    default_message = "command failed with exit code {exit_code}"
    help = "Run an external command per file; fail on unexpected exit code."

    def __init__(self, rule) -> None:
        super().__init__(rule)
        command = self.param("command")
        if not command:
            raise ValueError(f"{rule.id!r}: 'command' is required")
        self.command = str(command)
        self.expect_exit = int(self.param("expect_exit", 0))
        self.shell = as_bool(self.param("shell", True))
        self.timeout = float(self.param("timeout", 30.0))

    def _render(self, file: SourceFile) -> str:
        return self.command.format(
            path=file.path,
            rel_path=file.rel_path,
            filename=file.filename,
            extension=file.extension,
            language=file.language or "",
        )

    def run(self, file: SourceFile) -> Iterable[Violation]:
        if not as_bool(self.param("_allow_commands", False)):
            return
        command = self._render(file)
        working_dir = os.path.dirname(file.path) or None
        try:
            completed = subprocess.run(
                command,
                shell=self.shell,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=working_dir,
            )
        except subprocess.TimeoutExpired:
            yield self.violation(
                file, line=1, column=1,
                message=self.message(command=command, exit_code="timeout"),
            )
            return
        except OSError as exc:
            yield self.violation(
                file, line=1, column=1,
                message=self.message(command=command, exit_code=str(exc)),
            )
            return

        if completed.returncode != self.expect_exit:
            detail = truncate((completed.stdout or "") + (completed.stderr or ""), 200)
            yield self.violation(
                file,
                line=1,
                column=1,
                message=self.message(
                    command=command,
                    exit_code=completed.returncode,
                    output=detail,
                ),
            )
