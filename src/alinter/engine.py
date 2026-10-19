"""The lint engine: ties config, presets, checks and fixes together."""

from __future__ import annotations

import dataclasses
import fnmatch
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from .config import Config, default_user_preset_dirs, load_config
from .discovery import discover
from .fixer import apply_edits
from .ignores import Suppressions, parse_suppressions
from .models import LintResult, Rule, Severity, SourceFile, TextEdit, Violation
from .presets import PresetRepository
from .registry import CheckRegistry, get_registry
from .utils import (
    ConfigError,
    as_bool,
    as_str_list,
    detect_encoding,
    is_probably_binary,
    normalize_path,
)


@dataclass
class Options:
    """Runtime options for a lint run (mostly populated by the CLI)."""

    paths: List[str] = field(default_factory=list)
    cwd: str = "."
    config: Optional[str] = None
    no_config: bool = False
    fix: bool = False
    fix_dry_run: bool = False
    format: str = "text"
    severity: Severity = Severity.INFO
    fail_on: Severity = Severity.ERROR
    select: Tuple[str, ...] = ()
    ignore: Tuple[str, ...] = ()
    include: Tuple[str, ...] = ()
    exclude: Tuple[str, ...] = ()
    jobs: int = 0
    stdin_text: Optional[str] = None
    stdin_filename: str = "<stdin>"
    max_iterations: int = 10
    allow_commands: Optional[bool] = None
    use_gitignore: Optional[bool] = None
    color: Optional[bool] = None
    quiet: bool = False
    verbose: int = 0


def _matches_patterns(value: str, patterns: Sequence[str]) -> bool:
    return any(fnmatch.fnmatchcase(value, pattern) for pattern in patterns)


class Engine:
    """Runs checks over a set of files and returns a :class:`LintResult`."""

    def __init__(
        self,
        config: Config,
        options: Optional[Options] = None,
        registry: Optional[CheckRegistry] = None,
    ) -> None:
        self.config = config
        self.options = options or Options()
        self.registry = registry or get_registry()
        if config.plugins:
            self.registry.load_targets(config.plugins)
        self.presets = PresetRepository(self._preset_dirs())
        self._baseline_sources = {
            preset.source for preset in self.presets.presets.values() if preset.always_apply
        }
        self._preset_sources = {
            preset.source for preset in self.presets.presets.values()
        }
        self._preset_rule_cache: Dict[str, List[Rule]] = {}
        self._combined_cache: Dict[str, Dict[str, Rule]] = {}
        self._check_cache: Dict[str, Any] = {}
        self._reported_errors: Set[str] = set()
        self._rules_run: Set[str] = set()
        self._errors: List[str] = []

    # -- setup ------------------------------------------------------------

    def _preset_dirs(self) -> List[str]:
        dirs = list(self.config.preset_paths)
        dirs.extend(default_user_preset_dirs())
        return [d for d in dirs if d]

    def _allow_commands(self) -> bool:
        if self.options.allow_commands is not None:
            return bool(self.options.allow_commands)
        return as_bool(self.config.setting("allow_commands", False))

    def _enabled(self, rule_id: str) -> bool:
        select = tuple(self.config.select) + tuple(self.options.select)
        ignore = tuple(self.config.ignore) + tuple(self.options.ignore)
        if select and not _matches_patterns(rule_id, select):
            return False
        if ignore and _matches_patterns(rule_id, ignore):
            return False
        return True

    # -- rule selection ---------------------------------------------------

    def preset_rules(self, language: Optional[str]) -> List[Rule]:
        key = language or ""
        cached = self._preset_rule_cache.get(key)
        if cached is not None:
            return cached

        names: List[str] = []
        for name in self.config.extends:
            if name not in names:
                names.append(name)
        if self.config.auto_detect and language:
            if language in self.presets.presets and language not in names:
                names.append(language)
        for name in self.presets.names():
            if self.presets.presets[name].always_apply and name not in names:
                names.append(name)

        rules: List[Rule] = []
        for name in names:
            preset = self.presets.get(name)
            if preset is None:
                self._record_error(
                    f"preset:{name}",
                    f"unknown preset {name!r}; run `alinter presets` to see them all",
                )
                continue
            rules.extend(preset.build_rules())
        self._preset_rule_cache[key] = rules
        return rules

    def _rules_for(
        self, rel_path: str, language: Optional[str], include_disabled: bool = False
    ) -> List[Rule]:
        combined = self._combined_rules(language)

        selected: List[Rule] = []
        for rule in combined.values():
            if not self._enabled(rule.id):
                continue
            if include_disabled:
                if not rule.matches_path_language(rel_path, language):
                    continue
            elif not rule.scoped_to(rel_path, language):
                continue
            selected.append(rule)
        if include_disabled:
            return selected
        return self._apply_singletons(selected)

    def _combined_rules(self, language: Optional[str]) -> Dict[str, Rule]:
        """Preset rules + user rules + user overrides, keyed by rule id."""
        key = language or ""
        cached = self._combined_cache.get(key)
        if cached is not None:
            return cached

        combined: Dict[str, Rule] = {}
        for rule in self.preset_rules(language):
            combined[rule.id] = rule
        for rule in self.config.rules:
            combined[rule.id] = rule  # user rules override preset rules by id
        for rule_id, patch in self.config.overrides.items():
            base = combined.get(rule_id)
            if base is None:
                self._record_error(
                    f"override:{rule_id}",
                    f"override refers to unknown rule {rule_id!r}",
                )
                continue
            combined[rule_id] = self._apply_override(base, patch)

        self._combined_cache[key] = combined
        return combined

    def _apply_override(self, base: Rule, patch: Dict[str, Any]) -> Rule:
        params = dict(base.params)
        for key, value in patch.items():
            if key in ("type", "check", "severity", "level", "message", "description",
                       "enabled", "files", "exclude", "languages", "language", "tags",
                       "params"):
                continue
            params[key] = value
        nested = patch.get("params")
        if isinstance(nested, dict):
            params.update(nested)
        return dataclasses.replace(
            base,
            severity=Severity.coerce(patch.get("severity", patch.get("level", base.severity))),
            message=patch.get("message", base.message),
            description=patch.get("description", base.description),
            enabled=as_bool(patch.get("enabled", base.enabled), base.enabled),
            files=tuple(as_str_list(patch.get("files", base.files))),
            exclude=tuple(as_str_list(patch.get("exclude", base.exclude))),
            languages=tuple(
                as_str_list(patch.get("languages", patch.get("language", base.languages)))
            ),
            tags=tuple(as_str_list(patch.get("tags", base.tags))),
            params=params,
        )

    def _specificity(self, rule: Rule) -> int:
        if rule.source in self._baseline_sources:
            return 0
        if rule.source in self._preset_sources:
            return 1
        return 2  # user-defined

    def _apply_singletons(self, rules: List[Rule]) -> List[Rule]:
        """Keep only the most specific rule per singleton check type."""
        best: Dict[str, Rule] = {}
        passthrough: List[Rule] = []
        for rule in rules:
            check_cls = self.registry.get(rule.type)
            if check_cls is not None and getattr(check_cls, "singleton", False):
                current = best.get(rule.type)
                if current is None or self._specificity(rule) > self._specificity(current):
                    best[rule.type] = rule
            else:
                passthrough.append(rule)
        return passthrough + list(best.values())

    def _get_check(self, rule: Rule):
        check = self._check_cache.get(rule.id)
        if check is not None:
            return check if check is not False else None
        params = rule.params
        if rule.type == "command":
            params.setdefault("_allow_commands", self._allow_commands())
        try:
            check = self.registry.create(rule)
        except ConfigError as exc:
            self._record_error(rule.id, str(exc))
            self._check_cache[rule.id] = False
            return None
        self._check_cache[rule.id] = check
        return check

    def _record_error(self, key: str, message: str) -> None:
        if key in self._reported_errors:
            return
        self._reported_errors.add(key)
        self._errors.append(message)

    # -- source loading ---------------------------------------------------

    def _detect_language(self, filename: str, first_line: Optional[str]) -> Optional[str]:
        extension = os.path.splitext(filename)[1].lower()
        return self.presets.index.detect(filename, extension, first_line)

    def _source_from_text(self, text: str, name: str) -> SourceFile:
        first_line = text.splitlines()[0] if text.splitlines() else None
        return SourceFile(
            path=name,
            rel_path=normalize_path(name),
            text=text,
            encoding="utf-8",
            language=self._detect_language(os.path.basename(name), first_line),
            size=len(text.encode("utf-8", errors="replace")),
        )

    def _load_source(self, path: str, rel_path: str) -> Optional[SourceFile]:
        try:
            data = Path(path).read_bytes()
        except OSError as exc:
            self._record_error(path, f"could not read {rel_path}: {exc}")
            return None
        max_size = int(self.config.setting("max_file_size", 5_000_000))
        if max_size and len(data) > max_size:
            self._record_error(path, f"{rel_path}: skipped (larger than {max_size} bytes)")
            return None
        if is_probably_binary(data):
            return None
        encoding, has_bom = detect_encoding(
            data, str(self.config.setting("encoding", "utf-8"))
        )
        text = data.decode(encoding, errors="replace")
        first_line = text.splitlines()[0] if text.splitlines() else None
        filename = os.path.basename(rel_path)
        return SourceFile(
            path=path,
            rel_path=rel_path,
            text=text,
            encoding=encoding,
            has_bom=has_bom,
            language=self._detect_language(filename, first_line),
            size=len(data),
        )

    def _write_source(self, source: SourceFile, text: str) -> None:
        encoding = "utf-8-sig" if source.has_bom else (
            "utf-8" if source.encoding == "utf-8-sig" else source.encoding
        )
        try:
            payload = text.encode(encoding)
        except (UnicodeEncodeError, LookupError):
            payload = text.encode("utf-8")
        Path(source.path).write_bytes(payload)

    # -- linting ----------------------------------------------------------

    def _lint_source(self, source: SourceFile, suppressions: Suppressions) -> List[Violation]:
        violations: List[Violation] = []
        for rule in self._rules_for(source.rel_path, source.language):
            check = self._get_check(rule)
            if check is None:
                continue
            self._rules_run.add(rule.id)
            try:
                produced = list(check.run(source))
            except Exception as exc:  # noqa: BLE001 - one bad rule must not stop the run
                self._record_error(rule.id, f"rule {rule.id}: {exc}")
                continue
            for violation in produced:
                if suppressions.is_suppressed(violation.rule_id, violation.line):
                    continue
                if violation.severity.rank < self.options.severity.rank:
                    continue
                violations.append(violation)
        return violations

    def _lint_all(
        self, sources: Sequence[SourceFile]
    ) -> Tuple[List[Violation], Dict[str, List[TextEdit]]]:
        violations: List[Violation] = []
        edits: Dict[str, List[TextEdit]] = {}
        for source in sources:
            suppressions = parse_suppressions(source.text)
            for violation in self._lint_source(source, suppressions):
                violations.append(violation)
                if violation.fix is not None:
                    edits.setdefault(source.path, []).append(violation.fix)
        return violations, edits

    # -- planning ---------------------------------------------------------

    def active_rules(self, include_disabled: bool = False) -> Dict[str, Dict[str, Any]]:
        """Return ``rule_id -> info`` for the currently discovered files."""
        use_gitignore = self.options.use_gitignore
        if use_gitignore is None:
            use_gitignore = as_bool(self.config.setting("use_gitignore", True))
        discovery = discover(
            self.options.paths or ["."],
            cwd=self.options.cwd,
            include=tuple(self.config.include) + tuple(self.options.include),
            exclude=tuple(self.config.excludes()) + tuple(self.options.exclude),
            use_gitignore=bool(use_gitignore),
        )
        active: Dict[str, Dict[str, Any]] = {}
        languages: Set[str] = set()
        for item in discovery.files:
            source = self._load_source(item.path, item.rel_path)
            if source is None:
                continue
            if source.language:
                languages.add(source.language)
            for rule in self._rules_for(source.rel_path, source.language, include_disabled):
                info = active.setdefault(
                    rule.id,
                    {
                        "type": rule.type,
                        "severity": rule.severity.value,
                        "source": rule.source or "config",
                        "description": rule.description,
                        "languages": set(),
                        "files": set(),
                    },
                )
                if source.language:
                    info["languages"].add(source.language)
                info["files"].add(source.rel_path)
        return active

    # -- run --------------------------------------------------------------

    def run(self) -> LintResult:
        started = time.perf_counter()
        self._errors: List[str] = []
        result = LintResult()

        sources: List[SourceFile] = []
        if self.options.stdin_text is not None:
            sources.append(
                self._source_from_text(self.options.stdin_text, self.options.stdin_filename)
            )
            result.files_checked = 1
        else:
            use_gitignore = self.options.use_gitignore
            if use_gitignore is None:
                use_gitignore = as_bool(self.config.setting("use_gitignore", True))
            discovery = discover(
                self.options.paths or ["."],
                cwd=self.options.cwd,
                include=tuple(self.config.include) + tuple(self.options.include),
                exclude=tuple(self.config.excludes()) + tuple(self.options.exclude),
                use_gitignore=bool(use_gitignore),
            )
            for missing in discovery.missing:
                self._record_error(missing, f"path not found: {missing}")
            for item in discovery.files:
                source = self._load_source(item.path, item.rel_path)
                if source is None:
                    result.files_skipped += 1
                    continue
                sources.append(source)
            result.files_checked = len(sources)

        # Validate explicitly requested presets up front.
        for name in self.config.extends:
            if self.presets.get(name) is None:
                self._record_error(
                    f"preset:{name}",
                    f"unknown preset {name!r}; run `alinter presets` to see them all",
                )

        if self.options.fix or self.options.fix_dry_run:
            self._fix_loop(sources, result)

        violations, _ = self._lint_all(sources)
        violations.sort(key=lambda item: item.sort_key())
        result.violations = violations
        result.rules_run = len(self._rules_run)
        result.errors = list(self._errors)
        result.duration = time.perf_counter() - started
        return result

    def _fix_loop(self, sources: List[SourceFile], result: LintResult) -> None:
        dry_run = self.options.fix_dry_run
        for _ in range(max(1, self.options.max_iterations)):
            _, edits = self._lint_all(sources)
            if not edits:
                break
            if dry_run:
                for path, path_edits in edits.items():
                    rel = next((s.rel_path for s in sources if s.path == path), path)
                    if rel not in result.fixed_files:
                        result.fixed_files.append(rel)
                    result.fixed_count += len(path_edits)
                break
            changed = False
            for source in sources:
                source_edits = edits.get(source.path)
                if not source_edits:
                    continue
                new_text, applied = apply_edits(source.text, source_edits)
                if applied and new_text != source.text:
                    self._write_source(source, new_text)
                    source.text = new_text
                    source._line_starts = None
                    source.size = len(new_text.encode("utf-8", errors="replace"))
                    result.fixed_count += applied
                    if source.rel_path not in result.fixed_files:
                        result.fixed_files.append(source.rel_path)
                    changed = True
            if not changed:
                break


def lint(
    paths: Optional[Sequence[str]] = None,
    *,
    config: Optional[Any] = None,
    cwd: str = ".",
    **kwargs: Any,
) -> LintResult:
    """Convenience wrapper: load config and run the engine.

    ``config`` may be a :class:`Config`, a path to a config file, or ``None``
    (in which case normal discovery applies). Any extra keyword arguments are
    forwarded to :class:`Options`.
    """
    options = Options(paths=list(paths) if paths else ["."], cwd=cwd, **kwargs)
    if isinstance(config, Config):
        resolved = config
    elif isinstance(config, (str, os.PathLike)):
        options.config = str(config)
        resolved = load_config(options.config, cwd=cwd, no_config=options.no_config)
    else:
        resolved = load_config(options.config, cwd=cwd, no_config=options.no_config)
    return Engine(resolved, options).run()
