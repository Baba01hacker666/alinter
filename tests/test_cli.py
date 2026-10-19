from __future__ import annotations

import io
import json

from alinter.cli import main


def test_version(capsys):
    assert main(["version"]) == 0
    assert "alinter" in capsys.readouterr().out


def test_types(capsys):
    assert main(["types"]) == 0
    out = capsys.readouterr().out
    assert "regex" in out
    assert "structure" in out


def test_presets_list(capsys):
    assert main(["presets"]) == 0
    out = capsys.readouterr().out
    assert "python" in out
    assert "generic" in out


def test_presets_show(capsys):
    assert main(["presets", "--show", "python"]) == 0
    out = capsys.readouterr().out
    assert "python/no-print" in out


def test_explain(capsys):
    assert main(["explain", "python/no-print"]) == 0
    out = capsys.readouterr().out
    assert "python/no-print" in out
    assert "regex" in out


def test_check_finds_error(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.py").write_text("try:\n    pass\nexcept:\n    pass\n")
    code = main(["--no-config", "."])
    out = capsys.readouterr().out
    assert code == 1
    assert "python/no-bare-except" in out


def test_check_clean_exit_zero(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.py").write_text("x = 1\n")
    assert main(["--no-config", "."]) == 0


def test_check_json_format(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.py").write_text("print(1)\n")
    code = main(["--no-config", "--format", "json", "."])
    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["files"] == 1
    assert code == 0


def test_check_strict_fails_on_warning(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.py").write_text("print(1)\n")
    code = main(["--no-config", "--strict", "."])
    assert code == 1


def test_stdin(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.stdin", io.StringIO("print(1)\n"))
    main(["--no-config", "--stdin", "--stdin-filename", "x.py"])
    out = capsys.readouterr().out
    assert "python/no-print" in out


def test_validate(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    config = tmp_path / ".alinter.yaml"
    config.write_text("version: 1\nrules: []\n")
    assert main(["validate", "--config", str(config)]) == 0


def test_validate_flags_unknown_preset(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    config = tmp_path / ".alinter.yaml"
    config.write_text("extends: [not-a-preset]\n")
    assert main(["validate", "--config", str(config)]) == 1


def test_init_writes_file(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["init", str(tmp_path)]) == 0
    target = tmp_path / ".alinter.yaml"
    assert target.exists()
    # A second run refuses to overwrite.
    assert main(["init", str(tmp_path)]) == 2
    assert main(["init", str(tmp_path), "--force"]) == 0


def test_rules_command(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.py").write_text("x = 1\n")
    assert main(["rules", ".", "--no-config"]) == 0
    assert "python/" in capsys.readouterr().out


def test_bad_config_exit_code(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    config = tmp_path / "bad.yaml"
    config.write_text("rules: 42\n")
    assert main(["check", "--config", str(config)]) == 2


def test_presets_json(capsys):
    assert main(["presets", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert any(item["name"] == "python" for item in payload)


def test_presets_show_unknown_exits_2(capsys):
    assert main(["presets", "--show", "no-such-preset"]) == 2


def test_presets_show_json(capsys):
    assert main(["presets", "--show", "python", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["name"] == "python"


def test_explain_unknown_exits_2(capsys):
    assert main(["explain", "nope/no-such-rule"]) == 2


def test_rules_json_and_all(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.py").write_text("x = 1\n")
    assert main(["rules", ".", "--no-config", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert "python/no-print" in payload
    assert main(["rules", ".", "--no-config", "--all"]) == 0


def test_langs_and_json(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.py").write_text("x = 1\n")
    assert main(["langs", ".", "--no-config"]) == 0
    assert "python" in capsys.readouterr().out
    assert main(["langs", ".", "--no-config", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert "python" in payload


def test_validate_flags_bad_rule_type(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    config = tmp_path / ".alinter.yaml"
    config.write_text("rules:\n  - id: x\n    type: not-a-type\n")
    assert main(["validate", "--config", str(config)]) == 1


def test_init_with_preset(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["init", str(tmp_path), "--preset", "python"]) == 0
    assert "extends: [python]" in (tmp_path / ".alinter.yaml").read_text()


def test_check_fail_on_none_always_zero(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.py").write_text("try:\n    pass\nexcept:\n    pass\n")
    assert main(["--no-config", "--fail-on", "none", "."]) == 0


def test_check_select_accepts_comma_separated(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.py").write_text("print(1)\n")
    code = main(["--no-config", "--select", "python/no-print,generic/*", "."])
    out = capsys.readouterr().out
    assert "python/no-print" in out
    assert code == 0


def test_check_github_format(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.py").write_text("print(1)\n")
    assert main(["--no-config", "--format", "github", "."]) == 0
    assert "::warning" in capsys.readouterr().out


def test_check_sarif_and_junit_formats(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.py").write_text("print(1)\n")
    assert main(["--no-config", "--format", "sarif", "."]) == 0
    sarif = json.loads(capsys.readouterr().out)
    assert sarif["version"] == "2.1.0"
    assert main(["--no-config", "--format", "junit", "."]) == 0
    assert "<testsuites" in capsys.readouterr().out


def test_check_quiet_prints_only_summary(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.py").write_text("print(1)\n")
    assert main(["--no-config", "--quiet", "--no-color", "."]) == 0
    out = capsys.readouterr().out
    assert "python/no-print" not in out


def test_check_reports_config_errors_to_stderr(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    config = tmp_path / ".alinter.yaml"
    config.write_text("extends: [does-not-exist]\nrules: []\n")
    main(["check", "--config", str(config), "."])
    captured = capsys.readouterr()
    assert "does-not-exist" in captured.err


def test_module_entrypoint():
    import subprocess
    import sys

    proc = subprocess.run(
        [sys.executable, "-m", "alinter", "version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "alinter" in proc.stdout
