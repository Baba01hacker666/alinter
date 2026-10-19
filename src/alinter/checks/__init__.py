"""The built-in check catalog.

Maps rule ``type`` names (and a few friendly aliases) to check classes.
"""

from __future__ import annotations

from .base import Check
from .command import CommandCheck
from .filecheck import (
    EncodingCheck,
    FinalNewlineCheck,
    LineEndingCheck,
    MaxFileSizeCheck,
    MaxLinesCheck,
)
from .linecheck import MaxLineLengthCheck
from .naming import FilenameCheck
from .pattern import LiteralCheck, RegexCheck
from .structure import StructureCheck
from .whitespace import NoTabsCheck, TrailingWhitespaceCheck

BUILTIN_CHECKS: dict[str, type[Check]] = {
    # Canonical names -----------------------------------------------------
    "regex": RegexCheck,
    "literal": LiteralCheck,
    "max-line-length": MaxLineLengthCheck,
    "no-trailing-whitespace": TrailingWhitespaceCheck,
    "no-tabs": NoTabsCheck,
    "final-newline": FinalNewlineCheck,
    "line-ending": LineEndingCheck,
    "max-lines": MaxLinesCheck,
    "max-file-size": MaxFileSizeCheck,
    "encoding": EncodingCheck,
    "filename": FilenameCheck,
    "structure": StructureCheck,
    "command": CommandCheck,
    # Friendly aliases ----------------------------------------------------
    "pattern": RegexCheck,
    "forbidden-pattern": RegexCheck,
    "required-pattern": RegexCheck,
    "contains": LiteralCheck,
    "substring": LiteralCheck,
    "forbidden-text": LiteralCheck,
    "required-text": LiteralCheck,
    "line-length": MaxLineLengthCheck,
    "max-line": MaxLineLengthCheck,
    "trailing-whitespace": TrailingWhitespaceCheck,
    "tabs": NoTabsCheck,
    "eof-newline": FinalNewlineCheck,
    "final-newline-check": FinalNewlineCheck,
    "file-size": MaxFileSizeCheck,
    "file-name": FilenameCheck,
}

__all__ = ["BUILTIN_CHECKS", "Check"]
