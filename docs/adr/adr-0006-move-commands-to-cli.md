---
title: "ADR-0006: Move commands/ Folder into cli/ Folder"
status: "Proposed"
date: "2026-02-28"
authors: "Cyber-Syntax"
tags: ["architecture", "decision", "project-structure", "refactoring"]
supersedes: ""
superseded_by: ""
---

## Status

**Proposed**

## Context

The AutoTarCompress project currently has two separate subpackages that handle CLI-related concerns:

```
autotarcompress/
├── cli/
│   ├── __init__.py    # Exports Typer app
│   ├── parser.py      # Typer CLI commands and argument parsing
│   └── runner.py      # Config initialization and file utilities
├── commands/
│   ├── __init__.py    # Aggregates all command classes
│   ├── command.py     # Abstract Command ABC (execute() -> bool)
│   ├── backup.py      # BackupCommand
│   ├── encrypt.py     # EncryptCommand
│   ├── decrypt.py     # DecryptCommand
│   ├── extract.py     # ExtractCommand
│   ├── cleanup.py     # CleanupCommand
│   └── info.py        # InfoCommand
└── ...
```

This separation creates issues:

1. **Tight coupling between `cli/` and `commands/`** — `cli/parser.py` imports and instantiates every command class from `commands/`. The two packages are functionally inseparable — `commands/` has no consumers other than `cli/parser.py`.
2. **Artificial boundary** — The `commands/` folder contains the Command Pattern implementation that is exclusively orchestrated by the CLI layer. Splitting them into sibling packages suggests they are independent concerns, but they are not.
3. **Navigation overhead** — Developers must jump between two directories to understand the full CLI flow: `cli/parser.py` defines the Typer commands, then delegates to `commands/*.py`, which in turn delegates to `*_manager.py` classes. Collapsing `commands/` into `cli/` reduces one level of indirection.
4. **Import path verbosity** — Current imports like `from autotarcompress.commands.backup import BackupCommand` would become `from autotarcompress.cli.commands.backup import BackupCommand`, which more accurately reflects the ownership hierarchy.

## Decision

Move the `commands/` folder into `cli/` as a subpackage, resulting in:

```
autotarcompress/
├── cli/
│   ├── __init__.py      # Exports Typer app
│   ├── parser.py        # Typer CLI commands and argument parsing
│   ├── runner.py        # Config initialization and file utilities
│   └── commands/
│       ├── __init__.py  # Aggregates all command classes
│       ├── command.py   # Abstract Command ABC
│       ├── backup.py    # BackupCommand
│       ├── encrypt.py   # EncryptCommand
│       ├── decrypt.py   # DecryptCommand
│       ├── extract.py   # ExtractCommand
│       ├── cleanup.py   # CleanupCommand
│       └── info.py      # InfoCommand
└── ...
```

This consolidates all CLI-related code under a single `cli/` package, making the ownership hierarchy explicit: the CLI layer owns the command definitions and orchestration.

## Consequences

### Positive

- **POS-001**: Clearer package hierarchy — all CLI-related code (argument parsing, command definitions, config initialization) lives under `cli/`, reflecting the actual dependency graph.
- **POS-002**: Reduced import confusion — the `commands/` subpackage is nested under its sole consumer, eliminating the false impression that it is an independent, reusable module.
- **POS-003**: Easier navigation — developers exploring the CLI flow only need to look within `cli/` rather than jumping between two top-level subpackages.
- **POS-004**: Better alignment with the Command Pattern — the `cli/` package acts as the invoker, and its `commands/` subpackage contains the command objects, mirroring the pattern's structure.

### Negative

- **NEG-001**: All imports of `from autotarcompress.commands.xxx` must be updated to `from autotarcompress.cli.commands.xxx` across the codebase and tests. This is a mechanical but broad change.
- **NEG-002**: Git history for files in `commands/` will show a rename. Mitigated by using `git mv` to preserve history tracking.
- **NEG-003**: The top-level `autotarcompress/__init__.py` currently exports command classes — these import paths must be updated.
- **NEG-004**: If `commands/` were ever needed by a non-CLI consumer (e.g., a Python API), the nesting under `cli/` would be semantically incorrect. However, no such use case exists or is planned.

## Alternatives Considered

### Keep commands/ as a Sibling Package

- **ALT-001**: **Description**: Maintain `commands/` as a top-level subpackage of `autotarcompress/`, separate from `cli/`.
- **ALT-002**: **Rejection Reason**: The current structure implies `commands/` is an independent module, but it is exclusively consumed by `cli/parser.py`. Keeping them separate adds navigational overhead and misrepresents the dependency relationship.

### Merge commands/ Directly into cli/ (No Subpackage)

- **ALT-003**: **Description**: Move all command files (`backup.py`, `encrypt.py`, etc.) directly into `cli/` without a `commands/` subdirectory, renaming them to `cmd_backup.py`, `cmd_encrypt.py`, etc.
- **ALT-004**: **Rejection Reason**: Flattening 8 command files into `cli/` would make the directory crowded (10+ files) and lose the logical grouping. The `commands/` subdirectory preserves the Command Pattern organization and keeps `cli/` manageable.

### Create a Shared commands/ Library Package

- **ALT-005**: **Description**: Refactor `commands/` into a generic, reusable command library that could be consumed by multiple frontends (CLI, GUI, API).
- **ALT-006**: **Rejection Reason**: Over-engineering — AutoTarCompress is a CLI-only tool with no plans for alternative frontends. The command classes already delegate all logic to `*_manager.py` classes, which are the actual reusable layer.

## Implementation Notes

- **IMP-001**: Use `git mv autotarcompress/commands/ autotarcompress/cli/commands/` to preserve file history.
- **IMP-002**: Update all import statements project-wide:
    - `from autotarcompress.commands.xxx` → `from autotarcompress.cli.commands.xxx`
    - `from autotarcompress.commands import xxx` → `from autotarcompress.cli.commands import xxx`
- **IMP-003**: Update `autotarcompress/__init__.py` if it re-exports command classes.
- **IMP-004**: Update `autotarcompress/cli/parser.py` imports from `autotarcompress.commands.*` to relative imports (`from .commands.xxx import XxxCommand`) or absolute imports with the new path.
- **IMP-005**: Update all test files that import from `autotarcompress.commands` (notably `tests/test_commands.py`).
- **IMP-006**: Update `AGENTS.md` repository structure section.
- **IMP-007**: Success criteria — `uv run pytest -m "not slow"` passes, `ruff check .` reports no import errors, and `uv run autotarcompress --help` works correctly.

## References

- **REF-001**: [autotarcompress/cli/parser.py](../../autotarcompress/cli/parser.py) — CLI command definitions that consume `commands/`
- **REF-002**: [autotarcompress/commands/command.py](../../autotarcompress/commands/command.py) — Abstract Command ABC
- **REF-003**: [ADR-0005: Migrate from Flat Layout to src Layout](adr-0005-migrate-src-layout.md) — related structural change (should be coordinated)
- **REF-004**: [AGENTS.md](../../AGENTS.md) — repository structure documentation
