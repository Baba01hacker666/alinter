from __future__ import annotations

from alinter.config import load_config
from alinter.engine import Engine, Options
from alinter.models import Severity

BASIC = """
auto_detect: false
rules:
  - id: test/no-foo
    type: literal
    value: "FOO"
    severity: error
    files: ["**/*.txt"]
    message: "found FOO"
  - id: test/no-bar
    type: literal
    value: "BAR"
    severity: warning
    files: ["**/*.txt"]
"""


def test_basic_violation(project, lint):
    project.write("a.txt", "has FOO here\n")
    result = lint(config=BASIC, paths=["."])
    rule_ids = {v.rule_id for v in result.violations}
    assert "test/no-foo" in rule_ids
    assert result.files_checked >= 1
    assert result.has_errors


def test_only_matching_files(project, lint):
    project.write("a.txt", "FOO\n")
    project.write("b.md", "FOO\n")
    result = lint(config=BASIC, paths=["."])
    assert {v.path for v in result.violations} == {"a.txt"}


def test_select_limits_rules(project, lint):
    project.write("a.txt", "FOO BAR\n")
    result = lint(config=BASIC, paths=["."], select=("test/no-foo",))
    assert {v.rule_id for v in result.violations} == {"test/no-foo"}


def test_ignore_skips_rules(project, lint):
    project.write("a.txt", "FOO BAR\n")
    result = lint(config=BASIC, paths=["."], ignore=("test/*",))
    assert result.violations == []


def test_severity_threshold(project, lint):
    project.write("a.txt", "BAR\n")
    result = lint(config=BASIC, paths=["."], severity=Severity.ERROR)
    assert result.violations == []


def test_suppression_directive(project, lint):
    project.write("a.txt", "FOO  # alinter: disable-line=test/no-foo\n")
    result = lint(config=BASIC, paths=["."])
    assert "test/no-foo" not in {v.rule_id for v in result.violations}


def test_fix_writes_file(project, lint):
    path = project.write("a.txt", "trailing   \n")
    result = lint(paths=["."], fix=True)
    assert result.fixed_count >= 1
    assert path.read_text() == "trailing\n"


def test_fix_dry_run_does_not_write(project, lint):
    path = project.write("a.txt", "trailing   \n")
    result = lint(paths=["."], fix_dry_run=True)
    assert result.fixed_count >= 1
    assert path.read_text() == "trailing   \n"


def test_stdin_source(lint):
    result = lint(config=BASIC, stdin_text="FOO\n", stdin_filename="x.txt")
    assert result.files_checked == 1
    assert any(v.rule_id == "test/no-foo" for v in result.violations)


def test_language_detection_by_extension(project, lint):
    project.write("a.py", "print(1)\n")
    result = lint(paths=["."])
    assert any(v.rule_id == "python/no-print" for v in result.violations)


def test_language_detection_by_shebang(project, lint):
    project.write("runme", "#!/usr/bin/env python3\nprint(1)\n")
    result = lint(paths=["."])
    assert any(v.rule_id == "python/no-print" for v in result.violations)


def test_language_detection_by_filename(project, lint):
    project.write("Dockerfile", "FROM python:latest\n")
    result = lint(paths=["."])
    assert any(v.rule_id == "dockerfile/no-latest-tag" for v in result.violations)


def test_unknown_preset_reports_error(project, lint):
    result = lint(config="extends: [does-not-exist]\n", paths=["."])
    assert any("does-not-exist" in message for message in result.errors)


def test_binary_files_are_skipped(project, lint):
    project.write("blob.bin", b"\x00\x01\x02\x03")
    result = lint(paths=["."])
    assert result.files_checked == 0
    assert result.files_skipped >= 1


def test_exclude_patterns(project, lint):
    project.write("keep.txt", "FOO\n")
    project.write("skip/gone.txt", "FOO\n")
    result = lint(config=BASIC, paths=["."], exclude=("**/skip/**",))
    assert {v.path for v in result.violations} == {"keep.txt"}


def test_singleton_language_preset_overrides_generic(project, lint):
    project.write("style.css", "color: red")
    result = lint(paths=["."])
    final_newline = [v for v in result.violations if v.rule_type == "final-newline"]
    assert len(final_newline) == 1
    assert final_newline[0].rule_id == "css/final-newline"


def test_singleton_user_rule_overrides_preset(project, lint):
    project.write("style.css", "color: red")
    config = """
rules:
  - id: my/final-newline
    type: final-newline
    value: require
    severity: error
    languages: [css]
"""
    result = lint(config=config, paths=["."])
    final_newline = [v for v in result.violations if v.rule_type == "final-newline"]
    assert len(final_newline) == 1
    assert final_newline[0].rule_id == "my/final-newline"


def test_active_rules_lists_off_rules(project):
    project.write("a.py", "print(1)\n")
    config = load_config(None, cwd=str(project.root), use_user_config=False)
    options = Options(paths=["."], cwd=str(project.root))
    engine = Engine(config, options)
    active = engine.active_rules()
    assert "python/no-print" in active


def test_override_changes_preset_severity(project, lint):
    project.write("a.py", "print(1)\n")
    config = """
rules:
  - id: python/no-print
    severity: off
"""
    result = lint(config=config, paths=["."])
    assert "python/no-print" not in {v.rule_id for v in result.violations}


def test_override_can_tighten_severity(project, lint):
    project.write("a.py", "print(1)\n")
    config = """
rules:
  - id: python/no-print
    severity: error
"""
    result = lint(config=config, paths=["."])
    assert any(
        v.rule_id == "python/no-print" and v.severity is Severity.ERROR
        for v in result.violations
    )


def test_override_can_change_pattern(project, lint):
    project.write("a.py", "warn(1)\n")
    config = """
rules:
  - id: python/no-print
    pattern: '^\\s*warn\\s*\\('
    severity: warning
"""
    result = lint(config=config, paths=["."])
    assert any(v.rule_id == "python/no-print" for v in result.violations)


def test_override_of_unknown_rule_reports_error(project, lint):
    result = lint(config="rules:\n  - id: nope/no-such\n    severity: off\n", paths=["."])
    assert any("unknown rule" in message for message in result.errors)


def test_max_file_size_skips_large_files(project, lint):
    project.write("big.txt", "x" * 100)
    config = "settings:\n  max_file_size: 10\nauto_detect: false\n"
    result = lint(config=config, paths=["."])
    assert result.files_checked == 0
    assert any("larger than" in message for message in result.errors)


def test_missing_path_is_recorded(project, lint):
    result = lint(config="rules: []\n", paths=["does-not-exist.txt"])
    assert any("not found" in message for message in result.errors)


def test_unknown_check_type_is_reported(project, lint):
    config = "rules:\n  - id: x\n    type: not-a-real-type\n"
    result = lint(config=config, paths=["."])
    assert any("not-a-real-type" in message for message in result.errors)


def test_rule_exception_is_isolated(project, lint, monkeypatch):
    from alinter import engine as engine_module

    project.write("a.txt", "FOO\n")
    config = "rules:\n  - id: boom\n    type: literal\n    value: FOO\n"

    class Exploding:
        def run(self, file):
            raise RuntimeError("kaboom")

    monkeypatch.setattr(
        engine_module.Engine, "_get_check", lambda self, rule: Exploding()
    )
    result = lint(config=config, paths=["."])
    assert any("kaboom" in message for message in result.errors)


def test_allow_commands_option_runs_command_rule(project, lint):
    project.write("f.txt", "x\n")
    config = """
auto_detect: false
rules:
  - id: t/ok
    type: command
    command: "true"
    files: ["**/*.txt"]
"""
    result = lint(config=config, paths=["."], allow_commands=True)
    assert result.violations == []


def test_override_with_nested_params(project, lint):
    project.write("style.css", "color: red\n")
    config = """
rules:
  - id: css/final-newline
    params:
      value: forbid
"""
    result = lint(config=config, paths=["."])
    assert any(v.rule_id == "css/final-newline" for v in result.violations)


def test_active_rules_include_disabled(project):
    project.write("a.py", "print(1)\n")
    config = load_config(None, cwd=str(project.root), use_user_config=False)
    options = Options(paths=["."], cwd=str(project.root))
    engine = Engine(config, options)
    active = engine.active_rules(include_disabled=True)
    assert any(rule_id.startswith("python/") for rule_id in active)


def test_config_plugins_are_loaded(project, lint, monkeypatch):
    plugin = project.write(
        "my_checks.py",
        "from alinter.checks.base import Check\n"
        "class MarkerCheck(Check):\n"
        "    name = 'marker'\n"
        "    def run(self, file):\n"
        "        return []\n"
        "CHECKS = {'marker': MarkerCheck}\n",
    )
    monkeypatch.syspath_prepend(str(plugin.parent))
    project.write("a.txt", "x\n")
    config = "auto_detect: false\nplugins: [my_checks]\nrules:\n  - id: m\n    type: marker\n"
    result = lint(config=config, paths=["."])
    assert result.errors == []


def test_lint_wrapper_accepts_config_object(project):
    from alinter import lint as api_lint

    project.write("a.txt", "FOO\n")
    config_path = project.config(
        "auto_detect: false\nrules:\n  - id: t/no-foo\n    type: literal\n    value: FOO\n"
    )
    cfg = load_config(str(config_path), cwd=str(project.root), use_user_config=False)
    result = api_lint(["."], config=cfg, cwd=str(project.root))
    assert any(v.rule_id == "t/no-foo" for v in result.violations)


def test_lint_wrapper_accepts_config_path_string(project):
    from alinter import lint as api_lint

    project.write("a.txt", "FOO\n")
    config_path = project.config(
        "auto_detect: false\nrules:\n  - id: t/no-foo\n    type: literal\n    value: FOO\n"
    )
    result = api_lint(["."], config=str(config_path), cwd=str(project.root))
    assert any(v.rule_id == "t/no-foo" for v in result.violations)
