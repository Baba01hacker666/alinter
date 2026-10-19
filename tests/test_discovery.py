from __future__ import annotations

from pathlib import Path

import pytest

from alinter import discovery
from alinter.discovery import discover


def test_discovers_files_sorted(project):
    project.write("b.txt", "b\n")
    project.write("a.txt", "a\n")
    project.write("sub/c.txt", "c\n")
    result = discover(["."], cwd=str(project.root))
    assert [item.rel_path for item in result.files] == ["a.txt", "b.txt", "sub/c.txt"]
    assert result.missing == []
    # Paths are absolute on disk.
    assert all(Path(item.path).is_absolute() for item in result.files)


def test_explicit_file_target(project):
    project.write("only.txt", "x\n")
    project.write("other.txt", "y\n")
    result = discover(["only.txt"], cwd=str(project.root))
    assert [item.rel_path for item in result.files] == ["only.txt"]


def test_missing_path_is_recorded(project):
    result = discover(["nope.txt"], cwd=str(project.root))
    assert result.files == []
    assert result.missing == ["nope.txt"]


def test_duplicate_targets_are_deduplicated(project):
    project.write("a.txt", "x\n")
    result = discover([".", "a.txt"], cwd=str(project.root))
    assert [item.rel_path for item in result.files] == ["a.txt"]


def test_include_filters_files(project):
    project.write("keep.py", "x\n")
    project.write("skip.txt", "y\n")
    result = discover(["."], cwd=str(project.root), include=["**/*.py"])
    assert [item.rel_path for item in result.files] == ["keep.py"]
    assert result.skipped == 1


def test_exclude_prunes_directories(project):
    project.write("keep/a.txt", "x\n")
    project.write("skip/b.txt", "y\n")
    result = discover(["."], cwd=str(project.root), exclude=["skip"])
    assert [item.rel_path for item in result.files] == ["keep/a.txt"]


def test_exclude_with_trailing_slash_prunes(project):
    project.write("build/out.js", "x\n")
    project.write("src/app.js", "y\n")
    result = discover(["."], cwd=str(project.root), exclude=["build/"])
    assert [item.rel_path for item in result.files] == ["src/app.js"]


def test_empty_paths_default_to_cwd(project):
    project.write("a.txt", "x\n")
    result = discover([], cwd=str(project.root))
    assert [item.rel_path for item in result.files] == ["a.txt"]


def test_gitignore_is_honoured(project):
    if discovery.pathspec is None:  # pragma: no cover - optional dependency
        pytest.skip("pathspec is not installed")
    project.write(".gitignore", "ignored.txt\nbuild/\n")
    project.write("ignored.txt", "x\n")
    project.write("build/gen.txt", "x\n")
    project.write("kept.txt", "x\n")
    result = discover(["."], cwd=str(project.root), use_gitignore=True)
    rels = {item.rel_path for item in result.files}
    assert rels == {".gitignore", "kept.txt"}


def test_gitignore_not_used_without_flag(project):
    project.write(".gitignore", "ignored.txt\n")
    project.write("ignored.txt", "x\n")
    result = discover(["."], cwd=str(project.root))
    assert "ignored.txt" in {item.rel_path for item in result.files}


def test_load_gitignore_absent_when_pathspec_missing(project, monkeypatch):
    project.write(".gitignore", "x\n")
    monkeypatch.setattr(discovery, "pathspec", None)
    assert discovery._load_gitignore(str(project.root)) is None


def test_load_gitignore_none_when_no_patterns(project):
    assert discovery._load_gitignore(str(project.root)) is None


def test_load_gitignore_reads_git_info_exclude(project):
    if discovery.pathspec is None:  # pragma: no cover - optional dependency
        pytest.skip("pathspec is not installed")
    project.write(".git/info/exclude", "secret.txt\n")
    project.write("secret.txt", "x\n")
    spec = discovery._load_gitignore(str(project.root))
    assert spec is not None
    assert spec.match_file("secret.txt")
