"""Example custom check plugin.

Point alinter at this module from a config file:

    plugins:
      - examples.plugin_spdx

or publish it via the ``alinter.checks`` entry-point group.
"""

from __future__ import annotations

from collections.abc import Iterable

from alinter.checks.base import Check
from alinter.models import SourceFile, Violation


class LicenseHeaderCheck(Check):
    """Require an SPDX license identifier in the first few lines."""

    name = "spdx-header"
    help = "Require an 'SPDX-License-Identifier' comment near the top of a file."
    fixable = False

    def __init__(self, rule) -> None:
        super().__init__(rule)
        self.scan_lines = int(self.param("scan_lines", 5))
        self.identifier = str(self.param("identifier", "SPDX-License-Identifier"))

    def run(self, file: SourceFile) -> Iterable[Violation]:
        head = "\n".join(file.split_lines_keepends()[: self.scan_lines])
        if self.identifier not in head:
            yield self.violation(
                file,
                line=1,
                column=1,
                message=self.message(identifier=self.identifier),
            )


CHECKS = {"spdx-header": LicenseHeaderCheck}
