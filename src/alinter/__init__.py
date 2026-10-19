"""alinter - a universal, config-driven linter.

alinter lints *anything*: pick a language preset or write your own declarative
rules in a config file. Rules are plain data, so adding support for a new
language or a one-off check never requires changing the engine.

Basic use::

    from alinter import lint

    result = lint(["src/"], config=".alinter.yaml")
    for violation in result.violations:
        print(violation.path, violation.line, violation.message)

Or from the command line::

    alinter check src/
"""

from __future__ import annotations

__all__ = [
    "Config",
    "Engine",
    "Rule",
    "Severity",
    "Violation",
    "__version__",
    "lint",
    "load_config",
]

__version__ = "0.1.0"

from .config import Config, load_config
from .engine import Engine, lint
from .models import Rule, Severity, Violation
