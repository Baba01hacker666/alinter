"""Command line interface for alinter."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, List, Optional, Sequence

from . import __version__
from .config import Config, default_user_preset_dirs, load_config
from .engine import Engine, Options
from .models import Rule, Severity
from .presets import PresetRepository
from .registry import get_registry
from .reporters import get_reporter, reporter_names
from .utils import ConfigError

COMMANDS = ("check", "init", "presets", "rules", "explain", "langs", "validate", "types", "version")

INIT_TEMPLATE = """\
# alinter configuration
# Docs: https://github.com/Baba01hacker666/alinter
version: 1

# Automatically apply language/format presets based on file type.
auto_detect: true

# Pull in additional presets explicitly (names are shown by `alinter presets`).
# extends: [python, yaml]

# Files/directories to skip (glob patterns).
exclude:
  - "**/.git/**"
  - "**/node_modules/**"

# Turn individual rules off by id (fnmatch patterns allowed).
ignore: []

settings:
  encoding: utf-8
  max_file_size: 5000000
  use_gitignore: true
  # Opt in to running `command` checks:
  allow_commands: false

rules:
  # Add your own rules here. Anything not understood as a rule field becomes a
  # parameter for the chosen check `type`. See `alinter types`.
  - id: custom/no-todo
    type: regex
    pattern: '\\b(TODO|FIXME)\\b'
    mode: forbidden
    severity: info
    message: "unresolved {match} marker"
    files: ["**/*"]
"""


def _csv(values: Optional[Sequence[str]]) -> List[str]:
    out: List[str] = []
    for value in values or []:
        for part in str(value).split(","):
            part = part.strip()
            if part:
                out.append(part)
    return out


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="alinter",
        description="A universal, config-driven linter. Lint anything with declarative rules.",
    )
    parser.add_argument("--version", action="version", version=f"alinter {__version__}")
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    # -- check ------------------------------------------------------------
    check = subparsers.add_parser(
        "check", aliases=["lint", "run"], help="lint files and report violations"
    )
    check.add_argument("paths", nargs="*", help="files or directories to lint")
    check.add_argument("-c", "--config", help="path to a config file")
    check.add_argument(
        "-f", "--format", default="text",
        choices=reporter_names(), help="output format (default: text)",
    )
    check.add_argument("--fix", action="store_true", help="apply available fixes in place")
    check.add_argument(
        "--fix-dry-run", "--diff", dest="fix_dry_run", action="store_true",
        help="show what would be fixed without writing files",
    )
    check.add_argument("--select", action="append", default=[], metavar="RULE",
                       help="only run matching rule ids (fnmatch); repeatable")
    check.add_argument("--ignore", action="append", default=[], metavar="RULE",
                       help="skip matching rule ids (fnmatch); repeatable")
    check.add_argument("--include", action="append", default=[], metavar="GLOB",
                       help="only lint files matching this glob; repeatable")
    check.add_argument("--exclude", action="append", default=[], metavar="GLOB",
                       help="skip files matching this glob; repeatable")
    check.add_argument("--preset", action="append", default=[], metavar="NAME",
                       help="force a preset on (repeatable)")
    check.add_argument("--severity", default="info",
                       choices=["info", "warning", "error"],
                       help="minimum severity to report (default: info)")
    check.add_argument("--fail-on", default=None,
                       choices=["info", "warning", "error", "none"],
                       help="exit non-zero on this severity or worse (default: error)")
    check.add_argument("--strict", action="store_true",
                       help="same as --fail-on warning")
    check.add_argument("--stdin", action="store_true",
                       help="read a single file from standard input")
    check.add_argument("--stdin-filename", default="<stdin>",
                       help="file name to assume for --stdin")
    check.add_argument("--allow-commands", action="store_true",
                       help="allow rules of type 'command' to run external programs")
    check.add_argument("--no-gitignore", action="store_true",
                       help="do not honour .gitignore")
    check.add_argument("--jobs", "-j", type=int, default=0,
                       help="number of parallel workers (reserved; currently ignored)")
    color = check.add_mutually_exclusive_group()
    color.add_argument("--color", dest="color", action="store_true", default=None,
                       help="force colored output")
    color.add_argument("--no-color", dest="color", action="store_false",
                       help="disable colored output")
    check.add_argument("-q", "--quiet", action="store_true", help="only print the summary")
    check.add_argument("-v", "--verbose", action="count", default=0, help="increase verbosity")
    _add_config_ignoring(check)

    # -- init -------------------------------------------------------------
    init = subparsers.add_parser("init", help="write a starter .alinter.yaml")
    init.add_argument("path", nargs="?", default=".", help="directory to write into")
    init.add_argument("--preset", action="append", default=[], metavar="NAME",
                      help="preset names to enable in the template")
    init.add_argument("--force", action="store_true", help="overwrite an existing file")

    # -- presets ----------------------------------------------------------
    presets = subparsers.add_parser("presets", help="list available presets")
    presets.add_argument("--show", metavar="NAME", help="show one preset in detail")
    presets.add_argument("--json", action="store_true", help="emit JSON")

    # -- rules ------------------------------------------------------------
    rules = subparsers.add_parser("rules", help="list the rules that apply to files")
    rules.add_argument("paths", nargs="*", help="files or directories to inspect")
    rules.add_argument("-c", "--config")
    rules.add_argument("--preset", action="append", default=[])
    rules.add_argument("--json", action="store_true")
    rules.add_argument("--all", action="store_true",
                       help="include disabled/off rules")
    _add_config_ignoring(rules)

    # -- explain ----------------------------------------------------------
    explain = subparsers.add_parser("explain", help="explain a rule by id")
    explain.add_argument("rule_id")
    explain.add_argument("-c", "--config")
    _add_config_ignoring(explain)

    # -- langs ------------------------------------------------------------
    langs = subparsers.add_parser("langs", help="show detected languages for files")
    langs.add_argument("paths", nargs="*")
    langs.add_argument("-c", "--config")
    langs.add_argument("--json", action="store_true")
    _add_config_ignoring(langs)

    # -- validate ---------------------------------------------------------
    validate = subparsers.add_parser("validate", help="validate configuration and rules")
    validate.add_argument("-c", "--config")
    validate.add_argument("paths", nargs="*")
    _add_config_ignoring(validate)

    # -- types ------------------------------------------------------------
    subparsers.add_parser("types", help="list built-in check types")

    # -- version ----------------------------------------------------------
    subparsers.add_parser("version", help="print the version")

    return parser


def _add_config_ignoring(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--no-config", action="store_true", help="ignore config files")
    parser.add_argument("--no-user-config", action="store_true",
                        help="ignore the global user config")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _die(message: str, code: int = 2) -> int:
    print(f"alinter: error: {message}", file=sys.stderr)
    return code


def _resolve_config(args: argparse.Namespace) -> Config:
    config = load_config(
        getattr(args, "config", None),
        cwd=os.getcwd(),
        no_config=getattr(args, "no_config", False),
        use_user_config=not getattr(args, "no_user_config", False),
    )
    forced = list(getattr(args, "preset", []) or [])
    if forced:
        config.extends = tuple(dict.fromkeys([*config.extends, *forced]))
    return config


def _build_options(args: argparse.Namespace, paths: Sequence[str]) -> Options:
    stdin_text = sys.stdin.read() if getattr(args, "stdin", False) else None
    fail_on = "error"
    if getattr(args, "fail_on", None):
        fail_on = args.fail_on
    elif getattr(args, "strict", False):
        fail_on = "warning"
    return Options(
        paths=list(paths),
        cwd=os.getcwd(),
        config=getattr(args, "config", None),
        no_config=getattr(args, "no_config", False),
        fix=getattr(args, "fix", False),
        fix_dry_run=getattr(args, "fix_dry_run", False),
        format=getattr(args, "format", "text"),
        severity=Severity.coerce(getattr(args, "severity", "info")),
        fail_on=Severity.coerce(fail_on),
        select=tuple(_csv(getattr(args, "select", []))),
        ignore=tuple(_csv(getattr(args, "ignore", []))),
        include=tuple(_csv(getattr(args, "include", []))),
        exclude=tuple(_csv(getattr(args, "exclude", []))),
        jobs=getattr(args, "jobs", 0) or 0,
        stdin_text=stdin_text,
        stdin_filename=getattr(args, "stdin_filename", "<stdin>"),
        allow_commands=True if getattr(args, "allow_commands", False) else None,
        use_gitignore=False if getattr(args, "no_gitignore", False) else None,
        color=getattr(args, "color", None),
        quiet=getattr(args, "quiet", False),
        verbose=getattr(args, "verbose", 0) or 0,
    )


def _preset_repository(config: Config) -> PresetRepository:
    dirs = list(config.preset_paths) + default_user_preset_dirs()
    return PresetRepository([d for d in dirs if d])


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_check(args: argparse.Namespace) -> int:
    try:
        config = _resolve_config(args)
        options = _build_options(args, args.paths or ["."])
        result = Engine(config, options).run()
        reporter = get_reporter(options.format)
        reporter.render(result, config=config, options=options, out=sys.stdout)
    except ConfigError as exc:
        return _die(str(exc))

    if result.errors and options.format == "text":
        for message in result.errors:
            print(f"alinter: {message}", file=sys.stderr)

    threshold = options.fail_on
    if threshold is Severity.OFF:
        return 0
    failing = [v for v in result.violations if v.severity.rank >= threshold.rank]
    return 1 if failing else 0


def cmd_init(args: argparse.Namespace) -> int:
    target = os.path.join(args.path, ".alinter.yaml")
    if os.path.exists(target) and not args.force:
        return _die(f"{target} already exists (use --force to overwrite)")
    content = INIT_TEMPLATE
    if args.preset:
        names = ", ".join(args.preset)
        content = content.replace(
            "# extends: [python, yaml]", f"extends: [{names}]"
        )
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(content)
    print(f"Wrote {target}")
    return 0


def cmd_presets(args: argparse.Namespace) -> int:
    config = _resolve_config(args)
    repository = _preset_repository(config)

    if args.show:
        preset = repository.get(args.show)
        if preset is None:
            return _die(f"unknown preset {args.show!r}")
        if args.json:
            print(json.dumps(preset.raw, indent=2))
            return 0
        print(f"{preset.name} ({preset.language})")
        if preset.description:
            print(f"  {preset.description}")
        detect = ", ".join(
            f"{key}={value}" for key, value in preset.detect.items() if value
        )
        print(f"  detect: {detect or '(always)'}")
        print(f"  source: {preset.source}")
        print(f"  rules: {len(preset.raw_rules)}")
        for rule in preset.build_rules():
            print(f"    - {rule.id}  [{rule.severity.value}]  ({rule.type})")
        return 0

    if args.json:
        payload = [
            {
                "name": preset.name,
                "language": preset.language,
                "description": preset.description,
                "always_apply": preset.always_apply,
                "detect": preset.detect,
                "rules": len(preset.raw_rules),
                "source": preset.source,
            }
            for preset in (repository.presets[name] for name in repository.names())
        ]
        print(json.dumps(payload, indent=2))
        return 0

    print("Available presets:")
    for name in repository.names():
        preset = repository.presets[name]
        suffix = " (always applied)" if preset.always_apply else ""
        print(f"  {name:<12} {preset.description}{suffix}")
    for error in repository.errors:
        print(f"alinter: {error}", file=sys.stderr)
    return 0


def cmd_rules(args: argparse.Namespace) -> int:
    try:
        config = _resolve_config(args)
        options = _build_options(args, args.paths or ["."])
        engine = Engine(config, options)
        active = engine.active_rules(include_disabled=args.all)
    except ConfigError as exc:
        return _die(str(exc))

    if args.json:
        payload = {
            rule_id: {**info, "languages": sorted(info["languages"]),
                      "files": sorted(info["files"])}
            for rule_id, info in active.items()
        }
        print(json.dumps(payload, indent=2))
        return 0

    print(f"{len(active)} rules active for {len(options.paths)} path(s):")
    for rule_id in sorted(active):
        info = active[rule_id]
        languages = ",".join(sorted(info["languages"])) or "-"
        print(f"  {rule_id:<40} {info['severity']:<8} {info['type']:<22} [{languages}]")
    return 0


def _all_rules(config: Config, repository: PresetRepository) -> Dict[str, List[str]]:
    """Map rule id -> list of sources that define it."""
    found: Dict[str, List[str]] = {}
    for rule in config.rules:
        found.setdefault(rule.id, []).append(rule.source or "config")
    for name in repository.names():
        for rule in repository.presets[name].build_rules():
            found.setdefault(rule.id, []).append(name)
    return found


def cmd_explain(args: argparse.Namespace) -> int:
    try:
        config = _resolve_config(args)
    except ConfigError as exc:
        return _die(str(exc))
    repository = _preset_repository(config)
    rule_id = args.rule_id

    rule: Optional[Rule] = config.find_rule(rule_id)
    defined_in = [
        name for name in repository.names()
        if any(r.id == rule_id for r in repository.presets[name].build_rules())
    ]
    if rule is None:
        for name in defined_in:
            matches = [r for r in repository.presets[name].build_rules() if r.id == rule_id]
            if matches:
                rule = matches[0]
                break
    if rule is None:
        return _die(f"no rule named {rule_id!r} (try `alinter rules`)")

    print(f"{rule.id}")
    if rule.description:
        print(f"  description: {rule.description}")
    print(f"  type:        {rule.type}")
    print(f"  severity:    {rule.severity.value}")
    if rule.languages:
        print(f"  languages:   {', '.join(rule.languages)}")
    if rule.files:
        print(f"  files:       {', '.join(rule.files)}")
    if rule.tags:
        print(f"  tags:        {', '.join(rule.tags)}")
    if rule.source:
        print(f"  defined in:  {rule.source}")
    if defined_in:
        print(f"  also in:     {', '.join(defined_in)}")
    print("  params:")
    for key, value in sorted(rule.params.items()):
        print(f"    {key}: {value!r}")
    registry = get_registry()
    check_cls = registry.get(rule.type)
    if check_cls is not None and check_cls.help:
        print(f"  check help:  {check_cls.help}")
    return 0


def cmd_langs(args: argparse.Namespace) -> int:
    try:
        config = _resolve_config(args)
        options = _build_options(args, args.paths or ["."])
        engine = Engine(config, options)
    except ConfigError as exc:
        return _die(str(exc))

    from .discovery import discover

    discovery = discover(
        options.paths,
        cwd=options.cwd,
        include=tuple(config.include) + tuple(options.include),
        exclude=tuple(config.excludes()) + tuple(options.exclude),
        use_gitignore=bool(config.setting("use_gitignore", True)),
    )
    result: Dict[str, List[str]] = {}
    for item in discovery.files:
        source = engine._load_source(item.path, item.rel_path)
        if source is None:
            continue
        result.setdefault(source.language or "(unknown)", []).append(source.rel_path)

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    for language in sorted(result):
        files = result[language]
        print(f"{language} ({len(files)})")
        for path in files:
            print(f"  {path}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        config = _resolve_config(args)
        repository = _preset_repository(config)
    except ConfigError as exc:
        return _die(str(exc))

    problems: List[str] = []
    print("Configuration")
    if config.sources:
        for source in config.sources:
            print(f"  loaded: {source}")
    else:
        print("  loaded: (none - using built-in presets only)")
    print(f"  auto_detect: {config.auto_detect}")
    print(f"  rules: {len(config.rules)}")
    print(f"  overrides: {len(config.overrides)}")
    print(f"  extends: {', '.join(config.extends) or '-'}")

    for name in config.extends:
        if repository.get(name) is None:
            problems.append(f"unknown preset in extends: {name}")

    registry = get_registry()
    for rule in config.rules:
        try:
            registry.create(rule)
        except ConfigError as exc:
            problems.append(str(exc))

    known_ids = set(config.rule_ids())
    for name in repository.names():
        for rule in repository.presets[name].build_rules():
            known_ids.add(rule.id)
    for override_id in config.overrides:
        if override_id not in known_ids:
            problems.append(f"override refers to unknown rule: {override_id}")

    print("Presets")
    print(f"  available: {len(repository.names())}")
    for error in repository.errors:
        problems.append(error)

    if problems:
        print("\nProblems:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("\nOK - configuration looks valid.")
    return 0


def cmd_types(args: argparse.Namespace) -> int:
    registry = get_registry()
    print("Built-in check types:")
    for name in registry.names():
        cls = registry.get(name)
        help_text = getattr(cls, "help", "") or ""
        fixable = " (fixable)" if getattr(cls, "fixable", False) else ""
        print(f"  {name:<22}{fixable:<11} {help_text}")
    return 0


def cmd_version(args: argparse.Namespace) -> int:
    print(f"alinter {__version__}")
    return 0


HANDLERS = {
    "check": cmd_check,
    "lint": cmd_check,
    "run": cmd_check,
    "init": cmd_init,
    "presets": cmd_presets,
    "rules": cmd_rules,
    "explain": cmd_explain,
    "langs": cmd_langs,
    "validate": cmd_validate,
    "types": cmd_types,
    "version": cmd_version,
}


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point. Returns a process exit code."""
    raw = list(sys.argv[1:] if argv is None else argv)
    if not raw or (raw[0] not in COMMANDS and raw[0] not in ("-h", "--help", "--version")):
        raw = ["check", *raw]
    parser = _build_parser()
    args = parser.parse_args(raw)
    if not getattr(args, "command", None):
        parser.print_help()
        return 2
    handler = HANDLERS.get(args.command)
    if handler is None:  # pragma: no cover - argparse prevents this
        return _die(f"unknown command {args.command!r}")
    try:
        return handler(args)
    except KeyboardInterrupt:  # pragma: no cover
        return 130
    except ConfigError as exc:
        return _die(str(exc))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
