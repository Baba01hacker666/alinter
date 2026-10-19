"""File discovery: turn CLI paths into a deterministic list of files to lint."""

from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from .utils import normalize_path, path_matches

try:
    import pathspec  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - optional dependency
    pathspec = None  # type: ignore[assignment]


@dataclass
class DiscoveredFile:
    path: str  # absolute path on disk
    rel_path: str  # path relative to the working directory (POSIX)


@dataclass
class DiscoveryResult:
    files: list[DiscoveredFile] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    skipped: int = 0


def _load_gitignore(cwd: str) -> pathspec.PathSpec | None:
    if pathspec is None:
        return None
    patterns: list[str] = []
    for name in (".gitignore", os.path.join(".git", "info", "exclude")):
        candidate = Path(cwd) / name
        if candidate.is_file():
            try:
                patterns.extend(candidate.read_text(encoding="utf-8").splitlines())
            except OSError:
                continue
    if not patterns:
        return None
    # pathspec >= 0.12 ships GitIgnoreSpec; older versions only understand
    # "gitwildmatch" (which newer versions deprecate).
    spec_builder = getattr(pathspec, "GitIgnoreSpec", None)
    if spec_builder is not None:
        return spec_builder.from_lines(patterns)
    return pathspec.PathSpec.from_lines("gitwildmatch", patterns)


def discover(
    paths: Sequence[str],
    *,
    cwd: str = ".",
    include: Sequence[str] = (),
    exclude: Sequence[str] = (),
    use_gitignore: bool = False,
) -> DiscoveryResult:
    """Collect files under ``paths`` matching ``include`` and not ``exclude``."""
    result = DiscoveryResult()
    gitignore = _load_gitignore(cwd) if use_gitignore else None
    seen = set()

    def rel_of(path: Path) -> str:
        try:
            rel = os.path.relpath(str(path), cwd)
        except ValueError:  # pragma: no cover - different drives on Windows
            rel = str(path)
        return normalize_path(rel)

    def accept(path: Path) -> None:
        rel = rel_of(path)
        if rel in seen:
            return
        if include and not path_matches(rel, include):
            result.skipped += 1
            return
        if exclude and path_matches(rel, exclude):
            result.skipped += 1
            return
        if exclude and path_matches(rel + "/_", exclude):
            result.skipped += 1
            return
        if gitignore is not None and gitignore.match_file(rel):
            result.skipped += 1
            return
        seen.add(rel)
        result.files.append(DiscoveredFile(path=str(path.resolve()), rel_path=rel))

    def prune(directory: Path) -> bool:
        rel = rel_of(directory)
        if rel in (".", ""):
            return False
        return bool(exclude and (path_matches(rel + "/_", exclude) or path_matches(rel, exclude)))

    targets = [p for p in paths if p] or ["."]
    for target in targets:
        path = Path(target)
        if not path.is_absolute():
            path = Path(cwd) / path
        if not path.exists():
            result.missing.append(str(target))
            continue
        if path.is_file():
            accept(path)
            continue
        for root, dirs, files in os.walk(path, followlinks=False):
            root_path = Path(root)
            if prune(root_path):
                dirs[:] = []
                continue
            dirs[:] = sorted(
                d for d in dirs if not prune(root_path / d)
            )
            for name in sorted(files):
                accept(root_path / name)

    result.files.sort(key=lambda item: item.rel_path)
    return result
