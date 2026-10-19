"""Machine-readable reporters: JSON, SARIF, JUnit XML and GitHub Actions."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from typing import Any, Dict, List

from .. import __version__
from ..models import Severity
from .base import Reporter, summarize

_SEVERITY_LEVEL = {
    Severity.ERROR: "error",
    Severity.WARNING: "warning",
    Severity.INFO: "note",
}


class JsonReporter(Reporter):
    name = "json"

    def render(self, result, *, config=None, options=None, out=None) -> str:
        payload: Dict[str, Any] = {
            "tool": "alinter",
            "version": __version__,
            "summary": summarize(result),
            "violations": [violation.as_dict() for violation in result.violations],
            "fixed_files": list(result.fixed_files),
            "errors": list(result.errors),
        }
        return self.write(json.dumps(payload, indent=2, sort_keys=False) + "\n", out)


class SarifReporter(Reporter):
    name = "sarif"

    def render(self, result, *, config=None, options=None, out=None) -> str:
        rule_map: Dict[str, Dict[str, Any]] = {}
        results: List[Dict[str, Any]] = []

        for violation in result.violations:
            if violation.rule_id not in rule_map:
                rule_map[violation.rule_id] = {
                    "id": violation.rule_id,
                    "name": violation.rule_id,
                    "shortDescription": {"text": violation.message},
                    "defaultConfiguration": {
                        "level": _SEVERITY_LEVEL.get(violation.severity, "warning")
                    },
                }
            region: Dict[str, Any] = {}
            if violation.line is not None:
                region["startLine"] = violation.line
                region["startColumn"] = violation.column or 1
                if violation.end_line is not None:
                    region["endLine"] = violation.end_line
                if violation.end_column is not None:
                    region["endColumn"] = violation.end_column
            physical: Dict[str, Any] = {
                "artifactLocation": {"uri": violation.path.replace("\\", "/")}
            }
            if region:
                physical["region"] = region
            entry: Dict[str, Any] = {
                "ruleId": violation.rule_id,
                "level": _SEVERITY_LEVEL.get(violation.severity, "warning"),
                "message": {"text": violation.message},
                "locations": [{"physicalLocation": physical}],
            }
            if violation.tags:
                entry["properties"] = {"tags": list(violation.tags)}
            results.append(entry)

        sarif = {
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "alinter",
                            "informationUri": "https://github.com/baba01hacker/alinter",
                            "version": __version__,
                            "rules": list(rule_map.values()),
                        }
                    },
                    "results": results,
                    "invocations": [
                        {
                            "executionSuccessful": not result.has_errors,
                            "toolExecutionNotifications": [
                                {"level": "warning", "message": {"text": message}}
                                for message in result.errors
                            ],
                        }
                    ],
                }
            ],
        }
        return self.write(json.dumps(sarif, indent=2) + "\n", out)


class JUnitReporter(Reporter):
    name = "junit"

    def render(self, result, *, config=None, options=None, out=None) -> str:
        grouped = self.group_by_file(result.violations)
        suites = ET.Element(
            "testsuites",
            {
                "name": "alinter",
                "tests": str(max(1, result.files_checked)),
                "failures": str(len(result.violations)),
            },
        )
        suite = ET.SubElement(
            suites,
            "testsuite",
            {
                "name": "alinter",
                "tests": str(max(1, len(grouped))),
                "failures": str(len(result.violations)),
                "errors": "0",
            },
        )
        if not grouped:
            ET.SubElement(suite, "testcase", {"name": "alinter", "classname": "alinter"})
        for path in sorted(grouped):
            for index, violation in enumerate(grouped[path]):
                case = ET.SubElement(
                    suite,
                    "testcase",
                    {
                        "name": f"{violation.rule_id} ({index + 1})",
                        "classname": path,
                    },
                )
                failure = ET.SubElement(
                    case,
                    "failure",
                    {
                        "message": violation.message,
                        "type": violation.severity.value,
                    },
                )
                location = f"{path}:{violation.line}" if violation.line else path
                failure.text = f"{location}: {violation.message} [{violation.rule_id}]"
        xml_bytes = ET.tostring(suites, encoding="unicode")
        return self.write('<?xml version="1.0" encoding="utf-8"?>\n' + xml_bytes + "\n", out)


class GithubReporter(Reporter):
    name = "github"

    def render(self, result, *, config=None, options=None, out=None) -> str:
        # GitHub annotation commands must not be colorized.
        lines: List[str] = []
        for violation in result.violations:
            command = {
                Severity.ERROR: "error",
                Severity.WARNING: "warning",
                Severity.INFO: "notice",
            }.get(violation.severity, "warning")
            props = [f"file={_escape_property(violation.path)}"]
            if violation.line is not None:
                props.append(f"line={violation.line}")
                props.append(f"col={violation.column or 1}")
            if violation.end_line is not None:
                props.append(f"endLine={violation.end_line}")
            if violation.end_column is not None:
                props.append(f"endColumn={violation.end_column}")
            props.append(f"title={_escape_property(violation.rule_id)}")
            message = _escape_data(violation.message)
            lines.append(f"::{command} {','.join(props)}::{message}")
        return self.write("\n".join(lines) + ("\n" if lines else ""), out)


def _escape_data(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _escape_property(value: str) -> str:
    return _escape_data(value).replace(":", "%3A").replace(",", "%2C")
