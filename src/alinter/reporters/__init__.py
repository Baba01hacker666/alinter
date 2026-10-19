"""Reporter registry."""

from __future__ import annotations

from typing import Dict, Type

from ..utils import ConfigError
from .base import Reporter
from .machine import GithubReporter, JsonReporter, JUnitReporter, SarifReporter
from .text import TextReporter

REPORTERS: Dict[str, Type[Reporter]] = {
    "text": TextReporter,
    "json": JsonReporter,
    "sarif": SarifReporter,
    "junit": JUnitReporter,
    "xml": JUnitReporter,
    "github": GithubReporter,
    "gha": GithubReporter,
}


def get_reporter(name: str) -> Reporter:
    reporter = REPORTERS.get(name.strip().lower())
    if reporter is None:
        available = ", ".join(sorted(REPORTERS))
        raise ConfigError(f"unknown output format {name!r}. Available: {available}")
    return reporter()


def reporter_names():
    return sorted(REPORTERS)


__all__ = ["Reporter", "REPORTERS", "get_reporter", "reporter_names"]
