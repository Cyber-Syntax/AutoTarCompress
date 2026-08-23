# AGENTS.md

This document provides context, patterns, and guidelines for AI coding assistants working in this repository.

## Project Overview

AutoTarCompress is a Python 3.14+ CLI tool for managing backup archives on Linux
**Core Features**: Create compressed backups (tar+zstd), AES-256-GCM encryption/decryption, SHA256 integrity verification, archive extraction, and cleanup with configurable retention policies.
**Package Manager**: uv (replaces pip/poetry)

## Core Technologies

- **Python**: 3.14+ (fully synchronous — no async)
- **CLI Framework**: Typer (with Click underneath)
- **Compression**: tarfile + zstandard (zstd), legacy tar.xz support
- **Encryption**: `cryptography` library (AES-256-GCM, PBKDF2 key derivation)
- **Hashing**: SHA256 for integrity verification throughout backup lifecycle
- **Config Format**: INI (.conf) for global config, JSON for backup metadata
- **Testing**: pytest with pytest-cov, pytest-mock, hypothesis
- **Linting**: ruff (linter + formatter)
- **Type Checking**: mypy (strict mode)

## Repository Structure

```
autotarcompress/
├── __init__.py              # Package init, exposes managers, dynamic __version__
├── main.py                  # Entry point (Typer app invocation)
├── config.py                # BackupConfig dataclass (INI format)
├── metadata.py              # BackupMetadata dataclass (JSON, v2.0)
├── logger.py                # Logging setup (RotatingFileHandler, 1MB, 3 backups)
├── base_manager.py          # BaseCryptoManager (shared crypto: PBKDF2, key derivation)
├── backup_manager.py        # BackupManager (tar+zstd compression)
├── encrypt_manager.py       # EncryptManager (AES-256-GCM encryption)
├── decrypt_manager.py       # DecryptManager (decryption with retries)
├── extract_manager.py       # ExtractManager (tar.zst and tar.xz extraction)
├── cleanup_manager.py       # CleanupManager (retention policies)
├── info_manager.py          # InfoManager (metadata display)
├── cli/
│   ├── __init__.py          # Exports Typer app
│   ├── parser.py            # Typer CLI commands and argument parsing
│   └── runner.py            # Config initialization and file utilities
├── commands/
│   ├── __init__.py          # Aggregates all command classes
│   ├── command.py           # Abstract Command ABC (execute() -> bool)
│   ├── backup.py            # BackupCommand
│   ├── encrypt.py           # EncryptCommand
│   ├── decrypt.py           # DecryptCommand
│   ├── extract.py           # ExtractCommand
│   ├── cleanup.py           # CleanupCommand
│   └── info.py              # InfoCommand
└── utils/
    ├── __init__.py          # Utility exports
    ├── utils.py             # Path validation, backup folder creation, pv detection
    ├── hash_utils.py        # SHA256 calculation and verification
    ├── progress_bar.py      # SimpleProgressBar with ETA
    ├── get_password.py      # Secure password handling (PasswordContext, memory zeroing)
    ├── format.py            # Human-readable size formatting
    └── size_calculator.py   # Directory size calculator with ignore patterns

```

## Development Workflow

### Common Development Tasks

#### Running the CLI

```bash
# Run from source without installation
uv run autotarcompress <command> [options]

# Examples
uv run autotarcompress backup
uv run autotarcompress encrypt --latest
uv run autotarcompress encrypt --date dd-mm-yyyy
uv run autotarcompress decrypt --latest
uv run autotarcompress decrypt --date dd-mm-yyyy
uv run autotarcompress extract --latest
uv run autotarcompress extract --date dd-mm-yyyy
uv run autotarcompress cleanup --name my-project
uv run autotarcompress info --name my-project
uv run autotarcompress version
uv run autotarcompress --help
```

#### Installation Methods

```bash
# Development (editable install via uv)
./install.sh uv-dev

# Production (install from GitHub)
./install.sh uv-prod

# Legacy (deprecated)
./install.sh install

# Shell autocomplete
./install.sh autocomplete bash   # or zsh, or both

# Remove legacy installation
./install.sh remove [--dry-run]
```

#### Making Code Changes

**CRITICAL**: Always run ruff on modified files before committing.

```bash
# 1. Make your changes to files in autotarcompress/

# 2. Run linting (auto-fix issues)
ruff check --fix path/to/file.py
ruff check --fix . # or all Python files

# 3. Run formatting
ruff format path/to/file.py
ruff format . # or all Python files

# 4. Run type checking
uv run mypy autotarcompress/

# 5. Run fast tests (excludes slow logger tests)
uv run pytest -m "not slow"

# 6. Verify CLI still works
uv run autotarcompress --help
```

## Code Quality Standards

### Type Hints

CRITICAL: All Python code MUST include type hints and return types.

```python
# CORRECT
def filter_unknown_users(users: list[str], known_users: set[str]) -> list[str]:
    """Filter out users that are not in the known users set.

    Args:
        users: List of user identifiers to filter.
        known_users: Set of known/valid user identifiers.

    Returns:
        List of users that are not in the `known_users` set.
    """
    return [u for u in users if u not in known_users]

# INCORRECT (no type hints)
def filter_unknown_users(users, known_users):
    return [u for u in users if u not in known_users]
```

- **Type Annotations**: Use built-in types: `list[str]`, `dict[str, int]` (not `typing.List`, `typing.Dict`)

### Coding Standards

- **Logging Format**: Use `%s` style formatting in logging statements: `logger.info("User %s logged in", username)`
- **PEP 8**: Enforced by ruff
- **Datetime**: Use `astimezone()` for local time conversions
- **Variable Names**: Use descriptive, self-explanatory names
- **Functions**: Use functions over classes when state management is not needed
- **Function Size**: Keep functions focused (<20 lines when possible)
- **Pure Functions**: Prefer pure functions without side effects when possible
- **Error Handling**: Use custom exceptions from `exceptions.py`
- **Async Safe**:
    - All I/O operations must have async variants
    - Never block the event loop with sync I/O in async context
- **DRY Approach**:
    - Reuse existing abstractions; don't duplicate
    - Refactor safely when duplication is found
    - Check existing protocols before creating new ones

### Error Handling Guidelines

```python
# CORRECT - Handle expected errors, return bool for success/failure
try:
    hash_value = calculate_sha256(filepath)
except OSError as e:
    logger.warning("Failed to hash %s: %s", filepath, e)
    return False

# CORRECT - Log and exit gracefully via Typer
if not config.verify_config():
    logger.error("Invalid configuration")
    raise typer.Exit(1)

# INCORRECT - Don't use logger.exception() for expected errors
try:
    data = metadata.load()
except FileNotFoundError as e:
    logger.exception("Missing metadata")  # Leaks stack trace unnecessarily

# INCORRECT - Don't log passwords or sensitive data
logger.debug("Password: %s", password)  # Security risk!
```

## Testing Instructions

### Test Structure

Tests use a flat structure — all test files live directly in `tests/`. Shared fixtures are in `tests/conftest.py`.

**Key Fixtures** (from `tests/conftest.py`):

- `temp_dir` — Creates and cleans up a temporary directory
- `test_config` — `BackupConfig` instance with temp paths
- `test_backup_files` — Creates sample `.tar.xz` and `.enc` files
- `test_data_dir` — Creates test data with files and ignored directories
- `mock_backup_info` — Mock metadata dictionary

### Writing Tests

**CRITICAL**: Every new feature or bugfix MUST be covered by unit tests.

```python
# Example test structure
import pytest
from unittest.mock import MagicMock, patch

from autotarcompress.backup_manager import BackupManager
from autotarcompress.utils import verify_hash


class TestBackupManager:
    """Tests for BackupManager."""

    def test_backup_creates_archive(
        self, test_config: BackupConfig, tmp_path: Path,
    ) -> None:
        """Test that backup creates a compressed archive."""
        # Arrange
        manager = BackupManager(config=test_config)

        # Act
        result = manager.create_backup()

        # Assert
        assert result is True

    def test_hash_verification_failure(self) -> None:
        """Test that verification fails with incorrect hash."""
        # Arrange
        expected_hash = "abc123"
        actual_hash = "def456"

        # Act & Assert
        assert verify_hash(actual_hash, expected_hash) is False
```

### Testing Patterns

- **Class-based organization**: Group related tests in classes (`class TestBackupManager:`)
- **Mocking**: `unittest.mock` (MagicMock, patch) for external dependencies
- **CLI testing**: `typer.testing.CliRunner` for command-line tests
- **Arrange/Act/Assert**: Standard test pattern
- **All synchronous**: No async tests (project has no async code)
- **Type annotations**: Required on all test methods (return `-> None`)
- **Markers**: `slow`, `integration` for selective test runs

### Running Tests

```bash
# Run fast tests only (excludes slow logger integration tests)
uv run pytest -m "not slow"

# Run all tests (including slow tests)
uv run pytest

# Run tests with coverage
uv run pytest --cov=autotarcompress --cov-report=html

# Run specific test file
uv run pytest tests/test_backup_manager.py

# Run specific test class or function
uv run pytest tests/test_backup_manager.py::TestBackupManager::test_backup_creates_archive
```

### Test Checklist

Before committing, verify:

- [ ] Tests fail when your new logic is broken
- [ ] Happy path is covered
- [ ] Edge cases and error conditions are tested
- [ ] External dependencies are mocked (no real network calls in unit tests)
- [ ] Tests are deterministic (no flaky tests)
- [ ] Test methods have type annotations (`-> None`)
- [ ] Test names clearly describe what they test

## Debugging and Troubleshooting

### Common Issues and Solutions

#### Linting/Formatting Issues

```bash
# Problem: Ruff errors that can't be auto-fixed
# Solution: Review ruff output and fix manually
ruff check path/to/file.py

# Problem: Type checking errors
# Solution: Run mypy with verbose output
uv run mypy --show-error-codes autotarcompress/

# Common type error fixes:
# - Update type hints to match actual usage
# - Check for missing return type annotations
# - Ensure correct use of built-in types (list[str], dict[str, int], etc.)
```

### Debugging Tips

#### Gather Runtime Information

```bash
# Check log file
tail -f ~/.config/autotarcompress/logs/autotarcompress.log

# View global config
cat ~/.config/autotarcompress/config.conf

# Check backup metadata
cat /path/to/backup/folder/metadata.json
```

## Project-Specific Notes

### Configuration Structure

- Configuration stored at `~/.config/autotarcompress/`:
    - `config.conf` — INI-format global configuration (`backup_folder`, `keep_backup`, `keep_enc_backup`, `log_level`, `dirs_to_backup`, `ignore_list`)
    - `logs/autotarcompress.log` — Rotating log file (1MB max, 3 backups)
- Backup metadata stored alongside backups:
    - `metadata.json` — BackupMetadata v2.0 with file hashes, timestamps, and backup details
