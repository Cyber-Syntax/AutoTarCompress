---
title: "ADR-0005: Migrate from Flat Layout to src Layout"
status: "Proposed"
date: "2026-02-28"
authors: "Cyber-Syntax"
tags: ["architecture", "decision", "packaging", "project-structure"]
supersedes: ""
superseded_by: ""
---

## Status

**Proposed**

## Context

The AutoTarCompress project currently uses a **flat layout** where the `autotarcompress/` package directory sits at the repository root alongside `tests/`, `docs/`, `scripts/`, and other top-level directories:

```
AutoTarCompress/
├── autotarcompress/      # package source
│   ├── __init__.py
│   ├── main.py
│   ├── cli/
│   ├── commands/
│   ├── utils/
│   └── ...
├── tests/
├── docs/
├── scripts/
├── pyproject.toml
└── ...
```

This flat layout has several known drawbacks:

1. **Accidental import of uninstalled code** — Running `pytest` or `python` from the repository root can import the local `autotarcompress/` directory instead of the installed package. This masks packaging errors (e.g., missing files in the distribution) that only surface when users install from PyPI or GitHub.
2. **Build contamination risk** — Build tools like setuptools may accidentally include test files, scripts, or other top-level directories in the distribution if `find` configuration is not perfectly maintained. The current `pyproject.toml` uses `[tool.setuptools.packages.find]` with explicit `exclude` patterns to work around this.
3. **Inconsistent with modern Python packaging standards** — The [Python Packaging User Guide](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/) recommends the src layout for libraries and applications. Most modern Python projects (and tools like `uv`, `hatch`, `flit`) default to or prefer the src layout.
4. **Ruff include paths reference the flat structure** — The current `pyproject.toml` ruff config includes `"autotarcompress/**/*.py"` which would need updating regardless.

## Decision

Migrate the project to a **src layout** by moving the `autotarcompress/` package directory under a new `src/` directory:

```
AutoTarCompress/
├── src/
│   └── autotarcompress/
│       ├── __init__.py
│       ├── main.py
│       ├── cli/
│       ├── commands/
│       ├── utils/
│       └── ...
├── tests/
├── docs/
├── scripts/
├── pyproject.toml
└── ...
```

This aligns the project with the widely adopted Python src layout convention, preventing accidental imports of the source tree during testing and ensuring the installed package is always tested rather than the local directory.

### Configuration Changes

- **`pyproject.toml`**: Update `[tool.setuptools.packages.find]` to `where = ["src"]` and remove the `exclude` list since `tests/`, `scripts/`, etc. are no longer siblings of the package.
- **`pyproject.toml`**: Update `[tool.pytest.ini_options]` to set `pythonpath = ["src"]`.
- **`pyproject.toml`**: Update `[tool.ruff]` include paths from `"autotarcompress/**/*.py"` to `"src/**/*.py"`.
- **`pyproject.toml`**: Update `[tool.mypy]` source paths if configured.
- **Import paths**: No changes — all imports remain `from autotarcompress.xxx import yyy` since the package name is unchanged.
- **`AGENTS.md`**: Update repository structure documentation.

## Consequences

### Positive

- **POS-001**: Eliminates accidental import of local source during testing — `pytest` always tests the installed package, catching packaging bugs early.
- **POS-002**: Simplifies `pyproject.toml` packaging configuration — the `exclude` patterns for `tests*`, `scripts*`, `docs*`, `examples*` become unnecessary since they are outside `src/`.
- **POS-003**: Aligns with Python packaging best practices and the recommendation of the Python Packaging Authority (PyPA).
- **POS-004**: Better compatibility with modern build backends (`hatch`, `flit`, `maturin`) if the project migrates from `setuptools` in the future.
- **POS-005**: Clearer separation of concerns — source code lives in `src/`, everything else (tests, docs, scripts, config) lives at the root.

### Negative

- **NEG-001**: Requires a one-time migration of all files under `autotarcompress/` into `src/autotarcompress/`, which will show as large file renames in git history. Mitigated by using `git mv` to preserve history.
- **NEG-002**: All developer documentation, CI scripts, and contributor workflows that reference `autotarcompass/` paths must be updated simultaneously.
- **NEG-003**: The `uv run autotarcompress` development workflow requires the editable install (`uv pip install -e .`) to resolve the `src/` indirection — this is already the case with `uv run`.
- **NEG-004**: Existing ADRs and documentation reference the flat layout paths and will need path updates.

## Alternatives Considered

### Keep the Flat Layout

- **ALT-001**: **Description**: Maintain the current flat layout with `autotarcompress/` at the root, relying on `[tool.setuptools.packages.find]` exclude patterns and `pythonpath` configuration to work correctly.
- **ALT-002**: **Rejection Reason**: The flat layout continues to risk accidental local imports during development and testing. The `exclude` list in `pyproject.toml` is fragile — adding a new top-level directory requires remembering to exclude it. The src layout eliminates these issues structurally.

### Use a Namespace Package Under src/

- **ALT-003**: **Description**: Adopt a namespace package structure like `src/cyber_syntax/autotarcompress/` for future multi-package support.
- **ALT-004**: **Rejection Reason**: Over-engineering for a single-package project. Namespace packages add complexity with no current benefit. If multi-package support is needed later, migration from `src/autotarcompress/` to a namespace is straightforward.

## Implementation Notes

- **IMP-001**: Use `git mv autotarcompress/ src/autotarcompress/` to preserve file history in version control.
- **IMP-002**: Update `pyproject.toml` fields:
    - `[tool.setuptools.packages.find]`: set `where = ["src"]`, remove `exclude`
    - `[tool.pytest.ini_options]`: set `pythonpath = ["src"]`
    - `[tool.ruff]`: update `include` paths to reference `src/`
- **IMP-003**: Update `AGENTS.md` repository structure section to reflect the new layout.
- **IMP-004**: Run the full test suite (`uv run pytest`) after migration to verify no import breakage.
- **IMP-005**: Update CI workflows if they reference `autotarcompress/` paths directly.
- **IMP-006**: Success criteria — `uv run pytest -m "not slow"` passes, `uv run autotarcompress --help` works, and `ruff check src/` reports no new issues.

## References

- **REF-001**: [Python Packaging — src layout vs flat layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/)
- **REF-002**: [setuptools — package discovery](https://setuptools.pypa.io/en/latest/userguide/package_discovery.html)
- **REF-003**: [pyproject.toml](../../pyproject.toml) — current packaging and tool configuration
- **REF-004**: [AGENTS.md](../../AGENTS.md) — repository structure documentation
