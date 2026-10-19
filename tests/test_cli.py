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
