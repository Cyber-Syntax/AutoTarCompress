---
title: "ADR-0007: Remove Legacy venv-wrapper Install and Migrate Fully to uv"
status: "Proposed"
date: "2026-02-28"
authors: "Cyber-Syntax"
tags: ["architecture", "decision", "packaging", "installation", "uv"]
supersedes: ""
superseded_by: ""
---

## Status

**Proposed**

## Context

The AutoTarCompress project currently supports three installation methods via `install.sh`:

1. **Legacy `install`** — Copies source files to `~/.local/share/autotarcompress/`, creates a Python venv, installs the package in editable mode via `pip`, and installs a shell wrapper script (`scripts/venv-wrapper.sh`) to `~/.local/bin/autotarcompress`.
2. **`uv-dev`** — Runs `uv tool install --editable .` for development.
3. **`uv-prod`** — Runs `uv tool install git+https://github.com/Cyber-Syntax/AutoTarCompress --force` for production.

The legacy installation method has several problems:

1. **Redundant with uv** — The project already uses `uv` as its package manager for development (`uv run`, dependency management via `pyproject.toml`). Maintaining a parallel venv-based installation path duplicates effort and creates confusion about which method to use.
2. **Fragile file-copying approach** — The legacy installer copies source files to `~/.local/share/autotarcompress/` and creates a venv there. This is error-prone: updates require re-running the full installer, the wrapper script can break if paths change, and the venv can become stale.
3. **venv-wrapper.sh is a workaround** — The wrapper script (`scripts/venv-wrapper.sh`) exists solely to activate the venv and delegate to the installed console script. `uv tool install` handles this natively by creating managed tool environments with proper shims in `~/.local/bin/`.
4. **Maintenance burden** — The legacy `install`, `update`, PATH management (`ensure_path_for_shells`), and `remove` commands in `install.sh` account for ~150 lines of shell code that serve a deprecated workflow.
5. **install.sh autocomplete functions assume legacy paths** — The autocomplete installation references `$INSTALL_DIR/autocomplete/` which is the legacy install path, coupling shell completion to the legacy method.

## Decision

Remove the legacy venv-based installation method and migrate `install.sh` fully to `uv`:

### Remove

- **Legacy `install` command** — Remove `install_autotarcompress()`, `copy_source_to_install_dir()`, `setup_venv()`, `install_wrapper()` functions.
- **Legacy `update` command** — Remove `update_autotarcompress()` function.
- **venv-wrapper script** — Delete `scripts/venv-wrapper.sh`.
- **Legacy path management** — Remove `ensure_path_for_shells()`, `ensure_path_in_file()`, `detect_rc_file()` helper functions (only needed for legacy install).
- **Legacy configuration variables** — Remove `VENV_DIR`, `BIN_DIR`, `WRAPPER_SRC`, `WRAPPER_DST`, `EXPORT_LINE` variables.

### Keep and Update

- **`uv-dev` command** — Keep as-is (`uv tool install --editable .`). Rename to `install` as the default command.
- **`uv-prod` command** — Keep as-is (`uv tool install git+...`). Rename to `install-prod` or keep as `uv-prod`.
- **`remove` command** — Simplify to run `uv tool uninstall autotarcompress` instead of the interactive legacy removal. Keep legacy removal as a `remove-legacy` subcommand for users who still have the old installation.
- **`autocomplete` command** — Update to reference autocomplete files from the repository directory (or the uv tool environment) instead of `$INSTALL_DIR/autocomplete/`.

### Resulting install.sh Commands

| Command | Action |
|---------|--------|
| `install` | `uv tool install --editable .` (development) |
| `install-prod` | `uv tool install git+https://github.com/Cyber-Syntax/AutoTarCompress --force` |
| `uninstall` | `uv tool uninstall autotarcompress` |
| `remove-legacy` | Interactive removal of old venv-based install (transitional) |
| `autocomplete` | Install shell completion (bash/zsh/both) |

## Consequences

### Positive

- **POS-001**: Single installation method — users and documentation only reference `uv`, eliminating confusion about which method to use.
- **POS-002**: Reduced `install.sh` complexity — removing ~150 lines of legacy venv management code (file copying, venv creation, wrapper installation, PATH manipulation).
- **POS-003**: Better update workflow — `uv tool install --force` handles upgrades natively without manual file copying or venv rebuilds.
- **POS-004**: No wrapper script needed — `uv tool install` creates managed shims in `~/.local/bin/` automatically, making `venv-wrapper.sh` obsolete.
- **POS-005**: Consistent with the project's development workflow — developers already use `uv run` for running, testing, and linting. Production installation via `uv tool install` is the natural extension.

### Negative

- **NEG-001**: Users with existing legacy installations must manually clean up or use the transitional `remove-legacy` command. Mitigated by documenting the migration path in the changelog and README.
- **NEG-002**: `uv` becomes a hard requirement for installation (previously, users could install with just `python3` and `pip`). Mitigated by `uv`'s simple installation (`curl -LsSf https://astral.sh/uv/install.sh | sh`) and its growing adoption as a standard Python tool.
- **NEG-003**: The autocomplete installation must be reworked to locate completion scripts from the repository checkout or uv tool environment rather than the legacy `$INSTALL_DIR`.
- **NEG-004**: Users on systems where installing `uv` is restricted (e.g., locked-down corporate environments) lose the ability to install. This is an edge case for a personal CLI backup tool.

## Alternatives Considered

### Keep Both Installation Methods

- **ALT-001**: **Description**: Maintain the legacy venv-based installer alongside the uv commands, allowing users to choose their preferred method.
- **ALT-002**: **Rejection Reason**: Supporting two parallel installation methods doubles the maintenance burden, creates documentation confusion, and the legacy method provides no advantage over `uv tool install`. The project already requires Python 3.14+ which implies a modern development environment where `uv` is readily available.

### Replace with pipx Instead of uv

- **ALT-003**: **Description**: Use `pipx` for tool installation instead of `uv tool install`, since `pipx` is a more established tool for installing Python CLI applications.
- **ALT-004**: **Rejection Reason**: The project already uses `uv` for all development tasks (dependency management, running, testing). `uv tool install` provides the same functionality as `pipx` with better performance and integration with the existing `uv`-based workflow. Adding `pipx` as a separate tool would fragment the toolchain.

### Provide a Standalone Installer Script (No Tool Manager)

- **ALT-005**: **Description**: Create a self-contained install script that downloads the package from GitHub and installs it into an isolated environment without requiring `uv` or `pipx`.
- **ALT-006**: **Rejection Reason**: Reimplements what `uv tool install` already does (isolated environment creation, shim installation, upgrade management). The maintenance cost of a custom installer far outweighs the convenience of avoiding a `uv` dependency.

## Implementation Notes

- **IMP-001**: Create a transitional `remove-legacy` command in `install.sh` that reuses the existing `remove_legacy_install()` function, allowing users with old installations to clean up.
- **IMP-002**: Update `install.sh` entry point (`case` statement) to:
    - Default `install` → `uv tool install --editable .`
    - `install-prod` → `uv tool install git+... --force`
    - `uninstall` → `uv tool uninstall autotarcompress`
    - `remove-legacy` → existing interactive removal
    - `autocomplete` → updated path resolution
- **IMP-003**: Delete `scripts/venv-wrapper.sh`.
- **IMP-004**: Update autocomplete installation to locate completion scripts from the repository directory (`$(script_dir)/autocomplete/`) instead of `$INSTALL_DIR/autocomplete/`.
- **IMP-005**: Update `README.md`, `AGENTS.md`, and `docs/wiki.md` to remove references to legacy installation and document `uv`-based installation as the sole method.
- **IMP-006**: Add a migration note to `CHANGELOG.md` for the next release, guiding existing users to run `remove-legacy` before upgrading.
- **IMP-007**: Success criteria — `./install.sh install` runs `uv tool install --editable .` successfully, `autotarcompress --help` works after installation, and `./install.sh uninstall` cleanly removes the tool.

## References

- **REF-001**: [install.sh](../../install.sh) — current installer with legacy and uv methods
- **REF-002**: [scripts/venv-wrapper.sh](../../scripts/venv-wrapper.sh) — legacy wrapper script to be removed
- **REF-003**: [uv tool documentation](https://docs.astral.sh/uv/concepts/tools/)
- **REF-004**: [pyproject.toml](../../pyproject.toml) — `[project.scripts]` entry point definition
- **REF-005**: [AGENTS.md](../../AGENTS.md) — installation documentation
