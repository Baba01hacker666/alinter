from __future__ import annotations

import json
import xml.etree.ElementTree as ET

from alinter.models import LintResult, Severity, Violation
from alinter.reporters import get_reporter
from alinter.reporters.machine import (
    GithubReporter,
    JsonReporter,
    JUnitReporter,
    SarifReporter,
)
from alinter.reporters.text import TextReporter
from alinter.utils import ConfigError


def make_result() -> LintResult:
    result = LintResult(files_checked=1, rules_run=2)
    result.violations = [
        Violation(
            rule_id="x/y",
            message="something bad",
            path="a.py",
            severity=Severity.ERROR,
            line=3,
            column=5,
            end_line=3,
            end_column=8,
            snippet="bad line",
            rule_type="regex",
        ),
        Violation(
            rule_id="x/w",
            message="a warning",
            path="a.py",
            severity=Severity.WARNING,
            line=9,
            column=1,
        ),
    ]
    return result


def test_text_reporter_contains_details():
    out = TextReporter().render(make_result())
    assert "a.py" in out
    assert "something bad" in out
    assert "x/y" in out


def test_text_reporter_quiet_hides_details():
    class Opt:
        quiet = True
        color = False
        fix_dry_run = False

    out = TextReporter().render(make_result(), options=Opt())
    assert "something bad" not in out
    assert "Found" in out


def test_text_reporter_clean():
    out = TextReporter().render(LintResult(), options=None)
    assert "All clear" in out


def test_json_reporter():
    payload = json.loads(JsonReporter().render(make_result()))
    assert payload["summary"]["violations"] == 2
    assert payload["violations"][0]["rule"] == "x/y"
    assert payload["violations"][0]["line"] == 3


def test_sarif_reporter():
    payload = json.loads(SarifReporter().render(make_result()))
    assert payload["version"] == "2.1.0"
    run = payload["runs"][0]
    assert run["tool"]["driver"]["name"] == "alinter"
    assert len(run["results"]) == 2
    assert run["results"][0]["level"] == "error"


def test_junit_reporter():
    xml = JUnitReporter().render(make_result())
    root = ET.fromstring(xml.strip())
    assert root.tag == "testsuites"
    failures = root.findall(".//failure")
    assert len(failures) == 2


def test_github_reporter():
    out = GithubReporter().render(make_result())
    assert out.startswith("::error ")
    assert "file=a.py" in out
    assert "::warning " in out


def test_unknown_reporter():
    import pytest

    with pytest.raises(ConfigError):
        get_reporter("nope")
