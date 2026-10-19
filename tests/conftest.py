"""Shared pytest fixtures and small factories."""

from __future__ import annotations

from pathlib import Path

import pytest

from alinter.config import build_rule, load_config
from alinter.engine import Engine, Options
from alinter.models import SourceFile
from alinter.registry import get_registry


class Project:
    def __init__(self, root: Path) -> None:
        self.root = root

    def write(self, rel: str, content) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        return path

    def config(self, text: str, rel: str = ".alinter.yaml") -> Path:
        return self.write(rel, text)


@pytest.fixture
def project(tmp_path: Path) -> Project:
    return Project(tmp_path)


@pytest.fixture
def lint(project: Project):
    def _lint(config=None, paths=None, config_rel=".alinter.yaml", **options):
        config_path = None
        if config is not None:
            config_path = str(project.config(config, config_rel))
        cfg = load_config(config_path, cwd=str(project.root), use_user_config=False)
        opts = Options(paths=list(paths or ["."]), cwd=str(project.root), **options)
        return Engine(cfg, opts).run()

    return _lint


@pytest.fixture
def build_check():
    def _build(rule_dict):
        rule = build_rule(rule_dict)
        return get_registry().create(rule)

    return _build


@pytest.fixture
def build_rule_obj():
    return build_rule


@pytest.fixture
def source_factory():
    def _make(text: str, rel: str = "f.py", language=None, encoding="utf-8", has_bom=False):
        return SourceFile(
            path=rel,
            rel_path=rel,
            text=text,
            language=language,
            encoding=encoding,
            has_bom=has_bom,
            size=len(text.encode("utf-8", errors="replace")),
        )

    return _make
