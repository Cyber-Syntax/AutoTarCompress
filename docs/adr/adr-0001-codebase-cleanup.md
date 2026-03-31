---
title: "ADR-0001: Codebase Cleanup — Remove Unused Code"
status: "Proposed"
date: "2026-02-28"
authors: "Cyber-Syntax"
tags: ["architecture", "decision", "maintenance", "code-quality"]
supersedes: ""
superseded_by: ""
---

## Status

**Proposed**

## Context

The AutoTarCompress project has evolved through several refactoring rounds (command pattern adoption, module restructuring, migration to Typer CLI, migration to `uv`). During these iterations, unused methods, variables, imports, and dead code paths have accumulated across the codebase. This technical debt increases cognitive load for contributors, inflates line counts, and can obscure actual logic when debugging or reviewing changes.

Key areas of concern:

- Unused imports in modules such as `base_manager.py`, `config.py`, and command handlers.
- Methods or helper functions that were once needed but are no longer called after refactoring.
- Variables assigned but never referenced downstream.
- Potentially stale default values and configuration paths carried from earlier designs.

The project already enforces strict linting via `ruff` with `select = ["ALL"]`, which catches many categories of issues, but a dedicated audit pass is needed to address accumulated dead code holistically.

## Decision

Perform a systematic codebase cleanup pass across all Python modules under `autotarcompress/` and `tests/`:

1. **Run `ruff check` with all rules enabled** to identify unused imports (`F401`), unused variables (`F841`), and other code quality issues.
2. **Manually audit** each module to find unused methods and dead code paths that static analysis alone may not flag (e.g., methods only referenced via conditional branches that are never true).
3. **Remove** all confirmed unused code and verify no regressions via the existing test suite (`uv run pytest`).
4. **Do not change** public API surface or CLI command signatures during this cleanup — the scope is strictly internal.

## Consequences

### Positive

- **POS-001**: Reduced cognitive load — fewer irrelevant symbols for contributors to parse when reading or modifying code.
- **POS-002**: Smaller codebase footprint — faster static analysis, linting, and IDE indexing.
- **POS-003**: Cleaner diff history going forward — future changes will not intermingle with dead code removal.
- **POS-004**: Improved test coverage accuracy — dead code inflates the denominator of coverage ratios, masking true coverage gaps.

### Negative

- **NEG-001**: Risk of accidentally removing code that is still reachable through dynamic dispatch or rarely-exercised branches. Mitigated by running the full test suite.
- **NEG-002**: One-time effort with no user-facing impact — may compete with feature work for developer time.
- **NEG-003**: Git blame will shift for affected lines, making historical root-cause analysis slightly harder for those specific lines.

## Alternatives Considered

### Incremental Cleanup Only

- **ALT-001**: **Description**: Rely solely on `ruff`'s auto-fix (`ruff check --fix`) and address issues file-by-file as they are touched for other work.
- **ALT-002**: **Rejection Reason**: This approach is slower to converge and leaves dead code persisting in untouched modules indefinitely.

### Large-Scale Rewrite

- **ALT-003**: **Description**: Combine the cleanup with a broader rewrite or restructuring of the codebase.
- **ALT-004**: **Rejection Reason**: Violates YAGNI and introduces unnecessary risk. The current module structure (command pattern, manager classes) is sound; only dead code should be removed.

## Implementation Notes

- **IMP-001**: Start by running `ruff check autotarcompress/ tests/ --statistics` to get a summary of issue categories and counts.
- **IMP-002**: Apply safe auto-fixes first via `ruff check --fix`, then manually review remaining items.
- **IMP-003**: Run `uv run pytest` after each batch of changes to confirm no regressions before committing.
- **IMP-004**: Use `vulture` or similar dead-code detection tools as a supplementary pass to catch unreachable functions that `ruff` may not flag.
- **IMP-005**: Success criteria — zero `F401` (unused import) and `F841` (unused variable) warnings from `ruff`, and all existing tests pass.

## References

- **REF-001**: [Ruff documentation — rule index](https://docs.astral.sh/ruff/rules/)
- **REF-002**: [Vulture — find unused Python code](https://github.com/jendrikseipp/vulture)
- **REF-003**: [pyproject.toml](../../pyproject.toml) — current ruff configuration
